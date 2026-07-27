#!/usr/bin/env python3
"""Build and verify the deterministic continuous-001 final execution plan.

The tool is pre-gate only.  It validates the already materialized fixture lock
and build-readiness record, derives a plan from the neutral variant envelope,
and binds the exact locked execution surface.  It never invokes a formal
runner, comparator, prediction task, or formal input.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


sys.dont_write_bytecode = True
TOOLS_DIRECTORY = Path(__file__).resolve().parent
if str(TOOLS_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIRECTORY))

from formal_execution_target_contract import (  # noqa: E402
    EXECUTION_TARGET_PATHS,
)


BASE = Path("research/calibration-tests/continuous-action-pilot")
RUN = BASE / "runs/continuous-001"
SCHEMA = BASE / "schema"
PLAN_PATH = RUN / "execution/execution-plan.json"
LOCK_PATH = RUN / "fixtures/fixture-lock.json"
READINESS_PATH = RUN / "fixtures/formal-build-readiness-v0.1.0.json"
ENVELOPE_PATH = RUN / "inputs/stage2-variant-envelope.json"
PREDICTION_TASK_PATH = RUN / "inputs/stage2-prediction.task.json"
ASSEMBLER_PATH = BASE / "tools/materialize-fixture-assembly.py"
PLAN_SCHEMA_PATH = SCHEMA / "execution-artifact-0.1.1.schema.json"
PREPARATION_SCHEMA_PATH = SCHEMA / "execution-plan-preparation-0.1.0.schema.json"

PLAN_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "execution-artifact-0.1.1.schema.json"
)
PREPARATION_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "execution-plan-preparation-0.1.0.schema.json"
)
CASE_IDS = ("CA-R1", "CA-R2", "CA-R3")
FORMAL_OUTPUT_ROOT = r"D:\GamePrimitivesFormalOutputs"
REPETITION_INDEX_PLACEHOLDER = "${REPETITION_INDEX}"


class FinalPlanError(RuntimeError):
    """A fail-closed final-plan error."""


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FinalPlanError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonfinite(value: str) -> None:
    raise FinalPlanError(f"non-finite JSON number: {value}")


def load_json(path: Path) -> Any:
    try:
        value = json.loads(
            path.read_bytes().decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FinalPlanError(f"invalid JSON at {path.as_posix()}: {exc}") from exc
    return value


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalized_root(repo_root: Path) -> Path:
    root = repo_root.resolve()
    if not root.is_dir():
        raise FinalPlanError(f"repository root is not a directory: {root}")
    return root


def resolve_repo_path(repo_root: Path, relative: Path | str) -> Path:
    candidate = (repo_root / relative).resolve()
    if not candidate.is_relative_to(repo_root):
        raise FinalPlanError(f"path escapes repository: {relative}")
    return candidate


def load_schema_registry(
    repo_root: Path,
) -> tuple[Registry, dict[str, dict[str, Any]]]:
    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    schema_dir = resolve_repo_path(repo_root, SCHEMA)
    for path in sorted(schema_dir.glob("*.schema.json")):
        schema = load_json(path)
        if not isinstance(schema, dict):
            raise FinalPlanError(f"schema is not an object: {path.as_posix()}")
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise FinalPlanError(f"schema has no $id: {path.as_posix()}")
        if schema_id in schemas:
            raise FinalPlanError(f"duplicate schema $id: {schema_id}")
        schemas[schema_id] = schema
        registry = registry.with_resource(
            schema_id,
            Resource.from_contents(schema),
        )
    return registry, schemas


def validate_schema(
    value: Any,
    schema_id: str,
    registry: Registry,
    schemas: dict[str, dict[str, Any]],
    *,
    label: str,
) -> None:
    schema = schemas.get(schema_id)
    if schema is None:
        raise FinalPlanError(f"missing trusted schema for {label}: {schema_id}")
    errors = sorted(
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        pointer = "/" + "/".join(str(part) for part in error.absolute_path)
        raise FinalPlanError(f"{label} fails schema at {pointer}")


def invoke_fixture_assembly_verify(repo_root: Path) -> dict[str, Any]:
    assembler = resolve_repo_path(repo_root, ASSEMBLER_PATH)
    spec = importlib.util.spec_from_file_location(
        "continuous_001_fixture_assembler",
        assembler,
    )
    if spec is None or spec.loader is None:
        raise FinalPlanError("cannot load fixture assembly verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        result = module.verify(repo_root)
    except Exception as exc:  # noqa: BLE001 - normalize the gate failure.
        raise FinalPlanError("fixture assembly verification failed") from exc
    finally:
        sys.modules.pop(spec.name, None)
    if result.get("status") != "verified":
        raise FinalPlanError("fixture assembly verifier did not return verified")
    return result


def reference_key(reference: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(reference["artifact_id"]),
        str(reference["path"]),
        str(reference["sha256"]),
    )


def unique_references(
    references: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for reference in references:
        key = reference_key(reference)
        if key not in seen:
            result.append(copy.deepcopy(reference))
            seen.add(key)
    return result


def locked_configuration_surfaces(
    case_lock: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    common = list(case_lock["fixture_artifacts"])
    for patch_name in ("compatibility_patch_set", "observation_patch_set"):
        patch = case_lock[patch_name]
        common.extend(patch["artifacts"])
        common.extend(patch["configuration_artifacts"])
    baseline = unique_references(common)
    variant_patch = case_lock["variant_patch_set"]
    variant = unique_references(
        baseline
        + list(variant_patch["artifacts"])
        + list(variant_patch["configuration_artifacts"])
    )
    return baseline, variant


def readiness_output_ids(
    readiness_case: dict[str, Any],
) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for configuration in readiness_case["configurations"]:
        built_outputs = configuration["built_outputs"]
        if len(built_outputs) != 1:
            raise FinalPlanError(
                f"{readiness_case['case_id']} must bind one output per configuration"
            )
        outputs[configuration["configuration_id"]] = built_outputs[0]["output_id"]
    if set(outputs) != {"config.baseline", "config.variant"}:
        raise FinalPlanError(
            f"{readiness_case['case_id']} readiness configurations differ"
        )
    return outputs


def build_command(case_id: str) -> list[str]:
    target = EXECUTION_TARGET_PATHS[case_id]
    build_runner = target["support_artifacts"]["build_runner"]
    if case_id == "CA-R1":
        return [
            "powershell.exe",
            "-NoProfile",
            "-File",
            build_runner,
            "-SourcePath",
            "${FOOTSIES_SOURCE}",
            "-DotnetPath",
            "${DOTNET_8_0_100}",
            "-CacheRoot",
            "${CA_R1_BUILD_ROOT}",
        ]
    if case_id == "CA-R2":
        return [
            "powershell.exe",
            "-NoProfile",
            "-File",
            build_runner,
            "-SourcePath",
            "${QUAKE3_SOURCE}",
            "-OutputPath",
            "${CA_R2_BUILD_ROOT}",
            "-VcVarsPath",
            "${MSVC_VCVARS64}",
        ]
    return [
        "powershell.exe",
        "-NoProfile",
        "-File",
        build_runner,
        "-SourcePath",
        "${OSU_SOURCE}",
        "-DotnetPath",
        "${DOTNET_8_0_100}",
        "-CacheRoot",
        "${CA_R3_BUILD_ROOT}",
    ]


def run_command(case_id: str, configuration_id: str) -> list[str]:
    target = EXECUTION_TARGET_PATHS[case_id]
    runner = target["formal_runner"]
    if case_id == "CA-R1":
        return [
            "powershell.exe",
            "-NoProfile",
            "-File",
            runner,
            "-ConfigurationId",
            configuration_id,
            "-RepetitionIndex",
            REPETITION_INDEX_PLACEHOLDER,
            "-SourceRoot",
            "${FOOTSIES_SOURCE}",
            "-DotnetPath",
            "${DOTNET_8_0_100}",
            "-FormalOutputRoot",
            FORMAL_OUTPUT_ROOT,
            "-ExecutionPermitPath",
            "${FORMAL_EXECUTION_PERMIT}",
            "-PythonPath",
            "${PYTHON_3_14_3}",
        ]
    if case_id == "CA-R2":
        return [
            "powershell.exe",
            "-NoProfile",
            "-File",
            runner,
            "-BuildEvidencePath",
            target["support_artifacts"]["build_readiness_evidence"],
            "-ConfigurationId",
            configuration_id,
            "-RepetitionIndex",
            REPETITION_INDEX_PLACEHOLDER,
            "-ExecutionPermitPath",
            "${FORMAL_EXECUTION_PERMIT}",
            "-FormalOutputRoot",
            FORMAL_OUTPUT_ROOT,
            "-SourceRoot",
            "${QUAKE3_SOURCE}",
            "-ToolchainRoot",
            "${MSVC_TOOLCHAIN_ROOT}",
            "-PythonPath",
            "${PYTHON_3_14_3}",
        ]
    return [
        "powershell.exe",
        "-NoProfile",
        "-File",
        runner,
        "-ConfigurationId",
        configuration_id,
        "-RepetitionIndex",
        REPETITION_INDEX_PLACEHOLDER,
        "-SourcePath",
        "${OSU_SOURCE}",
        "-DotnetPath",
        "${DOTNET_8_0_100}",
        "-FormalOutputRoot",
        FORMAL_OUTPUT_ROOT,
        "-ExecutionPermitPath",
        "${FORMAL_EXECUTION_PERMIT}",
        "-PythonPath",
        "${PYTHON_3_14_3}",
    ]


def tolerance_rule(
    observation: dict[str, Any],
    tolerance_spec: dict[str, Any],
) -> dict[str, Any]:
    comparison_kind = tolerance_spec["comparison_kind"]
    if comparison_kind == "exact":
        comparison = "exact"
        value = {
            "serialized_value": "exact",
            "unit": None,
            "value_type": "status",
        }
    elif comparison_kind == "zero_or_nonzero_direction":
        comparison = "set_equality"
        value = {
            "serialized_value": "negative|zero|positive",
            "unit": None,
            "value_type": "id_set",
        }
    elif comparison_kind == "absolute_delta":
        comparison = "absolute"
        value = copy.deepcopy(tolerance_spec["threshold"])
    else:
        raise FinalPlanError(
            f"unsupported tolerance comparison: {comparison_kind}"
        )
    return {
        "comparison": comparison,
        "observation_id": observation["observation_id"],
        "tolerance_rule_id": observation["tolerance_rule_id"],
        "value": value,
    }


def build_case_plan(
    *,
    case_id: str,
    case_lock: dict[str, Any],
    readiness_case: dict[str, Any],
    intervention: dict[str, Any],
    observations_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    baseline_surface, variant_surface = locked_configuration_surfaces(case_lock)
    output_ids = readiness_output_ids(readiness_case)
    comparator_id = f"comparator.{case_id.lower()}.formal"
    tolerance_specs = {
        item["tolerance_rule_id"]: item
        for item in intervention["tolerance_specs"]
    }
    observations = [
        observations_by_id[observation_id]
        for observation_id in intervention["observation_ids"]
    ]
    tolerances = [
        tolerance_rule(
            observation,
            tolerance_specs[observation["tolerance_rule_id"]],
        )
        for observation in observations
    ]
    environment_id = (
        "environment.windows-msvc-19.50.35723"
        if case_id == "CA-R2"
        else "environment.windows-dotnet-8.0.100"
    )
    configurations = []
    for configuration_id, semantic_role, surface in (
        ("config.baseline", "baseline", baseline_surface),
        ("config.variant", "variant", variant_surface),
    ):
        configurations.append(
            {
                "build_command": build_command(case_id),
                "configuration_id": configuration_id,
                "expected_binary_path": (
                    f"external-builds/{output_ids[configuration_id]}"
                ),
                "fixture_artifacts": surface,
                "run_command": run_command(case_id, configuration_id),
                "semantic_role": semantic_role,
            }
        )
    return {
        "case_id": case_id,
        "comparators": [
            {
                "allowed_observation_ids": list(intervention["observation_ids"]),
                "comparator_id": comparator_id,
                "implementation": copy.deepcopy(
                    case_lock["comparator_artifacts"][0]
                ),
                "tolerance_rules": tolerances,
            }
        ],
        "configurations": configurations,
        "environment_refs": [
            environment_id,
            "environment.windows-python-3.14.3",
        ],
        "formal_input": copy.deepcopy(case_lock["formal_input_artifacts"][0]),
        "invariants": [
            {
                "comparator_id": comparator_id,
                "description": invariant["description"],
                "invariant_id": invariant["invariant_id"],
                "observation_ids": list(intervention["observation_ids"]),
            }
            for invariant in intervention["invariant_specs"]
        ],
        "negative_control": False,
        "repetition_count": 2,
        "source_commit": case_lock["source_identity"]["commit_sha"],
        "stop_boundary_id": case_lock["stop_boundary_id"],
        "time_base_ids": [
            intervention["formal_input_spec"]["time_base"]["time_base_id"]
        ],
    }


def build_negative_control(r3_plan: dict[str, Any]) -> dict[str, Any]:
    negative = copy.deepcopy(r3_plan)
    negative["case_id"] = "NEG-01"
    negative["negative_control"] = True
    negative["configurations"] = [
        {
            **copy.deepcopy(r3_plan["configurations"][0]),
            "configuration_id": "config.negative-a",
            "run_command": run_command("CA-R3", "config.negative-a"),
            "semantic_role": "negative_control_a",
        },
        {
            **copy.deepcopy(r3_plan["configurations"][1]),
            "configuration_id": "config.negative-b",
            "run_command": run_command("CA-R3", "config.negative-b"),
            "semantic_role": "negative_control_b",
        },
    ]
    return negative


def build_expected_plan(
    repo_root: Path,
    *,
    verify_fixture_assembly: bool = True,
) -> dict[str, Any]:
    repo_root = normalized_root(repo_root)
    assembly_result = (
        invoke_fixture_assembly_verify(repo_root)
        if verify_fixture_assembly
        else None
    )
    lock_path = resolve_repo_path(repo_root, LOCK_PATH)
    readiness_path = resolve_repo_path(repo_root, READINESS_PATH)
    envelope_path = resolve_repo_path(repo_root, ENVELOPE_PATH)
    task_path = resolve_repo_path(repo_root, PREDICTION_TASK_PATH)
    for path in (lock_path, readiness_path, envelope_path, task_path):
        if not path.is_file() or path.is_symlink():
            raise FinalPlanError(f"required regular file is missing: {path}")

    lock = load_json(lock_path)
    readiness = load_json(readiness_path)
    envelope = load_json(envelope_path)
    task = load_json(task_path)
    registry, schemas = load_schema_registry(repo_root)
    validate_schema(
        lock,
        str(lock["$schema"]),
        registry,
        schemas,
        label="fixture lock",
    )
    validate_schema(
        readiness,
        str(readiness["$schema"]),
        registry,
        schemas,
        label="formal build readiness",
    )
    validate_schema(
        envelope,
        str(envelope["$schema"]),
        registry,
        schemas,
        label="variant envelope",
    )
    validate_schema(
        task,
        str(task["$schema"]),
        registry,
        schemas,
        label="prediction task",
    )
    if assembly_result is not None:
        if (
            assembly_result["fixture_lock_sha256"] != sha256_path(lock_path)
            or assembly_result["formal_build_readiness_sha256"]
            != sha256_path(readiness_path)
        ):
            raise FinalPlanError("fixture assembly result hash binding failed")
    if (
        lock["run_id"] != "continuous-001"
        or readiness["run_id"] != "continuous-001"
        or envelope["run_id"] != "continuous-001"
        or task["run_id"] != "continuous-001"
    ):
        raise FinalPlanError("run id mismatch among final-plan inputs")
    if (
        lock["formal_input_executed"]
        or lock["formal_execution_authorized"]
        or readiness["formal_input_executed"]
        or readiness["formal_result_produced"]
    ):
        raise FinalPlanError("pre-gate execution state is not clean")

    lock_by_case = {case["case_id"]: case for case in lock["cases"]}
    readiness_by_case = {
        case["case_id"]: case for case in readiness["cases"]
    }
    intervention_by_case = {
        case["case_id"]: case for case in envelope["case_interventions"]
    }
    if (
        set(lock_by_case) != set(CASE_IDS)
        or set(readiness_by_case) != set(CASE_IDS)
        or set(intervention_by_case) != set(CASE_IDS)
    ):
        raise FinalPlanError("three-case coverage mismatch")
    observations_by_id = {
        item["observation_id"]: item for item in task["allowed_observations"]
    }
    cases = [
        build_case_plan(
            case_id=case_id,
            case_lock=lock_by_case[case_id],
            readiness_case=readiness_by_case[case_id],
            intervention=intervention_by_case[case_id],
            observations_by_id=observations_by_id,
        )
        for case_id in CASE_IDS
    ]
    cases.append(build_negative_control(cases[2]))
    plan = {
        "$schema": PLAN_SCHEMA_ID,
        "artifact_type": "execution_plan",
        "artifact_version": "0.1.1",
        "case_results": [],
        "cases": cases,
        "created_at": max(lock["created_at"], readiness["assessed_at"]),
        "derivation_artifacts": [],
        "environments": [
            {
                "environment_id": "environment.windows-dotnet-8.0.100",
                "name": "Windows isolated portable .NET execution",
                "platform": "Windows x64",
                "version": ".NET SDK 8.0.100",
            },
            {
                "environment_id": "environment.windows-msvc-19.50.35723",
                "name": "Windows isolated MSVC x64 execution",
                "platform": "Windows x64",
                "version": "MSVC 19.50.35723",
            },
            {
                "environment_id": "environment.windows-python-3.14.3",
                "name": "Hash-pinned Python verifier runtime",
                "platform": "Windows x64",
                "version": "Python 3.14.3",
            },
        ],
        "execution_plan_sha256": None,
        "executions": [],
        "finished_at": None,
        "fixture_lock": {
            "artifact_id": "fixture.lock-v0.1.0",
            "path": LOCK_PATH.as_posix(),
            "sha256": sha256_path(lock_path),
        },
        "prediction_set_digest": None,
        "protocol_version": "0.1.1",
        "run_id": "continuous-001",
        "started_at": None,
        "trace_bundle_sha256": None,
    }
    validate_schema(
        plan,
        PLAN_SCHEMA_ID,
        registry,
        schemas,
        label="final execution plan",
    )
    return plan


def verify_plan_document(
    repo_root: Path,
    plan: dict[str, Any],
) -> dict[str, Any]:
    expected = build_expected_plan(repo_root)
    if canonical_bytes(plan) != canonical_bytes(expected):
        raise FinalPlanError(
            "execution plan is not the deterministic locked projection"
        )
    return {
        "case_ids": [case["case_id"] for case in plan["cases"]],
        "formal_input_executed": False,
        "formal_result_produced": False,
        "sha256": sha256_bytes(canonical_bytes(plan)),
        "status": "verified",
    }


def verify_frozen_plan_without_formal_input(
    repo_root: Path,
    frozen_bindings: dict[str, dict[str, str]],
) -> dict[str, Any]:
    """Replay the frozen plan derivation without opening a formal input.

    Execution-permit verification runs before any formal-input read.  It may
    read the already frozen declarative lock, readiness record, neutral
    envelope, prediction task, and plan, but it must obtain every formal-input
    path/hash only from those frozen declarations.  This verifier therefore
    skips fixture assembly (whose normal pre-gate integrity pass hashes fixture
    members) and instead requires the exact non-input derivation files to match
    the authorization-bound frozen-set map before rebuilding the plan.
    """

    repo_root = normalized_root(repo_root)
    required_paths = (
        PLAN_PATH,
        LOCK_PATH,
        READINESS_PATH,
        ENVELOPE_PATH,
        PREDICTION_TASK_PATH,
    )
    for relative in required_paths:
        relative_text = relative.as_posix()
        reference = frozen_bindings.get(relative_text)
        if (
            not isinstance(reference, dict)
            or reference.get("path") != relative_text
            or not isinstance(reference.get("sha256"), str)
        ):
            raise FinalPlanError(
                f"frozen plan derivation is missing {relative_text}"
            )
        path = resolve_repo_path(repo_root, relative)
        if not path.is_file() or path.is_symlink():
            raise FinalPlanError(
                f"frozen plan derivation is not a regular file: {relative_text}"
            )
        if sha256_path(path) != reference["sha256"]:
            raise FinalPlanError(
                f"frozen plan derivation hash mismatch: {relative_text}"
            )

    plan_path = resolve_repo_path(repo_root, PLAN_PATH)
    plan = load_json(plan_path)
    if not isinstance(plan, dict) or plan.get("artifact_type") != "execution_plan":
        raise FinalPlanError("frozen execution plan is not a final plan")
    if plan_path.read_bytes() != canonical_bytes(plan):
        raise FinalPlanError("frozen execution plan is not canonical JSON")
    expected = build_expected_plan(
        repo_root,
        verify_fixture_assembly=False,
    )
    if canonical_bytes(plan) != canonical_bytes(expected):
        raise FinalPlanError(
            "frozen execution plan differs from its no-input deterministic replay"
        )
    return {
        "case_ids": [case["case_id"] for case in plan["cases"]],
        "formal_input_executed": False,
        "formal_input_read": False,
        "formal_result_produced": False,
        "sha256": sha256_path(plan_path),
        "status": "frozen_plan_verified_without_formal_input",
    }


def verify(repo_root: Path) -> dict[str, Any]:
    repo_root = normalized_root(repo_root)
    path = resolve_repo_path(repo_root, PLAN_PATH)
    if not path.is_file() or path.is_symlink():
        raise FinalPlanError("final execution plan is missing or not regular")
    plan = load_json(path)
    if not isinstance(plan, dict) or plan.get("artifact_type") != "execution_plan":
        raise FinalPlanError("execution plan path does not contain a final plan")
    result = verify_plan_document(repo_root, plan)
    if path.read_bytes() != canonical_bytes(plan):
        raise FinalPlanError("final execution plan is not canonical JSON")
    result["sha256"] = sha256_path(path)
    return result


def write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink():
        raise FinalPlanError("execution plan parent must not be a symlink")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=".execution-plan.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        if not temporary.resolve().is_relative_to(path.parent.resolve()):
            raise FinalPlanError("temporary plan path escaped output directory")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def materialize(repo_root: Path) -> dict[str, Any]:
    repo_root = normalized_root(repo_root)
    path = resolve_repo_path(repo_root, PLAN_PATH)
    expected = build_expected_plan(repo_root)
    payload = canonical_bytes(expected)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file():
            raise FinalPlanError("refusing non-regular existing plan path")
        existing = load_json(path)
        if (
            isinstance(existing, dict)
            and existing.get("artifact_type") == "execution_plan"
        ):
            if path.read_bytes() != payload:
                raise FinalPlanError("refusing to overwrite a different final plan")
            return {
                "formal_input_executed": False,
                "formal_result_produced": False,
                "sha256": sha256_bytes(payload),
                "status": "already_materialized",
            }
        if (
            not isinstance(existing, dict)
            or existing.get("artifact_type") != "execution_plan_preparation"
        ):
            raise FinalPlanError("existing plan is not the replaceable preparation")
        registry, schemas = load_schema_registry(repo_root)
        validate_schema(
            existing,
            PREPARATION_SCHEMA_ID,
            registry,
            schemas,
            label="execution plan preparation",
        )
    write_atomic(path, payload)
    return {
        "formal_input_executed": False,
        "formal_result_produced": False,
        "sha256": sha256_bytes(payload),
        "status": "materialized",
    }


def expect_rejected(repo_root: Path, plan: dict[str, Any]) -> bool:
    try:
        verify_plan_document(repo_root, plan)
    except FinalPlanError:
        return True
    return False


def self_test(repo_root: Path) -> dict[str, Any]:
    repo_root = normalized_root(repo_root)
    production_path = resolve_repo_path(repo_root, PLAN_PATH)
    before_hash = sha256_path(production_path) if production_path.is_file() else None
    expected = build_expected_plan(repo_root)
    verify_plan_document(repo_root, expected)

    wrong_lock = copy.deepcopy(expected)
    wrong_lock["fixture_lock"]["sha256"] = "0" * 64
    extra_fixture = copy.deepcopy(expected)
    extra_fixture["cases"][0]["configurations"][0]["fixture_artifacts"].append(
        copy.deepcopy(
            extra_fixture["cases"][0]["configurations"][0]["fixture_artifacts"][0]
        )
    )
    wrong_negative = copy.deepcopy(expected)
    wrong_negative["cases"][3]["configurations"][0][
        "semantic_role"
    ] = "baseline"
    wrong_environment = copy.deepcopy(expected)
    wrong_environment["environments"][0]["version"] = "unlocked"
    r2_build_reads_formal_input = copy.deepcopy(expected)
    r2_build_reads_formal_input["cases"][1]["configurations"][0][
        "build_command"
    ].extend(
        [
            "-InputPath",
            EXECUTION_TARGET_PATHS["CA-R2"]["formal_input"],
        ]
    )
    missing_repetition_binding = copy.deepcopy(expected)
    missing_repetition_binding["cases"][0]["configurations"][0][
        "run_command"
    ].remove(REPETITION_INDEX_PLACEHOLDER)
    negative_reuses_positive_command = copy.deepcopy(expected)
    negative_reuses_positive_command["cases"][3]["configurations"][0][
        "run_command"
    ] = copy.deepcopy(
        negative_reuses_positive_command["cases"][2]["configurations"][0][
            "run_command"
        ]
    )
    output_root_drift = copy.deepcopy(expected)
    output_root_drift["cases"][0]["configurations"][0]["run_command"][
        output_root_drift["cases"][0]["configurations"][0]["run_command"].index(
            FORMAL_OUTPUT_ROOT
        )
    ] = FORMAL_OUTPUT_ROOT + r"\alternate"
    controls = {
        "fixture_lock_tamper": expect_rejected(repo_root, wrong_lock),
        "fixture_surface_pollution": expect_rejected(repo_root, extra_fixture),
        "negative_control_role": expect_rejected(repo_root, wrong_negative),
        "environment_drift": expect_rejected(repo_root, wrong_environment),
        "r2_pre_gate_formal_input_read": expect_rejected(
            repo_root,
            r2_build_reads_formal_input,
        ),
        "missing_repetition_binding": expect_rejected(
            repo_root,
            missing_repetition_binding,
        ),
        "negative_command_alias": expect_rejected(
            repo_root,
            negative_reuses_positive_command,
        ),
        "formal_output_root_drift": expect_rejected(
            repo_root,
            output_root_drift,
        ),
    }
    if not all(controls.values()):
        raise FinalPlanError("one or more final-plan negative controls failed")
    after_hash = sha256_path(production_path) if production_path.is_file() else None
    if before_hash != after_hash:
        raise FinalPlanError("self-test modified the production plan")
    return {
        "formal_input_executed": False,
        "formal_result_produced": False,
        "negative_controls": sorted(controls),
        "negative_controls_passed": len(controls),
        "plan_sha256": sha256_bytes(canonical_bytes(expected)),
        "production_plan_modified": False,
        "status": "synthetic_self_test_passed",
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("materialize", "verify", "self-test"):
        child = commands.add_parser(command)
        child.add_argument("--repo-root", required=True, type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "materialize":
            result = materialize(args.repo_root)
        elif args.command == "verify":
            result = verify(args.repo_root)
        else:
            result = self_test(args.repo_root)
    except (FinalPlanError, KeyError, TypeError, ValueError) as exc:
        print(
            json.dumps(
                {"error": str(exc), "status": "failed"},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
