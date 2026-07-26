#!/usr/bin/env python3
"""Run the blind packaging pipeline against a disposable synthetic repository.

The test deliberately copies only the blind-dispatch schemas, frozen participant
inputs, and the two packaging tools that it exercises.  It never copies or runs
formal inputs, comparators, fixtures, or real dispatch artifacts.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


BASE = "research/calibration-tests/continuous-action-pilot"
RUN = f"{BASE}/runs/continuous-001"
INPUTS = f"{RUN}/inputs"
SCHEMA = f"{BASE}/schema"
TOOLS = f"{BASE}/tools"
URL_PREFIX = "https://github.com/onovich/Game-Primitives/blob/main/"

DISPATCH_TOOL = f"{TOOLS}/materialize-dispatch.py"
SUBMISSION_TOOL = f"{TOOLS}/build-role-submission.py"
EXECUTION_PERMIT_MATERIALIZER = f"{TOOLS}/materialize-execution-permit.py"
EXECUTION_PERMIT_VERIFIER = f"{TOOLS}/verify-formal-execution-permit.py"
RAW_TRACE_VERIFIER = f"{TOOLS}/verify-formal-raw-trace.py"
COHORT_LOCK = f"{RUN}/submissions/dispatch/stage1-cohort-lock.json"
AUTHORIZATION = f"{RUN}/submissions/dispatch/human-gate-authorization.json"
FORMAL_BUILD_READINESS = (
    f"{RUN}/fixtures/formal-build-readiness-v0.1.0.json"
)
FIXTURE_LOCK = f"{RUN}/fixtures/fixture-lock.json"
PROJECTION_AUDIT = f"{RUN}/source/projection-audit-v0.1.0.json"
FORMAL_READINESS_VERIFIER = f"{TOOLS}/verify-formal-readiness.py"
SYNTHETIC_AUTHORIZATION_ENV = (
    "GAME_PRIMITIVES_INTERNAL_SYNTHETIC_AUTHORIZATION"
)
SYNTHETIC_AUTHORIZATION_TOKEN = (
    "continuous-001-disposable-blind-pipeline-self-test"
)
SYNTHETIC_AUTHORIZATION_MARKER = ".synthetic-blind-pipeline-self-test"
SEATS = ("p01", "p02", "p03", "p04")

SCHEMA_FILES = {
    f"{SCHEMA}/blind-response-interface-0.1.0.schema.json",
    f"{SCHEMA}/ca-sr-artifact-0.1.0.schema.json",
    f"{SCHEMA}/ca-r1-raw-trace-0.1.0.schema.json",
    f"{SCHEMA}/ca-r2-raw-trace-0.1.0.schema.json",
    f"{SCHEMA}/ca-r3-raw-trace-0.1.0.schema.json",
    f"{SCHEMA}/formal-comparator-output-0.1.0.schema.json",
    f"{SCHEMA}/formal-human-gate-authorization-0.1.0.schema.json",
    f"{SCHEMA}/formal-execution-permit-0.1.0.schema.json",
    f"{SCHEMA}/response-template-0.1.0.schema.json",
    f"{SCHEMA}/role-submission-0.1.1.schema.json",
    f"{SCHEMA}/role-submission-0.1.2.schema.json",
    f"{SCHEMA}/stage1-cohort-lock-0.1.0.schema.json",
    f"{SCHEMA}/stage1-seat-dispatch-envelope-0.1.0.schema.json",
    f"{SCHEMA}/stage2-seat-dispatch-envelope-0.1.0.schema.json",
    f"{SCHEMA}/task-packet-0.1.0.schema.json",
    f"{SCHEMA}/task-packet-0.1.2.schema.json",
    f"{SCHEMA}/variant-envelope-0.1.0.schema.json",
}
INPUT_FILES = {
    f"{INPUTS}/prediction-response.template.json",
    f"{INPUTS}/reconstruction-response.template.json",
    f"{INPUTS}/stage1-condition-v01.task.json",
    f"{INPUTS}/stage1-condition-v02.task.json",
    f"{INPUTS}/stage1-view-v01.json",
    f"{INPUTS}/stage1-view-v02.json",
    f"{INPUTS}/stage2-prediction.task.json",
    f"{INPUTS}/stage2-variant-envelope.json",
    *{
        f"{INPUTS}/stage{stage}-dispatch-{seat}.template.json"
        for stage in (1, 2)
        for seat in SEATS
    },
}
TOOL_FILES = {
    DISPATCH_TOOL,
    EXECUTION_PERMIT_MATERIALIZER,
    EXECUTION_PERMIT_VERIFIER,
    RAW_TRACE_VERIFIER,
    SUBMISSION_TOOL,
}
MINIMAL_FILES = SCHEMA_FILES | INPUT_FILES | TOOL_FILES


class SelfTestFailure(RuntimeError):
    """The synthetic pipeline did not preserve a required invariant."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SelfTestFailure(f"expected a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_path(repo_root: Path, relative: str) -> Path:
    candidate = (repo_root / relative).resolve()
    if not candidate.is_relative_to(repo_root):
        raise SelfTestFailure(f"path escapes repository root: {relative}")
    return candidate


