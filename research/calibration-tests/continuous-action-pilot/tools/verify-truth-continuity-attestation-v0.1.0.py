#!/usr/bin/env python3
"""Read-only verifier for truth-continuity-attestation 0.1.0.

The verifier recomputes canonical hashes and metadata bindings only. It never
opens hidden truth/nonce files, runs a comparator, performs a reveal, or turns
the attestation into proof of hidden plaintext semantic equivalence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA_PATH = PILOT / (
    "schema/truth-continuity-attestation-0.1.0.schema.json"
)
MATERIALIZER_PATH = PILOT / (
    "tools/materialize-truth-continuity-attestation-v0.1.0.py"
)
VERIFIER_PATH = PILOT / (
    "tools/verify-truth-continuity-attestation-v0.1.0.py"
)
CANDIDATE_MANIFEST_PATH = PILOT / "runs/continuous-002/manifest.json"
INSTANCE_PATH = PILOT / (
    "runs/continuous-002/source/"
    "truth-continuity-attestation-v0.1.0.json"
)
SCHEMA_URL = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    f"{SCHEMA_PATH.as_posix()}"
)


class VerificationError(RuntimeError):
    """A stable fail-closed verification error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise VerificationError(
            "CANONICAL_JSON",
            f"value cannot be canonically encoded: {error}",
        ) from error
    return (text + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha256(name: str, value: str) -> str:
    if (
        len(value) != 64
        or any(
            character not in "0123456789abcdef"
            for character in value
        )
        or value == "0" * 64
    ):
        raise VerificationError(
            "PIN_FORMAT",
            f"{name} must be a nonzero lowercase SHA-256 digest",
        )
    return value


def reject_constant(value: str) -> None:
    raise VerificationError(
        "JSON_NONFINITE",
        f"non-finite JSON constant is forbidden: {value}",
    )


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(
                "JSON_DUPLICATE_KEY",
                f"duplicate JSON key is forbidden: {key}",
            )
        result[key] = value
    return result


def decode_canonical_json(raw: bytes, *, label: str) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise VerificationError(
            "JSON_BOM",
            f"{label} must be UTF-8 without BOM",
        )
    if b"\r" in raw:
        raise VerificationError(
            "JSON_CRLF",
            f"{label} must use LF line endings",
        )
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise VerificationError(
            "JSON_UTF8",
            f"{label} is not strict UTF-8: {error}",
        ) from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except VerificationError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise VerificationError(
            "JSON_PARSE",
            f"{label} is not valid JSON: {error}",
        ) from error
    if raw != canonical_bytes(value):
        raise VerificationError(
            "JSON_NONCANONICAL",
            f"{label} is not canonical JSON",
        )
    return value


def is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    junction = getattr(os.path, "isjunction", None)
    return bool(junction(path)) if junction is not None else False


def checked_repo_root(argument: Path) -> Path:
    if is_link_like(argument):
        raise VerificationError(
            "REPO_ROOT_LINK",
            "repository root must not be a symlink or junction",
        )
    try:
        root = argument.resolve(strict=True)
    except OSError as error:
        raise VerificationError(
            "REPO_ROOT",
            f"cannot resolve repository root: {error}",
        ) from error
    if not root.is_dir():
        raise VerificationError(
            "REPO_ROOT",
            f"repository root is not a directory: {root}",
        )
    return root


def read_fixed_file(
    root: Path,
    relative: Path,
) -> tuple[Path, bytes]:
    if relative.is_absolute() or ".." in relative.parts:
        raise VerificationError(
            "FIXED_PATH",
            f"unsafe repository path: {relative}",
        )
    current = root
    for part in relative.parts:
        try:
            child_names = {child.name for child in current.iterdir()}
        except OSError as error:
            raise VerificationError(
                "REPOSITORY_DIRECTORY_READ",
                f"cannot enumerate fixed path parent: {current}",
            ) from error
        if part not in child_names and any(
            name.casefold() == part.casefold()
            for name in child_names
        ):
            raise VerificationError(
                "REPOSITORY_PATH_CASE",
                f"fixed repository path has case drift: {relative}",
            )
        current = current / part
        if not current.exists():
            raise VerificationError(
                "REPOSITORY_INPUT_ABSENT",
                f"required repository path is absent: {relative}",
            )
        if is_link_like(current):
            raise VerificationError(
                "REPOSITORY_LINK",
                f"symlink or junction is forbidden: {relative}",
            )
    if not current.is_file():
        raise VerificationError(
            "REPOSITORY_INPUT_TYPE",
            f"required repository path is not a file: {relative}",
        )
    try:
        current.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as error:
        raise VerificationError(
            "REPOSITORY_ESCAPE",
            f"repository path escapes its root: {relative}",
        ) from error
    return current, current.read_bytes()


def require_runtime(args: argparse.Namespace) -> None:
    if sys.flags.isolated != 1:
        raise VerificationError(
            "ISOLATED_RUNTIME_REQUIRED",
            "invoke this tool with python -I",
        )
    if not args.allow_repository_byte_reads:
        raise VerificationError(
            "REPOSITORY_BYTE_READS_NOT_ACKNOWLEDGED",
            "pass --allow-repository-byte-reads",
        )


def parse_utc(name: str, value: str) -> datetime:
    try:
        return datetime.strptime(
            value,
            "%Y-%m-%dT%H:%M:%SZ",
        ).replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise VerificationError(
            "TIME_FORMAT",
            f"{name} must be canonical UTC seconds: {value}",
        ) from error


def schema_validator(schema: dict[str, Any]) -> Any:
    from jsonschema import Draft202012Validator, FormatChecker

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise VerificationError(
            "SCHEMA_INVALID",
            f"pinned schema is invalid: {error}",
        ) from error
    return Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )


