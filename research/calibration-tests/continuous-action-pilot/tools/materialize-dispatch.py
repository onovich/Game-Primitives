#!/usr/bin/env python3
"""Materialize and verify continuous-001 dispatch receipts and its cohort lock.

This tool never dispatches a participant message. It only creates new, hash-bound
facility receipts after all inputs already exist. Template files are immutable
plans and are never valid output paths.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
from collections import Counter, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


RUN_ID = "continuous-001"
SEATS = ("p01", "p02", "p03", "p04")
URL_PREFIX = "https://github.com/onovich/Game-Primitives/blob/main/"
BASE = "research/calibration-tests/continuous-action-pilot"
RUN = f"{BASE}/runs/{RUN_ID}"
INPUTS = f"{RUN}/inputs"
SCHEMA = f"{BASE}/schema"

STAGE1_SCHEMA_PATH = f"{SCHEMA}/stage1-seat-dispatch-envelope-0.1.0.schema.json"
STAGE2_SCHEMA_PATH = f"{SCHEMA}/stage2-seat-dispatch-envelope-0.1.0.schema.json"
COHORT_SCHEMA_PATH = f"{SCHEMA}/stage1-cohort-lock-0.1.0.schema.json"
COHORT_LOCK_PATH = f"{RUN}/submissions/dispatch/stage1-cohort-lock.json"
AUTHORIZATION_SCHEMA_PATH = (
    f"{SCHEMA}/formal-human-gate-authorization-0.1.0.schema.json"
)
AUTHORIZATION_PATH = (
    f"{RUN}/submissions/dispatch/human-gate-authorization.json"
)
FORMAL_BUILD_READINESS_PATH = (
    f"{RUN}/fixtures/formal-build-readiness-v0.1.0.json"
)
FIXTURE_LOCK_PATH = f"{RUN}/fixtures/fixture-lock.json"
PROJECTION_AUDIT_PATH = f"{RUN}/source/projection-audit-v0.1.0.json"
PROTOCOL_INCIDENT_SCHEMA_PATH = (
    f"{SCHEMA}/protocol-incident-0.1.0.schema.json"
)
PROTOCOL_INCIDENT_PATH = (
    f"{RUN}/source/protocol-incident-r3-byte-integrity-read-v0.1.0.json"
)
PROTOCOL_INCIDENT_ID = (
    "incident.r3.formal-input-byte-integrity-read.v0.1.0"
)
FORMAL_READINESS_VERIFIER_PATH = f"{BASE}/tools/verify-formal-readiness.py"
DISPATCH_MATERIALIZER_PATH = f"{BASE}/tools/materialize-dispatch.py"
SUBMISSION_BUILDER_PATH = f"{BASE}/tools/build-role-submission.py"
EXECUTION_PERMIT_SCHEMA_PATH = (
    f"{SCHEMA}/formal-execution-permit-0.1.0.schema.json"
)
EXECUTION_PERMIT_MATERIALIZER_PATH = (
    f"{BASE}/tools/materialize-execution-permit.py"
)
EXECUTION_PERMIT_VERIFIER_PATH = (
    f"{BASE}/tools/verify-formal-execution-permit.py"
)
FORMAL_COMPARATOR_OUTPUT_SCHEMA_PATH = (
    f"{SCHEMA}/formal-comparator-output-0.1.0.schema.json"
)
RAW_TRACE_SCHEMA_PATHS = {
    "ca_r1_raw_trace_schema": f"{SCHEMA}/ca-r1-raw-trace-0.1.0.schema.json",
    "ca_r2_raw_trace_schema": f"{SCHEMA}/ca-r2-raw-trace-0.1.0.schema.json",
    "ca_r3_raw_trace_schema": f"{SCHEMA}/ca-r3-raw-trace-0.1.0.schema.json",
}
RAW_TRACE_VERIFIER_PATH = f"{BASE}/tools/verify-formal-raw-trace.py"
SYNTHETIC_AUTHORIZATION_ENV = (
    "GAME_PRIMITIVES_INTERNAL_SYNTHETIC_AUTHORIZATION"
)
SYNTHETIC_AUTHORIZATION_TOKEN = (
    "continuous-001-disposable-blind-pipeline-self-test"
)
SYNTHETIC_AUTHORIZATION_MARKER = ".synthetic-blind-pipeline-self-test"
ROLE_011_PATH = f"{SCHEMA}/role-submission-0.1.1.schema.json"
ROLE_012_PATH = f"{SCHEMA}/role-submission-0.1.2.schema.json"
BLIND_RESPONSE_PATH = f"{SCHEMA}/blind-response-interface-0.1.0.schema.json"

STAGE1_SCHEMA_ID = URL_PREFIX + STAGE1_SCHEMA_PATH
STAGE2_SCHEMA_ID = URL_PREFIX + STAGE2_SCHEMA_PATH
COHORT_SCHEMA_ID = URL_PREFIX + COHORT_SCHEMA_PATH
AUTHORIZATION_SCHEMA_ID = URL_PREFIX + AUTHORIZATION_SCHEMA_PATH

OPERATIONAL_FACILITY_PATHS = {
    AUTHORIZATION_SCHEMA_PATH,
}
STAGE1_COGNITIVE_SCHEMA_PATHS = {
    f"{SCHEMA}/blind-response-interface-0.1.0.schema.json",
    f"{SCHEMA}/ca-sr-artifact-0.1.0.schema.json",
    f"{SCHEMA}/response-template-0.1.0.schema.json",
    f"{SCHEMA}/role-submission-0.1.1.schema.json",
    f"{SCHEMA}/role-submission-0.1.2.schema.json",
    f"{SCHEMA}/task-packet-0.1.0.schema.json",
    f"{SCHEMA}/task-packet-0.1.2.schema.json",
    f"{SCHEMA}/variant-envelope-0.1.0.schema.json",
}
STAGE2_COGNITIVE_SCHEMA_PATHS = STAGE1_COGNITIVE_SCHEMA_PATHS - {
    f"{SCHEMA}/ca-sr-artifact-0.1.0.schema.json"
}
STAGE1_FACILITY_PATHS = (
    STAGE1_COGNITIVE_SCHEMA_PATHS | OPERATIONAL_FACILITY_PATHS
)
STAGE2_FACILITY_PATHS = (
    STAGE2_COGNITIVE_SCHEMA_PATHS | OPERATIONAL_FACILITY_PATHS
)
FORBIDDEN_PATH_PARTS = (
    "/comparators/",
    "/fixtures/",
    "/results/",
    "/source/",
    "/submissions/",
    "/truth/",
)


class DispatchError(RuntimeError):
    """A fail-closed dispatch materialization or verification error."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def actor_object_sha256(actor: dict[str, Any]) -> str:
    """Hash the actor object using the project canonical JSON byte contract."""
    return sha256_bytes(canonical_bytes(actor))


def repo_path(repo_root: Path, value: str | Path) -> Path:
    path = (repo_root / value).resolve()
    if not path.is_relative_to(repo_root):
        raise DispatchError(f"path escapes repository root: {value}")
    if not path.is_file():
        raise DispatchError(f"required file does not exist: {value}")
    return path