def condition_for_seat(seat: str) -> str:
    return "condition-v01" if seat in ("p01", "p02") else "condition-v02"


def condition_task(seat: str) -> str:
    suffix = "v01" if condition_for_seat(seat) == "condition-v01" else "v02"
    return f"{INPUTS}/stage1-condition-{suffix}.task.json"


def actor_path(seat: str) -> str:
    return f"synthetic/actors/{seat}.json"


def stage1_receipt(seat: str) -> str:
    return f"{RUN}/submissions/dispatch/stage1-{seat}.json"


def stage2_receipt(seat: str) -> str:
    return f"{RUN}/submissions/dispatch/stage2-{seat}.json"


def artifact_path(stage: str, kind: str, seat: str) -> str:
    return f"{RUN}/submissions/self-test/{stage}/{kind}-{seat}.json"


def snapshot_directory(path: Path) -> dict[str, str] | None:
    if not path.exists():
        return None
    if not path.is_dir():
        raise SelfTestFailure(f"expected a directory: {path}")
    snapshot = {".": "directory"}
    for item in sorted(path.rglob("*")):
        relative = item.relative_to(path).as_posix()
        snapshot[relative] = sha256(item) if item.is_file() else "directory"
    return snapshot


def assert_safe_copy_set() -> None:
    forbidden_fragments = (
        "/comparators/",
        "/fixtures/",
        "/formal-input",
        "/formal_input",
        "/results/",
        "compare-",
    )
    for relative in MINIMAL_FILES:
        normalized = "/" + relative.replace("\\", "/").lower()
        if any(fragment in normalized for fragment in forbidden_fragments):
            raise SelfTestFailure(
                f"synthetic copy set contains a forbidden artifact: {relative}"
            )


def copy_minimal_repository(source_root: Path, target_root: Path) -> None:
    assert_safe_copy_set()
    for relative in sorted(MINIMAL_FILES):
        source = repo_path(source_root, relative)
        if not source.is_file():
            raise SelfTestFailure(f"required source artifact is missing: {relative}")
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def make_actor(seat: str) -> dict[str, str]:
    return {
        "identifier": f"synthetic-actor-{seat}",
        "model": "synthetic-model",
        "model_version": "self-test-0.1.0",
        "reasoning_effort": "high",
        "role": "blind_reconstructor_predictor",
        "session_id": f"synthetic-session-{seat}",
    }


def fill_pollution(payload: dict[str, Any]) -> None:
    payload["pollution"] = {
        "familiarity": {
            "exact_result_knowledge": "none",
            "exact_rule_knowledge": "none",
            "exact_variant_knowledge": "none",
            "project_exposure": "none",
            "recognition_status": "none",
            "recognized_family": None,
            "recognized_work": None,
            "related_genre_experience": "none",
        },
        "integrity_exposures": [],
        "stage_update_note": None,
    }


