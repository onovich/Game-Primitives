#!/usr/bin/env python3
"""Materialize a canonical frozen-set preimage and verify the two-commit freeze.

``prepare-manifest --write`` performs the single pre-commit-A transition from
an unfrozen, truth-committed manifest to the complete frozen member set and
its canonical preimage.  It uses compare-and-swap replacement and refuses
different existing preimage bytes.  ``materialize --write`` remains the
lower-level preimage-only operation and never edits the manifest.

``verify-commit-a`` and ``verify-commit-b`` read Git objects rather than the
working tree.  Commit A must contain the complete preimage and a still-preparing
manifest.  Commit B must be its single-parent successor and may change only the
manifest fields ``freeze_commit``, ``status``, and ``updated_at``.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import posixpath
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


BASE = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA_DIR = BASE / "schema"
DEFAULT_MANIFEST = BASE / "runs/continuous-001/manifest.json"
PREIMAGE_PATH = "inputs/frozen-set-preimage.tsv"
PREIMAGE_ARTIFACT_ID = "frozen-set-preimage"
PREIMAGE_SCHEMA_NAME = "frozen-set-preimage-0.1.0.schema.json"
PREIMAGE_SCHEMA_SHA256 = (
    "7914907b9fb8e1166aeafa4a1507018ea0d4718e5daee9c7235807905a8d5948"
)
MANIFEST_SCHEMA_NAME = "run-manifest-0.1.1.schema.json"
MANIFEST_BASE_SCHEMA_NAME = "run-manifest-0.1.0.schema.json"
MANIFEST_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "run-manifest-0.1.1.schema.json"
)
READINESS_TOOL_PATH = BASE / "tools/verify-formal-readiness.py"
TRUSTED_READINESS_SHA256 = (
    "2f26a047fa2fd93f4d72c7325b1bba5a22143e7f1f8e3c6172eb8718e519a41a"
)
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
TRUSTED_SCHEMA_SHA256 = {
    MANIFEST_SCHEMA_NAME: "21996046a40a31f2061d3b6a271588c5dd0cf402d3061018cca8301b233d814f",
    MANIFEST_BASE_SCHEMA_NAME: "367f890f52e56d06d8ef4dadbffdcd3d85946f12eff40c47e83373b44b3e7160",
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
POST_GATE_PREFIXES = ("execution/raw/", "reports/", "reveal/", "submissions/")
POST_GATE_PATHS = {
    "execution/execution-result.json",
    "execution/trace-bundle.json",
}


class FrozenSetError(ValueError):
    """A fail-closed frozen-set validation error."""


class StrictJsonError(ValueError):
    """Internal marker for duplicate keys or non-finite JSON constants."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_json_bytes(raw: bytes, code: str) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FrozenSetError(f"{code}:invalid_utf8") from exc

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
        raise FrozenSetError(f"{code}:invalid_json") from exc


