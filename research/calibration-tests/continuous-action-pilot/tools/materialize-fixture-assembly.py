#!/usr/bin/env python3
"""Fail-closed materialization of continuous-001 fixture gate artifacts.

The production command reads exactly one pre-gate assembly fragment for each
of CA-R1, CA-R2, and CA-R3. It validates the fragments and hashes their
repository artifact references before it writes either final artifact. It
never interprets or executes a formal input, launches a fixture, or runs a
comparator.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


sys.dont_write_bytecode = True
TOOLS_DIRECTORY = Path(__file__).resolve().parent
if str(TOOLS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIRECTORY))

from formal_execution_target_contract import (  # noqa: E402
    BUILD_READINESS_IDENTITIES,
    EXECUTION_TARGET_PATHS,
    LOCK_EXACT_ROLE_PLACEMENTS,
    LOCK_REQUIRED_ROLE_PLACEMENTS,
    expected_lock_paths,
)

RUN_ID = "continuous-001"
CASES = ("CA-R1", "CA-R2", "CA-R3")
URL_PREFIX = "https://github.com/onovich/Game-Primitives/blob/main/"
BASE = "research/calibration-tests/continuous-action-pilot"
RUN = f"{BASE}/runs/{RUN_ID}"
SCHEMA = f"{BASE}/schema"

FRAGMENT_SCHEMA_PATH = f"{SCHEMA}/fixture-assembly-fragment-0.1.0.schema.json"
READINESS_SCHEMA_PATH = f"{SCHEMA}/formal-build-readiness-0.1.0.schema.json"
FIXTURE_LOCK_SCHEMA_PATH = f"{SCHEMA}/fixture-lock-0.1.0.schema.json"
TASK_PACKET_SCHEMA_PATH = f"{SCHEMA}/task-packet-0.1.0.schema.json"
BUILD_EVIDENCE_SCHEMA_PATH = f"{SCHEMA}/fixture-build-evidence-0.1.0.schema.json"
R2_BUILD_EVIDENCE_SCHEMA_PATH = (
    f"{SCHEMA}/r2-build-readiness-evidence-0.1.0.schema.json"
)
R3_BUILD_EVIDENCE_SCHEMA_PATH = (
    f"{SCHEMA}/r3-build-list-evidence-0.1.0.schema.json"
)
READINESS_PATH = f"{RUN}/fixtures/formal-build-readiness-v0.1.0.json"
FIXTURE_LOCK_PATH = f"{RUN}/fixtures/fixture-lock.json"
SUPERSEDES_PATH = f"{RUN}/fixtures/toolchain-probe-v0.1.2.json"

FRAGMENT_PATHS = {
    "CA-R1": (
        f"{RUN}/fixtures/r1/r1-fixture-assembly-fragment-v0.1.0.json"
    ),
    "CA-R2": (
        f"{RUN}/fixtures/r2/r2-fixture-assembly-fragment-v0.1.0.json"
    ),
    "CA-R3": (
        f"{RUN}/fixtures/r3/r3-fixture-assembly-fragment-v0.1.0.json"
    ),
}

FRAGMENT_SCHEMA_ID = URL_PREFIX + FRAGMENT_SCHEMA_PATH
READINESS_SCHEMA_ID = URL_PREFIX + READINESS_SCHEMA_PATH
FIXTURE_LOCK_SCHEMA_ID = URL_PREFIX + FIXTURE_LOCK_SCHEMA_PATH

READINESS_ARTIFACT_ID = "readiness.continuous-001.formal-build.v0.1.0"
SELF_TEST_MARKER = ".synthetic-fixture-assembly-self-test"
SELF_TEST_TOKEN = "continuous-001-disposable-fixture-assembly-self-test"
FORBIDDEN_REFERENCE_PATHS = {
    READINESS_PATH,
    FIXTURE_LOCK_PATH,
    f"{RUN}/inputs/truth-commitment.json",
    f"{RUN}/execution/formal-execution-permit.json",
}
FORBIDDEN_REFERENCE_PREFIXES = (
    f"{RUN}/submissions/",
    f"{RUN}/reports/",
    f"{RUN}/reveal/",
)


class AssemblyError(RuntimeError):
    """A fail-closed fixture assembly error."""


@dataclass(frozen=True)
class LoadedFragment:
    document: dict[str, Any]
    fixture_lock_case: dict[str, Any]


@dataclass(frozen=True)
class EvidenceOutput:
    bytes: int
    external_path: str
    output_id: str
    sha256: str


@dataclass(frozen=True)
class EvidenceProjection:
    case_id: str
    configuration_attempt_ids: dict[str, tuple[str, ...]]
    configuration_outputs: dict[str, tuple[EvidenceOutput, ...]]
    source_commit: str


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def repo_path(repo_root: Path, value: str | Path, *, must_exist: bool = True) -> Path:
    candidate = (repo_root / value).resolve()
    if not candidate.is_relative_to(repo_root):
        raise AssemblyError(f"path escapes repository root: {value}")
    if must_exist and not candidate.is_file():
        raise AssemblyError(f"required file does not exist: {value}")
    return candidate


def relative_path(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AssemblyError(f"UTF-8 BOM is forbidden: {path}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AssemblyError(f"invalid UTF-8 JSON: {path}") from error
    if not isinstance(value, dict):
        raise AssemblyError(f"expected a JSON object: {path}")
    return value, raw


def artifact_reference(
    repo_root: Path,
    value: str | Path,
    *,
    artifact_id: str,
) -> dict[str, str]:
    path = repo_path(repo_root, value)
    return {
        "artifact_id": artifact_id,
        "path": relative_path(repo_root, path),
        "sha256": sha256_bytes(path.read_bytes()),
    }


def iter_references(value: Any) -> Iterable[dict[str, str]]:
    if isinstance(value, dict):
        if {"artifact_id", "path", "sha256"}.issubset(value):
            yield {
                "artifact_id": value["artifact_id"],
                "path": value["path"],
                "sha256": value["sha256"],
            }
        for child in value.values():
            yield from iter_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_references(child)


def verify_reference(repo_root: Path, reference: dict[str, str]) -> Path:
    path_value = reference["path"]
    if (
        path_value in FORBIDDEN_REFERENCE_PATHS
        or path_value.startswith(FORBIDDEN_REFERENCE_PREFIXES)
    ):
        raise AssemblyError(
            f"pre-gate fragment references forbidden artifact: {path_value}"
        )
    path = repo_path(repo_root, path_value)
    run_root = repo_path(repo_root, RUN, must_exist=False)
    if not path.is_relative_to(run_root):
        raise AssemblyError(
            f"fragment artifact is outside the formal run directory: {path_value}"
        )
    actual = sha256_bytes(path.read_bytes())
    if actual != reference["sha256"]:
        raise AssemblyError(
            f"hash mismatch for {path_value}: "
            f"expected {reference['sha256']}, got {actual}"
        )
    return path


def load_schema_registry(
    repo_root: Path,
) -> tuple[Registry, dict[str, dict[str, Any]]]:
    required = {
        TASK_PACKET_SCHEMA_PATH,
        READINESS_SCHEMA_PATH,
        FIXTURE_LOCK_SCHEMA_PATH,
        FRAGMENT_SCHEMA_PATH,
        BUILD_EVIDENCE_SCHEMA_PATH,
        R2_BUILD_EVIDENCE_SCHEMA_PATH,
    }
    schema_root = repo_path(repo_root, SCHEMA, must_exist=False)
    if not schema_root.is_dir():
        raise AssemblyError(f"schema directory does not exist: {SCHEMA}")
    discovered = {
        relative_path(repo_root, path): path
        for path in schema_root.glob("*.schema.json")
        if path.is_file()
    }
    missing = sorted(required - set(discovered))
    if missing:
        raise AssemblyError(f"required schemas are missing: {', '.join(missing)}")
    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    for relative, path in sorted(discovered.items()):
        schema, _ = read_json(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str):
            raise AssemblyError(f"schema lacks $id: {relative}")
        schemas[relative] = schema
        registry = registry.with_resource(
            schema_id,
            Resource.from_contents(schema),
        )
    return registry, schemas


def schema_for_document(
    document: dict[str, Any],
    schemas: dict[str, dict[str, Any]],
    *,
    label: str,
) -> dict[str, Any]:
    declared = document.get("$schema")
    if not isinstance(declared, str):
        raise AssemblyError(f"{label} does not declare a schema")
    for schema in schemas.values():
        if schema.get("$id") == declared:
            return schema
    raise AssemblyError(f"{label} declares an unregistered schema: {declared}")


def validate_document(
    document: dict[str, Any],
    schema: dict[str, Any],
    registry: Registry,
    *,
    label: str,
) -> None:
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(document), key=lambda item: list(item.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
            f"{error.message}"
            for error in errors
        )
        raise AssemblyError(f"{label} failed schema validation: {details}")


def verify_external_file(
    reference: dict[str, Any],
    *,
    label: str,
    allow_empty: bool = False,
) -> Path:
    raw_path = reference["external_path"]
    path = Path(raw_path)
    if not path.is_absolute():
        raise AssemblyError(f"{label} external path is not absolute: {raw_path}")
    resolved = path.resolve()
    if not resolved.is_file():
        raise AssemblyError(f"{label} external file is absent: {raw_path}")
    actual_bytes = resolved.stat().st_size
    if actual_bytes != reference["bytes"]:
        raise AssemblyError(
            f"{label} byte count mismatch: "
            f"expected {reference['bytes']}, got {actual_bytes}"
        )
    if not allow_empty and actual_bytes == 0:
        raise AssemblyError(f"{label} external file is unexpectedly empty")
    actual_sha256 = sha256_bytes(resolved.read_bytes())
    if actual_sha256 != reference["sha256"]:
        raise AssemblyError(
            f"{label} SHA-256 mismatch: "
            f"expected {reference['sha256']}, got {actual_sha256}"
        )
    return resolved


def validate_r2_upstream_evidence(
    evidence: dict[str, Any],
    projection_outputs: dict[str, tuple[EvidenceOutput, ...]],
) -> None:
    upstream_references = evidence["upstream_evidence_files"]
    reproducibility = evidence["reproducibility"]
    declared_roots = tuple(
        Path(path).resolve()
        for path in reproducibility["independent_build_roots"]
    )
    if (
        len(upstream_references) != 2
        or len(declared_roots) != 2
        or len(set(declared_roots)) != 2
        or any(
            left.is_relative_to(right) or right.is_relative_to(left)
            for left, right in ((declared_roots[0], declared_roots[1]),)
        )
        or reproducibility
        != {
            "byte_identical": True,
            "independent_build_roots": reproducibility[
                "independent_build_roots"
            ],
            "method": "msvc-brepro-sha256",
        }
        or evidence["output_boundary"]
        != {
            "child_root_rejected": True,
            "fixed_root": "D:/GamePrimitivesFormalOutputs",
        }
        or evidence["process_tree_cleanup"]
        != {
            "failure_descendant_zero": True,
            "supervision": "windows-job-object-kill-on-close",
            "timeout_descendant_zero": True,
        }
    ):
        raise AssemblyError(
            "CA-R2 reproducibility or execution-boundary claim is incomplete"
        )

    upstream_paths = tuple(
        verify_external_file(
            reference,
            label=f"CA-R2 upstream build evidence {index}",
        )
        for index, reference in enumerate(upstream_references)
    )
    if any(
        path.parent.resolve() != root
        for path, root in zip(upstream_paths, declared_roots, strict=True)
    ):
        raise AssemblyError(
            "CA-R2 upstream evidence is outside its independent build root"
        )

    upstream_keys = {
        "config.baseline": "baseline_executable",
        "config.variant": "variant_executable",
    }
    projected: dict[str, EvidenceOutput] = {}
    for configuration_id in upstream_keys:
        outputs = projection_outputs[configuration_id]
        if len(outputs) != 1:
            raise AssemblyError(
                f"CA-R2 {configuration_id} must bind exactly one output"
            )
        projected[configuration_id] = outputs[0]

    expected_self_tests = {
        "baseline": "passed",
        "variant": "passed",
        "comparator_fictional": "passed",
        "failure_descendant_cleanup": "passed",
        "guarded_formal_refusal": "passed",
        "output_child_root_rejected": "passed",
        "timeout_descendant_cleanup": "passed",
    }
    for replay_index, (upstream_path, replay_root) in enumerate(
        zip(upstream_paths, declared_roots, strict=True)
    ):
        upstream, _ = read_json(upstream_path)
        if (
            upstream.get("artifact_type")
            != "q3_r2_formal_fixture_build_evidence"
            or upstream.get("run_id") != RUN_ID
            or upstream.get("case_id") != "CA-R2"
            or upstream.get("source", {}).get("commit_sha")
            != evidence["source"]["commit_sha"]
            or upstream.get("source", {}).get("clean_before_and_after")
            is not True
            or upstream.get("formal_input_read") is not False
            or upstream.get("formal_input_executed") is not False
            or upstream.get("formal_result_created") is not False
            or upstream.get("self_tests") != expected_self_tests
        ):
            raise AssemblyError(
                "CA-R2 upstream build evidence failed cross-binding"
            )

        for configuration_id, artifact_key in upstream_keys.items():
            label = (
                "baseline"
                if configuration_id == "config.baseline"
                else "variant"
            )
            output = projected[configuration_id]
            upstream_output = upstream.get("artifacts", {}).get(
                artifact_key,
                {},
            )
            replay_claim = upstream.get("reproducibility", {}).get(label, {})
            primary_raw = upstream_output.get("path")
            primary_claim = replay_claim.get("primary_path")
            replica_claim = replay_claim.get("replica_path")
            if not all(
                isinstance(value, str)
                for value in (primary_raw, primary_claim, replica_claim)
            ):
                raise AssemblyError(
                    f"CA-R2 upstream evidence lacks {artifact_key}"
                )
            primary_path = Path(primary_raw).resolve()
            replica_path = Path(replica_claim).resolve()
            if (
                Path(primary_claim).resolve() != primary_path
                or not primary_path.is_relative_to(replay_root)
                or not replica_path.is_relative_to(replay_root)
                or primary_path == replica_path
                or replay_claim.get("algorithm") != "sha256"
                or replay_claim.get("byte_identical") is not True
                or replay_claim.get("sha256") != output.sha256
                or upstream_output.get("sha256") != output.sha256
            ):
                raise AssemblyError(
                    f"CA-R2 {configuration_id} reproducibility binding differs"
                )
            for candidate, kind in (
                (primary_path, "primary"),
                (replica_path, "replica"),
            ):
                if (
                    not candidate.is_file()
                    or sha256_bytes(candidate.read_bytes()) != output.sha256
                ):
                    raise AssemblyError(
                        f"CA-R2 {configuration_id} {kind} output is absent "
                        "or hash-mismatched"
                    )
            if primary_path.read_bytes() != replica_path.read_bytes():
                raise AssemblyError(
                    f"CA-R2 {configuration_id} replay outputs are not byte-identical"
                )
            if (
                replay_index == 0
                and primary_path != Path(output.external_path).resolve()
            ):
                raise AssemblyError(
                    f"CA-R2 structured {configuration_id} output is not the "
                    "selected first replay"
                )


def project_generic_build_evidence(
    evidence: dict[str, Any],
) -> EvidenceProjection:
    case_id = evidence["case_id"]
    formal_execution = evidence["formal_execution"]
    expected_formal_execution = {
        "formal_comparator_executed": False,
        "formal_fixture_executed": False,
        "formal_input_executed": False,
        "formal_result_produced": False,
    }
    if case_id == "CA-R2":
        expected_formal_execution["formal_input_read"] = False
    if (
        evidence["run_id"] != RUN_ID
        or evidence["build_gate_status"] != "passed"
        or formal_execution != expected_formal_execution
    ):
        raise AssemblyError(f"{case_id} structured evidence is not pre-gate clean")
    for index, upstream in enumerate(evidence["upstream_evidence_files"]):
        verify_external_file(
            upstream,
            label=f"{case_id} upstream evidence {index}",
        )

    attempts_by_configuration: dict[str, list[str]] = {
        "config.baseline": [],
        "config.variant": [],
    }
    outputs_by_configuration: dict[str, list[EvidenceOutput]] = {
        "config.baseline": [],
        "config.variant": [],
    }
    seen_attempt_ids: set[str] = set()
    for attempt in evidence["build_attempts"]:
        attempt_id = attempt["build_attempt_id"]
        if attempt_id in seen_attempt_ids:
            raise AssemblyError(
                f"{case_id} repeats build attempt ID {attempt_id}"
            )
        seen_attempt_ids.add(attempt_id)
        outputs: list[EvidenceOutput] = []
        for output_index, item in enumerate(attempt["outputs"]):
            verify_external_file(
                item,
                label=f"{case_id}/{attempt_id} output {output_index}",
            )
            outputs.append(
                EvidenceOutput(
                    bytes=item["bytes"],
                    external_path=item["external_path"],
                    output_id=item["output_id"],
                    sha256=item["sha256"],
                )
            )
        for configuration_id in attempt["configuration_ids"]:
            attempts_by_configuration[configuration_id].append(attempt_id)
            outputs_by_configuration[configuration_id].extend(outputs)

    for configuration_id in ("config.baseline", "config.variant"):
        if not attempts_by_configuration[configuration_id]:
            raise AssemblyError(
                f"{case_id} evidence lacks {configuration_id}"
            )
    projection = EvidenceProjection(
        case_id=case_id,
        configuration_attempt_ids={
            key: tuple(sorted(value))
            for key, value in attempts_by_configuration.items()
        },
        configuration_outputs={
            key: tuple(sorted(value, key=lambda item: item.output_id))
            for key, value in outputs_by_configuration.items()
        },
        source_commit=evidence["source"]["commit_sha"],
    )
    if case_id == "CA-R2":
        validate_r2_upstream_evidence(
            evidence,
            projection.configuration_outputs,
        )
    return projection


def validate_r1_upstream_evidence(
    evidence: dict[str, Any],
    projection_outputs: dict[str, tuple[EvidenceOutput, ...]],
) -> None:
    reproducibility = evidence["reproducibility"]
    if (
        reproducibility["verified"] is not True
        or reproducibility["formal_pdb_files_found"] != 0
    ):
        raise AssemblyError("CA-R1 reproducibility claim is not clean")

    raw_cache_roots = reproducibility["cache_roots"]
    cache_roots = tuple(Path(item).resolve() for item in raw_cache_roots)
    if (
        len(cache_roots) != 2
        or len(set(cache_roots)) != 2
        or any(not path.is_dir() for path in cache_roots)
    ):
        raise AssemblyError(
            "CA-R1 reproducibility requires two distinct existing cache roots"
        )
    upstream_paths = tuple(
        verify_external_file(
            item,
            label=f"CA-R1 reproducibility evidence {index}",
        )
        for index, item in enumerate(reproducibility["evidence_files"])
    )
    if (
        len(upstream_paths) != 2
        or len(set(upstream_paths)) != 2
        or any(
            path.parent != cache_root
            for path, cache_root in zip(upstream_paths, cache_roots, strict=True)
        )
    ):
        raise AssemblyError(
            "CA-R1 evidence files are not rooted in two independent caches"
        )
    if evidence["external_evidence"] not in reproducibility["evidence_files"]:
        raise AssemblyError(
            "CA-R1 primary external evidence is outside the reproducibility set"
        )

    output_fields = {
        "config.baseline": "baseline_formal_assembly_sha256",
        "config.variant": "variant_formal_assembly_sha256",
    }
    reproducible_hashes = {
        "config.baseline": reproducibility["formal_outputs"][
            "baseline_sha256"
        ],
        "config.variant": reproducibility["formal_outputs"]["variant_sha256"],
    }
    for configuration_id, expected_sha256 in reproducible_hashes.items():
        outputs = projection_outputs[configuration_id]
        if len(outputs) != 1 or outputs[0].sha256 != expected_sha256:
            raise AssemblyError(
                f"CA-R1 {configuration_id} output differs from "
                "the reproducibility binding"
            )

    expected_formal = {
        "authorization_created": False,
        "comparator_executed": False,
        "formal_environment_present": False,
        "formal_input_executed": False,
        "formal_input_path_accepted": False,
        "formal_input_read": False,
        "formal_result_created": False,
        "formal_runner_executed": False,
        "permit_created": False,
        "predictions_created": False,
    }
    for cache_root, upstream_path in zip(
        cache_roots,
        upstream_paths,
        strict=True,
    ):
        upstream, _ = read_json(upstream_path)
        source = upstream.get("source", {})
        formal = upstream.get("formal_execution", {})
        if (
            upstream.get("artifact_type")
            != "continuous_action_r1_standalone_build_evidence"
            or upstream.get("run_id") != RUN_ID
            or upstream.get("case_id") != "CA-R1"
            or upstream.get("build_gate_status") != "passed"
            or source.get("commit") != evidence["source_identity"]["commit_sha"]
            or source.get("input_checkout_clean") is not True
            or source.get("baseline_checkout_clean") is not True
            or formal != expected_formal
        ):
            raise AssemblyError(
                "CA-R1 upstream build evidence failed cross-binding"
            )

        builds = {
            item.get("configuration_id"): item
            for item in upstream.get("builds", [])
            if isinstance(item, dict)
        }
        fixture = upstream.get("fixture", {})
        for configuration_id, output_field in output_fields.items():
            build = builds.get(configuration_id, {})
            expected_sha256 = reproducible_hashes[configuration_id]
            if (
                build.get("restore_exit_code") != 0
                or build.get("build_exit_code") != 0
                or build.get("formal_restore_exit_code") != 0
                or build.get("formal_build_exit_code") != 0
                or build.get("warning_count") != 0
                or fixture.get(output_field) != expected_sha256
            ):
                raise AssemblyError(
                    f"CA-R1 upstream {configuration_id} build is not clean"
                )

            cache_suffix = (
                "baseline"
                if configuration_id == "config.baseline"
                else "variant"
            )
            formal_directory = (
                cache_root
                / f"artifacts-{cache_suffix}"
                / "bin"
                / "FootsiesR1Formal"
                / "release"
            )
            formal_dll = formal_directory / "FootsiesR1Formal.dll"
            if (
                not formal_dll.is_file()
                or sha256_bytes(formal_dll.read_bytes()) != expected_sha256
            ):
                raise AssemblyError(
                    f"CA-R1 {configuration_id} reproducible DLL is absent "
                    "or hash-mismatched"
                )
            if any(formal_directory.glob("*.pdb")):
                raise AssemblyError(
                    f"CA-R1 {configuration_id} reproducible output has a PDB"
                )


def project_r1_build_evidence(
    repo_root: Path,
    evidence: dict[str, Any],
) -> EvidenceProjection:
    case_id = "CA-R1"
    formal = evidence["formal_execution"]
    if (
        evidence["run_id"] != RUN_ID
        or evidence["case_id"] != case_id
        or evidence["build_gate_status"] != "passed"
        or evidence["source_identity"]["verified_clean"] is not True
        or formal
        != {
            "authorization_created": False,
            "comparator_executed": False,
            "formal_environment_present": False,
            "formal_input_executed": False,
            "formal_input_path_accepted": False,
            "formal_input_read": False,
            "formal_result_created": False,
            "formal_runner_executed": False,
            "permit_created": False,
            "predictions_created": False,
        }
    ):
        raise AssemblyError("CA-R1 structured evidence is not pre-gate clean")

    target = EXECUTION_TARGET_PATHS[case_id]
    expected_surface = {
        target["comparator"],
        target["formal_input"],
        target["formal_runner"],
        target["raw_trace_schema"],
        target["test_body"],
        *(
            path
            for key, path in target["support_artifacts"].items()
            if key != "build_evidence"
        ),
    }
    formal_surface = evidence["fixture_surfaces"]["formal_execution"]
    observed_surface = {item["path"] for item in formal_surface}
    if (
        len(observed_surface) != len(formal_surface)
        or observed_surface != expected_surface
    ):
        raise AssemblyError(
            "CA-R1 evidence execution surface differs from target contract"
        )
    for reference in formal_surface:
        path = repo_path(repo_root, reference["path"])
        actual_sha256 = sha256_bytes(path.read_bytes())
        if actual_sha256 != reference["sha256"]:
            raise AssemblyError(
                f"CA-R1 evidence surface hash mismatch: {reference['path']}"
            )

    verify_external_file(
        evidence["toolchain"]["dotnet_executable"],
        label="CA-R1 toolchain executable",
    )
    attempts: dict[str, tuple[str, ...]] = {}
    outputs: dict[str, tuple[EvidenceOutput, ...]] = {}
    for configuration in evidence["configurations"]:
        configuration_id = configuration["configuration_id"]
        projected_outputs: list[EvidenceOutput] = []
        for index, item in enumerate(configuration["outputs"]):
            verify_external_file(
                item,
                label=f"CA-R1/{configuration_id} output {index}",
            )
            if item["output_kind"] == "formal_execution":
                projected_outputs.append(
                    EvidenceOutput(
                        bytes=item["bytes"],
                        external_path=item["external_path"],
                        output_id=item["output_id"],
                        sha256=item["sha256"],
                    )
                )
        attempts[configuration_id] = (
            configuration["build_attempt_id"],
        )
        outputs[configuration_id] = tuple(projected_outputs)

    projection = EvidenceProjection(
        case_id=case_id,
        configuration_attempt_ids=attempts,
        configuration_outputs=outputs,
        source_commit=evidence["source_identity"]["commit_sha"],
    )
    validate_r1_upstream_evidence(evidence, projection.configuration_outputs)
    return projection


def project_r3_build_evidence(evidence: dict[str, Any]) -> EvidenceProjection:
    case_id = "CA-R3"
    formal = evidence["formal_execution"]
    results = evidence["results"]
    if (
        evidence["run_id"] != RUN_ID
        or evidence["case_id"] != case_id
        or evidence["build_gate_status"] != "passed"
        or formal["evidence_scope"]
        != "recorded_build_list_and_guard_probe_processes_only"
        or formal["formal_input_read_during_evidence_capture"] is not False
        or formal["formal_input_executed"] is not False
        or formal["formal_result_created"] is not False
        or formal["test_body_execution_count"] != 0
        or formal["comparator_executed"] is not False
        or results["build_error_count"] != 0
        or results["build_warning_count"] != 0
        or results["formal_test_discovered"] is not True
    ):
        raise AssemblyError("CA-R3 structured evidence is not pre-gate clean")
    build_records = [
        item
        for item in evidence["process_records"]
        if item["step"]
        in (
            "build-observation-fixture",
            "build-observation-fixture-replay-b",
        )
    ]
    if (
        {item["step"] for item in build_records}
        != {
            "build-observation-fixture",
            "build-observation-fixture-replay-b",
        }
        or any(
            item["exit_code"] != 0 or item["alive_after"] != 0
            for item in build_records
        )
    ):
        raise AssemblyError(
            "CA-R3 independent build process records are not successful"
        )

    verified_files: dict[str, Path] = {}
    for index, item in enumerate(evidence["evidence_files"]):
        verified_files[item["external_path"]] = verify_external_file(
            item,
            label=f"CA-R3 evidence file {index}",
            allow_empty=True,
        )
    summary_candidates = [
        path
        for raw_path, path in verified_files.items()
        if raw_path.endswith("/probe-summary.json")
    ]
    build_log_candidates = [
        path
        for raw_path, path in verified_files.items()
        if raw_path.endswith("/logs/build-msbuild.log")
    ]
    if len(summary_candidates) != 1 or len(build_log_candidates) != 1:
        raise AssemblyError("CA-R3 evidence lacks one probe summary/build log")
    summary, _ = read_json(summary_candidates[0])
    if (
        summary.get("source_commit") != evidence["source_commit"]
        or summary.get("build_exit_code") != 0
        or summary.get("build_warning_count") != 0
        or summary.get("formal_test_discovered") is not True
        or summary.get("formal_test_executed") is not False
        or summary.get("formal_input_read") is not False
        or summary.get("formal_input_executed") is not False
        or summary.get("formal_result_created") is not False
    ):
        raise AssemblyError("CA-R3 probe summary differs from repository evidence")

    reproducibility = evidence["reproducibility"]
    summary_reproducibility = summary.get("reproducibility")
    if (
        not isinstance(summary_reproducibility, dict)
        or reproducibility["replay_count"] != 2
        or reproducibility["independent_cache_roots"] is not True
        or reproducibility["byte_identical"] is not True
        or [item["replay_id"] for item in reproducibility["replays"]]
        != ["replay-a", "replay-b"]
    ):
        raise AssemblyError(
            "CA-R3 reproducibility projection differs from the probe summary"
        )
    for field in (
        "independent_cache_roots",
        "replay_count",
        "byte_identical",
        "formal_assembly_sha256",
        "formal_assembly_bytes",
        "execution_tree_manifest_sha256",
        "execution_replay_id",
    ):
        if reproducibility[field] != summary_reproducibility.get(field):
            raise AssemblyError(
                "CA-R3 reproducibility summary field differs: "
                f"{field}"
            )
    summary_replays = summary_reproducibility.get("replays")
    if not isinstance(summary_replays, list) or len(summary_replays) != 2:
        raise AssemblyError("CA-R3 probe summary lacks two build replays")
    for projected, recorded in zip(
        reproducibility["replays"],
        summary_replays,
        strict=True,
    ):
        expected_projection = {
            key: copy.deepcopy(recorded[key])
            for key in (
                "replay_id",
                "cache_root",
                "assembly",
                "execution_tree",
                "removed_discovery_ephemera",
            )
        }
        if projected != expected_projection:
            raise AssemblyError(
                "CA-R3 replay projection differs from the probe summary: "
                f"{projected['replay_id']}"
            )
        if (
            recorded.get("locked_restore_exit_code") != 0
            or recorded.get("build_exit_code") != 0
            or recorded.get("build_warning_count") != 0
            or recorded.get("test_discovery_exit_code") != 0
            or recorded.get("formal_test_discovered") is not True
            or recorded.get("formal_test_executed") is not False
            or recorded.get("formal_input_read") is not False
            or recorded.get("formal_input_executed") is not False
            or recorded.get("formal_result_created") is not False
        ):
            raise AssemblyError(
                "CA-R3 replay is not a clean build/list-only probe: "
                f"{projected['replay_id']}"
            )

    replay_outputs: list[Path] = []
    for replay in reproducibility["replays"]:
        output_path = Path(replay["assembly"]["external_path"]).resolve()
        if not output_path.is_file():
            raise AssemblyError(f"CA-R3 build output is absent: {output_path}")
        if (
            output_path.as_posix() not in verified_files
            or output_path.stat().st_size != replay["assembly"]["bytes"]
            or sha256_bytes(output_path.read_bytes())
            != replay["assembly"]["sha256"]
        ):
            raise AssemblyError(
                f"CA-R3 replay output is not bound by evidence: {output_path}"
            )
        replay_outputs.append(output_path)
    if (
        reproducibility["formal_assembly_sha256"]
        != reproducibility["replays"][0]["assembly"]["sha256"]
        or reproducibility["formal_assembly_sha256"]
        != reproducibility["replays"][1]["assembly"]["sha256"]
        or reproducibility["formal_assembly_bytes"]
        != reproducibility["replays"][0]["assembly"]["bytes"]
        or reproducibility["formal_assembly_bytes"]
        != reproducibility["replays"][1]["assembly"]["bytes"]
    ):
        raise AssemblyError("CA-R3 replay assemblies are not byte-identical")

    output_path = replay_outputs[0]
    output_sha256 = reproducibility["formal_assembly_sha256"]
    build_log = build_log_candidates[0].read_text(
        encoding="utf-8",
        errors="strict",
    )
    if str(output_path) not in build_log:
        raise AssemblyError("CA-R3 build log does not identify the bound output")
    identity = BUILD_READINESS_IDENTITIES[case_id]
    output = EvidenceOutput(
        bytes=output_path.stat().st_size,
        external_path=output_path.as_posix(),
        output_id=identity["config.baseline"]["output_ids"][0],
        sha256=output_sha256,
    )
    attempt_ids = identity["config.baseline"]["build_attempt_ids"]
    return EvidenceProjection(
        case_id=case_id,
        configuration_attempt_ids={
            "config.baseline": attempt_ids,
            "config.variant": attempt_ids,
        },
        configuration_outputs={
            "config.baseline": (output,),
            "config.variant": (output,),
        },
        source_commit=evidence["source_commit"],
    )


def load_evidence_projection(
    repo_root: Path,
    reference: dict[str, str],
    *,
    expected_case: str,
    registry: Registry,
    schemas: dict[str, dict[str, Any]],
) -> EvidenceProjection:
    evidence_path = verify_reference(repo_root, reference)
    evidence, raw = read_json(evidence_path)
    if raw != canonical_bytes(evidence):
        raise AssemblyError(
            f"structured build evidence is not canonical: {reference['path']}"
        )
    evidence_schema = schema_for_document(
        evidence,
        schemas,
        label=reference["path"],
    )
    validate_document(
        evidence,
        evidence_schema,
        registry,
        label=reference["path"],
    )
    artifact_type = evidence.get("artifact_type")
    if artifact_type == "fixture_build_evidence":
        projection = project_generic_build_evidence(evidence)
    elif artifact_type == "continuous_action_r1_standalone_build_evidence":
        projection = project_r1_build_evidence(repo_root, evidence)
    elif artifact_type == "continuous_action_r3_build_list_evidence":
        projection = project_r3_build_evidence(evidence)
    else:
        raise AssemblyError(
            f"unsupported structured build evidence type: {artifact_type}"
        )
    if projection.case_id != expected_case:
        raise AssemblyError(
            f"structured evidence case mismatch: "
            f"expected {expected_case}, got {projection.case_id}"
        )
    return projection


def ref_key(reference: dict[str, str]) -> tuple[str, str, str]:
    return (
        reference["path"],
        reference["artifact_id"],
        reference["sha256"],
    )


def unique_references(
    fragments: Iterable[dict[str, Any]],
    field_name: str,
) -> list[dict[str, str]]:
    references: dict[tuple[str, str, str], dict[str, str]] = {}
    for fragment in fragments:
        for reference in fragment[field_name]:
            references[ref_key(reference)] = copy.deepcopy(reference)
    return [references[key] for key in sorted(references)]


def latest_timestamp(fragments: Iterable[dict[str, Any]]) -> str:
    candidates: list[tuple[datetime, str]] = []
    for fragment in fragments:
        value = fragment["prepared_at"]
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            instant = datetime.fromisoformat(normalized)
        except ValueError as error:
            raise AssemblyError(f"invalid prepared_at timestamp: {value}") from error
        if instant.tzinfo is None:
            raise AssemblyError(f"prepared_at must include a timezone: {value}")
        candidates.append((instant, value))
    return max(candidates, key=lambda item: item[0])[1]


def locked_fixture_keys(case_lock: dict[str, Any]) -> set[tuple[str, str]]:
    references = list(case_lock["fixture_artifacts"])
    for field_name in (
        "compatibility_patch_set",
        "observation_patch_set",
        "variant_patch_set",
    ):
        patch_set = case_lock[field_name]
        references.extend(patch_set["artifacts"])
        references.extend(patch_set["configuration_artifacts"])
    return {(item["path"], item["sha256"]) for item in references}


def references_at(case_lock: dict[str, Any], dotted_field: str) -> list[dict[str, str]]:
    value: Any = case_lock
    for part in dotted_field.split("."):
        if not isinstance(value, dict) or part not in value:
            raise AssemblyError(
                f"{case_lock.get('case_id')} lock lacks {dotted_field}"
            )
        value = value[part]
    if not isinstance(value, list):
        raise AssemblyError(
            f"{case_lock.get('case_id')} lock field {dotted_field} is not a list"
        )
    return value


def validate_lock_execution_surface(
    case_lock: dict[str, Any],
    *,
    expected_case: str,
) -> None:
    if case_lock["case_id"] != expected_case:
        raise AssemblyError(
            f"fixture lock case mismatch: expected {expected_case}"
        )
    exact_paths = expected_lock_paths(
        expected_case,
        LOCK_EXACT_ROLE_PLACEMENTS[expected_case],
    )
    for field, expected in exact_paths.items():
        observed = tuple(
            sorted(reference["path"] for reference in references_at(case_lock, field))
        )
        expected_sorted = tuple(sorted(expected))
        if len(observed) != len(set(observed)):
            raise AssemblyError(
                f"{expected_case} lock repeats an artifact in {field}"
            )
        if observed != expected_sorted:
            raise AssemblyError(
                f"{expected_case} lock execution surface mismatch in {field}: "
                f"expected {expected_sorted}, got {observed}"
            )

    required_paths = expected_lock_paths(
        expected_case,
        LOCK_REQUIRED_ROLE_PLACEMENTS[expected_case],
    )
    for field, required in required_paths.items():
        observed = {
            reference["path"] for reference in references_at(case_lock, field)
        }
        missing = sorted(set(required) - observed)
        if missing:
            raise AssemblyError(
                f"{expected_case} lock execution surface is incomplete in "
                f"{field}; missing {missing}"
            )


def validate_build_evidence_bindings(
    fragment: dict[str, Any],
    projection: EvidenceProjection,
    *,
    expected_case: str,
) -> None:
    readiness = fragment["build_readiness"]
    if readiness["source_commit"] != projection.source_commit:
        raise AssemblyError(
            f"{expected_case} readiness source commit differs from build evidence"
        )
    structured = fragment["structured_build_evidence"]
    structured_key = (structured["path"], structured["sha256"])
    root_evidence = {
        (item["path"], item["sha256"])
        for item in fragment["build_readiness_evidence_artifacts"]
    }
    if structured_key not in root_evidence:
        raise AssemblyError(
            f"{expected_case} structured evidence is absent from readiness rollup"
        )

    configurations = {
        item["configuration_id"]: item
        for item in readiness["configurations"]
    }
    identity_contract = BUILD_READINESS_IDENTITIES[expected_case]
    for configuration_id in ("config.baseline", "config.variant"):
        configuration = configurations[configuration_id]
        evidence_refs = {
            (item["path"], item["sha256"])
            for item in configuration["build_evidence_artifacts"]
        }
        if structured_key not in evidence_refs:
            raise AssemblyError(
                f"{expected_case}/{configuration_id} does not cite its "
                "structured build evidence"
            )
        observed_attempt_ids = tuple(sorted(configuration["build_attempt_ids"]))
        contract_attempt_ids = tuple(
            sorted(identity_contract[configuration_id]["build_attempt_ids"])
        )
        evidence_attempt_ids = tuple(
            sorted(projection.configuration_attempt_ids[configuration_id])
        )
        if (
            observed_attempt_ids != contract_attempt_ids
            or observed_attempt_ids != evidence_attempt_ids
        ):
            raise AssemblyError(
                f"{expected_case}/{configuration_id} build attempt IDs "
                "differ from evidence/contract"
            )

        observed_outputs = {
            (item["output_id"], item["sha256"])
            for item in configuration["built_outputs"]
        }
        evidence_outputs = {
            (item.output_id, item.sha256)
            for item in projection.configuration_outputs[configuration_id]
        }
        observed_output_ids = tuple(sorted(item[0] for item in observed_outputs))
        contract_output_ids = tuple(
            sorted(identity_contract[configuration_id]["output_ids"])
        )
        if (
            observed_output_ids != contract_output_ids
            or observed_outputs != evidence_outputs
        ):
            raise AssemblyError(
                f"{expected_case}/{configuration_id} outputs differ from "
                "evidence/contract"
            )


def validate_fragment_cross_bindings(
    fragment: dict[str, Any],
    case_lock: dict[str, Any],
    *,
    expected_case: str,
) -> None:
    case_id = fragment["case_id"]
    readiness = fragment["build_readiness"]
    if case_id != expected_case:
        raise AssemblyError(
            f"fragment path for {expected_case} contains case_id {case_id}"
        )
    if case_lock["case_id"] != case_id or readiness["case_id"] != case_id:
        raise AssemblyError(f"nested case_id mismatch in {case_id} fragment")
    if readiness["source_commit"] != case_lock["source_identity"]["commit_sha"]:
        raise AssemblyError(f"source commit mismatch in {case_id} fragment")
    if (
        fragment["formal_input_executed"] is not False
        or fragment["formal_result_produced"] is not False
        or case_lock["formal_input_executed"] is not False
    ):
        raise AssemblyError(f"fragment records formal execution for {case_id}")

    evidence_keys = {
        (item["path"], item["sha256"])
        for item in fragment["build_readiness_evidence_artifacts"]
    }
    locked_keys = locked_fixture_keys(case_lock)
    configurations = {
        configuration["configuration_id"]: configuration
        for configuration in readiness["configurations"]
    }
    for configuration_id in ("config.baseline", "config.variant"):
        configuration = configurations.get(configuration_id)
        if configuration is None:
            raise AssemblyError(
                f"{case_id} lacks {configuration_id} build readiness"
            )
        used_evidence = {
            (item["path"], item["sha256"])
            for item in configuration["build_evidence_artifacts"]
        }
        if not used_evidence.issubset(evidence_keys):
            raise AssemblyError(
                f"{case_id}/{configuration_id} evidence is absent from fragment rollup"
            )
        used_fixtures = {
            (item["path"], item["sha256"])
            for item in configuration["fixture_artifacts"]
        }
        if not used_fixtures.issubset(locked_keys):
            raise AssemblyError(
                f"{case_id}/{configuration_id} uses an unlocked fixture artifact"
            )

    baseline = configurations["config.baseline"]
    variant = configurations["config.variant"]
    variant_realization = case_lock["variant_patch_set"]["realization"]
    if variant_realization == "configuration_only":
        for configuration in (baseline, variant):
            if configuration["realization"] != "shared_binary_configuration":
                raise AssemblyError(
                    f"{case_id} configuration-only variant is not a shared binary"
                )
        baseline_outputs = {
            (item["output_id"], item["sha256"])
            for item in baseline["built_outputs"]
        }
        variant_outputs = {
            (item["output_id"], item["sha256"])
            for item in variant["built_outputs"]
        }
        if baseline_outputs != variant_outputs:
            raise AssemblyError(
                f"{case_id} shared configurations bind different build outputs"
            )
    elif variant_realization == "patch":
        for configuration in (baseline, variant):
            if configuration["realization"] != "separate_binary":
                raise AssemblyError(
                    f"{case_id} patched variant is not a separate binary"
                )
    else:
        raise AssemblyError(
            f"{case_id} variant must use patch or configuration_only"
        )

    final_ref_paths = {
        item["path"] for item in case_lock["preparation_probe_artifacts"]
    }
    if READINESS_PATH in final_ref_paths:
        raise AssemblyError(
            f"{case_id} fragment must not precompute the final readiness hash"
        )


def load_case_lock_source(
    repo_root: Path,
    fragment: dict[str, Any],
    *,
    registry: Registry,
) -> dict[str, Any]:
    reference = fragment["fixture_lock_case_source"]
    source_path = verify_reference(repo_root, reference)
    source, source_raw = read_json(source_path)
    if source_raw != canonical_bytes(source):
        raise AssemblyError(
            "fixture-lock case source is not canonical JSON: "
            f"{reference['path']}"
        )
    pointer = fragment["fixture_lock_case_json_pointer"]
    if pointer == "":
        case_lock = source
    elif pointer == "/case_lock":
        case_lock = source.get("case_lock")
    else:
        raise AssemblyError(f"unsupported case-lock JSON pointer: {pointer}")
    if not isinstance(case_lock, dict):
        raise AssemblyError(
            f"case-lock JSON pointer does not select an object: {pointer}"
        )
    validate_document(
        case_lock,
        {"$ref": FIXTURE_LOCK_SCHEMA_ID + "#/$defs/caseLock"},
        registry,
        label=f"{reference['path']}#{pointer}",
    )
    for nested_reference in iter_references(case_lock):
        verify_reference(repo_root, nested_reference)
    return case_lock


def load_fragment(
    repo_root: Path,
    *,
    expected_case: str,
    registry: Registry,
    schemas: dict[str, dict[str, Any]],
) -> LoadedFragment:
    relative = FRAGMENT_PATHS[expected_case]
    path = repo_path(repo_root, relative)
    fragment, raw = read_json(path)
    if raw != canonical_bytes(fragment):
        raise AssemblyError(f"fragment is not canonical JSON: {relative}")
    validate_document(
        fragment,
        schemas[FRAGMENT_SCHEMA_PATH],
        registry,
        label=relative,
    )
    for reference in iter_references(fragment):
        verify_reference(repo_root, reference)
    case_lock = load_case_lock_source(
        repo_root,
        fragment,
        registry=registry,
    )
    validate_lock_execution_surface(
        case_lock,
        expected_case=expected_case,
    )
    projection = load_evidence_projection(
        repo_root,
        fragment["structured_build_evidence"],
        expected_case=expected_case,
        registry=registry,
        schemas=schemas,
    )
    validate_build_evidence_bindings(
        fragment,
        projection,
        expected_case=expected_case,
    )
    validate_fragment_cross_bindings(
        fragment,
        case_lock,
        expected_case=expected_case,
    )
    expected_supersedes = artifact_reference(
        repo_root,
        SUPERSEDES_PATH,
        artifact_id=fragment["supersedes_probe"]["artifact_id"],
    )
    if fragment["supersedes_probe"] != expected_supersedes:
        raise AssemblyError(
            f"{expected_case} does not bind the current toolchain probe"
        )
    return LoadedFragment(
        document=fragment,
        fixture_lock_case=case_lock,
    )


def load_all_fragments(
    repo_root: Path,
) -> tuple[
    list[LoadedFragment],
    Registry,
    dict[str, dict[str, Any]],
]:
    missing = [
        relative
        for relative in FRAGMENT_PATHS.values()
        if not repo_path(repo_root, relative, must_exist=False).is_file()
    ]
    if missing:
        raise AssemblyError(
            "all three case fragments are required before final assembly; "
            f"missing: {', '.join(missing)}"
        )
    registry, schemas = load_schema_registry(repo_root)
    fragments = [
        load_fragment(
            repo_root,
            expected_case=case_id,
            registry=registry,
            schemas=schemas,
        )
        for case_id in CASES
    ]
    supersedes = {
        ref_key(fragment.document["supersedes_probe"])
        for fragment in fragments
    }
    if len(supersedes) != 1:
        raise AssemblyError("case fragments disagree on the superseded probe")
    return fragments, registry, schemas


def build_documents(
    fragments: list[LoadedFragment],
) -> tuple[dict[str, Any], dict[str, Any]]:
    ordered = sorted(
        fragments,
        key=lambda item: CASES.index(item.document["case_id"]),
    )
    documents = [fragment.document for fragment in ordered]
    assessed_at = latest_timestamp(documents)
    supersedes = copy.deepcopy(documents[0]["supersedes_probe"])
    readiness = {
        "$schema": READINESS_SCHEMA_ID,
        "artifact_type": "formal_build_readiness",
        "artifact_version": "0.1.0",
        "assessed_at": assessed_at,
        "cases": [
            copy.deepcopy(fragment["build_readiness"])
            for fragment in documents
        ],
        "evidence_artifacts": unique_references(
            documents,
            "build_readiness_evidence_artifacts",
        ),
        "formal_input_executed": False,
        "formal_result_produced": False,
        "overall_status": "passed",
        "readiness_scope": "build_only",
        "run_id": RUN_ID,
        "supersedes_probe": supersedes,
    }
    readiness_raw = canonical_bytes(readiness)
    readiness_reference = {
        "artifact_id": READINESS_ARTIFACT_ID,
        "path": READINESS_PATH,
        "sha256": sha256_bytes(readiness_raw),
    }

    cases: list[dict[str, Any]] = []
    for fragment in ordered:
        case_lock = copy.deepcopy(fragment.fixture_lock_case)
        case_lock["preparation_probe_artifacts"].append(
            copy.deepcopy(readiness_reference)
        )
        cases.append(case_lock)
    fixture_lock = {
        "$schema": FIXTURE_LOCK_SCHEMA_ID,
        "artifact_type": "fixture_lock",
        "artifact_version": "0.1.0",
        "cases": cases,
        "created_at": assessed_at,
        "fixture_state": "locked",
        "formal_execution_authorized": False,
        "formal_input_executed": False,
        "negative_control_artifacts": unique_references(
            documents,
            "negative_control_artifacts",
        ),
        "run_id": RUN_ID,
    }
    return readiness, fixture_lock


def validate_documents(
    readiness: dict[str, Any],
    fixture_lock: dict[str, Any],
    *,
    registry: Registry,
    schemas: dict[str, dict[str, Any]],
) -> None:
    validate_document(
        readiness,
        schemas[READINESS_SCHEMA_PATH],
        registry,
        label=READINESS_PATH,
    )
    validate_document(
        fixture_lock,
        schemas[FIXTURE_LOCK_SCHEMA_PATH],
        registry,
        label=FIXTURE_LOCK_PATH,
    )


def write_pair_new(
    repo_root: Path,
    readiness: dict[str, Any],
    fixture_lock: dict[str, Any],
) -> None:
    readiness_path = repo_path(repo_root, READINESS_PATH, must_exist=False)
    fixture_lock_path = repo_path(repo_root, FIXTURE_LOCK_PATH, must_exist=False)
    if readiness_path.exists() or fixture_lock_path.exists():
        existing = [
            relative_path(repo_root, path)
            for path in (readiness_path, fixture_lock_path)
            if path.exists()
        ]
        raise AssemblyError(
            "refusing to overwrite final fixture artifacts: "
            + ", ".join(existing)
        )
    if (
        not readiness_path.parent.is_dir()
        or readiness_path.parent != fixture_lock_path.parent
    ):
        raise AssemblyError("final fixture output directory is not prepared")

    temp_paths: list[Path] = []
    created_paths: list[Path] = []
    try:
        for destination, value in (
            (readiness_path, readiness),
            (fixture_lock_path, fixture_lock),
        ):
            descriptor, temp_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
            )
            os.close(descriptor)
            temp_path = Path(temp_name)
            temp_paths.append(temp_path)
            temp_path.write_bytes(canonical_bytes(value))
        for temp_path, destination in zip(
            temp_paths,
            (readiness_path, fixture_lock_path),
            strict=True,
        ):
            os.link(temp_path, destination)
            created_paths.append(destination)
    except Exception:
        for destination in created_paths:
            destination.unlink(missing_ok=True)
        raise
    finally:
        for temp_path in temp_paths:
            temp_path.unlink(missing_ok=True)


def materialize(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_paths = (
        repo_path(repo_root, READINESS_PATH, must_exist=False),
        repo_path(repo_root, FIXTURE_LOCK_PATH, must_exist=False),
    )
    if any(path.exists() for path in output_paths):
        raise AssemblyError("final fixture artifacts already exist")
    fragments, registry, schemas = load_all_fragments(repo_root)
    readiness, fixture_lock = build_documents(fragments)
    validate_documents(
        readiness,
        fixture_lock,
        registry=registry,
        schemas=schemas,
    )
    write_pair_new(repo_root, readiness, fixture_lock)
    return {
        "fixture_lock": {
            "path": FIXTURE_LOCK_PATH,
            "sha256": sha256_bytes(canonical_bytes(fixture_lock)),
        },
        "formal_build_readiness": {
            "path": READINESS_PATH,
            "sha256": sha256_bytes(canonical_bytes(readiness)),
        },
        "formal_input_executed": False,
        "formal_result_produced": False,
        "status": "materialized",
    }


def verify(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    fragments, registry, schemas = load_all_fragments(repo_root)
    expected_readiness, expected_lock = build_documents(fragments)
    validate_documents(
        expected_readiness,
        expected_lock,
        registry=registry,
        schemas=schemas,
    )
    observed: list[tuple[str, dict[str, Any]]] = []
    for relative in (READINESS_PATH, FIXTURE_LOCK_PATH):
        path = repo_path(repo_root, relative)
        document, raw = read_json(path)
        if raw != canonical_bytes(document):
            raise AssemblyError(f"final artifact is not canonical JSON: {relative}")
        observed.append((relative, document))
    readiness = observed[0][1]
    fixture_lock = observed[1][1]
    validate_documents(
        readiness,
        fixture_lock,
        registry=registry,
        schemas=schemas,
    )
    if readiness != expected_readiness:
        raise AssemblyError("formal build readiness differs from its three fragments")
    if fixture_lock != expected_lock:
        raise AssemblyError("fixture lock differs from its three fragments")
    return {
        "fixture_lock_sha256": sha256_bytes(canonical_bytes(fixture_lock)),
        "formal_build_readiness_sha256": sha256_bytes(
            canonical_bytes(readiness)
        ),
        "formal_input_executed": False,
        "formal_result_produced": False,
        "status": "verified",
    }


def verify_fragment(repo_root: Path, fragment_path: str) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    fragment_bytes = repo_path(repo_root, fragment_path).read_bytes()
    expected_case = next(
        (
            case_id
            for case_id, expected_path in FRAGMENT_PATHS.items()
            if expected_path == fragment_path
        ),
        None,
    )
    if expected_case is None:
        raise AssemblyError(
            "fragment path is not one of the three fixed production paths"
        )
    registry, schemas = load_schema_registry(repo_root)
    load_fragment(
        repo_root,
        expected_case=expected_case,
        registry=registry,
        schemas=schemas,
    )
    return {
        "case_id": expected_case,
        "formal_input_executed": False,
        "formal_result_produced": False,
        "sha256": sha256_bytes(fragment_bytes),
        "status": "verified",
    }


def write_synthetic_file(
    root: Path,
    relative: str,
    content: bytes,
) -> dict[str, str]:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "artifact_id": "placeholder",
        "path": relative,
        "sha256": sha256_bytes(content),
    }


def synthetic_reference(
    root: Path,
    relative: str,
    artifact_id: str,
) -> dict[str, str]:
    reference = artifact_reference(root, relative, artifact_id=artifact_id)
    return reference


def synthetic_fragment(
    root: Path,
    case_id: str,
    *,
    prepared_at: str,
) -> dict[str, Any]:
    suffix = case_id.lower().replace("-", "")
    case_dir = f"{RUN}/fixtures/{case_id[-2:].lower()}"
    negative_path = f"{case_dir}/{suffix}-negative-control.log"
    source_path = f"{RUN}/source/{suffix}-source.json"
    source_commit = (
        "dbe4ddb10315479fc00086f08e25d968b4b43c49"
        if case_id == "CA-R2"
        else sha256_bytes(case_id.encode())[:40]
    )
    target = EXECUTION_TARGET_PATHS[case_id]
    roles = {
        "comparator": target["comparator"],
        "formal_input": target["formal_input"],
        "formal_runner": target["formal_runner"],
        "test_body": target["test_body"],
        **{
            f"support.{key}": value
            for key, value in target["support_artifacts"].items()
        },
    }
    evidence_role = LOCK_REQUIRED_ROLE_PLACEMENTS[case_id][
        "preparation_probe_artifacts"
    ][0]
    evidence_path = roles[evidence_role]

    for role, relative in roles.items():
        if role == evidence_role:
            continue
        content = (
            canonical_bytes(
                {
                    "case_id": case_id,
                    "formal_input_executed": False,
                    "role": role,
                }
            )
            if relative.endswith(".json")
            else f"synthetic {case_id} {role}\n".encode()
        )
        write_synthetic_file(root, relative, content)
    write_synthetic_file(root, negative_path, b"synthetic refusal passed\n")
    write_synthetic_file(
        root,
        source_path,
        canonical_bytes({"case_id": case_id, "commit_sha": source_commit}),
    )

    external_root = root.parent / "external-builds" / suffix
    external_root.mkdir(parents=True, exist_ok=True)
    identities = BUILD_READINESS_IDENTITIES[case_id]
    output_records: dict[str, dict[str, Any]] = {}
    for configuration_id in ("config.baseline", "config.variant"):
        for output_id in identities[configuration_id]["output_ids"]:
            if output_id in output_records:
                continue
            output_path = external_root / f"{output_id}.bin"
            output_path.write_bytes(
                f"synthetic external output {case_id} {output_id}\n".encode()
            )
            output_records[output_id] = {
                "bytes": output_path.stat().st_size,
                "external_path": output_path.as_posix(),
                "output_id": output_id,
                "repository_storage": False,
                "sha256": sha256_bytes(output_path.read_bytes()),
            }

    upstream_references: list[dict[str, Any]] = []
    if case_id == "CA-R2":
        baseline_output_id = identities["config.baseline"]["output_ids"][0]
        variant_output_id = identities["config.variant"]["output_ids"][0]
        replay_roots = (
            external_root / "replay-a",
            external_root / "replay-b",
        )
        first_replay_outputs: dict[str, dict[str, Any]] = {}
        for replay_index, replay_root in enumerate(replay_roots):
            replay_artifacts: dict[str, dict[str, str]] = {}
            replay_reproducibility: dict[str, dict[str, Any]] = {}
            for configuration_id, label, output_id in (
                ("config.baseline", "baseline", baseline_output_id),
                ("config.variant", "variant", variant_output_id),
            ):
                content = (
                    f"synthetic external output {case_id} {output_id}\n"
                ).encode()
                filename = f"{output_id}.bin"
                primary_path = replay_root / "build" / label / filename
                replica_path = replay_root / "repro" / label / filename
                primary_path.parent.mkdir(parents=True, exist_ok=True)
                replica_path.parent.mkdir(parents=True, exist_ok=True)
                primary_path.write_bytes(content)
                replica_path.write_bytes(content)
                digest = sha256_bytes(content)
                replay_artifacts[f"{label}_executable"] = {
                    "path": primary_path.as_posix(),
                    "sha256": digest,
                }
                replay_reproducibility[label] = {
                    "algorithm": "sha256",
                    "byte_identical": True,
                    "primary_path": primary_path.as_posix(),
                    "replica_path": replica_path.as_posix(),
                    "sha256": digest,
                }
                if replay_index == 0:
                    first_replay_outputs[output_id] = {
                        "bytes": len(content),
                        "external_path": primary_path.as_posix(),
                        "output_id": output_id,
                        "repository_storage": False,
                        "sha256": digest,
                    }

            upstream = {
                "artifact_type": "q3_r2_formal_fixture_build_evidence",
                "artifacts": replay_artifacts,
                "case_id": case_id,
                "formal_input_executed": False,
                "formal_input_read": False,
                "formal_result_created": False,
                "reproducibility": replay_reproducibility,
                "run_id": RUN_ID,
                "self_tests": {
                    "baseline": "passed",
                    "variant": "passed",
                    "comparator_fictional": "passed",
                    "failure_descendant_cleanup": "passed",
                    "guarded_formal_refusal": "passed",
                    "output_child_root_rejected": "passed",
                    "timeout_descendant_cleanup": "passed",
                },
                "source": {
                    "clean_before_and_after": True,
                    "commit_sha": source_commit,
                },
            }
            upstream_path = replay_root / "upstream-build-evidence.json"
            upstream_path.write_bytes(canonical_bytes(upstream))
            upstream_references.append(
                {
                    "bytes": upstream_path.stat().st_size,
                    "external_path": upstream_path.as_posix(),
                    "sha256": sha256_bytes(upstream_path.read_bytes()),
                }
            )
        output_records.update(first_replay_outputs)
    else:
        upstream = {
            "artifact_type": "synthetic_upstream_build_evidence",
            "case_id": case_id,
            "formal_input_executed": False,
            "formal_result_created": False,
            "run_id": RUN_ID,
            "source_commit": source_commit,
        }
        upstream_path = external_root / "upstream-build-evidence.json"
        upstream_path.write_bytes(canonical_bytes(upstream))
        upstream_references.append(
            {
                "bytes": upstream_path.stat().st_size,
                "external_path": upstream_path.as_posix(),
                "sha256": sha256_bytes(upstream_path.read_bytes()),
            }
        )

    attempts: dict[str, dict[str, Any]] = {}
    for configuration_id in ("config.baseline", "config.variant"):
        attempt_ids = identities[configuration_id]["build_attempt_ids"]
        output_ids = identities[configuration_id]["output_ids"]
        if not attempt_ids:
            raise AssemblyError(
                f"synthetic contract has no attempt for {case_id}/"
                f"{configuration_id}"
            )
        for attempt_id in attempt_ids:
            if attempt_id not in attempts:
                attempts[attempt_id] = {
                    "build_attempt_id": attempt_id,
                    "configuration_ids": [],
                    "outputs": [
                        copy.deepcopy(output_records[output_id])
                        for output_id in output_ids
                    ],
                    "status": "passed",
                }
            elif {
                item["output_id"] for item in attempts[attempt_id]["outputs"]
            } != set(output_ids):
                raise AssemblyError(
                    "synthetic shared attempt has inconsistent outputs: "
                    f"{attempt_id}"
                )
            attempts[attempt_id]["configuration_ids"].append(configuration_id)

    evidence = {
        "$schema": (
            URL_PREFIX + f"{SCHEMA}/r2-build-readiness-evidence-0.1.0.schema.json"
            if case_id == "CA-R2"
            else URL_PREFIX + BUILD_EVIDENCE_SCHEMA_PATH
        ),
        "artifact_type": "fixture_build_evidence",
        "artifact_version": "0.1.0",
        "build_attempts": list(attempts.values()),
        "build_gate_status": "passed",
        "case_id": case_id,
        "created_at": prepared_at,
        "formal_execution": {
            "formal_comparator_executed": False,
            "formal_fixture_executed": False,
            "formal_input_executed": False,
            "formal_result_produced": False,
        },
        "run_id": RUN_ID,
        "source": {
            "clean_before_and_after": True,
            "commit_sha": source_commit,
            "repository_url": f"https://example.invalid/{suffix}",
        },
        "upstream_evidence_files": upstream_references,
    }
    if case_id == "CA-R2":
        evidence["formal_execution"]["formal_input_read"] = False
        evidence["output_boundary"] = {
            "child_root_rejected": True,
            "fixed_root": "D:/GamePrimitivesFormalOutputs",
        }
        evidence["process_tree_cleanup"] = {
            "failure_descendant_zero": True,
            "supervision": "windows-job-object-kill-on-close",
            "timeout_descendant_zero": True,
        }
        evidence["reproducibility"] = {
            "byte_identical": True,
            "independent_build_roots": [
                path.as_posix() for path in replay_roots
            ],
            "method": "msvc-brepro-sha256",
        }
        evidence["source"]["repository_url"] = (
            "https://github.com/id-Software/Quake-III-Arena.git"
        )
    write_synthetic_file(root, evidence_path, canonical_bytes(evidence))

    references_by_path = {
        relative: synthetic_reference(
            root,
            relative,
            f"fixture.{suffix}.{role.replace('.', '-')}",
        )
        for role, relative in roles.items()
    }
    evidence_ref = copy.deepcopy(references_by_path[evidence_path])
    evidence_ref["artifact_id"] = f"evidence.{suffix}.build"

    exact_paths = expected_lock_paths(
        case_id,
        LOCK_EXACT_ROLE_PLACEMENTS[case_id],
    )
    required_paths = expected_lock_paths(
        case_id,
        LOCK_REQUIRED_ROLE_PLACEMENTS[case_id],
    )

    def exact_references(field: str) -> list[dict[str, str]]:
        return [
            copy.deepcopy(references_by_path[path])
            for path in exact_paths[field]
        ]

    def patch_set(
        role: str,
        artifact_field: str,
        configuration_field: str,
    ) -> dict[str, Any]:
        artifacts = exact_references(artifact_field)
        configurations = exact_references(configuration_field)
        if artifacts:
            realization = "patch"
        elif configurations:
            realization = "configuration_only"
        else:
            realization = "not_applicable"
        return {
            "artifacts": artifacts,
            "configuration_artifacts": configurations,
            "patch_role": role,
            "realization": realization,
        }

    compatibility_set = patch_set(
        "compatibility",
        "compatibility_patch_set.artifacts",
        "compatibility_patch_set.configuration_artifacts",
    )
    observation_set = patch_set(
        "observation",
        "observation_patch_set.artifacts",
        "observation_patch_set.configuration_artifacts",
    )
    variant_set = patch_set(
        "variant",
        "variant_patch_set.artifacts",
        "variant_patch_set.configuration_artifacts",
    )
    fixture_references = exact_references("fixture_artifacts")
    shared_binary = variant_set["realization"] == "configuration_only"
    realization = (
        "shared_binary_configuration" if shared_binary else "separate_binary"
    )
    configuration_fixture_references = (
        fixture_references
        + compatibility_set["artifacts"]
        + observation_set["artifacts"]
    )
    configuration_documents = []
    for configuration_id in ("config.baseline", "config.variant"):
        configuration_artifacts = copy.deepcopy(
            configuration_fixture_references
        )
        if configuration_id == "config.variant":
            configuration_artifacts.extend(
                copy.deepcopy(variant_set["artifacts"])
            )
            configuration_artifacts.extend(
                copy.deepcopy(variant_set["configuration_artifacts"])
            )
        configuration_artifacts = list(
            {
                ref_key(reference): reference
                for reference in configuration_artifacts
            }.values()
        )
        configuration_documents.append(
            {
                "build_attempt_ids": list(
                    identities[configuration_id]["build_attempt_ids"]
                ),
                "build_evidence_artifacts": [copy.deepcopy(evidence_ref)],
                "built_outputs": [
                    {
                        "output_id": output_id,
                        "repository_storage": False,
                        "sha256": output_records[output_id]["sha256"],
                    }
                    for output_id in identities[configuration_id]["output_ids"]
                ],
                "configuration_id": configuration_id,
                "fixture_artifacts": configuration_artifacts,
                "formal_input_executed": False,
                "formal_result_produced": False,
                "realization": realization,
                "status": "passed",
            }
        )

    fragment = {
        "$schema": FRAGMENT_SCHEMA_ID,
        "artifact_type": "fixture_assembly_fragment",
        "artifact_version": "0.1.0",
        "build_readiness": {
            "blockers": [],
            "case_id": case_id,
            "configurations": configuration_documents,
            "source_commit": source_commit,
            "status": "passed",
        },
        "build_readiness_evidence_artifacts": [copy.deepcopy(evidence_ref)],
        "case_id": case_id,
        "fixture_lock_case": {
            "build_gate_status": "passed",
            "case_id": case_id,
            "comparator_artifacts": exact_references(
                "comparator_artifacts"
            ),
            "compatibility_patch_set": compatibility_set,
            "fixture_artifacts": fixture_references,
            "fixture_id": f"fixture.{suffix}.synthetic",
            "formal_input_artifacts": exact_references(
                "formal_input_artifacts"
            ),
            "formal_input_executed": False,
            "invariant_ids": [f"inv.{suffix}.0001"],
            "observation_patch_set": observation_set,
            "preparation_probe_artifacts": [
                copy.deepcopy(references_by_path[path])
                for path in required_paths["preparation_probe_artifacts"]
            ],
            "source_identity": {
                "clean_tree_required": True,
                "commit_sha": source_commit,
                "repository_url": f"https://example.invalid/{suffix}",
                "source_identity_artifacts": [
                    synthetic_reference(
                        root,
                        source_path,
                        f"source.{suffix}",
                    )
                ],
            },
            "stop_boundary_id": f"stop.{suffix}",
            "tolerance_rule_ids": [f"tol.{suffix}.0001"],
            "variant_patch_set": variant_set,
        },
        "formal_input_executed": False,
        "formal_result_produced": False,
        "negative_control_artifacts": [
            synthetic_reference(
                root,
                negative_path,
                f"negative.{suffix}.guard",
            )
        ],
        "prepared_at": prepared_at,
        "run_id": RUN_ID,
        "structured_build_evidence": copy.deepcopy(evidence_ref),
        "supersedes_probe": synthetic_reference(
            root,
            SUPERSEDES_PATH,
            "probe.toolchain.v0.1.2",
        ),
    }
    case_source_path = f"{case_dir}/{suffix}-case-lock-source.json"
    case_lock = fragment.pop("fixture_lock_case")
    write_synthetic_file(
        root,
        case_source_path,
        canonical_bytes(case_lock),
    )
    fragment["fixture_lock_case_json_pointer"] = ""
    fragment["fixture_lock_case_source"] = synthetic_reference(
        root,
        case_source_path,
        f"fragment.{suffix}.case-lock-source",
    )
    return fragment


def self_test(source_repo_root: Path) -> dict[str, Any]:
    source_repo_root = source_repo_root.resolve()
    production_paths = (
        repo_path(source_repo_root, READINESS_PATH, must_exist=False),
        repo_path(source_repo_root, FIXTURE_LOCK_PATH, must_exist=False),
    )
    production_before = {
        path: path.read_bytes() if path.is_file() else None
        for path in production_paths
    }
    cases_materialized = 0
    build_attempt_id_passed = False
    missing_r1_passed = False
    missing_build_runner_passed = False
    missing_preparation_evidence_passed = False
    missing_preparation_verifier_passed = False
    missing_runner_passed = False
    missing_support_passed = False
    missing_test_body_passed = False
    output_sha256_passed = False
    tampered_reference_passed = False
    overwrite_refusal_passed = False

    with tempfile.TemporaryDirectory(
        prefix="game-primitives-fixture-assembly-",
    ) as temp_name:
        temp_root = Path(temp_name).resolve()
        synthetic_root = temp_root / "synthetic-repository"
        synthetic_root.mkdir()
        system_temp = Path(tempfile.gettempdir()).resolve()
        if (
            synthetic_root == system_temp
            or not synthetic_root.is_relative_to(system_temp)
            or (synthetic_root / ".git").exists()
        ):
            raise AssemblyError("self-test root is not isolated system temp")
        (synthetic_root / SELF_TEST_MARKER).write_text(
            SELF_TEST_TOKEN + "\n",
            encoding="utf-8",
            newline="\n",
        )
        for relative in (
            TASK_PACKET_SCHEMA_PATH,
            READINESS_SCHEMA_PATH,
            FIXTURE_LOCK_SCHEMA_PATH,
            FRAGMENT_SCHEMA_PATH,
            BUILD_EVIDENCE_SCHEMA_PATH,
            R2_BUILD_EVIDENCE_SCHEMA_PATH,
        ):
            source = repo_path(source_repo_root, relative)
            destination = synthetic_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        write_synthetic_file(
            synthetic_root,
            SUPERSEDES_PATH,
            b'{"synthetic_probe":true}\n',
        )

        fragments = {
            "CA-R1": synthetic_fragment(
                synthetic_root,
                "CA-R1",
                prepared_at="2026-01-01T00:00:01Z",
            ),
            "CA-R2": synthetic_fragment(
                synthetic_root,
                "CA-R2",
                prepared_at="2026-01-01T00:00:02Z",
            ),
            "CA-R3": synthetic_fragment(
                synthetic_root,
                "CA-R3",
                prepared_at="2026-01-01T00:00:03Z",
            ),
        }
        for case_id in ("CA-R2", "CA-R3"):
            path = synthetic_root / FRAGMENT_PATHS[case_id]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(canonical_bytes(fragments[case_id]))

        def final_artifacts_absent(label: str) -> None:
            if (
                (synthetic_root / READINESS_PATH).exists()
                or (synthetic_root / FIXTURE_LOCK_PATH).exists()
            ):
                raise AssemblyError(
                    f"{label} negative control created a final artifact"
                )

        def expect_failure(
            *,
            error_text: str,
            label: str,
        ) -> bool:
            try:
                materialize(synthetic_root)
            except AssemblyError as error:
                if error_text not in str(error):
                    raise AssemblyError(
                        f"{label} failed for an unexpected reason: {error}"
                    ) from error
            else:
                raise AssemblyError(f"{label} did not fail closed")
            final_artifacts_absent(label)
            return True

        try:
            materialize(synthetic_root)
        except AssemblyError as error:
            missing_r1_passed = "missing:" in str(error)
        else:
            raise AssemblyError("missing R1 fragment did not fail closed")
        final_artifacts_absent("missing R1")

        r1_path = synthetic_root / FRAGMENT_PATHS["CA-R1"]
        r1_path.parent.mkdir(parents=True, exist_ok=True)
        r1_path.write_bytes(canonical_bytes(fragments["CA-R1"]))
        result = materialize(synthetic_root)
        if result["status"] != "materialized":
            raise AssemblyError("synthetic three-case assembly did not materialize")
        cases_materialized = 3
        verification = verify(synthetic_root)
        if verification["status"] != "verified":
            raise AssemblyError("synthetic final artifacts did not verify")

        try:
            materialize(synthetic_root)
        except AssemblyError as error:
            overwrite_refusal_passed = "already exist" in str(error)
        else:
            raise AssemblyError("existing final artifact overwrite was not refused")

        (synthetic_root / READINESS_PATH).unlink()
        (synthetic_root / FIXTURE_LOCK_PATH).unlink()
        tamper_path = synthetic_root / EXECUTION_TARGET_PATHS["CA-R2"][
            "formal_runner"
        ]
        original = tamper_path.read_bytes()
        tamper_path.write_bytes(original + b"tampered\n")
        try:
            materialize(synthetic_root)
        except AssemblyError as error:
            tampered_reference_passed = "hash mismatch" in str(error)
        else:
            raise AssemblyError("tampered fragment reference did not fail closed")
        finally:
            tamper_path.write_bytes(original)
        final_artifacts_absent("tampered reference")

        r2_fragment_path = synthetic_root / FRAGMENT_PATHS["CA-R2"]
        r2_fragment_original = r2_fragment_path.read_bytes()

        build_attempt_document, _ = read_json(r2_fragment_path)
        build_attempt_document["build_readiness"]["configurations"][0][
            "build_attempt_ids"
        ] = ["build.ca-r2.synthetic-tampered"]
        try:
            r2_fragment_path.write_bytes(
                canonical_bytes(build_attempt_document)
            )
            build_attempt_id_passed = expect_failure(
                error_text="build attempt IDs",
                label="build attempt ID mutation",
            )
        finally:
            r2_fragment_path.write_bytes(r2_fragment_original)

        output_sha_document, _ = read_json(r2_fragment_path)
        output_sha_document["build_readiness"]["configurations"][0][
            "built_outputs"
        ][0]["sha256"] = "0" * 64
        try:
            r2_fragment_path.write_bytes(canonical_bytes(output_sha_document))
            output_sha256_passed = expect_failure(
                error_text="outputs differ from evidence/contract",
                label="output SHA-256 mutation",
            )
        finally:
            r2_fragment_path.write_bytes(r2_fragment_original)

        def missing_surface_negative(
            *,
            role: str,
            label: str,
        ) -> bool:
            fragment_document, fragment_raw = read_json(r2_fragment_path)
            case_source_relative = fragment_document[
                "fixture_lock_case_source"
            ]["path"]
            case_source_path = synthetic_root / case_source_relative
            case_source_document, case_source_raw = read_json(case_source_path)
            target_path = (
                EXECUTION_TARGET_PATHS["CA-R2"]["support_artifacts"][
                    role.removeprefix("support.")
                ]
                if role.startswith("support.")
                else EXECUTION_TARGET_PATHS["CA-R2"][role]
            )
            fixture_artifacts = case_source_document["fixture_artifacts"]
            filtered = [
                reference
                for reference in fixture_artifacts
                if reference["path"] != target_path
            ]
            if len(filtered) != len(fixture_artifacts) - 1:
                raise AssemblyError(
                    f"{label} target was not present exactly once"
                )
            case_source_document["fixture_artifacts"] = filtered
            mutated_source_raw = canonical_bytes(case_source_document)
            fragment_document["fixture_lock_case_source"]["sha256"] = (
                sha256_bytes(mutated_source_raw)
            )
            try:
                case_source_path.write_bytes(mutated_source_raw)
                r2_fragment_path.write_bytes(
                    canonical_bytes(fragment_document)
                )
                return expect_failure(
                    error_text="lock execution surface mismatch",
                    label=label,
                )
            finally:
                case_source_path.write_bytes(case_source_raw)
                r2_fragment_path.write_bytes(fragment_raw)

        missing_runner_passed = missing_surface_negative(
            role="formal_runner",
            label="missing formal runner",
        )
        missing_build_runner_passed = missing_surface_negative(
            role="support.build_runner",
            label="missing build runner",
        )
        missing_test_body_passed = missing_surface_negative(
            role="test_body",
            label="missing formal test body",
        )
        missing_support_passed = missing_surface_negative(
            role="support.compatibility_source",
            label="missing support artifact",
        )

        def missing_preparation_probe_negative(
            *,
            role: str,
            label: str,
        ) -> bool:
            fragment_document, fragment_raw = read_json(r2_fragment_path)
            case_source_relative = fragment_document[
                "fixture_lock_case_source"
            ]["path"]
            case_source_path = synthetic_root / case_source_relative
            case_source_document, case_source_raw = read_json(case_source_path)
            target_path = EXECUTION_TARGET_PATHS["CA-R2"][
                "support_artifacts"
            ][role.removeprefix("support.")]
            preparation_probes = case_source_document[
                "preparation_probe_artifacts"
            ]
            filtered = [
                reference
                for reference in preparation_probes
                if reference["path"] != target_path
            ]
            if len(filtered) != len(preparation_probes) - 1:
                raise AssemblyError(
                    f"{label} target was not present exactly once"
                )
            case_source_document["preparation_probe_artifacts"] = filtered
            mutated_source_raw = canonical_bytes(case_source_document)
            fragment_document["fixture_lock_case_source"]["sha256"] = (
                sha256_bytes(mutated_source_raw)
            )
            try:
                case_source_path.write_bytes(mutated_source_raw)
                r2_fragment_path.write_bytes(
                    canonical_bytes(fragment_document)
                )
                return expect_failure(
                    error_text="lock execution surface is incomplete",
                    label=label,
                )
            finally:
                case_source_path.write_bytes(case_source_raw)
                r2_fragment_path.write_bytes(fragment_raw)

        missing_preparation_evidence_passed = (
            missing_preparation_probe_negative(
                role="support.build_readiness_evidence",
                label="missing R2 preparation evidence",
            )
        )
        missing_preparation_verifier_passed = (
            missing_preparation_probe_negative(
                role="support.build_readiness_verifier",
                label="missing R2 preparation verifier",
            )
        )

    for path, expected in production_before.items():
        actual = path.read_bytes() if path.is_file() else None
        if actual != expected:
            raise AssemblyError(
                "self-test changed a production fixture artifact: "
                f"{relative_path(source_repo_root, path)}"
            )
    if not all(
        (
            missing_r1_passed,
            build_attempt_id_passed,
            missing_build_runner_passed,
            missing_preparation_evidence_passed,
            missing_preparation_verifier_passed,
            missing_runner_passed,
            missing_support_passed,
            missing_test_body_passed,
            output_sha256_passed,
            tampered_reference_passed,
            overwrite_refusal_passed,
        )
    ):
        raise AssemblyError("one or more synthetic negative controls did not pass")
    return {
        "build_attempt_id_negative_control_passed": build_attempt_id_passed,
        "cases_materialized": cases_materialized,
        "formal_input_executed": False,
        "formal_outputs_created_in_repository": False,
        "missing_build_runner_negative_control_passed": (
            missing_build_runner_passed
        ),
        "missing_preparation_evidence_negative_control_passed": (
            missing_preparation_evidence_passed
        ),
        "missing_preparation_verifier_negative_control_passed": (
            missing_preparation_verifier_passed
        ),
        "missing_r1_negative_control_passed": missing_r1_passed,
        "missing_runner_negative_control_passed": missing_runner_passed,
        "missing_support_negative_control_passed": missing_support_passed,
        "missing_test_body_negative_control_passed": (
            missing_test_body_passed
        ),
        "output_sha256_negative_control_passed": output_sha256_passed,
        "overwrite_refusal_negative_control_passed": overwrite_refusal_passed,
        "status": "synthetic_self_test_passed",
        "synthetic_negative_controls_checked": 11,
        "tampered_reference_negative_control_passed": tampered_reference_passed,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    materialize_command = commands.add_parser("materialize")
    materialize_command.add_argument("--repo-root", required=True, type=Path)
    materialize_command.set_defaults(
        func=lambda args: materialize(args.repo_root)
    )

    verify_command = commands.add_parser("verify")
    verify_command.add_argument("--repo-root", required=True, type=Path)
    verify_command.set_defaults(func=lambda args: verify(args.repo_root))

    fragment_command = commands.add_parser("verify-fragment")
    fragment_command.add_argument("--repo-root", required=True, type=Path)
    fragment_command.add_argument("--fragment", required=True)
    fragment_command.set_defaults(
        func=lambda args: verify_fragment(args.repo_root, args.fragment)
    )

    self_test_command = commands.add_parser("self-test")
    self_test_command.add_argument("--repo-root", required=True, type=Path)
    self_test_command.set_defaults(
        func=lambda args: self_test(args.repo_root)
    )
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        result = args.func(args)
    except (
        AssemblyError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        print(
            json.dumps(
                {
                    "error": str(error),
                    "formal_input_executed": False,
                    "formal_result_produced": False,
                    "status": "failed_closed",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