def assert_no_placeholders(value: Any, location: str = "<root>") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert_no_placeholders(child, f"{location}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_placeholders(child, f"{location}/{index}")
    elif isinstance(value, str) and value.startswith("<") and value.endswith(">"):
        raise SelfTestFailure(f"unfilled response placeholder at {location}: {value}")


def reconstruction_payload(repo_root: Path, seat: str) -> dict[str, Any]:
    wrapper = read_json(
        repo_path(repo_root, f"{INPUTS}/reconstruction-response.template.json")
    )
    payload = copy.deepcopy(wrapper["template_payload"])
    fill_pollution(payload)
    for answer in payload["reconstruction_answers"]:
        case_token = answer["case_id"].lower()
        answer["ambiguities"] = ["synthetic ambiguity retained for self-test"]
        answer["assumptions"] = []
        answer["confidence_percent"] = 25
        answer["uniqueness"] = "multiple_compatible_structures"
        answer["recovered_facts"] = [
            {
                "claim": "The dispatched view does not uniquely determine this fact.",
                "fact_id": f"fact.{seat}.{case_token}",
                "recovery_status": "not_recoverable",
                "supporting_record_ids": [],
            }
        ]
        answer["compatible_branches"] = [
            {
                "branch_id": f"branch.{seat}.{case_token}.a",
                "description": "Synthetic compatible branch A.",
                "supporting_record_ids": [],
            },
            {
                "branch_id": f"branch.{seat}.{case_token}.b",
                "description": "Synthetic compatible branch B.",
                "supporting_record_ids": [],
            },
        ]
    assert_no_placeholders(payload)
    return payload


def prediction_payload(repo_root: Path, seat: str) -> dict[str, Any]:
    wrapper = read_json(
        repo_path(repo_root, f"{INPUTS}/prediction-response.template.json")
    )
    payload = copy.deepcopy(wrapper["template_payload"])
    fill_pollution(payload)
    for answer in payload["prediction_answers"]:
        answer["assumptions"] = []
        answer["compatible_alternatives"] = []
        answer["confidence_percent"] = 25
        answer["prediction_status"] = "determinate"
        answer["reasoning"] = (
            f"Synthetic scope-valid prediction for {seat}; no fixture was executed."
        )
        answer["supporting_record_ids"] = []
        for expectation in answer["expectations"]:
            expectation["expectation_kind"] = "status"
            expectation["value"] = {
                "serialized_value": "synthetic",
                "unit": None,
                "value_type": "status",
            }
    assert_no_placeholders(payload)
    return payload


def run_cli(
    repo_root: Path,
    tool: str,
    arguments: list[str],
    *,
    expected_status: str | None = None,
    expected_failure_contains: str | None = None,
    expect_success: bool = True,
    synthetic_environment: bool = True,
) -> dict[str, Any] | None:
    executable = repo_path(repo_root, tool)
    if tool not in TOOL_FILES:
        raise SelfTestFailure(f"attempted to run a non-whitelisted tool: {tool}")
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if synthetic_environment:
        environment[SYNTHETIC_AUTHORIZATION_ENV] = SYNTHETIC_AUTHORIZATION_TOKEN
    else:
        environment.pop(SYNTHETIC_AUTHORIZATION_ENV, None)
    completed = subprocess.run(
        [sys.executable, str(executable), *arguments],
        cwd=repo_root,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=120,
    )
    if expect_success:
        if completed.returncode != 0:
            raise SelfTestFailure(
                "synthetic command failed:\n"
                f"tool={tool}\nargs={arguments}\n"
                f"stdout={completed.stdout}\nstderr={completed.stderr}"
            )
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            raise SelfTestFailure(f"synthetic command returned no JSON: {tool}")
        try:
            result = json.loads(lines[-1])
        except json.JSONDecodeError as error:
            raise SelfTestFailure(
                f"synthetic command returned invalid JSON: {completed.stdout}"
            ) from error
        if not isinstance(result, dict):
            raise SelfTestFailure(f"synthetic command returned non-object JSON: {tool}")
        if expected_status is not None and result.get("status") != expected_status:
            raise SelfTestFailure(
                f"{tool} returned status {result.get('status')!r}; "
                f"expected {expected_status!r}"
            )
        return result

    if completed.returncode == 0:
        raise SelfTestFailure(
            "negative control unexpectedly succeeded:\n"
            f"tool={tool}\nargs={arguments}\nstdout={completed.stdout}"
        )
    combined_output = completed.stdout + "\n" + completed.stderr
    if (
        expected_failure_contains is None
        or expected_failure_contains not in combined_output
    ):
        raise SelfTestFailure(
            "negative control failed for an unexpected reason:\n"
            f"tool={tool}\nargs={arguments}\n"
            f"expected={expected_failure_contains!r}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return None


def materialize_stage1(repo_root: Path, seat: str) -> None:
    run_cli(
        repo_root,
        DISPATCH_TOOL,
        [
            "materialize-stage1",
            "--repo-root",
            str(repo_root),
            "--template",
            f"{INPUTS}/stage1-dispatch-{seat}.template.json",
            "--actor",
            actor_path(seat),
            "--authorization-receipt",
            AUTHORIZATION,
            "--output",
            stage1_receipt(seat),
        ],
        expected_status="materialized",
    )


def package_reconstruction(repo_root: Path, seat: str) -> None:
    task = condition_task(seat)
    receipt = stage1_receipt(seat)
    envelope = artifact_path("reconstruction", "envelope", seat)
    payload = artifact_path("reconstruction", "payload", seat)
    submission = artifact_path("reconstruction", "submission", seat)
    write_json(repo_path(repo_root, payload), reconstruction_payload(repo_root, seat))

    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "capture-envelope",
            "--repo-root",
            str(repo_root),
            "--task",
            task,
            "--actor",
            actor_path(seat),
            "--dispatch-receipt",
            receipt,
            "--submission-id",
            f"submission.reconstruction.synthetic.{seat}",
            "--envelope-output",
            envelope,
        ],
        expected_status="envelope_captured",
    )
    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "assemble",
            "--repo-root",
            str(repo_root),
            "--task",
            task,
            "--envelope",
            envelope,
            "--payload",
            payload,
            "--dispatch-receipt",
            receipt,
            "--submission-output",
            submission,
        ],
        expected_status="assembled",
    )
    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "verify",
            "--repo-root",
            str(repo_root),
            "--task",
            task,
            "--envelope",
            envelope,
            "--payload",
            payload,
            "--dispatch-receipt",
            receipt,
            "--submission",
            submission,
        ],
        expected_status="verified",
    )


