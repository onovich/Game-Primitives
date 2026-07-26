#!/usr/bin/env python3
"""Materialize and verify the post-prediction continuous-001 execution permit.

The tool reads only authorization, prediction, schema, and facility-contract
artifacts. It never reads a formal input, launches a fixture, or runs a
comparator. The permit is a deterministic projection of an already verified
formal human authorization and the frozen four-seat prediction preimage.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

RUN_ID = "continuous-001"
SEATS = ("p01", "p02", "p03", "p04")
CASES = ("CA-R1", "CA-R2", "CA-R3")
OPERATIONS = ("formal_fixture_execution", "formal_comparison")
URL_PREFIX = "https://github.com/onovich/Game-Primitives/blob/main/"
BASE = "research/calibration-tests/continuous-action-pilot"
RUN = f"{BASE}/runs/{RUN_ID}"
SCHEMA = f"{BASE}/schema"
TOOLS = f"{BASE}/tools"

AUTHORIZATION_PATH = (
    f"{RUN}/submissions/dispatch/human-gate-authorization.json"
)
PREIMAGE_PATH = f"{RUN}/submissions/prediction-set-preimage.tsv"
PERMIT_PATH = f"{RUN}/execution/formal-execution-permit.json"
PERMIT_SCHEMA_PATH = f"{SCHEMA}/formal-execution-permit-0.1.0.schema.json"
PERMIT_MATERIALIZER_PATH = f"{TOOLS}/materialize-execution-permit.py"
PERMIT_VERIFIER_PATH = f"{TOOLS}/verify-formal-execution-permit.py"
DISPATCH_MATERIALIZER_PATH = f"{TOOLS}/materialize-dispatch.py"
SUBMISSION_BUILDER_PATH = f"{TOOLS}/build-role-submission.py"
FORMAL_COMPARATOR_OUTPUT_SCHEMA_PATH = (
    f"{SCHEMA}/formal-comparator-output-0.1.0.schema.json"
)
RAW_TRACE_VERIFIER_PATH = f"{TOOLS}/verify-formal-raw-trace.py"
RAW_TRACE_SCHEMA_PATHS = {
    "CA-R1": f"{SCHEMA}/ca-r1-raw-trace-0.1.0.schema.json",
    "CA-R2": f"{SCHEMA}/ca-r2-raw-trace-0.1.0.schema.json",
    "CA-R3": f"{SCHEMA}/ca-r3-raw-trace-0.1.0.schema.json",
}
AUTHORIZATION_SCHEMA_PATH = (
    f"{SCHEMA}/formal-human-gate-authorization-0.1.0.schema.json"
)
ROLE_SCHEMA_PATH = f"{SCHEMA}/role-submission-0.1.2.schema.json"

PERMIT_SCHEMA_ID = URL_PREFIX + PERMIT_SCHEMA_PATH
ROLE_SCHEMA_ID = URL_PREFIX + ROLE_SCHEMA_PATH
EXPECTED_PREDICTIONS = {
    "p01": (
        "condition-v01",
        f"{RUN}/submissions/p01-stage2.json",
    ),
    "p02": (
        "condition-v01",
        f"{RUN}/submissions/p02-stage2.json",
    ),
    "p03": (
        "condition-v02",
        f"{RUN}/submissions/p03-stage2.json",
    ),
    "p04": (
        "condition-v02",
        f"{RUN}/submissions/p04-stage2.json",
    ),
}
EXPECTED_STAGE2_RECEIPTS = {
    seat: f"{RUN}/submissions/dispatch/stage2-{seat}.json" for seat in SEATS
}
EXECUTION_TARGET_PATHS = {
    "CA-R1": {
        "comparator": f"{RUN}/fixtures/r1/compare-footsies-r1-v0.1.0.ps1",
        "formal_input": f"{RUN}/fixtures/r1/footsies-r1-formal-input-v0.1.0.json",
        "formal_runner": f"{RUN}/fixtures/r1/run-footsies-r1-formal-v0.1.0.ps1",
        "raw_trace_schema": RAW_TRACE_SCHEMA_PATHS["CA-R1"],
        "support_artifacts": {
            "test_body_metadata": (
                f"{RUN}/fixtures/r1/footsies-r1-observation-v0.1.0.cs.meta"
            ),
            "variant_patch": (
                f"{RUN}/fixtures/r1/footsies-r1-whiff-cancel-v0.1.0.patch"
            ),
        },
        "test_body": f"{RUN}/fixtures/r1/footsies-r1-observation-v0.1.0.cs",
    },
    "CA-R2": {
        "comparator": f"{RUN}/fixtures/r2/compare-q3-formal-traces-v0.1.0.ps1",
        "formal_input": f"{RUN}/fixtures/r2/r2-formal-input-v0.1.0.json",
        "formal_runner": f"{RUN}/fixtures/r2/run-q3-formal-guarded-v0.1.0.ps1",
        "raw_trace_schema": RAW_TRACE_SCHEMA_PATHS["CA-R2"],
        "support_artifacts": {
            "build_runner": (
                f"{RUN}/fixtures/r2/build-q3-formal-fixture-v0.1.0.ps1"
            ),
            "compatibility_patch": (
                f"{RUN}/fixtures/r2/q3-msvc-x64-compatibility-v0.1.0.patch"
            ),
            "compatibility_source": (
                f"{RUN}/fixtures/r2/q3-formal-compatibility-v0.1.0.c"
            ),
            "harness_header": (
                f"{RUN}/fixtures/r2/q3-formal-fixture-v0.1.0.h"
            ),
            "observation_patch": f"{RUN}/fixtures/r2/q3-observation-v0.1.0.patch",
            "variant_patch": (
                f"{RUN}/fixtures/r2/q3-entry-latch-variant-v0.1.0.patch"
            ),
        },
        "test_body": f"{RUN}/fixtures/r2/q3-formal-harness-v0.1.0.c",
    },
    "CA-R3": {
        "comparator": f"{RUN}/fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1",
        "formal_input": f"{RUN}/fixtures/r3/formal-input-r3-v0.1.0.json",
        "formal_runner": f"{RUN}/fixtures/r3/run-osu-r3-formal-v0.1.0.ps1",
        "raw_trace_schema": RAW_TRACE_SCHEMA_PATHS["CA-R3"],
        "support_artifacts": {
            "build_list_evidence": (
                f"{RUN}/fixtures/r3/r3-build-list-evidence-v0.1.0.json"
            ),
            "build_runner": (
                f"{RUN}/fixtures/r3/run-osu-r3-build-list-v0.1.0.ps1"
            ),
            "dependency_lock_set": (
                f"{RUN}/fixtures/r3/dependency-lock-set-v0.1.0.json"
            ),
            "fixture_spec": f"{RUN}/fixtures/r3/r3-fixture-spec-v0.1.0.json",
        },
        "test_body": f"{RUN}/fixtures/r3/TestSceneGamePrimitivesR3.cs",
    },
}

SELF_TEST_ENV = "GAME_PRIMITIVES_INTERNAL_EXECUTION_PERMIT_SELF_TEST"
SELF_TEST_TOKEN = "continuous-001-disposable-execution-permit-self-test"
SELF_TEST_MARKER = ".synthetic-execution-permit-self-test"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PermitError(RuntimeError):
    """A fail-closed execution-permit materialization or verification error."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def repo_path(repo_root: Path, value: str | Path, *, must_exist: bool = True) -> Path:
    candidate = (repo_root / value).resolve()
    if not candidate.is_relative_to(repo_root):
        raise PermitError(f"path escapes repository root: {value}")
    if must_exist and not candidate.is_file():
        raise PermitError(f"required file does not exist: {value}")
    return candidate


