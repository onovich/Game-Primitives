#!/usr/bin/env python3
"""Synthetic controls for truth-continuity-attestation 0.1.0.

This self-test is intentionally restricted to disposable data. It never opens
the repository's real ``runs/**`` tree and never executes a runner, comparator,
truth reveal, or commitment-management tool.
"""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA = PILOT / (
    "schema/truth-continuity-attestation-0.1.0.schema.json"
)
MATERIALIZER = PILOT / (
    "tools/materialize-truth-continuity-attestation-v0.1.0.py"
)
VERIFIER = PILOT / (
    "tools/verify-truth-continuity-attestation-v0.1.0.py"
)
INSTANCE_PATH = PILOT / (
    "runs/continuous-002/source/"
    "truth-continuity-attestation-v0.1.0.json"
)
SCHEMA_URL = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    f"{SCHEMA.as_posix()}"
)
BASE_MANIFEST = (
    "research/calibration-tests/continuous-action-pilot/"
    "runs/continuous-001/manifest.json"
)
CANDIDATE_MANIFEST = (
    "research/calibration-tests/continuous-action-pilot/"
    "runs/continuous-002/manifest.json"
)
EXPECTED_POSITIVE_IDS = (
    "P01_SCHEMA_ACCEPTS_MINIMAL_INSTANCE",
    "P02_MATERIALIZER_PREVIEW_IS_DETERMINISTIC_AND_INERT",
    "P03_MATERIALIZER_PUBLISHES_EXACTLY_ONCE",
    "P04_VERIFIER_RECOMPUTES_READ_ONLY",
)
EXPECTED_NEGATIVE_IDS = (
    "N-SCHEMA01_PLAINTEXT_FIELD_REJECTED",
    "N-SCHEMA02_EQUIVALENCE_CLAIM_REJECTED",
    "N-SCHEMA03_BASE_ANCHOR_DRIFT_REJECTED",
    "N-SCHEMA04_PROCESS_METHOD_DRIFT_REJECTED",
    "N-SCHEMA05_REVIEWER_ROLE_DRIFT_REJECTED",
    "N-SCHEMA06_NONCE_FIELD_REJECTED",
    "N-SCHEMA07_TOOL_PATH_DRIFT_REJECTED",
    "N-SCHEMA08_FUTURE_RECOMPUTATION_OVERCLAIM_REJECTED",
    "N-SCHEMA09_ZERO_DIGEST_REJECTED",
    "N-PUBLISH01_OVERWRITE_REJECTED",
    "N-CLI01_ISOLATED_RUNTIME_REQUIRED",
    "N-CLI02_REPOSITORY_READ_ACK_REQUIRED",
    "N-CLI03_EXTERNAL_REVIEW_READ_ACK_REQUIRED",
    "N-CLI04_WRITE_FLAG_REQUIRED",
    "N-CLI05_REVIEW_RECORD_MUST_BE_EXTERNAL",
    "N-PATH01_REPOSITORY_CASE_DRIFT_REJECTED",
    "N-TRUST01_SCHEMA_PIN_MISMATCH",
    "N-TRUST02_MATERIALIZER_PIN_MISMATCH",
    "N-TRUST03_VERIFIER_PIN_MISMATCH",
    "N-PIN01_ZERO_BASE_COMMITMENT_REJECTED",
    "N-PIN02_ZERO_CANDIDATE_COMMITMENT_REJECTED",
    "N-PIN03_ZERO_PROCESS_ARTIFACT_REJECTED",
    "N-REVIEW01_RECORD_PIN_MISMATCH",
    "N-REVIEW02_INPUT_PIN_MISMATCH",
    "N-REVIEW03_INTERNAL_INPUT_DIGEST_MISMATCH",
    "N-REVIEW04_REVIEWER_IDENTIFIER_PIN_MISMATCH",
    "N-REVIEW05_REVIEWER_SESSION_PIN_MISMATCH",
    "N-REVIEW06_PROCESS_ARTIFACT_PIN_MISMATCH",
    "N-REVIEW07_OPERATOR_REVIEWER_INDEPENDENCE_REQUIRED",
    "N-REVIEW08_TIME_ORDER_REJECTED",
    "N-COMMIT01_BASE_PIN_MISMATCH",
    "N-COMMIT02_CANDIDATE_PIN_MISMATCH",
    "N-COMMIT03_EQUAL_COMMITMENTS_REJECTED",
    "N-COMMIT04_CANDIDATE_MANIFEST_DRIFT_REJECTED",
    "N-BYTES01_REVIEW_BOM_REJECTED",
    "N-BYTES02_REVIEW_CRLF_REJECTED",
    "N-BYTES03_CANDIDATE_DUPLICATE_KEY_REJECTED",
    "N-BYTES04_CANDIDATE_NONFINITE_REJECTED",
    "N-HOSTILE01_COMMAND_METADATA_REJECTED_WITHOUT_EXECUTION",
    "N-VERIFY01_REPOSITORY_READ_ACK_REQUIRED",
    "N-VERIFY02_VERIFIER_PIN_MISMATCH",
    "N-VERIFY03_INSTANCE_TOOLCHAIN_DRIFT_REJECTED",
    "N-VERIFY04_INSTANCE_CRLF_REJECTED",
    "N-VERIFY05_MANIFEST_COMMITMENT_DRIFT_REJECTED",
)


