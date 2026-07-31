#!/usr/bin/env python3
"""Synthetic Git-backed controls for formal-run-delta 0.1.0.

The fixture is a fake repository in the system temporary directory. No file in
the real runs/ namespace is read, and no runner or comparator is invoked.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from formal_run_delta_contract import (
    BASE_MANIFEST,
    BASE_RUN_ROOT,
    CANDIDATE_MANIFEST,
    CANDIDATE_RUN_ROOT,
    CORE_PATH,
    DELTA_ENTRY_PATH,
    DELTA_INSTANCE_PATH,
    DENYLIST_CONTRACT_PATH,
    DENYLIST_SCHEMA_PATH,
    FORBIDDEN_REUSE_FAMILIES,
    INVENTORY_ENTRY_PATH,
    INVENTORY_INSTANCE_PATH,
    INVENTORY_SCHEMA_ID,
    INVENTORY_SCHEMA_PATH,
    INVENTORY_TOOL_PATH,
    MANAGER_PATH,
    PREIMAGE_ENTRY_PATH,
    PROTECTED_DOMAINS,
    PROVENANCE_REFERENCE_ROLES,
    REVIEW_SCHEMA_ID,
    REVIEW_SCHEMA_PATH,
    REGISTRY_CONTRACT_PATH,
    REGISTRY_SCHEMA_PATH,
    RUNTIME_BINDING_ROLES,
    SCHEMA_ID,
    SCHEMA_PATH,
    TOOLS_DIR,
    TRUSTED_DENYLIST_CONTRACT_SHA256,
    TRUSTED_REGISTRY_SHA256,
    TRUSTED_SCHEMA_SHA256,
    VERSION_MATRIX,
    DeltaContractError,
    _fill_version_matrix,
    _load_frozen_manager,
    _load_inventory_contract,
    _load_required_component_registry,
    _reference_occurrences,
    _unresolved_global_base_endpoints,
    _validate_required_components,
    _validate_required_component_absences,
    _validate_required_component_relationships,
    canonical_bytes,
    canonical_value_bytes,
    materialize_document,
    prepare_semantic_review_packet,
    read_json_object,
    semantic_review_input_sha256,
    sha256_bytes,
    sha256_path,
    verify_delta,
    write_bytes_exclusive,
)


TOOLS = Path(__file__).resolve().parent
MATERIALIZER = TOOLS / "materialize-formal-run-delta-v0.1.0.py"
VERIFIER = TOOLS / "verify-formal-run-delta-v0.1.0.py"
DRAFT = "drafts/formal-run-delta.draft.json"
GENERIC_SCHEMA = (
    "research/calibration-tests/continuous-action-pilot/schema/"
    "synthetic-artifact-0.1.0.schema.json"
)

BATCH2_SCHEMA_PATHS = (
    "research/calibration-tests/continuous-action-pilot/schema/"
    "ca-r1-raw-trace-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "ca-r2-raw-trace-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "ca-r3-raw-trace-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-build-readiness-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-comparator-output-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-execution-permit-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-human-gate-authorization-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "stage1-cohort-lock-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "stage1-seat-dispatch-envelope-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/"
    "stage2-seat-dispatch-envelope-0.1.1.schema.json",
)
BATCH2_TARGET_CONTRACT_PATH = (
    "research/calibration-tests/continuous-action-pilot/tools/"
    "formal-execution-target-contract-v0.1.1.py"
)

BASE_COMPONENT_PATHS = {
    "blind_response_interface": "inputs/stage1-condition-v01.task.json",
    "prediction_contract_check": "source/projection-audit-v0.1.0.json",
    "prediction_participant_contract": None,
    "prediction_response_template": "inputs/prediction-response.template.json",
    "reconstruction_contract_check": None,
    "reconstruction_participant_contract": None,
    "reconstruction_response_template": (
        "inputs/reconstruction-response.template.json"
    ),
    "role_submission": "source/encoding-audit-v0.1.0.json",
    "submission_assembler": "inputs/generate-stage2-envelope-v0.1.0.py",
    "task_packet": "inputs/stage2-prediction.task.json",
}

EXPECTED_POSITIVE_IDS = (
    "P01_SCHEMA_AND_CANONICAL_BYTES",
    "P02_DETERMINISTIC_PREVIEW",
    "P03_REAL_GIT_BASE_A_B",
    "P04_PRE_COMMIT_A_SCOPE_ONLY",
    "P05_BIDIRECTIONAL_MANIFEST_CLOSURE",
    "P06_DELTA_PREIMAGE_ROOT_BINDING",
    "P07_STRUCTURED_SEMANTIC_REVIEWS",
    "P08_REPOSITORY_DENYLIST_SINGLE_SOURCE",
    "P09_DECODED_REFERENCE_ALLOWLIST",
    "P10_DERIVED_FORBIDDEN_REUSE",
    "P11_BASE_BYTES_READ_FROM_COMMIT_A",
    "P12_NO_FORMAL_EXECUTION",
    "P13_TWO_STAGE_REVIEW_INPUT",
    "P14_GLOBAL_BASE_ENDPOINT_REACHABLE",
    "P15_CONTAINER_EXCLUDED_FULL_PATH",
    "P16_AUDITED_EMPTY_DEPENDENCY_LEAF",
    "P17_ROUND_BOUND_011_COMPONENT_MATRIX",
)

EXPECTED_NEGATIVE_IDS = (
    "N-B01_BOM",
    "N-B02_INVALID_UTF8",
    "N-B03_CRLF",
    "N-B04_MISSING_FINAL_LF",
    "N-B05_NONCANONICAL",
    "N-B06_DUPLICATE_KEY",
    "N-B07_NONFINITE",
    "N-SCHEMA01_WEAKENED_SCHEMA",
    "N-SCHEMA02_WEAKENED_DENYLIST_SCHEMA",
    "N-SCHEMA03_WEAKENED_REVIEW_SCHEMA",
    "N-SCHEMA04_WEAKENED_INVENTORY_SCHEMA",
    "N-SCHEMA05_WEAKENED_REGISTRY_SCHEMA",
    "N-REGISTRY01_TAMPERED_CONTRACT",
    "N-REGISTRY02_UNRESOLVED_BLOCKS_COMMIT_A",
    "N-REGISTRY03_ABSENCE_PATTERN_MATCH",
    "N-REGISTRY04_CONTAINER_HASH_STATE",
    "N-REGISTRY05_SELF_DEPENDENCY",
    "N-REGISTRY06_DEPENDENCY_CYCLE",
    "N-REGISTRY07_PRE_GATE_DEPENDS_ON_POST_GATE",
    "N-REGISTRY08_UNRESOLVED_SCOPE_VIOLATION",
    "N-REGISTRY09_CLOSED_DEPENDS_ON_UNRESOLVED",
    "N-REGISTRY10_CONTAINER_DEPENDENCY_EDGE",
    "N-REGISTRY11_POST_GATE_FIELD_MISMATCH",
    "N-REGISTRY12_CONTAINER_FULL_PATH_PINNED",
    "N-INVENTORY01_WEAKENED_TOOL",
    "N-MANAGER01_WEAKENED_FREEZE_MANAGER",
    "N-BASE01_INVALID_A_B_PAIR",
    "N-HEAD01_OBSERVED_HEAD_DRIFT",
    "N-MANIFEST01_FROZEN_STATE",
    "N-MANIFEST02_PATH_TRAVERSAL",
    "N-MANIFEST03_CASEFOLD_COLLISION",
    "N-MANIFEST04_ARTIFACT_HASH_DRIFT",
    "N-DELTA01_NOT_REGISTERED",
    "N-DELTA02_REGISTERED_SHA_DRIFT",
    "N-C12_MANIFEST_ITEM_OMITTED_FROM_DELTA",
    "N-C13_DELTA_ITEM_OMITTED_FROM_MANIFEST",
    "N-PREIMAGE01_DELTA_LINE_MISSING",
    "N-PREIMAGE02_SELF_INCLUDED",
    "N-PREIMAGE03_NONCANONICAL_ORDER",
    "N-ROOT01_DIGEST_MISMATCH",
    "N-MATRIX01_DUPLICATE_COMPONENT",
    "N-MATRIX02_WRONG_VERSION",
    "N-REVIEW01_FAILED_DECISION",
    "N-REVIEW02_MISSING_CLAIM",
    "N-REVIEW03_INPUT_HASH_DRIFT",
    "N-REVIEW04_REUSED_REVIEWER",
    "N-INVENTORY02_TREE_MISMATCH",
    "N-INVENTORY03_PROTECTED_FINGERPRINT",
    "N-DENY01_EMPTY_GLOB_REWRITE",
    "N-DENY02_FORBIDDEN_TYPE_OUTSIDE_NAMESPACE",
    "N-DENY03_NESTED_DOT_GIT_NOT_EXEMPT",
    "N-DENY04_UTF16_FORBIDDEN_TYPE",
    "N-DENY05_UTF32_FORBIDDEN_TYPE",
    "N-DENY06_MODIFIED_TRACKED_CANDIDATE_SIGNATURE",
    "N-DENY07_TRACKED_EOL_NORMALIZATION",
    "N-R01_OLD_TOKEN_IN_GENERATOR",
    "N-R02_UNICODE_ESCAPE_BLOCKED",
    "N-R03_ALLOWLIST_OMISSION",
    "N-R04_RECORDED_SCAN_TAMPER",
    "N-REUSE01_RENAMED_BASE_BYTES",
    "N-REUSE02_BASE_TRUTH_COMMITMENT",
    "N-REUSE03_REBOUND_POST_GATE_PAYLOAD",
    "N-DESIGN01_PROTECTED_VALUE_CHANGED",
    "N-GATE01_POST_B_ATTESTATION_PRE_A",
    "N-PATH01_DRAFT_ESCAPE",
    "N-WRITE01_SHORT_WRITE_ROLLBACK",
    "N-WRITE02_PARTIAL_EXCEPTION_ROLLBACK",
    "N-CLI00_ISOLATED_INTERPRETER_REQUIRED",
    "N-CLI01_SYNTHETIC_PROFILE_REJECTED",
    "N-CLI02_REPOSITORY_BYTE_READ_ACK_REQUIRED",
    "N-CLI03_WRAPPER_CROSS_ROOT_REJECTED",
    "N-CLI04_PREPARE_REVIEW_FAILS_CLOSED",
    "N-CLI05_TAMPERED_CORE_NOT_IMPORTED",
    "N-B2-01_CROSS_ROUND_ARTIFACT_REFERENCE",
    "N-B2-02_ZERO_DIGEST",
    "N-B2-03_SEAT_PROMPT_SWAP",
    "N-B2-04_INCOMPLETE_DISPATCH_READBACK",
    "N-B2-05_R1_ARTIFACT_VERSION_FORBIDDEN",
    "N-B2-06_BUILD_READINESS_CROSS_ROUND_REFERENCE",
)


def repo_path(root: Path, relative: str) -> Path:
    return root / Path(*relative.split("/"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value.encode("utf-8"))


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(arguments)} failed: {result.stderr}"
        )
    return result.stdout.strip()


def command(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-B", "-I", *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
    )


def require_success(
    completed: subprocess.CompletedProcess[str],
    expected_status: str,
) -> dict[str, Any]:
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed: {completed.stderr or completed.stdout}"
        )
    value = json.loads(completed.stdout)
    if value.get("status") != expected_status:
        raise RuntimeError(
            f"expected {expected_status}, got {value!r}"
        )
    return value


def require_failure(
    function: Callable[[], None],
    code: str,
) -> None:
    try:
        function()
    except DeltaContractError as error:
        if error.code != code:
            raise RuntimeError(
                f"expected {code}, got {error.code}: {error}"
            ) from error
    else:
        raise RuntimeError(f"negative control unexpectedly passed: {code}")


def require_cli_failure(
    completed: subprocess.CompletedProcess[str],
    *,
    expected_fragment: str,
) -> dict[str, Any]:
    if completed.returncode == 0:
        raise RuntimeError(
            f"CLI negative control unexpectedly passed: {completed.stdout}"
        )
    try:
        value = json.loads(completed.stderr or completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "CLI negative control did not emit structured JSON: "
            f"{completed.stderr or completed.stdout}"
        ) from error
    if (
        value.get("status") != "failed_closed"
        or expected_fragment not in value.get("error", "")
    ):
        raise RuntimeError(
            f"CLI did not fail closed with {expected_fragment}: {value!r}"
        )
    return value


def _batch2_definition_validator(
    schema: dict[str, Any],
    definition: str,
) -> Draft202012Validator:
    return Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": schema["$defs"],
            "$ref": f"#/$defs/{definition}",
        }
    )


def _batch2_component_matrix_controls(
    actual_root: Path,
    positive: list[str],
    negative: list[str],
) -> None:
    schemas: dict[str, dict[str, Any]] = {}
    for relative in BATCH2_SCHEMA_PATHS:
        path = repo_path(actual_root, relative)
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf") or b"continuous-001" in raw:
            raise RuntimeError(f"Batch 2 Schema is not cleanly rebound: {relative}")
        schema = json.loads(raw.decode("utf-8"))
        Draft202012Validator.check_schema(schema)
        if not schema["$id"].endswith("/" + Path(relative).name):
            raise RuntimeError(f"Batch 2 Schema identity drifted: {relative}")
        schemas[Path(relative).name] = schema

    r1 = schemas["ca-r1-raw-trace-0.1.1.schema.json"]
    if (
        r1.get("additionalProperties") is not False
        or "artifact_version" in r1["properties"]
    ):
        raise RuntimeError(
            "CA-R1 must retain its versionless instance contract and reject "
            "undeclared artifact_version"
        )
    for name, schema in schemas.items():
        if name == "ca-r1-raw-trace-0.1.1.schema.json":
            continue
        artifact_version = schema.get("properties", {}).get(
            "artifact_version"
        )
        if artifact_version is None and {
            "receipt",
            "template",
        } <= set(schema.get("$defs", {})):
            version_values = {
                schema["$defs"][kind]["properties"]["artifact_version"]["const"]
                for kind in ("receipt", "template")
            }
            artifact_version = {"const": version_values.pop()} if (
                len(version_values) == 1
            ) else None
        if artifact_version != {"const": "0.1.1"}:
            raise RuntimeError(f"Batch 2 artifact version drifted: {name}")

    human_gate = schemas[
        "formal-human-gate-authorization-0.1.1.schema.json"
    ]
    required_human_gate = {
        "actor_dispatch_plan",
        "external_dispatch_attestation",
        "external_dispatch_attestation_observed_head",
        "external_dispatch_attestation_saved_commit",
        "external_dispatch_attestation_sequence",
        "finalize_commit_b",
        "formal_run_delta",
        "truth_continuity_attestation",
    }
    if not required_human_gate <= set(human_gate["required"]):
        raise RuntimeError("human-gate A/B and attestation closure is incomplete")
    required_contracts = {
        "formal_actor_dispatch_plan_materializer",
        "formal_actor_dispatch_plan_schema",
        "formal_actor_dispatch_plan_verifier",
        "formal_post_gate_absence_denylist",
        "formal_post_gate_absence_verifier",
        "formal_run_delta_verifier",
    }
    if not required_contracts <= set(
        human_gate["$defs"]["contractArtifacts"]["required"]
    ):
        raise RuntimeError("human-gate verifier contract closure is incomplete")

    for name in (
        "stage1-seat-dispatch-envelope-0.1.1.schema.json",
        "stage2-seat-dispatch-envelope-0.1.1.schema.json",
    ):
        receipt_required = set(
            schemas[name]["$defs"]["receipt"]["required"]
        )
        if not {
            "actor_dispatch_plan",
            "dispatch_prompt",
            "dispatch_transport",
        } <= receipt_required:
            raise RuntimeError(f"dispatch readback closure is incomplete: {name}")
    if "stage1_turn_audit" not in schemas[
        "stage1-cohort-lock-0.1.1.schema.json"
    ]["$defs"]["cohortMember"]["required"]:
        raise RuntimeError("stage-1 cohort lock omits the turn audit")
    if "finalize_commit_b" not in schemas[
        "formal-execution-permit-0.1.1.schema.json"
    ]["properties"]["authorization_lineage"]["required"]:
        raise RuntimeError("execution permit omits Commit B")

    readiness = schemas["formal-build-readiness-0.1.1.schema.json"]
    external_refs: list[str] = []

    def collect_external_refs(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if (
                    key == "$ref"
                    and isinstance(child, str)
                    and not child.startswith("#")
                ):
                    external_refs.append(child)
                collect_external_refs(child)
        elif isinstance(value, list):
            for child in value:
                collect_external_refs(child)

    collect_external_refs(readiness)
    if external_refs:
        raise RuntimeError(
            "build-only readiness unexpectedly imports task-packet closure"
        )

    target_path = repo_path(actual_root, BATCH2_TARGET_CONTRACT_PATH)
    target_raw = target_path.read_bytes()
    if (
        target_raw.startswith(b"\xef\xbb\xbf")
        or b"continuous-001" in target_raw
    ):
        raise RuntimeError("execution-target contract is not cleanly rebound")
    spec = importlib.util.spec_from_file_location(
        "game_primitives_formal_execution_target_contract_011",
        target_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load fixed-path execution-target contract")
    target_contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(target_contract)
    if (
        target_contract.CONTRACT_VERSION != "0.1.1"
        or target_contract.RUN_ID != "continuous-002"
        or set(target_contract.CASES) != {"CA-R1", "CA-R2", "CA-R3"}
    ):
        raise RuntimeError("execution-target contract identity drifted")

    execution_paths: list[str] = []
    raw_schema_paths: list[str] = []
    for case in target_contract.CASES:
        target = target_contract.EXECUTION_TARGET_PATHS[case]
        raw_schema_paths.append(target["raw_trace_schema"])
        for key, value in target.items():
            if key == "raw_trace_schema":
                continue
            if isinstance(value, str):
                execution_paths.append(value)
            elif isinstance(value, dict):
                execution_paths.extend(value.values())
    if (
        len(execution_paths) != 37
        or any(
            not path.startswith(
                "research/calibration-tests/continuous-action-pilot/"
                "runs/continuous-002/"
            )
            for path in execution_paths
        )
        or sorted(raw_schema_paths)
        != sorted(target_contract.RAW_TRACE_SCHEMA_PATHS.values())
        or any(not path.endswith("-0.1.1.schema.json") for path in raw_schema_paths)
    ):
        raise RuntimeError("execution-target path closure drifted")
    positive.append("P17_ROUND_BOUND_011_COMPONENT_MATRIX")

    stage1 = schemas["stage1-seat-dispatch-envelope-0.1.1.schema.json"]
    reference_validator = _batch2_definition_validator(
        stage1,
        "artifactReference",
    )
    current_reference = {
        "path": (
            "research/calibration-tests/continuous-action-pilot/"
            "runs/continuous-002/inputs/example.json"
        ),
        "sha256": "1" * 64,
    }
    if not reference_validator.is_valid(current_reference):
        raise RuntimeError("Batch 2 reference positive control is invalid")
    cross_round = copy.deepcopy(current_reference)
    cross_round["path"] = cross_round["path"].replace(
        "continuous-002",
        "continuous-001",
    )
    if reference_validator.is_valid(cross_round):
        raise RuntimeError("cross-round artifact reference was accepted")
    negative.append("N-B2-01_CROSS_ROUND_ARTIFACT_REFERENCE")

    zero_digest = copy.deepcopy(current_reference)
    zero_digest["sha256"] = "0" * 64
    if reference_validator.is_valid(zero_digest):
        raise RuntimeError("zero digest was accepted")
    negative.append("N-B2-02_ZERO_DIGEST")

    seat_prompt_validator = Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": stage1["$defs"],
            "additionalProperties": False,
            "allOf": [
                {"$ref": "#/$defs/seatConditionInvariant"},
            ],
            "properties": {
                "dispatch_prompt": {
                    "$ref": "#/$defs/dispatchPromptReference"
                },
                "seat_id": {
                    "type": "string"
                },
            },
            "required": [
                "dispatch_prompt",
                "seat_id",
            ],
            "type": "object",
        }
    )
    swapped_prompt = {
        "dispatch_prompt": {
            "path": (
                "research/calibration-tests/continuous-action-pilot/"
                "runs/continuous-002/inputs/dispatch/prompts/"
                "stage1-p02.prompt.txt"
            ),
            "sha256": "2" * 64,
        },
        "seat_id": "p01",
    }
    if seat_prompt_validator.is_valid(swapped_prompt):
        raise RuntimeError("cross-seat dispatch prompt was accepted")
    negative.append("N-B2-03_SEAT_PROMPT_SWAP")

    transfer_validator = _batch2_definition_validator(
        stage1,
        "dispatchTransferReceipt",
    )
    incomplete_transfer = {
        "dispatched_at": "2026-07-31T00:00:00Z",
        "external_task_id": "task-1",
        "external_thread_id": "thread-1",
        "submitted_utf8_sha256": "3" * 64,
    }
    if transfer_validator.is_valid(incomplete_transfer):
        raise RuntimeError("dispatch receipt without readback was accepted")
    negative.append("N-B2-04_INCOMPLETE_DISPATCH_READBACK")

    entry_template = {
        "after_action_frame": 0,
        "after_action_id": 0,
        "after_buffer_action_id": 0,
        "attack_held": 0,
        "before_action_frame": 0,
        "before_action_id": 0,
        "before_buffer_action_id": 0,
        "cancel_eligible_before": 0,
        "contact_count": 0,
        "event_id": "",
        "hit_count": 0,
        "input_down": 0,
        "input_value": 0,
        "sequence_index": 0,
    }
    r1_instance = {
        "artifact_type": "ca_r1_raw_trace",
        "case_id": "CA-R1",
        "configuration_id": "config.baseline",
        "controlled_value": 0,
        "execution_permit_id": "execution-permit.continuous-002",
        "execution_permit_path": (
            "research/calibration-tests/continuous-action-pilot/"
            "runs/continuous-002/execution/formal-execution-permit.json"
        ),
        "execution_permit_sha256": "4" * 64,
        "formal_input_id": "o.a.0002",
        "formal_input_path": (
            "research/calibration-tests/continuous-action-pilot/"
            "runs/continuous-002/fixtures/r1/"
            "footsies-r1-formal-input-v0.1.0.json"
        ),
        "formal_input_sha256": "5" * 64,
        "invariant_first_request_recognized": 1,
        "invariant_second_request_buffered": 1,
        "invariant_zero_contacts": 1,
        "invariant_zero_hits": 1,
        "prediction_set_digest": "6" * 64,
        "run_id": "continuous-002",
        "stop_boundary_id": "o.a.0042",
        "trace_entries": [],
    }
    for index in range(7):
        entry = copy.deepcopy(entry_template)
        entry["event_id"] = f"event.ca-r1.update-{index}"
        entry["sequence_index"] = index
        r1_instance["trace_entries"].append(entry)
    r1_validator = Draft202012Validator(r1)
    if not r1_validator.is_valid(r1_instance):
        raise RuntimeError("CA-R1 versionless positive control is invalid")
    r1_with_version = copy.deepcopy(r1_instance)
    r1_with_version["artifact_version"] = "0.1.1"
    if r1_validator.is_valid(r1_with_version):
        raise RuntimeError("CA-R1 accepted the forbidden artifact_version")
    negative.append("N-B2-05_R1_ARTIFACT_VERSION_FORBIDDEN")

    build_reference_validator = _batch2_definition_validator(
        readiness,
        "artifactReference",
    )
    old_build_reference = {
        "artifact_id": "old-build-evidence",
        "path": (
            "research/calibration-tests/continuous-action-pilot/"
            "runs/continuous-001/fixtures/build.json"
        ),
        "sha256": "7" * 64,
    }
    if build_reference_validator.is_valid(old_build_reference):
        raise RuntimeError("build readiness accepted a prior-round reference")
    negative.append("N-B2-06_BUILD_READINESS_CROSS_ROUND_REFERENCE")


def synthetic_preview(root: Path) -> dict[str, Any]:
    draft, _ = read_json_object(
        repo_path(root, DRAFT),
        require_canonical=True,
    )
    document = materialize_document(
        root,
        draft,
        output_path=repo_path(root, DELTA_INSTANCE_PATH),
        synthetic_test_profile=True,
    )
    raw = canonical_bytes(document)
    return {
        "sha256": sha256_bytes(raw),
        "status": "synthetic_previewed_unbound",
    }


def synthetic_materialize(root: Path) -> dict[str, Any]:
    output = repo_path(root, DELTA_INSTANCE_PATH)
    if output.exists():
        raise DeltaContractError(
            "OUTPUT_EXISTS",
            f"refusing to overwrite: {DELTA_INSTANCE_PATH}",
        )
    draft, _ = read_json_object(
        repo_path(root, DRAFT),
        require_canonical=True,
    )
    document = materialize_document(
        root,
        draft,
        output_path=output,
        synthetic_test_profile=True,
    )
    raw = canonical_bytes(document)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_exclusive(output, raw)
    return {
        "sha256": sha256_bytes(raw),
        "status": "synthetic_materialized_unbound",
    }


def synthetic_verify(root: Path) -> dict[str, Any]:
    _, raw, binding = verify_delta(
        root,
        repo_path(root, DELTA_INSTANCE_PATH),
        synthetic_test_profile=True,
    )
    return {
        "sha256": sha256_bytes(raw),
        "status": "synthetic_verified",
        "verified_binding": binding,
    }


def local_id(path: str) -> str:
    value = re.sub(r"[^a-z0-9._-]+", "-", path.casefold())
    return value.strip("-.")[:120]


def commitment(value: str) -> dict[str, Any]:
    return {
        "algorithm": "SHA-256",
        "combination": "secret_nonce_bytes || exact_truth_bundle_bytes",
        "commitment": value,
        "created_at": "2026-07-28T08:00:00Z",
        "nonce_length_bytes": 32,
        "truth_bundle_bytes": 128,
        "truth_bundle_name": "sealed-truth.json",
    }


def manifest_entry(
    *,
    artifact_id: str,
    path: str,
    sha256: str,
    schema_path: str,
    schema_sha256: str,
    artifact_kind: str = "source",
    artifact_version: str = "0.1.0",
    included: bool = True,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "artifact_version": artifact_version,
        "audience": ["custodian"],
        "decision_relevant": True,
        "included_in_frozen_set": included,
        "path": path,
        "release_stage": "preparation",
        "schema_path": schema_path,
        "schema_sha256": schema_sha256,
        "sha256": sha256,
        "supersedes_artifact_id": None,
    }


def preimage_bytes(manifest: dict[str, Any]) -> bytes:
    lines = [
        f"{entry['path']}\t{entry['sha256']}\n"
        for entry in manifest["artifacts"]
        if entry["included_in_frozen_set"]
    ]
    return "".join(sorted(lines)).encode("utf-8")


def bind_candidate(root: Path, delta_raw: bytes) -> None:
    manifest_path = repo_path(root, CANDIDATE_MANIFEST)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["artifacts"]:
        if entry["path"] == DELTA_ENTRY_PATH:
            entry["sha256"] = sha256_bytes(delta_raw)
    preimage = preimage_bytes(manifest)
    digest = sha256_bytes(preimage)
    for entry in manifest["artifacts"]:
        if entry["path"] == PREIMAGE_ENTRY_PATH:
            entry["sha256"] = digest
    manifest["frozen_artifact_set_digest"] = digest
    repo_path(
        root,
        f"{CANDIDATE_RUN_ROOT}/{PREIMAGE_ENTRY_PATH}",
    ).write_bytes(preimage)
    write_json(manifest_path, manifest)


def _copy_contract_files(root: Path, actual_root: Path) -> None:
    relative_files = [
        SCHEMA_PATH.as_posix(),
        DENYLIST_SCHEMA_PATH.as_posix(),
        DENYLIST_CONTRACT_PATH.as_posix(),
        REVIEW_SCHEMA_PATH.as_posix(),
        INVENTORY_SCHEMA_PATH.as_posix(),
        REGISTRY_SCHEMA_PATH.as_posix(),
        REGISTRY_CONTRACT_PATH.as_posix(),
        (
            "research/calibration-tests/continuous-action-pilot/schema/"
            "run-manifest-0.1.0.schema.json"
        ),
        (
            "research/calibration-tests/continuous-action-pilot/schema/"
            "run-manifest-0.1.1.schema.json"
        ),
        (
            "research/calibration-tests/continuous-action-pilot/schema/"
            "frozen-set-preimage-0.1.0.schema.json"
        ),
        MANAGER_PATH.as_posix(),
        INVENTORY_TOOL_PATH.as_posix(),
        (TOOLS_DIR / "verify-formal-readiness.py").as_posix(),
    ]
    for relative in relative_files:
        target = repo_path(root, relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_path(actual_root, relative), target)
    write_json(
        repo_path(root, GENERIC_SCHEMA),
        {
            "$id": "https://example.invalid/synthetic-artifact-0.1.0",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Synthetic artifact",
        },
    )


def _base_artifact_value(path: str) -> bytes:
    if path == "README.md":
        return b"# Synthetic base run\n"
    if path.endswith(".py"):
        return f"# synthetic {path}\n".encode("utf-8")
    if path.endswith(".md"):
        return f"# synthetic {path}\n".encode("utf-8")
    return canonical_bytes(
        {
            "artifact_type": "synthetic_base_artifact",
            "path": path,
            "run_id": "continuous-001",
        }
    )


def build_base(
    root: Path,
    actual_root: Path,
) -> dict[str, Any]:
    _copy_contract_files(root, actual_root)
    git(root, "init", "--quiet")
    git(root, "config", "user.email", "synthetic@example.invalid")
    git(root, "config", "user.name", "Synthetic Test")
    control_text = repo_path(root, "notes/control-plane.md")
    control_text.parent.mkdir(parents=True, exist_ok=True)
    control_text.write_bytes(
        b"Tracked protocol text may mention continuous-002 and truth_reveal "
        b"without being a runtime artifact.\n"
    )

    manager = _load_frozen_manager(actual_root)
    generic_hash = sha256_path(repo_path(root, GENERIC_SCHEMA))
    base_root = repo_path(root, BASE_RUN_ROOT)
    protected = {
        domain: f"stable:{domain}"
        for domain in PROTECTED_DOMAINS
    }
    values: dict[str, bytes] = {}
    for path in manager.REQUIRED_PATHS:
        if path == PREIMAGE_ENTRY_PATH:
            continue
        values[path] = _base_artifact_value(path)
    values["source/source-packet.json"] = canonical_bytes(protected)
    values["source/legacy-runtime-binding.json"] = canonical_bytes(
        {
            "artifact_type": "legacy_runtime_binding",
            "opaque_bytes": "must-not-be-reused",
        }
    )
    values["source/sealed-truth.json"] = canonical_bytes(
        {
            "artifact_type": "sealed_truth",
            "ciphertext": "base-only",
        }
    )
    for path, raw in values.items():
        target = base_root / Path(*path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    entries: list[dict[str, Any]] = []
    for path, raw in sorted(values.items()):
        kind = "source"
        version = "0.1.0"
        for component, component_path in BASE_COMPONENT_PATHS.items():
            if component_path == path:
                declared = VERSION_MATRIX[component]["base_version"]
                if declared is not None:
                    version = declared
        if path == "README.md":
            kind = "documentation"
        elif path == "source/legacy-runtime-binding.json":
            kind = "trace"
        elif path == "source/sealed-truth.json":
            kind = "truth"
        entries.append(
            manifest_entry(
                artifact_id=local_id(path),
                path=path,
                sha256=sha256_bytes(raw),
                schema_path=GENERIC_SCHEMA,
                schema_sha256=generic_hash,
                artifact_kind=kind,
                artifact_version=version,
            )
        )
    preimage_schema = (
        "research/calibration-tests/continuous-action-pilot/schema/"
        "frozen-set-preimage-0.1.0.schema.json"
    )
    entries.append(
        manifest_entry(
            artifact_id="frozen-set-preimage",
            path=PREIMAGE_ENTRY_PATH,
            sha256="0" * 64,
            schema_path=preimage_schema,
            schema_sha256=manager.PREIMAGE_SCHEMA_SHA256,
            artifact_kind="audit",
            included=False,
        )
    )
    manifest = {
        "$schema": manager.MANIFEST_SCHEMA_ID,
        "artifact_type": "formal_run_manifest",
        "artifact_version": "0.1.1",
        "artifacts": sorted(entries, key=lambda item: item["path"]),
        "created_at": "2026-07-28T08:00:00Z",
        "freeze_commit": None,
        "frozen_artifact_set_digest": None,
        "protocol_version": "0.1.0",
        "run_id": "continuous-001",
        "schema_version": "0.1.1",
        "stage": "preparation",
        "stage_digests": [],
        "status": "preparing",
        "truth_commitment": commitment("1" * 64),
        "updated_at": "2026-07-28T08:00:00Z",
    }
    preimage = preimage_bytes(manifest)
    root_digest = sha256_bytes(preimage)
    for entry in manifest["artifacts"]:
        if entry["path"] == PREIMAGE_ENTRY_PATH:
            entry["sha256"] = root_digest
    manifest["frozen_artifact_set_digest"] = root_digest
    (base_root / PREIMAGE_ENTRY_PATH).write_bytes(preimage)
    write_json(repo_path(root, BASE_MANIFEST), manifest)

    git(root, "add", "--all")
    git(root, "commit", "--quiet", "-m", "synthetic base commit A")
    anchor = git(root, "rev-parse", "HEAD")
    manifest["freeze_commit"] = anchor
    manifest["status"] = "frozen"
    manifest["updated_at"] = "2026-07-28T08:01:00Z"
    write_json(repo_path(root, BASE_MANIFEST), manifest)
    git(root, "add", BASE_MANIFEST)
    git(root, "commit", "--quiet", "-m", "synthetic base commit B")
    finalize = git(root, "rev-parse", "HEAD")

    # The synthetic base has a real third, direct-child completion commit so
    # delta binding can exercise the post-gate inventory without depending on
    # the real continuous-001 working tree or its payloads.
    post_gate_values = {
        "submissions/actors/p01.json": canonical_bytes(
            {
                "actor_identifier": "synthetic-old-actor",
                "artifact_type": "formal_actor_descriptor",
                "artifact_version": "0.1.0",
                "run_id": "continuous-001",
            }
        ),
        "submissions/raw/p01-stage1.json": canonical_bytes(
            {
                "artifact_type": "response_payload",
                "artifact_version": "0.1.0",
                "response": {"choice": "synthetic-old"},
                "run_id": "continuous-001",
            }
        ),
        "reports/README.md": b"# Synthetic completion report\n",
    }
    for relative, raw in post_gate_values.items():
        path = base_root / Path(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "-m", "synthetic base completion")
    completion = git(root, "rev-parse", "HEAD")

    inventory_module = _load_inventory_contract(actual_root)
    grouped: dict[str, list[dict[str, Any]]] = {
        family: [] for family in FORBIDDEN_REUSE_FAMILIES
    }
    for relative, raw in sorted(post_gate_values.items()):
        repository_path = f"{BASE_RUN_ROOT}/{relative}"
        family = inventory_module.classify_post_gate_path(repository_path)
        try:
            payload = inventory_module.strict_json_bytes(raw)
            canonical_digest = sha256_bytes(
                inventory_module.canonical_json_value_bytes(payload)
            )
            artifact_type = (
                payload.get("artifact_type")
                if isinstance(payload, dict)
                else None
            )
            artifact_version = (
                payload.get("artifact_version")
                if isinstance(payload, dict)
                else None
            )
            media_type = "application/json"
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            canonical_digest = sha256_bytes(raw)
            artifact_type = None
            artifact_version = None
            media_type = "text/plain"
        grouped[family].append(
            {
                "artifact_type": artifact_type,
                "artifact_version": artifact_version,
                "byte_length": len(raw),
                "byte_sha256": sha256_bytes(raw),
                "canonical_payload_sha256": canonical_digest,
                "git_blob_oid": git(
                    root,
                    "rev-parse",
                    f"{completion}:{repository_path}",
                ),
                "media_type": media_type,
                "path": repository_path,
                "protected_payload_fingerprint": (
                    inventory_module.protected_payload_fingerprint(raw)
                ),
            }
        )
    inventory = {
        "$schema": INVENTORY_SCHEMA_ID,
        "artifact_type": "base_post_run_completion_inventory",
        "artifact_version": "0.1.0",
        "base_completion_commit": completion,
        "base_finalize_commit": finalize,
        "base_freeze_commit": anchor,
        "base_frozen_artifact_set_digest": root_digest,
        "base_run_id": "continuous-001",
        "base_tree_oid": git(root, "rev-parse", f"{completion}^{{tree}}"),
        "classifier_profile": "continuous-action-post-run-v1",
        "families": [
            {
                "artifact_count": len(grouped[family]),
                "artifacts": sorted(
                    grouped[family],
                    key=lambda item: item["path"],
                ),
                "family_id": family,
                "state": "present" if grouped[family] else "absent",
            }
            for family in FORBIDDEN_REUSE_FAMILIES
        ],
        "formal_input_executed": False,
        "formal_result_created": False,
        "run_outcome": "invalid_before_prediction_set",
        "status": "passed",
        "unclassified_post_gate_paths": [],
    }
    inventory_module._validate_inventory_mechanics(inventory)
    return {
        "anchor": anchor,
        "base_manifest": manifest,
        "base_values": values,
        "completion": completion,
        "finalize": finalize,
        "generic_hash": generic_hash,
        "inventory": inventory,
        "manager": manager,
        "protected": protected,
        "root_digest": root_digest,
    }


def artifact_reference(
    path: str,
    version: str,
    sha256: str | None = None,
    *,
    manifest_artifact_id: str | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": version,
        "manifest_artifact_id": (
            manifest_artifact_id
            if manifest_artifact_id is not None
            else local_id(path)
        ),
        "path": path,
    }
    if sha256 is not None:
        value["sha256"] = sha256
    return value


def repository_artifact_reference(
    path: str,
    version: str,
    sha256: str,
) -> dict[str, Any]:
    return {
        "artifact_version": version,
        "path": path,
        "sha256": sha256,
    }


def make_change(
    *,
    artifact_id: str,
    role: str,
    candidate_path: str,
    candidate_version: str,
    base_path: str | None = None,
    base_version: str | None = None,
    kind: str,
    semantic: bool = False,
    semantic_scope: str = "none",
    participant_visible: bool = False,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "artifact_role": role,
        "base_artifact": (
            artifact_reference(
                base_path,
                base_version,
                manifest_artifact_id=local_id(
                    base_path[len(BASE_RUN_ROOT) + 1 :]
                ),
            )
            if base_path is not None and base_version is not None
            else None
        ),
        "candidate_artifact": artifact_reference(
            candidate_path,
            candidate_version,
            manifest_artifact_id=artifact_id,
        ),
        "change_kind": kind,
        "participant_visible": participant_visible,
        "rationale": f"synthetic delta for {artifact_id}",
        "reference_scope": (
            "runtime_binding"
            if role in RUNTIME_BINDING_ROLES
            else (
                "provenance_reference"
                if role in PROVENANCE_REFERENCE_ROLES
                else "none"
            )
        ),
        "research_design_impact": "none",
        "semantic_change": semantic,
        "semantic_change_scope": semantic_scope,
    }


def _fill_change_hashes(
    root: Path,
    anchor: str,
    changes: list[dict[str, Any]],
) -> None:
    for change in changes:
        base = change["base_artifact"]
        candidate = change["candidate_artifact"]
        if isinstance(base, dict):
            raw = subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "show",
                    f"{anchor}:{base['path']}",
                ],
                check=True,
                capture_output=True,
            ).stdout
            base["sha256"] = sha256_bytes(raw)
        if isinstance(candidate, dict):
            candidate["sha256"] = sha256_path(
                repo_path(root, candidate["path"])
            )


def candidate_kind(role: str) -> str:
    return {
        "adr": "documentation",
        "audit_record": "audit",
        "generator": "generator",
        "prompt": "source",
        "research_contract": "documentation",
        "submission_assembler": "generator",
        "task_packet": "task_packet",
    }.get(role, "source")


def build_candidate(
    root: Path,
    base: dict[str, Any],
) -> dict[str, Any]:
    run_root = repo_path(root, CANDIDATE_RUN_ROOT)
    component_paths: dict[str, str] = {}
    changes: list[dict[str, Any]] = []
    for component, expected in sorted(VERSION_MATRIX.items()):
        if expected["binding_kind"] != "artifact_change":
            continue
        suffix = "py" if component == "submission_assembler" else "json"
        candidate_relative = (
            f"inputs/{component}-v{expected['candidate_version']}.{suffix}"
        )
        candidate_repo = f"{CANDIDATE_RUN_ROOT}/{candidate_relative}"
        component_paths[component] = candidate_repo
        if suffix == "py":
            write_text(
                repo_path(root, candidate_repo),
                "# synthetic candidate assembler 0.1.1\n",
            )
        else:
            artifact_type = (
                "role_submission_schema_contract"
                if component == "role_submission"
                else component
            )
            write_json(
                repo_path(root, candidate_repo),
                {
                    "artifact_type": artifact_type,
                    "artifact_version": expected["candidate_version"],
                    "component_id": component,
                    "run_id": "continuous-002",
                },
            )
        base_relative = BASE_COMPONENT_PATHS[component]
        if base_relative is None:
            kind = "candidate_added"
            base_repo = None
            base_version = None
        else:
            base_repo = f"{BASE_RUN_ROOT}/{base_relative}"
            base_version = expected["base_version"]
            kind = (
                "run_rematerialized"
                if base_version == expected["candidate_version"]
                else "versioned_replacement"
            )
        changes.append(
            make_change(
                artifact_id=component,
                role=expected["role"],
                base_path=base_repo,
                base_version=base_version,
                candidate_path=candidate_repo,
                candidate_version=expected["candidate_version"],
                kind=kind,
                semantic=kind == "versioned_replacement",
                semantic_scope=(
                    "participant_interface"
                    if kind == "versioned_replacement"
                    else "none"
                ),
                participant_visible=expected["role"]
                in {
                    "participant_contract",
                    "participant_interface",
                    "prompt",
                    "task_packet",
                },
            )
        )

    protected_relative = "inputs/protected-design.json"
    protected_repo = f"{CANDIDATE_RUN_ROOT}/{protected_relative}"
    write_json(repo_path(root, protected_repo), base["protected"])
    changes.append(
        make_change(
            artifact_id="protected_design_source",
            role="source_note",
            base_path=f"{BASE_RUN_ROOT}/source/source-packet.json",
            base_version="0.1.0",
            candidate_path=protected_repo,
            candidate_version="0.1.0",
            kind="reused_unchanged",
        )
    )

    adr_relative = "source/delta-provenance.md"
    adr_repo = f"{CANDIDATE_RUN_ROOT}/{adr_relative}"
    write_text(
        repo_path(root, adr_repo),
        "基准 continuous-001；候选 continuous-002。\n",
    )
    changes.append(
        make_change(
            artifact_id="adr.delta",
            role="adr",
            candidate_path=adr_repo,
            candidate_version="0.1.0",
            kind="candidate_added",
        )
    )

    generator_relative = "inputs/runtime-generator.json"
    generator_repo = f"{CANDIDATE_RUN_ROOT}/{generator_relative}"
    write_json(
        repo_path(root, generator_repo),
        {
            "artifact_type": "synthetic_runtime_generator",
            "run_id": "continuous-002",
        },
    )
    changes.append(
        make_change(
            artifact_id="generator.runtime",
            role="generator",
            candidate_path=generator_repo,
            candidate_version="0.1.0",
            kind="candidate_added",
        )
    )

    inventory_repo = INVENTORY_INSTANCE_PATH
    write_json(repo_path(root, inventory_repo), base["inventory"])
    changes.append(
        make_change(
            artifact_id="inventory.base-post-run",
            role="audit_record",
            candidate_path=inventory_repo,
            candidate_version="0.1.0",
            kind="candidate_added",
        )
    )

    external_relative = (
        "inputs/external-dispatch-attestation-contract-v0.1.0.json"
    )
    external_repo = f"{CANDIDATE_RUN_ROOT}/{external_relative}"
    write_json(
        repo_path(root, external_repo),
        {
            "artifact_type": "external_dispatch_attestation_contract",
            "artifact_version": "0.1.0",
            "candidate_run_id": "continuous-002",
        },
    )
    changes.append(
        make_change(
            artifact_id="external.attestation.contract",
            role="research_contract",
            candidate_path=external_repo,
            candidate_version="0.1.0",
            kind="candidate_added",
        )
    )

    covered_base_paths = {
        change["base_artifact"]["path"]
        for change in changes
        if isinstance(change["base_artifact"], dict)
    }
    for entry in base["base_manifest"]["artifacts"]:
        if entry["included_in_frozen_set"] is not True:
            continue
        base_repo = f"{BASE_RUN_ROOT}/{entry['path']}"
        if base_repo in covered_base_paths:
            continue
        changes.append(
            {
                "artifact_id": f"retired.{entry['artifact_id']}",
                "artifact_role": "other",
                "base_artifact": artifact_reference(
                    base_repo,
                    entry["artifact_version"],
                    manifest_artifact_id=entry["artifact_id"],
                ),
                "candidate_artifact": None,
                "change_kind": "base_retired",
                "participant_visible": False,
                "rationale": (
                    "synthetic explicit retirement for full base closure"
                ),
                "reference_scope": "none",
                "research_design_impact": "none",
                "semantic_change": False,
                "semantic_change_scope": "none",
            }
        )

    _fill_change_hashes(root, base["anchor"], changes)
    protected_assertions = [
        {
            "base_source": {
                "extraction": "canonical_json_pointer",
                "path": f"{BASE_RUN_ROOT}/source/source-packet.json",
                "selector": f"/{domain}",
                "value_sha256": sha256_bytes(
                    canonical_value_bytes(base["protected"][domain])
                ),
            },
            "candidate_source": {
                "extraction": "canonical_json_pointer",
                "path": protected_repo,
                "selector": f"/{domain}",
                "value_sha256": sha256_bytes(
                    canonical_value_bytes(base["protected"][domain])
                ),
            },
            "domain": domain,
            "review_claims": [
                {
                    "claim_id": f"projection.{domain}",
                    "review_id": "projection",
                },
                {
                    "claim_id": f"source.{domain}",
                    "review_id": "source",
                },
            ],
            "unchanged": True,
        }
        for domain in PROTECTED_DOMAINS
    ]
    review_paths = {
        "projection": (
            f"{CANDIDATE_RUN_ROOT}/source/"
            "formal-run-delta-projection-review-v0.1.0.json"
        ),
        "source": (
            f"{CANDIDATE_RUN_ROOT}/source/"
            "formal-run-delta-source-review-v0.1.0.json"
        ),
    }
    draft: dict[str, Any] = {
        "$schema": SCHEMA_ID,
        "artifact_changes": changes,
        "artifact_type": "formal_run_delta",
        "artifact_version": "0.1.0",
        "audit": {
            "forbidden_reuse": "passed",
            "independent_semantic_review": "passed",
            "machine_diff_closure": "passed",
            "reference_scope": "passed",
            "repository_absence": "passed",
            "reviewed_at": "2026-07-28T08:10:00Z",
            "status": "passed",
        },
        "audit_phase": "pre_commit_a",
        "audited_at": "2026-07-28T08:10:00Z",
        "base_completion_inventory": artifact_reference(
            inventory_repo,
            "0.1.0",
            sha256_path(repo_path(root, inventory_repo)),
            manifest_artifact_id="inventory.base-post-run",
        ),
        "base_completion_inventory_digest": sha256_path(
            repo_path(root, inventory_repo)
        ),
        "base_run": {
            "completion_commit": base["completion"],
            "finalize_commit": base["finalize"],
            "freeze_commit": base["anchor"],
            "frozen_artifact_set_digest": base["root_digest"],
            "manifest_path": BASE_MANIFEST,
            "run_id": "continuous-001",
        },
        "candidate_run": {
            "commit_b_allowed_manifest_json_pointers": [
                "/freeze_commit",
                "/status",
                "/updated_at",
            ],
            "expected_post_b_status": "frozen",
            "freeze_commit_at_audit": None,
            "frozen_set_preimage_path": (
                f"{CANDIDATE_RUN_ROOT}/{PREIMAGE_ENTRY_PATH}"
            ),
            "manifest_path": CANDIDATE_MANIFEST,
            "manifest_schema_version": "0.1.1",
            "other_commit_b_changes_allowed": False,
            "post_b_frozen_artifact_changes_allowed": False,
            "run_id": "continuous-002",
            "status_at_audit": "preparing",
        },
        "delta_instance_path": DELTA_INSTANCE_PATH,
        "delta_scope": {
            "manifest_in_artifact_changes": False,
            "preimage_in_artifact_changes": False,
            "preimage_must_not_be_frozen_member": True,
            "self_in_artifact_changes": False,
            "self_must_be_frozen_member": True,
            "self_must_be_in_preimage": True,
        },
        "forbidden_reuse_evidence": [],
        "forbidden_reuse_family_summary": [
            {
                "artifact_count": family["artifact_count"],
                "family_id": family["family_id"],
                "state": family["state"],
            }
            for family in base["inventory"]["families"]
        ],
        "gate_policy": {
            "external_dispatch_attestation_contract": artifact_reference(
                external_repo,
                "0.1.0",
                sha256_path(repo_path(root, external_repo)),
                manifest_artifact_id="external.attestation.contract",
            ),
            "external_dispatch_attestation_instances_allowed": False,
            "external_dispatch_attestation_required_after_b": True,
        },
        "materialization_status": "materialized_unbound",
        "protected_design_assertions": protected_assertions,
        "protocol_transition": {
            "from": "0.1.0",
            "to": "0.1.1",
        },
        "reference_policy": {
            "provenance_occurrence_allowlist": [],
            "provenance_reference_roles": list(PROVENANCE_REFERENCE_ROLES),
            "runtime_binding_roles": list(RUNTIME_BINDING_ROLES),
        },
        "reference_scan": {
            "observed_occurrences": [],
            "status": "passed",
            "violations": [],
        },
        "required_component_registry": {
            "artifact_version": "0.1.0",
            "path": REGISTRY_CONTRACT_PATH.as_posix(),
            "sha256": TRUSTED_REGISTRY_SHA256,
        },
        "required_component_registry_digest": TRUSTED_REGISTRY_SHA256,
        "repository_absence": {
            "denylist_contract": repository_artifact_reference(
                DENYLIST_CONTRACT_PATH.as_posix(),
                "0.1.0",
                TRUSTED_DENYLIST_CONTRACT_SHA256,
            ),
            "matches": [],
            "observed_head": base["completion"],
            "repository_scope": (
                "candidate_namespace_plus_repository_path_and_binding_scan"
            ),
            "scan_snapshot_sha256": "0" * 64,
            "status": "passed",
        },
        "research_design_change": False,
        "semantic_reviews": {
            review_id: {
                "artifact": artifact_reference(
                    path,
                    "0.1.0",
                    "0" * 64,
                    manifest_artifact_id=f"review.{review_id}",
                ),
                "decision_pointer": "/decision",
                "input_set_sha256": "0" * 64,
                "required_decision": "passed",
                "review_id": review_id,
            }
            for review_id, path in review_paths.items()
        },
        "verification_scope": "pre_commit_a_only",
        "version_matrix": [],
    }
    _fill_version_matrix(
        draft,
        _load_required_component_registry(root, draft),
    )
    review_input = "0" * 64
    for review_id, review_kind in (
        ("projection", "projection_audit"),
        ("source", "source_audit"),
    ):
        review = {
            "$schema": REVIEW_SCHEMA_ID,
            "artifact_type": "formal_run_delta_semantic_review",
            "artifact_version": "0.1.0",
            "base_finalize_commit": base["finalize"],
            "base_freeze_commit": base["anchor"],
            "base_run_id": "continuous-001",
            "candidate_observed_head": base["completion"],
            "candidate_run_id": "continuous-002",
            "claims": [
                {
                    "claim_id": f"{review_id}.{domain}",
                    "decision": "passed",
                    "domain": domain,
                    "notes": f"synthetic {review_id} evidence",
                }
                for domain in PROTECTED_DOMAINS
            ],
            "decision": "passed",
            "input_set_sha256": review_input,
            "review_id": review_id,
            "review_kind": review_kind,
            "reviewed_at": "2026-07-28T08:09:00Z",
            "reviewer": {
                "identifier": f"{review_id}-reviewer",
                "role": "independent_semantic_reviewer",
                "session_id": f"{review_id}-session",
            },
        }
        write_json(repo_path(root, review_paths[review_id]), review)
        review_change = make_change(
            artifact_id=f"review.{review_id}",
            role="audit_record",
            candidate_path=review_paths[review_id],
            candidate_version="0.1.0",
            kind="candidate_added",
        )
        review_change["candidate_artifact"]["sha256"] = sha256_path(
            repo_path(root, review_paths[review_id])
        )
        changes.append(review_change)
        draft["semantic_reviews"][review_id]["artifact"]["sha256"] = (
            review_change["candidate_artifact"]["sha256"]
        )
        draft["semantic_reviews"][review_id][
            "input_set_sha256"
        ] = review_input

    # Rebind the list object after appending the review artifacts.
    draft["artifact_changes"] = changes
    generic_hash = base["generic_hash"]
    entries: list[dict[str, Any]] = []
    for change in changes:
        reference = change["candidate_artifact"]
        if not isinstance(reference, dict):
            continue
        relative = reference["path"][len(CANDIDATE_RUN_ROOT) + 1 :]
        if relative == INVENTORY_ENTRY_PATH:
            schema_path = INVENTORY_SCHEMA_PATH.as_posix()
            schema_hash = TRUSTED_SCHEMA_SHA256[schema_path]
        elif reference["path"] in review_paths.values():
            schema_path = REVIEW_SCHEMA_PATH.as_posix()
            schema_hash = TRUSTED_SCHEMA_SHA256[schema_path]
        else:
            schema_path = GENERIC_SCHEMA
            schema_hash = generic_hash
        entry = manifest_entry(
            artifact_id=change["artifact_id"],
            path=relative,
            sha256=reference["sha256"],
            schema_path=schema_path,
            schema_sha256=schema_hash,
            artifact_kind=candidate_kind(change["artifact_role"]),
            artifact_version=reference["artifact_version"],
        )
        if relative == INVENTORY_ENTRY_PATH:
            entry["audience"] = ["custodian", "public_after_reveal"]
        entries.append(entry)
    entries.append(
        {
            **manifest_entry(
                artifact_id="formal-run-delta",
                path=DELTA_ENTRY_PATH,
                sha256="0" * 64,
                schema_path=SCHEMA_PATH.as_posix(),
                schema_sha256=TRUSTED_SCHEMA_SHA256[
                    SCHEMA_PATH.as_posix()
                ],
                artifact_kind="audit",
            ),
            "audience": ["custodian", "public_after_reveal"],
        }
    )
    manager = base["manager"]
    entries.append(
        {
            **manifest_entry(
                artifact_id="frozen-set-preimage",
                path=PREIMAGE_ENTRY_PATH,
                sha256="0" * 64,
                schema_path=(
                    "research/calibration-tests/continuous-action-pilot/"
                    "schema/frozen-set-preimage-0.1.0.schema.json"
                ),
                schema_sha256=manager.PREIMAGE_SCHEMA_SHA256,
                artifact_kind="audit",
                included=False,
            ),
            "audience": ["custodian", "public_after_reveal"],
        }
    )
    manifest = {
        "$schema": manager.MANIFEST_SCHEMA_ID,
        "artifact_type": "formal_run_manifest",
        "artifact_version": "0.1.1",
        "artifacts": sorted(entries, key=lambda item: item["path"]),
        "created_at": "2026-07-28T08:05:00Z",
        "freeze_commit": None,
        "frozen_artifact_set_digest": None,
        "protocol_version": "0.1.1",
        "run_id": "continuous-002",
        "schema_version": "0.1.1",
        "stage": "preparation",
        "stage_digests": [],
        "status": "preparing",
        "truth_commitment": commitment("2" * 64),
        "updated_at": "2026-07-28T08:05:00Z",
    }
    # Review artifacts are appended after the draft skeleton is created, so
    # regenerate the registry-derived matrix before scanning references or
    # freezing the semantic-review input.
    _fill_version_matrix(
        draft,
        _load_required_component_registry(root, draft),
    )
    manifest_by_path = {
        entry["path"]: entry
        for entry in manifest["artifacts"]
    }
    draft["reference_policy"]["provenance_occurrence_allowlist"] = (
        _reference_occurrences(root, draft, manifest_by_path)
    )
    draft["reference_scan"] = {
        "observed_occurrences": draft["reference_policy"][
            "provenance_occurrence_allowlist"
        ],
        "status": "passed",
        "violations": [],
    }
    review_input = semantic_review_input_sha256(draft, manifest)
    for review_id, review_path in review_paths.items():
        path = repo_path(root, review_path)
        review = json.loads(path.read_text(encoding="utf-8"))
        review["input_set_sha256"] = review_input
        write_json(path, review)
        review_hash = sha256_path(path)
        for change in changes:
            if change["artifact_id"] == f"review.{review_id}":
                change["candidate_artifact"]["sha256"] = review_hash
        draft["semantic_reviews"][review_id]["artifact"]["sha256"] = (
            review_hash
        )
        draft["semantic_reviews"][review_id]["input_set_sha256"] = (
            review_input
        )
        for entry in manifest["artifacts"]:
            if entry["artifact_id"] == f"review.{review_id}":
                entry["sha256"] = review_hash
    write_json(repo_path(root, CANDIDATE_MANIFEST), manifest)
    write_json(repo_path(root, DRAFT), draft)
    return {
        "component_paths": component_paths,
        "denylist": DENYLIST_CONTRACT_PATH.as_posix(),
        "draft": draft,
        "external": external_repo,
        "generator": generator_repo,
        "inventory": inventory_repo,
        "manifest": manifest,
        "protected": protected_repo,
        "review_paths": review_paths,
    }


def verify_now(root: Path) -> None:
    verify_delta(
        root,
        repo_path(root, DELTA_INSTANCE_PATH),
        synthetic_test_profile=True,
    )


def _set_manifest_artifact_hash(
    manifest: dict[str, Any],
    repo_relative: str,
    sha256: str,
) -> None:
    relative = repo_relative[len(CANDIDATE_RUN_ROOT) + 1 :]
    matches = [
        entry
        for entry in manifest["artifacts"]
        if entry["path"] == relative
    ]
    if len(matches) != 1:
        raise RuntimeError(f"manifest entry not unique: {repo_relative}")
    matches[0]["sha256"] = sha256


def _set_document_artifact_hash(
    document: dict[str, Any],
    repo_relative: str,
    sha256: str,
) -> None:
    matches = 0
    for change in document["artifact_changes"]:
        reference = change["candidate_artifact"]
        if isinstance(reference, dict) and reference["path"] == repo_relative:
            reference["sha256"] = sha256
            matches += 1
    for reference in (
        document["base_completion_inventory"],
        document["repository_absence"]["denylist_contract"],
        document["gate_policy"]["external_dispatch_attestation_contract"],
        document["semantic_reviews"]["projection"]["artifact"],
        document["semantic_reviews"]["source"]["artifact"],
    ):
        if reference["path"] == repo_relative:
            reference["sha256"] = sha256
    if document["base_completion_inventory"]["path"] == repo_relative:
        document["base_completion_inventory_digest"] = sha256
    for row in document["version_matrix"]:
        if row["candidate_path"] == repo_relative:
            row["candidate_sha256"] = sha256
    if matches != 1:
        raise RuntimeError(f"delta change not unique: {repo_relative}")


def run_self_test(actual_root: Path) -> dict[str, Any]:
    positive: list[str] = []
    negative: list[str] = []
    with tempfile.TemporaryDirectory(
        prefix="gp-formal-run-delta-",
    ) as temporary:
        root = Path(temporary).resolve()
        base = build_base(root, actual_root)
        fixture = build_candidate(root, base)
        denylist_reference = fixture["draft"]["repository_absence"][
            "denylist_contract"
        ]
        if (
            denylist_reference
            != repository_artifact_reference(
                DENYLIST_CONTRACT_PATH.as_posix(),
                "0.1.0",
                TRUSTED_DENYLIST_CONTRACT_SHA256,
            )
            or any(
                isinstance(change["candidate_artifact"], dict)
                and change["candidate_artifact"]["path"]
                == DENYLIST_CONTRACT_PATH.as_posix()
                for change in fixture["draft"]["artifact_changes"]
            )
        ):
            raise RuntimeError(
                "denylist must have one repository-level source and no "
                "candidate artifact-change binding"
            )

        packet_a = prepare_semantic_review_packet(
            root,
            fixture["draft"],
            delta_output_path=repo_path(root, DELTA_INSTANCE_PATH),
            synthetic_test_profile=True,
        )
        packet_b = prepare_semantic_review_packet(
            root,
            fixture["draft"],
            delta_output_path=repo_path(root, DELTA_INSTANCE_PATH),
            synthetic_test_profile=True,
        )
        excluded_review_components = {
            "formal_run_delta_projection_review_instance",
            "formal_run_delta_source_review_instance",
        }
        if (
            canonical_bytes(packet_a) != canonical_bytes(packet_b)
            or packet_a["input_set_sha256"]
            != sha256_bytes(
                canonical_value_bytes(packet_a["input_set"])
            )
            or excluded_review_components
            & {
                row["component_id"]
                for row in packet_a["input_set"]["version_matrix"]
            }
        ):
            raise RuntimeError("two-stage review input is not deterministic")

        preview_a = synthetic_preview(root)
        preview_b = synthetic_preview(root)
        if preview_a["sha256"] != preview_b["sha256"]:
            raise RuntimeError("materializer preview is not deterministic")
        positive.extend(
            (
                "P01_SCHEMA_AND_CANONICAL_BYTES",
                "P02_DETERMINISTIC_PREVIEW",
            )
        )

        materialized = synthetic_materialize(root)
        delta_path = repo_path(root, DELTA_INSTANCE_PATH)
        unbound_raw = delta_path.read_bytes()
        bind_candidate(root, unbound_raw)
        verified = synthetic_verify(root)
        if materialized["sha256"] != verified["sha256"]:
            raise RuntimeError("materialized and verified delta hashes differ")
        binding = verified["verified_binding"]
        if (
            binding["base_finalize_commit"] != base["finalize"]
            or binding["candidate_status"] != "preparing"
            or binding["observed_head"] != base["completion"]
            or binding["trust_profile"] != "synthetic_test"
            or binding["verification_scope"] != "pre_commit_a_only"
            or binding["frozen_artifact_count"] < 12
        ):
            raise RuntimeError(f"verified binding is incomplete: {binding!r}")
        positive.extend(
            (
                "P03_REAL_GIT_BASE_A_B",
                "P04_PRE_COMMIT_A_SCOPE_ONLY",
                "P05_BIDIRECTIONAL_MANIFEST_CLOSURE",
                "P06_DELTA_PREIMAGE_ROOT_BINDING",
                "P07_STRUCTURED_SEMANTIC_REVIEWS",
                "P08_REPOSITORY_DENYLIST_SINGLE_SOURCE",
                "P09_DECODED_REFERENCE_ALLOWLIST",
                "P10_DERIVED_FORBIDDEN_REUSE",
            )
        )

        # Base evidence must come from Commit A, not mutable working-tree bytes.
        base_source = repo_path(
            root,
            f"{BASE_RUN_ROOT}/source/source-packet.json",
        )
        base_source_raw = base_source.read_bytes()
        base_source.write_bytes(base_source_raw + b" ")
        verify_now(root)
        base_source.write_bytes(base_source_raw)
        positive.extend(
            (
                "P11_BASE_BYTES_READ_FROM_COMMIT_A",
                "P12_NO_FORMAL_EXECUTION",
                "P13_TWO_STAGE_REVIEW_INPUT",
            )
        )
        endpoint_sha256 = "7" * 64
        endpoint_document = {
            "artifact_changes": [
                {
                    "artifact_id": "synthetic_reused_schema",
                    "base_artifact": {
                        "artifact_version": "0.1.0",
                        "path": "base/synthetic.schema.json",
                        "sha256": endpoint_sha256,
                    },
                    "candidate_artifact": {
                        "artifact_version": "0.1.0",
                        "path": "schema/synthetic.schema.json",
                        "sha256": endpoint_sha256,
                    },
                    "change_kind": "reused_unchanged",
                }
            ]
        }
        endpoint_registry = {
            "components": [
                {
                    "binding_kind": "global_git_bound",
                    "canonical_path": "schema/synthetic.schema.json",
                    "change_kind": "reused_unchanged",
                    "component_id": "synthetic_reused_schema",
                    "expected_sha256": endpoint_sha256,
                    "version": "0.1.0",
                }
            ]
        }
        if _unresolved_global_base_endpoints(
            endpoint_document,
            endpoint_registry,
        ):
            raise RuntimeError("valid global base endpoint remained blocked")
        positive.append("P14_GLOBAL_BASE_ENDPOINT_REACHABLE")

        container_root = root / "container-full-path"
        container_manifest = {"artifacts": []}
        container_manifest_path = repo_path(
            container_root,
            CANDIDATE_MANIFEST,
        )
        write_json(container_manifest_path, container_manifest)
        container_component = {
            "binding_kind": "container_excluded",
            "binding_scope": "container_excluded",
            "canonical_path": CANDIDATE_MANIFEST,
            "component_id": "candidate_run_manifest_instance",
            "component_kind": "manifest_container",
            "dependency_state": "not_applicable",
            "expected_absent_at_b": False,
            "expected_sha256": None,
            "hash_state": "container_excluded",
            "required_at_b": True,
        }
        container_registry = {"components": [container_component]}
        container_document = {"artifact_changes": []}
        _validate_required_components(
            container_root,
            container_document,
            container_registry,
            container_manifest,
            synthetic_test_profile=False,
        )
        positive.append("P15_CONTAINER_EXCLUDED_FULL_PATH")

        original_delta = delta_path.read_bytes()
        original_document = json.loads(original_delta.decode("utf-8"))
        manifest_path = repo_path(root, CANDIDATE_MANIFEST)
        preimage_path = repo_path(
            root,
            f"{CANDIDATE_RUN_ROOT}/{PREIMAGE_ENTRY_PATH}",
        )
        original_manifest = manifest_path.read_bytes()
        original_preimage = preimage_path.read_bytes()

        def restore_binding() -> None:
            delta_path.write_bytes(original_delta)
            manifest_path.write_bytes(original_manifest)
            preimage_path.write_bytes(original_preimage)

        def byte_failure(raw: bytes, code: str, test_id: str) -> None:
            delta_path.write_bytes(raw)
            require_failure(lambda: verify_now(root), code)
            negative.append(test_id)
            restore_binding()

        byte_failure(
            b"\xef\xbb\xbf" + original_delta,
            "BYTES_BOM",
            "N-B01_BOM",
        )
        byte_failure(
            b"\xff\n",
            "BYTES_INVALID_UTF8",
            "N-B02_INVALID_UTF8",
        )
        byte_failure(
            original_delta.replace(b"\n", b"\r\n"),
            "BYTES_NON_LF",
            "N-B03_CRLF",
        )
        byte_failure(
            original_delta.rstrip(b"\n"),
            "BYTES_FINAL_LF",
            "N-B04_MISSING_FINAL_LF",
        )
        byte_failure(
            original_delta + b"\n",
            "BYTES_NON_CANONICAL",
            "N-B05_NONCANONICAL",
        )
        byte_failure(
            (
                b'{"artifact_type":"formal_run_delta",'
                b'"artifact_type":"formal_run_delta"}\n'
            ),
            "JSON_DUPLICATE_KEY",
            "N-B06_DUPLICATE_KEY",
        )
        byte_failure(
            b'{"value":NaN}\n',
            "JSON_NONFINITE",
            "N-B07_NONFINITE",
        )

        schema_path = repo_path(root, SCHEMA_PATH.as_posix())
        schema_raw = schema_path.read_bytes()
        weakened = json.loads(schema_raw.decode("utf-8"))
        weakened["properties"]["research_design_change"]["const"] = True
        write_json(schema_path, weakened)
        require_failure(
            lambda: verify_now(root),
            "TRUSTED_SCHEMA_HASH_MISMATCH",
        )
        negative.append("N-SCHEMA01_WEAKENED_SCHEMA")
        schema_path.write_bytes(schema_raw)

        denylist_schema_path = repo_path(
            root,
            DENYLIST_SCHEMA_PATH.as_posix(),
        )
        denylist_schema_raw = denylist_schema_path.read_bytes()
        denylist_schema_path.write_bytes(denylist_schema_raw + b" ")
        manifest = json.loads(original_manifest.decode("utf-8"))
        weakened_hash = sha256_path(denylist_schema_path)
        for entry in manifest["artifacts"]:
            if entry["schema_path"] == DENYLIST_SCHEMA_PATH.as_posix():
                entry["schema_sha256"] = weakened_hash
        write_json(manifest_path, manifest)
        require_failure(
            lambda: verify_now(root),
            "TRUSTED_SCHEMA_HASH_MISMATCH",
        )
        negative.append("N-SCHEMA02_WEAKENED_DENYLIST_SCHEMA")
        denylist_schema_path.write_bytes(denylist_schema_raw)
        restore_binding()

        review_schema_path = repo_path(
            root,
            REVIEW_SCHEMA_PATH.as_posix(),
        )
        review_schema_raw = review_schema_path.read_bytes()
        review_schema_path.write_bytes(review_schema_raw + b" ")
        manifest = json.loads(original_manifest.decode("utf-8"))
        weakened_hash = sha256_path(review_schema_path)
        for entry in manifest["artifacts"]:
            if entry["schema_path"] == REVIEW_SCHEMA_PATH.as_posix():
                entry["schema_sha256"] = weakened_hash
        write_json(manifest_path, manifest)
        require_failure(
            lambda: verify_now(root),
            "TRUSTED_SCHEMA_HASH_MISMATCH",
        )
        negative.append("N-SCHEMA03_WEAKENED_REVIEW_SCHEMA")
        review_schema_path.write_bytes(review_schema_raw)
        restore_binding()

        inventory_schema_path = repo_path(
            root,
            INVENTORY_SCHEMA_PATH.as_posix(),
        )
        inventory_schema_raw = inventory_schema_path.read_bytes()
        inventory_schema_path.write_bytes(inventory_schema_raw + b" ")
        require_failure(
            lambda: verify_now(root),
            "TRUSTED_SCHEMA_HASH_MISMATCH",
        )
        negative.append("N-SCHEMA04_WEAKENED_INVENTORY_SCHEMA")
        inventory_schema_path.write_bytes(inventory_schema_raw)

        registry_schema_path = repo_path(
            root,
            REGISTRY_SCHEMA_PATH.as_posix(),
        )
        registry_schema_raw = registry_schema_path.read_bytes()
        registry_schema_path.write_bytes(registry_schema_raw + b" ")
        require_failure(
            lambda: verify_now(root),
            "TRUSTED_SCHEMA_HASH_MISMATCH",
        )
        negative.append("N-SCHEMA05_WEAKENED_REGISTRY_SCHEMA")
        registry_schema_path.write_bytes(registry_schema_raw)

        registry_path = repo_path(root, REGISTRY_CONTRACT_PATH.as_posix())
        registry_raw = registry_path.read_bytes()
        registry_path.write_bytes(registry_raw + b" ")
        require_failure(
            lambda: verify_now(root),
            "TRUSTED_REGISTRY_HASH_MISMATCH",
        )
        negative.append("N-REGISTRY01_TAMPERED_CONTRACT")
        registry_path.write_bytes(registry_raw)

        registry = _load_required_component_registry(
            root,
            original_document,
        )
        closed_leaf_registry = copy.deepcopy(registry)
        closed_leaf = next(
            component
            for component in closed_leaf_registry["components"]
            if component["component_id"] == "truth_continuity_attestation"
        )
        closed_leaf["allowed_dependency_component_ids"] = []
        closed_leaf["dependency_state"] = "closed"
        _validate_required_component_relationships(closed_leaf_registry)
        positive.append("P16_AUDITED_EMPTY_DEPENDENCY_LEAF")

        require_failure(
            lambda: _validate_required_components(
                root,
                original_document,
                registry,
                json.loads(original_manifest.decode("utf-8")),
                synthetic_test_profile=False,
            ),
            "REQUIRED_COMPONENTS_UNRESOLVED",
        )
        negative.append("N-REGISTRY02_UNRESOLVED_BLOCKS_COMMIT_A")

        absent_rogue = repo_path(
            root,
            (
                f"{CANDIDATE_RUN_ROOT}/submissions/actors/"
                "nested/unexpected-actor.json"
            ),
        )
        write_json(
            absent_rogue,
            {
                "artifact_type": "formal_actor_descriptor",
                "run_id": "continuous-002",
            },
        )
        try:
            require_failure(
                lambda: _validate_required_component_absences(
                    root,
                    registry,
                ),
                "REQUIRED_COMPONENT_PATTERN_COUNT",
            )
        finally:
            absent_rogue.unlink()
            absent_rogue.parent.rmdir()
            absent_rogue.parent.parent.rmdir()
            absent_rogue.parent.parent.parent.rmdir()
        negative.append("N-REGISTRY03_ABSENCE_PATTERN_MATCH")

        invalid_container_registry = copy.deepcopy(registry)
        invalid_container = next(
            component
            for component in invalid_container_registry["components"]
            if component["component_id"] == "candidate_run_manifest_instance"
        )
        invalid_container["hash_state"] = "unresolved_blocks_commit_a"
        require_failure(
            lambda: _validate_required_component_relationships(
                invalid_container_registry,
            ),
            "REQUIRED_COMPONENT_CONTAINER_HASH_STATE",
        )
        invalid_non_container_registry = copy.deepcopy(registry)
        invalid_non_container = next(
            component
            for component in invalid_non_container_registry["components"]
            if component["component_id"]
            == "formal_required_component_registry"
        )
        invalid_non_container["hash_state"] = "container_excluded"
        invalid_non_container["expected_sha256"] = None
        require_failure(
            lambda: _validate_required_component_relationships(
                invalid_non_container_registry,
            ),
            "REQUIRED_COMPONENT_CONTAINER_HASH_STATE",
        )
        negative.append("N-REGISTRY04_CONTAINER_HASH_STATE")

        self_dependency_registry = copy.deepcopy(registry)
        self_dependent = next(
            component
            for component in self_dependency_registry["components"]
            if component["component_id"]
            == "candidate_formal_build_readiness_instance"
        )
        self_dependent["allowed_dependency_component_ids"] = [
            self_dependent["component_id"],
        ]
        require_failure(
            lambda: _validate_required_component_relationships(
                self_dependency_registry,
            ),
            "REQUIRED_COMPONENT_DEPENDENCY_SELF_LOOP",
        )
        negative.append("N-REGISTRY05_SELF_DEPENDENCY")

        cyclic_registry = copy.deepcopy(registry)
        cyclic_by_id = {
            component["component_id"]: component
            for component in cyclic_registry["components"]
        }
        cyclic_by_id["candidate_formal_build_readiness_instance"][
            "allowed_dependency_component_ids"
        ] = ["candidate_fixture_lock_instance"]
        cyclic_by_id["candidate_fixture_lock_instance"][
            "allowed_dependency_component_ids"
        ] = ["candidate_formal_build_readiness_instance"]
        require_failure(
            lambda: _validate_required_component_relationships(
                cyclic_registry,
            ),
            "REQUIRED_COMPONENT_DEPENDENCY_CYCLE",
        )
        negative.append("N-REGISTRY06_DEPENDENCY_CYCLE")

        time_reversed_registry = copy.deepcopy(registry)
        pre_gate_component = next(
            component
            for component in time_reversed_registry["components"]
            if component["component_id"]
            == "candidate_formal_build_readiness_instance"
        )
        pre_gate_component["allowed_dependency_component_ids"] = [
            "external_dispatch_attestation_instance",
        ]
        require_failure(
            lambda: _validate_required_component_relationships(
                time_reversed_registry,
            ),
            "REQUIRED_COMPONENT_DEPENDENCY_TIME_ORDER",
        )
        negative.append("N-REGISTRY07_PRE_GATE_DEPENDS_ON_POST_GATE")

        unresolved_scope_registry = copy.deepcopy(registry)
        runtime_component = next(
            component
            for component in unresolved_scope_registry["components"]
            if component["component_id"]
            == "candidate_formal_build_readiness_instance"
        )
        runtime_component["allowed_dependency_component_ids"] = [
            "formal_required_component_registry",
        ]
        require_failure(
            lambda: _validate_required_component_relationships(
                unresolved_scope_registry,
            ),
            "RUNTIME_DEPENDENCY_SCOPE_VIOLATION",
        )
        negative.append("N-REGISTRY08_UNRESOLVED_SCOPE_VIOLATION")

        unresolved_target_registry = copy.deepcopy(registry)
        closed_component = next(
            component
            for component in unresolved_target_registry["components"]
            if component["component_id"]
            == "base_post_run_inventory_tool"
        )
        closed_component["allowed_dependency_component_ids"] = [
            "candidate_formal_build_readiness_instance",
        ]
        require_failure(
            lambda: _validate_required_component_relationships(
                unresolved_target_registry,
            ),
            "REQUIRED_COMPONENT_DEPENDENCY_TARGET_UNRESOLVED",
        )
        negative.append("N-REGISTRY09_CLOSED_DEPENDS_ON_UNRESOLVED")

        container_edge_registry = copy.deepcopy(registry)
        container_dependent = next(
            component
            for component in container_edge_registry["components"]
            if component["component_id"]
            == "candidate_formal_build_readiness_instance"
        )
        container_dependent["allowed_dependency_component_ids"] = [
            "candidate_run_manifest_instance",
        ]
        require_failure(
            lambda: _validate_required_component_relationships(
                container_edge_registry,
            ),
            "REQUIRED_COMPONENT_CONTAINER_DEPENDENCY",
        )
        container_outbound_registry = copy.deepcopy(registry)
        manifest_container = next(
            component
            for component in container_outbound_registry["components"]
            if component["component_id"] == "candidate_run_manifest_instance"
        )
        manifest_container["allowed_dependency_component_ids"] = [
            "formal_required_component_registry",
        ]
        require_failure(
            lambda: _validate_required_component_relationships(
                container_outbound_registry,
            ),
            "REQUIRED_COMPONENT_CONTAINER_DEPENDENCY",
        )
        negative.append("N-REGISTRY10_CONTAINER_DEPENDENCY_EDGE")

        inconsistent_post_gate_registry = copy.deepcopy(registry)
        post_gate_component = next(
            component
            for component in inconsistent_post_gate_registry["components"]
            if component["component_id"]
            == "external_dispatch_attestation_instance"
        )
        post_gate_component["hash_state"] = "unresolved_blocks_commit_a"
        require_failure(
            lambda: _validate_required_component_relationships(
                inconsistent_post_gate_registry,
            ),
            "REQUIRED_COMPONENT_POST_GATE_STATE",
        )
        invalid_post_gate_scope_registry = copy.deepcopy(registry)
        invalid_post_gate_scope = next(
            component
            for component in invalid_post_gate_scope_registry["components"]
            if component["component_id"]
            == "external_dispatch_attestation_instance"
        )
        invalid_post_gate_scope["binding_scope"] = "none"
        require_failure(
            lambda: _validate_required_component_relationships(
                invalid_post_gate_scope_registry,
            ),
            "REQUIRED_COMPONENT_POST_GATE_STATE",
        )
        negative.append("N-REGISTRY11_POST_GATE_FIELD_MISMATCH")

        pinned_container_component = copy.deepcopy(container_component)
        pinned_container_component["hash_state"] = "pinned"
        pinned_container_component["expected_sha256"] = sha256_path(
            container_manifest_path
        )
        require_failure(
            lambda: _validate_required_components(
                container_root,
                container_document,
                {"components": [pinned_container_component]},
                container_manifest,
                synthetic_test_profile=False,
            ),
            "REQUIRED_COMPONENT_CONTAINER_HASH_STATE",
        )
        negative.append("N-REGISTRY12_CONTAINER_FULL_PATH_PINNED")

        inventory_tool_path = repo_path(
            root,
            INVENTORY_TOOL_PATH.as_posix(),
        )
        inventory_tool_raw = inventory_tool_path.read_bytes()
        inventory_tool_path.write_bytes(inventory_tool_raw + b" ")
        require_failure(
            lambda: verify_now(root),
            "TRUSTED_INVENTORY_TOOL_HASH_MISMATCH",
        )
        negative.append("N-INVENTORY01_WEAKENED_TOOL")
        inventory_tool_path.write_bytes(inventory_tool_raw)

        manager_path = repo_path(root, MANAGER_PATH.as_posix())
        manager_raw = manager_path.read_bytes()
        manager_path.write_bytes(manager_raw + b" ")
        require_failure(
            lambda: verify_now(root),
            "TRUSTED_MANAGER_HASH_MISMATCH",
        )
        negative.append("N-MANAGER01_WEAKENED_FREEZE_MANAGER")
        manager_path.write_bytes(manager_raw)

        def document_failure(
            mutate: Callable[[dict[str, Any]], None],
            code: str,
            test_id: str,
            *,
            rebind: bool = False,
            refresh_semantic_reviews: bool = False,
        ) -> None:
            changed = copy.deepcopy(original_document)
            mutate(changed)
            saved_reviews: dict[str, bytes] = {}
            if refresh_semantic_reviews:
                manifest = json.loads(original_manifest.decode("utf-8"))
                saved_reviews = refresh_review_bindings(
                    changed,
                    manifest,
                )
                write_json(manifest_path, manifest)
                rebind = True
            delta_path.write_bytes(canonical_bytes(changed))
            if rebind:
                bind_candidate(root, delta_path.read_bytes())
            require_failure(lambda: verify_now(root), code)
            negative.append(test_id)
            for review_relative, review_raw in saved_reviews.items():
                repo_path(root, review_relative).write_bytes(review_raw)
            restore_binding()

        document_failure(
            lambda value: value["base_run"].update(
                {"finalize_commit": base["anchor"]}
            ),
            "BASE_FREEZE_PAIR_INVALID",
            "N-BASE01_INVALID_A_B_PAIR",
        )
        document_failure(
            lambda value: value["repository_absence"].update(
                {"observed_head": "f" * 40}
            ),
            "OBSERVED_HEAD_MISMATCH",
            "N-HEAD01_OBSERVED_HEAD_DRIFT",
            rebind=True,
        )

        manifest = json.loads(original_manifest.decode("utf-8"))
        manifest["freeze_commit"] = base["anchor"]
        manifest["status"] = "frozen"
        write_json(manifest_path, manifest)
        require_failure(
            lambda: verify_now(root),
            "CANDIDATE_STATE_INVALID",
        )
        negative.append("N-MANIFEST01_FROZEN_STATE")
        restore_binding()

        manifest = json.loads(original_manifest.decode("utf-8"))
        escaped = copy.deepcopy(manifest["artifacts"][0])
        escaped["artifact_id"] = "escape"
        escaped["path"] = "../escape.json"
        manifest["artifacts"].append(escaped)
        write_json(manifest_path, manifest)
        require_failure(
            lambda: verify_now(root),
            "CANDIDATE_MANIFEST_SCHEMA_INVALID",
        )
        negative.append("N-MANIFEST02_PATH_TRAVERSAL")
        restore_binding()

        manifest = json.loads(original_manifest.decode("utf-8"))
        collision = copy.deepcopy(manifest["artifacts"][0])
        collision["artifact_id"] = "casefold-collision"
        directory, filename = collision["path"].rsplit("/", 1)
        collision["path"] = f"{directory}/{filename.swapcase()}"
        manifest["artifacts"].append(collision)
        write_json(manifest_path, manifest)
        require_failure(
            lambda: verify_now(root),
            "MANIFEST_PATH_CASE_COLLISION",
        )
        negative.append("N-MANIFEST03_CASEFOLD_COLLISION")
        restore_binding()

        generator_path = repo_path(root, fixture["generator"])
        generator_raw = generator_path.read_bytes()
        generator_path.write_bytes(generator_raw + b" ")
        require_failure(
            lambda: verify_now(root),
            "ARTIFACT_HASH_MISMATCH",
        )
        negative.append("N-MANIFEST04_ARTIFACT_HASH_DRIFT")
        generator_path.write_bytes(generator_raw)
        restore_binding()

        manifest = json.loads(original_manifest.decode("utf-8"))
        manifest["artifacts"] = [
            entry
            for entry in manifest["artifacts"]
            if entry["path"] != DELTA_ENTRY_PATH
        ]
        write_json(manifest_path, manifest)
        require_failure(lambda: verify_now(root), "DELTA_NOT_REGISTERED")
        negative.append("N-DELTA01_NOT_REGISTERED")
        restore_binding()

        manifest = json.loads(original_manifest.decode("utf-8"))
        for entry in manifest["artifacts"]:
            if entry["path"] == DELTA_ENTRY_PATH:
                entry["sha256"] = "0" * 64
        preimage = preimage_bytes(manifest)
        digest = sha256_bytes(preimage)
        for entry in manifest["artifacts"]:
            if entry["path"] == PREIMAGE_ENTRY_PATH:
                entry["sha256"] = digest
        manifest["frozen_artifact_set_digest"] = digest
        preimage_path.write_bytes(preimage)
        write_json(manifest_path, manifest)
        require_failure(lambda: verify_now(root), "DELTA_SHA_MISMATCH")
        negative.append("N-DELTA02_REGISTERED_SHA_DRIFT")
        restore_binding()

        extra_relative = "inputs/undeclared-frozen.json"
        extra_path = repo_path(
            root,
            f"{CANDIDATE_RUN_ROOT}/{extra_relative}",
        )
        write_json(extra_path, {"artifact_type": "benign_extra"})
        manifest = json.loads(original_manifest.decode("utf-8"))
        manifest["artifacts"].append(
            manifest_entry(
                artifact_id="undeclared-frozen",
                path=extra_relative,
                sha256=sha256_path(extra_path),
                schema_path=GENERIC_SCHEMA,
                schema_sha256=base["generic_hash"],
            )
        )
        preimage = preimage_bytes(manifest)
        digest = sha256_bytes(preimage)
        for entry in manifest["artifacts"]:
            if entry["path"] == PREIMAGE_ENTRY_PATH:
                entry["sha256"] = digest
        manifest["frozen_artifact_set_digest"] = digest
        preimage_path.write_bytes(preimage)
        write_json(manifest_path, manifest)
        require_failure(
            lambda: verify_now(root),
            "CLOSURE_REVERSE_MISSING",
        )
        negative.append("N-C12_MANIFEST_ITEM_OMITTED_FROM_DELTA")
        extra_path.unlink()
        restore_binding()

        manifest = json.loads(original_manifest.decode("utf-8"))
        generator_relative = fixture["generator"][
            len(CANDIDATE_RUN_ROOT) + 1 :
        ]
        manifest["artifacts"] = [
            entry
            for entry in manifest["artifacts"]
            if entry["path"] != generator_relative
        ]
        write_json(manifest_path, manifest)
        require_failure(
            lambda: verify_now(root),
            "MANIFEST_UNREGISTERED_FILE",
        )
        negative.append("N-C13_DELTA_ITEM_OMITTED_FROM_MANIFEST")
        restore_binding()

        def bad_preimage(raw: bytes, test_id: str) -> None:
            manifest = json.loads(original_manifest.decode("utf-8"))
            digest = sha256_bytes(raw)
            for entry in manifest["artifacts"]:
                if entry["path"] == PREIMAGE_ENTRY_PATH:
                    entry["sha256"] = digest
            manifest["frozen_artifact_set_digest"] = digest
            preimage_path.write_bytes(raw)
            write_json(manifest_path, manifest)
            require_failure(
                lambda: verify_now(root),
                "PREIMAGE_BYTES_NONCANONICAL",
            )
            negative.append(test_id)
            restore_binding()

        delta_line = next(
            line
            for line in original_preimage.splitlines(keepends=True)
            if line.startswith(DELTA_ENTRY_PATH.encode("utf-8") + b"\t")
        )
        bad_preimage(
            original_preimage.replace(delta_line, b""),
            "N-PREIMAGE01_DELTA_LINE_MISSING",
        )
        bad_preimage(
            original_preimage
            + f"{PREIMAGE_ENTRY_PATH}\t{'a' * 64}\n".encode("utf-8"),
            "N-PREIMAGE02_SELF_INCLUDED",
        )
        bad_preimage(
            b"".join(reversed(original_preimage.splitlines(keepends=True))),
            "N-PREIMAGE03_NONCANONICAL_ORDER",
        )

        manifest = json.loads(original_manifest.decode("utf-8"))
        manifest["frozen_artifact_set_digest"] = "f" * 64
        write_json(manifest_path, manifest)
        require_failure(lambda: verify_now(root), "FROZEN_ROOT_MISMATCH")
        negative.append("N-ROOT01_DIGEST_MISMATCH")
        restore_binding()

        document_failure(
            lambda value: value["version_matrix"].__setitem__(
                1,
                copy.deepcopy(value["version_matrix"][0]),
            ),
            "VERSION_MATRIX_COVERAGE",
            "N-MATRIX01_DUPLICATE_COMPONENT",
        )
        document_failure(
            lambda value: value["version_matrix"][0].update(
                {"candidate_version": "9.9.9"}
            ),
            "VERSION_MATRIX_VERSION",
            "N-MATRIX02_WRONG_VERSION",
        )

        def refresh_review_bindings(
            document: dict[str, Any],
            manifest: dict[str, Any],
        ) -> dict[str, bytes]:
            review_input = semantic_review_input_sha256(
                document,
                manifest,
            )
            saved: dict[str, bytes] = {}
            for review_id, repo_relative in fixture["review_paths"].items():
                path = repo_path(root, repo_relative)
                raw = path.read_bytes()
                saved[repo_relative] = raw
                value = json.loads(raw.decode("utf-8"))
                value["input_set_sha256"] = review_input
                write_json(path, value)
                digest = sha256_path(path)
                _set_document_artifact_hash(
                    document,
                    repo_relative,
                    digest,
                )
                _set_manifest_artifact_hash(
                    manifest,
                    repo_relative,
                    digest,
                )
                document["semantic_reviews"][review_id][
                    "input_set_sha256"
                ] = review_input
            return saved

        def candidate_json_failure(
            repo_relative: str,
            mutate: Callable[[dict[str, Any]], None],
            code: str,
            test_id: str,
            *,
            refresh_semantic_reviews: bool = False,
        ) -> None:
            path = repo_path(root, repo_relative)
            original_raw = path.read_bytes()
            value = json.loads(original_raw.decode("utf-8"))
            mutate(value)
            write_json(path, value)
            changed_raw = path.read_bytes()
            document = copy.deepcopy(original_document)
            manifest = json.loads(original_manifest.decode("utf-8"))
            digest = sha256_bytes(changed_raw)
            _set_document_artifact_hash(document, repo_relative, digest)
            _set_manifest_artifact_hash(manifest, repo_relative, digest)
            saved_reviews: dict[str, bytes] = {}
            if refresh_semantic_reviews:
                saved_reviews = refresh_review_bindings(
                    document,
                    manifest,
                )
            delta_path.write_bytes(canonical_bytes(document))
            write_json(manifest_path, manifest)
            bind_candidate(root, delta_path.read_bytes())
            require_failure(lambda: verify_now(root), code)
            negative.append(test_id)
            path.write_bytes(original_raw)
            for review_relative, review_raw in saved_reviews.items():
                repo_path(root, review_relative).write_bytes(review_raw)
            restore_binding()

        source_review = fixture["review_paths"]["source"]
        candidate_json_failure(
            source_review,
            lambda value: value.update({"decision": "failed"}),
            "REVIEW_DECISION_FAILED",
            "N-REVIEW01_FAILED_DECISION",
        )
        candidate_json_failure(
            source_review,
            lambda value: value["claims"].__setitem__(
                -1,
                copy.deepcopy(value["claims"][0]),
            ),
            "REVIEW_CLAIM_COVERAGE",
            "N-REVIEW02_MISSING_CLAIM",
        )
        candidate_json_failure(
            source_review,
            lambda value: value.update({"input_set_sha256": "f" * 64}),
            "REVIEW_INPUT_HASH_MISMATCH",
            "N-REVIEW03_INPUT_HASH_DRIFT",
        )
        candidate_json_failure(
            fixture["review_paths"]["projection"],
            lambda value: value.update(
                {
                    "reviewer": {
                        "identifier": "source-reviewer",
                        "role": "independent_semantic_reviewer",
                        "session_id": "source-session",
                    }
                }
            ),
            "REVIEWER_NOT_INDEPENDENT",
            "N-REVIEW04_REUSED_REVIEWER",
        )

        candidate_json_failure(
            fixture["inventory"],
            lambda value: value.update({"base_tree_oid": "f" * 40}),
            "BASE_INVENTORY_TREE_MISMATCH",
            "N-INVENTORY02_TREE_MISMATCH",
            refresh_semantic_reviews=True,
        )
        candidate_json_failure(
            fixture["inventory"],
            lambda value: value["families"][0]["artifacts"][0].update(
                {"protected_payload_fingerprint": "f" * 64}
            ),
            "BASE_INVENTORY_ARTIFACT_MISMATCH",
            "N-INVENTORY03_PROTECTED_FINGERPRINT",
            refresh_semantic_reviews=True,
        )

        denylist_path = repo_path(root, fixture["denylist"])
        denylist_raw = denylist_path.read_bytes()
        denylist_value = json.loads(denylist_raw.decode("utf-8"))
        for rule in denylist_value["rules"]:
            rule["path_patterns"] = ["never/matches/*.json"]
        write_json(denylist_path, denylist_value)
        require_failure(
            lambda: verify_now(root),
            "DENYLIST_CONTRACT_HASH_MISMATCH",
        )
        negative.append("N-DENY01_EMPTY_GLOB_REWRITE")
        denylist_path.write_bytes(denylist_raw)
        restore_binding()

        rogue = repo_path(root, "misc/candidate-bound-result.json")
        write_json(
            rogue,
            {
                "artifact_type": "execution_result",
                "run_id": "continuous-002",
            },
        )
        require_failure(lambda: verify_now(root), "ABSENCE_MATCH")
        negative.append("N-DENY02_FORBIDDEN_TYPE_OUTSIDE_NAMESPACE")
        rogue.unlink()
        rogue.parent.rmdir()
        restore_binding()

        nested_git = repo_path(
            root,
            "ordinary/.git/continuous-002/reveal/truth-reveal.json",
        )
        write_json(
            nested_git,
            {"artifact_type": "synthetic_renamed_payload"},
        )
        require_failure(lambda: verify_now(root), "ABSENCE_MATCH")
        negative.append("N-DENY03_NESTED_DOT_GIT_NOT_EXEMPT")
        shutil.rmtree(repo_path(root, "ordinary"))
        restore_binding()

        utf16_rogue = repo_path(root, "misc/utf16-result.json")
        utf16_rogue.parent.mkdir(parents=True, exist_ok=True)
        utf16_rogue.write_bytes(
            json.dumps(
                {
                    "artifact_type": "execution_result",
                    "candidate_run_id": "continuous-002",
                },
                sort_keys=True,
            ).encode("utf-16")
        )
        require_failure(lambda: verify_now(root), "ABSENCE_MATCH")
        negative.append("N-DENY04_UTF16_FORBIDDEN_TYPE")
        utf16_rogue.unlink()
        utf16_rogue.parent.rmdir()
        restore_binding()

        utf32_rogue = repo_path(root, "misc/utf32-result.json")
        utf32_rogue.parent.mkdir(parents=True, exist_ok=True)
        utf32_rogue.write_bytes(
            json.dumps(
                {
                    "artifact_type": "execution_result",
                    "candidate_run_id": "continuous-002",
                },
                sort_keys=True,
            ).encode("utf-32")
        )
        require_failure(lambda: verify_now(root), "ABSENCE_MATCH")
        negative.append("N-DENY05_UTF32_FORBIDDEN_TYPE")
        utf32_rogue.unlink()
        utf32_rogue.parent.rmdir()
        restore_binding()

        control_text = repo_path(root, "notes/control-plane.md")
        control_text_raw = control_text.read_bytes()
        control_text.write_bytes(
            b"Modified tracked protocol text mentions continuous-002 and "
            b"truth_reveal as a hidden runtime payload.\n"
        )
        require_failure(lambda: verify_now(root), "ABSENCE_MATCH")
        negative.append(
            "N-DENY06_MODIFIED_TRACKED_CANDIDATE_SIGNATURE"
        )
        control_text.write_bytes(control_text_raw)
        restore_binding()

        control_text.write_bytes(
            control_text_raw.replace(b"\n", b"\r\n")
        )
        require_failure(lambda: verify_now(root), "ABSENCE_MATCH")
        negative.append("N-DENY07_TRACKED_EOL_NORMALIZATION")
        control_text.write_bytes(control_text_raw)
        restore_binding()

        candidate_json_failure(
            fixture["generator"],
            lambda value: value.update(
                {"source_run_id": "continuous-001"}
            ),
            "REFERENCE_SCOPE_VIOLATION",
            "N-R01_OLD_TOKEN_IN_GENERATOR",
            refresh_semantic_reviews=True,
        )

        generator_path = repo_path(root, fixture["generator"])
        generator_original = generator_path.read_bytes()
        escaped_raw = (
            b'{\n'
            b'  "artifact_type": "synthetic_runtime_generator",\n'
            b'  "run_id": "continuous-002",\n'
            b'  "source_run_id": "continuous-\\u0030001"\n'
            b'}\n'
        )
        generator_path.write_bytes(escaped_raw)
        document = copy.deepcopy(original_document)
        manifest = json.loads(original_manifest.decode("utf-8"))
        escaped_hash = sha256_bytes(escaped_raw)
        _set_document_artifact_hash(
            document,
            fixture["generator"],
            escaped_hash,
        )
        _set_manifest_artifact_hash(
            manifest,
            fixture["generator"],
            escaped_hash,
        )
        saved_reviews = refresh_review_bindings(document, manifest)
        delta_path.write_bytes(canonical_bytes(document))
        write_json(manifest_path, manifest)
        bind_candidate(root, delta_path.read_bytes())
        require_failure(lambda: verify_now(root), "BYTES_NON_CANONICAL")
        negative.append("N-R02_UNICODE_ESCAPE_BLOCKED")
        generator_path.write_bytes(generator_original)
        for review_relative, review_raw in saved_reviews.items():
            repo_path(root, review_relative).write_bytes(review_raw)
        restore_binding()

        document_failure(
            lambda value: value["reference_policy"][
                "provenance_occurrence_allowlist"
            ].pop(),
            "REFERENCE_ALLOWLIST_MISMATCH",
            "N-R03_ALLOWLIST_OMISSION",
            rebind=True,
            refresh_semantic_reviews=True,
        )
        document_failure(
            lambda value: value["reference_scan"].update(
                {"observed_occurrences": []}
            ),
            "REFERENCE_SCAN_MISMATCH",
            "N-R04_RECORDED_SCAN_TAMPER",
            rebind=True,
            refresh_semantic_reviews=True,
        )

        legacy_raw = base["base_values"][
            "source/legacy-runtime-binding.json"
        ]
        generator_path = repo_path(root, fixture["generator"])
        generator_original = generator_path.read_bytes()
        generator_path.write_bytes(legacy_raw)
        document = copy.deepcopy(original_document)
        manifest = json.loads(original_manifest.decode("utf-8"))
        reused_hash = sha256_bytes(legacy_raw)
        _set_document_artifact_hash(
            document,
            fixture["generator"],
            reused_hash,
        )
        _set_manifest_artifact_hash(
            manifest,
            fixture["generator"],
            reused_hash,
        )
        saved_reviews = refresh_review_bindings(document, manifest)
        delta_path.write_bytes(canonical_bytes(document))
        write_json(manifest_path, manifest)
        bind_candidate(root, delta_path.read_bytes())
        require_failure(
            lambda: verify_now(root),
            "FORBIDDEN_REUSE_DETECTED",
        )
        negative.append("N-REUSE01_RENAMED_BASE_BYTES")
        generator_path.write_bytes(generator_original)
        for review_relative, review_raw in saved_reviews.items():
            repo_path(root, review_relative).write_bytes(review_raw)
        restore_binding()

        manifest = json.loads(original_manifest.decode("utf-8"))
        manifest["truth_commitment"]["commitment"] = "1" * 64
        write_json(manifest_path, manifest)
        require_failure(
            lambda: verify_now(root),
            "FORBIDDEN_REUSE_DETECTED",
        )
        negative.append("N-REUSE02_BASE_TRUTH_COMMITMENT")
        restore_binding()

        def rebind_post_gate_actor(value: dict[str, Any]) -> None:
            value.clear()
            value.update(
                {
                    "actor_identifier": "synthetic-new-actor",
                    "artifact_type": "formal_actor_descriptor",
                    "artifact_version": "0.1.0",
                    "run_id": "continuous-002",
                }
            )

        candidate_json_failure(
            fixture["generator"],
            rebind_post_gate_actor,
            "FORBIDDEN_REUSE_DETECTED",
            "N-REUSE03_REBOUND_POST_GATE_PAYLOAD",
            refresh_semantic_reviews=True,
        )

        protected_path = repo_path(root, fixture["protected"])
        protected_original = protected_path.read_bytes()
        protected = json.loads(protected_original.decode("utf-8"))
        domain = PROTECTED_DOMAINS[0]
        protected[domain] = "changed"
        write_json(protected_path, protected)
        changed_raw = protected_path.read_bytes()
        document = copy.deepcopy(original_document)
        manifest = json.loads(original_manifest.decode("utf-8"))
        changed_hash = sha256_bytes(changed_raw)
        _set_document_artifact_hash(
            document,
            fixture["protected"],
            changed_hash,
        )
        for change in document["artifact_changes"]:
            reference = change["candidate_artifact"]
            if (
                isinstance(reference, dict)
                and reference["path"] == fixture["protected"]
            ):
                change["change_kind"] = "run_rematerialized"
        _set_manifest_artifact_hash(
            manifest,
            fixture["protected"],
            changed_hash,
        )
        for assertion in document["protected_design_assertions"]:
            if assertion["domain"] == domain:
                assertion["candidate_source"]["value_sha256"] = (
                    sha256_bytes(canonical_value_bytes("changed"))
                )
        delta_path.write_bytes(canonical_bytes(document))
        write_json(manifest_path, manifest)
        bind_candidate(root, delta_path.read_bytes())
        require_failure(
            lambda: verify_now(root),
            "PROTECTED_DESIGN_CHANGED",
        )
        negative.append("N-DESIGN01_PROTECTED_VALUE_CHANGED")
        protected_path.write_bytes(protected_original)
        restore_binding()

        attestation = repo_path(
            root,
            (
                f"{CANDIDATE_RUN_ROOT}/gate/"
                "external-dispatch-attestations/attestation-001.json"
            ),
        )
        write_json(
            attestation,
            {
                "artifact_type": "external_dispatch_attestation",
                "run_id": "continuous-002",
            },
        )
        require_failure(
            lambda: verify_now(root),
            "MANIFEST_UNREGISTERED_FILE",
        )
        negative.append("N-GATE01_POST_B_ATTESTATION_PRE_A")
        attestation.unlink()
        attestation.parent.rmdir()
        attestation.parent.parent.rmdir()
        restore_binding()

        draft_path = repo_path(root, DRAFT)
        original_draft = draft_path.read_bytes()
        escaping = json.loads(original_draft.decode("utf-8"))
        escaping["artifact_changes"][0]["candidate_artifact"]["path"] = (
            "../escape.json"
        )
        write_json(draft_path, escaping)
        require_failure(
            lambda: materialize_document(
                root,
                escaping,
                output_path=repo_path(root, DELTA_INSTANCE_PATH),
                synthetic_test_profile=True,
            ),
            "PATH_ESCAPE",
        )
        negative.append("N-PATH01_DRAFT_ESCAPE")
        draft_path.write_bytes(original_draft)

        class FaultyWriter:
            def __init__(
                self,
                handle: Any,
                *,
                raise_after_write: bool,
            ) -> None:
                self.handle = handle
                self.raise_after_write = raise_after_write

            def __enter__(self) -> "FaultyWriter":
                return self

            def __exit__(self, *_args: Any) -> None:
                self.handle.close()

            def write(self, raw: bytes) -> int:
                written = self.handle.write(raw[: max(1, len(raw) // 2)])
                if self.raise_after_write:
                    raise OSError("synthetic partial-write failure")
                return written

        write_control = root / "synthetic-write-control.json"
        for raise_after_write, expected_code, control_id in (
            (
                False,
                "OUTPUT_PARTIAL_WRITE",
                "N-WRITE01_SHORT_WRITE_ROLLBACK",
            ),
            (
                True,
                "OUTPUT_WRITE_FAILED",
                "N-WRITE02_PARTIAL_EXCEPTION_ROLLBACK",
            ),
        ):
            def faulty_opener(
                target: Path,
                mode: str,
                *,
                should_raise: bool = raise_after_write,
            ) -> FaultyWriter:
                return FaultyWriter(
                    target.open(mode),
                    raise_after_write=should_raise,
                )

            require_failure(
                lambda: write_bytes_exclusive(
                    write_control,
                    b"synthetic partial-write control\n",
                    opener=faulty_opener,
                ),
                expected_code,
            )
            if write_control.exists() or write_control.is_symlink():
                raise RuntimeError(
                    f"{control_id} left a partial output behind"
                )
            negative.append(control_id)

        unisolated_environment = dict(os.environ)
        unisolated_environment["PYTHONDONTWRITEBYTECODE"] = "1"
        unisolated = subprocess.run(
            [sys.executable, "-B", str(MATERIALIZER)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env=unisolated_environment,
        )
        require_cli_failure(
            unisolated,
            expected_fragment="PYTHON_ISOLATION_REQUIRED",
        )
        negative.append("N-CLI00_ISOLATED_INTERPRETER_REQUIRED")

        rejected = command(
            str(MATERIALIZER),
            "preview",
            "--repo-root",
            str(root),
            "--draft",
            DRAFT,
            "--output",
            DELTA_INSTANCE_PATH,
            "--expected-core-sha256",
            sha256_path(TOOLS / "formal_run_delta_contract.py"),
            "--allow-repository-wide-byte-reads",
            "--synthetic-test-profile",
        )
        if (
            rejected.returncode == 0
            or "unrecognized arguments: --synthetic-test-profile"
            not in rejected.stderr
        ):
            raise RuntimeError(
                "production CLI accepted the synthetic trust bypass: "
                f"{rejected.stderr}"
            )
        negative.append("N-CLI01_SYNTHETIC_PROFILE_REJECTED")

        core_digest = sha256_path(actual_root / CORE_PATH)
        acknowledgement_blocked = command(
            str(MATERIALIZER),
            "preview",
            "--repo-root",
            str(actual_root),
            "--draft",
            REGISTRY_CONTRACT_PATH.as_posix(),
            "--output",
            DELTA_INSTANCE_PATH,
            "--expected-core-sha256",
            core_digest,
        )
        require_cli_failure(
            acknowledgement_blocked,
            expected_fragment=(
                "REPOSITORY_WIDE_BYTE_READS_NOT_ACKNOWLEDGED"
            ),
        )
        negative.append("N-CLI02_REPOSITORY_BYTE_READ_ACK_REQUIRED")

        synthetic_core = repo_path(root, CORE_PATH.as_posix())
        synthetic_core.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(actual_root / CORE_PATH, synthetic_core)
        synthetic_materializer = repo_path(
            root,
            (CORE_PATH.parent / MATERIALIZER.name).as_posix(),
        )
        shutil.copy2(MATERIALIZER, synthetic_materializer)
        synthetic_verifier = repo_path(
            root,
            (CORE_PATH.parent / VERIFIER.name).as_posix(),
        )
        shutil.copy2(VERIFIER, synthetic_verifier)
        try:
            cross_root = command(
                str(MATERIALIZER),
                "preview",
                "--repo-root",
                str(root),
                "--draft",
                DRAFT,
                "--output",
                DELTA_INSTANCE_PATH,
                "--expected-core-sha256",
                core_digest,
                "--allow-repository-wide-byte-reads",
            )
            require_cli_failure(
                cross_root,
                expected_fragment="RUNTIME_WRAPPER_BINDING",
            )
            negative.append("N-CLI03_WRAPPER_CROSS_ROOT_REJECTED")

            review_failure = command(
                str(synthetic_materializer),
                "prepare-review-input",
                "--repo-root",
                str(root),
                "--draft",
                DRAFT,
                "--expected-core-sha256",
                core_digest,
                "--allow-repository-wide-byte-reads",
            )
            review_error = require_cli_failure(
                review_failure,
                expected_fragment="BASE_CANONICAL_ANCHOR_MISMATCH",
            )
            if "AttributeError" in review_error["error"]:
                raise RuntimeError(
                    "prepare-review-input still accesses a missing output argument"
                )
            negative.append("N-CLI04_PREPARE_REVIEW_FAILS_CLOSED")

            marker = root / "tampered-core-imported.marker"
            good_core_raw = synthetic_core.read_bytes()
            synthetic_core.write_bytes(
                (
                    "from pathlib import Path\n"
                    f"Path({str(marker)!r}).write_text("
                    "'imported', encoding='utf-8')\n"
                ).encode("utf-8")
            )
            tampered_materializer = command(
                str(synthetic_materializer),
                "preview",
                "--repo-root",
                str(root),
                "--draft",
                DRAFT,
                "--output",
                DELTA_INSTANCE_PATH,
                "--expected-core-sha256",
                core_digest,
                "--allow-repository-wide-byte-reads",
            )
            require_cli_failure(
                tampered_materializer,
                expected_fragment="RUNTIME_CORE_PIN_MISMATCH",
            )
            tampered_verifier = command(
                str(synthetic_verifier),
                "verify",
                "--repo-root",
                str(root),
                "--delta",
                DRAFT,
                "--expected-core-sha256",
                core_digest,
                "--allow-repository-wide-byte-reads",
            )
            require_cli_failure(
                tampered_verifier,
                expected_fragment="RUNTIME_CORE_PIN_MISMATCH",
            )
            if marker.exists() or marker.is_symlink():
                raise RuntimeError(
                    "a tampered contract core executed before pin validation"
                )
            synthetic_core.write_bytes(good_core_raw)
            negative.append("N-CLI05_TAMPERED_CORE_NOT_IMPORTED")
        finally:
            synthetic_verifier.unlink(missing_ok=True)
            synthetic_materializer.unlink(missing_ok=True)
            synthetic_core.unlink(missing_ok=True)

    _batch2_component_matrix_controls(
        actual_root,
        positive,
        negative,
    )

    if tuple(positive) != EXPECTED_POSITIVE_IDS:
        raise RuntimeError(
            f"positive control set drifted: {positive!r}"
        )
    if tuple(negative) != EXPECTED_NEGATIVE_IDS:
        raise RuntimeError(
            f"negative control set drifted: {negative!r}"
        )
    return {
        "formal_input_access": False,
        "negative_controls": negative,
        "negative_controls_passed": len(negative),
        "positive_controls": positive,
        "positive_controls_passed": len(positive),
        "runner_or_comparator_executed": False,
        "status": "synthetic_self_test_passed",
        "temporary_repository_only": True,
    }


def main() -> int:
    try:
        report = run_self_test(Path(__file__).resolve().parents[4])
    except Exception as error:
        print(
            json.dumps(
                {
                    "error": str(error),
                    "status": "synthetic_self_test_failed",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