def relative_path(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise PermitError(f"UTF-8 BOM is forbidden: {path}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PermitError(f"invalid UTF-8 JSON: {path}") from error
    if not isinstance(value, dict):
        raise PermitError(f"expected a JSON object: {path}")
    return value, raw


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
        raise PermitError(
            f"hash mismatch for {reference['path']}: "
            f"expected {reference['sha256']}, got {actual}"
        )
    return path


def load_dispatch_module(repo_root: Path) -> Any:
    path = repo_path(repo_root, DISPATCH_MATERIALIZER_PATH)
    spec = importlib.util.spec_from_file_location(
        "continuous_action_dispatch_materializer",
        path,
    )
    if spec is None or spec.loader is None:
        raise PermitError("cannot load the bound dispatch authorization verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_submission_builder(repo_root: Path) -> Any:
    path = repo_path(repo_root, SUBMISSION_BUILDER_PATH)
    spec = importlib.util.spec_from_file_location(
        "continuous_action_submission_builder",
        path,
    )
    if spec is None or spec.loader is None:
        raise PermitError("cannot load the bound submission-chain verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_no_formal_outputs(repo_root: Path) -> None:
    """Require an observable clean pre-execution repository state."""
    execution_root = repo_root / RUN / "execution"
    allowed_execution_files = {
        "execution-plan.json",
        "formal-execution-permit.json",
        "plan.json",
    }
    if execution_root.is_dir():
        for candidate in execution_root.rglob("*"):
            if not candidate.is_file():
                continue
            relative = candidate.relative_to(execution_root).as_posix()
            if "/" not in relative and relative in allowed_execution_files:
                continue
            raise PermitError(
                "formal execution output already exists before permit use: "
                f"{RUN}/execution/{relative}"
            )
    for directory in ("reports", "reveal"):
        root = repo_root / RUN / directory
        if root.is_dir():
            for candidate in root.rglob("*"):
                if candidate.is_file():
                    relative = candidate.relative_to(repo_root).as_posix()
                    raise PermitError(
                        "post-execution artifact already exists before permit use: "
                        f"{relative}"
                    )


def isolated_self_test_enabled(repo_root: Path) -> bool:
    system_temp = Path(tempfile.gettempdir()).resolve()
    marker = repo_root / SELF_TEST_MARKER
    return (
        os.environ.get(SELF_TEST_ENV) == SELF_TEST_TOKEN
        and repo_root.name == "synthetic-repository"
        and repo_root != system_temp
        and repo_root.is_relative_to(system_temp)
        and not (repo_root / ".git").exists()
        and marker.is_file()
        and marker.read_text(encoding="utf-8") == SELF_TEST_TOKEN + "\n"
    )


def expected_contract_references(repo_root: Path) -> dict[str, dict[str, str]]:
    return {
        "ca_r1_raw_trace_schema": artifact_reference(
            repo_root, RAW_TRACE_SCHEMA_PATHS["CA-R1"]
        ),
        "ca_r2_raw_trace_schema": artifact_reference(
            repo_root, RAW_TRACE_SCHEMA_PATHS["CA-R2"]
        ),
        "ca_r3_raw_trace_schema": artifact_reference(
            repo_root, RAW_TRACE_SCHEMA_PATHS["CA-R3"]
        ),
        "execution_permit_materializer": artifact_reference(
            repo_root, PERMIT_MATERIALIZER_PATH
        ),
        "execution_permit_schema": artifact_reference(
            repo_root, PERMIT_SCHEMA_PATH
        ),
        "execution_permit_verifier": artifact_reference(
            repo_root, PERMIT_VERIFIER_PATH
        ),
        "formal_comparator_output_schema": artifact_reference(
            repo_root, FORMAL_COMPARATOR_OUTPUT_SCHEMA_PATH
        ),
        "raw_trace_verifier": artifact_reference(
            repo_root, RAW_TRACE_VERIFIER_PATH
        ),
        "submission_builder": artifact_reference(
            repo_root, SUBMISSION_BUILDER_PATH
        ),
    }


def verify_formal_authorization(repo_root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    reference = artifact_reference(repo_root, AUTHORIZATION_PATH)
    path = repo_path(repo_root, AUTHORIZATION_PATH)
    authorization, raw = read_json(path)
    if raw != canonical_bytes(authorization):
        raise PermitError("human authorization receipt is not canonical JSON")

    dispatch = load_dispatch_module(repo_root)
    if isolated_self_test_enabled(repo_root):
        try:
            dispatch.validate_against_repo_schema_registry(
                repo_root,
                authorization,
                AUTHORIZATION_SCHEMA_PATH,
            )
        except Exception as error:
            raise PermitError(
                f"synthetic formal authorization schema check failed: {error}"
            ) from error
        for item in authorization.get("contract_artifacts", {}).values():
            verify_reference(repo_root, item)
    else:
        try:
            authorization = dispatch.verify_authorization_receipt(
                repo_root,
                reference,
            )
        except Exception as error:
            raise PermitError(
                f"formal human authorization verification failed: {error}"
            ) from error

    if authorization.get("authorization_context") != "formal_run":
        raise PermitError("synthetic authorization cannot authorize formal execution")
    if authorization.get("authorization_state") != "authorized":
        raise PermitError("human authorization is not in the authorized state")
    scopes = authorization.get("authorization_scopes", {})
    if (
        scopes.get("blind_dispatch_authorized") is not True
        or scopes.get("formal_execution_after_prediction_freeze_authorized")
        is not True
        or scopes.get("synthetic_receipt_materialization_authorized") is not False
    ):
        raise PermitError("human authorization scopes do not permit formal execution")
    state = authorization.get("state_at_authorization", {})
    if (
        state.get("formal_input_executed") is not False
        or state.get("formal_result_produced") is not False
    ):
        raise PermitError("human authorization does not record a clean pre-run state")

    expected_contract = expected_contract_references(repo_root)
    contract = authorization.get("contract_artifacts", {})
    for name, expected in expected_contract.items():
        if contract.get(name) != expected:
            raise PermitError(
                f"human authorization does not bind the current {name}"
            )
    return authorization, reference


def verify_synthetic_prediction_lineage(
    repo_root: Path,
    seat: str,
    prediction: dict[str, Any],
) -> None:
    """Exercise equivalent byte bindings inside the isolated self-test only."""
    receipt_path = repo_path(repo_root, EXPECTED_STAGE2_RECEIPTS[seat])
    receipt, receipt_raw = read_json(receipt_path)
    if receipt_raw != canonical_bytes(receipt):
        raise PermitError(f"synthetic stage2 receipt is not canonical for {seat}")
    condition = EXPECTED_PREDICTIONS[seat][0]
    if (
        receipt.get("seat_id") != seat
        or receipt.get("condition_id") != condition
        or receipt.get("actor") != prediction.get("actor")
    ):
        raise PermitError(f"synthetic stage2 receipt binding differs for {seat}")
    authorization_reference = receipt.get("authorization_receipt")
    if not isinstance(authorization_reference, dict):
        raise PermitError(f"synthetic stage2 receipt lacks authorization for {seat}")
    verify_reference(repo_root, authorization_reference)

    prior_reference = receipt.get("stage1_submission")
    prior_dispatch_reference = receipt.get("stage1_dispatch_receipt")
    if not isinstance(prior_reference, dict) or not isinstance(
        prior_dispatch_reference, dict
    ):
        raise PermitError(f"synthetic stage2 receipt lacks prior lineage for {seat}")
    prior_path = verify_reference(repo_root, prior_reference)
    verify_reference(repo_root, prior_dispatch_reference)
    prior, prior_raw = read_json(prior_path)
    if prior_raw != canonical_bytes(prior):
        raise PermitError(f"synthetic prior submission is not canonical for {seat}")
    if (
        prediction.get("prior_stage_submission_sha256")
        != sha256_bytes(prior_raw)
        or prior.get("artifact_type") != "reconstruction_submission"
        or prior.get("condition_id") != condition
        or prior.get("actor") != prediction.get("actor")
    ):
        raise PermitError(f"synthetic prior-stage continuity differs for {seat}")

    packaging = prediction["packaging"]
    envelope_path = verify_reference(
        repo_root,
        {
            "path": packaging["envelope_path"],
            "sha256": packaging["envelope_sha256"],
        },
    )
    envelope, envelope_raw = read_json(envelope_path)
    if envelope_raw != canonical_bytes(envelope):
        raise PermitError(f"synthetic machine envelope is not canonical for {seat}")
    if (
        envelope.get("actor") != prediction.get("actor")
        or envelope.get("condition_id") != condition
        or envelope.get("submission_id") != prediction.get("submission_id")
        or envelope.get("prior_stage_submission_sha256")
        != prediction.get("prior_stage_submission_sha256")
        or envelope.get("task_id") != prediction.get("task_id")
    ):
        raise PermitError(f"synthetic machine envelope continuity differs for {seat}")

    payload_reference = prediction["raw_payload"]
    payload_path = verify_reference(
        repo_root,
        {
            "path": payload_reference["path"],
            "sha256": payload_reference["sha256"],
        },
    )
    payload, payload_raw = read_json(payload_path)
    if payload_raw != canonical_bytes(payload):
        raise PermitError(f"synthetic raw prediction payload is not canonical for {seat}")
    if (
        payload.get("pollution") != prediction.get("pollution")
        or payload.get("prediction_answers") != prediction.get("prediction_answers")
    ):
        raise PermitError(f"synthetic deterministic payload copy differs for {seat}")


def verify_formal_prediction_lineage(
    repo_root: Path,
    seat: str,
    prediction_path: Path,
    prediction: dict[str, Any],
) -> None:
    if isolated_self_test_enabled(repo_root):
        verify_synthetic_prediction_lineage(repo_root, seat, prediction)
        return

    receipt_path = repo_path(repo_root, EXPECTED_STAGE2_RECEIPTS[seat])
    receipt, receipt_raw = read_json(receipt_path)
    if receipt_raw != canonical_bytes(receipt):
        raise PermitError(f"stage2 dispatch receipt is not canonical for {seat}")
    if (
        receipt.get("seat_id") != seat
        or receipt.get("actor_binding", {}).get("actor_identifier")
        != prediction.get("actor", {}).get("identifier")
        or receipt.get("actor_binding", {}).get("session_id")
        != prediction.get("actor", {}).get("session_id")
    ):
        raise PermitError(f"prediction does not belong to stage2 seat {seat}")
    prior_receipt = receipt.get("stage1_dispatch_receipt")
    prior_submission = receipt.get("stage1_submission")
    if not isinstance(prior_receipt, dict) or not isinstance(
        prior_submission, dict
    ):
        raise PermitError(f"stage2 dispatch lineage is incomplete for {seat}")
    verify_reference(repo_root, prior_receipt)
    verify_reference(repo_root, prior_submission)

    condition = EXPECTED_PREDICTIONS[seat][0]
    prior_task = (
        f"{RUN}/inputs/stage1-condition-v01.task.json"
        if condition == "condition-v01"
        else f"{RUN}/inputs/stage1-condition-v02.task.json"
    )
    builder = load_submission_builder(repo_root)
    arguments = argparse.Namespace(
        actor=None,
        condition_id=None,
        dispatch_receipt=Path(EXPECTED_STAGE2_RECEIPTS[seat]),
        envelope=Path(prediction["packaging"]["envelope_path"]),
        payload=Path(prediction["raw_payload"]["path"]),
        prior_stage_dispatch_receipt=Path(prior_receipt["path"]),
        prior_stage_submission=Path(prior_submission["path"]),
        prior_stage_task=Path(prior_task),
        repo_root=repo_root,
        submission=Path(relative_path(repo_root, prediction_path)),
        task=Path(f"{RUN}/inputs/stage2-prediction.task.json"),
    )
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured_stdout), contextlib.redirect_stderr(
            captured_stderr
        ):
            status = builder.command_verify(arguments)
    except Exception as error:
        raise PermitError(
            f"full submission-chain verification failed for {seat}: {error}"
        ) from error
    if status != 0:
        raise PermitError(
            f"full submission-chain verification returned {status} for {seat}"
        )
    try:
        result = json.loads(captured_stdout.getvalue())
    except json.JSONDecodeError as error:
        raise PermitError(
            f"submission-chain verifier returned invalid output for {seat}"
        ) from error
    if (
        result.get("status") != "verified"
        or result.get("submission_sha256")
        != sha256_bytes(prediction_path.read_bytes())
    ):
        raise PermitError(
            f"submission-chain verifier did not bind the final prediction for {seat}"
        )


def validate_prediction_documents(
    repo_root: Path,
    dispatch: Any,
    listed_paths: list[str],
    listed_hashes: list[str],
) -> list[dict[str, Any]]:
    seat_predictions: list[dict[str, Any]] = []
    actor_ids: set[str] = set()
    session_ids: set[str] = set()
    submission_ids: set[str] = set()
    for seat, listed_path, listed_hash in zip(
        SEATS,
        listed_paths,
        listed_hashes,
        strict=True,
    ):
        prediction_path = repo_path(repo_root, listed_path)
        document, prediction_raw = read_json(prediction_path)
        if prediction_raw != canonical_bytes(document):
            raise PermitError(f"prediction submission is not canonical JSON: {listed_path}")
        actual_hash = sha256_bytes(prediction_raw)
        if actual_hash != listed_hash:
            raise PermitError(
                f"prediction preimage hash mismatch for {listed_path}: "
                f"expected {listed_hash}, got {actual_hash}"
            )
        try:
            dispatch.validate_against_repo_schema_registry(
                repo_root,
                document,
                ROLE_SCHEMA_PATH,
            )
        except Exception as error:
            raise PermitError(
                f"prediction submission schema check failed for {seat}: {error}"
            ) from error

        condition, expected_path = EXPECTED_PREDICTIONS[seat]
        if listed_path != expected_path:
            raise PermitError(f"prediction path does not match seat {seat}")
        if (
            document.get("$schema") != ROLE_SCHEMA_ID
            or document.get("artifact_type") != "prediction_submission"
            or document.get("artifact_version") != "0.1.2"
            or document.get("run_id") != RUN_ID
            or document.get("stage") != "prediction"
            or document.get("first_submission") is not True
            or document.get("condition_id") != condition
        ):
            raise PermitError(f"prediction submission identity mismatch for {seat}")
        answer_cases = [
            answer.get("case_id") for answer in document.get("prediction_answers", [])
        ]
        if answer_cases != list(CASES) or len(set(answer_cases)) != len(CASES):
            raise PermitError(
                f"prediction submission {seat} must cover CA-R1 through CA-R3 "
                "exactly once in canonical order"
            )
        verify_formal_prediction_lineage(
            repo_root,
            seat,
            prediction_path,
            document,
        )
        actor = document.get("actor", {})
        actor_id = actor.get("identifier")
        session_id = actor.get("session_id")
        submission_id = document.get("submission_id")
        if not all(isinstance(value, str) and value for value in (
            actor_id,
            session_id,
            submission_id,
        )):
            raise PermitError(f"prediction submission identity is incomplete for {seat}")
        if actor_id in actor_ids or session_id in session_ids:
            raise PermitError("prediction preimage contains a duplicate actor or session")
        if submission_id in submission_ids:
            raise PermitError("prediction preimage contains a duplicate submission")
        actor_ids.add(actor_id)
        session_ids.add(session_id)
        submission_ids.add(submission_id)
        seat_predictions.append(
            {
                "condition_id": condition,
                "seat_id": seat,
                "submission": {
                    "path": listed_path,
                    "sha256": actual_hash,
                },
            }
        )
    return seat_predictions


def canonical_preimage_bytes(repo_root: Path) -> bytes:
    return "".join(
        f"{EXPECTED_PREDICTIONS[seat][1]}\t"
        f"{sha256_bytes(repo_path(repo_root, EXPECTED_PREDICTIONS[seat][1]).read_bytes())}\n"
        for seat in SEATS
    ).encode("utf-8")


def parse_prediction_preimage(
    repo_root: Path,
    dispatch: Any,
) -> tuple[list[dict[str, Any]], dict[str, str], str]:
    path = repo_path(repo_root, PREIMAGE_PATH)
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise PermitError("prediction preimage must not contain a UTF-8 BOM")
    if b"\r" in raw or not raw.endswith(b"\n"):
        raise PermitError("prediction preimage must use LF and end with one LF")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PermitError("prediction preimage is not UTF-8") from error
    lines = text[:-1].split("\n")
    if len(lines) != len(SEATS):
        raise PermitError("prediction preimage must contain exactly four seats")

    expected_paths = [EXPECTED_PREDICTIONS[seat][1] for seat in SEATS]
    seen_paths: list[str] = []
    listed_hashes: list[str] = []
    for line in lines:
        fields = line.split("\t")
        if len(fields) != 2:
            raise PermitError(
                "each prediction preimage line must be <path><TAB><sha256>"
            )
        listed_path, listed_hash = fields
        if not SHA256_RE.fullmatch(listed_hash) or listed_hash == "0" * 64:
            raise PermitError("prediction preimage contains an invalid SHA-256")
        seen_paths.append(listed_path)
        listed_hashes.append(listed_hash)
    if len(set(seen_paths)) != len(SEATS):
        raise PermitError("prediction preimage contains a duplicate seat path")
    if seen_paths != expected_paths:
        raise PermitError(
            "prediction preimage paths must be the fixed p01-to-p04 canonical order"
        )
    if raw != canonical_preimage_bytes(repo_root):
        raise PermitError(
            "prediction preimage bytes differ from the deterministic four-seat projection"
        )

    seat_predictions = validate_prediction_documents(
        repo_root,
        dispatch,
        seen_paths,
        listed_hashes,
    )

    preimage_reference = {
        "path": PREIMAGE_PATH,
        "sha256": sha256_bytes(raw),
    }
    return seat_predictions, preimage_reference, preimage_reference["sha256"]


def expected_execution_targets(repo_root: Path) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for case_id in CASES:
        paths = EXECUTION_TARGET_PATHS[case_id]
        targets.append(
            {
                "case_id": case_id,
                "comparator": artifact_reference(
                    repo_root, paths["comparator"]
                ),
                "formal_input": artifact_reference(
                    repo_root, paths["formal_input"]
                ),
                "formal_runner": artifact_reference(
                    repo_root, paths["formal_runner"]
                ),
                "raw_trace_schema": artifact_reference(
                    repo_root, paths["raw_trace_schema"]
                ),
                "support_artifacts": {
                    name: artifact_reference(repo_root, path)
                    for name, path in paths["support_artifacts"].items()
                },
                "test_body": artifact_reference(
                    repo_root, paths["test_body"]
                ),
            }
        )
    return targets


def verify_execution_target_freeze(
    repo_root: Path,
    authorization: dict[str, Any],
    dispatch: Any,
    targets: list[dict[str, Any]],
) -> None:
    manifest_path = repo_path(repo_root, authorization["frozen_manifest_path"])
    manifest, manifest_raw = read_json(manifest_path)
    if manifest_raw != canonical_bytes(manifest):
        raise PermitError("human authorization manifest is not canonical JSON")
    if manifest.get("run_id") != RUN_ID or manifest.get("status") not in (
        "frozen",
        "collecting",
        "reported",
        "revealed",
    ):
        raise PermitError("execution targets are not bound to a frozen run manifest")

    expected_contract = expected_contract_references(repo_root)
    seen_paths: set[str] = set()
    for target in targets:
        case_id = target["case_id"]
        raw_contract_name = {
            "CA-R1": "ca_r1_raw_trace_schema",
            "CA-R2": "ca_r2_raw_trace_schema",
            "CA-R3": "ca_r3_raw_trace_schema",
        }[case_id]
        if (
            target["raw_trace_schema"] != expected_contract[raw_contract_name]
            or authorization["contract_artifacts"].get(raw_contract_name)
            != target["raw_trace_schema"]
        ):
            raise PermitError(
                f"{case_id} raw trace schema is outside the bound contract closure"
            )
        manifest_references = [
            target["comparator"],
            target["formal_input"],
            target["formal_runner"],
            target["test_body"],
            *target["support_artifacts"].values(),
        ]
        for reference in manifest_references:
            if reference["path"] in seen_paths:
                raise PermitError(
                    f"duplicate execution-surface path: {reference['path']}"
                )
            seen_paths.add(reference["path"])
            try:
                dispatch.manifest_entry_for_reference(manifest, reference)
            except Exception as error:
                raise PermitError(
                    f"{case_id} execution target is not frozen: {error}"
                ) from error


def build_expected_permit(
    repo_root: Path,
) -> tuple[dict[str, Any], str]:
    authorization, authorization_reference = verify_formal_authorization(repo_root)
    dispatch = load_dispatch_module(repo_root)
    execution_targets = expected_execution_targets(repo_root)
    verify_execution_target_freeze(
        repo_root,
        authorization,
        dispatch,
        execution_targets,
    )
    seat_predictions, preimage_reference, prediction_set_digest = (
        parse_prediction_preimage(repo_root, dispatch)
    )
    permit = {
        "$schema": PERMIT_SCHEMA_ID,
        "artifact_type": "formal_execution_permit",
        "artifact_version": "0.1.0",
        "authorization_lineage": {
            "freeze_commit": authorization["freeze_commit"],
            "frozen_artifact_set_digest": authorization[
                "frozen_artifact_set_digest"
            ],
            "frozen_manifest_path": authorization["frozen_manifest_path"],
        },
        "contract_artifacts": expected_contract_references(repo_root),
        "execution_targets": execution_targets,
        "human_gate_authorization": authorization_reference,
        "permit_id": "execution-permit.continuous-001",
        "permit_state": "ready_for_formal_execution",
        "prediction_set": {
            "prediction_set_digest": prediction_set_digest,
            "preimage": preimage_reference,
            "seat_predictions": seat_predictions,
        },
        "run_id": RUN_ID,
        "scope": {
            "case_ids": list(CASES),
            "operations": list(OPERATIONS),
        },
        "state_at_materialization": {
            "formal_input_executed": False,
            "formal_result_produced": False,
            "predictions_frozen": True,
        },
    }
    try:
        dispatch.validate_against_repo_schema_registry(
            repo_root,
            permit,
            PERMIT_SCHEMA_PATH,
        )
    except Exception as error:
        raise PermitError(f"generated execution permit is schema-invalid: {error}") from error
    return permit, prediction_set_digest


def assert_fixed_path(
    repo_root: Path,
    supplied: Path,
    expected_relative: str,
    label: str,
) -> Path:
    actual = repo_path(repo_root, supplied, must_exist=False)
    expected = repo_path(repo_root, expected_relative, must_exist=False)
    if actual != expected:
        raise PermitError(f"{label} must use the fixed path {expected_relative}")
    return actual


def materialize_preimage(repo_root: Path, preimage_path: Path) -> dict[str, Any]:
    output = assert_fixed_path(
        repo_root,
        preimage_path,
        PREIMAGE_PATH,
        "prediction preimage output",
    )
    if output.exists():
        raise PermitError(
            f"refusing to overwrite existing prediction preimage: {PREIMAGE_PATH}"
        )
    if not output.parent.is_dir():
        raise PermitError(
            f"prediction preimage parent must already exist: {output.parent}"
        )
    assert_no_formal_outputs(repo_root)
    verify_formal_authorization(repo_root)
    dispatch = load_dispatch_module(repo_root)
    raw = canonical_preimage_bytes(repo_root)
    paths = [EXPECTED_PREDICTIONS[seat][1] for seat in SEATS]
    hashes = [
        sha256_bytes(repo_path(repo_root, path).read_bytes()) for path in paths
    ]
    validate_prediction_documents(repo_root, dispatch, paths, hashes)
    output.write_bytes(raw)
    return {
        "formal_input_executed": False,
        "prediction_preimage_path": PREIMAGE_PATH,
        "prediction_set_digest": sha256_bytes(raw),
        "run_id": RUN_ID,
        "status": "prediction_set_preimage_materialized",
    }


def materialize_permit(repo_root: Path, permit_path: Path) -> dict[str, Any]:
    output = assert_fixed_path(repo_root, permit_path, PERMIT_PATH, "permit output")
    if output.exists():
        raise PermitError(f"refusing to overwrite existing permit: {PERMIT_PATH}")
    if not output.parent.is_dir():
        raise PermitError(
            f"permit output parent must already exist: {output.parent}"
        )
    assert_no_formal_outputs(repo_root)
    permit, prediction_set_digest = build_expected_permit(repo_root)
    raw = canonical_bytes(permit)
    output.write_bytes(raw)
    return {
        "execution_permit_sha256": sha256_bytes(raw),
        "permit_path": PERMIT_PATH,
        "prediction_set_digest": prediction_set_digest,
        "run_id": RUN_ID,
        "status": "formal_execution_permit_materialized",
    }


def verify_permit(
    repo_root: Path,
    permit_path: Path,
    case_id: str,
) -> dict[str, Any]:
    if case_id not in CASES:
        raise PermitError("case-id must be one of CA-R1, CA-R2, or CA-R3")
    path = assert_fixed_path(repo_root, permit_path, PERMIT_PATH, "permit")
    if not path.is_file():
        raise PermitError(f"required file does not exist: {PERMIT_PATH}")
    permit, raw = read_json(path)
    if raw != canonical_bytes(permit):
        raise PermitError("execution permit is not canonical JSON")
    dispatch = load_dispatch_module(repo_root)
    try:
        dispatch.validate_against_repo_schema_registry(
            repo_root,
            permit,
            PERMIT_SCHEMA_PATH,
        )
    except Exception as error:
        raise PermitError(f"execution permit schema check failed: {error}") from error
    expected, prediction_set_digest = build_expected_permit(repo_root)
    expected_raw = canonical_bytes(expected)
    if raw != expected_raw:
        raise PermitError(
            "execution permit does not equal the deterministic authorization "
            "and prediction projection"
        )
    if case_id not in permit["scope"]["case_ids"]:
        raise PermitError(f"execution permit does not authorize {case_id}")
    execution_target = next(
        target
        for target in permit["execution_targets"]
        if target["case_id"] == case_id
    )
    return {
        "case_id": case_id,
        "execution_permit_sha256": sha256_bytes(raw),
        "execution_target": execution_target,
        "permit_path": PERMIT_PATH,
        "prediction_set_digest": prediction_set_digest,
        "run_id": RUN_ID,
        "status": "formal_execution_permit_verified",
    }


def write_canonical(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def synthetic_prediction(seat: str) -> dict[str, Any]:
    condition = EXPECTED_PREDICTIONS[seat][0]
    answer_template = {
        "assumptions": [],
        "case_id": "CA-R1",
        "compatible_alternatives": [],
        "confidence_percent": 80,
        "expectations": [
            {
                "configuration_id": "config.baseline",
                "expectation_kind": "exact",
                "observation_id": "obs.synthetic",
                "tolerance_rule_id": None,
                "value": {
                    "serialized_value": "1",
                    "unit": "count",
                    "value_type": "integer",
                },
            },
            {
                "configuration_id": "config.variant",
                "expectation_kind": "exact",
                "observation_id": "obs.synthetic",
                "tolerance_rule_id": None,
                "value": {
                    "serialized_value": "2",
                    "unit": "count",
                    "value_type": "integer",
                },
            },
        ],
        "prediction_status": "determinate",
        "reasoning": "Synthetic prediction used only by the disposable permit self-test.",
        "supporting_record_ids": [],
    }
    predictions = []
    for case_id in CASES:
        answer = copy.deepcopy(answer_template)
        answer["case_id"] = case_id
        predictions.append(answer)
    nonzero = sha256_bytes(f"synthetic-{seat}".encode("utf-8"))
    return {
        "$schema": ROLE_SCHEMA_ID,
        "actor": {
            "identifier": f"synthetic.actor.{seat}",
            "model": "synthetic-self-test",
            "model_version": "0",
            "reasoning_effort": "high",
            "role": "blind_reconstructor_predictor",
            "session_id": f"synthetic.session.{seat}",
        },
        "artifact_type": "prediction_submission",
        "artifact_version": "0.1.2",
        "audit_checks": [],
        "audit_decision": None,
        "condition_id": condition,
        "findings": [],
        "first_submission": True,
        "input_artifacts": [
            {
                "artifact_id": "variant-envelope",
                "sha256": nonzero,
            },
            {
                "artifact_id": f"submission.reconstruction.{seat}",
                "sha256": sha256_bytes(f"prior-{seat}".encode("utf-8")),
            },
        ],
        "packaging": {
            "copied_fields": [
                "pollution",
                "prediction_answers",
            ],
            "envelope_path": f"synthetic/envelopes/{seat}.json",
            "envelope_sha256": sha256_bytes(f"envelope-{seat}".encode("utf-8")),
            "mode": "deterministic_field_copy",
            "semantic_copy_verified": True,
            "tool_path": f"{TOOLS}/build-role-submission.py",
            "tool_sha256": sha256_bytes(b"synthetic submission builder"),
        },
        "pollution": {
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
        },
        "prediction_answers": predictions,
        "prior_stage_submission_sha256": sha256_bytes(
            f"prior-{seat}".encode("utf-8")
        ),
        "raw_payload": {
            "artifact_id": f"raw.prediction.{seat}",
            "path": f"synthetic/raw/{seat}.json",
            "schema_path": f"{SCHEMA}/blind-response-interface-0.1.0.schema.json",
            "schema_sha256": sha256_bytes(b"synthetic raw schema"),
            "sha256": sha256_bytes(f"raw-{seat}".encode("utf-8")),
        },
        "reconstruction_answers": [],
        "run_id": RUN_ID,
        "stage": "prediction",
        "submission_id": f"submission.prediction.{seat}",
        "submitted_at": "2026-07-27T08:00:00Z",
        "task_id": "task.predict.neutral",
    }


def synthetic_authorization(repo_root: Path) -> dict[str, Any]:
    dummy_paths = {
        "final_build_readiness": f"{RUN}/fixtures/formal-build-readiness-v0.1.0.json",
        "fixture_lock": f"{RUN}/fixtures/fixture-lock.json",
        "projection_audit": f"{RUN}/source/projection-audit-v0.1.0.json",
        "formal_readiness_verifier": f"{TOOLS}/verify-formal-readiness.py",
    }
    for name, relative in dummy_paths.items():
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((f"synthetic {name}; no formal input\n").encode("utf-8"))
    targets = expected_execution_targets(repo_root)
    manifest_artifacts = []
    for target in targets:
        references = [
            target["comparator"],
            target["formal_input"],
            target["formal_runner"],
            target["test_body"],
            *target["support_artifacts"].values(),
        ]
        for reference in references:
            manifest_artifacts.append(
                {
                    "included_in_frozen_set": True,
                    "path": reference["path"].removeprefix(RUN + "/"),
                    "sha256": reference["sha256"],
                }
            )
    write_canonical(
        repo_root / f"{RUN}/manifest.json",
        {
            "artifact_type": "formal_run_manifest",
            "artifacts": manifest_artifacts,
            "freeze_commit": "1" * 40,
            "frozen_artifact_set_digest": sha256_bytes(
                b"synthetic frozen execution surface"
            ),
            "run_id": RUN_ID,
            "status": "frozen",
        },
    )

    commitment = {
        "algorithm": "SHA-256",
        "combination": "secret_nonce_bytes || exact_truth_bundle_bytes",
        "commitment": sha256_bytes(b"synthetic truth commitment"),
        "created_at": "2026-07-27T07:58:00Z",
        "nonce_length_bytes": 32,
        "truth_bundle_bytes": 1,
        "truth_bundle_name": "sealed-truth.json",
    }
    dispatch_contract = {
        "authorization_schema": artifact_reference(
            repo_root, AUTHORIZATION_SCHEMA_PATH
        ),
        "dispatch_materializer": artifact_reference(
            repo_root, DISPATCH_MATERIALIZER_PATH
        ),
    }
    dispatch_contract.update(expected_contract_references(repo_root))
    return {
        "$schema": URL_PREFIX + AUTHORIZATION_SCHEMA_PATH,
        "artifact_type": "formal_human_gate_authorization",
        "artifact_version": "0.1.0",
        "authorization_basis": {
            "decision": "authorized",
            "message_sha256": sha256_bytes(b"synthetic explicit gate message"),
            "source_kind": "explicit_user_message",
            "source_locator": "synthetic-self-test://formal-branch-only",
        },
        "authorization_context": "formal_run",
        "authorization_id": "authorization.continuous-001.human-gate",
        "authorization_phrase": "RUN_CONTINUOUS_001_FORMAL_AFTER_HUMAN_GATE",
        "authorization_scopes": {
            "blind_dispatch_authorized": True,
            "formal_execution_after_prediction_freeze_authorized": True,
            "synthetic_receipt_materialization_authorized": False,
        },
        "authorization_state": "authorized",
        "authorized_at": "2026-07-27T08:00:00Z",
        "authorized_by": {
            "identifier": "synthetic-self-test-author",
            "role": "author",
        },
        "contract_artifacts": dispatch_contract,
        "final_build_readiness": artifact_reference(
            repo_root, dummy_paths["final_build_readiness"]
        ),
        "fixture_lock": artifact_reference(
            repo_root, dummy_paths["fixture_lock"]
        ),
        "formal_readiness_verifier": artifact_reference(
            repo_root, dummy_paths["formal_readiness_verifier"]
        ),
        "frozen_artifact_set_digest": sha256_bytes(
            b"synthetic frozen execution surface"
        ),
        "frozen_manifest_path": f"{RUN}/manifest.json",
        "freeze_commit": "1" * 40,
        "manifest_status_at_authorization": "frozen",
        "projection_audit": artifact_reference(
            repo_root, dummy_paths["projection_audit"]
        ),
        "run_id": RUN_ID,
        "state_at_authorization": {
            "blind_dispatch_performed": False,
            "formal_input_executed": False,
            "formal_result_produced": False,
        },
        "truth_commitment": commitment,
        "verification": {
            "require_frozen": True,
            "status": "passed",
            "verified_at": "2026-07-27T07:59:00Z",
        },
    }


def write_synthetic_execution_surface(repo_root: Path) -> None:
    for case_id, paths in EXECUTION_TARGET_PATHS.items():
        named_paths = {
            "comparator": paths["comparator"],
            "formal_input": paths["formal_input"],
            "formal_runner": paths["formal_runner"],
            "test_body": paths["test_body"],
            **paths["support_artifacts"],
        }
        for name, relative in named_paths.items():
            path = repo_root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(
                (
                    f"synthetic isolated execution-surface placeholder "
                    f"{case_id} {name}; never executable\n"
                ).encode("utf-8")
            )


def prepare_synthetic_repo(
    source_root: Path,
    target_root: Path,
    *,
    include_preimage: bool = True,
) -> None:
    if target_root.exists():
        raise PermitError(f"synthetic target already exists: {target_root}")
    target_root.mkdir(parents=True)
    marker = target_root / SELF_TEST_MARKER
    marker.write_text(SELF_TEST_TOKEN + "\n", encoding="utf-8", newline="\n")

    schema_source = source_root / SCHEMA
    schema_target = target_root / SCHEMA
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(schema_source, schema_target)
    for relative in (
        DISPATCH_MATERIALIZER_PATH,
        PERMIT_MATERIALIZER_PATH,
        PERMIT_VERIFIER_PATH,
        RAW_TRACE_VERIFIER_PATH,
        SUBMISSION_BUILDER_PATH,
    ):
        source = repo_path(source_root, relative)
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    write_synthetic_execution_surface(target_root)
    authorization = synthetic_authorization(target_root)
    write_canonical(target_root / AUTHORIZATION_PATH, authorization)
    for seat in SEATS:
        prediction = synthetic_prediction(seat)
        prior_path = f"synthetic/prior/{seat}.json"
        prior = {
            "actor": copy.deepcopy(prediction["actor"]),
            "artifact_type": "reconstruction_submission",
            "condition_id": prediction["condition_id"],
            "run_id": RUN_ID,
            "stage": "reconstruction",
            "submission_id": f"submission.reconstruction.{seat}",
        }
        write_canonical(target_root / prior_path, prior)
        prior_sha256 = sha256_bytes((target_root / prior_path).read_bytes())
        prediction["prior_stage_submission_sha256"] = prior_sha256
        prediction["input_artifacts"][1]["sha256"] = prior_sha256

        prior_dispatch_path = f"synthetic/prior-dispatch/{seat}.json"
        write_canonical(
            target_root / prior_dispatch_path,
            {
                "artifact_type": "stage1_seat_dispatch_receipt",
                "seat_id": seat,
            },
        )
        envelope_path = prediction["packaging"]["envelope_path"]
        envelope = {
            "actor": copy.deepcopy(prediction["actor"]),
            "condition_id": prediction["condition_id"],
            "prior_stage_submission_sha256": prior_sha256,
            "submission_id": prediction["submission_id"],
            "task_id": prediction["task_id"],
        }
        write_canonical(target_root / envelope_path, envelope)
        prediction["packaging"]["envelope_sha256"] = sha256_bytes(
            (target_root / envelope_path).read_bytes()
        )
        payload_path = prediction["raw_payload"]["path"]
        payload = {
            "pollution": copy.deepcopy(prediction["pollution"]),
            "prediction_answers": copy.deepcopy(prediction["prediction_answers"]),
        }
        write_canonical(target_root / payload_path, payload)
        prediction["raw_payload"]["sha256"] = sha256_bytes(
            (target_root / payload_path).read_bytes()
        )
        write_canonical(
            target_root / EXPECTED_PREDICTIONS[seat][1],
            prediction,
        )
        write_canonical(
            target_root / EXPECTED_STAGE2_RECEIPTS[seat],
            {
                "actor": copy.deepcopy(prediction["actor"]),
                "artifact_type": "stage2_seat_dispatch_receipt",
                "authorization_receipt": artifact_reference(
                    target_root, AUTHORIZATION_PATH
                ),
                "condition_id": prediction["condition_id"],
                "seat_id": seat,
                "stage1_dispatch_receipt": artifact_reference(
                    target_root, prior_dispatch_path
                ),
                "stage1_submission": artifact_reference(
                    target_root, prior_path
                ),
            },
        )
    lines = [
        f"{EXPECTED_PREDICTIONS[seat][1]}\t"
        f"{sha256_bytes((target_root / EXPECTED_PREDICTIONS[seat][1]).read_bytes())}\n"
        for seat in SEATS
    ]
    preimage = target_root / PREIMAGE_PATH
    preimage.parent.mkdir(parents=True, exist_ok=True)
    if include_preimage:
        preimage.write_bytes("".join(lines).encode("utf-8"))
    (target_root / PERMIT_PATH).parent.mkdir(parents=True, exist_ok=True)


def expect_failure(label: str, callback: Any) -> None:
    try:
        callback()
    except PermitError:
        return
    raise PermitError(f"negative control unexpectedly succeeded: {label}")


def run_self_test(source_root: Path) -> dict[str, Any]:
    source_root = source_root.resolve()
    system_temp = Path(tempfile.gettempdir()).resolve()
    prior_env = os.environ.get(SELF_TEST_ENV)
    negatives: list[str] = []
    try:
        with tempfile.TemporaryDirectory(
            prefix="game-primitives-execution-permit-",
        ) as temporary:
            test_parent = Path(temporary).resolve()
            if not test_parent.is_relative_to(system_temp):
                raise PermitError("self-test temporary directory escaped system temp")

            positive = test_parent / "positive" / "synthetic-repository"
            prepare_synthetic_repo(
                source_root,
                positive,
                include_preimage=False,
            )
            os.environ[SELF_TEST_ENV] = SELF_TEST_TOKEN
            expected_preimage = canonical_preimage_bytes(positive)
            preimage_result = materialize_preimage(
                positive,
                Path(PREIMAGE_PATH),
            )
            if (positive / PREIMAGE_PATH).read_bytes() != expected_preimage:
                raise PermitError("preimage materializer was not deterministic")
            expect_failure(
                "existing_preimage",
                lambda: materialize_preimage(positive, Path(PREIMAGE_PATH)),
            )
            negatives.append("existing_preimage")
            materialized = materialize_permit(positive, Path(PERMIT_PATH))
            verified = verify_permit(positive, Path(PERMIT_PATH), "CA-R1")
            if (
                materialized["execution_permit_sha256"]
                != verified["execution_permit_sha256"]
            ):
                raise PermitError("materialize and verify hashes differ")
            verifier_process = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(positive / PERMIT_VERIFIER_PATH),
                    "verify",
                    "--repo-root",
                    str(positive),
                    "--permit-path",
                    PERMIT_PATH,
                    "--case-id",
                    "CA-R2",
                ],
                cwd=positive,
                env={**os.environ, SELF_TEST_ENV: SELF_TEST_TOKEN},
                capture_output=True,
                check=False,
                text=True,
            )
            if verifier_process.returncode != 0:
                raise PermitError(
                    "verify-only entry point failed: "
                    + verifier_process.stderr.strip()
                )
            verifier_output = json.loads(verifier_process.stdout)
            if (
                verifier_output.get("status")
                != "formal_execution_permit_verified"
                or verifier_output.get("case_id") != "CA-R2"
                or verifier_output.get("execution_permit_sha256")
                != verified["execution_permit_sha256"]
                or verifier_output.get("execution_target", {}).get("case_id")
                != "CA-R2"
                or verifier_output.get("execution_target", {})
                .get("formal_runner", {})
                .get("path")
                != EXECUTION_TARGET_PATHS["CA-R2"]["formal_runner"]
            ):
                raise PermitError("verify-only entry point returned wrong fields")
            post_materialization_raw = (
                positive / RUN / "execution/raw/CA-R1/trace.json"
            )
            post_materialization_raw.parent.mkdir(parents=True, exist_ok=True)
            post_materialization_raw.write_bytes(
                b"synthetic post-materialization raw output\n"
            )
            post_output_verify = verify_permit(
                positive,
                Path(PERMIT_PATH),
                "CA-R3",
            )
            if (
                post_output_verify["execution_permit_sha256"]
                != verified["execution_permit_sha256"]
            ):
                raise PermitError("post-output permit verification changed the permit")
            expect_failure(
                "existing_output",
                lambda: materialize_permit(positive, Path(PERMIT_PATH)),
            )
            negatives.append("existing_output")

            def negative_repo(label: str) -> Path:
                target = test_parent / label / "synthetic-repository"
                prepare_synthetic_repo(source_root, target)
                return target

            existing_formal_output = negative_repo("existing_formal_output")
            raw_output = (
                existing_formal_output / RUN / "execution/raw/CA-R1/trace.json"
            )
            raw_output.parent.mkdir(parents=True, exist_ok=True)
            raw_output.write_bytes(b"synthetic formal-output sentinel\n")
            expect_failure(
                "existing_formal_output",
                lambda: materialize_permit(
                    existing_formal_output,
                    Path(PERMIT_PATH),
                ),
            )
            negatives.append("existing_formal_output")

            target_mutation = negative_repo("target_byte_mutation")
            target_path = (
                target_mutation
                / EXECUTION_TARGET_PATHS["CA-R1"]["support_artifacts"][
                    "variant_patch"
                ]
            )
            target_path.write_bytes(
                target_path.read_bytes() + b"synthetic mutation\n"
            )
            expect_failure(
                "target_byte_mutation",
                lambda: materialize_permit(
                    target_mutation,
                    Path(PERMIT_PATH),
                ),
            )
            negatives.append("target_byte_mutation")

            manifest_missing = negative_repo("manifest_missing_target")
            manifest_path = manifest_missing / RUN / "manifest.json"
            manifest, _ = read_json(manifest_path)
            missing_path = EXECUTION_TARGET_PATHS["CA-R1"]["formal_runner"].removeprefix(
                RUN + "/"
            )
            manifest["artifacts"] = [
                entry
                for entry in manifest["artifacts"]
                if entry["path"] != missing_path
            ]
            write_canonical(manifest_path, manifest)
            expect_failure(
                "manifest_missing_target",
                lambda: materialize_permit(
                    manifest_missing,
                    Path(PERMIT_PATH),
                ),
            )
            negatives.append("manifest_missing_target")

            manifest_not_frozen = negative_repo("manifest_target_not_frozen")
            manifest_path = manifest_not_frozen / RUN / "manifest.json"
            manifest, _ = read_json(manifest_path)
            target_path_value = EXECUTION_TARGET_PATHS["CA-R2"][
                "formal_input"
            ].removeprefix(RUN + "/")
            for entry in manifest["artifacts"]:
                if entry["path"] == target_path_value:
                    entry["included_in_frozen_set"] = False
                    break
            write_canonical(manifest_path, manifest)
            expect_failure(
                "manifest_target_not_frozen",
                lambda: materialize_permit(
                    manifest_not_frozen,
                    Path(PERMIT_PATH),
                ),
            )
            negatives.append("manifest_target_not_frozen")

            manifest_status = negative_repo("manifest_status_not_frozen")
            manifest_path = manifest_status / RUN / "manifest.json"
            manifest, _ = read_json(manifest_path)
            manifest["status"] = "preparing"
            write_canonical(manifest_path, manifest)
            expect_failure(
                "manifest_status_not_frozen",
                lambda: materialize_permit(
                    manifest_status,
                    Path(PERMIT_PATH),
                ),
            )
            negatives.append("manifest_status_not_frozen")

            manifest_hash_mismatch = negative_repo("manifest_hash_mismatch")
            manifest_path = manifest_hash_mismatch / RUN / "manifest.json"
            manifest, _ = read_json(manifest_path)
            target_path_value = EXECUTION_TARGET_PATHS["CA-R3"][
                "test_body"
            ].removeprefix(RUN + "/")
            for entry in manifest["artifacts"]:
                if entry["path"] == target_path_value:
                    entry["sha256"] = "f" * 64
                    break
            write_canonical(manifest_path, manifest)
            expect_failure(
                "manifest_hash_mismatch",
                lambda: materialize_permit(
                    manifest_hash_mismatch,
                    Path(PERMIT_PATH),
                ),
            )
            negatives.append("manifest_hash_mismatch")

            synthetic_auth = negative_repo("synthetic_authorization")
            auth_path = synthetic_auth / AUTHORIZATION_PATH
            auth, _ = read_json(auth_path)
            auth.update(
                {
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
                    "authorized_by": {
                        "identifier": "synthetic-self-test-harness",
                        "role": "self_test_harness",
                    },
                }
            )
            auth["authorization_basis"].update(
                {
                    "decision": "synthetic_only",
                    "source_kind": "synthetic_self_test",
                }
            )
            write_canonical(auth_path, auth)
            expect_failure(
                "synthetic_authorization",
                lambda: materialize_permit(synthetic_auth, Path(PERMIT_PATH)),
            )
            negatives.append("synthetic_authorization")

            missing = negative_repo("missing_seat")
            preimage_path = missing / PREIMAGE_PATH
            preimage_path.write_bytes(
                b"\n".join(preimage_path.read_bytes().splitlines()[:3]) + b"\n"
            )
            expect_failure(
                "missing_seat",
                lambda: materialize_permit(missing, Path(PERMIT_PATH)),
            )
            negatives.append("missing_seat")

            duplicate = negative_repo("duplicate_seat")
            preimage_path = duplicate / PREIMAGE_PATH
            lines = preimage_path.read_bytes().splitlines(keepends=True)
            lines[1] = lines[0]
            preimage_path.write_bytes(b"".join(lines))
            expect_failure(
                "duplicate_seat",
                lambda: materialize_permit(duplicate, Path(PERMIT_PATH)),
            )
            negatives.append("duplicate_seat")

            mismatch = negative_repo("condition_mismatch")
            prediction_path = mismatch / EXPECTED_PREDICTIONS["p02"][1]
            prediction, _ = read_json(prediction_path)
            prediction["condition_id"] = "condition-v02"
            write_canonical(prediction_path, prediction)
            preimage_path = mismatch / PREIMAGE_PATH
            lines = preimage_path.read_text(encoding="utf-8").splitlines()
            lines[1] = (
                f"{EXPECTED_PREDICTIONS['p02'][1]}\t"
                f"{sha256_bytes(prediction_path.read_bytes())}"
            )
            preimage_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
            expect_failure(
                "condition_mismatch",
                lambda: materialize_permit(mismatch, Path(PERMIT_PATH)),
            )
            negatives.append("condition_mismatch")

            order = negative_repo("noncanonical_path_order")
            preimage_path = order / PREIMAGE_PATH
            lines = preimage_path.read_bytes().splitlines(keepends=True)
            lines[0], lines[1] = lines[1], lines[0]
            preimage_path.write_bytes(b"".join(lines))
            expect_failure(
                "noncanonical_path_order",
                lambda: materialize_permit(order, Path(PERMIT_PATH)),
            )
            negatives.append("noncanonical_path_order")

            noncanonical = negative_repo("noncanonical_prediction")
            prediction_path = noncanonical / EXPECTED_PREDICTIONS["p03"][1]
            prediction, _ = read_json(prediction_path)
            prediction_path.write_text(
                json.dumps(prediction, ensure_ascii=False),
                encoding="utf-8",
                newline="\n",
            )
            preimage_path = noncanonical / PREIMAGE_PATH
            lines = preimage_path.read_text(encoding="utf-8").splitlines()
            lines[2] = (
                f"{EXPECTED_PREDICTIONS['p03'][1]}\t"
                f"{sha256_bytes(prediction_path.read_bytes())}"
            )
            preimage_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
            expect_failure(
                "noncanonical_prediction",
                lambda: materialize_permit(noncanonical, Path(PERMIT_PATH)),
            )
            negatives.append("noncanonical_prediction")

            non_first = negative_repo("non_first_submission")
            prediction_path = non_first / EXPECTED_PREDICTIONS["p04"][1]
            prediction, _ = read_json(prediction_path)
            prediction["first_submission"] = False
            write_canonical(prediction_path, prediction)
            preimage_path = non_first / PREIMAGE_PATH
            lines = preimage_path.read_text(encoding="utf-8").splitlines()
            lines[3] = (
                f"{EXPECTED_PREDICTIONS['p04'][1]}\t"
                f"{sha256_bytes(prediction_path.read_bytes())}"
            )
            preimage_path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
            expect_failure(
                "non_first_submission",
                lambda: materialize_permit(non_first, Path(PERMIT_PATH)),
            )
            negatives.append("non_first_submission")

            broken_lineage = negative_repo("broken_lineage")
            raw_path = broken_lineage / "synthetic/raw/p01.json"
            raw_path.write_bytes(b'{"tampered":true}\n')
            expect_failure(
                "broken_lineage",
                lambda: materialize_permit(
                    broken_lineage,
                    Path(PERMIT_PATH),
                ),
            )
            negatives.append("broken_lineage")

            return {
                "execution_permit_sha256": verified[
                    "execution_permit_sha256"
                ],
                "formal_comparator_executed": False,
                "formal_input_executed": False,
                "negative_controls": negatives,
                "prediction_preimage_materialized": (
                    preimage_result["status"]
                    == "prediction_set_preimage_materialized"
                ),
                "prediction_set_digest": verified["prediction_set_digest"],
                "real_fixture_executed": False,
                "run_id": RUN_ID,
                "status": "synthetic_execution_permit_self_test_passed",
                "synthetic_repository_removed_on_exit": True,
                "synthetic_repository_under_system_temp": True,
                "verify_only_entrypoint_checked": True,
                "verify_succeeds_after_materialization_output": True,
            }
    finally:
        if prior_env is None:
            os.environ.pop(SELF_TEST_ENV, None)
        else:
            os.environ[SELF_TEST_ENV] = prior_env


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    materialize = subparsers.add_parser("materialize")
    materialize.add_argument("--repo-root", type=Path, required=True)
    materialize.add_argument("--permit-path", type=Path, required=True)

    preimage = subparsers.add_parser("materialize-preimage")
    preimage.add_argument("--repo-root", type=Path, required=True)
    preimage.add_argument("--preimage-path", type=Path, required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--permit-path", type=Path, required=True)
    verify.add_argument("--case-id", choices=CASES, required=True)

    self_test = subparsers.add_parser("self-test")
    self_test.add_argument("--repo-root", type=Path, required=True)
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "materialize":
            result = materialize_permit(
                args.repo_root.resolve(),
                args.permit_path,
            )
        elif args.command == "materialize-preimage":
            result = materialize_preimage(
                args.repo_root.resolve(),
                args.preimage_path,
            )
        elif args.command == "verify":
            result = verify_permit(
                args.repo_root.resolve(),
                args.permit_path,
                args.case_id,
            )
        else:
            result = run_self_test(args.repo_root.resolve())
    except (PermitError, OSError, ValueError, KeyError) as error:
        print(f"execution permit error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