def commitment(
    digest: str,
    created_at: str,
    *,
    truth_bundle_bytes: int,
) -> dict[str, Any]:
    return {
        "algorithm": "SHA-256",
        "combination": (
            "secret_nonce_bytes || exact_truth_bundle_bytes"
        ),
        "commitment": digest,
        "created_at": created_at,
        "nonce_length_bytes": 32,
        "truth_bundle_bytes": truth_bundle_bytes,
        "truth_bundle_name": "sealed-truth.json",
    }


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def refresh_review_input(record: dict[str, Any]) -> None:
    review_input = {
        "base_binding": record["base_binding"],
        "candidate_binding": record["candidate_binding"],
        "continuity_process": record["continuity_process"],
    }
    record["review"]["input_set_sha256"] = sha256_bytes(
        canonical_bytes(review_input)
    )


def claim_boundary() -> dict[str, bool]:
    return {
        "commitment_records_bound": True,
        "formal_comparator_executed": False,
        "formal_dispatch_authorized": False,
        "formal_dispatch_performed": False,
        "formal_runner_executed": False,
        "future_commitment_recomputation_proven": False,
        "hidden_plaintext_semantic_equivalence_proven": False,
        "offline_process_metadata_bound": True,
        "plaintext_fields_present": False,
        "post_reveal_mechanical_verification_required": True,
        "reviewer_identity_cryptographically_authenticated": False,
        "reviewer_identity_statement_bound": True,
        "secret_nonce_fields_present": False,
        "truth_reveal_performed": False,
    }


def valid_review_record() -> dict[str, Any]:
    record = {
        "artifact_type": "truth_continuity_review_record",
        "artifact_version": "0.1.0",
        "base_binding": {
            "completion_commit": (
                "c42013d5cad89811e8838696c4072f6f71a859fb"
            ),
            "completion_tree": (
                "f8aae165fcf9620b8ba9cee64766e39f642d8d4c"
            ),
            "finalize_commit_b": (
                "972589c6fb716932e01e09c7cefa92f59953336b"
            ),
            "freeze_anchor_commit_a": (
                "bbea296b019ea1b5f5f3bb8cfe5937b0ff276f5b"
            ),
            "frozen_artifact_set_digest": (
                "05ecfdb1e88db74e6839c1a443e6cb09a7a9e89754131b018e13ed04f7ff3c69"
            ),
            "manifest_path": BASE_MANIFEST,
            "run_id": "continuous-001",
            "truth_commitment": commitment(
                "1" * 64,
                "2026-07-20T00:00:00Z",
                truth_bundle_bytes=1200,
            ),
        },
        "candidate_binding": {
            "manifest_path": CANDIDATE_MANIFEST,
            "manifest_schema_version": "0.1.1",
            "manifest_status_at_review": "preparing",
            "run_id": "continuous-002",
            "truth_commitment": commitment(
                "2" * 64,
                "2026-07-30T00:00:00Z",
                truth_bundle_bytes=1300,
            ),
        },
        "claim_boundary": claim_boundary(),
        "continuity_process": {
            "allowed_variation_profile_id": (
                "nonsemantic_serialization_metadata_only_v0.1.0"
            ),
            "comparison_policy_id": (
                "truth_continuity_offline_review_policy_v0.1.0"
            ),
            "confidentiality_boundary": {
                "plaintext_processed_outside_repository": True,
                "raw_comparison_output_embedded": False,
                "repository_truth_or_nonce_written": False,
                "semantic_projection_digest_embedded": False,
            },
            "method": (
                "offline_semantic_projection_review_v0.1.0"
            ),
            "operator": {
                "identifier": "synthetic.operator",
                "role": "offline_continuity_review_operator",
                "session_id": "operator-session-001",
            },
            "performed_at": "2026-07-30T00:01:00Z",
            "process_artifact": {
                "artifact_id": (
                    "truth-continuity-offline-review-process"
                ),
                "artifact_version": "0.1.0",
                "sha256": "3" * 64,
            },
            "protected_projection_profile_id": (
                "continuous_action_truth_semantics_v0.1.0"
            ),
            "result": (
                "reviewer_reported_process_continuity_supported"
            ),
        },
        "review": {
            "decision": "passed",
            "identity_assurance": (
                "caller_pinned_identifier_and_session_"
                "not_cryptographically_authenticated"
            ),
            "input_set_sha256": "0" * 64,
            "reviewed_at": "2026-07-30T00:02:00Z",
            "reviewer": {
                "identifier": "synthetic.reviewer",
                "role": "independent_truth_continuity_reviewer",
                "session_id": "reviewer-session-001",
            },
        },
    }
    refresh_review_input(record)
    return record


def valid_instance() -> dict[str, Any]:
    record = valid_review_record()
    return {
        "$schema": SCHEMA_URL,
        "artifact_type": "truth_continuity_attestation",
        "artifact_version": "0.1.0",
        "attestation_id": (
            "tca-"
            + record["candidate_binding"]["truth_commitment"][
                "commitment"
            ][:12]
            + "-"
            + record["review"]["input_set_sha256"][:12]
        ),
        "candidate_run_id": "continuous-002",
        "conclusion": {
            "claim_scope": (
                "commitments_process_metadata_and_"
                "caller_pinned_review_identity_only"
            ),
            "hidden_plaintext_semantic_equivalence_proven": False,
            "post_reveal_mechanical_verification_required": True,
            "status": "nonplaintext_continuity_process_attested",
        },
        "document_state": "pre_gate_nonplaintext_process_attestation",
        "instance_path": INSTANCE_PATH.as_posix(),
        "materialized_at": "2026-07-30T00:03:00Z",
        "review_input_sha256": record["review"]["input_set_sha256"],
        "review_record": record,
        "review_record_sha256": sha256_bytes(canonical_bytes(record)),
        "toolchain": {
            "materializer": {
                "artifact_version": "0.1.0",
                "path": (
                    f"{PILOT.as_posix()}/tools/"
                    "materialize-truth-continuity-attestation-v0.1.0.py"
                ),
                "sha256": "6" * 64,
            },
            "schema": {
                "artifact_version": "0.1.0",
                "path": SCHEMA.as_posix(),
                "sha256": "7" * 64,
            },
            "verifier": {
                "artifact_version": "0.1.0",
                "path": (
                    f"{PILOT.as_posix()}/tools/"
                    "verify-truth-continuity-attestation-v0.1.0.py"
                ),
                "sha256": "8" * 64,
            },
        },
    }


