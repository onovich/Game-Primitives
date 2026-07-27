#!/usr/bin/env python3
"""Create and verify a sealed-truth commitment without persisting either secret.

The commitment is SHA-256(secret nonce bytes || exact sealed-truth.json bytes).
Only ``update-manifest --write`` mutates a file.  Every command rejects a truth
bundle or nonce whose resolved path is inside the repository.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


BASE = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA_DIR = BASE / "schema"
TRUTH_SCHEMA_NAME = "truth-reveal-0.1.0.schema.json"
MANIFEST_SCHEMA_NAME = "run-manifest-0.1.1.schema.json"
MANIFEST_BASE_SCHEMA_NAME = "run-manifest-0.1.0.schema.json"
TRUTH_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "truth-reveal-0.1.0.schema.json"
)
MANIFEST_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "run-manifest-0.1.1.schema.json"
)
TRUSTED_SCHEMA_SHA256 = {
    TRUTH_SCHEMA_NAME: "b28c141a64f16a2a14406753d0a690a021ff95230af0d8e6151b698193746323",
    MANIFEST_SCHEMA_NAME: "21996046a40a31f2061d3b6a271588c5dd0cf402d3061018cca8301b233d814f",
    MANIFEST_BASE_SCHEMA_NAME: "367f890f52e56d06d8ef4dadbffdcd3d85946f12eff40c47e83373b44b3e7160",
}


class CommitmentError(ValueError):
    """A fail-closed commitment validation error."""


class StrictJsonError(ValueError):
    """Internal marker for duplicate keys or non-finite JSON constants."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json_bytes(raw: bytes, code: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CommitmentError(f"{code}:invalid_utf8") from exc

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise StrictJsonError("duplicate_key")
            result[key] = value
        return result

    def reject_constant(_: str) -> Any:
        raise StrictJsonError("non_finite_number")

    try:
        return json.loads(
            text,
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, StrictJsonError) as exc:
        raise CommitmentError(f"{code}:invalid_json") from exc


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_repo_file(repo_root: Path, value: Path) -> Path:
    repo_root = repo_root.resolve()
    candidate = value if value.is_absolute() else repo_root / value
    candidate = candidate.resolve()
    if not is_within(candidate, repo_root):
        raise CommitmentError(f"repository file escapes repository root: {value}")
    if not candidate.is_file():
        raise CommitmentError(f"repository file does not exist: {value}")
    return candidate


def resolve_external_secret(repo_root: Path, value: Path, label: str) -> Path:
    repo_root = repo_root.resolve()
    candidate = value.resolve()
    if is_within(candidate, repo_root):
        raise CommitmentError(f"{label} must be outside the repository")
    if not candidate.is_file():
        raise CommitmentError(f"{label} does not exist")
    return candidate


def load_registry(schema_dir: Path) -> tuple[Registry, dict[str, dict[str, Any]]]:
    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    for schema_name, trusted_hash in TRUSTED_SCHEMA_SHA256.items():
        schema_path = schema_dir / schema_name
        try:
            raw = schema_path.read_bytes()
        except OSError as exc:
            raise CommitmentError(
                f"trusted_schema_missing:{schema_name}"
            ) from exc
        if sha256_bytes(raw) != trusted_hash:
            raise CommitmentError(
                f"trusted_schema_hash_mismatch:{schema_name}"
            )
        schema = strict_json_bytes(raw, f"schema_json:{schema_name}")
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            if schema_id in schemas:
                raise CommitmentError(f"duplicate schema id: {schema_id}")
            schemas[schema_id] = schema
            registry = registry.with_resource(
                schema_id,
                Resource.from_contents(schema),
            )
    return registry, schemas