def run_negative_controls(repo_root: Path) -> dict[str, str]:
    negative_root = repo_path(repo_root, f"{RUN}/submissions/self-test/negative")
    negative_root.mkdir(parents=True, exist_ok=True)
    task = condition_task("p01")

    missing_output = f"{RUN}/submissions/self-test/negative/missing-receipt.json"
    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "capture-envelope",
            "--repo-root",
            str(repo_root),
            "--task",
            task,
            "--actor",
            actor_path("p01"),
            "--submission-id",
            "negative.missing.receipt",
            "--envelope-output",
            missing_output,
        ],
        expected_failure_contains=(
            "the following arguments are required: --dispatch-receipt"
        ),
        expect_success=False,
    )
    if repo_path(repo_root, missing_output).exists():
        raise SelfTestFailure("missing-receipt control created an envelope")

    wrong_actor_output = f"{RUN}/submissions/self-test/negative/wrong-actor.json"
    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "capture-envelope",
            "--repo-root",
            str(repo_root),
            "--task",
            task,
            "--actor",
            actor_path("p02"),
            "--dispatch-receipt",
            stage1_receipt("p01"),
            "--submission-id",
            "negative.wrong.actor",
            "--envelope-output",
            wrong_actor_output,
        ],
        expected_failure_contains=(
            "dispatch receipt actor differs from packaging actor"
        ),
        expect_success=False,
    )
    if repo_path(repo_root, wrong_actor_output).exists():
        raise SelfTestFailure("wrong-actor control created an envelope")

    template_output = f"{RUN}/submissions/self-test/negative/template-receipt.json"
    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "capture-envelope",
            "--repo-root",
            str(repo_root),
            "--task",
            task,
            "--actor",
            actor_path("p01"),
            "--dispatch-receipt",
            f"{INPUTS}/stage1-dispatch-p01.template.json",
            "--submission-id",
            "negative.template.receipt",
            "--envelope-output",
            template_output,
        ],
        expected_failure_contains="expected a stage1 dispatch receipt",
        expect_success=False,
    )
    if repo_path(repo_root, template_output).exists():
        raise SelfTestFailure("template-as-receipt control created an envelope")

    return {
        "missing_receipt": "failed_closed",
        "template_as_receipt": "failed_closed",
        "wrong_actor_or_seat_binding": "failed_closed",
    }