def validate_document(
    validator: Any,
    value: Any,
    *,
    label: str,
) -> None:
    errors = sorted(
        validator.iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path)
        raise VerificationError(
            "SCHEMA_VALIDATION",
            f"{label} failed at {location or '<root>'}: {first.message}",
        )


def review_input(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "base_binding": record["base_binding"],
        "candidate_binding": record["candidate_binding"],
        "continuity_process": record["continuity_process"],
    }


def verify_semantics(
    instance: dict[str, Any],
    manifest: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    record = instance["review_record"]
    base = record["base_binding"]["truth_commitment"]
    candidate = record["candidate_binding"]["truth_commitment"]
    expected_base = require_sha256(
        "expected base commitment",
        args.expected_base_commitment,
    )
    expected_candidate = require_sha256(
        "expected candidate commitment",
        args.expected_candidate_commitment,
    )
    if base["commitment"] != expected_base:
        raise VerificationError(
            "BASE_COMMITMENT_PIN_MISMATCH",
            "base commitment differs from caller pin",
        )
    if candidate["commitment"] != expected_candidate:
        raise VerificationError(
            "CANDIDATE_COMMITMENT_PIN_MISMATCH",
            "candidate commitment differs from caller pin",
        )
    if expected_base == expected_candidate:
        raise VerificationError(
            "COMMITMENT_FRESHNESS",
            "candidate commitment must differ from the base commitment",
        )
    expected_manifest_fields = {
        "artifact_type": "formal_run_manifest",
        "run_id": "continuous-002",
        "schema_version": "0.1.1",
        "status": "preparing",
    }
    actual_manifest_fields = {
        key: manifest.get(key) for key in expected_manifest_fields
    }
    if actual_manifest_fields != expected_manifest_fields:
        raise VerificationError(
            "CANDIDATE_MANIFEST_STATE",
            "candidate manifest is not continuous-002 schema 0.1.1 preparing",
        )
    if manifest.get("truth_commitment") != candidate:
        raise VerificationError(
            "CANDIDATE_MANIFEST_COMMITMENT_MISMATCH",
            "candidate manifest commitment differs from attestation",
        )

    calculated_record_digest = sha256_bytes(canonical_bytes(record))
    if calculated_record_digest != require_sha256(
        "expected review record",
        args.expected_review_record_sha256,
    ):
        raise VerificationError(
            "REVIEW_RECORD_PIN_MISMATCH",
            "embedded review record differs from caller pin",
        )
    if calculated_record_digest != instance["review_record_sha256"]:
        raise VerificationError(
            "REVIEW_RECORD_DIGEST_MISMATCH",
            "embedded review record digest does not recompute",
        )
    calculated_input_digest = sha256_bytes(
        canonical_bytes(review_input(record))
    )
    expected_input = require_sha256(
        "expected review input",
        args.expected_review_input_sha256,
    )
    if calculated_input_digest != expected_input:
        raise VerificationError(
            "REVIEW_INPUT_PIN_MISMATCH",
            "review input differs from caller pin",
        )
    if (
        calculated_input_digest != instance["review_input_sha256"]
        or calculated_input_digest
        != record["review"]["input_set_sha256"]
    ):
        raise VerificationError(
            "REVIEW_INPUT_DIGEST_MISMATCH",
            "review input digest does not recompute",
        )
    reviewer = record["review"]["reviewer"]
    if reviewer["identifier"] != args.expected_reviewer_identifier:
        raise VerificationError(
            "REVIEWER_IDENTIFIER_PIN_MISMATCH",
            "reviewer identifier differs from caller pin",
        )
    if reviewer["session_id"] != args.expected_reviewer_session_id:
        raise VerificationError(
            "REVIEWER_SESSION_PIN_MISMATCH",
            "reviewer session differs from caller pin",
        )
    operator = record["continuity_process"]["operator"]
    if (
        operator["identifier"] == reviewer["identifier"]
        or operator["session_id"] == reviewer["session_id"]
    ):
        raise VerificationError(
            "REVIEW_INDEPENDENCE",
            "operator and reviewer identities/sessions must differ",
        )
    expected_process = require_sha256(
        "expected process artifact",
        args.expected_process_artifact_sha256,
    )
    if (
        record["continuity_process"]["process_artifact"]["sha256"]
        != expected_process
    ):
        raise VerificationError(
            "PROCESS_ARTIFACT_PIN_MISMATCH",
            "process artifact differs from caller pin",
        )
    if instance["attestation_id"] != (
        f"tca-{expected_candidate[:12]}-{calculated_input_digest[:12]}"
    ):
        raise VerificationError(
            "ATTESTATION_ID",
            "attestation identifier does not recompute",
        )

    base_created = parse_utc("base created_at", base["created_at"])
    candidate_created = parse_utc(
        "candidate created_at",
        candidate["created_at"],
    )
    process_performed = parse_utc(
        "process performed_at",
        record["continuity_process"]["performed_at"],
    )
    reviewed = parse_utc(
        "reviewed_at",
        record["review"]["reviewed_at"],
    )
    materialized = parse_utc(
        "materialized_at",
        instance["materialized_at"],
    )
    if not (
        base_created
        <= candidate_created
        <= process_performed
        <= reviewed
        <= materialized
    ):
        raise VerificationError(
            "TIME_ORDER",
            "commitment, process, review, and materialization times are reversed",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--expected-schema-sha256", required=True)
    parser.add_argument("--expected-materializer-sha256", required=True)
    parser.add_argument("--expected-verifier-sha256", required=True)
    parser.add_argument("--expected-base-commitment", required=True)
    parser.add_argument("--expected-candidate-commitment", required=True)
    parser.add_argument("--expected-review-record-sha256", required=True)
    parser.add_argument("--expected-review-input-sha256", required=True)
    parser.add_argument("--expected-reviewer-identifier", required=True)
    parser.add_argument("--expected-reviewer-session-id", required=True)
    parser.add_argument("--expected-process-artifact-sha256", required=True)
    parser.add_argument(
        "--allow-repository-byte-reads",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        require_runtime(args)
        root = checked_repo_root(args.repo_root)
        expected_schema = require_sha256(
            "expected schema",
            args.expected_schema_sha256,
        )
        expected_materializer = require_sha256(
            "expected materializer",
            args.expected_materializer_sha256,
        )
        expected_verifier = require_sha256(
            "expected verifier",
            args.expected_verifier_sha256,
        )

        verifier_path, verifier_raw = read_fixed_file(
            root,
            VERIFIER_PATH,
        )
        try:
            invoked = Path(__file__).resolve(strict=True)
            expected_invoked = verifier_path.resolve(strict=True)
        except OSError as error:
            raise VerificationError(
                "RUNTIME_WRAPPER_BINDING",
                f"cannot resolve verifier wrapper: {error}",
            ) from error
        if invoked != expected_invoked:
            raise VerificationError(
                "RUNTIME_WRAPPER_BINDING",
                "invoked verifier is not the fixed repository verifier",
            )
        if sha256_bytes(verifier_raw) != expected_verifier:
            raise VerificationError(
                "VERIFIER_PIN_MISMATCH",
                "verifier bytes differ from caller pin",
            )

        _, schema_raw = read_fixed_file(root, SCHEMA_PATH)
        if sha256_bytes(schema_raw) != expected_schema:
            raise VerificationError(
                "SCHEMA_PIN_MISMATCH",
                "schema bytes differ from caller pin",
            )
        schema = decode_canonical_json(schema_raw, label="schema")
        if not isinstance(schema, dict):
            raise VerificationError(
                "SCHEMA_TYPE",
                "schema root must be an object",
            )

        _, instance_raw = read_fixed_file(root, INSTANCE_PATH)
        instance = decode_canonical_json(
            instance_raw,
            label="attestation",
        )
        if not isinstance(instance, dict):
            raise VerificationError(
                "ATTESTATION_TYPE",
                "attestation root must be an object",
            )
        validate_document(
            schema_validator(schema),
            instance,
            label="attestation",
        )

        toolchain = instance["toolchain"]
        expected_toolchain_hashes = {
            "schema": expected_schema,
            "materializer": expected_materializer,
            "verifier": expected_verifier,
        }
        for role, digest in expected_toolchain_hashes.items():
            if toolchain[role]["sha256"] != digest:
                raise VerificationError(
                    "TOOLCHAIN_BINDING_MISMATCH",
                    f"attestation {role} hash differs from caller pin",
                )

        _, manifest_raw = read_fixed_file(
            root,
            CANDIDATE_MANIFEST_PATH,
        )
        manifest = decode_canonical_json(
            manifest_raw,
            label="candidate manifest",
        )
        if not isinstance(manifest, dict):
            raise VerificationError(
                "CANDIDATE_MANIFEST_TYPE",
                "candidate manifest root must be an object",
            )
        verify_semantics(instance, manifest, args)

        print(
            json.dumps(
                {
                    "attestation_id": instance["attestation_id"],
                    "attestation_sha256": sha256_bytes(instance_raw),
                    "formal_comparator_executed": False,
                    "formal_runner_executed": False,
                    "instance_path": INSTANCE_PATH.as_posix(),
                    "plaintext_read": False,
                    "status": "verified_nonplaintext",
                    "truth_or_nonce_read": False,
                    "truth_reveal_performed": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (
        VerificationError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        message = (
            str(error)
            if isinstance(error, VerificationError)
            else f"VERIFY_INPUT: {error}"
        )
        print(
            json.dumps(
                {
                    "error": message,
                    "formal_comparator_executed": False,
                    "formal_runner_executed": False,
                    "status": "failed_closed",
                    "truth_or_nonce_read": False,
                    "truth_reveal_performed": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