def relative_path(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise DispatchError(f"UTF-8 BOM is forbidden: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise DispatchError(f"expected a JSON object: {path}")
    return value, raw


def read_repo_json(
    repo_root: Path, value: str | Path
) -> tuple[dict[str, Any], bytes, Path]:
    path = repo_path(repo_root, value)
    document, raw = read_json(path)
    return document, raw, path


def artifact_reference(repo_root: Path, value: str | Path) -> dict[str, str]:
    path = repo_path(repo_root, value)
    return {
        "path": relative_path(repo_root, path),
        "sha256": sha256_bytes(path.read_bytes()),
    }


def verify_reference(repo_root: Path, reference: dict[str, str]) -> Path:
    path = repo_path(repo_root, reference["path"])
    actual = sha256_bytes(path.read_bytes())
    if actual != reference["sha256"]:
        raise DispatchError(
            f"hash mismatch for {reference['path']}: "
            f"expected {reference['sha256']}, got {actual}"
        )
    return path


def parse_date_time(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise DispatchError(f"{field_name} is not an RFC 3339 date-time") from error
    if parsed.tzinfo is None:
        raise DispatchError(f"{field_name} must include a timezone")
    return parsed


def manifest_entry_for_reference(
    manifest: dict[str, Any],
    reference: dict[str, str],
) -> dict[str, Any]:
    prefix = RUN + "/"
    path = reference["path"].replace("\\", "/")
    if not path.startswith(prefix):
        raise DispatchError(f"authorization basis is outside the run: {path}")
    run_relative = path[len(prefix) :]
    matches = [
        entry
        for entry in manifest.get("artifacts", [])
        if entry.get("path") == run_relative
    ]
    if len(matches) != 1:
        raise DispatchError(
            f"frozen manifest must contain exactly one authorization basis: {path}"
        )
    entry = matches[0]
    if entry.get("sha256") != reference["sha256"]:
        raise DispatchError(f"frozen manifest hash differs for {path}")
    if entry.get("included_in_frozen_set") is not True:
        raise DispatchError(f"authorization basis is not in the frozen set: {path}")
    return entry


def synthetic_authorization_enabled(repo_root: Path) -> bool:
    system_temp = Path(tempfile.gettempdir()).resolve()
    marker = repo_root / SYNTHETIC_AUTHORIZATION_MARKER
    return (
        os.environ.get(SYNTHETIC_AUTHORIZATION_ENV)
        == SYNTHETIC_AUTHORIZATION_TOKEN
        and repo_root.name == "synthetic-repository"
        and repo_root != system_temp
        and repo_root.is_relative_to(system_temp)
        and not (repo_root / ".git").exists()
        and marker.is_file()
        and marker.read_text(encoding="utf-8")
        == SYNTHETIC_AUTHORIZATION_TOKEN + "\n"
    )


def verify_protocol_incident_disposition(
    repo_root: Path,
    authorization: dict[str, Any],
    manifest: dict[str, Any],
    context: str,
) -> None:
    disposition = authorization.get("protocol_incident_disposition")
    if not isinstance(disposition, dict):
        raise DispatchError(
            "authorization lacks the required protocol-incident disposition"
        )
    expected_disposition = (
        "accepted_nonsemantic_integrity_exception"
        if context == "formal_run"
        else "synthetic_only"
    )
    if (
        disposition.get("incident_id") != PROTOCOL_INCIDENT_ID
        or disposition.get("disposition") != expected_disposition
        or disposition.get("recorded_gate_status")
        != "pending_explicit_human_acceptance"
        or disposition.get("acknowledged_facts")
        != {
            "byte_integrity_read_occurred": True,
            "fact_basis_is_subtask_self_report": True,
            "no_semantic_content_or_result_exposure_reported": True,
        }
    ):
        raise DispatchError(
            "authorization does not explicitly acknowledge and dispose of "
            "the R3 byte-integrity-read incident"
        )

    reference = disposition.get("incident_record")
    if not isinstance(reference, dict):
        raise DispatchError("protocol-incident record reference is absent")
    record_path = verify_reference(repo_root, reference)
    manifest_entry_for_reference(manifest, reference)
    record, raw = read_json(record_path)
    if raw != canonical_bytes(record):
        raise DispatchError("protocol-incident record is not canonical JSON")
    validate_against_repo_schema(
        repo_root,
        record,
        PROTOCOL_INCIDENT_SCHEMA_PATH,
    )
    if (
        record.get("incident_id") != PROTOCOL_INCIDENT_ID
        or record.get("run_id") != RUN_ID
        or record.get("case_id") != "CA-R3"
        or record.get("aggregate_state")
        != {
            "formal_input_byte_read": True,
            "formal_input_executed": False,
            "formal_result_produced": False,
        }
        or record.get("observed_operations")
        != {
            "byte_read_api": "Path.read_bytes",
            "byte_read_count": 1,
            "compared_with_existing_case_lock_digest": True,
            "digest_algorithm": "SHA-256",
        }
        or record.get("non_operations")
        != {
            "content_persisted": False,
            "content_printed_or_returned": False,
            "digest_persisted": False,
            "digest_printed_or_returned": False,
            "formal_execution": False,
            "json_parse": False,
            "semantic_interpretation": False,
        }
        or record.get("exposure")
        != {
            "content_exposed_to_main_thread": False,
            "content_exposed_to_prediction_flow": False,
            "digest_exposed_to_main_thread": False,
            "formal_result_observed": False,
        }
        or record.get("fact_basis", {}).get("kind") != "subtask_self_report"
        or record.get("gate_disposition")
        != {
            "recommended": (
                "retain_with_documented_nonsemantic_integrity_exception"
            ),
            "required": True,
            "status": "pending_explicit_human_acceptance",
        }
    ):
        raise DispatchError(
            "protocol-incident record does not match the acknowledged "
            "nonsemantic integrity exception"
        )


def verify_authorization_receipt(
    repo_root: Path,
    reference: dict[str, str],
) -> dict[str, Any]:
    if reference.get("path", "").replace("\\", "/") != AUTHORIZATION_PATH:
        raise DispatchError(
            f"authorization receipt must use the fixed path {AUTHORIZATION_PATH}"
        )
    path = verify_reference(repo_root, reference)
    authorization, raw = read_json(path)
    if raw != canonical_bytes(authorization):
        raise DispatchError("authorization receipt is not canonical JSON")
    validate_against_repo_schema(
        repo_root,
        authorization,
        AUTHORIZATION_SCHEMA_PATH,
    )
    if authorization.get("$schema") != AUTHORIZATION_SCHEMA_ID:
        raise DispatchError("authorization receipt schema identity differs")
    context = authorization["authorization_context"]
    if context == "synthetic_self_test":
        if not synthetic_authorization_enabled(repo_root):
            raise DispatchError(
                "synthetic authorization is confined to a marked disposable "
                "repository under the system temporary directory"
            )
    elif context != "formal_run":
        raise DispatchError("unknown authorization context")
    verified_at = parse_date_time(
        authorization["verification"]["verified_at"],
        "verification.verified_at",
    )
    authorized_at = parse_date_time(
        authorization["authorized_at"],
        "authorized_at",
    )
    if authorized_at < verified_at:
        raise DispatchError("authorization predates its frozen-readiness verification")

    manifest_path = repo_path(repo_root, authorization["frozen_manifest_path"])
    manifest, _ = read_json(manifest_path)
    if (
        manifest.get("artifact_type") != "formal_run_manifest"
        or manifest.get("run_id") != RUN_ID
        or manifest.get("status")
        not in ("frozen", "collecting", "reported", "revealed")
    ):
        raise DispatchError(
            "authorization does not bind a valid frozen formal run lineage"
        )
    if manifest.get("freeze_commit") != authorization["freeze_commit"]:
        raise DispatchError("authorization freeze commit differs from manifest")
    if (
        manifest.get("frozen_artifact_set_digest")
        != authorization["frozen_artifact_set_digest"]
    ):
        raise DispatchError("authorization frozen-set digest differs from manifest")
    if manifest.get("truth_commitment") is None:
        raise DispatchError("authorization manifest has no truth commitment")
    if manifest.get("truth_commitment") != authorization["truth_commitment"]:
        raise DispatchError("authorization truth commitment differs from manifest")

    readiness_path = verify_reference(
        repo_root, authorization["final_build_readiness"]
    )
    fixture_lock_path = verify_reference(repo_root, authorization["fixture_lock"])
    projection_audit_path = verify_reference(
        repo_root, authorization["projection_audit"]
    )
    incident_record_path = verify_reference(
        repo_root,
        authorization["protocol_incident_disposition"]["incident_record"],
    )
    verify_reference(repo_root, authorization["formal_readiness_verifier"])
    for contract_reference in authorization["contract_artifacts"].values():
        verify_reference(repo_root, contract_reference)
    for basis_reference in (
        authorization["final_build_readiness"],
        authorization["fixture_lock"],
        authorization["projection_audit"],
        authorization["protocol_incident_disposition"]["incident_record"],
    ):
        manifest_entry_for_reference(manifest, basis_reference)
    verify_protocol_incident_disposition(
        repo_root,
        authorization,
        manifest,
        context,
    )

    readiness, _ = read_json(readiness_path)
    if (
        readiness.get("$schema")
        != URL_PREFIX + f"{SCHEMA}/formal-build-readiness-0.1.0.schema.json"
        or readiness.get("artifact_type") != "formal_build_readiness"
        or readiness.get("run_id") != RUN_ID
        or readiness.get("overall_status") != "passed"
        or readiness.get("readiness_scope") != "build_only"
        or readiness.get("formal_input_executed") is not False
        or readiness.get("formal_result_produced") is not False
    ):
        raise DispatchError("final build readiness basis is not a clean pass")

    fixture_lock, _ = read_json(fixture_lock_path)
    if (
        fixture_lock.get("$schema")
        != URL_PREFIX + f"{SCHEMA}/fixture-lock-0.1.0.schema.json"
        or fixture_lock.get("artifact_type") != "fixture_lock"
        or fixture_lock.get("run_id") != RUN_ID
        or fixture_lock.get("fixture_state") != "locked"
        or fixture_lock.get("formal_execution_authorized") is not False
        or fixture_lock.get("formal_input_executed") is not False
    ):
        raise DispatchError("fixture lock basis is not a withheld, unexecuted lock")

    projection_audit, _ = read_json(projection_audit_path)
    if (
        projection_audit.get("$schema") != URL_PREFIX + ROLE_012_PATH
        or projection_audit.get("artifact_type") != "source_fidelity_audit"
        or projection_audit.get("run_id") != RUN_ID
        or projection_audit.get("stage") != "source_audit"
        or projection_audit.get("audit_decision") != "approved"
    ):
        raise DispatchError("projection audit basis is not approved")
    if context == "formal_run":
        validate_against_repo_schema_registry(
            repo_root,
            manifest,
            f"{SCHEMA}/run-manifest-0.1.1.schema.json",
        )
        validate_against_repo_schema_registry(
            repo_root,
            readiness,
            f"{SCHEMA}/formal-build-readiness-0.1.0.schema.json",
        )
        validate_against_repo_schema_registry(
            repo_root,
            fixture_lock,
            f"{SCHEMA}/fixture-lock-0.1.0.schema.json",
        )
        validate_against_repo_schema_registry(
            repo_root,
            projection_audit,
            ROLE_012_PATH,
        )
        incident_record, _ = read_json(incident_record_path)
        validate_against_repo_schema_registry(
            repo_root,
            incident_record,
            PROTOCOL_INCIDENT_SCHEMA_PATH,
        )
    return authorization


def write_new(repo_root: Path, value: str | Path, document: dict[str, Any]) -> Path:
    candidate = (repo_root / value).resolve()
    if not candidate.is_relative_to(repo_root):
        raise DispatchError(f"output escapes repository root: {value}")
    if candidate.name.endswith(".template.json"):
        raise DispatchError("an inert .template.json file can never be an output")
    if candidate.exists():
        raise DispatchError(f"refusing to overwrite an existing artifact: {value}")
    if not candidate.parent.is_dir():
        raise DispatchError(
            f"output parent must already exist and be authorized: {candidate.parent}"
        )
    candidate.write_bytes(canonical_bytes(document))
    return candidate


def validate_schema(document: dict[str, Any], schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(document), key=lambda item: list(item.path))
    if errors:
        rendered = []
        for error in errors[:12]:
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            rendered.append(f"{location}: {error.message}")
        raise DispatchError("schema validation failed:\n" + "\n".join(rendered))


def validate_against_repo_schema(
    repo_root: Path, document: dict[str, Any], schema_path: str
) -> None:
    schema, _, _ = read_repo_json(repo_root, schema_path)
    validate_schema(document, schema)


def validate_against_repo_schema_registry(
    repo_root: Path,
    document: dict[str, Any],
    schema_path: str,
) -> None:
    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    schema_root = (repo_root / SCHEMA).resolve()
    if not schema_root.is_relative_to(repo_root) or not schema_root.is_dir():
        raise DispatchError("repository schema root is absent or escapes the repository")
    for path in sorted(schema_root.glob("*.schema.json")):
        schema, _ = read_json(path)
        Draft202012Validator.check_schema(schema)
        schemas[schema["$id"]] = schema
        registry = registry.with_resource(
            schema["$id"],
            Resource.from_contents(schema),
        )
    schema_id = URL_PREFIX + schema_path
    if schema_id not in schemas:
        raise DispatchError(f"schema is absent from repository registry: {schema_path}")
    validate_with_registry(document, schemas[schema_id], registry)


def validate_actor(repo_root: Path, actor: dict[str, Any]) -> None:
    role_011, _, _ = read_repo_json(repo_root, ROLE_011_PATH)
    actor_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": role_011["$defs"],
        "$ref": "#/$defs/testActor",
    }
    validate_schema(actor, actor_schema)
    if actor["role"] != "blind_reconstructor_predictor":
        raise DispatchError("dispatch actor role must be blind_reconstructor_predictor")


def role_registry(repo_root: Path) -> tuple[dict[str, Any], dict[str, Any], Registry]:
    role_011, _, _ = read_repo_json(repo_root, ROLE_011_PATH)
    role_012, _, _ = read_repo_json(repo_root, ROLE_012_PATH)
    registry = Registry().with_resource(
        role_011["$id"], Resource.from_contents(role_011)
    )
    return role_011, role_012, registry


def validate_with_registry(
    document: dict[str, Any],
    schema: dict[str, Any],
    registry: Registry,
) -> None:
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(document), key=lambda item: list(item.path))
    if errors:
        rendered = []
        for error in errors[:12]:
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            rendered.append(f"{location}: {error.message}")
        raise DispatchError("schema validation failed:\n" + "\n".join(rendered))


def condition_for_seat(seat_id: str) -> str:
    if seat_id in ("p01", "p02"):
        return "condition-v01"
    if seat_id in ("p03", "p04"):
        return "condition-v02"
    raise DispatchError(f"unknown seat: {seat_id}")


def condition_suffix(condition_id: str) -> str:
    if condition_id == "condition-v01":
        return "v01"
    if condition_id == "condition-v02":
        return "v02"
    raise DispatchError(f"unknown condition: {condition_id}")


def expected_participant_paths(stage: str, condition_id: str) -> set[str]:
    if stage == "reconstruction":
        suffix = condition_suffix(condition_id)
        return {
            f"{INPUTS}/reconstruction-response.template.json",
            f"{INPUTS}/stage1-condition-{suffix}.task.json",
            f"{INPUTS}/stage1-view-{suffix}.json",
        }
    if stage == "prediction":
        return {
            f"{INPUTS}/prediction-response.template.json",
            f"{INPUTS}/stage2-prediction.task.json",
            f"{INPUTS}/stage2-variant-envelope.json",
        }
    raise DispatchError(f"unknown dispatch stage: {stage}")


def project_schema_path(uri: str) -> str | None:
    if not uri.startswith(URL_PREFIX):
        return None
    path = uri[len(URL_PREFIX) :].split("#", 1)[0]
    if not path.startswith(f"{SCHEMA}/") or not path.endswith(".schema.json"):
        raise DispatchError(f"project schema reference is outside schema root: {uri}")
    return path


def walk_refs(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                yield child
            yield from walk_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_refs(child)


def discover_schema_closure(
    repo_root: Path,
    participant_paths: set[str],
) -> tuple[set[str], set[tuple[str, str]]]:
    schemas: set[str] = set()
    edges: set[tuple[str, str]] = set()
    queue: deque[str] = deque(sorted(participant_paths))
    visited: set[str] = set()

    while queue:
        document_path = queue.popleft()
        if document_path in visited:
            continue
        visited.add(document_path)
        document, _, _ = read_repo_json(repo_root, document_path)

        root_schema = document.get("$schema")
        if isinstance(root_schema, str):
            schema_path = project_schema_path(root_schema)
            if schema_path is not None:
                edges.add((document_path, schema_path))
                if schema_path not in schemas:
                    schemas.add(schema_path)
                    queue.append(schema_path)

        for ref in walk_refs(document):
            schema_path = project_schema_path(ref)
            if schema_path is not None:
                edges.add((document_path, schema_path))
                if schema_path not in schemas:
                    schemas.add(schema_path)
                    queue.append(schema_path)

        template_payload = document.get("template_payload")
        if isinstance(template_payload, dict):
            payload_schema = template_payload.get("$schema")
            if isinstance(payload_schema, str):
                schema_path = project_schema_path(payload_schema)
                if schema_path is not None:
                    edges.add((document_path + "#/template_payload", schema_path))
                    if schema_path not in schemas:
                        schemas.add(schema_path)
                        queue.append(schema_path)

        target = document.get("target_response_schema")
        if isinstance(target, dict) and isinstance(target.get("path"), str):
            schema_path = target["path"].replace("\\", "/")
            edges.add((document_path + "#/target_response_schema", schema_path))
            if schema_path not in schemas:
                schemas.add(schema_path)
                queue.append(schema_path)

        for field in ("output_schema", "assembled_output_schema"):
            target = document.get(field)
            if isinstance(target, dict) and isinstance(target.get("path"), str):
                schema_path = target["path"].replace("\\", "/")
                edges.add((document_path + f"#/{field}", schema_path))
                if schema_path not in schemas:
                    schemas.add(schema_path)
                    queue.append(schema_path)

    return schemas, edges


def listed_paths(items: list[dict[str, Any]]) -> set[str]:
    paths = [item["path"].replace("\\", "/") for item in items]
    if len(paths) != len(set(paths)):
        raise DispatchError("dispatch file paths must be unique")
    return set(paths)


def listed_edges(items: list[dict[str, str]]) -> set[tuple[str, str]]:
    edges = {
        (
            item["document_path"].replace("\\", "/"),
            item["schema_path"].replace("\\", "/"),
        )
        for item in items
    }
    if len(edges) != len(items):
        raise DispatchError("schema dependency edges must be unique")
    return edges


def reject_forbidden_participant_references(
    repo_root: Path,
    paths: set[str],
    seat_id: str,
    condition_id: str | None,
) -> None:
    wrong_conditions = {
        value for value in ("condition-v01", "condition-v02") if value != condition_id
    }
    wrong_seats = {value for value in SEATS if value != seat_id}

    def inspect(value: Any, origin: str) -> None:
        if isinstance(value, dict):
            for child in value.values():
                inspect(child, origin)
        elif isinstance(value, list):
            for child in value:
                inspect(child, origin)
        elif isinstance(value, str):
            normalized = "/" + value.replace("\\", "/").lower().lstrip("/")
            if value.startswith("research/") and any(
                part in normalized for part in FORBIDDEN_PATH_PARTS
            ):
                raise DispatchError(
                    f"participant file {origin} references forbidden path {value}"
                )
            if any(
                re.search(
                    rf"(?<![a-z0-9]){re.escape(other)}(?![a-z0-9])",
                    normalized,
                )
                for other in wrong_conditions
            ):
                raise DispatchError(
                    f"participant file {origin} exposes other condition {value}"
                )
            if any(
                re.search(
                    rf"(?<![a-z0-9]){re.escape(other)}(?![a-z0-9])",
                    normalized,
                )
                for other in wrong_seats
            ):
                raise DispatchError(
                    f"participant file {origin} exposes other seat {value}"
                )

    for path in paths:
        document, _, _ = read_repo_json(repo_root, path)
        inspect(document, path)


def verify_file_lists(
    repo_root: Path,
    document: dict[str, Any],
    stage: str,
    condition_id: str,
    expect_hashes: bool,
) -> None:
    participant = document["participant_files"]
    facility = document["facility_files"]
    participant_paths = listed_paths(participant)
    facility_paths = listed_paths(facility)

    expected_participant = expected_participant_paths(stage, condition_id)
    if participant_paths != expected_participant:
        raise DispatchError(
            f"{stage} participant file set differs from exact contract: "
            f"{sorted(participant_paths ^ expected_participant)}"
        )
    task_path = (
        f"{INPUTS}/stage1-condition-{condition_suffix(condition_id)}.task.json"
        if stage == "reconstruction"
        else f"{INPUTS}/stage2-prediction.task.json"
    )
    task, _, _ = read_repo_json(repo_root, task_path)
    task_input_paths = {
        item["path"].replace("\\", "/") for item in task["input_artifacts"]
    }
    if task_input_paths | {task_path} != expected_participant:
        raise DispatchError(
            f"{stage} task input paths differ from the exact participant set"
        )
    for item in task["input_artifacts"]:
        actual = sha256_bytes(repo_path(repo_root, item["path"]).read_bytes())
        if item["sha256"] != actual:
            raise DispatchError(
                f"{stage} task binds a stale input hash: {item['path']}"
            )
    expected_facility = (
        STAGE1_FACILITY_PATHS if stage == "reconstruction" else STAGE2_FACILITY_PATHS
    )
    if facility_paths != expected_facility:
        raise DispatchError(
            f"{stage} facility file set differs from recursive closure: "
            f"{sorted(facility_paths ^ expected_facility)}"
        )

    for item in participant:
        if item["dispatch_role"] != "participant_cognitive_input":
            raise DispatchError("participant files must use participant_cognitive_input")
    for item in facility:
        if item["dispatch_role"] != "facility_schema":
            raise DispatchError("facility files must use facility_schema")

    discovered_schemas, discovered_edges = discover_schema_closure(
        repo_root, participant_paths
    )
    cognitive_facility_paths = facility_paths - OPERATIONAL_FACILITY_PATHS
    if discovered_schemas != cognitive_facility_paths:
        raise DispatchError(
            "facility file set does not equal the recursive local schema closure: "
            f"{sorted(discovered_schemas ^ cognitive_facility_paths)}"
        )
    declared_edges = listed_edges(document["schema_dependency_closure"])
    if declared_edges != discovered_edges:
        raise DispatchError(
            "declared schema dependency closure differs from recursive discovery"
        )

    for item in participant + facility:
        path = repo_path(repo_root, item["path"])
        actual = sha256_bytes(path.read_bytes())
        if expect_hashes:
            if item["sha256"] != actual:
                raise DispatchError(f"dispatch file hash mismatch: {item['path']}")
        elif item["sha256"] is not None:
            raise DispatchError("inert templates must contain only null file hashes")

    reject_forbidden_participant_references(
        repo_root, participant_paths, document["seat_id"], condition_id
    )


def template_path(repo_root: Path, stage: str, seat_id: str) -> Path:
    name = f"stage{1 if stage == 'reconstruction' else 2}-dispatch-{seat_id}.template.json"
    return repo_path(repo_root, f"{INPUTS}/{name}")


def verify_dispatch_template(
    repo_root: Path, path: Path, expected_stage: str
) -> dict[str, Any]:
    document, _, _ = read_repo_json(repo_root, relative_path(repo_root, path))
    schema_path = (
        STAGE1_SCHEMA_PATH if expected_stage == "reconstruction" else STAGE2_SCHEMA_PATH
    )
    validate_against_repo_schema(repo_root, document, schema_path)
    expected_type = (
        "stage1_seat_dispatch_template"
        if expected_stage == "reconstruction"
        else "stage2_seat_dispatch_template"
    )
    if document["artifact_type"] != expected_type:
        raise DispatchError(f"not an inert {expected_stage} dispatch template")
    if document["dispatch_status"] != "template_only":
        raise DispatchError("template dispatch_status must remain template_only")
    if document["release_authorized"] is not False:
        raise DispatchError("template can never authorize release")
    seat_id = document["seat_id"]
    condition_id = condition_for_seat(seat_id)
    if document["condition_binding"]["condition_id"] != condition_id:
        raise DispatchError("seat-condition mapping is invalid")
    verify_file_lists(
        repo_root,
        document,
        expected_stage,
        condition_id,
        expect_hashes=False,
    )
    return document


def fill_locked_files(
    repo_root: Path, template_items: list[dict[str, Any]]
) -> list[dict[str, str]]:
    return [
        {
            "dispatch_role": item["dispatch_role"],
            "path": item["path"],
            "sha256": sha256_bytes(repo_path(repo_root, item["path"]).read_bytes()),
        }
        for item in template_items
    ]


def materialize_stage1(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    template = verify_dispatch_template(
        repo_root, repo_path(repo_root, args.template), "reconstruction"
    )
    actor, _, actor_path = read_repo_json(repo_root, args.actor)
    validate_actor(repo_root, actor)
    authorization = artifact_reference(repo_root, args.authorization_receipt)
    verify_authorization_receipt(repo_root, authorization)
    output_rel = Path(args.output).as_posix()
    if output_rel != template["planned_receipt_path"]:
        raise DispatchError("output must equal the template planned_receipt_path")

    receipt = {
        "$schema": STAGE1_SCHEMA_ID,
        "actor_binding": {
            "actor_identifier": actor["identifier"],
            "actor_object_sha256": actor_object_sha256(actor),
            "session_id": actor["session_id"],
        },
        "actor_source": artifact_reference(repo_root, actor_path),
        "artifact_type": "stage1_seat_dispatch_receipt",
        "artifact_version": "0.1.0",
        "authorization_receipt": authorization,
        "condition_binding": {
            "condition_id": template["condition_binding"]["condition_id"],
            "condition_view_path": template["condition_binding"][
                "condition_view_path"
            ],
            "condition_view_sha256": sha256_bytes(
                repo_path(
                    repo_root, template["condition_binding"]["condition_view_path"]
                ).read_bytes()
            ),
            "task_path": template["condition_binding"]["task_path"],
            "task_sha256": sha256_bytes(
                repo_path(
                    repo_root, template["condition_binding"]["task_path"]
                ).read_bytes()
            ),
        },
        "dispatch_status": "ready_for_dispatch",
        "facility_files": fill_locked_files(repo_root, template["facility_files"]),
        "participant_files": fill_locked_files(
            repo_root, template["participant_files"]
        ),
        "receipt_id": f"dispatch-receipt.{RUN_ID}.{template['seat_id']}.stage1",
        "release_authorized": True,
        "run_id": RUN_ID,
        "schema_dependency_closure": copy.deepcopy(
            template["schema_dependency_closure"]
        ),
        "seat_id": template["seat_id"],
        "stage": "reconstruction",
        "template_source": artifact_reference(repo_root, args.template),
    }
    validate_against_repo_schema(repo_root, receipt, STAGE1_SCHEMA_PATH)
    output = write_new(repo_root, args.output, receipt)
    verify_stage1_receipt(repo_root, output)
    return {
        "artifact": relative_path(repo_root, output),
        "artifact_type": receipt["artifact_type"],
        "formal_dispatch_performed": False,
        "sha256": sha256_bytes(output.read_bytes()),
        "status": "materialized",
    }


def verify_stage1_receipt(repo_root: Path, path: Path) -> dict[str, Any]:
    receipt, _, _ = read_repo_json(repo_root, relative_path(repo_root, path))
    validate_against_repo_schema(repo_root, receipt, STAGE1_SCHEMA_PATH)
    if receipt["artifact_type"] != "stage1_seat_dispatch_receipt":
        raise DispatchError("expected a stage1 dispatch receipt")
    template_file = verify_reference(repo_root, receipt["template_source"])
    template = verify_dispatch_template(repo_root, template_file, "reconstruction")
    if relative_path(repo_root, path) != template["planned_receipt_path"]:
        raise DispatchError("receipt path differs from immutable template plan")
    if receipt["seat_id"] != template["seat_id"]:
        raise DispatchError("receipt seat differs from template")
    condition_id = condition_for_seat(receipt["seat_id"])
    verify_file_lists(
        repo_root, receipt, "reconstruction", condition_id, expect_hashes=True
    )
    actor_file = verify_reference(repo_root, receipt["actor_source"])
    actor, _, _ = read_repo_json(repo_root, actor_file)
    validate_actor(repo_root, actor)
    expected_actor = {
        "actor_identifier": actor["identifier"],
        "actor_object_sha256": actor_object_sha256(actor),
        "session_id": actor["session_id"],
    }
    if receipt["actor_binding"] != expected_actor:
        raise DispatchError("receipt actor binding cannot be reproduced")
    verify_authorization_receipt(repo_root, receipt["authorization_receipt"])
    condition = receipt["condition_binding"]
    if condition["condition_id"] != condition_id:
        raise DispatchError("receipt condition differs from seat assignment")
    if condition["task_sha256"] != sha256_bytes(
        repo_path(repo_root, condition["task_path"]).read_bytes()
    ):
        raise DispatchError("stage1 task binding cannot be reproduced")
    if condition["condition_view_sha256"] != sha256_bytes(
        repo_path(repo_root, condition["condition_view_path"]).read_bytes()
    ):
        raise DispatchError("stage1 view binding cannot be reproduced")
    return receipt


def verify_raw_envelope_submission(
    repo_root: Path,
    receipt: dict[str, Any],
    receipt_path: Path,
    submission_path: Path,
) -> tuple[dict[str, Any], dict[str, str], dict[str, str], dict[str, str]]:
    if verify_stage1_receipt(repo_root, receipt_path) != receipt:
        raise DispatchError("stage1 receipt changed during submission verification")
    submission, submission_raw = read_json(submission_path)
    role_011, role_012, registry = role_registry(repo_root)
    validate_with_registry(submission, role_012, registry)
    if submission.get("artifact_type") != "reconstruction_submission":
        raise DispatchError("cohort member must use a reconstruction submission")
    if submission.get("stage") != "reconstruction" or not submission.get(
        "first_submission"
    ):
        raise DispatchError("cohort member must be an effective first reconstruction")
    if submission.get("run_id") != RUN_ID:
        raise DispatchError("cohort submission run differs")
    if submission.get("condition_id") != receipt["condition_binding"]["condition_id"]:
        raise DispatchError("cohort submission condition differs from dispatch")
    actor = submission["actor"]
    if receipt["actor_binding"] != {
        "actor_identifier": actor["identifier"],
        "actor_object_sha256": actor_object_sha256(actor),
        "session_id": actor["session_id"],
    }:
        raise DispatchError("submission actor differs from dispatch receipt")

    task, _, _ = read_repo_json(
        repo_root, receipt["condition_binding"]["task_path"]
    )
    if submission.get("task_id") != task["task_id"]:
        raise DispatchError("submission task differs from stage1 receipt")
    expected_submission_inputs = [
        {
            "artifact_id": task["task_id"],
            "sha256": sha256_bytes(
                repo_path(
                    repo_root, receipt["condition_binding"]["task_path"]
                ).read_bytes()
            ),
        },
        *[
            {
                "artifact_id": item["artifact_id"],
                "sha256": item["sha256"],
            }
            for item in task["input_artifacts"]
        ],
        {
            "artifact_id": receipt["receipt_id"],
            "sha256": sha256_bytes(receipt_path.read_bytes()),
        },
    ]
    if submission["input_artifacts"] != expected_submission_inputs:
        raise DispatchError(
            "submission input artifacts differ from the exact ordered stage1 dispatch"
        )

    raw_reference = submission["raw_payload"]
    raw_path = verify_reference(
        repo_root,
        {"path": raw_reference["path"], "sha256": raw_reference["sha256"]},
    )
    payload, _, _ = read_repo_json(repo_root, raw_path)
    blind, _, _ = read_repo_json(repo_root, BLIND_RESPONSE_PATH)
    blind_registry = Registry().with_resource(
        role_011["$id"], Resource.from_contents(role_011)
    )
    validate_with_registry(payload, blind, blind_registry)
    if payload.get("artifact_type") != "reconstruction_response_payload":
        raise DispatchError("cohort raw payload is not a reconstruction response")

    envelope_reference = {
        "path": submission["packaging"]["envelope_path"],
        "sha256": submission["packaging"]["envelope_sha256"],
    }
    envelope_path = verify_reference(repo_root, envelope_reference)
    envelope, _, _ = read_repo_json(repo_root, envelope_path)
    validate_with_registry(envelope, blind, blind_registry)
    if envelope.get("artifact_type") != "role_submission_envelope":
        raise DispatchError("cohort machine envelope has an unexpected type")
    if envelope.get("stage") != "reconstruction":
        raise DispatchError("cohort machine envelope is not reconstruction")
    if envelope.get("prior_stage_submission_sha256") is not None:
        raise DispatchError("stage1 machine envelope cannot bind a prior stage")
    if (
        envelope.get("actor") != actor
        or envelope.get("condition_id") != submission["condition_id"]
        or envelope.get("run_id") != RUN_ID
    ):
        raise DispatchError("machine envelope continuity check failed")
    if envelope.get("dispatch_artifacts") != expected_submission_inputs:
        raise DispatchError(
            "machine envelope differs from the exact ordered stage1 dispatch"
        )

    return (
        submission,
        {"path": relative_path(repo_root, raw_path), "sha256": raw_reference["sha256"]},
        {
            "path": relative_path(repo_root, envelope_path),
            "sha256": envelope_reference["sha256"],
        },
        {
            "path": relative_path(repo_root, submission_path),
            "sha256": sha256_bytes(submission_raw),
        },
    )


def parse_seat_map(values: list[str], label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        seat, separator, path = value.partition("=")
        if not separator or seat not in SEATS or not path:
            raise DispatchError(f"{label} must use p0N=repo/path syntax")
        if seat in result:
            raise DispatchError(f"duplicate {label} for {seat}")
        result[seat] = path
    if set(result) != set(SEATS):
        raise DispatchError(f"{label} must cover p01 through p04 exactly once")
    return result


def validate_cohort_independence(members: list[dict[str, Any]]) -> None:
    identifiers = [item["actor_binding"]["actor_identifier"] for item in members]
    sessions = [item["actor_binding"]["session_id"] for item in members]
    actor_hashes = [item["actor_binding"]["actor_object_sha256"] for item in members]
    if len(set(identifiers)) != 4:
        raise DispatchError("cohort actor identifiers must be pairwise distinct")
    if len(set(sessions)) != 4:
        raise DispatchError("cohort sessions must be pairwise distinct")
    if len(set(actor_hashes)) != 4:
        raise DispatchError("cohort actor objects must be pairwise distinct")
    counts = Counter(item["condition_id"] for item in members)
    if counts != Counter({"condition-v01": 2, "condition-v02": 2}):
        raise DispatchError("cohort condition balance must be exactly 2+2")


def common_stage2_template_contract(repo_root: Path) -> dict[str, Any]:
    templates = [
        verify_dispatch_template(
            repo_root, template_path(repo_root, "prediction", seat), "prediction"
        )
        for seat in SEATS
    ]
    first = templates[0]
    for value in templates[1:]:
        if (
            value["participant_files"] != first["participant_files"]
            or value["facility_files"] != first["facility_files"]
            or value["schema_dependency_closure"]
            != first["schema_dependency_closure"]
        ):
            raise DispatchError("stage2 templates do not share identical common inputs")
    return first


def materialize_cohort(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    output_rel = Path(args.output).as_posix()
    if output_rel != COHORT_LOCK_PATH:
        raise DispatchError(
            f"cohort lock output must use the fixed path {COHORT_LOCK_PATH}"
        )
    receipt_map = parse_seat_map(args.stage1_receipt, "stage1 receipt")
    submission_map = parse_seat_map(args.stage1_submission, "stage1 submission")
    authorization = artifact_reference(repo_root, args.authorization_receipt)
    verify_authorization_receipt(repo_root, authorization)
    members = []
    for seat in SEATS:
        receipt_path = repo_path(repo_root, receipt_map[seat])
        receipt = verify_stage1_receipt(repo_root, receipt_path)
        if receipt["seat_id"] != seat:
            raise DispatchError(f"stage1 receipt seat mismatch for {seat}")
        if receipt["authorization_receipt"] != authorization:
            raise DispatchError("all stage1 receipts must bind the same authorization")
        submission_path = repo_path(repo_root, submission_map[seat])
        submission, raw_ref, envelope_ref, submission_ref = (
            verify_raw_envelope_submission(
                repo_root,
                receipt,
                receipt_path,
                submission_path,
            )
        )
        members.append(
            {
                "actor_binding": copy.deepcopy(receipt["actor_binding"]),
                "condition_id": receipt["condition_binding"]["condition_id"],
                "freeze_status": "frozen_by_exact_hash",
                "machine_envelope": envelope_ref,
                "raw_payload": raw_ref,
                "reconstruction_submission": submission_ref,
                "seat_id": seat,
                "stage1_dispatch_receipt": artifact_reference(
                    repo_root, receipt_path
                ),
            }
        )
        if submission["actor"]["session_id"] != receipt["actor_binding"]["session_id"]:
            raise DispatchError("stage1 session continuity check failed")

    validate_cohort_independence(members)
    common = common_stage2_template_contract(repo_root)
    lock = {
        "$schema": COHORT_SCHEMA_ID,
        "all_stage1_frozen": True,
        "artifact_type": "stage1_cohort_lock",
        "artifact_version": "0.1.0",
        "authorization_receipt": authorization,
        "common_stage2_facility_files": fill_locked_files(
            repo_root, common["facility_files"]
        ),
        "common_stage2_participant_files": fill_locked_files(
            repo_root, common["participant_files"]
        ),
        "common_stage2_schema_dependency_closure": copy.deepcopy(
            common["schema_dependency_closure"]
        ),
        "condition_counts": {
            "condition-v01": 2,
            "condition-v02": 2,
        },
        "independent_actor_sessions_verified": True,
        "lock_id": f"cohort-lock.{RUN_ID}.stage1",
        "lock_status": "locked",
        "members": members,
        "run_id": RUN_ID,
    }
    validate_against_repo_schema(repo_root, lock, COHORT_SCHEMA_PATH)
    output = write_new(repo_root, args.output, lock)
    verify_cohort_lock(repo_root, output)
    return {
        "artifact": relative_path(repo_root, output),
        "artifact_type": lock["artifact_type"],
        "formal_dispatch_performed": False,
        "sha256": sha256_bytes(output.read_bytes()),
        "status": "materialized",
    }


def verify_locked_file_list(
    repo_root: Path,
    items: list[dict[str, str]],
    expected_paths: set[str],
) -> None:
    if listed_paths(items) != expected_paths:
        raise DispatchError("cohort common stage2 file set differs from contract")
    for item in items:
        verify_reference(repo_root, item)


def verify_cohort_lock(repo_root: Path, path: Path) -> dict[str, Any]:
    if relative_path(repo_root, path) != COHORT_LOCK_PATH:
        raise DispatchError(
            f"cohort lock must use the fixed path {COHORT_LOCK_PATH}"
        )
    lock, _, _ = read_repo_json(repo_root, relative_path(repo_root, path))
    validate_against_repo_schema(repo_root, lock, COHORT_SCHEMA_PATH)
    if lock["artifact_type"] != "stage1_cohort_lock":
        raise DispatchError("expected a stage1 cohort lock")
    authorization_path = verify_reference(repo_root, lock["authorization_receipt"])
    verify_authorization_receipt(repo_root, lock["authorization_receipt"])
    participant_paths = expected_participant_paths("prediction", "condition-v01")
    verify_locked_file_list(
        repo_root, lock["common_stage2_participant_files"], participant_paths
    )
    verify_locked_file_list(
        repo_root, lock["common_stage2_facility_files"], STAGE2_FACILITY_PATHS
    )
    discovered_schemas, discovered_edges = discover_schema_closure(
        repo_root, participant_paths
    )
    if discovered_schemas != STAGE2_COGNITIVE_SCHEMA_PATHS:
        raise DispatchError("cohort common facility closure is incomplete")
    if listed_edges(lock["common_stage2_schema_dependency_closure"]) != discovered_edges:
        raise DispatchError("cohort common schema edge closure is incomplete")

    members = lock["members"]
    validate_cohort_independence(members)
    for member in members:
        seat = member["seat_id"]
        if member["condition_id"] != condition_for_seat(seat):
            raise DispatchError("cohort seat-condition mapping failed")
        receipt_path = verify_reference(
            repo_root, member["stage1_dispatch_receipt"]
        )
        receipt = verify_stage1_receipt(repo_root, receipt_path)
        if receipt["seat_id"] != seat:
            raise DispatchError("cohort member receipt seat mismatch")
        if receipt["authorization_receipt"]["path"] != relative_path(
            repo_root, authorization_path
        ) or receipt["authorization_receipt"]["sha256"] != lock[
            "authorization_receipt"
        ]["sha256"]:
            raise DispatchError("cohort authorization continuity failed")
        submission_path = verify_reference(
            repo_root, member["reconstruction_submission"]
        )
        _, raw_ref, envelope_ref, submission_ref = verify_raw_envelope_submission(
            repo_root,
            receipt,
            receipt_path,
            submission_path,
        )
        if (
            raw_ref != member["raw_payload"]
            or envelope_ref != member["machine_envelope"]
            or submission_ref != member["reconstruction_submission"]
        ):
            raise DispatchError("cohort frozen member references cannot be reproduced")
        if member["actor_binding"] != receipt["actor_binding"]:
            raise DispatchError("cohort actor binding differs from stage1 receipt")
    return lock


def find_member(lock: dict[str, Any], seat_id: str) -> dict[str, Any]:
    matches = [item for item in lock["members"] if item["seat_id"] == seat_id]
    if len(matches) != 1:
        raise DispatchError(f"cohort lock does not contain exactly one {seat_id}")
    return matches[0]


def materialize_stage2(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    template_path_value = repo_path(repo_root, args.template)
    template = verify_dispatch_template(repo_root, template_path_value, "prediction")
    cohort_path = repo_path(repo_root, args.cohort_lock)
    lock = verify_cohort_lock(repo_root, cohort_path)
    seat_id = template["seat_id"]
    member = find_member(lock, seat_id)
    receipt_path = repo_path(repo_root, args.stage1_receipt)
    submission_path = repo_path(repo_root, args.stage1_submission)
    if artifact_reference(repo_root, receipt_path) != member[
        "stage1_dispatch_receipt"
    ]:
        raise DispatchError("stage2 prior dispatch receipt differs from cohort lock")
    if artifact_reference(repo_root, submission_path) != member[
        "reconstruction_submission"
    ]:
        raise DispatchError("stage2 prior submission differs from cohort lock")
    receipt1 = verify_stage1_receipt(repo_root, receipt_path)
    verify_raw_envelope_submission(
        repo_root,
        receipt1,
        receipt_path,
        submission_path,
    )
    if receipt1["actor_binding"] != member["actor_binding"]:
        raise DispatchError("stage2 actor continuity failed")
    if receipt1["condition_binding"]["condition_id"] != condition_for_seat(seat_id):
        raise DispatchError("stage2 condition continuity failed")
    output_rel = Path(args.output).as_posix()
    if output_rel != template["planned_receipt_path"]:
        raise DispatchError("output must equal the template planned_receipt_path")

    receipt2 = {
        "$schema": STAGE2_SCHEMA_ID,
        "actor_binding": copy.deepcopy(member["actor_binding"]),
        "artifact_type": "stage2_seat_dispatch_receipt",
        "artifact_version": "0.1.0",
        "authorization_receipt": copy.deepcopy(lock["authorization_receipt"]),
        "cohort_lock": artifact_reference(repo_root, cohort_path),
        "condition_binding": {
            "condition_id": receipt1["condition_binding"]["condition_id"],
            "condition_view_path": receipt1["condition_binding"][
                "condition_view_path"
            ],
            "condition_view_sha256": receipt1["condition_binding"][
                "condition_view_sha256"
            ],
        },
        "dispatch_status": "ready_for_dispatch",
        "facility_files": copy.deepcopy(lock["common_stage2_facility_files"]),
        "participant_files": copy.deepcopy(
            lock["common_stage2_participant_files"]
        ),
        "receipt_id": f"dispatch-receipt.{RUN_ID}.{seat_id}.stage2",
        "release_authorized": True,
        "run_id": RUN_ID,
        "schema_dependency_closure": copy.deepcopy(
            lock["common_stage2_schema_dependency_closure"]
        ),
        "seat_id": seat_id,
        "stage": "prediction",
        "stage1_dispatch_receipt": artifact_reference(repo_root, receipt_path),
        "stage1_submission": artifact_reference(repo_root, submission_path),
        "template_source": artifact_reference(repo_root, template_path_value),
    }
    validate_against_repo_schema(repo_root, receipt2, STAGE2_SCHEMA_PATH)
    output = write_new(repo_root, args.output, receipt2)
    verify_stage2_receipt(repo_root, output)
    return {
        "artifact": relative_path(repo_root, output),
        "artifact_type": receipt2["artifact_type"],
        "formal_dispatch_performed": False,
        "sha256": sha256_bytes(output.read_bytes()),
        "status": "materialized",
    }


def verify_stage2_receipt(repo_root: Path, path: Path) -> dict[str, Any]:
    receipt, _, _ = read_repo_json(repo_root, relative_path(repo_root, path))
    validate_against_repo_schema(repo_root, receipt, STAGE2_SCHEMA_PATH)
    if receipt["artifact_type"] != "stage2_seat_dispatch_receipt":
        raise DispatchError("expected a stage2 dispatch receipt")
    template_file = verify_reference(repo_root, receipt["template_source"])
    template = verify_dispatch_template(repo_root, template_file, "prediction")
    if relative_path(repo_root, path) != template["planned_receipt_path"]:
        raise DispatchError("stage2 receipt path differs from immutable template plan")
    if receipt["seat_id"] != template["seat_id"]:
        raise DispatchError("stage2 receipt seat differs from template")
    condition_id = condition_for_seat(receipt["seat_id"])
    verify_file_lists(
        repo_root, receipt, "prediction", condition_id, expect_hashes=True
    )
    cohort_path = verify_reference(repo_root, receipt["cohort_lock"])
    lock = verify_cohort_lock(repo_root, cohort_path)
    member = find_member(lock, receipt["seat_id"])
    if receipt["authorization_receipt"] != lock["authorization_receipt"]:
        raise DispatchError("stage2 authorization differs from cohort lock")
    verify_authorization_receipt(repo_root, receipt["authorization_receipt"])
    if receipt["participant_files"] != lock["common_stage2_participant_files"]:
        raise DispatchError("stage2 participant inputs differ from cohort common set")
    if receipt["facility_files"] != lock["common_stage2_facility_files"]:
        raise DispatchError("stage2 facility files differ from cohort common set")
    if (
        receipt["schema_dependency_closure"]
        != lock["common_stage2_schema_dependency_closure"]
    ):
        raise DispatchError("stage2 schema closure differs from cohort common set")
    if receipt["stage1_dispatch_receipt"] != member["stage1_dispatch_receipt"]:
        raise DispatchError("stage2 prior receipt differs from cohort member")
    if receipt["stage1_submission"] != member["reconstruction_submission"]:
        raise DispatchError("stage2 prior submission differs from cohort member")
    receipt1_path = verify_reference(
        repo_root, receipt["stage1_dispatch_receipt"]
    )
    receipt1 = verify_stage1_receipt(repo_root, receipt1_path)
    submission_path = verify_reference(repo_root, receipt["stage1_submission"])
    verify_raw_envelope_submission(
        repo_root,
        receipt1,
        receipt1_path,
        submission_path,
    )
    if receipt["actor_binding"] != member["actor_binding"]:
        raise DispatchError("stage2 actor binding differs from cohort member")
    if receipt["condition_binding"] != {
        "condition_id": receipt1["condition_binding"]["condition_id"],
        "condition_view_path": receipt1["condition_binding"]["condition_view_path"],
        "condition_view_sha256": receipt1["condition_binding"][
            "condition_view_sha256"
        ],
    }:
        raise DispatchError("stage2 inherited condition binding cannot be reproduced")
    return receipt


def write_synthetic_authorization_chain(repo_root: Path) -> None:
    freeze_commit = "1" * 40
    frozen_digest = "2" * 64
    truth_commitment = {
        "algorithm": "SHA-256",
        "combination": "secret_nonce_bytes || exact_truth_bundle_bytes",
        "commitment": "3" * 64,
        "created_at": "2026-07-27T05:59:00Z",
        "nonce_length_bytes": 32,
        "truth_bundle_bytes": 1,
        "truth_bundle_name": "sealed-truth.json",
    }
    supporting_documents = {
        FORMAL_BUILD_READINESS_PATH: {
            "$schema": URL_PREFIX
            + f"{SCHEMA}/formal-build-readiness-0.1.0.schema.json",
            "artifact_type": "formal_build_readiness",
            "formal_input_executed": False,
            "formal_result_produced": False,
            "overall_status": "passed",
            "readiness_scope": "build_only",
            "run_id": RUN_ID,
            "synthetic_self_test_only": True,
        },
        FIXTURE_LOCK_PATH: {
            "$schema": URL_PREFIX + f"{SCHEMA}/fixture-lock-0.1.0.schema.json",
            "artifact_type": "fixture_lock",
            "fixture_state": "locked",
            "formal_execution_authorized": False,
            "formal_input_executed": False,
            "run_id": RUN_ID,
            "synthetic_self_test_only": True,
        },
        PROJECTION_AUDIT_PATH: {
            "$schema": URL_PREFIX + ROLE_012_PATH,
            "artifact_type": "source_fidelity_audit",
            "audit_decision": "approved",
            "run_id": RUN_ID,
            "stage": "source_audit",
            "synthetic_self_test_only": True,
        },
        PROTOCOL_INCIDENT_PATH: {
            "$schema": URL_PREFIX + PROTOCOL_INCIDENT_SCHEMA_PATH,
            "aggregate_state": {
                "formal_input_byte_read": True,
                "formal_input_executed": False,
                "formal_result_produced": False,
            },
            "artifact_type": "protocol_incident_record",
            "artifact_version": "0.1.0",
            "case_id": "CA-R3",
            "evidence_scope_note": (
                "Any formal_input_read=false assertion in R3 build evidence "
                "is scoped only to the recorded build, list, and guard-probe "
                "processes; it is not an aggregate run-level assertion."
            ),
            "exposure": {
                "content_exposed_to_main_thread": False,
                "content_exposed_to_prediction_flow": False,
                "digest_exposed_to_main_thread": False,
                "formal_result_observed": False,
            },
            "fact_basis": {
                "independent_process_log_available": False,
                "kind": "subtask_self_report",
                "limitation": (
                    "Negative exposure and non-operation statements are based "
                    "on the subtask report and available task output, not an "
                    "independent byte-level process transcript."
                ),
            },
            "gate_disposition": {
                "recommended": (
                    "retain_with_documented_nonsemantic_integrity_exception"
                ),
                "required": True,
                "status": "pending_explicit_human_acceptance",
            },
            "incident_id": PROTOCOL_INCIDENT_ID,
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
            "phase": "pre_gate_evidence_hardening",
            "run_id": RUN_ID,
            "sequence_position": (
                "after_r3_evidence_generation_before_pre_audit_freeze"
            ),
            "target_artifact": {
                "artifact_id": "fixture.r3.formal-input-v0.1.0",
                "path": "fixtures/r3/formal-input-r3-v0.1.0.json",
            },
        },
    }
    for relative, document in supporting_documents.items():
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_bytes(document))

    verifier_path = repo_root / FORMAL_READINESS_VERIFIER_PATH
    verifier_path.parent.mkdir(parents=True, exist_ok=True)
    verifier_path.write_bytes(
        b"synthetic read-only readiness verifier; no formal input is present\n"
    )

    manifest = {
        "artifact_type": "formal_run_manifest",
        "artifacts": [
            {
                "included_in_frozen_set": True,
                "path": relative.removeprefix(RUN + "/"),
                "sha256": sha256_bytes((repo_root / relative).read_bytes()),
            }
            for relative in (
                FORMAL_BUILD_READINESS_PATH,
                FIXTURE_LOCK_PATH,
                PROJECTION_AUDIT_PATH,
                PROTOCOL_INCIDENT_PATH,
            )
        ],
        "freeze_commit": freeze_commit,
        "frozen_artifact_set_digest": frozen_digest,
        "run_id": RUN_ID,
        "status": "frozen",
        "synthetic_self_test_only": True,
        "truth_commitment": truth_commitment,
    }
    manifest_path = repo_root / f"{RUN}/manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(canonical_bytes(manifest))

    authorization = {
        "$schema": AUTHORIZATION_SCHEMA_ID,
        "artifact_type": "formal_human_gate_authorization",
        "artifact_version": "0.1.0",
        "authorization_basis": {
            "decision": "synthetic_only",
            "message_sha256": sha256_bytes(
                b"synthetic authorization for disposable self-test repository"
            ),
            "source_kind": "synthetic_self_test",
            "source_locator": "synthetic-self-test://local-only",
        },
        "authorization_context": "synthetic_self_test",
        "authorization_id": "authorization.continuous-001.synthetic-self-test",
        "authorization_phrase": (
            "SYNTHETIC_SELF_TEST_ONLY_DO_NOT_DISPATCH_OR_EXECUTE"
        ),
        "authorization_scopes": {
            "blind_dispatch_authorized": False,
            "formal_execution_after_prediction_freeze_authorized": False,
            "synthetic_receipt_materialization_authorized": True,
        },
        "authorization_state": "synthetic_only",
        "authorized_at": "2026-07-27T06:01:00Z",
        "authorized_by": {
            "identifier": "materialize-dispatch.self-test",
            "role": "self_test_harness",
        },
        "contract_artifacts": {
            "authorization_schema": artifact_reference(
                repo_root, AUTHORIZATION_SCHEMA_PATH
            ),
            **{
                name: artifact_reference(repo_root, path)
                for name, path in RAW_TRACE_SCHEMA_PATHS.items()
            },
            "dispatch_materializer": artifact_reference(
                repo_root, DISPATCH_MATERIALIZER_PATH
            ),
            "execution_permit_materializer": artifact_reference(
                repo_root, EXECUTION_PERMIT_MATERIALIZER_PATH
            ),
            "execution_permit_schema": artifact_reference(
                repo_root, EXECUTION_PERMIT_SCHEMA_PATH
            ),
            "execution_permit_verifier": artifact_reference(
                repo_root, EXECUTION_PERMIT_VERIFIER_PATH
            ),
            "formal_comparator_output_schema": artifact_reference(
                repo_root, FORMAL_COMPARATOR_OUTPUT_SCHEMA_PATH
            ),
            "protocol_incident_schema": artifact_reference(
                repo_root, PROTOCOL_INCIDENT_SCHEMA_PATH
            ),
            "raw_trace_verifier": artifact_reference(
                repo_root, RAW_TRACE_VERIFIER_PATH
            ),
            "submission_builder": artifact_reference(
                repo_root, SUBMISSION_BUILDER_PATH
            ),
        },
        "final_build_readiness": artifact_reference(
            repo_root, FORMAL_BUILD_READINESS_PATH
        ),
        "fixture_lock": artifact_reference(repo_root, FIXTURE_LOCK_PATH),
        "formal_readiness_verifier": artifact_reference(
            repo_root, FORMAL_READINESS_VERIFIER_PATH
        ),
        "frozen_artifact_set_digest": frozen_digest,
        "frozen_manifest_path": f"{RUN}/manifest.json",
        "freeze_commit": freeze_commit,
        "manifest_status_at_authorization": "frozen",
        "projection_audit": artifact_reference(repo_root, PROJECTION_AUDIT_PATH),
        "protocol_incident_disposition": {
            "acknowledged_facts": {
                "byte_integrity_read_occurred": True,
                "fact_basis_is_subtask_self_report": True,
                "no_semantic_content_or_result_exposure_reported": True,
            },
            "disposition": "synthetic_only",
            "incident_id": PROTOCOL_INCIDENT_ID,
            "incident_record": artifact_reference(
                repo_root,
                PROTOCOL_INCIDENT_PATH,
            ),
            "recorded_gate_status": "pending_explicit_human_acceptance",
        },
        "run_id": RUN_ID,
        "state_at_authorization": {
            "blind_dispatch_performed": False,
            "formal_input_executed": False,
            "formal_result_produced": False,
        },
        "truth_commitment": truth_commitment,
        "verification": {
            "require_frozen": True,
            "status": "passed",
            "verified_at": "2026-07-27T06:00:00Z",
        },
    }
    marker_path = repo_root / SYNTHETIC_AUTHORIZATION_MARKER
    marker_path.write_text(
        SYNTHETIC_AUTHORIZATION_TOKEN + "\n",
        encoding="utf-8",
        newline="\n",
    )
    authorization_path = repo_root / AUTHORIZATION_PATH
    authorization_path.parent.mkdir(parents=True, exist_ok=True)
    authorization_path.write_bytes(canonical_bytes(authorization))
    os.environ[SYNTHETIC_AUTHORIZATION_ENV] = SYNTHETIC_AUTHORIZATION_TOKEN
    verify_authorization_receipt(
        repo_root,
        artifact_reference(repo_root, AUTHORIZATION_PATH),
    )


def verify_command(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    path = repo_path(repo_root, args.artifact)
    document, raw = read_json(path)
    artifact_type = document.get("artifact_type")
    if artifact_type == "stage1_seat_dispatch_receipt":
        verify_stage1_receipt(repo_root, path)
    elif artifact_type == "stage1_cohort_lock":
        verify_cohort_lock(repo_root, path)
    elif artifact_type == "stage2_seat_dispatch_receipt":
        verify_stage2_receipt(repo_root, path)
    else:
        raise DispatchError(f"unsupported verification artifact: {artifact_type}")
    return {
        "artifact": relative_path(repo_root, path),
        "artifact_type": artifact_type,
        "formal_dispatch_performed": False,
        "sha256": sha256_bytes(raw),
        "status": "verified",
    }


def self_test(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    for schema_path in (
        STAGE1_SCHEMA_PATH,
        STAGE2_SCHEMA_PATH,
        COHORT_SCHEMA_PATH,
        AUTHORIZATION_SCHEMA_PATH,
    ):
        schema, _, _ = read_repo_json(repo_root, schema_path)
        Draft202012Validator.check_schema(schema)
    for seat in SEATS:
        verify_dispatch_template(
            repo_root, template_path(repo_root, "reconstruction", seat), "reconstruction"
        )
        verify_dispatch_template(
            repo_root, template_path(repo_root, "prediction", seat), "prediction"
        )

    actor_a = {
        "identifier": "actor-a",
        "model": "test",
        "model_version": "test",
        "reasoning_effort": "high",
        "role": "blind_reconstructor_predictor",
        "session_id": "session-a",
    }
    actor_b = dict(reversed(list(actor_a.items())))
    if actor_object_sha256(actor_a) != actor_object_sha256(actor_b):
        raise DispatchError("actor hash is not independent of input key order")
    if b"\r\n" in canonical_bytes(actor_a) or not canonical_bytes(actor_a).endswith(
        b"\n"
    ):
        raise DispatchError("canonical JSON newline contract failed")

    synthetic_members = []
    for index, seat in enumerate(SEATS, start=1):
        synthetic_members.append(
            {
                "actor_binding": {
                    "actor_identifier": f"actor-{index}",
                    "actor_object_sha256": f"{index:064x}",
                    "session_id": f"session-{index}",
                },
                "condition_id": condition_for_seat(seat),
                "seat_id": seat,
            }
        )
    validate_cohort_independence(synthetic_members)
    duplicate = copy.deepcopy(synthetic_members)
    duplicate[1]["actor_binding"]["session_id"] = duplicate[0]["actor_binding"][
        "session_id"
    ]
    try:
        validate_cohort_independence(duplicate)
    except DispatchError:
        pass
    else:
        raise DispatchError("duplicate session negative control did not fail")

    with tempfile.TemporaryDirectory(
        prefix="continuous-dispatch-self-test-",
        dir=tempfile.gettempdir(),
    ) as temp:
        test_path = Path(temp) / "canonical.json"
        test_path.write_bytes(canonical_bytes(actor_a))
        if test_path.read_bytes() != canonical_bytes(actor_b):
            raise DispatchError("temporary canonical-byte round trip failed")

        synthetic_root = (Path(temp) / "synthetic-repository").resolve()
        required_paths = (
            {
                STAGE1_SCHEMA_PATH,
                DISPATCH_MATERIALIZER_PATH,
                EXECUTION_PERMIT_MATERIALIZER_PATH,
                EXECUTION_PERMIT_SCHEMA_PATH,
                EXECUTION_PERMIT_VERIFIER_PATH,
                FORMAL_COMPARATOR_OUTPUT_SCHEMA_PATH,
                PROTOCOL_INCIDENT_SCHEMA_PATH,
                *RAW_TRACE_SCHEMA_PATHS.values(),
                RAW_TRACE_VERIFIER_PATH,
                ROLE_011_PATH,
                SUBMISSION_BUILDER_PATH,
                f"{INPUTS}/stage1-dispatch-p01.template.json",
            }
            | STAGE1_FACILITY_PATHS
            | expected_participant_paths("reconstruction", "condition-v01")
        )
        for relative in required_paths:
            source = repo_path(repo_root, relative)
            target = synthetic_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        actor_path = synthetic_root / "synthetic/actor.json"
        actor_path.parent.mkdir(parents=True, exist_ok=True)
        actor_path.write_bytes(canonical_bytes(actor_a))
        write_synthetic_authorization_chain(synthetic_root)
        authorization_path = synthetic_root / AUTHORIZATION_PATH
        authorization_before = authorization_path.read_bytes()
        tampered_authorization, _ = read_json(authorization_path)
        tampered_authorization["authorization_basis"]["message_sha256"] = "0" * 64
        authorization_path.write_bytes(canonical_bytes(tampered_authorization))
        try:
            verify_authorization_receipt(
                synthetic_root,
                artifact_reference(synthetic_root, AUTHORIZATION_PATH),
            )
        except DispatchError:
            pass
        else:
            raise DispatchError(
                "malformed authorization negative control did not fail"
            )
        finally:
            authorization_path.write_bytes(authorization_before)
        tampered_authorization, _ = read_json(authorization_path)
        tampered_authorization["protocol_incident_disposition"][
            "disposition"
        ] = "accepted_nonsemantic_integrity_exception"
        authorization_path.write_bytes(canonical_bytes(tampered_authorization))
        try:
            verify_authorization_receipt(
                synthetic_root,
                artifact_reference(synthetic_root, AUTHORIZATION_PATH),
            )
        except DispatchError:
            pass
        else:
            raise DispatchError(
                "protocol-incident disposition negative control did not fail"
            )
        finally:
            authorization_path.write_bytes(authorization_before)
        synthetic_output = synthetic_root / (
            f"{RUN}/submissions/dispatch/stage1-p01.json"
        )
        synthetic_output.parent.mkdir(parents=True, exist_ok=True)
        template_copy = synthetic_root / (
            f"{INPUTS}/stage1-dispatch-p01.template.json"
        )
        template_before = template_copy.read_bytes()
        result = materialize_stage1(
            argparse.Namespace(
                repo_root=synthetic_root,
                template=f"{INPUTS}/stage1-dispatch-p01.template.json",
                actor="synthetic/actor.json",
                authorization_receipt=AUTHORIZATION_PATH,
                output=f"{RUN}/submissions/dispatch/stage1-p01.json",
            )
        )
        if result["status"] != "materialized":
            raise DispatchError("synthetic stage1 receipt was not materialized")
        if template_copy.read_bytes() != template_before:
            raise DispatchError("materialization mutated an inert template")
        verify_stage1_receipt(synthetic_root, synthetic_output)
        try:
            materialize_stage1(
                argparse.Namespace(
                    repo_root=synthetic_root,
                    template=f"{INPUTS}/stage1-dispatch-p01.template.json",
                    actor="synthetic/actor.json",
                    authorization_receipt=AUTHORIZATION_PATH,
                    output=f"{RUN}/submissions/dispatch/stage1-p01.json",
                )
            )
        except DispatchError:
            pass
        else:
            raise DispatchError("existing receipt overwrite negative control did not fail")
        try:
            write_new(
                synthetic_root,
                f"{INPUTS}/forbidden-output.template.json",
                {"synthetic": True},
            )
        except DispatchError:
            pass
        else:
            raise DispatchError("template output negative control did not fail")

    return {
        "formal_dispatch_performed": False,
        "formal_input_executed": False,
        "authorization_negative_controls_checked": 2,
        "schemas_checked": 4,
        "synthetic_stage1_receipts_checked": 1,
        "status": "synthetic_self_test_passed",
        "templates_checked": 8,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    stage1 = commands.add_parser("materialize-stage1")
    stage1.add_argument("--repo-root", required=True, type=Path)
    stage1.add_argument("--template", required=True)
    stage1.add_argument("--actor", required=True)
    stage1.add_argument("--authorization-receipt", required=True)
    stage1.add_argument("--output", required=True)
    stage1.set_defaults(func=materialize_stage1)

    cohort = commands.add_parser("materialize-cohort")
    cohort.add_argument("--repo-root", required=True, type=Path)
    cohort.add_argument("--stage1-receipt", action="append", required=True)
    cohort.add_argument("--stage1-submission", action="append", required=True)
    cohort.add_argument("--authorization-receipt", required=True)
    cohort.add_argument("--output", required=True)
    cohort.set_defaults(func=materialize_cohort)

    stage2 = commands.add_parser("materialize-stage2")
    stage2.add_argument("--repo-root", required=True, type=Path)
    stage2.add_argument("--template", required=True)
    stage2.add_argument("--cohort-lock", required=True)
    stage2.add_argument("--stage1-receipt", required=True)
    stage2.add_argument("--stage1-submission", required=True)
    stage2.add_argument("--output", required=True)
    stage2.set_defaults(func=materialize_stage2)

    verify = commands.add_parser("verify")
    verify.add_argument("--repo-root", required=True, type=Path)
    verify.add_argument("--artifact", required=True)
    verify.set_defaults(func=verify_command)

    smoke = commands.add_parser("self-test")
    smoke.add_argument("--repo-root", required=True, type=Path)
    smoke.set_defaults(func=self_test)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        result = args.func(args)
    except (DispatchError, KeyError, TypeError, ValueError) as error:
        print(
            json.dumps(
                {
                    "formal_dispatch_performed": False,
                    "status": "failed_closed",
                    "error": str(error),
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