def materialize_cohort(repo_root: Path) -> None:
    arguments = [
        "materialize-cohort",
        "--repo-root",
        str(repo_root),
    ]
    for seat in SEATS:
        arguments.extend(
            ["--stage1-receipt", f"{seat}={stage1_receipt(seat)}"]
        )
    for seat in SEATS:
        arguments.extend(
            [
                "--stage1-submission",
                f"{seat}={artifact_path('reconstruction', 'submission', seat)}",
            ]
        )
    arguments.extend(
        [
            "--authorization-receipt",
            AUTHORIZATION,
            "--output",
            COHORT_LOCK,
        ]
    )
    run_cli(
        repo_root,
        DISPATCH_TOOL,
        arguments,
        expected_status="materialized",
    )


def materialize_stage2(repo_root: Path, seat: str) -> None:
    run_cli(
        repo_root,
        DISPATCH_TOOL,
        [
            "materialize-stage2",
            "--repo-root",
            str(repo_root),
            "--template",
            f"{INPUTS}/stage2-dispatch-{seat}.template.json",
            "--cohort-lock",
            COHORT_LOCK,
            "--stage1-receipt",
            stage1_receipt(seat),
            "--stage1-submission",
            artifact_path("reconstruction", "submission", seat),
            "--output",
            stage2_receipt(seat),
        ],
        expected_status="materialized",
    )


def package_prediction(repo_root: Path, seat: str) -> None:
    task = f"{INPUTS}/stage2-prediction.task.json"
    prior_task = condition_task(seat)
    prior_receipt = stage1_receipt(seat)
    prior_submission = artifact_path("reconstruction", "submission", seat)
    receipt = stage2_receipt(seat)
    envelope = artifact_path("prediction", "envelope", seat)
    payload = artifact_path("prediction", "payload", seat)
    submission = artifact_path("prediction", "submission", seat)
    write_json(repo_path(repo_root, payload), prediction_payload(repo_root, seat))

    common = [
        "--repo-root",
        str(repo_root),
        "--task",
        task,
    ]
    prior = [
        "--prior-stage-dispatch-receipt",
        prior_receipt,
        "--prior-stage-submission",
        prior_submission,
        "--prior-stage-task",
        prior_task,
    ]
    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "capture-envelope",
            *common,
            "--actor",
            actor_path(seat),
            "--dispatch-receipt",
            receipt,
            "--submission-id",
            f"submission.prediction.synthetic.{seat}",
            "--condition-id",
            condition_for_seat(seat),
            *prior,
            "--envelope-output",
            envelope,
        ],
        expected_status="envelope_captured",
    )
    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "assemble",
            *common,
            "--envelope",
            envelope,
            "--payload",
            payload,
            "--dispatch-receipt",
            receipt,
            *prior,
            "--submission-output",
            submission,
        ],
        expected_status="assembled",
    )
    run_cli(
        repo_root,
        SUBMISSION_TOOL,
        [
            "verify",
            *common,
            "--envelope",
            envelope,
            "--payload",
            payload,
            "--dispatch-receipt",
            receipt,
            *prior,
            "--submission",
            submission,
        ],
        expected_status="verified",
    )


