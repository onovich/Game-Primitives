#!/usr/bin/env python3
"""Check the continuous-action pre-gate contract without executing formal inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REQUIRED_AUDIT_CHECKS = {
    "answer_hint_scan",
    "atomic_projection_equivalence",
    "dispatch_symmetry",
    "formal_build_readiness_integrity",
    "identity_leak_scan",
    "invariant_integrity",
    "projection_fidelity",
    "protocol_incident_disposition",
    "reference_closure",
    "single_variable_isolation",
    "stage2_input_closure",
}

REQUIRED_AUDIT_INPUTS = {
    "research/calibration-tests/continuous-action-pilot/schema/execution-artifact-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/execution-artifact-0.1.1.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/fixture-assembly-fragment-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/fixture-lock-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/formal-build-readiness-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/task-packet-0.1.2.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/ca-r1-raw-trace-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/ca-r2-raw-trace-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/ca-r3-raw-trace-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/formal-comparator-output-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/formal-execution-permit-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/formal-human-gate-authorization-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/r1-standalone-build-evidence-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/r2-build-readiness-evidence-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/python-runtime-evidence-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/schema/protocol-incident-0.1.0.schema.json",
    "research/calibration-tests/continuous-action-pilot/tools/build-role-submission.py",
    "research/calibration-tests/continuous-action-pilot/tools/materialize-execution-permit.py",
    "research/calibration-tests/continuous-action-pilot/tools/materialize-dispatch.py",
    "research/calibration-tests/continuous-action-pilot/tools/verify-formal-execution-permit.py",
    "research/calibration-tests/continuous-action-pilot/tools/verify-formal-raw-trace.py",
    "research/calibration-tests/continuous-action-pilot/tools/formal_execution_target_contract.py",
    "research/calibration-tests/continuous-action-pilot/tools/materialize-fixture-assembly.py",
    "research/calibration-tests/continuous-action-pilot/tools/materialize-final-execution-plan.py",
    "research/calibration-tests/continuous-action-pilot/tools/materialize-python-runtime-evidence.py",
    "research/calibration-tests/continuous-action-pilot/tools/materialize-projection-audit-task.py",
    "research/calibration-tests/continuous-action-pilot/tools/verify-formal-readiness.py",
    "research/calibration-tests/continuous-action-pilot/tools/verify-run-package.py",
    "execution/execution-plan.json",
    "fixtures/python-runtime-evidence-v0.1.0.json",
    "fixtures/fixture-lock.json",
    "fixtures/formal-build-readiness-v0.1.0.json",
    "fixtures/r1/r1-fixture-assembly-fragment-v0.1.0.json",
    "fixtures/r2/r2-fixture-assembly-fragment-v0.1.0.json",
    "fixtures/r3/r3-fixture-assembly-fragment-v0.1.0.json",
    "inputs/actor-plan.md",
    "inputs/generate-continuous-views-v0.1.0.py",
    "inputs/generate-stage2-envelope-v0.1.0.py",
    "inputs/generate-stage2-prediction-task-v0.1.0.py",
    "inputs/prediction-response.template.json",
    "inputs/projection-spec.json",
    "inputs/reconstruction-response.template.json",
    "inputs/stage1-dispatch-p01.template.json",
    "inputs/stage1-dispatch-p02.template.json",
    "inputs/stage1-dispatch-p03.template.json",
    "inputs/stage1-dispatch-p04.template.json",
    "inputs/stage1-condition-v01.task.json",
    "inputs/stage1-condition-v02.task.json",
    "inputs/stage1-view-v01.json",
    "inputs/stage1-view-v02.json",
    "inputs/stage2-dispatch-p01.template.json",
    "inputs/stage2-dispatch-p02.template.json",
    "inputs/stage2-dispatch-p03.template.json",
    "inputs/stage2-dispatch-p04.template.json",
    "inputs/stage2-prediction.task.json",
    "inputs/stage2-variant-envelope.json",
    "source/canonical-encoding-v0.1.0.json",
    "source/protocol-incident-r3-byte-integrity-read-v0.1.0.json",
}

REQUIRED_PATHS = {
    "README.md": True,
    "execution/execution-plan.json": True,
    "fixtures/fixture-lock.json": True,
    "fixtures/formal-build-readiness-v0.1.0.json": True,
    "fixtures/toolchain-probe-v0.1.2.json": True,
    "inputs/actor-plan.md": True,
    "inputs/frozen-set-preimage.tsv": False,
    "inputs/generate-continuous-views-v0.1.0.py": True,
    "inputs/generate-stage2-envelope-v0.1.0.py": True,
    "inputs/generate-stage2-prediction-task-v0.1.0.py": True,
    "inputs/prediction-response.template.json": True,
    "inputs/projection-audit.task.json": True,
    "inputs/projection-spec.json": True,
    "inputs/reconstruction-response.template.json": True,
    "inputs/source-audit-packet.json": True,
    "inputs/source-encoding-packet.json": True,
    "inputs/stage1-condition-v01.task.json": True,
    "inputs/stage1-condition-v02.task.json": True,
    "inputs/stage1-dispatch-p01.template.json": True,
    "inputs/stage1-dispatch-p02.template.json": True,
    "inputs/stage1-dispatch-p03.template.json": True,
    "inputs/stage1-dispatch-p04.template.json": True,
    "inputs/stage1-view-v01.json": True,
    "inputs/stage1-view-v02.json": True,
    "inputs/stage2-dispatch-p01.template.json": True,
    "inputs/stage2-dispatch-p02.template.json": True,
    "inputs/stage2-dispatch-p03.template.json": True,
    "inputs/stage2-dispatch-p04.template.json": True,
    "inputs/stage2-prediction.task.json": True,
    "inputs/stage2-variant-envelope.json": True,
    "source/canonical-encoding-v0.1.0.json": True,
    "source/encoding-audit-v0.1.0.json": True,
    "source/protocol-incident-r3-byte-integrity-read-v0.1.0.json": True,
    "source/projection-audit-v0.1.0.json": True,
    "source/source-packet.json": True,
}

POST_GATE_PREFIXES = (
    "execution/raw/",
    "reports/",
    "reveal/",
    "submissions/",
)

POST_GATE_PATHS = {
    "execution/execution-result.json",
    "execution/trace-bundle.json",
}

SCHEMA_PATHS = {
    "fixtures/fixture-lock.json": "research/calibration-tests/continuous-action-pilot/schema/fixture-lock-0.1.0.schema.json",
    "fixtures/formal-build-readiness-v0.1.0.json": "research/calibration-tests/continuous-action-pilot/schema/formal-build-readiness-0.1.0.schema.json",
    "inputs/prediction-response.template.json": "research/calibration-tests/continuous-action-pilot/schema/response-template-0.1.0.schema.json",
    "inputs/projection-audit.task.json": "research/calibration-tests/continuous-action-pilot/schema/task-packet-0.1.2.schema.json",
    "inputs/reconstruction-response.template.json": "research/calibration-tests/continuous-action-pilot/schema/response-template-0.1.0.schema.json",
    "inputs/source-audit-packet.json": "research/calibration-tests/continuous-action-pilot/schema/task-packet-0.1.2.schema.json",
    "inputs/source-encoding-packet.json": "research/calibration-tests/continuous-action-pilot/schema/task-packet-0.1.2.schema.json",
    "inputs/stage1-condition-v01.task.json": "research/calibration-tests/continuous-action-pilot/schema/task-packet-0.1.2.schema.json",
    "inputs/stage1-condition-v02.task.json": "research/calibration-tests/continuous-action-pilot/schema/task-packet-0.1.2.schema.json",
    "inputs/stage1-dispatch-p01.template.json": "research/calibration-tests/continuous-action-pilot/schema/stage1-seat-dispatch-envelope-0.1.0.schema.json",
    "inputs/stage1-dispatch-p02.template.json": "research/calibration-tests/continuous-action-pilot/schema/stage1-seat-dispatch-envelope-0.1.0.schema.json",
    "inputs/stage1-dispatch-p03.template.json": "research/calibration-tests/continuous-action-pilot/schema/stage1-seat-dispatch-envelope-0.1.0.schema.json",
    "inputs/stage1-dispatch-p04.template.json": "research/calibration-tests/continuous-action-pilot/schema/stage1-seat-dispatch-envelope-0.1.0.schema.json",
    "inputs/stage2-dispatch-p01.template.json": "research/calibration-tests/continuous-action-pilot/schema/stage2-seat-dispatch-envelope-0.1.0.schema.json",
    "inputs/stage2-dispatch-p02.template.json": "research/calibration-tests/continuous-action-pilot/schema/stage2-seat-dispatch-envelope-0.1.0.schema.json",
    "inputs/stage2-dispatch-p03.template.json": "research/calibration-tests/continuous-action-pilot/schema/stage2-seat-dispatch-envelope-0.1.0.schema.json",
    "inputs/stage2-dispatch-p04.template.json": "research/calibration-tests/continuous-action-pilot/schema/stage2-seat-dispatch-envelope-0.1.0.schema.json",
    "inputs/stage2-prediction.task.json": "research/calibration-tests/continuous-action-pilot/schema/task-packet-0.1.2.schema.json",
    "inputs/stage2-variant-envelope.json": "research/calibration-tests/continuous-action-pilot/schema/variant-envelope-0.1.0.schema.json",
    "source/encoding-audit-v0.1.0.json": "research/calibration-tests/continuous-action-pilot/schema/role-submission-0.1.2.schema.json",
    "source/protocol-incident-r3-byte-integrity-read-v0.1.0.json": "research/calibration-tests/continuous-action-pilot/schema/protocol-incident-0.1.0.schema.json",
    "source/projection-audit-v0.1.0.json": "research/calibration-tests/continuous-action-pilot/schema/role-submission-0.1.2.schema.json",
}

EXECUTION_PLAN_PREPARATION_SCHEMA = (
    "research/calibration-tests/continuous-action-pilot/schema/"
    "execution-plan-preparation-0.1.0.schema.json"
)
FINAL_EXECUTION_PLAN_SCHEMA = (
    "research/calibration-tests/continuous-action-pilot/schema/"
    "execution-artifact-0.1.1.schema.json"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add_failure(
    failures: list[dict[str, Any]],
    kind: str,
    path: str,
    expected: Any,
    actual: Any,
) -> None:
    failures.append(
        {
            "actual": actual,
            "expected": expected,
            "kind": kind,
            "path": path,
        }
    )


def iter_references(value: Any) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(value.get("sha256"), str):
            references.append(value)
        for child in value.values():
            references.extend(iter_references(child))
    elif isinstance(value, list):
        for child in value:
            references.extend(iter_references(child))
    return references


def to_run_relative(
    reference_path: str,
    *,
    repo_root: Path,
    run_dir: Path,
) -> str | None:
    candidate = (repo_root / reference_path).resolve()
    if not candidate.is_relative_to(run_dir):
        return None
    return candidate.relative_to(run_dir).as_posix()


def check_protocol_incident(
    *,
    incident: dict[str, Any],
    entries_by_path: dict[str, dict[str, Any]],
    failures: list[dict[str, Any]],
) -> None:
    incident_path = (
        "source/protocol-incident-r3-byte-integrity-read-v0.1.0.json"
    )
    expected_sections = {
        "aggregate_state": {
            "formal_input_byte_read": True,
            "formal_input_executed": False,
            "formal_result_produced": False,
        },
        "exposure": {
            "content_exposed_to_main_thread": False,
            "content_exposed_to_prediction_flow": False,
            "digest_exposed_to_main_thread": False,
            "formal_result_observed": False,
        },
        "gate_disposition": {
            "recommended": (
                "retain_with_documented_nonsemantic_integrity_exception"
            ),
            "required": True,
            "status": "pending_explicit_human_acceptance",
        },
        "non_operations": {
            "content_persisted": False,
            "content_printed_or_returned": False,
            "digest_persisted": False,
            "digest_printed_or_returned": False,
            "formal_execution": False,
            "json_parse": False,
            "semantic_interpretation": False,
        },
        "observed_operations": {
            "byte_read_api": "Path.read_bytes",
            "byte_read_count": 1,
            "compared_with_existing_case_lock_digest": True,
            "digest_algorithm": "SHA-256",
        },
        "target_artifact": {
            "artifact_id": "fixture.r3.formal-input-v0.1.0",
            "path": "fixtures/r3/formal-input-r3-v0.1.0.json",
        },
    }
    expected_scalars = {
        "artifact_type": "protocol_incident_record",
        "artifact_version": "0.1.0",
        "case_id": "CA-R3",
        "incident_id": "incident.r3.formal-input-byte-integrity-read.v0.1.0",
        "phase": "pre_gate_evidence_hardening",
        "run_id": "continuous-001",
        "sequence_position": (
            "after_r3_evidence_generation_before_pre_audit_freeze"
        ),
    }
    for field_name, expected in expected_scalars.items():
        if incident.get(field_name) != expected:
            add_failure(
                failures,
                "protocol_incident_semantics",
                f"{incident_path}#{field_name}",
                expected,
                incident.get(field_name),
            )
    for field_name, expected in expected_sections.items():
        if incident.get(field_name) != expected:
            add_failure(
                failures,
                "protocol_incident_semantics",
                f"{incident_path}#{field_name}",
                expected,
                incident.get(field_name),
            )
    aggregate = incident.get("aggregate_state")
    if isinstance(aggregate, dict) and "formal_input_read" in aggregate:
        add_failure(
            failures,
            "protocol_incident_ambiguous_read_claim",
            f"{incident_path}#aggregate_state",
            "no aggregate formal_input_read=false assertion",
            aggregate.get("formal_input_read"),
        )
    target = incident.get("target_artifact")
    if isinstance(target, dict):
        target_entry = entries_by_path.get(target.get("path"))
        if (
            target_entry is None
            or target_entry.get("artifact_id") != target.get("artifact_id")
        ):
            add_failure(
                failures,
                "protocol_incident_target_binding",
                f"{incident_path}#target_artifact",
                target,
                (
                    None
                    if target_entry is None
                    else {
                        "artifact_id": target_entry.get("artifact_id"),
                        "path": target_entry.get("path"),
                    }
                ),
            )


def check_fixture_lock(
    *,
    fixture_lock: dict[str, Any],
    entries_by_path: dict[str, dict[str, Any]],
    repo_root: Path,
    run_dir: Path,
    failures: list[dict[str, Any]],
) -> None:
    if fixture_lock.get("formal_execution_authorized") is not False:
        add_failure(
            failures,
            "formal_execution_authorized",
            "fixtures/fixture-lock.json",
            False,
            fixture_lock.get("formal_execution_authorized"),
        )
    if fixture_lock.get("formal_input_executed") is not False:
        add_failure(
            failures,
            "formal_input_executed",
            "fixtures/fixture-lock.json",
            False,
            fixture_lock.get("formal_input_executed"),
        )

    seen_reference_paths: set[str] = set()
    for reference in iter_references(fixture_lock):
        if reference["path"] in seen_reference_paths:
            continue
        seen_reference_paths.add(reference["path"])
        run_relative = to_run_relative(
            reference["path"],
            repo_root=repo_root,
            run_dir=run_dir,
        )
        if run_relative is None:
            add_failure(
                failures,
                "fixture_reference_scope",
                reference["path"],
                "artifact inside the formal run directory",
                reference["path"],
            )
            continue
        entry = entries_by_path.get(run_relative)
        if entry is None:
            add_failure(
                failures,
                "fixture_reference_manifested",
                run_relative,
                "manifest entry",
                None,
            )
            continue
        if not entry.get("included_in_frozen_set"):
            add_failure(
                failures,
                "fixture_reference_frozen",
                run_relative,
                True,
                entry.get("included_in_frozen_set"),
            )

    for case in fixture_lock.get("cases", []):
        case_id = case.get("case_id", "<missing>")
        role_sets: dict[str, set[tuple[str, str]]] = {}
        for field_name in (
            "compatibility_patch_set",
            "observation_patch_set",
            "variant_patch_set",
        ):
            patch_set = case.get(field_name, {})
            role_sets[field_name] = {
                (reference["path"], reference["sha256"])
                for reference in patch_set.get("artifacts", [])
            }

        role_names = list(role_sets)
        for index, left_name in enumerate(role_names):
            for right_name in role_names[index + 1 :]:
                overlap = sorted(role_sets[left_name] & role_sets[right_name])
                if overlap:
                    add_failure(
                        failures,
                        "patch_role_overlap",
                        f"fixtures/fixture-lock.json#{case_id}",
                        "disjoint compatibility, observation, and variant artifacts",
                        overlap,
                    )

        variant_patch_set = case.get("variant_patch_set", {})
        if variant_patch_set.get("realization") == "configuration_only":
            allowed_configuration_refs = {
                (reference["path"], reference["sha256"])
                for reference in (
                    case.get("formal_input_artifacts", [])
                    + case.get("fixture_artifacts", [])
                )
            }
            configured_refs = {
                (reference["path"], reference["sha256"])
                for reference in variant_patch_set.get(
                    "configuration_artifacts",
                    [],
                )
            }
            if not configured_refs.issubset(allowed_configuration_refs):
                add_failure(
                    failures,
                    "variant_configuration_binding",
                    f"fixtures/fixture-lock.json#{case_id}",
                    sorted(allowed_configuration_refs),
                    sorted(configured_refs),
                )

        for formal_input in case.get("formal_input_artifacts", []):
            run_relative = to_run_relative(
                formal_input["path"],
                repo_root=repo_root,
                run_dir=run_dir,
            )
            if run_relative is None:
                continue
            entry = entries_by_path.get(run_relative)
            if entry is None:
                continue
            expected_schema = "research/calibration-tests/continuous-action-pilot/schema/formal-input-trace-0.1.0.schema.json"
            if entry.get("schema_path") != expected_schema:
                add_failure(
                    failures,
                    "formal_input_schema",
                    run_relative,
                    expected_schema,
                    entry.get("schema_path"),
                )
                continue
            formal_path = run_dir / run_relative
            if not formal_path.is_file():
                continue
            formal = load_json(formal_path)
            if formal.get("case_id") != case_id:
                add_failure(
                    failures,
                    "formal_input_case_binding",
                    run_relative,
                    case_id,
                    formal.get("case_id"),
                )
            if formal.get("stop_boundary_id") != case.get("stop_boundary_id"):
                add_failure(
                    failures,
                    "formal_input_stop_boundary_binding",
                    run_relative,
                    case.get("stop_boundary_id"),
                    formal.get("stop_boundary_id"),
                )
            guard = formal.get("pre_gate_guard", {})
            expected_guard = {
                "authorization_state": "withheld",
                "execution_status": "not_executed",
                "expected_result_included": False,
                "formal_input_executed": False,
                "formal_result_created": False,
            }
            if guard != expected_guard:
                add_failure(
                    failures,
                    "formal_input_guard",
                    run_relative,
                    expected_guard,
                    guard,
                )
            events = formal.get("input_events", [])
            fixture_field_ids = [
                field.get("field_id")
                for field in formal.get("fixture_configuration_fields", [])
            ]
            if len(fixture_field_ids) != len(set(fixture_field_ids)):
                add_failure(
                    failures,
                    "formal_input_fixture_field_ids",
                    run_relative,
                    "unique fixture configuration field_id values",
                    fixture_field_ids,
                )
            actual_indices = [event.get("sequence_index") for event in events]
            if actual_indices != list(range(len(events))):
                add_failure(
                    failures,
                    "formal_input_sequence",
                    run_relative,
                    list(range(len(events))),
                    actual_indices,
                )
            event_ids = [event.get("event_id") for event in events]
            if len(event_ids) != len(set(event_ids)):
                add_failure(
                    failures,
                    "formal_input_event_ids",
                    run_relative,
                    "unique event_id values",
                    event_ids,
                )
            for event in events:
                field_ids = [
                    field.get("field_id")
                    for field in event.get("fields", [])
                ]
                if len(field_ids) != len(set(field_ids)):
                    add_failure(
                        failures,
                        "formal_input_event_field_ids",
                        f"{run_relative}#{event.get('event_id')}",
                        "unique field_id values within each event",
                        field_ids,
                    )


def check_formal_build_readiness(
    *,
    readiness: dict[str, Any],
    fixture_lock: dict[str, Any],
    entries_by_path: dict[str, dict[str, Any]],
    repo_root: Path,
    run_dir: Path,
    failures: list[dict[str, Any]],
) -> None:
    for reference in iter_references(readiness):
        run_relative = to_run_relative(
            reference["path"],
            repo_root=repo_root,
            run_dir=run_dir,
        )
        if run_relative is None:
            add_failure(
                failures,
                "build_readiness_reference_scope",
                reference["path"],
                "artifact inside the formal run directory",
                reference["path"],
            )
            continue
        entry = entries_by_path.get(run_relative)
        if entry is None:
            add_failure(
                failures,
                "build_readiness_reference_manifested",
                run_relative,
                "manifest entry",
                None,
            )
        elif not entry.get("included_in_frozen_set"):
            add_failure(
                failures,
                "build_readiness_reference_frozen",
                run_relative,
                True,
                entry.get("included_in_frozen_set"),
            )

    historical_entry = entries_by_path.get("fixtures/toolchain-probe-v0.1.2.json")
    supersedes_probe = readiness.get("supersedes_probe")
    expected_supersedes = None
    if historical_entry is not None:
        expected_supersedes = {
            "path": "fixtures/toolchain-probe-v0.1.2.json",
            "sha256": historical_entry["sha256"],
        }
    actual_supersedes = None
    if isinstance(supersedes_probe, dict):
        actual_supersedes = {
            "path": to_run_relative(
                supersedes_probe["path"],
                repo_root=repo_root,
                run_dir=run_dir,
            ),
            "sha256": supersedes_probe["sha256"],
        }
    if actual_supersedes != expected_supersedes:
        add_failure(
            failures,
            "build_readiness_supersedes_probe",
            "fixtures/formal-build-readiness-v0.1.0.json",
            expected_supersedes,
            actual_supersedes,
        )

    readiness_entry = entries_by_path.get(
        "fixtures/formal-build-readiness-v0.1.0.json"
    )
    if readiness_entry is not None:
        expected_binding = (
            "research/calibration-tests/continuous-action-pilot/runs/"
            f"continuous-001/{readiness_entry['path']}",
            readiness_entry["sha256"],
        )
        for case_lock in fixture_lock.get("cases", []):
            probe_bindings = {
                (reference["path"], reference["sha256"])
                for reference in case_lock.get("preparation_probe_artifacts", [])
            }
            if expected_binding not in probe_bindings:
                add_failure(
                    failures,
                    "fixture_lock_final_build_binding",
                    f"fixtures/fixture-lock.json#{case_lock.get('case_id')}",
                    expected_binding,
                    sorted(probe_bindings),
                )

    lock_by_case = {
        case["case_id"]: case
        for case in fixture_lock.get("cases", [])
    }
    readiness_by_case = {
        case["case_id"]: case
        for case in readiness.get("cases", [])
    }
    root_evidence = {
        (reference["path"], reference["sha256"])
        for reference in readiness.get("evidence_artifacts", [])
    }
    for case_id in ("CA-R1", "CA-R2", "CA-R3"):
        case_lock = lock_by_case.get(case_id)
        case_readiness = readiness_by_case.get(case_id)
        if case_lock is None or case_readiness is None:
            continue
        if (
            case_readiness.get("source_commit")
            != case_lock["source_identity"]["commit_sha"]
        ):
            add_failure(
                failures,
                "build_readiness_source_binding",
                f"fixtures/formal-build-readiness-v0.1.0.json#{case_id}",
                case_lock["source_identity"]["commit_sha"],
                case_readiness.get("source_commit"),
            )

        locked_fixture_refs = {
            (reference["path"], reference["sha256"])
            for reference in case_lock.get("fixture_artifacts", [])
        }
        for patch_set_name in (
            "compatibility_patch_set",
            "observation_patch_set",
            "variant_patch_set",
        ):
            patch_set = case_lock.get(patch_set_name, {})
            locked_fixture_refs.update(
                (reference["path"], reference["sha256"])
                for reference in (
                    patch_set.get("artifacts", [])
                    + patch_set.get("configuration_artifacts", [])
                )
            )

        configurations = {
            configuration["configuration_id"]: configuration
            for configuration in case_readiness.get("configurations", [])
        }
        for configuration_id, configuration in configurations.items():
            used_fixture_refs = {
                (reference["path"], reference["sha256"])
                for reference in configuration.get("fixture_artifacts", [])
            }
            if not used_fixture_refs.issubset(locked_fixture_refs):
                add_failure(
                    failures,
                    "build_readiness_fixture_binding",
                    (
                        "fixtures/formal-build-readiness-v0.1.0.json"
                        f"#{case_id}/{configuration_id}"
                    ),
                    sorted(locked_fixture_refs),
                    sorted(used_fixture_refs),
                )
            configuration_evidence = {
                (reference["path"], reference["sha256"])
                for reference in configuration.get(
                    "build_evidence_artifacts",
                    [],
                )
            }
            if not configuration_evidence.issubset(root_evidence):
                add_failure(
                    failures,
                    "build_readiness_evidence_rollup",
                    (
                        "fixtures/formal-build-readiness-v0.1.0.json"
                        f"#{case_id}/{configuration_id}"
                    ),
                    sorted(root_evidence),
                    sorted(configuration_evidence),
                )

        variant_realization = case_lock["variant_patch_set"]["realization"]
        baseline = configurations.get("config.baseline")
        variant = configurations.get("config.variant")
        if baseline is None or variant is None:
            continue
        if variant_realization == "configuration_only":
            expected_realization = "shared_binary_configuration"
            for configuration in (baseline, variant):
                if configuration.get("realization") != expected_realization:
                    add_failure(
                        failures,
                        "build_readiness_shared_realization",
                        f"fixtures/formal-build-readiness-v0.1.0.json#{case_id}",
                        expected_realization,
                        configuration.get("realization"),
                    )
            baseline_outputs = {
                (output["output_id"], output["sha256"])
                for output in baseline.get("built_outputs", [])
            }
            variant_outputs = {
                (output["output_id"], output["sha256"])
                for output in variant.get("built_outputs", [])
            }
            if baseline_outputs != variant_outputs:
                add_failure(
                    failures,
                    "build_readiness_shared_outputs",
                    f"fixtures/formal-build-readiness-v0.1.0.json#{case_id}",
                    sorted(baseline_outputs),
                    sorted(variant_outputs),
                )
        elif variant_realization == "patch":
            for configuration in (baseline, variant):
                if configuration.get("realization") != "separate_binary":
                    add_failure(
                        failures,
                        "build_readiness_separate_realization",
                        f"fixtures/formal-build-readiness-v0.1.0.json#{case_id}",
                        "separate_binary",
                        configuration.get("realization"),
                    )
        else:
            add_failure(
                failures,
                "build_readiness_variant_realization",
                f"fixtures/fixture-lock.json#{case_id}",
                "patch or configuration_only",
                variant_realization,
            )


def check_variant_envelope(
    envelope: dict[str, Any],
    failures: list[dict[str, Any]],
) -> None:
    forbidden_tokens = ("rich", "atomic")

    def walk(value: Any, location: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lowered_key = key.lower()
                allowed_assertion_keys = {
                    "source_identity_included",
                    "source_paths_included",
                }
                if key != "$schema" and key not in allowed_assertion_keys and any(
                    token in lowered_key for token in ("path", "source", "url")
                ):
                    add_failure(
                        failures,
                        "variant_envelope_identity_field",
                        f"{location}/{key}",
                        "no path, source, or URL field",
                        key,
                    )
                walk(child, f"{location}/{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{location}/{index}")
        elif isinstance(value, str) and not location.endswith("/$schema"):
            lowered = value.lower()
            matched = [token for token in forbidden_tokens if token in lowered]
            if matched:
                add_failure(
                    failures,
                    "variant_envelope_forbidden_token",
                    location,
                    "no condition-label hint",
                    matched,
                )
            if any(marker in value for marker in ("/", "\\", "://")):
                add_failure(
                    failures,
                    "variant_envelope_path_like_value",
                    location,
                    "non-path blind scalar or identifier",
                    value,
                )

    walk(envelope, "inputs/stage2-variant-envelope.json")
    for intervention in envelope.get("case_interventions", []):
        case_id = intervention.get("case_id")
        invariant_ids = intervention.get("invariant_ids", [])
        invariant_specs = intervention.get("invariant_specs", [])
        spec_ids = [
            spec.get("invariant_id")
            for spec in invariant_specs
            if isinstance(spec, dict)
        ]
        if len(spec_ids) != len(set(spec_ids)):
            add_failure(
                failures,
                "variant_envelope_invariant_spec_ids",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                "one neutral definition per invariant ID",
                spec_ids,
            )
        if set(spec_ids) != set(invariant_ids):
            add_failure(
                failures,
                "variant_envelope_invariant_spec_closure",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                sorted(invariant_ids),
                sorted(spec_ids),
            )
        descriptions = [
            spec.get("description")
            for spec in invariant_specs
            if isinstance(spec, dict)
        ]
        if len(descriptions) != len(set(descriptions)):
            add_failure(
                failures,
                "variant_envelope_invariant_spec_descriptions",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                "distinct neutral descriptions",
                descriptions,
            )
        tolerance_ids = intervention.get("tolerance_rule_ids", [])
        tolerance_specs = intervention.get("tolerance_specs", [])
        tolerance_spec_ids = [
            spec.get("tolerance_rule_id")
            for spec in tolerance_specs
            if isinstance(spec, dict)
        ]
        if (
            len(tolerance_spec_ids) != len(set(tolerance_spec_ids))
            or set(tolerance_spec_ids) != set(tolerance_ids)
        ):
            add_failure(
                failures,
                "variant_envelope_tolerance_spec_closure",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                sorted(tolerance_ids),
                tolerance_spec_ids,
            )
        stop_boundary_id = intervention.get("stop_boundary_id")
        stop_boundary_spec = intervention.get("stop_boundary_spec")
        stop_spec_id = (
            stop_boundary_spec.get("stop_boundary_id")
            if isinstance(stop_boundary_spec, dict)
            else None
        )
        if stop_spec_id != stop_boundary_id:
            add_failure(
                failures,
                "variant_envelope_stop_boundary_spec_closure",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                stop_boundary_id,
                stop_spec_id,
            )

        initial_field_ids = [
            spec.get("field_id")
            for spec in intervention.get("initial_state_specs", [])
            if isinstance(spec, dict)
        ]
        if not initial_field_ids:
            add_failure(
                failures,
                "variant_envelope_initial_state_closure",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                "at least one neutral typed initial-state field",
                initial_field_ids,
            )
        if len(initial_field_ids) != len(set(initial_field_ids)):
            add_failure(
                failures,
                "variant_envelope_initial_state_field_ids",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                "unique neutral initial-state field IDs",
                initial_field_ids,
            )

        formal_input_value = intervention.get("formal_input_spec")
        formal_input = (
            formal_input_value
            if isinstance(formal_input_value, dict)
            else {}
        )
        events_value = formal_input.get("events")
        events = events_value if isinstance(events_value, list) else []
        time_base = formal_input.get("time_base")
        time_base_id = (
            time_base.get("time_base_id")
            if isinstance(time_base, dict)
            else None
        )
        if (
            not formal_input.get("formal_input_id")
            or not time_base_id
            or not events
        ):
            add_failure(
                failures,
                "variant_envelope_formal_input_closure",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                "neutral formal-input ID, time base, and at least one event",
                formal_input_value,
            )
        event_ids = [
            event.get("event_id")
            for event in events
            if isinstance(event, dict)
        ]
        sequence_indexes = [
            event.get("sequence_index")
            for event in events
            if isinstance(event, dict)
        ]
        expected_indexes = list(range(len(events)))
        if len(event_ids) != len(set(event_ids)):
            add_failure(
                failures,
                "variant_envelope_formal_input_event_ids",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                "unique neutral event IDs",
                event_ids,
            )
        if sequence_indexes != expected_indexes:
            add_failure(
                failures,
                "variant_envelope_formal_input_sequence",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                expected_indexes,
                sequence_indexes,
            )
        for event in events:
            event_field_ids = [
                field.get("field_id")
                for field in event.get("fields", [])
                if isinstance(field, dict)
            ]
            if len(event_field_ids) != len(set(event_field_ids)):
                add_failure(
                    failures,
                    "variant_envelope_formal_input_field_ids",
                    (
                        "inputs/stage2-variant-envelope.json"
                        f"#{case_id}/{event.get('event_id')}"
                    ),
                    "unique neutral field IDs within each event",
                    event_field_ids,
                )


def check_prediction_task_bindings(
    *,
    envelope: dict[str, Any],
    prediction_task: dict[str, Any],
    repo_root: Path,
    run_dir: Path,
    failures: list[dict[str, Any]],
) -> None:
    input_paths = {
        to_run_relative(
            reference.get("path", ""),
            repo_root=repo_root,
            run_dir=run_dir,
        )
        for reference in prediction_task.get("input_artifacts", [])
    }
    expected_input_paths = {
        "inputs/prediction-response.template.json",
        "inputs/stage2-variant-envelope.json",
    }
    if input_paths != expected_input_paths:
        add_failure(
            failures,
            "prediction_task_dispatch_inputs",
            "inputs/stage2-prediction.task.json",
            sorted(expected_input_paths),
            sorted(path for path in input_paths if path is not None),
        )

    envelope_by_case = {
        intervention.get("case_id"): intervention
        for intervention in envelope.get("case_interventions", [])
    }
    task_interventions = prediction_task.get("variant_interventions", [])
    task_case_ids = [
        intervention.get("case_id")
        for intervention in task_interventions
    ]
    if (
        set(task_case_ids) != set(envelope_by_case)
        or len(task_case_ids) != len(envelope_by_case)
    ):
        add_failure(
            failures,
            "prediction_task_invariant_case_coverage",
            "inputs/stage2-prediction.task.json",
            sorted(envelope_by_case),
            task_case_ids,
        )
        return

    expected_tolerance_ids = {
        tolerance_id
        for intervention in envelope_by_case.values()
        for tolerance_id in intervention.get("tolerance_rule_ids", [])
    }
    actual_tolerance_ids = set(prediction_task.get("tolerance_rule_refs", []))
    if actual_tolerance_ids != expected_tolerance_ids:
        add_failure(
            failures,
            "prediction_task_tolerance_refs",
            "inputs/stage2-prediction.task.json",
            sorted(expected_tolerance_ids),
            sorted(actual_tolerance_ids),
        )
    expected_stop_boundaries = {
        intervention.get("stop_boundary_id")
        for intervention in envelope_by_case.values()
    }
    actual_stop_boundaries = set(prediction_task.get("stop_boundary_refs", []))
    if actual_stop_boundaries != expected_stop_boundaries:
        add_failure(
            failures,
            "prediction_task_stop_boundary_refs",
            "inputs/stage2-prediction.task.json",
            sorted(expected_stop_boundaries),
            sorted(actual_stop_boundaries),
        )
    expected_configuration_ids = {
        configuration_id
        for intervention in envelope_by_case.values()
        for configuration_id in intervention.get(
            "allowed_configuration_ids",
            [],
        )
    }
    actual_configuration_ids = set(
        prediction_task.get("allowed_configurations", [])
    )
    if actual_configuration_ids != expected_configuration_ids:
        add_failure(
            failures,
            "prediction_task_allowed_configurations",
            "inputs/stage2-prediction.task.json",
            sorted(expected_configuration_ids),
            sorted(actual_configuration_ids),
        )
    expected_observation_ids = {
        observation_id
        for intervention in envelope_by_case.values()
        for observation_id in intervention.get("observation_ids", [])
    }
    actual_observation_id_list = [
        observation.get("observation_id")
        for observation in prediction_task.get("allowed_observations", [])
    ]
    if (
        len(actual_observation_id_list) != len(set(actual_observation_id_list))
        or set(actual_observation_id_list) != expected_observation_ids
    ):
        add_failure(
            failures,
            "prediction_task_allowed_observations",
            "inputs/stage2-prediction.task.json",
            sorted(expected_observation_ids),
            actual_observation_id_list,
        )

    for task_intervention in task_interventions:
        case_id = task_intervention.get("case_id")
        envelope_intervention = envelope_by_case[case_id]
        expected_ids = envelope_intervention.get("invariant_ids", [])
        actual_ids = task_intervention.get("invariant_ids", [])
        if actual_ids != expected_ids:
            add_failure(
                failures,
                "prediction_task_invariant_ids",
                f"inputs/stage2-prediction.task.json#{case_id}",
                expected_ids,
                actual_ids,
            )
        expected_specs = envelope_intervention.get("invariant_specs", [])
        actual_specs = task_intervention.get("invariant_specs", [])
        if actual_specs != expected_specs:
            add_failure(
                failures,
                "prediction_task_invariant_specs",
                f"inputs/stage2-prediction.task.json#{case_id}",
                expected_specs,
                actual_specs,
            )
        for field in (
            "baseline_value",
            "formal_input_spec",
            "initial_state_specs",
            "observation_ids",
            "stop_boundary_id",
            "stop_boundary_spec",
            "tolerance_specs",
            "variable_id",
            "variant_value",
        ):
            expected_value = envelope_intervention.get(field)
            actual_value = task_intervention.get(field)
            if actual_value != expected_value:
                add_failure(
                    failures,
                    f"prediction_task_{field}",
                    f"inputs/stage2-prediction.task.json#{case_id}",
                    expected_value,
                    actual_value,
                )


def contains_exact_scalar(value: Any, target: str) -> bool:
    if isinstance(value, dict):
        return any(
            contains_exact_scalar(child, target)
            for child in value.values()
        )
    if isinstance(value, list):
        return any(contains_exact_scalar(child, target) for child in value)
    return value == target


def check_controlled_variable_reference_closure(
    *,
    canonical_encoding: dict[str, Any],
    envelope: dict[str, Any],
    projection_spec: dict[str, Any],
    views: dict[str, dict[str, Any]],
    failures: list[dict[str, Any]],
) -> None:
    structural_fields = (
        "composition_edges",
        "operational_edges",
        "operational_records",
        "rules",
        "temporal_edges",
    )

    def check_cases(
        *,
        artifact_path: str,
        cases: list[dict[str, Any]],
        failure_kind: str,
    ) -> None:
        for case in cases:
            case_scope = case.get("case_scope", {})
            case_id = case_scope.get("case_id")
            controlled_variable_id = case_scope.get("controlled_variable_id")
            referenced = (
                isinstance(controlled_variable_id, str)
                and any(
                    contains_exact_scalar(case.get(field), controlled_variable_id)
                    for field in structural_fields
                )
            )
            if not referenced:
                add_failure(
                    failures,
                    failure_kind,
                    f"{artifact_path}#{case_id}",
                    (
                        "controlled_variable_id referenced by at least one "
                        "structural relationship or rule role"
                    ),
                    controlled_variable_id,
                )

    check_cases(
        artifact_path="source/canonical-encoding-v0.1.0.json",
        cases=canonical_encoding.get("cases", []),
        failure_kind="canonical_controlled_variable_reference_closure",
    )

    rich_projection_ids = {
        projection.get("projection_id")
        for projection in projection_spec.get("projections", [])
        if any(
            rule.get("operation") == "include_path"
            and rule.get("path") == "/cases"
            and rule.get("to_value") == "typed-structure-view"
            for rule in projection.get("rules", [])
        )
    }
    rich_views = [
        (path, view)
        for path, view in views.items()
        if view.get("projection_id") in rich_projection_ids
    ]
    if len(rich_views) != 1:
        add_failure(
            failures,
            "rich_projection_identification",
            "inputs/projection-spec.json",
            "exactly one generated typed-structure view",
            [
                {
                    "path": path,
                    "projection_id": view.get("projection_id"),
                }
                for path, view in rich_views
            ],
        )
        return
    rich_path, rich_view = rich_views[0]
    check_cases(
        artifact_path=rich_path,
        cases=rich_view.get("cases", []),
        failure_kind="rich_view_controlled_variable_reference_closure",
    )

    structural_remove_paths = {
        f"/cases/{field}"
        for field in structural_fields
    }
    atomic_projection_ids = {
        projection.get("projection_id")
        for projection in projection_spec.get("projections", [])
        if structural_remove_paths.issubset(
            {
                rule.get("path")
                for rule in projection.get("rules", [])
                if rule.get("operation") == "remove_path"
            }
        )
    }
    atomic_views = [
        (path, view)
        for path, view in views.items()
        if view.get("projection_id") in atomic_projection_ids
    ]
    if len(atomic_views) != 1:
        add_failure(
            failures,
            "atomic_projection_identification",
            "inputs/projection-spec.json",
            "exactly one generated boundary-only view",
            [
                {
                    "path": path,
                    "projection_id": view.get("projection_id"),
                }
                for path, view in atomic_views
            ],
        )
    else:
        atomic_path, atomic_view = atomic_views[0]
        for case in atomic_view.get("cases", []):
            case_scope = case.get("case_scope", {})
            case_id = case_scope.get("case_id")
            controlled_variable_id = case_scope.get("controlled_variable_id")
            retained = (
                isinstance(controlled_variable_id, str)
                and any(
                    contains_exact_scalar(
                        case.get(field),
                        controlled_variable_id,
                    )
                    for field in structural_fields
                )
            )
            if retained:
                add_failure(
                    failures,
                    "atomic_view_controlled_variable_duty_removed",
                    f"{atomic_path}#{case_id}",
                    "controlled-variable duty edge removed by projection",
                    controlled_variable_id,
                )

    envelope_by_case = {
        intervention.get("case_id"): intervention
        for intervention in envelope.get("case_interventions", [])
    }
    for case in rich_view.get("cases", []):
        case_scope = case.get("case_scope", {})
        case_id = case_scope.get("case_id")
        intervention = envelope_by_case.get(case_id)
        if intervention is None:
            continue
        formal_input_value = intervention.get("formal_input_spec")
        formal_input = (
            formal_input_value
            if isinstance(formal_input_value, dict)
            else {}
        )
        time_base = formal_input.get("time_base")
        time_base_id = (
            time_base.get("time_base_id")
            if isinstance(time_base, dict)
            else None
        )
        formal_input_id = formal_input.get("formal_input_id")
        if case_scope.get("formal_input_ref") != formal_input_id:
            add_failure(
                failures,
                "rich_view_formal_input_binding",
                f"{rich_path}#{case_id}",
                formal_input_id,
                case_scope.get("formal_input_ref"),
            )

        initial_field_ids = {
            spec.get("field_id")
            for spec in intervention.get("initial_state_specs", [])
            if isinstance(spec, dict)
        }
        event_field_ids = {
            field.get("field_id")
            for event in (
                formal_input.get("events")
                if isinstance(formal_input.get("events"), list)
                else []
            )
            if isinstance(event, dict)
            for field in event.get("fields", [])
            if isinstance(field, dict)
        }
        required_ids_by_roles = {
            formal_input_id: (
                "composition_edges",
                "operational_edges",
                "operational_records",
                "rules",
                "trace_contract",
            ),
            intervention.get("stop_boundary_id"): (
                "rules",
                "temporal_edges",
                "trace_contract",
            ),
            time_base_id: (
                "rules",
                "temporal_edges",
                "time_bases",
                "trace_contract",
            ),
            **{
                field_id: (
                    "operational_records",
                    "rules",
                    "state_channels",
                    "trace_contract",
                )
                for field_id in initial_field_ids | event_field_ids
            },
        }
        required_ids_by_roles.pop(None, None)
        missing_ids = sorted(
            identifier
            for identifier, allowed_roles in required_ids_by_roles.items()
            if not any(
                contains_exact_scalar(case.get(role), identifier)
                for role in allowed_roles
            )
        )
        if missing_ids:
            add_failure(
                failures,
                "rich_view_stage2_input_reference_closure",
                f"{rich_path}#{case_id}",
                "all neutral formal-input and initial-state IDs structurally referenced",
                missing_ids,
            )


def check_response_templates(
    *,
    envelope: dict[str, Any],
    prediction_template: dict[str, Any],
    reconstruction_template: dict[str, Any],
    failures: list[dict[str, Any]],
) -> None:
    observations_by_case = {
        intervention["case_id"]: set(intervention["observation_ids"])
        for intervention in envelope.get("case_interventions", [])
    }
    prediction_answers = prediction_template.get("template_payload", {}).get(
        "prediction_answers",
        [],
    )
    prediction_case_ids = [answer.get("case_id") for answer in prediction_answers]
    if len(prediction_case_ids) != len(set(prediction_case_ids)):
        add_failure(
            failures,
            "prediction_template_case_ids",
            "inputs/prediction-response.template.json",
            "one answer template per case",
            prediction_case_ids,
        )
    for answer in prediction_answers:
        case_id = answer.get("case_id")
        expected_pairs = {
            (configuration_id, observation_id)
            for configuration_id in ("config.baseline", "config.variant")
            for observation_id in observations_by_case.get(case_id, set())
        }
        actual_pairs = [
            (
                expectation.get("configuration_id"),
                expectation.get("observation_id"),
            )
            for expectation in answer.get("expectations", [])
        ]
        if len(actual_pairs) != len(set(actual_pairs)):
            add_failure(
                failures,
                "prediction_template_duplicate_pair",
                f"inputs/prediction-response.template.json#{case_id}",
                "unique configuration-observation pairs",
                actual_pairs,
            )
        if set(actual_pairs) != expected_pairs:
            add_failure(
                failures,
                "prediction_template_cartesian_product",
                f"inputs/prediction-response.template.json#{case_id}",
                sorted(expected_pairs),
                sorted(set(actual_pairs)),
            )

    reconstruction_answers = reconstruction_template.get("template_payload", {}).get(
        "reconstruction_answers",
        [],
    )
    reconstruction_case_ids = [
        answer.get("case_id")
        for answer in reconstruction_answers
    ]
    expected_case_ids = sorted(observations_by_case)
    if sorted(reconstruction_case_ids) != expected_case_ids:
        add_failure(
            failures,
            "reconstruction_template_case_coverage",
            "inputs/reconstruction-response.template.json",
            expected_case_ids,
            sorted(reconstruction_case_ids),
        )


def check_execution_plan(
    *,
    entries_by_path: dict[str, dict[str, Any]],
    envelope: dict[str, Any],
    fixture_lock: dict[str, Any],
    plan: dict[str, Any],
    repo_root: Path,
    run_dir: Path,
    failures: list[dict[str, Any]],
) -> None:
    fixture_entry = entries_by_path.get("fixtures/fixture-lock.json")
    fixture_reference = plan.get("fixture_lock")
    if fixture_entry is not None:
        expected_fixture_reference = {
            "path": "fixtures/fixture-lock.json",
            "sha256": fixture_entry["sha256"],
        }
        actual_run_relative = None
        if isinstance(fixture_reference, dict):
            actual_run_relative = to_run_relative(
                fixture_reference["path"],
                repo_root=repo_root,
                run_dir=run_dir,
            )
        actual_fixture_reference = {
            "path": actual_run_relative,
            "sha256": (
                fixture_reference.get("sha256")
                if isinstance(fixture_reference, dict)
                else None
            ),
        }
        if actual_fixture_reference != expected_fixture_reference:
            add_failure(
                failures,
                "execution_plan_fixture_binding",
                "execution/execution-plan.json",
                expected_fixture_reference,
                actual_fixture_reference,
            )

    cases = plan.get("cases", [])
    case_ids = [case.get("case_id") for case in cases]
    expected_case_ids = {"CA-R1", "CA-R2", "CA-R3", "NEG-01"}
    if set(case_ids) != expected_case_ids or len(case_ids) != len(expected_case_ids):
        add_failure(
            failures,
            "execution_plan_case_coverage",
            "execution/execution-plan.json",
            sorted(expected_case_ids),
            case_ids,
        )

    lock_by_case = {
        case["case_id"]: case
        for case in fixture_lock.get("cases", [])
    }
    envelope_by_case = {
        intervention["case_id"]: intervention
        for intervention in envelope.get("case_interventions", [])
    }
    plan_by_case = {
        case["case_id"]: case
        for case in cases
    }

    for case_id in ("CA-R1", "CA-R2", "CA-R3"):
        case_plan = plan_by_case.get(case_id)
        case_lock = lock_by_case.get(case_id)
        intervention = envelope_by_case.get(case_id)
        if case_plan is None or case_lock is None or intervention is None:
            continue
        if case_plan.get("negative_control") is not False:
            add_failure(
                failures,
                "execution_plan_case_role",
                f"execution/execution-plan.json#{case_id}",
                False,
                case_plan.get("negative_control"),
            )
        if case_plan.get("source_commit") != case_lock["source_identity"]["commit_sha"]:
            add_failure(
                failures,
                "execution_plan_source_binding",
                f"execution/execution-plan.json#{case_id}",
                case_lock["source_identity"]["commit_sha"],
                case_plan.get("source_commit"),
            )
        expected_input = case_lock["formal_input_artifacts"][0]
        actual_input = case_plan.get("formal_input")
        if actual_input != expected_input:
            add_failure(
                failures,
                "execution_plan_formal_input_binding",
                f"execution/execution-plan.json#{case_id}",
                expected_input,
                actual_input,
            )
        expected_stop = case_lock["stop_boundary_id"]
        if case_plan.get("stop_boundary_id") != expected_stop:
            add_failure(
                failures,
                "execution_plan_stop_boundary_binding",
                f"execution/execution-plan.json#{case_id}",
                expected_stop,
                case_plan.get("stop_boundary_id"),
            )
        if intervention.get("stop_boundary_id") != expected_stop:
            add_failure(
                failures,
                "variant_envelope_stop_boundary_binding",
                f"inputs/stage2-variant-envelope.json#{case_id}",
                expected_stop,
                intervention.get("stop_boundary_id"),
            )

        lock_invariants = set(case_lock.get("invariant_ids", []))
        plan_invariants = {
            invariant.get("invariant_id")
            for invariant in case_plan.get("invariants", [])
        }
        envelope_invariants = set(intervention.get("invariant_ids", []))
        if not (lock_invariants == plan_invariants == envelope_invariants):
            add_failure(
                failures,
                "invariant_binding",
                f"execution/execution-plan.json#{case_id}",
                sorted(lock_invariants),
                {
                    "envelope": sorted(envelope_invariants),
                    "plan": sorted(plan_invariants),
                },
            )

        configuration_ids = [
            configuration.get("configuration_id")
            for configuration in case_plan.get("configurations", [])
        ]
        semantic_roles = [
            configuration.get("semantic_role")
            for configuration in case_plan.get("configurations", [])
        ]
        expected_configurations = ["config.baseline", "config.variant"]
        expected_roles = ["baseline", "variant"]
        if sorted(configuration_ids) != expected_configurations:
            add_failure(
                failures,
                "execution_plan_configurations",
                f"execution/execution-plan.json#{case_id}",
                expected_configurations,
                sorted(configuration_ids),
            )
        if sorted(semantic_roles) != expected_roles:
            add_failure(
                failures,
                "execution_plan_semantic_roles",
                f"execution/execution-plan.json#{case_id}",
                expected_roles,
                sorted(semantic_roles),
            )

        locked_fixture_refs = {
            (reference["path"], reference["sha256"])
            for reference in case_lock.get("fixture_artifacts", [])
        }
        for patch_set_name in (
            "compatibility_patch_set",
            "observation_patch_set",
            "variant_patch_set",
        ):
            patch_set = case_lock.get(patch_set_name, {})
            locked_fixture_refs.update(
                (reference["path"], reference["sha256"])
                for reference in (
                    patch_set.get("artifacts", [])
                    + patch_set.get("configuration_artifacts", [])
                )
            )
        planned_fixture_refs = {
            (reference["path"], reference["sha256"])
            for configuration in case_plan.get("configurations", [])
            for reference in configuration.get("fixture_artifacts", [])
        }
        if not planned_fixture_refs.issubset(locked_fixture_refs):
            add_failure(
                failures,
                "execution_plan_fixture_artifacts",
                f"execution/execution-plan.json#{case_id}",
                sorted(locked_fixture_refs),
                sorted(planned_fixture_refs),
            )

        locked_comparators = {
            (reference["path"], reference["sha256"])
            for reference in case_lock.get("comparator_artifacts", [])
        }
        planned_comparators = {
            (
                comparator["implementation"]["path"],
                comparator["implementation"]["sha256"],
            )
            for comparator in case_plan.get("comparators", [])
        }
        if planned_comparators != locked_comparators:
            add_failure(
                failures,
                "execution_plan_comparator_binding",
                f"execution/execution-plan.json#{case_id}",
                sorted(locked_comparators),
                sorted(planned_comparators),
            )

        plan_observations = {
            observation_id
            for comparator in case_plan.get("comparators", [])
            for observation_id in comparator.get("allowed_observation_ids", [])
        }
        envelope_observations = set(intervention.get("observation_ids", []))
        if plan_observations != envelope_observations:
            add_failure(
                failures,
                "observation_binding",
                f"execution/execution-plan.json#{case_id}",
                sorted(envelope_observations),
                sorted(plan_observations),
            )

        plan_tolerances = {
            tolerance.get("tolerance_rule_id")
            for comparator in case_plan.get("comparators", [])
            for tolerance in comparator.get("tolerance_rules", [])
        }
        lock_tolerances = set(case_lock.get("tolerance_rule_ids", []))
        envelope_tolerances = set(intervention.get("tolerance_rule_ids", []))
        if not (plan_tolerances == lock_tolerances == envelope_tolerances):
            add_failure(
                failures,
                "tolerance_binding",
                f"execution/execution-plan.json#{case_id}",
                sorted(lock_tolerances),
                {
                    "envelope": sorted(envelope_tolerances),
                    "plan": sorted(plan_tolerances),
                },
            )

    negative_control = plan_by_case.get("NEG-01")
    if negative_control is not None:
        if negative_control.get("negative_control") is not True:
            add_failure(
                failures,
                "negative_control_role",
                "execution/execution-plan.json#NEG-01",
                True,
                negative_control.get("negative_control"),
            )
        negative_roles = sorted(
            configuration.get("semantic_role")
            for configuration in negative_control.get("configurations", [])
        )
        expected_negative_roles = [
            "negative_control_a",
            "negative_control_b",
        ]
        if negative_roles != expected_negative_roles:
            add_failure(
                failures,
                "negative_control_configurations",
                "execution/execution-plan.json#NEG-01",
                expected_negative_roles,
                negative_roles,
            )
        r3_plan = plan_by_case.get("CA-R3")
        if r3_plan is not None:
            for field_name in (
                "formal_input",
                "source_commit",
                "stop_boundary_id",
                "time_base_ids",
            ):
                if negative_control.get(field_name) != r3_plan.get(field_name):
                    add_failure(
                        failures,
                        "negative_control_r3_binding",
                        f"execution/execution-plan.json#NEG-01/{field_name}",
                        r3_plan.get(field_name),
                        negative_control.get(field_name),
                    )
            r3_invariants = {
                invariant.get("invariant_id")
                for invariant in r3_plan.get("invariants", [])
            }
            negative_invariants = {
                invariant.get("invariant_id")
                for invariant in negative_control.get("invariants", [])
            }
            if negative_invariants != r3_invariants:
                add_failure(
                    failures,
                    "negative_control_r3_invariants",
                    "execution/execution-plan.json#NEG-01",
                    sorted(r3_invariants),
                    sorted(negative_invariants),
                )


def check_execution_plan_preparation(
    *,
    entry: dict[str, Any] | None,
    plan: dict[str, Any],
    failures: list[dict[str, Any]],
) -> None:
    """Recognize an honest blocked draft without accepting it at the human gate."""

    if entry is None:
        return
    if entry.get("schema_path") != EXECUTION_PLAN_PREPARATION_SCHEMA:
        add_failure(
            failures,
            "execution_plan_preparation_schema",
            "execution/execution-plan.json",
            EXECUTION_PLAN_PREPARATION_SCHEMA,
            entry.get("schema_path"),
        )

    expected_execution_state = {
        "formal_comparator_started": False,
        "formal_execution_permit_created": False,
        "formal_fixture_started": False,
        "formal_input_content_embedded_in_plan": False,
        "formal_input_executed": False,
        "formal_result_created": False,
        "human_gate_authorization_created": False,
        "prediction_set_created": False,
        "truth_commitment_created": False,
    }
    if plan.get("execution_state") != expected_execution_state:
        add_failure(
            failures,
            "execution_plan_preparation_state",
            "execution/execution-plan.json",
            expected_execution_state,
            plan.get("execution_state"),
        )

    cases = plan.get("case_preparations", [])
    actual_case_ids = [
        case.get("case_id")
        for case in cases
        if isinstance(case, dict)
    ]
    expected_case_ids = ["CA-R1", "CA-R2", "CA-R3"]
    if actual_case_ids != expected_case_ids:
        add_failure(
            failures,
            "execution_plan_preparation_case_coverage",
            "execution/execution-plan.json",
            expected_case_ids,
            actual_case_ids,
        )

    case_by_id = {
        case.get("case_id"): case
        for case in cases
        if isinstance(case, dict)
    }
    r1 = case_by_id.get("CA-R1", {})
    r1_blocker_ids = [
        blocker.get("blocker_id")
        for blocker in r1.get("blockers", [])
        if isinstance(blocker, dict)
    ]
    if (
        r1.get("preparation_status") != "blocked"
        or r1_blocker_ids != ["r1.legal-unity-license-activation"]
    ):
        add_failure(
            failures,
            "execution_plan_preparation_r1_blocker",
            "execution/execution-plan.json#CA-R1",
            {
                "blocker_ids": ["r1.legal-unity-license-activation"],
                "preparation_status": "blocked",
            },
            {
                "blocker_ids": r1_blocker_ids,
                "preparation_status": r1.get("preparation_status"),
            },
        )

    successor = plan.get("successor_plan_schema")
    successor_path = (
        successor.get("path")
        if isinstance(successor, dict)
        else None
    )
    if successor_path != FINAL_EXECUTION_PLAN_SCHEMA:
        add_failure(
            failures,
            "execution_plan_preparation_successor",
            "execution/execution-plan.json",
            FINAL_EXECUTION_PLAN_SCHEMA,
            successor_path,
        )

    add_failure(
        failures,
        "execution_plan_not_final",
        "execution/execution-plan.json",
        (
            "final execution_plan bound to passed formal build readiness "
            "and fixtures/fixture-lock.json"
        ),
        {
            "artifact_type": plan.get("artifact_type"),
            "global_blocker_ids": plan.get("global_blocker_ids"),
            "plan_status": plan.get("plan_status"),
        },
    )


def check_projection_audit_semantics(
    *,
    projection_audit: dict[str, Any],
    encoding_audit: dict[str, Any] | None,
    failures: list[dict[str, Any]],
) -> None:
    projection_actor = projection_audit.get("actor")
    if (
        not isinstance(projection_actor, dict)
        or projection_actor.get("role") != "source_auditor"
        or not isinstance(projection_actor.get("identifier"), str)
        or not projection_actor.get("identifier")
        or not isinstance(projection_actor.get("session_id"), str)
        or not projection_actor.get("session_id")
    ):
        add_failure(
            failures,
            "projection_audit_actor_identity",
            "source/projection-audit-v0.1.0.json",
            {
                "identifier": "non-empty string",
                "role": "source_auditor",
                "session_id": "non-empty string",
            },
            (
                projection_actor
                if isinstance(projection_actor, dict)
                else {"actor": None}
            ),
        )
    encoding_actor = (
        encoding_audit.get("actor")
        if isinstance(encoding_audit, dict)
        else None
    )
    if not isinstance(encoding_actor, dict):
        add_failure(
            failures,
            "projection_audit_independence_basis",
            "source/encoding-audit-v0.1.0.json",
            "actor object with identifier and session_id",
            encoding_actor,
        )
    elif isinstance(projection_actor, dict):
        reused_identity_fields = [
            field_name
            for field_name in ("identifier", "session_id")
            if projection_actor.get(field_name)
            == encoding_actor.get(field_name)
        ]
        if reused_identity_fields:
            add_failure(
                failures,
                "projection_audit_independence",
                "source/projection-audit-v0.1.0.json",
                {
                    "different_from": (
                        "source/encoding-audit-v0.1.0.json#actor"
                    ),
                    "identity_fields": [
                        "identifier",
                        "session_id",
                    ],
                },
                {
                    "reused_fields": reused_identity_fields,
                    "source_auditor": projection_actor,
                },
            )
    if projection_audit.get("audit_decision") != "approved":
        add_failure(
            failures,
            "projection_audit_decision",
            "source/projection-audit-v0.1.0.json",
            "approved",
            projection_audit.get("audit_decision"),
        )
    audit_checks = projection_audit.get("audit_checks", [])
    check_ids = [
        check.get("check_id")
        for check in audit_checks
        if isinstance(check, dict)
    ]
    all_checks_passed = (
        len(audit_checks) == len(REQUIRED_AUDIT_CHECKS)
        and len(check_ids) == len(REQUIRED_AUDIT_CHECKS)
        and set(check_ids) == REQUIRED_AUDIT_CHECKS
        and len(check_ids) == len(set(check_ids))
        and all(
            check.get("status") == "passed"
            for check in audit_checks
            if isinstance(check, dict)
        )
    )
    if not all_checks_passed:
        add_failure(
            failures,
            "projection_audit_passes",
            "source/projection-audit-v0.1.0.json",
            {
                "check_ids": sorted(REQUIRED_AUDIT_CHECKS),
                "count": len(REQUIRED_AUDIT_CHECKS),
                "status": "passed for every exact-one record",
            },
            audit_checks,
        )
    incident_check = next(
        (
            check
            for check in audit_checks
            if isinstance(check, dict)
            and check.get("check_id") == "protocol_incident_disposition"
        ),
        None,
    )
    incident_artifact_id = (
        "audit.protocol-incident.r3-byte-integrity-read-v0.1.0"
    )
    if (
        not isinstance(incident_check, dict)
        or incident_artifact_id
        not in incident_check.get("target_artifact_ids", [])
    ):
        add_failure(
            failures,
            "projection_audit_protocol_incident_target",
            "source/projection-audit-v0.1.0.json"
            "#protocol_incident_disposition",
            incident_artifact_id,
            (
                None
                if not isinstance(incident_check, dict)
                else incident_check.get("target_artifact_ids")
            ),
        )
    expected_source_audit_fields = {
        "condition_id": None,
        "findings": [],
        "packaging": None,
        "pollution": None,
        "prediction_answers": [],
        "prior_stage_submission_sha256": None,
        "raw_payload": None,
        "reconstruction_answers": [],
    }
    actual_source_audit_fields = {
        field_name: projection_audit.get(field_name)
        for field_name in expected_source_audit_fields
    }
    if actual_source_audit_fields != expected_source_audit_fields:
        add_failure(
            failures,
            "projection_audit_approved_shape",
            "source/projection-audit-v0.1.0.json",
            expected_source_audit_fields,
            actual_source_audit_fields,
        )


def self_test_projection_audit_semantics(
    repo_root: Path,
) -> dict[str, Any]:
    encoding_actor = {
        "actor": {
            "identifier": "actor.encoding",
            "session_id": "session.encoding",
        }
    }
    base = {
        "actor": {
            "identifier": "actor.projection",
            "role": "source_auditor",
            "session_id": "session.projection",
        },
        "audit_checks": [
            {
                "check_id": check_id,
                "evidence": "synthetic evidence",
                "status": "passed",
                "target_artifact_ids": (
                    [
                        "audit.protocol-incident."
                        "r3-byte-integrity-read-v0.1.0"
                    ]
                    if check_id == "protocol_incident_disposition"
                    else ["synthetic.input"]
                ),
            }
            for check_id in sorted(REQUIRED_AUDIT_CHECKS)
        ],
        "audit_decision": "approved",
        "condition_id": None,
        "findings": [],
        "packaging": None,
        "pollution": None,
        "prediction_answers": [],
        "prior_stage_submission_sha256": None,
        "raw_payload": None,
        "reconstruction_answers": [],
    }
    controls: dict[str, bool] = {}

    def rejected(label: str, mutation: Any) -> None:
        candidate = json.loads(json.dumps(base))
        mutation(candidate)
        local_failures: list[dict[str, Any]] = []
        check_projection_audit_semantics(
            projection_audit=candidate,
            encoding_audit=encoding_actor,
            failures=local_failures,
        )
        controls[label] = bool(local_failures)

    accepted_failures: list[dict[str, Any]] = []
    check_projection_audit_semantics(
        projection_audit=base,
        encoding_audit=encoding_actor,
        failures=accepted_failures,
    )
    if accepted_failures:
        raise RuntimeError(
            f"valid projection audit failed semantic self-test: "
            f"{accepted_failures}"
        )
    rejected(
        "same_identifier",
        lambda value: value["actor"].update(
            {"identifier": "actor.encoding"}
        ),
    )
    rejected(
        "same_session",
        lambda value: value["actor"].update(
            {"session_id": "session.encoding"}
        ),
    )
    rejected(
        "missing_identifier",
        lambda value: value["actor"].pop("identifier"),
    )
    rejected(
        "duplicate_check",
        lambda value: value["audit_checks"].__setitem__(
            1, dict(value["audit_checks"][0])
        ),
    )
    rejected(
        "failed_duplicate_of_passed",
        lambda value: value["audit_checks"].append(
            {
                **dict(value["audit_checks"][0]),
                "status": "failed",
            }
        ),
    )
    rejected(
        "incident_check_without_incident_target",
        lambda value: next(
            check
            for check in value["audit_checks"]
            if check["check_id"] == "protocol_incident_disposition"
        ).update({"target_artifact_ids": ["synthetic.input"]}),
    )
    rejected(
        "approved_with_findings",
        lambda value: value.update({"findings": ["synthetic contradiction"]}),
    )
    if not all(controls.values()):
        raise RuntimeError(
            f"projection-audit semantic negative control failed: {controls}"
        )
    incident_path = (
        repo_root
        / "research/calibration-tests/continuous-action-pilot/"
        "runs/continuous-001/source/"
        "protocol-incident-r3-byte-integrity-read-v0.1.0.json"
    )
    incident = load_json(incident_path)
    incident_entries = {
        "fixtures/r3/formal-input-r3-v0.1.0.json": {
            "artifact_id": "fixture.r3.formal-input-v0.1.0",
            "path": "fixtures/r3/formal-input-r3-v0.1.0.json",
        }
    }
    incident_failures: list[dict[str, Any]] = []
    check_protocol_incident(
        incident=incident,
        entries_by_path=incident_entries,
        failures=incident_failures,
    )
    if incident_failures:
        raise RuntimeError(
            "valid protocol incident failed semantic self-test: "
            f"{incident_failures}"
        )
    denied_read = json.loads(json.dumps(incident))
    denied_read["aggregate_state"]["formal_input_byte_read"] = False
    denied_read_failures: list[dict[str, Any]] = []
    check_protocol_incident(
        incident=denied_read,
        entries_by_path=incident_entries,
        failures=denied_read_failures,
    )
    controls["incident_denied_byte_read"] = bool(denied_read_failures)
    if not controls["incident_denied_byte_read"]:
        raise RuntimeError(
            "protocol-incident semantic negative control failed"
        )
    return {
        "negative_controls": sorted(controls),
        "negative_controls_passed": len(controls),
        "positive_controls_passed": 1,
        "status": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--require-frozen", action="store_true")
    parser.add_argument(
        "--self-test-projection-audit-semantics",
        action="store_true",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    if args.self_test_projection_audit_semantics:
        print(
            json.dumps(
                self_test_projection_audit_semantics(repo_root),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.manifest is None:
        parser.error("manifest is required outside semantic self-test mode")
    manifest_path = args.manifest.resolve()
    run_dir = manifest_path.parent
    failures: list[dict[str, Any]] = []

    verifier_path = repo_root / "research/calibration-tests/continuous-action-pilot/tools/verify-run-package.py"
    verifier_command = [
        sys.executable,
        str(verifier_path),
        str(manifest_path),
        "--repo-root",
        str(repo_root),
    ]
    if args.require_frozen:
        verifier_command.append("--require-frozen")
    package_result = subprocess.run(
        verifier_command,
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        package_report = json.loads(package_result.stdout)
    except json.JSONDecodeError:
        package_report = {
            "stderr": package_result.stderr,
            "stdout": package_result.stdout,
        }
    if package_result.returncode != 0:
        add_failure(
            failures,
            "package_verifier",
            manifest_path.as_posix(),
            "passed",
            package_report,
        )

    manifest = load_json(manifest_path)
    if manifest.get("artifact_type") != "formal_run_manifest":
        add_failure(
            failures,
            "manifest_type",
            "manifest.json",
            "formal_run_manifest",
            manifest.get("artifact_type"),
        )
    if manifest.get("run_id") != "continuous-001":
        add_failure(
            failures,
            "run_id",
            "manifest.json",
            "continuous-001",
            manifest.get("run_id"),
        )
    if manifest.get("truth_commitment") is None:
        add_failure(
            failures,
            "truth_commitment",
            "manifest.json",
            "sealed non-null commitment",
            None,
        )

    entries_by_path = {
        entry["path"]: entry
        for entry in manifest.get("artifacts", [])
    }
    for relative_path, must_be_frozen in REQUIRED_PATHS.items():
        entry = entries_by_path.get(relative_path)
        if entry is None:
            add_failure(
                failures,
                "required_artifact",
                relative_path,
                "manifested pre-gate artifact",
                None,
            )
            continue
        if must_be_frozen and not entry.get("included_in_frozen_set"):
            add_failure(
                failures,
                "required_artifact_frozen",
                relative_path,
                True,
                entry.get("included_in_frozen_set"),
            )

    for relative_path, schema_path in SCHEMA_PATHS.items():
        entry = entries_by_path.get(relative_path)
        if entry is not None and entry.get("schema_path") != schema_path:
            add_failure(
                failures,
                "required_schema",
                relative_path,
                schema_path,
                entry.get("schema_path"),
            )

    for relative_path in entries_by_path:
        if relative_path in POST_GATE_PATHS or relative_path.startswith(POST_GATE_PREFIXES):
            add_failure(
                failures,
                "post_gate_artifact_present",
                relative_path,
                "absent before human gate",
                "manifested",
            )

    incident_path = (
        run_dir
        / "source/protocol-incident-r3-byte-integrity-read-v0.1.0.json"
    )
    if incident_path.is_file():
        check_protocol_incident(
            incident=load_json(incident_path),
            entries_by_path=entries_by_path,
            failures=failures,
        )

    fixture_path = run_dir / "fixtures/fixture-lock.json"
    fixture_lock = None
    if fixture_path.is_file():
        fixture_lock = load_json(fixture_path)
        check_fixture_lock(
            fixture_lock=fixture_lock,
            entries_by_path=entries_by_path,
            repo_root=repo_root,
            run_dir=run_dir,
            failures=failures,
        )

    build_readiness_path = run_dir / "fixtures/formal-build-readiness-v0.1.0.json"
    if fixture_lock is not None and build_readiness_path.is_file():
        check_formal_build_readiness(
            readiness=load_json(build_readiness_path),
            fixture_lock=fixture_lock,
            entries_by_path=entries_by_path,
            repo_root=repo_root,
            run_dir=run_dir,
            failures=failures,
        )

    envelope_path = run_dir / "inputs/stage2-variant-envelope.json"
    envelope = None
    if envelope_path.is_file():
        envelope = load_json(envelope_path)
        check_variant_envelope(envelope, failures)
        prediction_task_path = run_dir / "inputs/stage2-prediction.task.json"
        if prediction_task_path.is_file():
            check_prediction_task_bindings(
                envelope=envelope,
                prediction_task=load_json(prediction_task_path),
                repo_root=repo_root,
                run_dir=run_dir,
                failures=failures,
            )
        prediction_template_path = run_dir / "inputs/prediction-response.template.json"
        reconstruction_template_path = run_dir / "inputs/reconstruction-response.template.json"
        if prediction_template_path.is_file() and reconstruction_template_path.is_file():
            check_response_templates(
                envelope=envelope,
                prediction_template=load_json(prediction_template_path),
                reconstruction_template=load_json(reconstruction_template_path),
                failures=failures,
            )

    canonical_encoding_path = run_dir / "source/canonical-encoding-v0.1.0.json"
    projection_spec_path = run_dir / "inputs/projection-spec.json"
    rich_view_candidate_paths = (
        "inputs/stage1-view-v01.json",
        "inputs/stage1-view-v02.json",
    )
    if (
        envelope is not None
        and canonical_encoding_path.is_file()
        and projection_spec_path.is_file()
        and all((run_dir / path).is_file() for path in rich_view_candidate_paths)
    ):
        check_controlled_variable_reference_closure(
            canonical_encoding=load_json(canonical_encoding_path),
            envelope=envelope,
            projection_spec=load_json(projection_spec_path),
            views={
                path: load_json(run_dir / path)
                for path in rich_view_candidate_paths
            },
            failures=failures,
        )

    execution_plan_path = run_dir / "execution/execution-plan.json"
    if execution_plan_path.is_file():
        execution_plan = load_json(execution_plan_path)
        execution_plan_entry = entries_by_path.get("execution/execution-plan.json")
        artifact_type = execution_plan.get("artifact_type")
        if artifact_type == "execution_plan_preparation":
            check_execution_plan_preparation(
                entry=execution_plan_entry,
                plan=execution_plan,
                failures=failures,
            )
        elif artifact_type == "execution_plan":
            if (
                execution_plan_entry is not None
                and execution_plan_entry.get("schema_path")
                != FINAL_EXECUTION_PLAN_SCHEMA
            ):
                add_failure(
                    failures,
                    "execution_plan_schema",
                    "execution/execution-plan.json",
                    FINAL_EXECUTION_PLAN_SCHEMA,
                    execution_plan_entry.get("schema_path"),
                )
            if fixture_lock is not None and envelope is not None:
                check_execution_plan(
                    entries_by_path=entries_by_path,
                    envelope=envelope,
                    fixture_lock=fixture_lock,
                    plan=execution_plan,
                    repo_root=repo_root,
                    run_dir=run_dir,
                    failures=failures,
                )
        else:
            add_failure(
                failures,
                "execution_plan_type",
                "execution/execution-plan.json",
                [
                    "execution_plan_preparation",
                    "execution_plan",
                ],
                artifact_type,
            )

    projection_task_path = run_dir / "inputs/projection-audit.task.json"
    projection_task = None
    if projection_task_path.is_file():
        projection_task = load_json(projection_task_path)
        if projection_task.get("artifact_type") != "projection_audit_task_packet":
            add_failure(
                failures,
                "projection_audit_task_type",
                "inputs/projection-audit.task.json",
                "projection_audit_task_packet",
                projection_task.get("artifact_type"),
            )
        actual_check_list = projection_task.get("required_audit_checks", [])
        actual_checks = set(actual_check_list)
        if (
            actual_checks != REQUIRED_AUDIT_CHECKS
            or len(actual_check_list) != len(REQUIRED_AUDIT_CHECKS)
        ):
            add_failure(
                failures,
                "projection_audit_checks",
                "inputs/projection-audit.task.json",
                sorted(REQUIRED_AUDIT_CHECKS),
                actual_check_list,
            )
        input_paths: list[str] = []
        input_artifact_ids: list[str] = []
        for reference in projection_task.get("input_artifacts", []):
            run_relative = to_run_relative(
                reference["path"],
                repo_root=repo_root,
                run_dir=run_dir,
            )
            input_paths.append(run_relative or reference["path"])
            input_artifact_ids.append(reference["artifact_id"])
        if (
            set(input_paths) != REQUIRED_AUDIT_INPUTS
            or len(input_paths) != len(REQUIRED_AUDIT_INPUTS)
            or len(input_artifact_ids) != len(set(input_artifact_ids))
        ):
            add_failure(
                failures,
                "projection_audit_inputs",
                "inputs/projection-audit.task.json",
                sorted(REQUIRED_AUDIT_INPUTS),
                {
                    "artifact_ids": input_artifact_ids,
                    "paths": input_paths,
                },
            )
        projection_materializer = (
            repo_root
            / "research/calibration-tests/continuous-action-pilot/tools/"
            "materialize-projection-audit-task.py"
        )
        deterministic_result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(projection_materializer),
                "verify",
                "--repo-root",
                str(repo_root),
                "--run-dir",
                str(run_dir),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        try:
            deterministic_report = json.loads(
                deterministic_result.stdout
            )
        except json.JSONDecodeError:
            deterministic_report = {
                "stderr": deterministic_result.stderr,
                "stdout": deterministic_result.stdout,
            }
        if deterministic_result.returncode != 0:
            add_failure(
                failures,
                "projection_audit_task_deterministic_verification",
                "inputs/projection-audit.task.json",
                "exact deterministic materialization",
                deterministic_report,
            )

    projection_audit_path = run_dir / "source/projection-audit-v0.1.0.json"
    if projection_audit_path.is_file():
        projection_audit = load_json(projection_audit_path)
        if projection_audit.get("artifact_type") != "source_fidelity_audit":
            add_failure(
                failures,
                "projection_audit_artifact_type",
                "source/projection-audit-v0.1.0.json",
                "source_fidelity_audit",
                projection_audit.get("artifact_type"),
            )
        if projection_audit.get("stage") != "source_audit":
            add_failure(
                failures,
                "projection_audit_stage",
                "source/projection-audit-v0.1.0.json",
                "source_audit",
                projection_audit.get("stage"),
            )
        encoding_audit_path = run_dir / "source/encoding-audit-v0.1.0.json"
        encoding_audit = (
            load_json(encoding_audit_path)
            if encoding_audit_path.is_file()
            else None
        )
        check_projection_audit_semantics(
            projection_audit=projection_audit,
            encoding_audit=encoding_audit,
            failures=failures,
        )
        if projection_task is not None:
            if projection_audit.get("task_id") != projection_task.get("task_id"):
                add_failure(
                    failures,
                    "projection_audit_task_binding",
                    "source/projection-audit-v0.1.0.json",
                    projection_task.get("task_id"),
                    projection_audit.get("task_id"),
                )
            task_inputs = {
                (reference["artifact_id"], reference["sha256"])
                for reference in projection_task.get("input_artifacts", [])
            }
            projection_task_entry = entries_by_path.get(
                "inputs/projection-audit.task.json"
            )
            expected_audit_inputs = set(task_inputs)
            if projection_task_entry is not None:
                expected_audit_inputs.add(
                    (
                        projection_task_entry["artifact_id"],
                        projection_task_entry["sha256"],
                    )
                )
            audit_inputs = {
                (reference["artifact_id"], reference["sha256"])
                for reference in projection_audit.get("input_artifacts", [])
            }
            audit_input_list = projection_audit.get("input_artifacts", [])
            if (
                audit_inputs != expected_audit_inputs
                or len(audit_input_list) != len(expected_audit_inputs)
            ):
                add_failure(
                    failures,
                    "projection_audit_input_binding",
                    "source/projection-audit-v0.1.0.json",
                    sorted(expected_audit_inputs),
                    sorted(audit_inputs),
                )
            task_input_ids = {
                reference["artifact_id"]
                for reference in projection_task.get("input_artifacts", [])
            }
            if projection_task_entry is not None:
                task_input_ids.add(projection_task_entry["artifact_id"])
            for check in projection_audit.get("audit_checks", []):
                unknown_targets = sorted(
                    set(check.get("target_artifact_ids", [])) - task_input_ids
                )
                if unknown_targets:
                    add_failure(
                        failures,
                        "projection_audit_check_targets",
                        f"source/projection-audit-v0.1.0.json#{check.get('check_id')}",
                        sorted(task_input_ids),
                        unknown_targets,
                    )

    result = {
        "failure_count": len(failures),
        "failures": failures,
        "manifest": manifest_path.relative_to(repo_root).as_posix(),
        "package_verifier": package_report,
        "require_frozen": args.require_frozen,
        "status": "failed" if failures else "passed",
        "verifier_executed_formal_input": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