def validate_readiness_contract(raw: bytes) -> None:
    if sha256_bytes(raw) != TRUSTED_READINESS_SHA256:
        raise FrozenSetError("trusted_readiness_hash_mismatch")
    try:
        module = ast.parse(raw.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise FrozenSetError("trusted_readiness_parse_failed") from exc
    extracted: Any = None
    for statement in module.body:
        if not isinstance(statement, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == "REQUIRED_PATHS"
            for target in statement.targets
        ):
            try:
                extracted = ast.literal_eval(statement.value)
            except (ValueError, TypeError) as exc:
                raise FrozenSetError(
                    "trusted_readiness_required_paths_not_literal"
                ) from exc
            break
    if extracted != REQUIRED_PATHS:
        raise FrozenSetError("trusted_readiness_required_paths_mismatch")


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_repo_path(repo_root: Path, value: Path, *, must_exist: bool) -> Path:
    repo_root = repo_root.resolve()
    candidate = value if value.is_absolute() else repo_root / value
    candidate = candidate.resolve()
    if not is_within(candidate, repo_root):
        raise FrozenSetError(f"path escapes repository root: {value}")
    if must_exist and not candidate.is_file():
        raise FrozenSetError(f"file does not exist: {value}")
    return candidate


def repo_relative(repo_root: Path, value: Path) -> str:
    resolved = resolve_repo_path(repo_root, value, must_exist=True)
    return resolved.relative_to(repo_root.resolve()).as_posix()


def normalize_manifest_entry_path(manifest_relative: str, entry_path: str) -> str:
    if (
        not isinstance(entry_path, str)
        or not entry_path
        or "\\" in entry_path
        or "\t" in entry_path
        or "\n" in entry_path
        or "\r" in entry_path
        or PurePosixPath(entry_path).is_absolute()
    ):
        raise FrozenSetError(f"non-canonical manifest artifact path: {entry_path!r}")
    normalized = posixpath.normpath(
        posixpath.join(posixpath.dirname(manifest_relative), entry_path)
    )
    if normalized == ".." or normalized.startswith("../") or normalized.startswith("/"):
        raise FrozenSetError(f"manifest artifact path escapes repository: {entry_path}")
    return normalized


def load_registry_from_files(
    schema_files: list[tuple[str, bytes]],
) -> tuple[Registry, dict[str, dict[str, Any]]]:
    by_name: dict[str, bytes] = {}
    for label, raw in schema_files:
        name = PurePosixPath(label.replace("\\", "/")).name
        if name in by_name:
            raise FrozenSetError(f"duplicate_trusted_schema:{name}")
        by_name[name] = raw

    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    for name, trusted_hash in TRUSTED_SCHEMA_SHA256.items():
        raw = by_name.get(name)
        if raw is None:
            raise FrozenSetError(f"trusted_schema_missing:{name}")
        if sha256_bytes(raw) != trusted_hash:
            raise FrozenSetError(f"trusted_schema_hash_mismatch:{name}")
        schema = strict_json_bytes(raw, f"schema_json:{name}")
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            if schema_id in schemas:
                raise FrozenSetError(f"duplicate schema id: {schema_id}")
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


def validate_manifest(
    manifest: Any,
    schema_files: list[tuple[str, bytes]],
) -> dict[str, Any]:
    registry, schemas = load_registry_from_files(schema_files)
    schema = schemas.get(MANIFEST_SCHEMA_ID)
    if schema is None:
        raise FrozenSetError("run-manifest 0.1.1 schema is absent")
    allowed_names = schema_property_names(schema)
    errors = sorted(
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(manifest),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        details: list[str] = []
        for error in errors[:12]:
            validator = str(error.validator)
            if not re.fullmatch(r"[A-Za-z0-9_$.-]+", validator):
                validator = "unknown"
            details.append(
                "schema_validation_failed|pointer="
                f"{safe_json_pointer(error.absolute_path, allowed_names)}"
                f"|validator={validator}"
            )
        raise FrozenSetError("manifest_schema_invalid:\n" + "\n".join(details))
    if not isinstance(manifest, dict):
        raise FrozenSetError("manifest root must be an object")
    return manifest


def filesystem_schema_files(repo_root: Path) -> list[tuple[str, bytes]]:
    schema_dir = repo_root / SCHEMA_DIR
    files: list[tuple[str, bytes]] = []
    for name in TRUSTED_SCHEMA_SHA256:
        path = schema_dir / name
        try:
            files.append((name, path.read_bytes()))
        except OSError as exc:
            raise FrozenSetError(f"trusted_schema_missing:{name}") from exc
    return files


def git(
    repo_root: Path,
    arguments: list[str],
    *,
    check: bool = True,
) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise FrozenSetError(
            f"git {' '.join(arguments)} failed: {stderr or result.returncode}"
        )
    return result.stdout


def require_commit(repo_root: Path, value: str, label: str) -> str:
    if not FULL_SHA.fullmatch(value):
        raise FrozenSetError(f"{label} must be a full lowercase 40-hex commit id")
    resolved = (
        git(repo_root, ["rev-parse", "--verify", f"{value}^{{commit}}"])
        .decode("ascii")
        .strip()
    )
    if resolved != value:
        raise FrozenSetError(f"{label} did not resolve to itself")
    return value


def git_file(repo_root: Path, commit: str, path: str) -> bytes:
    if not path or path.startswith("/") or ".." in PurePosixPath(path).parts:
        raise FrozenSetError(f"unsafe Git path: {path}")
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{commit}:{path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise FrozenSetError(f"file is absent at {commit}: {path}")
    return result.stdout


def git_schema_files(repo_root: Path, commit: str) -> list[tuple[str, bytes]]:
    return [
        (
            (SCHEMA_DIR / name).as_posix(),
            git_file(repo_root, commit, (SCHEMA_DIR / name).as_posix()),
        )
        for name in TRUSTED_SCHEMA_SHA256
    ]


def decode_manifest(raw: bytes, label: str) -> Any:
    return strict_json_bytes(raw, label)


def preimage_entry(manifest: dict[str, Any]) -> dict[str, Any]:
    matches = [
        entry
        for entry in manifest["artifacts"]
        if entry.get("artifact_id") == PREIMAGE_ARTIFACT_ID
        or entry.get("path") == PREIMAGE_PATH
    ]
    if len(matches) != 1:
        raise FrozenSetError("manifest must contain exactly one frozen-set preimage entry")
    entry = matches[0]
    if (
        entry.get("artifact_id") != PREIMAGE_ARTIFACT_ID
        or entry.get("path") != PREIMAGE_PATH
    ):
        raise FrozenSetError("frozen-set preimage id and path must match the contract")
    if entry.get("included_in_frozen_set") is not False:
        raise FrozenSetError("frozen-set preimage must not include itself")
    return entry


def validate_formal_completeness(manifest: dict[str, Any]) -> None:
    if manifest.get("artifact_type") != "formal_run_manifest":
        raise FrozenSetError("formal_completeness:artifact_type")
    if manifest.get("run_id") != "continuous-001":
        raise FrozenSetError("formal_completeness:run_id")
    entries: dict[str, dict[str, Any]] = {}
    for entry in manifest["artifacts"]:
        path = entry["path"]
        if path in entries:
            raise FrozenSetError("formal_completeness:duplicate_path")
        entries[path] = entry
    for path, must_be_frozen in REQUIRED_PATHS.items():
        entry = entries.get(path)
        if entry is None:
            raise FrozenSetError(f"formal_completeness:missing:{path}")
        if entry.get("included_in_frozen_set") is not must_be_frozen:
            raise FrozenSetError(f"formal_completeness:frozen_flag:{path}")
    for path in entries:
        if path in POST_GATE_PATHS or path.startswith(POST_GATE_PREFIXES):
            raise FrozenSetError(f"formal_completeness:post_gate:{path}")


def build_preimage(
    manifest: dict[str, Any],
    read_artifact: Callable[[str], bytes],
) -> tuple[bytes, list[str]]:
    preimage_entry(manifest)
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    members: list[tuple[str, str]] = []
    for entry in manifest["artifacts"]:
        artifact_id = entry["artifact_id"]
        path = entry["path"]
        if artifact_id in seen_ids:
            raise FrozenSetError(f"duplicate artifact id: {artifact_id}")
        if path in seen_paths:
            raise FrozenSetError(f"duplicate artifact path: {path}")
        seen_ids.add(artifact_id)
        seen_paths.add(path)
        if not entry["included_in_frozen_set"]:
            continue
        if (
            "\\" in path
            or "\t" in path
            or "\n" in path
            or "\r" in path
            or not path
        ):
            raise FrozenSetError(f"non-canonical frozen artifact path: {path!r}")
        actual = sha256_bytes(read_artifact(path))
        if actual != entry["sha256"]:
            raise FrozenSetError(
                f"frozen artifact hash mismatch for {path}: "
                f"expected {entry['sha256']}, found {actual}"
            )
        members.append((path, actual))
    if not members:
        raise FrozenSetError("frozen artifact set must contain at least one artifact")
    members.sort(key=lambda pair: pair[0])
    preimage = "".join(f"{path}\t{digest}\n" for path, digest in members).encode(
        "utf-8"
    )
    return preimage, [path for path, _ in members]


def working_context(
    repo_root: Path,
    manifest_path: Path,
) -> tuple[Path, str, dict[str, Any]]:
    repo_root = repo_root.resolve()
    resolved_manifest = resolve_repo_path(repo_root, manifest_path, must_exist=True)
    relative_manifest = resolved_manifest.relative_to(repo_root).as_posix()
    manifest = validate_manifest(
        decode_manifest(resolved_manifest.read_bytes(), "manifest"),
        filesystem_schema_files(repo_root),
    )
    return resolved_manifest, relative_manifest, manifest


def materialize(
    repo_root: Path,
    manifest_path: Path,
    *,
    write: bool,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    try:
        readiness_bytes = (repo_root / READINESS_TOOL_PATH).read_bytes()
    except OSError as exc:
        raise FrozenSetError("trusted_readiness_missing") from exc
    validate_readiness_contract(readiness_bytes)
    _, manifest_relative, manifest = working_context(repo_root, manifest_path)
    if manifest.get("status") != "preparing":
        raise FrozenSetError("manifest status must be preparing")
    if manifest.get("freeze_commit") is not None:
        raise FrozenSetError("preimage generation requires freeze_commit=null")
    if manifest.get("stage_digests") != []:
        raise FrozenSetError("preimage generation requires no stage digests")
    if manifest.get("truth_commitment") is None:
        raise FrozenSetError("preimage generation requires a truth commitment")
    validate_formal_completeness(manifest)

    def read_artifact(path: str) -> bytes:
        relative = normalize_manifest_entry_path(manifest_relative, path)
        return resolve_repo_path(
            repo_root, Path(PurePosixPath(relative)), must_exist=True
        ).read_bytes()

    preimage, members = build_preimage(manifest, read_artifact)
    digest = sha256_bytes(preimage)
    declared_digest = manifest.get("frozen_artifact_set_digest")
    if declared_digest is not None and declared_digest != digest:
        raise FrozenSetError(
            "manifest frozen_artifact_set_digest conflicts with canonical preimage"
        )

    entry = preimage_entry(manifest)
    output_relative = normalize_manifest_entry_path(
        manifest_relative, entry["path"]
    )
    output = resolve_repo_path(
        repo_root, Path(PurePosixPath(output_relative)), must_exist=False
    )
    if output.exists():
        if not output.is_file():
            raise FrozenSetError("preimage target exists but is not a file")
        if output.read_bytes() != preimage:
            raise FrozenSetError("refusing to overwrite a different preimage")
        status = "unchanged"
    elif write:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=output.parent,
                prefix=f".{output.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(preimage)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, output)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        status = "written"
    else:
        status = "preview"
    return {
        "frozen_artifact_count": len(members),
        "frozen_artifact_set_digest": digest,
        "members": members,
        "preimage_path": entry["path"],
        "preimage_sha256": digest,
        "status": status,
    }


def prepare_manifest(
    repo_root: Path,
    manifest_path: Path,
    updated_at: str,
    *,
    write: bool,
) -> dict[str, Any]:
    """Atomically prepare commit A's manifest and canonical preimage.

    This is intentionally a separate transition from truth commitment.  The
    input manifest must already contain that commitment while every artifact
    remains unfrozen.  The transition freezes every pre-gate manifest artifact,
    leaves only the preimage itself outside its own member set, computes the
    digest, and updates the two linked manifest fields without a manual edit.
    """

    repo_root = repo_root.resolve()
    try:
        readiness_bytes = (repo_root / READINESS_TOOL_PATH).read_bytes()
    except OSError as exc:
        raise FrozenSetError("trusted_readiness_missing") from exc
    validate_readiness_contract(readiness_bytes)
    resolved_manifest, manifest_relative, manifest = working_context(
        repo_root,
        manifest_path,
    )
    initial_manifest_bytes = resolved_manifest.read_bytes()
    if manifest.get("status") != "preparing":
        raise FrozenSetError("manifest status must be preparing")
    if manifest.get("freeze_commit") is not None:
        raise FrozenSetError("commit A preparation requires freeze_commit=null")
    if manifest.get("stage_digests") != []:
        raise FrozenSetError("commit A preparation requires no stage digests")
    if manifest.get("truth_commitment") is None:
        raise FrozenSetError("commit A preparation requires a truth commitment")
    declared_digest = manifest.get("frozen_artifact_set_digest")

    preimage_schema = repo_root / SCHEMA_DIR / PREIMAGE_SCHEMA_NAME
    try:
        preimage_schema_bytes = preimage_schema.read_bytes()
    except OSError as exc:
        raise FrozenSetError("trusted_preimage_schema_missing") from exc
    if sha256_bytes(preimage_schema_bytes) != PREIMAGE_SCHEMA_SHA256:
        raise FrozenSetError("trusted_preimage_schema_hash_mismatch")

    candidate = copy.deepcopy(manifest)
    existing_preimages = [
        entry
        for entry in candidate["artifacts"]
        if entry.get("artifact_id") == PREIMAGE_ARTIFACT_ID
        or entry.get("path") == PREIMAGE_PATH
    ]
    if len(existing_preimages) > 1:
        raise FrozenSetError("multiple frozen-set preimage entries")
    expected_preimage_entry = {
        "artifact_id": PREIMAGE_ARTIFACT_ID,
        "artifact_kind": "audit",
        "artifact_version": "0.1.0",
        "audience": ["custodian", "public_after_reveal"],
        "decision_relevant": True,
        "included_in_frozen_set": False,
        "path": PREIMAGE_PATH,
        "release_stage": "preparation",
        "schema_path": (SCHEMA_DIR / PREIMAGE_SCHEMA_NAME).as_posix(),
        "schema_sha256": PREIMAGE_SCHEMA_SHA256,
        "sha256": "0" * 64,
        "supersedes_artifact_id": None,
    }
    if existing_preimages:
        existing = copy.deepcopy(existing_preimages[0])
        existing["sha256"] = "0" * 64
        if existing != expected_preimage_entry:
            raise FrozenSetError("existing preimage entry differs from contract")

    frozen_entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for entry in candidate["artifacts"]:
        if (
            entry.get("artifact_id") == PREIMAGE_ARTIFACT_ID
            or entry.get("path") == PREIMAGE_PATH
        ):
            continue
        artifact_id = entry.get("artifact_id")
        path = entry.get("path")
        if artifact_id in seen_ids or path in seen_paths:
            raise FrozenSetError("duplicate artifact id or path before freeze")
        seen_ids.add(artifact_id)
        seen_paths.add(path)
        if path in POST_GATE_PATHS or any(
            path.startswith(prefix) for prefix in POST_GATE_PREFIXES
        ):
            raise FrozenSetError(f"commit A contains post-gate artifact: {path}")
        frozen = copy.deepcopy(entry)
        frozen["included_in_frozen_set"] = True
        frozen_entries.append(frozen)
    frozen_entries.append(expected_preimage_entry)
    candidate["artifacts"] = frozen_entries
    candidate["frozen_artifact_set_digest"] = None
    candidate["updated_at"] = updated_at
    candidate = validate_manifest(candidate, filesystem_schema_files(repo_root))
    validate_formal_completeness(candidate)

    def read_artifact(path: str) -> bytes:
        relative = normalize_manifest_entry_path(manifest_relative, path)
        return resolve_repo_path(
            repo_root,
            Path(PurePosixPath(relative)),
            must_exist=True,
        ).read_bytes()

    preimage, members = build_preimage(candidate, read_artifact)
    digest = sha256_bytes(preimage)
    if declared_digest is not None and declared_digest != digest:
        raise FrozenSetError(
            "existing frozen artifact set digest conflicts with canonical preimage"
        )
    candidate["frozen_artifact_set_digest"] = digest
    preimage_entry(candidate)["sha256"] = digest
    candidate = validate_manifest(candidate, filesystem_schema_files(repo_root))
    validate_formal_completeness(candidate)
    manifest_output = canonical_json_bytes(candidate)

    output_relative = normalize_manifest_entry_path(
        manifest_relative,
        PREIMAGE_PATH,
    )
    preimage_output = resolve_repo_path(
        repo_root,
        Path(PurePosixPath(output_relative)),
        must_exist=False,
    )
    if preimage_output.is_symlink():
        raise FrozenSetError("preimage target must not be a symlink")
    if preimage_output.exists() and not preimage_output.is_file():
        raise FrozenSetError("preimage target exists but is not a file")
    if preimage_output.is_file() and preimage_output.read_bytes() != preimage:
        raise FrozenSetError("refusing to overwrite a different preimage")

    status = "preview"
    if write:
        if resolved_manifest.read_bytes() != initial_manifest_bytes:
            raise FrozenSetError("manifest changed after preparation began")
        preimage_output.parent.mkdir(parents=True, exist_ok=True)
        if not preimage_output.exists():
            temporary_preimage: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    dir=preimage_output.parent,
                    prefix=f".{preimage_output.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as handle:
                    temporary_preimage = Path(handle.name)
                    handle.write(preimage)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary_preimage, preimage_output)
                temporary_preimage = None
            finally:
                if temporary_preimage is not None:
                    temporary_preimage.unlink(missing_ok=True)
        if resolved_manifest.read_bytes() != initial_manifest_bytes:
            raise FrozenSetError("manifest changed before atomic replacement")
        temporary_manifest: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=resolved_manifest.parent,
                prefix=f".{resolved_manifest.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_manifest = Path(handle.name)
                handle.write(manifest_output)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_manifest, resolved_manifest)
            temporary_manifest = None
        finally:
            if temporary_manifest is not None:
                temporary_manifest.unlink(missing_ok=True)
        status = "written"
    return {
        "frozen_artifact_count": len(members),
        "frozen_artifact_set_digest": digest,
        "manifest_sha256": sha256_bytes(manifest_output),
        "members": members,
        "preimage_path": PREIMAGE_PATH,
        "preimage_sha256": digest,
        "status": status,
    }


def load_manifest_at_commit(
    repo_root: Path,
    commit: str,
    manifest_relative: str,
) -> dict[str, Any]:
    raw = git_file(repo_root, commit, manifest_relative)
    return validate_manifest(
        decode_manifest(raw, f"manifest at {commit}"),
        git_schema_files(repo_root, commit),
    )


def verify_commit_a(
    repo_root: Path,
    manifest_relative: str,
    anchor_commit: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    anchor_commit = require_commit(repo_root, anchor_commit, "anchor commit")
    validate_readiness_contract(
        git_file(repo_root, anchor_commit, READINESS_TOOL_PATH.as_posix())
    )
    if (
        not manifest_relative
        or "\\" in manifest_relative
        or manifest_relative.startswith("/")
        or ".." in PurePosixPath(manifest_relative).parts
    ):
        raise FrozenSetError("manifest-relative must be a canonical repository path")
    manifest = load_manifest_at_commit(
        repo_root, anchor_commit, manifest_relative
    )
    if manifest.get("status") != "preparing":
        raise FrozenSetError("commit A manifest status must be preparing")
    if manifest.get("freeze_commit") is not None:
        raise FrozenSetError("commit A manifest freeze_commit must be null")
    if manifest.get("stage_digests") != []:
        raise FrozenSetError("commit A manifest must not have stage digests")
    if manifest.get("truth_commitment") is None:
        raise FrozenSetError("commit A manifest must contain a truth commitment")
    validate_formal_completeness(manifest)

    def read_artifact(path: str) -> bytes:
        relative = normalize_manifest_entry_path(manifest_relative, path)
        return git_file(repo_root, anchor_commit, relative)

    expected_preimage, members = build_preimage(manifest, read_artifact)
    digest = sha256_bytes(expected_preimage)
    entry = preimage_entry(manifest)
    actual_preimage = read_artifact(entry["path"])
    if actual_preimage != expected_preimage:
        raise FrozenSetError("commit A preimage bytes are not canonical")
    if entry.get("sha256") != digest:
        raise FrozenSetError("commit A preimage manifest hash does not match its bytes")
    if manifest.get("frozen_artifact_set_digest") != digest:
        raise FrozenSetError("commit A frozen artifact set digest is incorrect")
    return {
        "anchor_commit": anchor_commit,
        "frozen_artifact_count": len(members),
        "frozen_artifact_set_digest": digest,
        "manifest": manifest_relative,
        "status": "passed",
    }


def changed_top_level_fields(
    before: dict[str, Any],
    after: dict[str, Any],
) -> set[str]:
    return {
        key
        for key in set(before) | set(after)
        if before.get(key) != after.get(key)
    }


def verify_commit_b(
    repo_root: Path,
    manifest_relative: str,
    anchor_commit: str,
    finalize_commit: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    anchor_result = verify_commit_a(repo_root, manifest_relative, anchor_commit)
    finalize_commit = require_commit(repo_root, finalize_commit, "finalize commit")
    parents = (
        git(repo_root, ["rev-list", "--parents", "-n", "1", finalize_commit])
        .decode("ascii")
        .strip()
        .split()
    )
    if parents != [finalize_commit, anchor_commit]:
        raise FrozenSetError(
            "commit B must be a non-merge commit whose sole parent is commit A"
        )
    changes = (
        git(
            repo_root,
            [
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "-r",
                anchor_commit,
                finalize_commit,
            ],
        )
        .decode("utf-8")
        .splitlines()
    )
    if changes != [f"M\t{manifest_relative}"]:
        raise FrozenSetError("commit B must modify only the run manifest")

    before = load_manifest_at_commit(repo_root, anchor_commit, manifest_relative)
    after = load_manifest_at_commit(repo_root, finalize_commit, manifest_relative)
    if after.get("status") != "frozen":
        raise FrozenSetError("commit B manifest status must be frozen")
    if after.get("freeze_commit") != anchor_commit:
        raise FrozenSetError("commit B manifest freeze_commit must equal commit A")
    changed_fields = changed_top_level_fields(before, after)
    required_changes = {"freeze_commit", "status", "updated_at"}
    if changed_fields != required_changes:
        raise FrozenSetError(
            "commit B manifest must change exactly freeze_commit, status, and updated_at"
        )
    return {
        **anchor_result,
        "finalize_commit": finalize_commit,
        "status": "passed",
    }


def artifact_entry(
    artifact_id: str,
    path: str,
    digest: str,
    schema_hash: str,
    *,
    included: bool,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "artifact_kind": "audit" if not included else "source",
        "artifact_version": "0.1.0",
        "audience": ["custodian"],
        "decision_relevant": True,
        "included_in_frozen_set": included,
        "path": path,
        "release_stage": "preparation",
        "schema_path": (SCHEMA_DIR / MANIFEST_SCHEMA_NAME).as_posix(),
        "schema_sha256": schema_hash,
        "sha256": digest,
        "supersedes_artifact_id": None,
    }


def sample_manifest(
    schema_hash: str,
    artifact_hashes: dict[str, str],
) -> dict[str, Any]:
    timestamp = "2026-07-27T00:00:00Z"
    artifacts: list[dict[str, Any]] = []
    for index, (path, included) in enumerate(REQUIRED_PATHS.items(), start=1):
        if path == PREIMAGE_PATH:
            artifact_id = PREIMAGE_ARTIFACT_ID
            digest = "0" * 64
        else:
            artifact_id = f"required-{index:03d}"
            digest = artifact_hashes[path]
        artifacts.append(
            artifact_entry(
                artifact_id,
                path,
                digest,
                schema_hash,
                included=included,
            )
        )
    return {
        "$schema": MANIFEST_SCHEMA_ID,
        "artifact_type": "formal_run_manifest",
        "artifact_version": "0.1.1",
        "artifacts": artifacts,
        "created_at": timestamp,
        "freeze_commit": None,
        "frozen_artifact_set_digest": None,
        "protocol_version": "0.1.0",
        "run_id": "continuous-001",
        "schema_version": "0.1.1",
        "stage": "preparation",
        "stage_digests": [],
        "status": "preparing",
        "truth_commitment": {
            "algorithm": "SHA-256",
            "combination": "secret_nonce_bytes || exact_truth_bundle_bytes",
            "commitment": "1" * 64,
            "created_at": timestamp,
            "nonce_length_bytes": 32,
            "truth_bundle_bytes": 1,
            "truth_bundle_name": "sealed-truth.json",
        },
        "updated_at": timestamp,
    }


def git_text(repo_root: Path, arguments: list[str]) -> str:
    return git(repo_root, arguments).decode("utf-8").strip()


def run_self_test(source_schema_dir: Path) -> dict[str, Any]:
    positive = 0
    negative = 0
    with tempfile.TemporaryDirectory(prefix="game-primitives-freeze-") as raw_temp:
        repo = (Path(raw_temp) / "repo").resolve()
        schema_dir = repo / SCHEMA_DIR
        run_dir = repo / BASE / "runs" / "continuous-001"
        run_dir.mkdir(parents=True)
        schema_dir.mkdir(parents=True)
        for name in (
            MANIFEST_SCHEMA_NAME,
            MANIFEST_BASE_SCHEMA_NAME,
            PREIMAGE_SCHEMA_NAME,
        ):
            shutil.copyfile(source_schema_dir / name, schema_dir / name)
        readiness_path = repo / READINESS_TOOL_PATH
        readiness_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            source_schema_dir.parent / "tools" / READINESS_TOOL_PATH.name,
            readiness_path,
        )
        git(repo, ["init", "--quiet"])
        git(repo, ["config", "user.email", "self-test@example.invalid"])
        git(repo, ["config", "user.name", "Frozen Set Self Test"])

        artifact_hashes: dict[str, str] = {}
        for index, path in enumerate(REQUIRED_PATHS, start=1):
            if path == PREIMAGE_PATH:
                continue
            content = f"temporary formal artifact {index}: {path}\n".encode("utf-8")
            artifact_path = run_dir / Path(PurePosixPath(path))
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_bytes(content)
            artifact_hashes[path] = sha256_bytes(content)
        schema_hash = sha256_bytes((schema_dir / MANIFEST_SCHEMA_NAME).read_bytes())
        manifest = sample_manifest(schema_hash, artifact_hashes)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        preparing_manifest_bytes = manifest_path.read_bytes()

        unfrozen = copy.deepcopy(manifest)
        unfrozen["artifacts"] = [
            {
                **entry,
                "included_in_frozen_set": False,
            }
            for entry in unfrozen["artifacts"]
            if entry["path"] != PREIMAGE_PATH
        ]
        manifest_path.write_bytes(canonical_json_bytes(unfrozen))
        prepared_preview = prepare_manifest(
            repo,
            manifest_path,
            "2026-07-27T00:00:01Z",
            write=False,
        )
        if prepared_preview["status"] != "preview":
            raise AssertionError("commit A manifest preview failed")
        positive += 1
        prepared = prepare_manifest(
            repo,
            manifest_path,
            "2026-07-27T00:00:01Z",
            write=True,
        )
        if prepared["status"] != "written":
            raise AssertionError("commit A manifest preparation failed")
        prepared_manifest = strict_json_bytes(
            manifest_path.read_bytes(),
            "prepared_manifest",
        )
        validate_formal_completeness(prepared_manifest)
        if (
            prepared_manifest["frozen_artifact_set_digest"]
            != prepared["preimage_sha256"]
            or preimage_entry(prepared_manifest)["sha256"]
            != prepared["preimage_sha256"]
        ):
            raise AssertionError("prepared manifest digest binding failed")
        positive += 1
        (run_dir / PREIMAGE_PATH).unlink()
        manifest_path.write_bytes(preparing_manifest_bytes)

        incomplete = dict(manifest)
        incomplete["artifacts"] = [
            manifest["artifacts"][0],
            preimage_entry(manifest),
        ]
        try:
            validate_formal_completeness(incomplete)
        except FrozenSetError:
            negative += 1
        else:
            raise AssertionError("schema-valid incomplete formal manifest was accepted")

        empty_commitment = dict(manifest)
        empty_commitment["truth_commitment"] = {}
        try:
            validate_manifest(
                empty_commitment,
                filesystem_schema_files(repo),
            )
        except FrozenSetError:
            negative += 1
        else:
            raise AssertionError("empty truth commitment was accepted")

        preimage_path = run_dir / PREIMAGE_PATH
        preimage_path.write_bytes(b"different\n")
        try:
            materialize(repo, manifest_path, write=True)
        except FrozenSetError:
            negative += 1
        else:
            raise AssertionError("different preimage overwrite was accepted")
        preimage_path.unlink()

        preview = materialize(repo, manifest_path, write=False)
        if preview["status"] != "preview":
            raise AssertionError("preimage preview failed")
        positive += 1
        created = materialize(repo, manifest_path, write=True)
        if created["status"] != "written":
            raise AssertionError("preimage materialization failed")
        positive += 1
        if manifest_path.read_bytes() != preparing_manifest_bytes:
            raise AssertionError("preimage materialization changed the manifest")
        positive += 1

        preimage_entry(manifest)["sha256"] = created["preimage_sha256"]
        manifest["frozen_artifact_set_digest"] = created[
            "frozen_artifact_set_digest"
        ]
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        git(repo, ["add", "--all"])
        git(repo, ["commit", "--quiet", "-m", "anchor"])
        anchor = git_text(repo, ["rev-parse", "HEAD"])
        manifest_relative = manifest_path.relative_to(repo).as_posix()
        verify_commit_a(repo, manifest_relative, anchor)
        positive += 1

        finalized = dict(manifest)
        finalized["freeze_commit"] = anchor
        finalized["status"] = "frozen"
        finalized["updated_at"] = "2026-07-27T00:01:00Z"
        manifest_path.write_bytes(canonical_json_bytes(finalized))
        git(repo, ["add", "--", manifest_relative])
        git(repo, ["commit", "--quiet", "-m", "finalize"])
        final = git_text(repo, ["rev-parse", "HEAD"])
        verify_commit_b(repo, manifest_relative, anchor, final)
        positive += 1

        (repo / "extra.txt").write_text("extra\n", encoding="utf-8")
        git(repo, ["add", "--", "extra.txt"])
        git(repo, ["commit", "--quiet", "-m", "extra"])
        extra = git_text(repo, ["rev-parse", "HEAD"])
        try:
            verify_commit_b(repo, manifest_relative, anchor, extra)
        except FrozenSetError:
            negative += 1
        else:
            raise AssertionError("non-successor commit B was accepted")

        git(repo, ["switch", "--quiet", "-c", "invalid-final", anchor])
        invalid = dict(manifest)
        invalid["freeze_commit"] = anchor
        invalid["status"] = "frozen"
        invalid["updated_at"] = "2026-07-27T00:02:00Z"
        invalid["truth_commitment"] = dict(invalid["truth_commitment"])
        invalid["truth_commitment"]["commitment"] = "2" * 64
        manifest_path.write_bytes(canonical_json_bytes(invalid))
        git(repo, ["add", "--", manifest_relative])
        git(repo, ["commit", "--quiet", "-m", "invalid finalize"])
        invalid_final = git_text(repo, ["rev-parse", "HEAD"])
        try:
            verify_commit_b(repo, manifest_relative, anchor, invalid_final)
        except FrozenSetError:
            negative += 1
        else:
            raise AssertionError("commit B with an extra manifest change was accepted")

        git(repo, ["switch", "--quiet", "-c", "corrupt-anchor", anchor])
        (run_dir / "README.md").write_bytes(b"changed\n")
        git(repo, ["add", "--", (run_dir / "README.md").relative_to(repo).as_posix()])
        git(repo, ["commit", "--quiet", "-m", "corrupt frozen member"])
        corrupt = git_text(repo, ["rev-parse", "HEAD"])
        try:
            verify_commit_a(repo, manifest_relative, corrupt)
        except FrozenSetError:
            negative += 1
        else:
            raise AssertionError("corrupt anchor artifact was accepted")

        try:
            decode_manifest(
                b'{"run_id":"continuous-001","run_id":"duplicate"}',
                "manifest_json",
            )
        except FrozenSetError as exc:
            if str(exc) != "manifest_json:invalid_json":
                raise
            negative += 1
        else:
            raise AssertionError("duplicate manifest key was accepted")

        try:
            decode_manifest(b'{"value":NaN}', "manifest_json")
        except FrozenSetError as exc:
            if str(exc) != "manifest_json:invalid_json":
                raise
            negative += 1
        else:
            raise AssertionError("manifest NaN was accepted")

        try:
            strict_json_bytes(b'{"value":Infinity}', "schema_json:self-test")
        except FrozenSetError as exc:
            if str(exc) != "schema_json:self-test:invalid_json":
                raise
            negative += 1
        else:
            raise AssertionError("schema Infinity was accepted")

        git(repo, ["switch", "--quiet", "-c", "empty-commitment", anchor])
        empty_anchor_manifest = dict(manifest)
        empty_anchor_manifest["truth_commitment"] = {}
        manifest_path.write_bytes(canonical_json_bytes(empty_anchor_manifest))
        git(repo, ["add", "--", manifest_relative])
        git(repo, ["commit", "--quiet", "-m", "empty truth commitment"])
        empty_anchor = git_text(repo, ["rev-parse", "HEAD"])
        try:
            verify_commit_a(repo, manifest_relative, empty_anchor)
        except FrozenSetError:
            negative += 1
        else:
            raise AssertionError("commit A with an empty truth commitment was accepted")

        git(repo, ["switch", "--quiet", "-c", "weakened-schema", anchor])
        weakened_schema_path = schema_dir / MANIFEST_SCHEMA_NAME
        weakened_schema_path.write_bytes(
            canonical_json_bytes(
                {
                    "$id": MANIFEST_SCHEMA_ID,
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                }
            )
        )
        git(
            repo,
            [
                "add",
                "--",
                weakened_schema_path.relative_to(repo).as_posix(),
            ],
        )
        git(repo, ["commit", "--quiet", "-m", "weaken manifest schema"])
        weakened = git_text(repo, ["rev-parse", "HEAD"])
        try:
            verify_commit_a(repo, manifest_relative, weakened)
        except FrozenSetError as exc:
            if not str(exc).startswith("trusted_schema_hash_mismatch:"):
                raise
            negative += 1
        else:
            raise AssertionError("commit A with a weakened schema was accepted")

        try:
            verify_commit_a(repo, manifest_relative, "HEAD")
        except FrozenSetError:
            negative += 1
        else:
            raise AssertionError("symbolic commit reference was accepted")

    return {
        "negative_controls_passed": negative,
        "positive_checks_passed": positive,
        "status": "passed",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare-manifest")
    prepare_parser.add_argument("--repo-root", required=True, type=Path)
    prepare_parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    prepare_parser.add_argument("--updated-at", required=True)
    prepare_parser.add_argument("--write", action="store_true")

    materialize_parser = subparsers.add_parser("materialize")
    materialize_parser.add_argument("--repo-root", required=True, type=Path)
    materialize_parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    materialize_parser.add_argument("--write", action="store_true")

    commit_a = subparsers.add_parser("verify-commit-a")
    commit_a.add_argument("--repo-root", required=True, type=Path)
    commit_a.add_argument(
        "--manifest-relative",
        default=DEFAULT_MANIFEST.as_posix(),
    )
    commit_a.add_argument("--anchor-commit", required=True)

    commit_b = subparsers.add_parser("verify-commit-b")
    commit_b.add_argument("--repo-root", required=True, type=Path)
    commit_b.add_argument(
        "--manifest-relative",
        default=DEFAULT_MANIFEST.as_posix(),
    )
    commit_b.add_argument("--anchor-commit", required=True)
    commit_b.add_argument("--finalize-commit", required=True)

    subparsers.add_parser("self-test")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source_schema_dir = Path(__file__).resolve().parent.parent / "schema"
    try:
        if args.command == "self-test":
            result = run_self_test(source_schema_dir)
        elif args.command == "prepare-manifest":
            result = prepare_manifest(
                args.repo_root.resolve(),
                args.manifest,
                args.updated_at,
                write=args.write,
            )
        elif args.command == "materialize":
            result = materialize(
                args.repo_root.resolve(),
                args.manifest,
                write=args.write,
            )
        elif args.command == "verify-commit-a":
            result = verify_commit_a(
                args.repo_root.resolve(),
                args.manifest_relative,
                args.anchor_commit,
            )
        else:
            result = verify_commit_b(
                args.repo_root.resolve(),
                args.manifest_relative,
                args.anchor_commit,
                args.finalize_commit,
            )
    except (FrozenSetError, OSError, KeyError, TypeError) as exc:
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