def artifact_reference(repo_root: Path, relative: str) -> dict[str, str]:
    path = repo_path(repo_root, relative)
    return {
        "path": relative,
        "sha256": sha256(path),
    }


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
        FORMAL_BUILD_READINESS: {
            "$schema": URL_PREFIX
            + f"{SCHEMA}/formal-build-readiness-0.1.0.schema.json",
            "artifact_type": "formal_build_readiness",
            "formal_input_executed": False,
            "formal_result_produced": False,
            "overall_status": "passed",
            "readiness_scope": "build_only",
            "run_id": "continuous-001",
            "synthetic_self_test_only": True,
        },
        FIXTURE_LOCK: {
            "$schema": URL_PREFIX + f"{SCHEMA}/fixture-lock-0.1.0.schema.json",
            "artifact_type": "fixture_lock",
            "fixture_state": "locked",
            "formal_execution_authorized": False,
            "formal_input_executed": False,
            "run_id": "continuous-001",
            "synthetic_self_test_only": True,
        },
        PROJECTION_AUDIT: {
            "$schema": URL_PREFIX
            + f"{SCHEMA}/role-submission-0.1.2.schema.json",
            "artifact_type": "source_fidelity_audit",
            "audit_decision": "approved",
            "run_id": "continuous-001",
            "stage": "source_audit",
            "synthetic_self_test_only": True,
        },
    }
    for relative, document in supporting_documents.items():
        write_json(repo_path(repo_root, relative), document)

    verifier_path = repo_path(repo_root, FORMAL_READINESS_VERIFIER)
    verifier_path.parent.mkdir(parents=True, exist_ok=True)
    verifier_path.write_bytes(
        b"synthetic read-only readiness verifier; no formal input is present\n"
    )

    write_json(
        repo_path(repo_root, f"{RUN}/manifest.json"),
        {
            "artifact_type": "formal_run_manifest",
            "artifacts": [
                {
                    "included_in_frozen_set": True,
                    "path": relative.removeprefix(RUN + "/"),
                    "sha256": sha256(repo_path(repo_root, relative)),
                }
                for relative in (
                    FORMAL_BUILD_READINESS,
                    FIXTURE_LOCK,
                    PROJECTION_AUDIT,
                )
            ],
            "freeze_commit": freeze_commit,
            "frozen_artifact_set_digest": frozen_digest,
            "run_id": "continuous-001",
            "status": "frozen",
            "synthetic_self_test_only": True,
            "truth_commitment": truth_commitment,
        },
    )
    marker_path = repo_path(repo_root, SYNTHETIC_AUTHORIZATION_MARKER)
    marker_path.write_text(
        SYNTHETIC_AUTHORIZATION_TOKEN + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_json(
        repo_path(repo_root, AUTHORIZATION),
        {
            "$schema": URL_PREFIX
            + f"{SCHEMA}/formal-human-gate-authorization-0.1.0.schema.json",
            "artifact_type": "formal_human_gate_authorization",
            "artifact_version": "0.1.0",
            "authorization_basis": {
                "decision": "synthetic_only",
                "message_sha256": hashlib.sha256(
                    b"synthetic authorization for disposable self-test repository"
                ).hexdigest(),
                "source_kind": "synthetic_self_test",
                "source_locator": "synthetic-self-test://local-only",
            },
            "authorization_context": "synthetic_self_test",
            "authorization_id": (
                "authorization.continuous-001.synthetic-self-test"
            ),
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
                "identifier": "self-test-blind-pipeline",
                "role": "self_test_harness",
            },
            "contract_artifacts": {
                "authorization_schema": artifact_reference(
                    repo_root,
                    f"{SCHEMA}/formal-human-gate-authorization-0.1.0.schema.json",
                ),
                "ca_r1_raw_trace_schema": artifact_reference(
                    repo_root,
                    f"{SCHEMA}/ca-r1-raw-trace-0.1.0.schema.json",
                ),
                "ca_r2_raw_trace_schema": artifact_reference(
                    repo_root,
                    f"{SCHEMA}/ca-r2-raw-trace-0.1.0.schema.json",
                ),
                "ca_r3_raw_trace_schema": artifact_reference(
                    repo_root,
                    f"{SCHEMA}/ca-r3-raw-trace-0.1.0.schema.json",
                ),
                "dispatch_materializer": artifact_reference(
                    repo_root, DISPATCH_TOOL
                ),
                "execution_permit_materializer": artifact_reference(
                    repo_root, EXECUTION_PERMIT_MATERIALIZER
                ),
                "execution_permit_schema": artifact_reference(
                    repo_root,
                    f"{SCHEMA}/formal-execution-permit-0.1.0.schema.json",
                ),
                "execution_permit_verifier": artifact_reference(
                    repo_root, EXECUTION_PERMIT_VERIFIER
                ),
                "formal_comparator_output_schema": artifact_reference(
                    repo_root,
                    f"{SCHEMA}/formal-comparator-output-0.1.0.schema.json",
                ),
                "raw_trace_verifier": artifact_reference(
                    repo_root, RAW_TRACE_VERIFIER
                ),
                "submission_builder": artifact_reference(
                    repo_root, SUBMISSION_TOOL
                ),
            },
            "final_build_readiness": artifact_reference(
                repo_root, FORMAL_BUILD_READINESS
            ),
            "fixture_lock": artifact_reference(repo_root, FIXTURE_LOCK),
            "formal_readiness_verifier": artifact_reference(
                repo_root, FORMAL_READINESS_VERIFIER
            ),
            "frozen_artifact_set_digest": frozen_digest,
            "frozen_manifest_path": f"{RUN}/manifest.json",
            "freeze_commit": freeze_commit,
            "manifest_status_at_authorization": "frozen",
            "projection_audit": artifact_reference(repo_root, PROJECTION_AUDIT),
            "run_id": "continuous-001",
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
        },
    )


