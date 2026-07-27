#!/usr/bin/env python3
"""Refresh the explicit continuous-001 preparing-manifest allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


BASE = Path("research/calibration-tests/continuous-action-pilot")
RUN = BASE / "runs/continuous-001"
SCHEMA = BASE / "schema"
FINAL_EXECUTION_PLAN_PATH = "execution/execution-plan.json"
FINAL_EXECUTION_PLAN_SCHEMA_PATH = (
    SCHEMA / "execution-artifact-0.1.1.schema.json"
)
FINAL_EXECUTION_PLAN_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "execution-artifact-0.1.1.schema.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def strict_json_bytes(value: bytes) -> Any:
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = item
        return result

    def reject_constant(constant: str) -> Any:
        raise ValueError(f"non-finite JSON number: {constant}")

    return json.loads(
        value.decode("utf-8"),
        object_pairs_hook=object_pairs,
        parse_constant=reject_constant,
    )


def write_atomic(path: Path, output: bytes, expected_input: bytes) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError("manifest must remain a regular file")
    if path.read_bytes() != expected_input:
        raise ValueError("manifest changed after it was read")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(output)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def repo_path(repo_root: Path, value: str | Path) -> Path:
    path = (repo_root / value).resolve()
    if not path.is_relative_to(repo_root):
        raise ValueError(f"path escapes repository root: {value}")
    return path


def artifact_spec(
    artifact_id: str,
    path: str,
    artifact_kind: str,
    schema_name: str,
    audience: list[str],
    release_stage: str,
    artifact_version: str = "0.1.0",
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "artifact_version": artifact_version,
        "audience": audience,
        "decision_relevant": True,
        "included_in_frozen_set": False,
        "path": path,
        "release_stage": release_stage,
        "schema_path": (SCHEMA / schema_name).as_posix(),
        "supersedes_artifact_id": None,
    }


ADDITIONS = [
    artifact_spec(
        "execution-plan.continuous-001",
        "execution/execution-plan.json",
        "execution_plan",
        "execution-artifact-0.1.1.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "preparation",
        "0.1.1",
    ),
    artifact_spec(
        "fixture-lock.continuous-001",
        "fixtures/fixture-lock.json",
        "fixture",
        "fixture-lock-0.1.0.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "preparation",
    ),
    artifact_spec(
        "formal-build-readiness.continuous-001",
        "fixtures/formal-build-readiness-v0.1.0.json",
        "build_record",
        "formal-build-readiness-0.1.0.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "preparation",
    ),
    artifact_spec(
        "evidence.python-runtime.continuous-001",
        "fixtures/python-runtime-evidence-v0.1.0.json",
        "build_record",
        "python-runtime-evidence-0.1.0.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "preparation",
    ),
    artifact_spec(
        "audit.protocol-incident.r3-byte-integrity-read-v0.1.0",
        "source/protocol-incident-r3-byte-integrity-read-v0.1.0.json",
        "audit",
        "protocol-incident-0.1.0.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "source_audit",
    ),
    artifact_spec(
        "task.projection-audit.continuous-001",
        "inputs/projection-audit.task.json",
        "task_packet",
        "task-packet-0.1.2.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "source_audit",
        "0.1.2",
    ),
    artifact_spec(
        "audit.projection.continuous-001",
        "source/projection-audit-v0.1.0.json",
        "audit",
        "role-submission-0.1.2.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "source_audit",
        "0.1.2",
    ),
    artifact_spec(
        "actor-plan.continuous-001",
        "inputs/actor-plan.md",
        "actor_descriptor",
        "markdown-document-0.1.0.schema.json",
        ["custodian", "public_after_reveal"],
        "preparation",
    ),
    artifact_spec(
        "generator.stage2-envelope-v0.1.0",
        "inputs/generate-stage2-envelope-v0.1.0.py",
        "generator",
        "text-artifact-0.1.0.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "prediction",
    ),
    artifact_spec(
        "generator.stage2-task-v0.1.0",
        "inputs/generate-stage2-prediction-task-v0.1.0.py",
        "generator",
        "text-artifact-0.1.0.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "prediction",
    ),
    artifact_spec(
        "template.reconstruction-response-v0.1.0",
        "inputs/reconstruction-response.template.json",
        "fixture",
        "response-template-0.1.0.schema.json",
        ["all_blind_testers", "custodian", "public_after_reveal"],
        "reconstruction",
    ),
    artifact_spec(
        "template.prediction-response-v0.1.0",
        "inputs/prediction-response.template.json",
        "fixture",
        "response-template-0.1.0.schema.json",
        ["all_blind_testers", "custodian", "public_after_reveal"],
        "prediction",
    ),
    artifact_spec(
        "task.reconstruction.condition-v01",
        "inputs/stage1-condition-v01.task.json",
        "task_packet",
        "task-packet-0.1.2.schema.json",
        ["condition-v01", "custodian", "public_after_reveal"],
        "reconstruction",
        "0.1.2",
    ),
    artifact_spec(
        "task.reconstruction.condition-v02",
        "inputs/stage1-condition-v02.task.json",
        "task_packet",
        "task-packet-0.1.2.schema.json",
        ["condition-v02", "custodian", "public_after_reveal"],
        "reconstruction",
        "0.1.2",
    ),
    artifact_spec(
        "task.prediction.continuous-001",
        "inputs/stage2-prediction.task.json",
        "task_packet",
        "task-packet-0.1.2.schema.json",
        ["all_blind_testers", "custodian", "public_after_reveal"],
        "prediction",
        "0.1.2",
    ),
    artifact_spec(
        "envelope.variant.stage2-v0.1.0",
        "inputs/stage2-variant-envelope.json",
        "fixture",
        "variant-envelope-0.1.0.schema.json",
        ["all_blind_testers", "custodian", "public_after_reveal"],
        "prediction",
    ),
]

for stage, schema_name, release_stage in (
    (
        "stage1",
        "stage1-seat-dispatch-envelope-0.1.0.schema.json",
        "reconstruction",
    ),
    (
        "stage2",
        "stage2-seat-dispatch-envelope-0.1.0.schema.json",
        "prediction",
    ),
):
    for seat in ("p01", "p02", "p03", "p04"):
        ADDITIONS.append(
            artifact_spec(
                f"dispatch-template.{stage}.{seat}",
                f"inputs/{stage}-dispatch-{seat}.template.json",
                "submission_envelope",
                schema_name,
                ["custodian", "public_after_reveal"],
                release_stage,
            )
        )

COMMON_FORMAL_AUDIENCE = [
    "custodian",
    "public_after_reveal",
    "source_auditor",
]

ADDITIONS.extend(
    [
        artifact_spec(
            "build.r1.formal-preparation-v0.1.0",
            "fixtures/r1/footsies-r1-formal-preparation-v0.1.0.md",
            "build_record",
            "markdown-document-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.observation-source-v0.1.0",
            "fixtures/r1/footsies-r1-observation-v0.1.0.cs",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.observation-meta-v0.1.0",
            "fixtures/r1/footsies-r1-observation-v0.1.0.cs.meta",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.variant-patch-v0.1.0",
            "fixtures/r1/footsies-r1-whiff-cancel-v0.1.0.patch",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.formal-input-v0.1.0",
            "fixtures/r1/footsies-r1-formal-input-v0.1.0.json",
            "fixture",
            "formal-input-trace-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r1.formal-runner-v0.1.0",
            "fixtures/r1/run-footsies-r1-formal-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r1.formal-comparator-v0.1.0",
            "fixtures/r1/compare-footsies-r1-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "build.r1.standalone-evidence-v0.1.0",
            "fixtures/r1/r1-standalone-build-evidence-v0.1.0.json",
            "build_record",
            "r1-standalone-build-evidence-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r1.standalone-build-runner-v0.1.0",
            "fixtures/r1/run-footsies-r1-standalone-build-smoke-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "validator.r1.build-readiness-v0.1.0",
            "fixtures/r1/verify-r1-build-readiness-v0.1.0.py",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r1.formal-output-boundary-v0.1.0",
            "fixtures/r1/r1-formal-output-boundary-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r1.process-boundary-v0.1.0",
            "fixtures/r1/r1-process-boundary-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "probe.r1.formal-output-boundary-self-test-v0.1.0",
            "fixtures/r1/self-test-r1-formal-output-boundary-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "probe.r1.process-boundary-self-test-v0.1.0",
            "fixtures/r1/self-test-r1-process-boundary-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "negative.r1.standalone-permit-first-v0.1.0",
            "fixtures/r1/r1-standalone-permit-first-negative-v0.1.0.json",
            "build_record",
            "r1-standalone-permit-first-negative-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "negative.r1.formal-output-boundary-v0.1.0",
            "fixtures/r1/r1-formal-output-boundary-negative-v0.1.0.json",
            "build_record",
            "r1-formal-output-boundary-negative-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "negative.r1.process-boundary-v0.1.0",
            "fixtures/r1/r1-process-boundary-negative-v0.1.0.json",
            "build_record",
            "r1-process-boundary-negative-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "method.r1.standalone-v0.1.0",
            "fixtures/r1/footsies-r1-standalone-method-v0.1.0.md",
            "build_record",
            "markdown-document-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r1.standalone-formal-runner-v0.1.0",
            "fixtures/r1/run-footsies-r1-standalone-formal-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.standalone-formal-project-v0.1.0",
            "fixtures/r1/standalone/FootsiesR1Formal.csproj",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.standalone-formal-body-v0.1.0",
            "fixtures/r1/standalone/FormalProgram.cs",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.standalone-source-contract-v0.1.0",
            "fixtures/r1/standalone/FrozenSourceContract.cs",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.standalone-nuget-config-v0.1.0",
            "fixtures/r1/standalone/NuGet.config",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.standalone-unity-compatibility-v0.1.0",
            "fixtures/r1/standalone/UnityCompatibility.cs",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.standalone-yaml-loader-v0.1.0",
            "fixtures/r1/standalone/UnityYamlAssetLoader.cs",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "build.r2.formal-preparation-v0.1.0",
            "fixtures/r2/q3-formal-fixture-preparation-v0.1.0.md",
            "build_record",
            "markdown-document-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "build.r2.structured-readiness-v0.1.0",
            "fixtures/r2/r2-build-readiness-evidence-v0.1.0.json",
            "build_record",
            "r2-build-readiness-evidence-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.compatibility-source-v0.1.0",
            "fixtures/r2/q3-formal-compatibility-v0.1.0.c",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.harness-header-v0.1.0",
            "fixtures/r2/q3-formal-fixture-v0.1.0.h",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.harness-source-v0.1.0",
            "fixtures/r2/q3-formal-harness-v0.1.0.c",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.compatibility-patch-v0.1.0",
            "fixtures/r2/q3-msvc-x64-compatibility-v0.1.0.patch",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.observation-patch-v0.1.0",
            "fixtures/r2/q3-observation-v0.1.0.patch",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.variant-patch-v0.1.0",
            "fixtures/r2/q3-entry-latch-variant-v0.1.0.patch",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.formal-input-v0.1.0",
            "fixtures/r2/r2-formal-input-v0.1.0.json",
            "fixture",
            "formal-input-trace-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r2.build-runner-v0.1.0",
            "fixtures/r2/build-q3-formal-fixture-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r2.formal-runner-v0.1.0",
            "fixtures/r2/run-q3-formal-guarded-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "validator.r2.build-readiness-v0.1.0",
            "fixtures/r2/verify-r2-build-readiness-v0.1.0.py",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r2.formal-comparator-v0.1.0",
            "fixtures/r2/compare-q3-formal-traces-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.spec-v0.1.0",
            "fixtures/r3/r3-fixture-spec-v0.1.0.json",
            "fixture",
            "r3-fixture-spec-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "build.r3.formal-evidence-v0.1.0",
            "fixtures/r3/r3-build-list-evidence-v0.1.0.json",
            "build_record",
            "r3-build-list-evidence-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.dependency-lock-set-v0.1.0",
            "fixtures/r3/dependency-lock-set-v0.1.0.json",
            "fixture",
            "dependency-lock-set-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.deterministic-build-targets-v0.1.0",
            "fixtures/r3/r3-deterministic-build-v0.1.0.targets",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.observation-source-v0.1.0",
            "fixtures/r3/TestSceneGamePrimitivesR3.cs",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.formal-input-v0.1.0",
            "fixtures/r3/formal-input-r3-v0.1.0.json",
            "fixture",
            "formal-input-trace-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r3.build-list-runner-v0.1.0",
            "fixtures/r3/run-osu-r3-build-list-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r3.formal-runner-v0.1.0",
            "fixtures/r3/run-osu-r3-formal-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r3.safety-guards-v0.1.0",
            "fixtures/r3/r3-safety-guards-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r3.formal-comparator-v0.1.0",
            "fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
    ]
)


def load_registry(
    repo_root: Path,
) -> tuple[Registry, dict[str, dict[str, Any]]]:
    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(repo_path(repo_root, SCHEMA).glob("*.schema.json")):
        schema = strict_json_bytes(path.read_bytes())
        Draft202012Validator.check_schema(schema)
        schemas[schema["$id"]] = schema
        registry = registry.with_resource(
            schema["$id"],
            Resource.from_contents(schema),
        )
    return registry, schemas


def validate_final_execution_plan(
    repo_root: Path,
    run_dir: Path,
    registry: Registry,
    schemas: dict[str, dict[str, Any]],
) -> None:
    artifact_path = repo_path(run_dir, FINAL_EXECUTION_PLAN_PATH)
    if artifact_path.is_symlink() or not artifact_path.is_file():
        raise ValueError(
            "final execution plan must be a regular repository file"
        )
    document = strict_json_bytes(artifact_path.read_bytes())
    if not isinstance(document, dict):
        raise ValueError("final execution plan must be a JSON object")

    expected_identity = {
        "$schema": FINAL_EXECUTION_PLAN_SCHEMA_ID,
        "artifact_type": "execution_plan",
        "artifact_version": "0.1.1",
        "run_id": "continuous-001",
    }
    actual_identity = {
        key: document.get(key)
        for key in expected_identity
    }
    if actual_identity != expected_identity:
        raise ValueError(
            "execution/execution-plan.json is not the final execution plan; "
            f"expected {expected_identity}, got {actual_identity}"
        )

    schema = schemas.get(FINAL_EXECUTION_PLAN_SCHEMA_ID)
    if schema is None:
        raise ValueError(
            "final execution-plan schema is absent from the local registry: "
            f"{FINAL_EXECUTION_PLAN_SCHEMA_PATH.as_posix()}"
        )
    errors = sorted(
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        details = "\n".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: "
            f"{error.message}"
            for error in errors[:12]
        )
        raise ValueError(
            "execution/execution-plan.json does not validate against "
            f"{FINAL_EXECUTION_PLAN_SCHEMA_PATH.as_posix()}:\n{details}"
        )


def refresh_entry(
    repo_root: Path,
    run_dir: Path,
    entry: dict[str, Any],
) -> dict[str, Any]:
    result = dict(entry)
    artifact_path = repo_path(run_dir, result["path"])
    schema_path = repo_path(repo_root, result["schema_path"])
    if not artifact_path.is_file():
        raise FileNotFoundError(f"manifest artifact is missing: {artifact_path}")
    if not schema_path.is_file():
        raise FileNotFoundError(f"manifest schema is missing: {schema_path}")
    if artifact_path.suffix.lower() == ".json":
        document = strict_json_bytes(artifact_path.read_bytes())
        declared_version = document.get("artifact_version")
        if isinstance(declared_version, str):
            result["artifact_version"] = declared_version
    result["sha256"] = sha256(artifact_path)
    result["schema_sha256"] = sha256(schema_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument(
        "--manifest",
        default=(RUN / "manifest.json").as_posix(),
    )
    parser.add_argument("--updated-at", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    manifest_path = repo_path(repo_root, args.manifest)
    run_dir = manifest_path.parent
    manifest_input = manifest_path.read_bytes()
    manifest = strict_json_bytes(manifest_input)
    if (
        manifest.get("status") != "preparing"
        or manifest.get("freeze_commit") is not None
        or manifest.get("frozen_artifact_set_digest") is not None
        or manifest.get("stage_digests") != []
    ):
        raise ValueError("refusing to refresh a non-preparing or partially frozen manifest")

    entries = {
        entry["path"]: dict(entry)
        for entry in manifest["artifacts"]
    }
    if len(entries) != len(manifest["artifacts"]):
        raise ValueError("manifest contains duplicate artifact paths")

    registry, schemas = load_registry(repo_root)
    source_task_schema = (
        SCHEMA / "task-packet-0.1.2.schema.json"
    ).as_posix()
    for path in (
        "inputs/source-encoding-packet.json",
        "inputs/source-audit-packet.json",
    ):
        entries[path]["artifact_version"] = "0.1.2"
        entries[path]["schema_path"] = source_task_schema

    deferred_until_created = {
        "source/projection-audit-v0.1.0.json",
    }
    active_additions = [
        addition
        for addition in ADDITIONS
        if (
            addition["path"] not in deferred_until_created
            or repo_path(run_dir, addition["path"]).is_file()
        )
    ]

    for addition in active_additions:
        existing = entries.get(addition["path"])
        if addition["path"] == FINAL_EXECUTION_PLAN_PATH:
            validate_final_execution_plan(
                repo_root,
                run_dir,
                registry,
                schemas,
            )
        if (
            addition["path"] == FINAL_EXECUTION_PLAN_PATH
            and existing is not None
            and existing.get("artifact_id")
            == "execution-plan-preparation.continuous-001"
            and existing.get("schema_path")
            == (
                SCHEMA / "execution-plan-preparation-0.1.0.schema.json"
            ).as_posix()
        ):
            entries[addition["path"]] = addition
            continue
        if existing is not None and any(
            existing.get(key) != value
            for key, value in addition.items()
        ):
            raise ValueError(
                f"allowlisted addition conflicts with existing entry: {addition['path']}"
            )
        entries[addition["path"]] = addition

    original_paths = [entry["path"] for entry in manifest["artifacts"]]
    added_paths = [
        entry["path"]
        for entry in active_additions
        if entry["path"] not in original_paths
    ]
    ordered_paths = original_paths + added_paths
    manifest["artifacts"] = [
        refresh_entry(repo_root, run_dir, entries[path])
        for path in ordered_paths
    ]
    manifest["updated_at"] = args.updated_at

    schema = schemas[manifest["$schema"]]
    errors = sorted(
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        details = "\n".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: "
            f"{error.message}"
            for error in errors[:12]
        )
        raise ValueError(f"refreshed manifest does not validate:\n{details}")

    output = canonical_bytes(manifest)
    if args.write:
        write_atomic(manifest_path, output, manifest_input)
    print(
        json.dumps(
            {
                "artifact_count": len(manifest["artifacts"]),
                "manifest_sha256": hashlib.sha256(output).hexdigest(),
                "status": "written" if args.write else "preview",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
