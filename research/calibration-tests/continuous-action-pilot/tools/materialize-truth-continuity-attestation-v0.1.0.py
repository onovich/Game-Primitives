#!/usr/bin/env python3
"""Preview or exclusively materialize a nonplaintext continuity attestation.

The tool binds caller-pinned commitment metadata and an external canonical
review record. It does not read truth plaintext or a nonce, run a comparator,
perform a reveal, or claim that hidden semantic equivalence has been proven.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
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
SHA256_PATTERN_LENGTH = 64


class AttestationError(RuntimeError):
    """A stable fail-closed materialization error."""

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
        raise AttestationError(
            "CANONICAL_JSON",
            f"value cannot be canonically encoded: {error}",
        ) from error
    return (text + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def require_sha256(name: str, value: str) -> str:
    if (
        len(value) != SHA256_PATTERN_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
        or value == "0" * SHA256_PATTERN_LENGTH
    ):
        raise AttestationError(
            "PIN_FORMAT",
            f"{name} must be a nonzero lowercase SHA-256 digest",
        )
    return value


def reject_constant(value: str) -> None:
    raise AttestationError(
        "JSON_NONFINITE",
        f"non-finite JSON constant is forbidden: {value}",
    )


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AttestationError(
                "JSON_DUPLICATE_KEY",
                f"duplicate JSON key is forbidden: {key}",
            )
        result[key] = value
    return result


def decode_canonical_json(
    raw: bytes,
    *,
    label: str,
) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AttestationError(
            "JSON_BOM",
            f"{label} must be UTF-8 without BOM",
        )
    if b"\r" in raw:
        raise AttestationError(
            "JSON_CRLF",
            f"{label} must use LF line endings",
        )
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise AttestationError(
            "JSON_UTF8",
            f"{label} is not strict UTF-8: {error}",
        ) from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except AttestationError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise AttestationError(
            "JSON_PARSE",
            f"{label} is not valid JSON: {error}",
        ) from error
    if raw != canonical_bytes(value):
        raise AttestationError(
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
        raise AttestationError(
            "REPO_ROOT_LINK",
            "repository root must not be a symlink or junction",
        )
    try:
        root = argument.resolve(strict=True)
    except OSError as error:
        raise AttestationError(
            "REPO_ROOT",
            f"cannot resolve repository root: {error}",
        ) from error
    if not root.is_dir():
        raise AttestationError(
            "REPO_ROOT",
            f"repository root is not a directory: {root}",
        )
    return root


def checked_repo_path(
    root: Path,
    relative: Path,
    *,
    require_file: bool,
    require_parent: bool = False,
) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise AttestationError(
            "FIXED_PATH",
            f"unsafe repository path: {relative}",
        )
    current = root
    parts = relative.parts if not require_parent else relative.parent.parts
    for part in parts:
        try:
            child_names = {child.name for child in current.iterdir()}
        except OSError as error:
            raise AttestationError(
                "REPOSITORY_DIRECTORY_READ",
                f"cannot enumerate fixed path parent: {current}",
            ) from error
        if part not in child_names and any(
            name.casefold() == part.casefold()
            for name in child_names
        ):
            raise AttestationError(
                "REPOSITORY_PATH_CASE",
                f"fixed repository path has case drift: {relative}",
            )
        current = current / part
        if not current.exists():
            if require_parent:
                raise AttestationError(
                    "OUTPUT_PARENT_ABSENT",
                    f"fixed output parent is absent: {relative.parent}",
                )
            raise AttestationError(
                "REPOSITORY_INPUT_ABSENT",
                f"required repository path is absent: {relative}",
            )
        if is_link_like(current):
            raise AttestationError(
                "REPOSITORY_LINK",
                f"symlink or junction is forbidden: {relative}",
            )
    target = root / relative
    if require_file and not target.is_file():
        raise AttestationError(
            "REPOSITORY_INPUT_TYPE",
            f"required repository path is not a file: {relative}",
        )
    try:
        resolved = (
            target.parent.resolve(strict=True) / target.name
            if require_parent and not require_file
            else target.resolve(strict=require_file)
        )
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise AttestationError(
            "REPOSITORY_ESCAPE",
            f"repository path escapes its root: {relative}",
        ) from error
    return target


def checked_external_review_path(root: Path, argument: Path) -> Path:
    if is_link_like(argument):
        raise AttestationError(
            "REVIEW_RECORD_LINK",
            "external review record must not be a symlink or junction",
        )
    try:
        review_path = argument.resolve(strict=True)
    except OSError as error:
        raise AttestationError(
            "REVIEW_RECORD",
            f"cannot resolve external review record: {error}",
        ) from error
    if not review_path.is_file():
        raise AttestationError(
            "REVIEW_RECORD",
            "external review record is not a regular file",
        )
    try:
        review_path.relative_to(root)
    except ValueError:
        return review_path
    raise AttestationError(
        "REVIEW_RECORD_INSIDE_REPOSITORY",
        "review record must be outside the repository",
    )


def read_fixed_file(
    root: Path,
    relative: Path,
) -> tuple[Path, bytes]:
    path = checked_repo_path(root, relative, require_file=True)
    return path, path.read_bytes()


def require_runtime() -> None:
    if sys.flags.isolated != 1:
        raise AttestationError(
            "ISOLATED_RUNTIME_REQUIRED",
            "invoke this tool with python -I",
        )


def require_acknowledgements(args: argparse.Namespace) -> None:
    if not args.allow_repository_byte_reads:
        raise AttestationError(
            "REPOSITORY_BYTE_READS_NOT_ACKNOWLEDGED",
            "pass --allow-repository-byte-reads",
        )
    if not args.allow_external_review_record_byte_read:
        raise AttestationError(
            "EXTERNAL_REVIEW_BYTE_READ_NOT_ACKNOWLEDGED",
            "pass --allow-external-review-record-byte-read",
        )


def parse_utc(name: str, value: str) -> datetime:
    try:
        parsed = datetime.strptime(
            value,
            "%Y-%m-%dT%H:%M:%SZ",
        ).replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise AttestationError(
            "TIME_FORMAT",
            f"{name} must be canonical UTC seconds: {value}",
        ) from error
    return parsed


def schema_validator(
    schema: dict[str, Any],
    *,
    review_record: bool,
) -> Any:
    from jsonschema import Draft202012Validator, FormatChecker

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise AttestationError(
            "SCHEMA_INVALID",
            f"pinned schema is invalid: {error}",
        ) from error
    target = schema
    if review_record:
        target = {
            "$defs": schema["$defs"],
            "$ref": "#/$defs/reviewRecord",
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        }
    return Draft202012Validator(
        target,
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
        raise AttestationError(
            "SCHEMA_VALIDATION",
            f"{label} failed at {location or '<root>'}: {first.message}",
        )


def review_input(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "base_binding": record["base_binding"],
        "candidate_binding": record["candidate_binding"],
        "continuity_process": record["continuity_process"],
    }


def validate_record_semantics(
    record: dict[str, Any],
    *,
    candidate_manifest: dict[str, Any],
    expected_base_commitment: str,
    expected_candidate_commitment: str,
    expected_review_input_sha256: str,
    expected_reviewer_identifier: str,
    expected_reviewer_session_id: str,
    expected_process_artifact_sha256: str,
    materialized_at: str,
) -> str:
    base_commitment = record["base_binding"]["truth_commitment"]
    candidate_commitment = record["candidate_binding"][
        "truth_commitment"
    ]
    if base_commitment["commitment"] != expected_base_commitment:
        raise AttestationError(
            "BASE_COMMITMENT_PIN_MISMATCH",
            "review record base commitment differs from caller pin",
        )
    if candidate_commitment["commitment"] != expected_candidate_commitment:
        raise AttestationError(
            "CANDIDATE_COMMITMENT_PIN_MISMATCH",
            "review record candidate commitment differs from caller pin",
        )
    if expected_base_commitment == expected_candidate_commitment:
        raise AttestationError(
            "COMMITMENT_FRESHNESS",
            "candidate commitment must differ from the base commitment",
        )
    manifest_fields = {
        "artifact_type": candidate_manifest.get("artifact_type"),
        "run_id": candidate_manifest.get("run_id"),
        "schema_version": candidate_manifest.get("schema_version"),
        "status": candidate_manifest.get("status"),
    }
    expected_manifest_fields = {
        "artifact_type": "formal_run_manifest",
        "run_id": "continuous-002",
        "schema_version": "0.1.1",
        "status": "preparing",
    }
    if manifest_fields != expected_manifest_fields:
        raise AttestationError(
            "CANDIDATE_MANIFEST_STATE",
            "candidate manifest is not continuous-002 schema 0.1.1 preparing",
        )
    if candidate_manifest.get("truth_commitment") != candidate_commitment:
        raise AttestationError(
            "CANDIDATE_MANIFEST_COMMITMENT_MISMATCH",
            "candidate manifest commitment differs from review record",
        )
    review = record["review"]
    reviewer = review["reviewer"]
    if reviewer["identifier"] != expected_reviewer_identifier:
        raise AttestationError(
            "REVIEWER_IDENTIFIER_PIN_MISMATCH",
            "reviewer identifier differs from caller pin",
        )
    if reviewer["session_id"] != expected_reviewer_session_id:
        raise AttestationError(
            "REVIEWER_SESSION_PIN_MISMATCH",
            "reviewer session differs from caller pin",
        )
    operator = record["continuity_process"]["operator"]
    if (
        operator["identifier"] == reviewer["identifier"]
        or operator["session_id"] == reviewer["session_id"]
    ):
        raise AttestationError(
            "REVIEW_INDEPENDENCE",
            "operator and reviewer identities/sessions must differ",
        )
    process_digest = record["continuity_process"][
        "process_artifact"
    ]["sha256"]
    if process_digest != expected_process_artifact_sha256:
        raise AttestationError(
            "PROCESS_ARTIFACT_PIN_MISMATCH",
            "process artifact digest differs from caller pin",
        )
    calculated_input_digest = sha256_bytes(
        canonical_bytes(review_input(record))
    )
    if calculated_input_digest != review["input_set_sha256"]:
        raise AttestationError(
            "REVIEW_INPUT_DIGEST_MISMATCH",
            "review record input_set_sha256 does not match its inputs",
        )
    if calculated_input_digest != expected_review_input_sha256:
        raise AttestationError(
            "REVIEW_INPUT_PIN_MISMATCH",
            "review input digest differs from caller pin",
        )
    base_created = parse_utc(
        "base commitment created_at",
        base_commitment["created_at"],
    )
    candidate_created = parse_utc(
        "candidate commitment created_at",
        candidate_commitment["created_at"],
    )
    process_performed = parse_utc(
        "continuity process performed_at",
        record["continuity_process"]["performed_at"],
    )
    reviewed = parse_utc("reviewed_at", review["reviewed_at"])
    materialized = parse_utc("materialized_at", materialized_at)
    if not (
        base_created
        <= candidate_created
        <= process_performed
        <= reviewed
        <= materialized
    ):
        raise AttestationError(
            "TIME_ORDER",
            "commitment, process, review, and materialization times are reversed",
        )
    return calculated_input_digest


def expected_attestation(
    *,
    record: dict[str, Any],
    record_sha256: str,
    review_input_sha256: str,
    schema_sha256: str,
    materializer_sha256: str,
    verifier_sha256: str,
    materialized_at: str,
) -> dict[str, Any]:
    candidate_commitment = record["candidate_binding"][
        "truth_commitment"
    ]["commitment"]
    return {
        "$schema": SCHEMA_URL,
        "artifact_type": "truth_continuity_attestation",
        "artifact_version": "0.1.0",
        "attestation_id": (
            f"tca-{candidate_commitment[:12]}-"
            f"{review_input_sha256[:12]}"
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
        "materialized_at": materialized_at,
        "review_input_sha256": review_input_sha256,
        "review_record": record,
        "review_record_sha256": record_sha256,
        "toolchain": {
            "materializer": {
                "artifact_version": "0.1.0",
                "path": MATERIALIZER_PATH.as_posix(),
                "sha256": materializer_sha256,
            },
            "schema": {
                "artifact_version": "0.1.0",
                "path": SCHEMA_PATH.as_posix(),
                "sha256": schema_sha256,
            },
            "verifier": {
                "artifact_version": "0.1.0",
                "path": VERIFIER_PATH.as_posix(),
                "sha256": verifier_sha256,
            },
        },
    }


def build_attestation(
    root: Path,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], bytes]:
    require_runtime()
    require_acknowledgements(args)
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
    expected_record = require_sha256(
        "expected review record",
        args.expected_review_record_sha256,
    )
    expected_review_input = require_sha256(
        "expected review input",
        args.expected_review_input_sha256,
    )
    expected_base = require_sha256(
        "expected base commitment",
        args.expected_base_commitment,
    )
    expected_candidate = require_sha256(
        "expected candidate commitment",
        args.expected_candidate_commitment,
    )
    expected_process = require_sha256(
        "expected process artifact",
        args.expected_process_artifact_sha256,
    )

    materializer_path, materializer_raw = read_fixed_file(
        root,
        MATERIALIZER_PATH,
    )
    try:
        invoked_path = Path(__file__).resolve(strict=True)
        expected_invoked_path = materializer_path.resolve(strict=True)
    except OSError as error:
        raise AttestationError(
            "RUNTIME_WRAPPER_BINDING",
            f"cannot resolve materializer wrapper: {error}",
        ) from error
    if invoked_path != expected_invoked_path:
        raise AttestationError(
            "RUNTIME_WRAPPER_BINDING",
            "invoked materializer is not the fixed repository materializer",
        )
    if sha256_bytes(materializer_raw) != expected_materializer:
        raise AttestationError(
            "MATERIALIZER_PIN_MISMATCH",
            "materializer bytes differ from caller pin",
        )

    _, schema_raw = read_fixed_file(root, SCHEMA_PATH)
    if sha256_bytes(schema_raw) != expected_schema:
        raise AttestationError(
            "SCHEMA_PIN_MISMATCH",
            "schema bytes differ from caller pin",
        )
    schema = decode_canonical_json(schema_raw, label="schema")
    if not isinstance(schema, dict):
        raise AttestationError(
            "SCHEMA_TYPE",
            "schema root must be an object",
        )

    _, verifier_raw = read_fixed_file(root, VERIFIER_PATH)
    if sha256_bytes(verifier_raw) != expected_verifier:
        raise AttestationError(
            "VERIFIER_PIN_MISMATCH",
            "verifier bytes differ from caller pin",
        )

    review_path = checked_external_review_path(root, args.review_record)
    review_raw = review_path.read_bytes()
    if sha256_bytes(review_raw) != expected_record:
        raise AttestationError(
            "REVIEW_RECORD_PIN_MISMATCH",
            "external review record bytes differ from caller pin",
        )
    record = decode_canonical_json(
        review_raw,
        label="external review record",
    )
    if not isinstance(record, dict):
        raise AttestationError(
            "REVIEW_RECORD_TYPE",
            "external review record root must be an object",
        )
    validate_document(
        schema_validator(schema, review_record=True),
        record,
        label="external review record",
    )

    _, manifest_raw = read_fixed_file(root, CANDIDATE_MANIFEST_PATH)
    candidate_manifest = decode_canonical_json(
        manifest_raw,
        label="candidate manifest",
    )
    if not isinstance(candidate_manifest, dict):
        raise AttestationError(
            "CANDIDATE_MANIFEST_TYPE",
            "candidate manifest root must be an object",
        )
    calculated_review_input = validate_record_semantics(
        record,
        candidate_manifest=candidate_manifest,
        expected_base_commitment=expected_base,
        expected_candidate_commitment=expected_candidate,
        expected_review_input_sha256=expected_review_input,
        expected_reviewer_identifier=args.expected_reviewer_identifier,
        expected_reviewer_session_id=args.expected_reviewer_session_id,
        expected_process_artifact_sha256=expected_process,
        materialized_at=args.materialized_at,
    )
    attestation = expected_attestation(
        record=record,
        record_sha256=expected_record,
        review_input_sha256=calculated_review_input,
        schema_sha256=expected_schema,
        materializer_sha256=expected_materializer,
        verifier_sha256=expected_verifier,
        materialized_at=args.materialized_at,
    )
    validate_document(
        schema_validator(schema, review_record=False),
        attestation,
        label="attestation",
    )
    return attestation, canonical_bytes(attestation)


def write_exclusive(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise AttestationError(
            "OUTPUT_EXISTS",
            f"refusing to overwrite fixed instance: {INSTANCE_PATH}",
        )
    descriptor = -1
    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary_name, path)
        if path.read_bytes() != raw:
            try:
                if os.path.samefile(temporary_name, path):
                    path.unlink()
            except OSError:
                pass
            raise AttestationError(
                "OUTPUT_READBACK",
                "exclusive publication readback differs",
            )
    except FileExistsError as error:
        raise AttestationError(
            "OUTPUT_EXISTS",
            f"refusing to overwrite fixed instance: {INSTANCE_PATH}",
        ) from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_name is not None:
            try:
                Path(temporary_name).unlink()
            except FileNotFoundError:
                pass


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--review-record", required=True, type=Path)
    parser.add_argument("--materialized-at", required=True)
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
    parser.add_argument(
        "--allow-external-review-record-byte-read",
        action="store_true",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    preview = commands.add_parser("preview")
    add_common_arguments(preview)
    materialize = commands.add_parser("materialize")
    add_common_arguments(materialize)
    materialize.add_argument("--write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        root = checked_repo_root(args.repo_root)
        attestation, raw = build_attestation(root, args)
        output = checked_repo_path(
            root,
            INSTANCE_PATH,
            require_file=False,
            require_parent=True,
        )
        if args.command == "preview":
            status = "previewed_nonplaintext"
        else:
            if not args.write:
                raise AttestationError(
                    "WRITE_FLAG_REQUIRED",
                    "materialize requires the explicit --write flag",
                )
            write_exclusive(output, raw)
            status = "materialized_nonplaintext"
        print(
            json.dumps(
                {
                    "attestation_id": attestation["attestation_id"],
                    "attestation_sha256": sha256_bytes(raw),
                    "formal_comparator_executed": False,
                    "formal_runner_executed": False,
                    "instance_path": INSTANCE_PATH.as_posix(),
                    "plaintext_read": False,
                    "status": status,
                    "truth_or_nonce_read": False,
                    "truth_reveal_performed": False,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (
        AttestationError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        message = (
            str(error)
            if isinstance(error, AttestationError)
            else f"MATERIALIZE_INPUT: {error}"
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