def schema_property_names(schema: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(schema, dict):
        properties = schema.get("properties")
        if isinstance(properties, dict):
            names.update(str(key) for key in properties)
        for value in schema.values():
            names.update(schema_property_names(value))
    elif isinstance(schema, list):
        for value in schema:
            names.update(schema_property_names(value))
    return names


def safe_json_pointer(parts: Any, allowed_names: set[str]) -> str:
    encoded: list[str] = []
    for part in parts:
        if isinstance(part, int):
            token = str(part)
        elif isinstance(part, str) and part in allowed_names:
            token = part
        else:
            token = "~redacted~"
        encoded.append(token.replace("~", "~0").replace("/", "~1"))
    return "/" + "/".join(encoded) if encoded else ""


def validation_diagnostics(
    document: Any,
    schema: dict[str, Any],
    registry: Registry,
) -> list[str]:
    allowed_names = schema_property_names(schema)
    errors = sorted(
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(document),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    diagnostics: list[str] = []
    for error in errors:
        validator = str(error.validator)
        if not re.fullmatch(r"[A-Za-z0-9_$.-]+", validator):
            validator = "unknown"
        pointer = safe_json_pointer(error.absolute_path, allowed_names)
        diagnostics.append(
            f"schema_validation_failed|pointer={pointer}|validator={validator}"
        )
    return diagnostics


def load_and_validate_truth(
    repo_root: Path,
    truth_path: Path,
    schema_dir: Path,
) -> tuple[dict[str, Any], bytes]:
    resolved = resolve_external_secret(repo_root, truth_path, "sealed truth")
    if resolved.name != "sealed-truth.json":
        raise CommitmentError("sealed truth filename must be exactly sealed-truth.json")
    try:
        exact_bytes = resolved.read_bytes()
    except OSError as exc:
        raise CommitmentError("sealed_truth_read_failed") from exc
    if not exact_bytes:
        raise CommitmentError("sealed truth must not be empty")
    document = strict_json_bytes(exact_bytes, "sealed_truth_json")
    if not isinstance(document, dict):
        raise CommitmentError("sealed truth root must be an object")

    registry, schemas = load_registry(schema_dir)
    root_schema = schemas.get(TRUTH_SCHEMA_ID)
    if root_schema is None:
        raise CommitmentError("truth-reveal schema is absent from the schema registry")
    sealed_only_schema = {
        "$schema": root_schema["$schema"],
        "$defs": root_schema["$defs"],
        "$ref": "#/$defs/sealedTruth",
    }
    messages = validation_diagnostics(document, sealed_only_schema, registry)
    if messages:
        raise CommitmentError(
            "sealed_truth_schema_invalid:\n"
            + "\n".join(messages[:12])
        )
    if document.get("$schema") != TRUTH_SCHEMA_ID:
        raise CommitmentError("sealed truth declares an unexpected $schema")
    return document, exact_bytes


def read_nonce(repo_root: Path, nonce_path: Path) -> bytes:
    resolved = resolve_external_secret(repo_root, nonce_path, "secret nonce")
    try:
        nonce = resolved.read_bytes()
    except OSError as exc:
        raise CommitmentError("secret_nonce_read_failed") from exc
    if len(nonce) != 32:
        raise CommitmentError(
            f"secret nonce must contain exactly 32 bytes, found {len(nonce)}"
        )
    return nonce


def validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CommitmentError(f"created-at is not an RFC 3339 date-time: {value}") from exc
    if parsed.tzinfo is None:
        raise CommitmentError("created-at must include a timezone")


def build_commitment(
    truth_bytes: bytes,
    nonce: bytes,
    created_at: str,
) -> dict[str, Any]:
    validate_timestamp(created_at)
    return {
        "algorithm": "SHA-256",
        "combination": "secret_nonce_bytes || exact_truth_bundle_bytes",
        "commitment": sha256_bytes(nonce + truth_bytes),
        "created_at": created_at,
        "nonce_length_bytes": 32,
        "truth_bundle_bytes": len(truth_bytes),
        "truth_bundle_name": "sealed-truth.json",
    }


def load_and_validate_manifest(
    repo_root: Path,
    manifest_path: Path,
    schema_dir: Path,
) -> tuple[Path, dict[str, Any], bytes]:
    resolved = resolve_repo_file(repo_root, manifest_path)
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise CommitmentError("manifest_read_failed") from exc
    manifest = strict_json_bytes(raw, "manifest_json")
    registry, schemas = load_registry(schema_dir)
    schema = schemas.get(MANIFEST_SCHEMA_ID)
    if schema is None:
        raise CommitmentError("run manifest schema is absent from the schema registry")
    messages = validation_diagnostics(manifest, schema, registry)
    if messages:
        raise CommitmentError(
            "manifest_schema_invalid:\n" + "\n".join(messages[:12])
        )
    return resolved, manifest, raw


def validate_secret_binding(
    manifest: dict[str, Any],
    truth: dict[str, Any],
) -> None:
    if manifest.get("run_id") != truth.get("run_id"):
        raise CommitmentError(
            "sealed truth run_id does not match the target manifest run_id"
        )


def calculate(
    repo_root: Path,
    manifest_path: Path,
    truth_path: Path,
    nonce_path: Path,
    created_at: str,
    schema_dir: Path,
) -> tuple[Path, dict[str, Any], bytes, dict[str, Any]]:
    resolved_manifest, manifest, manifest_bytes = load_and_validate_manifest(
        repo_root, manifest_path, schema_dir
    )
    truth, truth_bytes = load_and_validate_truth(repo_root, truth_path, schema_dir)
    nonce = read_nonce(repo_root, nonce_path)
    validate_secret_binding(manifest, truth)
    return resolved_manifest, manifest, manifest_bytes, build_commitment(
        truth_bytes,
        nonce,
        created_at,
    )


def atomic_write(path: Path, content: bytes) -> None:
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
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def update_manifest(
    repo_root: Path,
    manifest_path: Path,
    truth_path: Path,
    nonce_path: Path,
    created_at: str,
    schema_dir: Path,
    *,
    before_cas: Callable[[], None] | None = None,
) -> dict[str, Any]:
    resolved, manifest, initial_manifest_bytes, commitment = calculate(
        repo_root,
        manifest_path,
        truth_path,
        nonce_path,
        created_at,
        schema_dir,
    )
    if manifest.get("status") != "preparing":
        raise CommitmentError("refusing to update a manifest whose status is not preparing")
    if manifest.get("freeze_commit") is not None:
        raise CommitmentError("refusing to update a manifest with a freeze_commit")
    if manifest.get("frozen_artifact_set_digest") is not None:
        raise CommitmentError(
            "refusing to update a manifest with a frozen artifact set digest"
        )
    if manifest.get("stage_digests") != []:
        raise CommitmentError("refusing to update a manifest with stage digests")
    if any(entry.get("included_in_frozen_set") for entry in manifest["artifacts"]):
        raise CommitmentError(
            "refusing to add a truth commitment after frozen-set membership began"
        )

    existing = manifest.get("truth_commitment")
    if existing is not None:
        comparable_fields = (
            "algorithm",
            "combination",
            "commitment",
            "nonce_length_bytes",
            "truth_bundle_bytes",
            "truth_bundle_name",
        )
        if any(existing.get(key) != commitment[key] for key in comparable_fields):
            raise CommitmentError("refusing to overwrite a different truth commitment")
        return {
            "commitment": existing["commitment"],
            "manifest_sha256": sha256_bytes(resolved.read_bytes()),
            "status": "unchanged",
        }

    manifest["truth_commitment"] = commitment
    manifest["updated_at"] = created_at
    registry, schemas = load_registry(schema_dir)
    messages = validation_diagnostics(
        manifest,
        schemas[MANIFEST_SCHEMA_ID],
        registry,
    )
    if messages:
        raise CommitmentError(
            "updated_manifest_schema_invalid:\n" + "\n".join(messages[:12])
        )
    output = canonical_bytes(manifest)
    if before_cas is not None:
        before_cas()
    try:
        current_manifest_bytes = resolved.read_bytes()
    except OSError as exc:
        raise CommitmentError("manifest_cas_read_failed") from exc
    if current_manifest_bytes != initial_manifest_bytes:
        raise CommitmentError("manifest_cas_conflict")
    atomic_write(resolved, output)
    return {
        "commitment": commitment["commitment"],
        "manifest_sha256": sha256_bytes(output),
        "status": "written",
    }


def verify_commitment(
    repo_root: Path,
    manifest_path: Path,
    truth_path: Path,
    nonce_path: Path,
    schema_dir: Path,
) -> dict[str, Any]:
    _, manifest, _ = load_and_validate_manifest(
        repo_root, manifest_path, schema_dir
    )
    truth, truth_bytes = load_and_validate_truth(repo_root, truth_path, schema_dir)
    nonce = read_nonce(repo_root, nonce_path)
    validate_secret_binding(manifest, truth)
    existing = manifest.get("truth_commitment")
    if existing is None:
        raise CommitmentError("manifest has no truth commitment")
    recomputed = sha256_bytes(nonce + truth_bytes)
    expected_fields = {
        "algorithm": "SHA-256",
        "combination": "secret_nonce_bytes || exact_truth_bundle_bytes",
        "commitment": recomputed,
        "nonce_length_bytes": 32,
        "truth_bundle_bytes": len(truth_bytes),
        "truth_bundle_name": "sealed-truth.json",
    }
    mismatches = [
        key for key, expected in expected_fields.items() if existing.get(key) != expected
    ]
    if mismatches:
        raise CommitmentError(
            "truth commitment verification failed for: " + ", ".join(mismatches)
        )
    return {
        "commitment": recomputed,
        "run_id": manifest["run_id"],
        "status": "passed",
    }


def sample_truth(run_id: str) -> dict[str, Any]:
    zero = "0" * 64
    return {
        "$schema": TRUTH_SCHEMA_ID,
        "alias_witnesses": [],
        "artifact_type": "sealed_truth",
        "artifact_version": "0.1.0",
        "case_truths": [
            {
                "alias_witness_ids": [],
                "case_id": "NEG-01",
                "expected_observations": [
                    {
                        "comparison": "status",
                        "configuration_id": "negative-control",
                        "observation_id": "status",
                        "tolerance_rule_id": None,
                        "value": {
                            "serialized_value": "rejected",
                            "unit": None,
                            "value_type": "status",
                        },
                    }
                ],
                "expected_prediction_status": "determinate",
                "required_reconstruction_facts": [],
            }
        ],
        "condition_mapping": [
            {"condition_id": "condition-v01", "view_kind": "atomic_projection"},
            {"condition_id": "condition-v02", "view_kind": "blind_rich_view"},
        ],
        "created_at": "2026-07-27T00:00:00Z",
        "hard_condition_rules": [
            {
                "condition_id": f"CA-H0{index}",
                "failure_effect": (
                    "core_claim_refuted" if index == 1 else "inconclusive"
                ),
                "requirement": f"temporary self-test condition {index}",
            }
            for index in range(1, 5)
        ],
        "input_artifacts": [
            {"artifact_id": "temporary-input", "sha256": zero}
        ],
        "projection_spec_sha256": zero,
        "protocol_version": "0.1.0",
        "run_id": run_id,
    }


def sample_manifest(run_id: str) -> dict[str, Any]:
    timestamp = "2026-07-27T00:00:00Z"
    return {
        "$schema": MANIFEST_SCHEMA_ID,
        "artifact_type": "formal_run_manifest",
        "artifact_version": "0.1.1",
        "artifacts": [],
        "created_at": timestamp,
        "freeze_commit": None,
        "frozen_artifact_set_digest": None,
        "protocol_version": "0.1.0",
        "run_id": run_id,
        "schema_version": "0.1.1",
        "stage": "preparation",
        "stage_digests": [],
        "status": "preparing",
        "truth_commitment": None,
        "updated_at": timestamp,
    }


def run_self_test(source_schema_dir: Path) -> dict[str, Any]:
    positive = 0
    negative = 0
    with tempfile.TemporaryDirectory(prefix="game-primitives-truth-") as raw_temp:
        temp_root = Path(raw_temp)
        fake_repo = temp_root / "repo"
        external = temp_root / "external"
        schema_dir = fake_repo / SCHEMA_DIR
        run_dir = fake_repo / BASE / "runs" / "continuous-999"
        schema_dir.mkdir(parents=True)
        run_dir.mkdir(parents=True)
        external.mkdir()
        for name in (
            TRUTH_SCHEMA_NAME,
            MANIFEST_SCHEMA_NAME,
            MANIFEST_BASE_SCHEMA_NAME,
        ):
            shutil.copyfile(source_schema_dir / name, schema_dir / name)

        manifest_path = run_dir / "manifest.json"
        truth_path = external / "sealed-truth.json"
        nonce_path = external / "nonce.bin"
        nonce = bytes(range(32))
        truth_bytes = canonical_bytes(sample_truth("continuous-999"))
        original_manifest = sample_manifest("continuous-999")
        manifest_path.write_bytes(canonical_bytes(original_manifest))
        truth_path.write_bytes(truth_bytes)
        nonce_path.write_bytes(nonce)

        concurrent_manifest = dict(original_manifest)
        concurrent_manifest["updated_at"] = "2026-07-27T00:00:30Z"
        concurrent_bytes = canonical_bytes(concurrent_manifest)

        def concurrent_update() -> None:
            manifest_path.write_bytes(concurrent_bytes)

        try:
            update_manifest(
                fake_repo,
                manifest_path,
                truth_path,
                nonce_path,
                "2026-07-27T00:01:00Z",
                schema_dir,
                before_cas=concurrent_update,
            )
        except CommitmentError as exc:
            if str(exc) != "manifest_cas_conflict":
                raise
            if manifest_path.read_bytes() != concurrent_bytes:
                raise AssertionError("CAS conflict overwrote concurrent manifest bytes")
            negative += 1
        else:
            raise AssertionError("manifest CAS conflict was accepted")
        manifest_path.write_bytes(canonical_bytes(original_manifest))

        result = update_manifest(
            fake_repo,
            manifest_path,
            truth_path,
            nonce_path,
            "2026-07-27T00:01:00Z",
            schema_dir,
        )
        if result["status"] != "written":
            raise AssertionError("initial update did not write")
        positive += 1
        updated_manifest = strict_json_bytes(
            manifest_path.read_bytes(), "self_test_manifest"
        )
        changed_fields = {
            key
            for key in original_manifest
            if original_manifest[key] != updated_manifest[key]
        }
        if changed_fields != {"truth_commitment", "updated_at"}:
            raise AssertionError(
                "truth commitment update changed fields outside its authority"
            )
        positive += 1
        verify_commitment(
            fake_repo, manifest_path, truth_path, nonce_path, schema_dir
        )
        positive += 1
        repeat = update_manifest(
            fake_repo,
            manifest_path,
            truth_path,
            nonce_path,
            "2026-07-27T00:02:00Z",
            schema_dir,
        )
        if repeat["status"] != "unchanged":
            raise AssertionError("same commitment was not idempotent")
        positive += 1

        for secret in (nonce, truth_bytes):
            if any(
                secret in path.read_bytes()
                for path in fake_repo.rglob("*")
                if path.is_file()
            ):
                raise AssertionError("secret bytes leaked into the temporary repository")
        positive += 1

        changed_truth = sample_truth("continuous-999")
        changed_truth["created_at"] = "2026-07-27T00:03:00Z"
        truth_path.write_bytes(canonical_bytes(changed_truth))
        try:
            update_manifest(
                fake_repo,
                manifest_path,
                truth_path,
                nonce_path,
                "2026-07-27T00:03:00Z",
                schema_dir,
            )
        except CommitmentError:
            negative += 1
        else:
            raise AssertionError("different commitment overwrite was accepted")

        try:
            verify_commitment(
                fake_repo, manifest_path, truth_path, nonce_path, schema_dir
            )
        except CommitmentError:
            negative += 1
        else:
            raise AssertionError("changed exact truth bytes verified")

        truth_path.write_bytes(truth_bytes)
        short_nonce = external / "short-nonce.bin"
        short_nonce.write_bytes(b"x" * 31)
        try:
            verify_commitment(
                fake_repo, manifest_path, truth_path, short_nonce, schema_dir
            )
        except CommitmentError:
            negative += 1
        else:
            raise AssertionError("short nonce was accepted")

        internal_truth = fake_repo / "sealed-truth.json"
        internal_truth.write_bytes(truth_bytes)
        try:
            verify_commitment(
                fake_repo, manifest_path, internal_truth, nonce_path, schema_dir
            )
        except CommitmentError:
            negative += 1
        else:
            raise AssertionError("in-repository truth was accepted")

        internal_nonce = fake_repo / "nonce.bin"
        internal_nonce.write_bytes(nonce)
        try:
            verify_commitment(
                fake_repo, manifest_path, truth_path, internal_nonce, schema_dir
            )
        except CommitmentError:
            negative += 1
        else:
            raise AssertionError("in-repository nonce was accepted")

        wrong_name = external / "truth.json"
        wrong_name.write_bytes(truth_bytes)
        try:
            verify_commitment(
                fake_repo, manifest_path, wrong_name, nonce_path, schema_dir
            )
        except CommitmentError:
            negative += 1
        else:
            raise AssertionError("wrong truth filename was accepted")

        reveal = {
            "$schema": TRUTH_SCHEMA_ID,
            "algorithm": "SHA-256",
            "artifact_type": "truth_reveal",
            "artifact_version": "0.1.0",
            "combination": "secret_nonce_bytes || exact_truth_bundle_bytes",
            "commitment": "0" * 64,
            "commitment_recomputed": "0" * 64,
            "commitment_verified": True,
            "execution_result_sha256": "0" * 64,
            "prediction_set_digest": "0" * 64,
            "revealed_at": "2026-07-27T00:04:00Z",
            "run_id": "continuous-999",
            "secret_nonce_hex": "0" * 64,
            "truth_bundle_bytes": 1,
            "truth_bundle_sha256": "0" * 64,
        }
        registry, schemas = load_registry(schema_dir)
        if validation_diagnostics(reveal, schemas[TRUTH_SCHEMA_ID], registry):
            raise AssertionError("truthReveal negative control is not schema-valid")
        truth_path.write_bytes(canonical_bytes(reveal))
        try:
            verify_commitment(
                fake_repo, manifest_path, truth_path, nonce_path, schema_dir
            )
        except CommitmentError:
            negative += 1
        else:
            raise AssertionError("truthReveal branch was accepted as sealedTruth")

        truth_path.write_bytes(
            b'{"artifact_type":"sealed_truth","artifact_type":"duplicate"}'
        )
        try:
            load_and_validate_truth(fake_repo, truth_path, schema_dir)
        except CommitmentError as exc:
            if str(exc) != "sealed_truth_json:invalid_json":
                raise
            negative += 1
        else:
            raise AssertionError("duplicate truth key was accepted")

        original_manifest_bytes = manifest_path.read_bytes()
        manifest_path.write_bytes(b'{"run_id":NaN}')
        try:
            load_and_validate_manifest(fake_repo, manifest_path, schema_dir)
        except CommitmentError as exc:
            if str(exc) != "manifest_json:invalid_json":
                raise
            negative += 1
        else:
            raise AssertionError("manifest NaN was accepted")
        manifest_path.write_bytes(original_manifest_bytes)

        try:
            strict_json_bytes(b'{"value":Infinity}', "schema_json:self-test")
        except CommitmentError as exc:
            if str(exc) != "schema_json:self-test:invalid_json":
                raise
            negative += 1
        else:
            raise AssertionError("schema Infinity was accepted")

        trusted_schema = schema_dir / TRUTH_SCHEMA_NAME
        trusted_schema_bytes = trusted_schema.read_bytes()
        trusted_schema.write_bytes(trusted_schema_bytes + b" ")
        try:
            load_registry(schema_dir)
        except CommitmentError as exc:
            if not str(exc).startswith("trusted_schema_hash_mismatch:"):
                raise
            negative += 1
        else:
            raise AssertionError("modified trusted schema was accepted")
        trusted_schema.write_bytes(trusted_schema_bytes)

        leak_dir = temp_root / "SECRET-PAYLOAD-DIR"
        leak_dir.mkdir()
        leak_truth = leak_dir / "sealed-truth.json"
        leak_truth.write_bytes(
            b'{"artifact_type":"sealed_truth",'
            b'"unexpected":"SECRET-PAYLOAD"}'
        )
        captured_out = io.StringIO()
        captured_err = io.StringIO()
        original_argv = sys.argv
        try:
            sys.argv = [
                str(Path(__file__).resolve()),
                "verify",
                "--repo-root",
                str(fake_repo),
                "--manifest",
                str(manifest_path),
                "--truth",
                str(leak_truth),
                "--nonce",
                str(nonce_path),
            ]
            with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(
                captured_err
            ):
                exit_code = main()
        finally:
            sys.argv = original_argv
        captured = captured_out.getvalue() + captured_err.getvalue()
        if exit_code != 1 or "schema_validation_failed" not in captured:
            raise AssertionError("sanitized schema failure was not emitted")
        if (
            "SECRET-PAYLOAD" in captured
            or str(leak_truth) in captured
            or str(leak_dir) in captured
        ):
            raise AssertionError("schema diagnostics leaked secret content or path")
        negative += 1

    return {
        "negative_controls_passed": negative,
        "positive_checks_passed": positive,
        "status": "passed",
    }


def common_secret_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--truth", required=True, type=Path)
    parser.add_argument("--nonce", required=True, type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview = subparsers.add_parser("preview")
    common_secret_arguments(preview)
    preview.add_argument("--created-at", required=True)

    update = subparsers.add_parser("update-manifest")
    common_secret_arguments(update)
    update.add_argument("--created-at", required=True)
    update.add_argument("--write", action="store_true")

    verify = subparsers.add_parser("verify")
    common_secret_arguments(verify)

    subparsers.add_parser("self-test")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_schema_dir = Path(__file__).resolve().parent.parent / "schema"
    try:
        if args.command == "self-test":
            result = run_self_test(source_schema_dir)
        else:
            repo_root = args.repo_root.resolve()
            schema_dir = repo_root / SCHEMA_DIR
            if args.command == "preview":
                _, manifest, _, commitment = calculate(
                    repo_root,
                    args.manifest,
                    args.truth,
                    args.nonce,
                    args.created_at,
                    schema_dir,
                )
                result = {
                    "commitment": commitment["commitment"],
                    "run_id": manifest["run_id"],
                    "status": "preview",
                }
            elif args.command == "update-manifest":
                if not args.write:
                    raise CommitmentError(
                        "update-manifest requires the explicit --write switch"
                    )
                result = update_manifest(
                    repo_root,
                    args.manifest,
                    args.truth,
                    args.nonce,
                    args.created_at,
                    schema_dir,
                )
            else:
                result = verify_commitment(
                    repo_root,
                    args.manifest,
                    args.truth,
                    args.nonce,
                    schema_dir,
                )
    except (CommitmentError, OSError, KeyError, TypeError) as exc:
        print(
            json.dumps(
                {"error": str(exc), "status": "failed"},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