def command(tool: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(tool), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def require_success(
    completed: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    if completed.returncode != 0:
        raise RuntimeError(
            "CLI unexpectedly failed: "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    return json.loads(completed.stdout)


def require_failure(
    completed: subprocess.CompletedProcess[str],
    *,
    expected_fragment: str,
) -> dict[str, Any]:
    if completed.returncode == 0:
        raise RuntimeError(
            f"CLI unexpectedly succeeded: {completed.stdout!r}"
        )
    result = json.loads(completed.stderr)
    if expected_fragment not in result.get("error", ""):
        raise RuntimeError(
            "CLI failed for the wrong reason: "
            f"expected={expected_fragment!r} stderr={completed.stderr!r}"
        )
    return result


def without_flag(arguments: list[str], flag: str) -> list[str]:
    if flag not in arguments:
        raise RuntimeError(f"test argument flag is absent: {flag}")
    return [argument for argument in arguments if argument != flag]


def replace_option(
    arguments: list[str],
    option: str,
    value: str,
) -> list[str]:
    replaced = list(arguments)
    try:
        index = replaced.index(option)
    except ValueError as error:
        raise RuntimeError(
            f"test argument option is absent: {option}"
        ) from error
    replaced[index + 1] = value
    return replaced


def materializer_arguments(
    root: Path,
    review_path: Path,
    *,
    materialized_at: str,
) -> list[str]:
    record = json.loads(review_path.read_text(encoding="utf-8"))
    review_raw = review_path.read_bytes()
    return [
        "--repo-root",
        str(root),
        "--review-record",
        str(review_path),
        "--materialized-at",
        materialized_at,
        "--expected-schema-sha256",
        sha256_bytes((root / SCHEMA).read_bytes()),
        "--expected-materializer-sha256",
        sha256_bytes((root / MATERIALIZER).read_bytes()),
        "--expected-verifier-sha256",
        sha256_bytes((root / VERIFIER).read_bytes()),
        "--expected-base-commitment",
        record["base_binding"]["truth_commitment"]["commitment"],
        "--expected-candidate-commitment",
        record["candidate_binding"]["truth_commitment"]["commitment"],
        "--expected-review-record-sha256",
        sha256_bytes(review_raw),
        "--expected-review-input-sha256",
        record["review"]["input_set_sha256"],
        "--expected-reviewer-identifier",
        record["review"]["reviewer"]["identifier"],
        "--expected-reviewer-session-id",
        record["review"]["reviewer"]["session_id"],
        "--expected-process-artifact-sha256",
        record["continuity_process"]["process_artifact"]["sha256"],
        "--allow-repository-byte-reads",
        "--allow-external-review-record-byte-read",
    ]


def verifier_arguments(root: Path) -> list[str]:
    instance = json.loads((root / INSTANCE_PATH).read_text(encoding="utf-8"))
    record = instance["review_record"]
    return [
        "--repo-root",
        str(root),
        "--expected-schema-sha256",
        sha256_bytes((root / SCHEMA).read_bytes()),
        "--expected-materializer-sha256",
        sha256_bytes((root / MATERIALIZER).read_bytes()),
        "--expected-verifier-sha256",
        sha256_bytes((root / VERIFIER).read_bytes()),
        "--expected-base-commitment",
        record["base_binding"]["truth_commitment"]["commitment"],
        "--expected-candidate-commitment",
        record["candidate_binding"]["truth_commitment"]["commitment"],
        "--expected-review-record-sha256",
        instance["review_record_sha256"],
        "--expected-review-input-sha256",
        instance["review_input_sha256"],
        "--expected-reviewer-identifier",
        record["review"]["reviewer"]["identifier"],
        "--expected-reviewer-session-id",
        record["review"]["reviewer"]["session_id"],
        "--expected-process-artifact-sha256",
        record["continuity_process"]["process_artifact"]["sha256"],
        "--allow-repository-byte-reads",
    ]


def snapshot_files(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_bytes(path.read_bytes())
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def build_synthetic_repository(
    source_root: Path,
    root: Path,
    external: Path,
) -> Path:
    for relative in (SCHEMA, MATERIALIZER, VERIFIER):
        source = source_root / relative
        if not source.is_file():
            raise RuntimeError(f"required source is absent: {source}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    record = valid_review_record()
    manifest = {
        "artifact_type": "formal_run_manifest",
        "run_id": "continuous-002",
        "schema_version": "0.1.1",
        "status": "preparing",
        "truth_commitment": record["candidate_binding"][
            "truth_commitment"
        ],
    }
    write_json(root / CANDIDATE_MANIFEST, manifest)
    (root / INSTANCE_PATH).parent.mkdir(parents=True, exist_ok=True)
    review_path = external / "truth-continuity-review-record.json"
    write_json(review_path, record)
    return review_path


def build_case(
    source_root: Path,
    temporary_root: Path,
    name: str,
) -> tuple[Path, Path]:
    root = temporary_root / name / "repository"
    external = temporary_root / name / "external"
    root.mkdir(parents=True)
    external.mkdir(parents=True)
    return root, build_synthetic_repository(source_root, root, external)


def build_case_arguments(
    source_root: Path,
    temporary_root: Path,
    name: str,
) -> tuple[Path, Path, list[str]]:
    root, review_path = build_case(source_root, temporary_root, name)
    return (
        root,
        review_path,
        materializer_arguments(
            root,
            review_path,
            materialized_at="2026-07-30T00:03:00Z",
        ),
    )


def require_invalid(
    validator: Draft202012Validator,
    value: dict[str, Any],
) -> None:
    if not tuple(validator.iter_errors(value)):
        raise RuntimeError("schema unexpectedly accepted invalid fixture")


def run_self_test(repo_root: Path) -> dict[str, Any]:
    schema_path = repo_root / SCHEMA
    if not schema_path.is_file():
        raise RuntimeError(f"required source is absent: {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )

    positive: list[str] = []
    negative: list[str] = []
    instance = valid_instance()
    validator.validate(instance)
    positive.append("P01_SCHEMA_ACCEPTS_MINIMAL_INSTANCE")

    plaintext = copy.deepcopy(instance)
    plaintext["review_record"]["continuity_process"][
        "plaintext_truth"
    ] = {"case": "forbidden"}
    require_invalid(validator, plaintext)
    negative.append("N-SCHEMA01_PLAINTEXT_FIELD_REJECTED")

    overclaim = copy.deepcopy(instance)
    overclaim["review_record"]["claim_boundary"][
        "hidden_plaintext_semantic_equivalence_proven"
    ] = True
    require_invalid(validator, overclaim)
    negative.append("N-SCHEMA02_EQUIVALENCE_CLAIM_REJECTED")

    anchor_drift = copy.deepcopy(instance)
    anchor_drift["review_record"]["base_binding"][
        "freeze_anchor_commit_a"
    ] = "9" * 40
    require_invalid(validator, anchor_drift)
    negative.append("N-SCHEMA03_BASE_ANCHOR_DRIFT_REJECTED")

    method_drift = copy.deepcopy(instance)
    method_drift["review_record"]["continuity_process"][
        "method"
    ] = "uncontrolled_manual_comparison"
    require_invalid(validator, method_drift)
    negative.append("N-SCHEMA04_PROCESS_METHOD_DRIFT_REJECTED")

    reviewer_role_drift = copy.deepcopy(instance)
    reviewer_role_drift["review_record"]["review"]["reviewer"][
        "role"
    ] = "process_operator"
    require_invalid(validator, reviewer_role_drift)
    negative.append("N-SCHEMA05_REVIEWER_ROLE_DRIFT_REJECTED")

    nonce_leak = copy.deepcopy(instance)
    nonce_leak["review_record"]["candidate_binding"][
        "secret_nonce"
    ] = "forbidden"
    require_invalid(validator, nonce_leak)
    negative.append("N-SCHEMA06_NONCE_FIELD_REJECTED")

    path_drift = copy.deepcopy(instance)
    path_drift["toolchain"]["verifier"]["path"] = (
        "../untrusted-verifier.py"
    )
    require_invalid(validator, path_drift)
    negative.append("N-SCHEMA07_TOOL_PATH_DRIFT_REJECTED")

    recomputation_overclaim = copy.deepcopy(instance)
    recomputation_overclaim["review_record"]["claim_boundary"][
        "future_commitment_recomputation_proven"
    ] = True
    require_invalid(validator, recomputation_overclaim)
    negative.append(
        "N-SCHEMA08_FUTURE_RECOMPUTATION_OVERCLAIM_REJECTED"
    )

    zero_digest = copy.deepcopy(instance)
    zero_digest["review_record"]["continuity_process"][
        "process_artifact"
    ]["sha256"] = "0" * 64
    require_invalid(validator, zero_digest)
    negative.append("N-SCHEMA09_ZERO_DIGEST_REJECTED")

    with tempfile.TemporaryDirectory(
        prefix="truth-continuity-attestation-self-test-"
    ) as temporary:
        temporary_root = Path(temporary)
        synthetic_root = temporary_root / "repository"
        external_root = temporary_root / "external"
        synthetic_root.mkdir()
        external_root.mkdir()
        review_path = build_synthetic_repository(
            repo_root,
            synthetic_root,
            external_root,
        )
        arguments = materializer_arguments(
            synthetic_root,
            review_path,
            materialized_at="2026-07-30T00:03:00Z",
        )
        first = require_success(
            command(
                synthetic_root / MATERIALIZER,
                "preview",
                *arguments,
            )
        )
        second = require_success(
            command(
                synthetic_root / MATERIALIZER,
                "preview",
                *arguments,
            )
        )
        if first != second:
            raise RuntimeError("materializer preview is not deterministic")
        if (synthetic_root / INSTANCE_PATH).exists():
            raise RuntimeError("materializer preview wrote the instance")
        if first["status"] != "previewed_nonplaintext":
            raise RuntimeError("unexpected materializer preview status")
        positive.append(
            "P02_MATERIALIZER_PREVIEW_IS_DETERMINISTIC_AND_INERT"
        )
        materialized = require_success(
            command(
                synthetic_root / MATERIALIZER,
                "materialize",
                *arguments,
                "--write",
            )
        )
        instance_path = synthetic_root / INSTANCE_PATH
        instance_raw = instance_path.read_bytes()
        if materialized["attestation_sha256"] != sha256_bytes(
            instance_raw
        ):
            raise RuntimeError(
                "materialized attestation digest does not match its bytes"
            )
        validator.validate(json.loads(instance_raw))
        positive.append("P03_MATERIALIZER_PUBLISHES_EXACTLY_ONCE")

        require_failure(
            command(
                synthetic_root / MATERIALIZER,
                "materialize",
                *arguments,
                "--write",
            ),
            expected_fragment="OUTPUT_EXISTS",
        )
        negative.append("N-PUBLISH01_OVERWRITE_REJECTED")

        before_verify = snapshot_files(synthetic_root)
        verified = require_success(
            command(
                synthetic_root / VERIFIER,
                "verify",
                *verifier_arguments(synthetic_root),
            )
        )
        after_verify = snapshot_files(synthetic_root)
        if before_verify != after_verify:
            raise RuntimeError("verifier changed synthetic repository bytes")
        if verified["status"] != "verified_nonplaintext":
            raise RuntimeError("unexpected verifier status")
        positive.append("P04_VERIFIER_RECOMPUTES_READ_ONLY")

        cli01_root, _, cli01_args = build_case_arguments(
            repo_root,
            temporary_root,
            "cli01",
        )
        require_failure(
            subprocess.run(
                [
                    sys.executable,
                    str(cli01_root / MATERIALIZER),
                    "preview",
                    *cli01_args,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            ),
            expected_fragment="ISOLATED_RUNTIME_REQUIRED",
        )
        negative.append("N-CLI01_ISOLATED_RUNTIME_REQUIRED")

        cli02_root, _, cli02_args = build_case_arguments(
            repo_root,
            temporary_root,
            "cli02",
        )
        require_failure(
            command(
                cli02_root / MATERIALIZER,
                "preview",
                *without_flag(
                    cli02_args,
                    "--allow-repository-byte-reads",
                ),
            ),
            expected_fragment=(
                "REPOSITORY_BYTE_READS_NOT_ACKNOWLEDGED"
            ),
        )
        negative.append("N-CLI02_REPOSITORY_READ_ACK_REQUIRED")

        cli03_root, _, cli03_args = build_case_arguments(
            repo_root,
            temporary_root,
            "cli03",
        )
        require_failure(
            command(
                cli03_root / MATERIALIZER,
                "preview",
                *without_flag(
                    cli03_args,
                    "--allow-external-review-record-byte-read",
                ),
            ),
            expected_fragment=(
                "EXTERNAL_REVIEW_BYTE_READ_NOT_ACKNOWLEDGED"
            ),
        )
        negative.append("N-CLI03_EXTERNAL_REVIEW_READ_ACK_REQUIRED")

        cli04_root, _, cli04_args = build_case_arguments(
            repo_root,
            temporary_root,
            "cli04",
        )
        require_failure(
            command(
                cli04_root / MATERIALIZER,
                "materialize",
                *cli04_args,
            ),
            expected_fragment="WRITE_FLAG_REQUIRED",
        )
        negative.append("N-CLI04_WRITE_FLAG_REQUIRED")

        cli05_root, cli05_review, _ = build_case_arguments(
            repo_root,
            temporary_root,
            "cli05",
        )
        inside_review = cli05_root / "inside-review-record.json"
        shutil.copy2(cli05_review, inside_review)
        cli05_args = materializer_arguments(
            cli05_root,
            inside_review,
            materialized_at="2026-07-30T00:03:00Z",
        )
        require_failure(
            command(
                cli05_root / MATERIALIZER,
                "preview",
                *cli05_args,
            ),
            expected_fragment="REVIEW_RECORD_INSIDE_REPOSITORY",
        )
        negative.append("N-CLI05_REVIEW_RECORD_MUST_BE_EXTERNAL")

        path01_root, _, path01_args = build_case_arguments(
            repo_root,
            temporary_root,
            "path01",
        )
        schema_directory = path01_root / PILOT / "schema"
        intermediate_directory = path01_root / PILOT / "schema-temporary"
        wrong_case_directory = path01_root / PILOT / "Schema"
        schema_directory.rename(intermediate_directory)
        intermediate_directory.rename(wrong_case_directory)
        require_failure(
            command(
                path01_root / MATERIALIZER,
                "preview",
                *path01_args,
            ),
            expected_fragment="REPOSITORY_PATH_CASE",
        )
        negative.append("N-PATH01_REPOSITORY_CASE_DRIFT_REJECTED")

        trust01_root, _, trust01_args = build_case_arguments(
            repo_root,
            temporary_root,
            "trust01",
        )
        require_failure(
            command(
                trust01_root / MATERIALIZER,
                "preview",
                *replace_option(
                    trust01_args,
                    "--expected-schema-sha256",
                    "9" * 64,
                ),
            ),
            expected_fragment="SCHEMA_PIN_MISMATCH",
        )
        negative.append("N-TRUST01_SCHEMA_PIN_MISMATCH")

        trust02_root, _, trust02_args = build_case_arguments(
            repo_root,
            temporary_root,
            "trust02",
        )
        require_failure(
            command(
                trust02_root / MATERIALIZER,
                "preview",
                *replace_option(
                    trust02_args,
                    "--expected-materializer-sha256",
                    "9" * 64,
                ),
            ),
            expected_fragment="MATERIALIZER_PIN_MISMATCH",
        )
        negative.append("N-TRUST02_MATERIALIZER_PIN_MISMATCH")

        trust03_root, _, trust03_args = build_case_arguments(
            repo_root,
            temporary_root,
            "trust03",
        )
        require_failure(
            command(
                trust03_root / MATERIALIZER,
                "preview",
                *replace_option(
                    trust03_args,
                    "--expected-verifier-sha256",
                    "9" * 64,
                ),
            ),
            expected_fragment="VERIFIER_PIN_MISMATCH",
        )
        negative.append("N-TRUST03_VERIFIER_PIN_MISMATCH")

        pin_root, _, pin_args = build_case_arguments(
            repo_root,
            temporary_root,
            "pin-zero",
        )
        require_failure(
            command(
                pin_root / MATERIALIZER,
                "preview",
                *replace_option(
                    pin_args,
                    "--expected-base-commitment",
                    "0" * 64,
                ),
            ),
            expected_fragment="PIN_FORMAT",
        )
        negative.append("N-PIN01_ZERO_BASE_COMMITMENT_REJECTED")

        require_failure(
            command(
                pin_root / MATERIALIZER,
                "preview",
                *replace_option(
                    pin_args,
                    "--expected-candidate-commitment",
                    "0" * 64,
                ),
            ),
            expected_fragment="PIN_FORMAT",
        )
        negative.append(
            "N-PIN02_ZERO_CANDIDATE_COMMITMENT_REJECTED"
        )

        require_failure(
            command(
                pin_root / MATERIALIZER,
                "preview",
                *replace_option(
                    pin_args,
                    "--expected-process-artifact-sha256",
                    "0" * 64,
                ),
            ),
            expected_fragment="PIN_FORMAT",
        )
        negative.append(
            "N-PIN03_ZERO_PROCESS_ARTIFACT_REJECTED"
        )

        review01_root, _, review01_args = build_case_arguments(
            repo_root,
            temporary_root,
            "review01",
        )
        require_failure(
            command(
                review01_root / MATERIALIZER,
                "preview",
                *replace_option(
                    review01_args,
                    "--expected-review-record-sha256",
                    "9" * 64,
                ),
            ),
            expected_fragment="REVIEW_RECORD_PIN_MISMATCH",
        )
        negative.append("N-REVIEW01_RECORD_PIN_MISMATCH")

        review02_root, _, review02_args = build_case_arguments(
            repo_root,
            temporary_root,
            "review02",
        )
        require_failure(
            command(
                review02_root / MATERIALIZER,
                "preview",
                *replace_option(
                    review02_args,
                    "--expected-review-input-sha256",
                    "9" * 64,
                ),
            ),
            expected_fragment="REVIEW_INPUT_PIN_MISMATCH",
        )
        negative.append("N-REVIEW02_INPUT_PIN_MISMATCH")

        review03_root, review03_path, _ = build_case_arguments(
            repo_root,
            temporary_root,
            "review03",
        )
        review03_record = json.loads(
            review03_path.read_text(encoding="utf-8")
        )
        review03_record["review"]["input_set_sha256"] = "9" * 64
        write_json(review03_path, review03_record)
        review03_args = materializer_arguments(
            review03_root,
            review03_path,
            materialized_at="2026-07-30T00:03:00Z",
        )
        require_failure(
            command(
                review03_root / MATERIALIZER,
                "preview",
                *review03_args,
            ),
            expected_fragment="REVIEW_INPUT_DIGEST_MISMATCH",
        )
        negative.append("N-REVIEW03_INTERNAL_INPUT_DIGEST_MISMATCH")

        review04_root, _, review04_args = build_case_arguments(
            repo_root,
            temporary_root,
            "review04",
        )
        require_failure(
            command(
                review04_root / MATERIALIZER,
                "preview",
                *replace_option(
                    review04_args,
                    "--expected-reviewer-identifier",
                    "other.reviewer",
                ),
            ),
            expected_fragment="REVIEWER_IDENTIFIER_PIN_MISMATCH",
        )
        negative.append(
            "N-REVIEW04_REVIEWER_IDENTIFIER_PIN_MISMATCH"
        )

        review05_root, _, review05_args = build_case_arguments(
            repo_root,
            temporary_root,
            "review05",
        )
        require_failure(
            command(
                review05_root / MATERIALIZER,
                "preview",
                *replace_option(
                    review05_args,
                    "--expected-reviewer-session-id",
                    "other-session-001",
                ),
            ),
            expected_fragment="REVIEWER_SESSION_PIN_MISMATCH",
        )
        negative.append("N-REVIEW05_REVIEWER_SESSION_PIN_MISMATCH")

        review06_root, _, review06_args = build_case_arguments(
            repo_root,
            temporary_root,
            "review06",
        )
        require_failure(
            command(
                review06_root / MATERIALIZER,
                "preview",
                *replace_option(
                    review06_args,
                    "--expected-process-artifact-sha256",
                    "9" * 64,
                ),
            ),
            expected_fragment="PROCESS_ARTIFACT_PIN_MISMATCH",
        )
        negative.append("N-REVIEW06_PROCESS_ARTIFACT_PIN_MISMATCH")

        review07_root, review07_path, _ = build_case_arguments(
            repo_root,
            temporary_root,
            "review07",
        )
        review07_record = json.loads(
            review07_path.read_text(encoding="utf-8")
        )
        review07_record["review"]["reviewer"]["identifier"] = (
            review07_record["continuity_process"]["operator"][
                "identifier"
            ]
        )
        write_json(review07_path, review07_record)
        review07_args = materializer_arguments(
            review07_root,
            review07_path,
            materialized_at="2026-07-30T00:03:00Z",
        )
        require_failure(
            command(
                review07_root / MATERIALIZER,
                "preview",
                *review07_args,
            ),
            expected_fragment="REVIEW_INDEPENDENCE",
        )
        negative.append(
            "N-REVIEW07_OPERATOR_REVIEWER_INDEPENDENCE_REQUIRED"
        )

        review08_root, review08_path, _ = build_case_arguments(
            repo_root,
            temporary_root,
            "review08",
        )
        review08_record = json.loads(
            review08_path.read_text(encoding="utf-8")
        )
        review08_record["review"]["reviewed_at"] = (
            "2026-07-30T00:00:30Z"
        )
        write_json(review08_path, review08_record)
        review08_args = materializer_arguments(
            review08_root,
            review08_path,
            materialized_at="2026-07-30T00:03:00Z",
        )
        require_failure(
            command(
                review08_root / MATERIALIZER,
                "preview",
                *review08_args,
            ),
            expected_fragment="TIME_ORDER",
        )
        negative.append("N-REVIEW08_TIME_ORDER_REJECTED")

        commit01_root, _, commit01_args = build_case_arguments(
            repo_root,
            temporary_root,
            "commit01",
        )
        require_failure(
            command(
                commit01_root / MATERIALIZER,
                "preview",
                *replace_option(
                    commit01_args,
                    "--expected-base-commitment",
                    "9" * 64,
                ),
            ),
            expected_fragment="BASE_COMMITMENT_PIN_MISMATCH",
        )
        negative.append("N-COMMIT01_BASE_PIN_MISMATCH")

        commit02_root, _, commit02_args = build_case_arguments(
            repo_root,
            temporary_root,
            "commit02",
        )
        require_failure(
            command(
                commit02_root / MATERIALIZER,
                "preview",
                *replace_option(
                    commit02_args,
                    "--expected-candidate-commitment",
                    "9" * 64,
                ),
            ),
            expected_fragment="CANDIDATE_COMMITMENT_PIN_MISMATCH",
        )
        negative.append("N-COMMIT02_CANDIDATE_PIN_MISMATCH")

        commit03_root, commit03_path, _ = build_case_arguments(
            repo_root,
            temporary_root,
            "commit03",
        )
        commit03_record = json.loads(
            commit03_path.read_text(encoding="utf-8")
        )
        commit03_record["base_binding"]["truth_commitment"][
            "commitment"
        ] = commit03_record["candidate_binding"]["truth_commitment"][
            "commitment"
        ]
        refresh_review_input(commit03_record)
        write_json(commit03_path, commit03_record)
        commit03_args = materializer_arguments(
            commit03_root,
            commit03_path,
            materialized_at="2026-07-30T00:03:00Z",
        )
        require_failure(
            command(
                commit03_root / MATERIALIZER,
                "preview",
                *commit03_args,
            ),
            expected_fragment="COMMITMENT_FRESHNESS",
        )
        negative.append("N-COMMIT03_EQUAL_COMMITMENTS_REJECTED")

        commit04_root, commit04_path, _ = build_case_arguments(
            repo_root,
            temporary_root,
            "commit04",
        )
        commit04_manifest_path = commit04_root / CANDIDATE_MANIFEST
        commit04_manifest = json.loads(
            commit04_manifest_path.read_text(encoding="utf-8")
        )
        commit04_manifest["truth_commitment"]["commitment"] = "9" * 64
        write_json(commit04_manifest_path, commit04_manifest)
        commit04_args = materializer_arguments(
            commit04_root,
            commit04_path,
            materialized_at="2026-07-30T00:03:00Z",
        )
        require_failure(
            command(
                commit04_root / MATERIALIZER,
                "preview",
                *commit04_args,
            ),
            expected_fragment=(
                "CANDIDATE_MANIFEST_COMMITMENT_MISMATCH"
            ),
        )
        negative.append(
            "N-COMMIT04_CANDIDATE_MANIFEST_DRIFT_REJECTED"
        )

        bytes01_root, bytes01_path, bytes01_args = (
            build_case_arguments(
                repo_root,
                temporary_root,
                "bytes01",
            )
        )
        bytes01_raw = b"\xef\xbb\xbf" + bytes01_path.read_bytes()
        bytes01_path.write_bytes(bytes01_raw)
        bytes01_args = replace_option(
            bytes01_args,
            "--expected-review-record-sha256",
            sha256_bytes(bytes01_raw),
        )
        require_failure(
            command(
                bytes01_root / MATERIALIZER,
                "preview",
                *bytes01_args,
            ),
            expected_fragment="JSON_BOM",
        )
        negative.append("N-BYTES01_REVIEW_BOM_REJECTED")

        bytes02_root, bytes02_path, bytes02_args = (
            build_case_arguments(
                repo_root,
                temporary_root,
                "bytes02",
            )
        )
        bytes02_raw = bytes02_path.read_bytes().replace(b"\n", b"\r\n")
        bytes02_path.write_bytes(bytes02_raw)
        bytes02_args = replace_option(
            bytes02_args,
            "--expected-review-record-sha256",
            sha256_bytes(bytes02_raw),
        )
        require_failure(
            command(
                bytes02_root / MATERIALIZER,
                "preview",
                *bytes02_args,
            ),
            expected_fragment="JSON_CRLF",
        )
        negative.append("N-BYTES02_REVIEW_CRLF_REJECTED")

        bytes03_root, _, bytes03_args = build_case_arguments(
            repo_root,
            temporary_root,
            "bytes03",
        )
        bytes03_manifest_path = bytes03_root / CANDIDATE_MANIFEST
        bytes03_text = bytes03_manifest_path.read_text(encoding="utf-8")
        bytes03_manifest_path.write_text(
            bytes03_text[:-2] + ',\n  "status": "preparing"\n}\n',
            encoding="utf-8",
            newline="\n",
        )
        require_failure(
            command(
                bytes03_root / MATERIALIZER,
                "preview",
                *bytes03_args,
            ),
            expected_fragment="JSON_DUPLICATE_KEY",
        )
        negative.append(
            "N-BYTES03_CANDIDATE_DUPLICATE_KEY_REJECTED"
        )

        bytes04_root, _, bytes04_args = build_case_arguments(
            repo_root,
            temporary_root,
            "bytes04",
        )
        bytes04_manifest_path = bytes04_root / CANDIDATE_MANIFEST
        bytes04_text = bytes04_manifest_path.read_text(encoding="utf-8")
        bytes04_manifest_path.write_text(
            bytes04_text[:-2] + ',\n  "nonfinite": NaN\n}\n',
            encoding="utf-8",
            newline="\n",
        )
        require_failure(
            command(
                bytes04_root / MATERIALIZER,
                "preview",
                *bytes04_args,
            ),
            expected_fragment="JSON_NONFINITE",
        )
        negative.append("N-BYTES04_CANDIDATE_NONFINITE_REJECTED")

        hostile_root, hostile_path, _ = build_case_arguments(
            repo_root,
            temporary_root,
            "hostile01",
        )
        hostile_marker = temporary_root / "hostile-command.marker"
        hostile_record = json.loads(
            hostile_path.read_text(encoding="utf-8")
        )
        hostile_record["continuity_process"]["command"] = [
            sys.executable,
            "-c",
            (
                "from pathlib import Path;"
                f"Path({str(hostile_marker)!r}).write_text('executed')"
            ),
        ]
        refresh_review_input(hostile_record)
        write_json(hostile_path, hostile_record)
        hostile_args = materializer_arguments(
            hostile_root,
            hostile_path,
            materialized_at="2026-07-30T00:03:00Z",
        )
        require_failure(
            command(
                hostile_root / MATERIALIZER,
                "preview",
                *hostile_args,
            ),
            expected_fragment="SCHEMA_VALIDATION",
        )
        if hostile_marker.exists():
            raise RuntimeError("hostile command metadata was executed")
        negative.append(
            "N-HOSTILE01_COMMAND_METADATA_REJECTED_WITHOUT_EXECUTION"
        )

        valid_verifier_args = verifier_arguments(synthetic_root)
        require_failure(
            command(
                synthetic_root / VERIFIER,
                "verify",
                *without_flag(
                    valid_verifier_args,
                    "--allow-repository-byte-reads",
                ),
            ),
            expected_fragment=(
                "REPOSITORY_BYTE_READS_NOT_ACKNOWLEDGED"
            ),
        )
        negative.append("N-VERIFY01_REPOSITORY_READ_ACK_REQUIRED")

        require_failure(
            command(
                synthetic_root / VERIFIER,
                "verify",
                *replace_option(
                    valid_verifier_args,
                    "--expected-verifier-sha256",
                    "9" * 64,
                ),
            ),
            expected_fragment="VERIFIER_PIN_MISMATCH",
        )
        negative.append("N-VERIFY02_VERIFIER_PIN_MISMATCH")

        original_instance_raw = instance_path.read_bytes()
        verify03_instance = json.loads(original_instance_raw)
        verify03_instance["toolchain"]["materializer"]["sha256"] = (
            "9" * 64
        )
        write_json(instance_path, verify03_instance)
        require_failure(
            command(
                synthetic_root / VERIFIER,
                "verify",
                *valid_verifier_args,
            ),
            expected_fragment="TOOLCHAIN_BINDING_MISMATCH",
        )
        instance_path.write_bytes(original_instance_raw)
        negative.append(
            "N-VERIFY03_INSTANCE_TOOLCHAIN_DRIFT_REJECTED"
        )

        instance_path.write_bytes(
            original_instance_raw.replace(b"\n", b"\r\n")
        )
        require_failure(
            command(
                synthetic_root / VERIFIER,
                "verify",
                *valid_verifier_args,
            ),
            expected_fragment="JSON_CRLF",
        )
        instance_path.write_bytes(original_instance_raw)
        negative.append("N-VERIFY04_INSTANCE_CRLF_REJECTED")

        manifest_path = synthetic_root / CANDIDATE_MANIFEST
        original_manifest_raw = manifest_path.read_bytes()
        verify05_manifest = json.loads(original_manifest_raw)
        verify05_manifest["truth_commitment"]["commitment"] = "9" * 64
        write_json(manifest_path, verify05_manifest)
        require_failure(
            command(
                synthetic_root / VERIFIER,
                "verify",
                *valid_verifier_args,
            ),
            expected_fragment=(
                "CANDIDATE_MANIFEST_COMMITMENT_MISMATCH"
            ),
        )
        manifest_path.write_bytes(original_manifest_raw)
        negative.append(
            "N-VERIFY05_MANIFEST_COMMITMENT_DRIFT_REJECTED"
        )

    if tuple(positive) != EXPECTED_POSITIVE_IDS:
        raise RuntimeError(f"positive control set drifted: {positive!r}")
    if tuple(negative) != EXPECTED_NEGATIVE_IDS:
        raise RuntimeError(f"negative control set drifted: {negative!r}")
    return {
        "formal_comparator_executed": False,
        "formal_input_access": False,
        "formal_runner_executed": False,
        "formal_runner_or_comparator_executed": False,
        "negative_controls": negative,
        "negative_controls_passed": len(negative),
        "positive_controls": positive,
        "positive_controls_passed": len(positive),
        "real_run_bytes_read": False,
        "status": "synthetic_self_test_passed",
        "temporary_repository_only": True,
        "truth_or_nonce_read": False,
        "truth_plaintext_access": False,
        "truth_reveal_performed": False,
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
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