def prepare_synthetic_repository(source_root: Path, target_root: Path) -> None:
    copy_minimal_repository(source_root, target_root)
    for relative in (
        f"{RUN}/submissions/dispatch",
        f"{RUN}/submissions/self-test/reconstruction",
        f"{RUN}/submissions/self-test/prediction",
    ):
        repo_path(target_root, relative).mkdir(parents=True, exist_ok=True)

    actors = [make_actor(seat) for seat in SEATS]
    if len({actor["identifier"] for actor in actors}) != 4:
        raise SelfTestFailure("synthetic actors are not independent")
    if len({actor["session_id"] for actor in actors}) != 4:
        raise SelfTestFailure("synthetic sessions are not independent")
    for seat, actor in zip(SEATS, actors, strict=True):
        write_json(repo_path(target_root, actor_path(seat)), actor)

    write_synthetic_authorization_chain(target_root)


def run_self_test(source_root: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    real_dispatch = repo_path(source_root, f"{RUN}/submissions/dispatch")
    real_dispatch_before = snapshot_directory(real_dispatch)
    system_temp = Path(tempfile.gettempdir()).resolve()
    temporary_path: Path | None = None
    negative_results: dict[str, str] = {}

    with tempfile.TemporaryDirectory(
        prefix="game-primitives-blind-pipeline-", dir=system_temp
    ) as temporary:
        temporary_path = Path(temporary).resolve()
        if temporary_path == system_temp or not temporary_path.is_relative_to(
            system_temp
        ):
            raise SelfTestFailure(
                f"temporary repository is outside system temp: {temporary_path}"
            )
        synthetic_root = temporary_path / "synthetic-repository"
        synthetic_root.mkdir()
        prepare_synthetic_repository(source_root, synthetic_root)

        stage1_p01_arguments = [
            "materialize-stage1",
            "--repo-root",
            str(synthetic_root),
            "--template",
            f"{INPUTS}/stage1-dispatch-p01.template.json",
            "--actor",
            actor_path("p01"),
            "--authorization-receipt",
            AUTHORIZATION,
            "--output",
            stage1_receipt("p01"),
        ]
        run_cli(
            synthetic_root,
            DISPATCH_TOOL,
            stage1_p01_arguments,
            expected_failure_contains="synthetic authorization is confined",
            expect_success=False,
            synthetic_environment=False,
        )
        negative_results["synthetic_authorization_on_production_policy"] = (
            "failed_closed"
        )
        if repo_path(synthetic_root, stage1_receipt("p01")).exists():
            raise SelfTestFailure(
                "production-policy synthetic authorization control created a receipt"
            )

        authorization_path = repo_path(synthetic_root, AUTHORIZATION)
        authorization_before = authorization_path.read_bytes()
        malformed_authorization = read_json(authorization_path)
        malformed_authorization["authorization_basis"]["message_sha256"] = "0" * 64
        write_json(authorization_path, malformed_authorization)
        try:
            run_cli(
                synthetic_root,
                DISPATCH_TOOL,
                stage1_p01_arguments,
                expected_failure_contains="schema validation failed",
                expect_success=False,
            )
            negative_results["malformed_authorization"] = "failed_closed"
        finally:
            authorization_path.write_bytes(authorization_before)
        if repo_path(synthetic_root, stage1_receipt("p01")).exists():
            raise SelfTestFailure(
                "malformed authorization control created a dispatch receipt"
            )

        for seat in SEATS:
            materialize_stage1(synthetic_root, seat)
            package_reconstruction(synthetic_root, seat)

        negative_results.update(run_negative_controls(synthetic_root))
        materialize_cohort(synthetic_root)
        cohort = read_json(repo_path(synthetic_root, COHORT_LOCK))
        if (
            cohort.get("all_stage1_frozen") is not True
            or len(cohort.get("members", [])) != 4
        ):
            raise SelfTestFailure("synthetic cohort did not freeze four stage1 seats")

        for seat in SEATS:
            materialize_stage2(synthetic_root, seat)
            package_prediction(synthetic_root, seat)

        for seat in SEATS:
            reconstruction = read_json(
                repo_path(
                    synthetic_root,
                    artifact_path("reconstruction", "submission", seat),
                )
            )
            prediction = read_json(
                repo_path(
                    synthetic_root,
                    artifact_path("prediction", "submission", seat),
                )
            )
            actor = read_json(repo_path(synthetic_root, actor_path(seat)))
            if reconstruction["actor"] != actor or prediction["actor"] != actor:
                raise SelfTestFailure(f"{seat} actor continuity was not preserved")
            if prediction["prior_stage_submission_sha256"] != sha256(
                repo_path(
                    synthetic_root,
                    artifact_path("reconstruction", "submission", seat),
                )
            ):
                raise SelfTestFailure(f"{seat} prior-stage hash was not preserved")

    if temporary_path is None or temporary_path.exists():
        raise SelfTestFailure("temporary synthetic repository was not cleaned up")
    if snapshot_directory(real_dispatch) != real_dispatch_before:
        raise SelfTestFailure("self-test changed the real dispatch directory")

    return {
        "comparator_executed": False,
        "formal_input_executed": False,
        "negative_controls": negative_results,
        "real_dispatch_directory_unchanged": True,
        "stage1_receipts_materialized": 4,
        "stage1_submissions_verified": 4,
        "stage2_receipts_materialized": 4,
        "stage2_submissions_verified": 4,
        "status": "synthetic_blind_pipeline_self_test_passed",
        "synthetic_actor_sessions_verified_independent": True,
        "synthetic_repository_removed": True,
        "temporary_root_verified_under_system_temp": True,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description=(
            "Exercise the continuous-001 blind dispatch and submission pipeline "
            "inside a disposable synthetic repository."
        )
    )
    root.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[4],
        help="source repository root (defaults to the root containing this tool)",
    )
    return root


def main() -> int:
    arguments = parser().parse_args()
    try:
        result = run_self_test(arguments.repo_root)
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        KeyError,
        OSError,
        SelfTestFailure,
        subprocess.SubprocessError,
        TypeError,
        ValueError,
    ) as error:
        print(
            json.dumps(
                {
                    "comparator_executed": False,
                    "formal_input_executed": False,
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
