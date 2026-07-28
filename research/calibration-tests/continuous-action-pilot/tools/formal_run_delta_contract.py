#!/usr/bin/env python3
"""Fail-closed semantics for formal-run-delta 0.1.0.

The verifier is intentionally limited to the state before candidate Commit A.
It never executes a formal input, runner, comparator, trace, or result.  A real
candidate verification does read repository bytes outside .git, including
historical run files, to recompute hashes, Schema validation, the frozen
preimage, and repository absence.  The public CLIs therefore require an
explicit repository-wide byte-read acknowledgement; only the synthetic
self-test can truthfully claim that no formal input was accessed.  Callers
must pin the two CLI entry points and this core out of band, and invoke either
entry point with Python isolated mode (-I).
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any, Callable, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA_DIR = PILOT / "schema"
TOOLS_DIR = PILOT / "tools"

SCHEMA_PATH = SCHEMA_DIR / "formal-run-delta-0.1.0.schema.json"
DENYLIST_SCHEMA_PATH = (
    SCHEMA_DIR / "formal-post-gate-absence-denylist-0.1.0.schema.json"
)
REVIEW_SCHEMA_PATH = (
    SCHEMA_DIR / "formal-run-delta-semantic-review-0.1.0.schema.json"
)
INVENTORY_SCHEMA_PATH = (
    SCHEMA_DIR / "base-post-run-completion-inventory-0.1.0.schema.json"
)
REGISTRY_SCHEMA_PATH = (
    SCHEMA_DIR / "formal-required-component-registry-0.1.0.schema.json"
)
MANAGER_PATH = TOOLS_DIR / "manage-frozen-set.py"
INVENTORY_TOOL_PATH = TOOLS_DIR / "base_post_run_inventory_contract.py"
CORE_PATH = TOOLS_DIR / "formal_run_delta_contract.py"
REGISTRY_CONTRACT_PATH = (
    PILOT / "contracts/formal-required-component-registry-0.1.0.json"
)

SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-run-delta-0.1.0.schema.json"
)
DENYLIST_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-post-gate-absence-denylist-0.1.0.schema.json"
)
REVIEW_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-run-delta-semantic-review-0.1.0.schema.json"
)
INVENTORY_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "base-post-run-completion-inventory-0.1.0.schema.json"
)
REGISTRY_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-required-component-registry-0.1.0.schema.json"
)

# These are executable trust anchors, not documentation. Before first frozen
# use, a pre-Commit-A closure fix requires new constants; after frozen use, an
# intentional contract change also requires a new artifact version.
TRUSTED_SCHEMA_SHA256 = {
    SCHEMA_PATH.as_posix(): (
        "9f4fe7db6c4367e7d978d049bc1b835788cd3cfb90ff0d1ed9f095a987cff0f2"
    ),
    DENYLIST_SCHEMA_PATH.as_posix(): (
        "5a8c16e7dc82c9517e35e20f06d5d64d4cc8b5eac406fc62ea7c46c8ee0a1f7d"
    ),
    REVIEW_SCHEMA_PATH.as_posix(): (
        "0ab272f33892175ebae1a16e84843ed2f513aaae6a576c54aa8dff75ef9c7d44"
    ),
    INVENTORY_SCHEMA_PATH.as_posix(): (
        "657eaeaad2b678ff1c755c683b109e02baa2dee7901c4e3a446887088002f1fa"
    ),
    REGISTRY_SCHEMA_PATH.as_posix(): (
        "0f5f6ef1ba9f638a7adef1ea79f970b36f3191a9ff9481076de65ee9fb35ec03"
    ),
}
TRUSTED_MANAGER_SHA256 = (
    "96f6414ef8a1f72782256af9cefe3e64854025790018e54383c13bcc90ce222b"
)
TRUSTED_INVENTORY_TOOL_SHA256 = (
    "1837e945da545b281c2fd5bcf95becae0874fc174628c996f1f8a35794dd843f"
)
TRUSTED_REGISTRY_SHA256 = (
    "9ecb305bf6b6ec00e9f71384764a6a1ca7264a9f2365539b5b07a1f75e2af855"
)

BASE_RUN_ID = "continuous-001"
CANDIDATE_RUN_ID = "continuous-002"
CANONICAL_BASE_FREEZE_COMMIT = (
    "bbea296b019ea1b5f5f3bb8cfe5937b0ff276f5b"
)
CANONICAL_BASE_FINALIZE_COMMIT = (
    "972589c6fb716932e01e09c7cefa92f59953336b"
)
CANONICAL_BASE_COMPLETION_COMMIT = (
    "c42013d5cad89811e8838696c4072f6f71a859fb"
)
BASE_RUN_ROOT = (
    PILOT / f"runs/{BASE_RUN_ID}"
).as_posix()
CANDIDATE_RUN_ROOT = (
    PILOT / f"runs/{CANDIDATE_RUN_ID}"
).as_posix()
BASE_MANIFEST = f"{BASE_RUN_ROOT}/manifest.json"
CANDIDATE_MANIFEST = f"{CANDIDATE_RUN_ROOT}/manifest.json"
DELTA_INSTANCE_PATH = (
    f"{CANDIDATE_RUN_ROOT}/inputs/formal-run-delta-v0.1.0.json"
)
PREIMAGE_REPO_PATH = (
    f"{CANDIDATE_RUN_ROOT}/inputs/frozen-set-preimage.tsv"
)
PREIMAGE_ENTRY_PATH = "inputs/frozen-set-preimage.tsv"
DELTA_ENTRY_PATH = "inputs/formal-run-delta-v0.1.0.json"
INVENTORY_ENTRY_PATH = (
    "inputs/base-continuous-001-post-run-inventory-v0.1.0.json"
)
INVENTORY_INSTANCE_PATH = f"{CANDIDATE_RUN_ROOT}/{INVENTORY_ENTRY_PATH}"
REGISTRY_ENTRY_PATH = (
    "inputs/formal-required-component-registry-v0.1.0.json"
)
REGISTRY_INSTANCE_PATH = f"{CANDIDATE_RUN_ROOT}/{REGISTRY_ENTRY_PATH}"

FORBIDDEN_REUSE_FAMILIES = (
    "actors_sessions",
    "authorization",
    "blind_response_chain",
    "dispatch_and_cohort",
    "execution_evidence",
    "execution_permit",
    "prediction_set",
    "reveal_and_closure",
)

PROTECTED_DOMAINS = (
    "analysis_boundary",
    "case_identity_source_version_and_roles",
    "conditions_and_dispatch_symmetry",
    "controlled_variable_and_counterfactual",
    "familiarity_pollution_policy",
    "formal_input_and_initial_state",
    "hard_checks_and_conclusion_rule",
    "observation_contract",
    "representation_contract",
    "research_question_and_falsifiability",
    "tolerance_and_stopping_boundary",
)

PROVENANCE_REFERENCE_ROLES = (
    "adr",
    "audit_record",
    "research_contract",
    "source_note",
    "truth_continuity_attestation",
    "verification_tool",
)
RUNTIME_BINDING_ROLES = (
    "dispatch_body",
    "dispatch_plan",
    "generator",
    "participant_contract",
    "participant_interface",
    "prompt",
    "submission_assembler",
    "task_packet",
    "truth_commitment",
)
PARTICIPANT_VISIBLE_ROLES = {
    "fixture",
    "participant_contract",
    "participant_interface",
    "prompt",
    "task_packet",
}
REQUIRED_PARTICIPANT_VISIBLE_ROLES = {
    "participant_contract",
    "participant_interface",
    "prompt",
    "task_packet",
}

# A role is not authenticated merely because the delta author wrote its name.
# Candidate manifest kind and file shape provide an independent structural
# binding; exact bytes remain covered by the two semantic reviews.
ROLE_MANIFEST_KINDS = {
    "adr": {"documentation"},
    "audit_record": {"audit"},
    "build_record": {"build_record"},
    "dispatch_body": {"source"},
    "dispatch_plan": {"execution_plan"},
    "fixture": {"fixture"},
    "generator": {"generator"},
    "other": {"documentation", "source"},
    "participant_contract": {"source"},
    "participant_interface": {"source"},
    "prompt": {"source"},
    "research_contract": {"documentation", "source"},
    "schema": {"source"},
    "source_note": {"documentation", "source"},
    "submission_assembler": {"generator"},
    "task_packet": {"task_packet"},
    "truth_commitment": {"truth"},
    "truth_continuity_attestation": {"audit", "truth"},
    "verification_tool": {"generator"},
}
ROLE_SUFFIXES = {
    "adr": {".md"},
    "dispatch_body": {".txt"},
    "schema": {".json"},
    "submission_assembler": {".py"},
    "verification_tool": {".py"},
}
POST_GATE_MANIFEST_KINDS = {
    "actor_descriptor": "formal_actor_descriptor",
    "execution_raw": "formal_raw_trace",
    "execution_result": "execution_result",
    "response_payload": "response_payload",
    "reveal": "truth_reveal",
    "submission": "role_submission",
    "submission_envelope": "submission_envelope",
}

VERSION_MATRIX = {
    "blind_response_interface": {
        "base_version": "0.1.0",
        "candidate_version": "0.1.1",
        "binding_kind": "artifact_change",
        "role": "participant_interface",
    },
    "prediction_contract_check": {
        "base_version": "0.1.0",
        "candidate_version": "0.1.1",
        "binding_kind": "artifact_change",
        "role": "audit_record",
    },
    "prediction_participant_contract": {
        "base_version": None,
        "candidate_version": "0.1.1",
        "binding_kind": "artifact_change",
        "role": "participant_contract",
    },
    "prediction_response_template": {
        "base_version": "0.1.0",
        "candidate_version": "0.1.1",
        "binding_kind": "artifact_change",
        "role": "prompt",
    },
    "protocol": {
        "base_version": "0.1.0",
        "candidate_version": "0.1.1",
        "binding_kind": "protocol",
        "role": None,
    },
    "reconstruction_contract_check": {
        "base_version": None,
        "candidate_version": "0.1.1",
        "binding_kind": "artifact_change",
        "role": "audit_record",
    },
    "reconstruction_participant_contract": {
        "base_version": None,
        "candidate_version": "0.1.1",
        "binding_kind": "artifact_change",
        "role": "participant_contract",
    },
    "reconstruction_response_template": {
        "base_version": "0.1.0",
        "candidate_version": "0.1.1",
        "binding_kind": "artifact_change",
        "role": "prompt",
    },
    "role_submission": {
        "base_version": "0.1.1",
        "candidate_version": "0.1.2",
        "binding_kind": "artifact_change",
        "role": "participant_interface",
    },
    "run_manifest": {
        "base_version": "0.1.1",
        "candidate_version": "0.1.1",
        "binding_kind": "container_excluded",
        "role": None,
    },
    "submission_assembler": {
        "base_version": "0.1.0",
        "candidate_version": "0.1.1",
        "binding_kind": "artifact_change",
        "role": "submission_assembler",
    },
    "task_packet": {
        "base_version": "0.1.2",
        "candidate_version": "0.1.2",
        "binding_kind": "artifact_change",
        "role": "task_packet",
    },
}

LEGACY_TOKENS = (
    BASE_RUN_ID,
    f"runs/{BASE_RUN_ID}",
    "blind-response-interface-0.1.0.schema.json",
    "build-role-submission.py",
    "participant-response-contract-0.1.0.schema.json",
    "reconstruction-response-template-0.1.0.schema.json",
    "response-template-0.1.0.schema.json",
    "role-submission-0.1.1.schema.json",
)

SEMVER_PATTERN = re.compile(r"^([0-9]+)\.([0-9]+)\.([0-9]+)$")
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_BASE_FREEZE_CACHE: dict[
    tuple[str, str, str, str, str, str],
    tuple[ModuleType, dict[str, Any], str],
] = {}


class DeltaContractError(RuntimeError):
    """A stable, fail-closed delta-contract failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


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


def canonical_value_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DeltaContractError(
                "JSON_DUPLICATE_KEY",
                f"duplicate JSON key {key!r}",
            )
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise DeltaContractError(
        "JSON_NONFINITE",
        f"non-finite JSON number {value!r}",
    )


def decode_json_bytes(
    raw: bytes,
    *,
    label: str,
    require_canonical: bool,
) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise DeltaContractError("BYTES_BOM", f"UTF-8 BOM: {label}")
    if b"\r" in raw:
        raise DeltaContractError("BYTES_NON_LF", f"CR or CRLF: {label}")
    if not raw.endswith(b"\n"):
        raise DeltaContractError("BYTES_FINAL_LF", f"missing final LF: {label}")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except UnicodeDecodeError as error:
        raise DeltaContractError(
            "BYTES_INVALID_UTF8",
            f"invalid UTF-8: {label}",
        ) from error
    except json.JSONDecodeError as error:
        raise DeltaContractError(
            "JSON_INVALID",
            f"invalid JSON at line {error.lineno}: {label}",
        ) from error
    if require_canonical and raw != canonical_bytes(value):
        raise DeltaContractError(
            "BYTES_NON_CANONICAL",
            f"JSON bytes are not canonical: {label}",
        )
    return value


def read_json_object(
    path: Path,
    *,
    require_canonical: bool,
) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = decode_json_bytes(
        raw,
        label=str(path),
        require_canonical=require_canonical,
    )
    if not isinstance(value, dict):
        raise DeltaContractError(
            "JSON_NOT_OBJECT",
            f"expected JSON object: {path}",
        )
    return value, raw


def _path_segments(relative: str) -> tuple[str, ...]:
    if not isinstance(relative, str) or not relative:
        raise DeltaContractError(
            "PATH_NON_CANONICAL",
            "repository path must be a nonempty string",
        )
    if "\\" in relative or ":" in relative or relative.startswith("/"):
        raise DeltaContractError(
            "PATH_NON_CANONICAL",
            f"repository path is not canonical POSIX: {relative!r}",
        )
    parts = relative.split("/")
    if any(not part or part in {".", ".."} for part in parts):
        code = "PATH_ESCAPE" if ".." in parts else "PATH_NON_CANONICAL"
        raise DeltaContractError(
            code,
            f"repository path contains a forbidden segment: {relative!r}",
        )
    if PurePosixPath(relative).as_posix() != relative:
        raise DeltaContractError(
            "PATH_NON_CANONICAL",
            f"repository path is not normalized: {relative!r}",
        )
    return tuple(parts)


def _check_case_and_symlinks(
    repo_root: Path,
    segments: Iterable[str],
    *,
    final_may_be_missing: bool,
) -> Path:
    cursor = repo_root.resolve()
    parts = tuple(segments)
    for index, segment in enumerate(parts):
        final = index == len(parts) - 1
        if cursor.is_symlink():
            raise DeltaContractError(
                "PATH_SYMLINK",
                f"symlinked path component: {cursor}",
            )
        proposed = cursor / segment
        if final and final_may_be_missing and not proposed.exists():
            return proposed
        try:
            matches = [
                child
                for child in cursor.iterdir()
                if child.name.casefold() == segment.casefold()
            ]
        except OSError as error:
            raise DeltaContractError(
                "PATH_MISSING",
                f"cannot enumerate repository path: {cursor}",
            ) from error
        if len(matches) != 1 or matches[0].name != segment:
            raise DeltaContractError(
                "PATH_CASE_MISMATCH",
                f"path spelling differs from filesystem: {segment!r}",
            )
        cursor = matches[0]
        if cursor.is_symlink():
            raise DeltaContractError(
                "PATH_SYMLINK",
                f"symlinked path component: {cursor}",
            )
    return cursor


def resolve_repo_file(repo_root: Path, relative: str) -> Path:
    root = repo_root.resolve()
    candidate = _check_case_and_symlinks(
        root,
        _path_segments(relative),
        final_may_be_missing=False,
    )
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise DeltaContractError(
            "PATH_MISSING",
            f"repository file does not exist: {relative}",
        ) from error
    if not resolved.is_relative_to(root):
        raise DeltaContractError(
            "PATH_ESCAPE",
            f"repository path escapes root: {relative}",
        )
    if not resolved.is_file():
        raise DeltaContractError(
            "PATH_NOT_FILE",
            f"repository path is not a file: {relative}",
        )
    return resolved


def resolve_repo_output(repo_root: Path, relative: str) -> Path:
    root = repo_root.resolve()
    candidate = _check_case_and_symlinks(
        root,
        _path_segments(relative),
        final_may_be_missing=True,
    )
    parent = candidate.parent.resolve(strict=True)
    if not parent.is_relative_to(root):
        raise DeltaContractError(
            "PATH_ESCAPE",
            f"output path escapes root: {relative}",
        )
    if candidate.exists() and candidate.is_symlink():
        raise DeltaContractError(
            "PATH_SYMLINK",
            f"output path is a symlink: {relative}",
        )
    return candidate


def write_bytes_exclusive(
    path: Path,
    raw: bytes,
    *,
    opener: Callable[[Path, str], Any] | None = None,
) -> None:
    """Create one file transactionally and verify its exact persisted bytes."""

    if path.exists() or path.is_symlink():
        raise DeltaContractError(
            "OUTPUT_EXISTS",
            f"refusing to overwrite: {path}",
        )
    created = False
    try:
        stream = path.open("xb") if opener is None else opener(path, "xb")
        created = True
        with stream:
            written = stream.write(raw)
            if written != len(raw):
                raise DeltaContractError(
                    "OUTPUT_PARTIAL_WRITE",
                    f"output was only partially written: {path}",
                )
        if path.read_bytes() != raw:
            raise DeltaContractError(
                "OUTPUT_READBACK_MISMATCH",
                f"persisted output differs from requested bytes: {path}",
            )
    except FileExistsError as error:
        raise DeltaContractError(
            "OUTPUT_EXISTS",
            f"refusing to overwrite: {path}",
        ) from error
    except Exception as error:
        if created:
            path.unlink(missing_ok=True)
        if isinstance(error, DeltaContractError):
            raise
        raise DeltaContractError(
            "OUTPUT_WRITE_FAILED",
            f"could not create output {path}: {error}",
        ) from error


def _parse_semver(value: str) -> tuple[int, int, int]:
    match = SEMVER_PATTERN.fullmatch(value)
    if match is None:
        raise DeltaContractError(
            "VERSION_INVALID",
            f"invalid semantic version: {value!r}",
        )
    return tuple(int(part) for part in match.groups())


def _load_trusted_schema(
    repo_root: Path,
    relative: Path,
) -> dict[str, Any]:
    relative_text = relative.as_posix()
    path = resolve_repo_file(repo_root, relative_text)
    raw = path.read_bytes()
    expected = TRUSTED_SCHEMA_SHA256[relative_text]
    if sha256_bytes(raw) != expected:
        raise DeltaContractError(
            "TRUSTED_SCHEMA_HASH_MISMATCH",
            f"trusted Schema bytes differ: {relative_text}",
        )
    value = decode_json_bytes(
        raw,
        label=relative_text,
        require_canonical=False,
    )
    if not isinstance(value, dict):
        raise DeltaContractError(
            "SCHEMA_INVALID",
            f"trusted Schema is not an object: {relative_text}",
        )
    try:
        Draft202012Validator.check_schema(value)
    except Exception as error:
        raise DeltaContractError(
            "SCHEMA_INVALID",
            f"invalid trusted Schema {relative_text}: {error}",
        ) from error
    return value


def _schema_validate(
    schema: dict[str, Any],
    document: Any,
    *,
    code: str,
    registry: Registry | None = None,
) -> None:
    validator_arguments: dict[str, Any] = {
        "format_checker": FormatChecker(),
    }
    if registry is not None:
        validator_arguments["registry"] = registry
    errors = sorted(
        Draft202012Validator(
            schema,
            **validator_arguments,
        ).iter_errors(document),
        key=lambda item: [str(part) for part in item.absolute_path],
    )
    if not errors:
        return
    error = errors[0]
    pointer = "/" + "/".join(str(part) for part in error.absolute_path)
    raise DeltaContractError(
        code,
        f"{pointer or '/'}: {error.message}",
    )


def _local_schema_registry(repo_root: Path) -> Registry:
    registry = Registry()
    schema_root = resolve_repo_file(
        repo_root,
        (SCHEMA_DIR / "run-manifest-0.1.1.schema.json").as_posix(),
    ).parent
    seen_ids: set[str] = set()
    for path in sorted(
        (
            candidate
            for candidate in schema_root.rglob("*")
            if candidate.is_file() and candidate.suffix.casefold() == ".json"
        ),
        key=lambda item: item.as_posix().casefold(),
    ):
        if path.is_symlink():
            raise DeltaContractError(
                "PATH_SYMLINK",
                f"symlinked Schema path: {path}",
            )
        value = decode_json_bytes(
            path.read_bytes(),
            label=str(path),
            require_canonical=False,
        )
        if not isinstance(value, dict):
            raise DeltaContractError(
                "SCHEMA_INVALID",
                f"local Schema is not an object: {path}",
            )
        try:
            Draft202012Validator.check_schema(value)
        except Exception as error:
            raise DeltaContractError(
                "SCHEMA_INVALID",
                f"invalid local Schema {path}: {error}",
            ) from error
        schema_id = value.get("$id")
        if not isinstance(schema_id, str):
            continue
        if schema_id in seen_ids:
            raise DeltaContractError(
                "SCHEMA_ID_DUPLICATE",
                f"duplicate local Schema id: {schema_id}",
            )
        seen_ids.add(schema_id)
        registry = registry.with_resource(
            schema_id,
            Resource.from_contents(value),
        )
    return registry


def validate_schema(
    repo_root: Path,
    document: dict[str, Any],
) -> None:
    schemas = {
        path: _load_trusted_schema(repo_root, path)
        for path in (
            SCHEMA_PATH,
            DENYLIST_SCHEMA_PATH,
            REVIEW_SCHEMA_PATH,
            INVENTORY_SCHEMA_PATH,
            REGISTRY_SCHEMA_PATH,
        )
    }
    _schema_validate(
        schemas[SCHEMA_PATH],
        document,
        code="SCHEMA_MISMATCH",
    )


def _load_frozen_manager(repo_root: Path) -> ModuleType:
    path = resolve_repo_file(repo_root, MANAGER_PATH.as_posix())
    if sha256_path(path) != TRUSTED_MANAGER_SHA256:
        raise DeltaContractError(
            "TRUSTED_MANAGER_HASH_MISMATCH",
            f"trusted freeze manager bytes differ: {MANAGER_PATH.as_posix()}",
        )
    module_name = (
        "_game_primitives_manage_frozen_set_"
        + sha256_bytes(str(path).encode("utf-8"))[:12]
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise DeltaContractError(
            "TRUSTED_MANAGER_LOAD",
            "cannot construct trusted freeze-manager module",
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    prior_dont_write_bytecode = sys.dont_write_bytecode
    try:
        # Loading a verifier dependency must not mutate the repository being
        # verified by creating an untracked __pycache__ side effect.
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except Exception as error:
        raise DeltaContractError(
            "TRUSTED_MANAGER_LOAD",
            f"cannot load trusted freeze manager: {error}",
        ) from error
    finally:
        sys.dont_write_bytecode = prior_dont_write_bytecode
    return module


def _load_inventory_contract(repo_root: Path) -> ModuleType:
    path = resolve_repo_file(repo_root, INVENTORY_TOOL_PATH.as_posix())
    if sha256_path(path) != TRUSTED_INVENTORY_TOOL_SHA256:
        raise DeltaContractError(
            "TRUSTED_INVENTORY_TOOL_HASH_MISMATCH",
            (
                "trusted completion-inventory tool bytes differ: "
                f"{INVENTORY_TOOL_PATH.as_posix()}"
            ),
        )
    module_name = (
        "_game_primitives_base_post_run_inventory_"
        + sha256_bytes(str(path).encode("utf-8"))[:12]
    )
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise DeltaContractError(
            "TRUSTED_INVENTORY_TOOL_LOAD",
            "cannot construct trusted completion-inventory module",
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    prior_dont_write_bytecode = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    except Exception as error:
        raise DeltaContractError(
            "TRUSTED_INVENTORY_TOOL_LOAD",
            f"cannot load trusted completion-inventory module: {error}",
        ) from error
    finally:
        sys.dont_write_bytecode = prior_dont_write_bytecode
    if (
        tuple(getattr(module, "FAMILY_IDS", ()))
        != FORBIDDEN_REUSE_FAMILIES
        or getattr(module, "BASE_COMPLETION_COMMIT", None)
        != CANONICAL_BASE_COMPLETION_COMMIT
    ):
        raise DeltaContractError(
            "TRUSTED_INVENTORY_TOOL_CONTRACT",
            "completion-inventory module constants differ from delta policy",
        )
    return module


def _git(
    repo_root: Path,
    arguments: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if check and result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise DeltaContractError(
            "GIT_FAILURE",
            f"git {' '.join(arguments)}: {stderr or result.returncode}",
        )
    return result


def _git_head(repo_root: Path) -> str:
    value = _git(repo_root, ["rev-parse", "HEAD"]).stdout.decode("ascii").strip()
    if not FULL_SHA_PATTERN.fullmatch(value):
        raise DeltaContractError("GIT_HEAD", "Git HEAD is not a full commit id")
    return value


def _validate_candidate_namespace_not_in_head(
    repo_root: Path,
    head: str,
) -> None:
    tree_paths = (
        _git(
            repo_root,
            ["ls-tree", "-r", "--name-only", head],
        )
        .stdout.decode("utf-8", errors="strict")
        .splitlines()
    )
    folded_root = CANDIDATE_RUN_ROOT.casefold()
    tracked = [
        path
        for path in tree_paths
        if path.casefold() == folded_root
        or path.casefold().startswith(folded_root + "/")
    ]
    if tracked:
        raise DeltaContractError(
            "CANDIDATE_NAMESPACE_ALREADY_COMMITTED",
            (
                "pre-Commit-A verification requires the candidate namespace "
                f"to be absent from HEAD; first tracked path: {tracked[0]}"
            ),
        )


def _git_file(
    manager: ModuleType,
    repo_root: Path,
    commit: str,
    path: str,
) -> bytes:
    try:
        return manager.git_file(repo_root, commit, path)
    except Exception as error:
        raise DeltaContractError(
            "BASE_GIT_FILE",
            f"cannot read {path} at {commit}",
        ) from error


def _verify_base_freeze(
    repo_root: Path,
    document: dict[str, Any],
    *,
    synthetic_test_profile: bool,
) -> tuple[ModuleType, dict[str, Any], str]:
    base = document["base_run"]
    anchor = base["freeze_commit"]
    finalize = base["finalize_commit"]
    completion = base["completion_commit"]
    if not synthetic_test_profile and (
        anchor != CANONICAL_BASE_FREEZE_COMMIT
        or finalize != CANONICAL_BASE_FINALIZE_COMMIT
        or completion != CANONICAL_BASE_COMPLETION_COMMIT
    ):
        raise DeltaContractError(
            "BASE_CANONICAL_ANCHOR_MISMATCH",
            (
                "base Commit A/B/completion differs from the canonical "
                "continuous-001 chain"
            ),
        )
    head = _git_head(repo_root)
    manager_hash = sha256_path(
        resolve_repo_file(repo_root, MANAGER_PATH.as_posix())
    )
    cache_key = (
        str(repo_root.resolve()),
        anchor,
        finalize,
        completion,
        head,
        manager_hash,
    )
    cached = _BASE_FREEZE_CACHE.get(cache_key)
    if cached is not None:
        return cached
    manager = _load_frozen_manager(repo_root)
    try:
        result = manager.verify_commit_b(
            repo_root,
            BASE_MANIFEST,
            anchor,
            finalize,
        )
        manifest = manager.load_manifest_at_commit(
            repo_root,
            finalize,
            BASE_MANIFEST,
        )
    except Exception as error:
        raise DeltaContractError(
            "BASE_FREEZE_PAIR_INVALID",
            f"base Commit A/B verification failed: {error}",
        ) from error
    if result.get("frozen_artifact_set_digest") != (
        base["frozen_artifact_set_digest"]
    ):
        raise DeltaContractError(
            "BASE_ROOT_MISMATCH",
            "declared base frozen root differs from Commit A",
        )
    if (
        manifest.get("run_id") != BASE_RUN_ID
        or manifest.get("protocol_version") != "0.1.0"
        or manifest.get("freeze_commit") != anchor
        or manifest.get("status") != "frozen"
    ):
        raise DeltaContractError(
            "BASE_MANIFEST_MISMATCH",
            "finalized base manifest does not match the delta contract",
        )
    ancestry = _git(
        repo_root,
        ["merge-base", "--is-ancestor", completion, head],
        check=False,
    )
    if ancestry.returncode != 0:
        raise DeltaContractError(
            "BASE_NOT_ANCESTOR_OF_HEAD",
            "base completion commit is not an ancestor of observed HEAD",
        )
    result_value = (manager, manifest, head)
    _BASE_FREEZE_CACHE[cache_key] = result_value
    return result_value


def _candidate_manifest(
    repo_root: Path,
    manager: ModuleType,
    base_finalize: str,
) -> tuple[dict[str, Any], Path]:
    manifest_path = resolve_repo_file(repo_root, CANDIDATE_MANIFEST)
    manifest, _ = read_json_object(
        manifest_path,
        require_canonical=True,
    )
    try:
        validated = manager.validate_manifest(
            manifest,
            manager.git_schema_files(repo_root, base_finalize),
        )
    except Exception as error:
        raise DeltaContractError(
            "CANDIDATE_MANIFEST_SCHEMA_INVALID",
            f"candidate manifest fails trusted 0.1.1 Schema: {error}",
        ) from error
    return validated, manifest_path.parent


def _validate_candidate_state(
    manifest: dict[str, Any],
    *,
    materializing: bool,
) -> None:
    expected = {
        "artifact_type": "formal_run_manifest",
        "artifact_version": "0.1.1",
        "freeze_commit": None,
        "protocol_version": "0.1.1",
        "run_id": CANDIDATE_RUN_ID,
        "schema_version": "0.1.1",
        "stage": "preparation",
        "stage_digests": [],
        "status": "preparing",
    }
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise DeltaContractError(
                "CANDIDATE_STATE_INVALID",
                f"candidate manifest {field} differs",
            )
    if manifest.get("truth_commitment") is None:
        raise DeltaContractError(
            "CANDIDATE_STATE_INVALID",
            "candidate manifest lacks a fresh truth commitment",
        )
    root = manifest.get("frozen_artifact_set_digest")
    if materializing:
        if root is not None and not re.fullmatch(r"[0-9a-f]{64}", str(root)):
            raise DeltaContractError(
                "CANDIDATE_STATE_INVALID",
                "candidate frozen root is malformed",
            )
    elif not isinstance(root, str) or not re.fullmatch(r"[0-9a-f]{64}", root):
        raise DeltaContractError(
            "CANDIDATE_STATE_INVALID",
            "bound verification requires a candidate frozen root",
        )


def _manifest_indexes(
    manifest: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_path: dict[str, dict[str, Any]] = {}
    folded_paths: set[str] = set()
    for entry in manifest.get("artifacts", []):
        if not isinstance(entry, dict):
            raise DeltaContractError(
                "MANIFEST_ARTIFACT_INVALID",
                "candidate manifest contains a non-object artifact",
            )
        artifact_id = entry.get("artifact_id")
        path = entry.get("path")
        if not isinstance(artifact_id, str) or not isinstance(path, str):
            raise DeltaContractError(
                "MANIFEST_ARTIFACT_INVALID",
                "manifest artifact lacks id or path",
            )
        _path_segments(path)
        if artifact_id in by_id:
            raise DeltaContractError(
                "MANIFEST_ARTIFACT_ID_DUPLICATE",
                f"duplicate manifest artifact id: {artifact_id}",
            )
        folded = path.casefold()
        if path in by_path or folded in folded_paths:
            raise DeltaContractError(
                "MANIFEST_PATH_CASE_COLLISION",
                f"duplicate manifest path after casefold: {path}",
            )
        by_id[artifact_id] = entry
        by_path[path] = entry
        folded_paths.add(folded)
    return by_id, by_path


def _expected_delta_entry() -> dict[str, Any]:
    return {
        "artifact_id": "formal-run-delta",
        "artifact_kind": "audit",
        "artifact_version": "0.1.0",
        "audience": ["custodian", "public_after_reveal"],
        "decision_relevant": True,
        "included_in_frozen_set": True,
        "path": DELTA_ENTRY_PATH,
        "release_stage": "preparation",
        "schema_path": SCHEMA_PATH.as_posix(),
        "schema_sha256": TRUSTED_SCHEMA_SHA256[SCHEMA_PATH.as_posix()],
        "supersedes_artifact_id": None,
    }


def _expected_preimage_entry(manager: ModuleType) -> dict[str, Any]:
    return {
        "artifact_id": "frozen-set-preimage",
        "artifact_kind": "audit",
        "artifact_version": "0.1.0",
        "audience": ["custodian", "public_after_reveal"],
        "decision_relevant": True,
        "included_in_frozen_set": False,
        "path": PREIMAGE_ENTRY_PATH,
        "release_stage": "preparation",
        "schema_path": (
            SCHEMA_DIR / manager.PREIMAGE_SCHEMA_NAME
        ).as_posix(),
        "schema_sha256": manager.PREIMAGE_SCHEMA_SHA256,
        "supersedes_artifact_id": None,
    }


def _expected_inventory_entry() -> dict[str, Any]:
    return {
        "artifact_id": "inventory.base-post-run",
        "artifact_kind": "audit",
        "artifact_version": "0.1.0",
        "audience": ["custodian", "public_after_reveal"],
        "decision_relevant": True,
        "included_in_frozen_set": True,
        "path": INVENTORY_ENTRY_PATH,
        "release_stage": "preparation",
        "schema_path": INVENTORY_SCHEMA_PATH.as_posix(),
        "schema_sha256": TRUSTED_SCHEMA_SHA256[
            INVENTORY_SCHEMA_PATH.as_posix()
        ],
        "supersedes_artifact_id": None,
    }


def _entry_without_sha(entry: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in entry.items() if key != "sha256"}


def _validate_manifest_files(
    repo_root: Path,
    manager: ModuleType,
    manifest: dict[str, Any],
    run_root: Path,
    *,
    delta_path: Path | None,
    materializing: bool,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id, by_path = _manifest_indexes(manifest)
    schema_registry = _local_schema_registry(repo_root)
    delta_entry = by_path.get(DELTA_ENTRY_PATH)
    if delta_entry is None or _entry_without_sha(delta_entry) != (
        _expected_delta_entry()
    ):
        raise DeltaContractError(
            "DELTA_NOT_REGISTERED",
            "delta manifest entry differs from the fixed contract",
        )
    preimage_entry = by_path.get(PREIMAGE_ENTRY_PATH)
    if preimage_entry is None or _entry_without_sha(preimage_entry) != (
        _expected_preimage_entry(manager)
    ):
        raise DeltaContractError(
            "PREIMAGE_ENTRY_INVALID",
            "frozen-set preimage entry differs from the fixed contract",
        )
    inventory_entry = by_path.get(INVENTORY_ENTRY_PATH)
    if inventory_entry is None or _entry_without_sha(inventory_entry) != (
        _expected_inventory_entry()
    ):
        raise DeltaContractError(
            "BASE_INVENTORY_ENTRY_INVALID",
            "base completion inventory entry differs from the fixed contract",
        )
    allowed_missing: set[str] = set()
    if materializing:
        allowed_missing.add(PREIMAGE_ENTRY_PATH)
        if delta_path is not None and not delta_path.exists():
            allowed_missing.add(DELTA_ENTRY_PATH)
    for path, entry in by_path.items():
        if path != PREIMAGE_ENTRY_PATH and (
            entry.get("included_in_frozen_set") is not True
        ):
            raise DeltaContractError(
                "MANIFEST_UNFROZEN_MEMBER",
                f"pre-A artifact is not frozen: {path}",
            )
        schema_path = entry.get("schema_path")
        schema_hash = entry.get("schema_sha256")
        if not isinstance(schema_path, str) or not isinstance(schema_hash, str):
            raise DeltaContractError(
                "ARTIFACT_SCHEMA_HASH_MISMATCH",
                f"artifact Schema binding is malformed: {path}",
            )
        resolved_schema = resolve_repo_file(repo_root, schema_path)
        actual_schema_hash = sha256_path(resolved_schema)
        if actual_schema_hash != schema_hash:
            raise DeltaContractError(
                "ARTIFACT_SCHEMA_HASH_MISMATCH",
                f"artifact Schema hash differs: {path}",
            )
        target = run_root / Path(*path.split("/"))
        if path in allowed_missing:
            continue
        target = resolve_repo_file(
            repo_root,
            target.relative_to(repo_root).as_posix(),
        )
        if sha256_path(target) != entry.get("sha256"):
            if path == DELTA_ENTRY_PATH:
                code = "DELTA_SHA_MISMATCH"
            elif path == PREIMAGE_ENTRY_PATH:
                code = "PREIMAGE_SHA_MISMATCH"
            else:
                code = "ARTIFACT_HASH_MISMATCH"
            raise DeltaContractError(
                code,
                f"manifest artifact hash differs: {path}",
            )
        if target.suffix.casefold() == ".json":
            value = decode_json_bytes(
                target.read_bytes(),
                label=str(target),
                require_canonical=True,
            )
            schema_value = decode_json_bytes(
                resolved_schema.read_bytes(),
                label=schema_path,
                require_canonical=False,
            )
            if not isinstance(schema_value, dict):
                raise DeltaContractError(
                    "ARTIFACT_SCHEMA_INVALID",
                    f"artifact Schema is not an object: {schema_path}",
                )
            try:
                _schema_validate(
                    schema_value,
                    value,
                    code="ARTIFACT_SCHEMA_VALIDATION",
                    registry=schema_registry,
                )
            except DeltaContractError:
                raise
            except Exception as error:
                raise DeltaContractError(
                    "ARTIFACT_SCHEMA_VALIDATION",
                    f"cannot resolve artifact Schema {schema_path}: {error}",
                ) from error
    registered = set(by_path)
    for path in run_root.rglob("*"):
        if path.is_symlink():
            raise DeltaContractError(
                "PATH_SYMLINK",
                f"symlink in candidate run: {path}",
            )
        if not path.is_file():
            continue
        relative = path.relative_to(run_root).as_posix()
        if relative == "manifest.json" or relative in registered:
            continue
        if (
            materializing
            and delta_path is not None
            and path.resolve() == delta_path.resolve()
        ):
            continue
        raise DeltaContractError(
            "MANIFEST_UNREGISTERED_FILE",
            f"candidate run has an unregistered file: {relative}",
        )
    return by_id, by_path


def _is_within_repo_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def _base_bytes(
    manager: ModuleType,
    repo_root: Path,
    anchor: str,
    path: str,
) -> bytes:
    _path_segments(path)
    if not _is_within_repo_prefix(path, BASE_RUN_ROOT):
        raise DeltaContractError(
            "BASE_ARTIFACT_SCOPE",
            f"base artifact is outside the frozen base run: {path}",
        )
    return _git_file(manager, repo_root, anchor, path)


def _candidate_path(repo_root: Path, path: str) -> Path:
    _path_segments(path)
    if not _is_within_repo_prefix(path, CANDIDATE_RUN_ROOT):
        raise DeltaContractError(
            "CANDIDATE_ARTIFACT_SCOPE",
            f"candidate artifact is outside the candidate run: {path}",
        )
    if path in {CANDIDATE_MANIFEST, DELTA_INSTANCE_PATH, PREIMAGE_REPO_PATH}:
        raise DeltaContractError(
            "DELTA_SCOPE_SELF_OR_CONTAINER",
            f"container or delta self entered artifact_changes: {path}",
        )
    return resolve_repo_file(repo_root, path)


def _fill_artifact_reference(
    repo_root: Path,
    manager: ModuleType,
    anchor: str,
    reference: dict[str, Any],
    *,
    base: bool,
) -> None:
    if base:
        raw = _base_bytes(
            manager,
            repo_root,
            anchor,
            reference["path"],
        )
        actual = sha256_bytes(raw)
    else:
        actual = sha256_path(_candidate_path(repo_root, reference["path"]))
    declared = reference.get("sha256")
    if declared is not None and declared != actual:
        raise DeltaContractError(
            "ARTIFACT_HASH_MISMATCH",
            f"declared artifact hash differs: {reference['path']}",
        )
    reference["sha256"] = actual


def _iter_artifact_references(
    document: dict[str, Any],
) -> Iterable[tuple[str, dict[str, Any], bool]]:
    for change in document["artifact_changes"]:
        base = change.get("base_artifact")
        candidate = change.get("candidate_artifact")
        if isinstance(base, dict):
            yield f"{change['artifact_id']}:base", base, True
        if isinstance(candidate, dict):
            yield f"{change['artifact_id']}:candidate", candidate, False
    yield (
        "base_completion_inventory",
        document["base_completion_inventory"],
        False,
    )
    yield (
        "repository_absence:denylist",
        document["repository_absence"]["denylist_contract"],
        False,
    )
    yield (
        "gate_policy:external_contract",
        document["gate_policy"][
            "external_dispatch_attestation_contract"
        ],
        False,
    )
    for review_id in ("projection", "source"):
        yield (
            f"semantic_reviews:{review_id}",
            document["semantic_reviews"][review_id]["artifact"],
            False,
        )


def _expected_reference_scope(role: str) -> str:
    if role in RUNTIME_BINDING_ROLES:
        return "runtime_binding"
    if role in PROVENANCE_REFERENCE_ROLES:
        return "provenance_reference"
    return "none"


def _validate_change(
    repo_root: Path,
    manager: ModuleType,
    anchor: str,
    base_by_path: dict[str, dict[str, Any]],
    change: dict[str, Any],
) -> None:
    base = change["base_artifact"]
    candidate = change["candidate_artifact"]
    kind = change["change_kind"]
    if kind in {
        "reused_unchanged",
        "run_rematerialized",
        "versioned_replacement",
    }:
        if not isinstance(base, dict) or not isinstance(candidate, dict):
            raise DeltaContractError(
                "CHANGE_ENDPOINTS",
                f"{kind} requires two endpoints: {change['artifact_id']}",
            )
    elif kind == "candidate_added":
        if base is not None or not isinstance(candidate, dict):
            raise DeltaContractError(
                "CHANGE_ENDPOINTS",
                f"candidate_added endpoints differ: {change['artifact_id']}",
            )
    elif kind == "base_retired":
        if not isinstance(base, dict) or candidate is not None:
            raise DeltaContractError(
                "CHANGE_ENDPOINTS",
                f"base_retired endpoints differ: {change['artifact_id']}",
            )
    else:
        raise DeltaContractError(
            "CHANGE_KIND",
            f"unknown change kind: {kind}",
        )

    if isinstance(base, dict):
        relative = base["path"][len(BASE_RUN_ROOT) + 1 :]
        entry = base_by_path.get(relative)
        if (
            entry is None
            or entry.get("included_in_frozen_set") is not True
            or base["manifest_artifact_id"] != entry.get("artifact_id")
            or base["artifact_version"] != entry.get("artifact_version")
            or base["sha256"] != entry.get("sha256")
        ):
            raise DeltaContractError(
                "BASE_MANIFEST_BINDING",
                (
                    "base endpoint does not match one frozen base manifest "
                    f"entry: {base['path']}"
                ),
            )
        actual = sha256_bytes(
            _base_bytes(manager, repo_root, anchor, base["path"])
        )
        if actual != base["sha256"]:
            raise DeltaContractError(
                "ARTIFACT_HASH_MISMATCH",
                f"base artifact hash differs: {base['path']}",
            )
    if isinstance(candidate, dict):
        if candidate["manifest_artifact_id"] != change["artifact_id"]:
            raise DeltaContractError(
                "CANDIDATE_MANIFEST_BINDING",
                (
                    "candidate endpoint manifest id differs from change id: "
                    f"{change['artifact_id']}"
                ),
            )
        actual = sha256_path(_candidate_path(repo_root, candidate["path"]))
        if actual != candidate["sha256"]:
            raise DeltaContractError(
                "ARTIFACT_HASH_MISMATCH",
                f"candidate artifact hash differs: {candidate['path']}",
            )

    if kind == "reused_unchanged":
        assert isinstance(base, dict) and isinstance(candidate, dict)
        if (
            base["artifact_version"] != candidate["artifact_version"]
            or base["sha256"] != candidate["sha256"]
            or base["path"] == candidate["path"]
        ):
            raise DeltaContractError(
                "CHANGE_KIND_MISMATCH",
                "reused_unchanged requires equal bytes/version at a new path",
            )
        if change["semantic_change"]:
            raise DeltaContractError(
                "SEMANTIC_CHANGE_MISMATCH",
                "reused_unchanged cannot be semantic",
            )
    elif kind == "run_rematerialized":
        assert isinstance(base, dict) and isinstance(candidate, dict)
        if (
            base["artifact_version"] != candidate["artifact_version"]
            or base["sha256"] == candidate["sha256"]
            or base["path"] == candidate["path"]
        ):
            raise DeltaContractError(
                "CHANGE_KIND_MISMATCH",
                "run_rematerialized requires same version and new path/bytes",
            )
        if change["semantic_change"]:
            raise DeltaContractError(
                "SEMANTIC_CHANGE_MISMATCH",
                "run_rematerialized cannot be semantic",
            )
    elif kind == "versioned_replacement":
        assert isinstance(base, dict) and isinstance(candidate, dict)
        if (
            base["path"] == candidate["path"]
            or base["sha256"] == candidate["sha256"]
            or _parse_semver(candidate["artifact_version"])
            <= _parse_semver(base["artifact_version"])
        ):
            raise DeltaContractError(
                "VERSION_NOT_INCREASED",
                "versioned replacement requires new path/bytes/version",
            )

    semantic = change["semantic_change"]
    scope = change["semantic_change_scope"]
    if semantic != (scope != "none"):
        raise DeltaContractError(
            "SEMANTIC_CHANGE_MISMATCH",
            f"semantic flag and scope differ: {change['artifact_id']}",
        )
    expected_scope = _expected_reference_scope(change["artifact_role"])
    if change["reference_scope"] != expected_scope:
        raise DeltaContractError(
            "REFERENCE_SCOPE_MISMATCH",
            (
                f"{change['artifact_role']} requires {expected_scope}, got "
                f"{change['reference_scope']}"
            ),
        )
    if (
        change["participant_visible"]
        and change["artifact_role"] not in PARTICIPANT_VISIBLE_ROLES
    ):
        raise DeltaContractError(
            "PARTICIPANT_VISIBILITY",
            f"{change['artifact_role']} cannot be participant-visible",
        )
    if (
        change["artifact_role"] in REQUIRED_PARTICIPANT_VISIBLE_ROLES
        and change["participant_visible"] is not True
    ):
        raise DeltaContractError(
            "PARTICIPANT_VISIBILITY",
            f"{change['artifact_role']} must be participant-visible",
        )


def _load_required_component_registry(
    repo_root: Path,
    document: dict[str, Any],
) -> dict[str, Any]:
    reference = document["required_component_registry"]
    expected_reference = {
        "artifact_version": "0.1.0",
        "path": REGISTRY_CONTRACT_PATH.as_posix(),
        "sha256": TRUSTED_REGISTRY_SHA256,
    }
    if (
        reference != expected_reference
        or document["required_component_registry_digest"]
        != TRUSTED_REGISTRY_SHA256
    ):
        raise DeltaContractError(
            "REQUIRED_COMPONENT_REGISTRY_BINDING",
            "required-component registry reference differs from trust root",
        )
    path = resolve_repo_file(repo_root, REGISTRY_CONTRACT_PATH.as_posix())
    raw = path.read_bytes()
    if sha256_bytes(raw) != TRUSTED_REGISTRY_SHA256:
        raise DeltaContractError(
            "TRUSTED_REGISTRY_HASH_MISMATCH",
            "required-component registry bytes differ from trust root",
        )
    registry = decode_json_bytes(
        raw,
        label=REGISTRY_CONTRACT_PATH.as_posix(),
        require_canonical=False,
    )
    if not isinstance(registry, dict):
        raise DeltaContractError(
            "REQUIRED_COMPONENT_REGISTRY_INVALID",
            "required-component registry is not an object",
        )
    schema = _load_trusted_schema(repo_root, REGISTRY_SCHEMA_PATH)
    _schema_validate(
        schema,
        registry,
        code="REQUIRED_COMPONENT_REGISTRY_SCHEMA_MISMATCH",
    )
    components = registry["components"]
    ids = [component["component_id"] for component in components]
    if (
        registry["component_count"] != len(components)
        or registry["component_order"] != "component_id_ascending"
        or ids != sorted(ids)
        or len(ids) != len(set(ids))
        or tuple(registry["protected_design_domains"])
        != PROTECTED_DOMAINS
    ):
        raise DeltaContractError(
            "REQUIRED_COMPONENT_REGISTRY_CLOSURE",
            "registry count, ordering, IDs, or protected domains differ",
        )
    by_id = {component["component_id"]: component for component in components}
    expected_external_roots = [
        {
            "canonical_path": (
                TOOLS_DIR / "formal_run_delta_contract.py"
            ).as_posix(),
            "component_id": "formal_run_delta_core",
            "required_at_invocation": True,
            "trust_model": "caller_pins_exact_bytes_out_of_band",
        },
        {
            "canonical_path": (
                TOOLS_DIR / "materialize-formal-run-delta-v0.1.0.py"
            ).as_posix(),
            "component_id": "formal_run_delta_materializer",
            "required_at_invocation": True,
            "trust_model": (
                "caller_pins_exact_bytes_out_of_band_and_invokes_"
                "python_isolated"
            ),
        },
        {
            "canonical_path": (
                TOOLS_DIR / "verify-formal-run-delta-v0.1.0.py"
            ).as_posix(),
            "component_id": "formal_run_delta_verifier",
            "required_at_invocation": True,
            "trust_model": (
                "caller_pins_exact_bytes_out_of_band_and_invokes_"
                "python_isolated"
            ),
        },
    ]
    if registry["external_trust_roots"] != expected_external_roots:
        raise DeltaContractError(
            "REQUIRED_COMPONENT_EXTERNAL_TRUST_ROOT",
            (
                "the registry must declare the core and both isolated CLI "
                "entry points as out-of-band caller trust roots"
            ),
        )
    core_root = expected_external_roots[0]
    component_paths = {
        component["canonical_path"]: component["component_id"]
        for component in components
        if isinstance(component["canonical_path"], str)
    }
    if (
        core_root["component_id"] in by_id
        or core_root["canonical_path"] in component_paths
    ):
        raise DeltaContractError(
            "REQUIRED_COMPONENT_EXTERNAL_TRUST_OVERLAP",
            "the externally pinned core must remain outside the registry cycle",
        )
    for root in expected_external_roots[1:]:
        component = by_id.get(root["component_id"])
        if (
            component is None
            or component["canonical_path"] != root["canonical_path"]
            or component["hash_state"] != "pinned"
            or not isinstance(component["expected_sha256"], str)
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_EXTERNAL_TRUST_ENTRYPOINT",
                (
                    "an externally pinned CLI root must also be recorded as "
                    f"a pinned registry component: {root['component_id']}"
                ),
            )
    review_manifest_ids = {
        "formal_run_delta_projection_review_instance": "review.projection",
        "formal_run_delta_source_review_instance": "review.source",
    }
    for component_id, manifest_id in review_manifest_ids.items():
        component = by_id.get(component_id)
        if (
            component is None
            or component["manifest_artifact_id"] != manifest_id
            or component["expected_sha256"] is not None
            or component["hash_state"]
            not in {
                "manifest_bound_at_b",
                "unresolved_blocks_commit_a",
            }
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_REVIEW_CYCLE",
                (
                    "semantic-review artifacts must bind through the candidate "
                    f"manifest without registry byte hashes: {component_id}"
                ),
            )
    for component in components:
        component_id = component["component_id"]
        binding_kind = component["binding_kind"]
        canonical_path = component["canonical_path"]
        path_pattern = component["path_pattern"]
        expected_count = component["expected_instance_count_at_b"]
        candidate_prefix = f"{CANDIDATE_RUN_ROOT}/"
        if component["required_at_b"] and expected_count != 1:
            raise DeltaContractError(
                "REQUIRED_COMPONENT_INSTANCE_COUNT",
                f"required component must have one B instance: {component_id}",
            )
        if component["expected_absent_at_b"] and expected_count != 0:
            raise DeltaContractError(
                "REQUIRED_COMPONENT_INSTANCE_COUNT",
                f"absent component must have zero B instances: {component_id}",
            )
        if binding_kind == "candidate_manifest_bound":
            if (
                not isinstance(canonical_path, str)
                or not canonical_path.startswith(candidate_prefix)
            ):
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_BINDING_SCOPE",
                    f"candidate component escaped its run: {component_id}",
                )
            expected_manifest_id = review_manifest_ids.get(
                component_id,
                component_id,
            )
            if component["manifest_artifact_id"] != expected_manifest_id:
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_MANIFEST_ALIAS",
                    f"manifest artifact ID is not the fixed mapping: {component_id}",
                )
        elif (
            binding_kind == "global_git_bound"
            and isinstance(canonical_path, str)
            and canonical_path.startswith(candidate_prefix)
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_BINDING_SCOPE",
                f"global binding entered candidate run: {component_id}",
            )
        if binding_kind == "container_excluded":
            expected_container_paths = {
                "candidate_run_manifest_instance": CANDIDATE_MANIFEST,
                "run_manifest": (
                    SCHEMA_DIR / "run-manifest-0.1.1.schema.json"
                ).as_posix(),
            }
            if canonical_path != expected_container_paths.get(component_id):
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_CONTAINER_BINDING",
                    f"container exclusion is not a fixed path: {component_id}",
                )
        if path_pattern is not None and not path_pattern.startswith(
            candidate_prefix
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_PATTERN_SCOPE",
                f"absence pattern escaped candidate run: {component_id}",
            )
        if (
            binding_kind == "candidate_manifest_bound"
            and component["hash_state"] == "pinned"
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_MANIFEST_HASH_DUPLICATION",
                (
                    "candidate-manifest components cannot duplicate their "
                    f"future byte hash in the registry: {component['component_id']}"
                ),
            )
    _validate_required_component_relationships(registry)
    return registry


def _validate_required_component_relationships(
    registry: dict[str, Any],
) -> None:
    components = registry["components"]
    by_id = {
        component["component_id"]: component
        for component in components
    }

    for component in components:
        component_id = component["component_id"]
        dependencies = component["allowed_dependency_component_ids"]
        is_manifest_container = (
            component["component_kind"] == "manifest_container"
        )
        has_container_hash_state = (
            component["hash_state"] == "container_excluded"
        )
        if is_manifest_container != has_container_hash_state:
            raise DeltaContractError(
                "REQUIRED_COMPONENT_CONTAINER_HASH_STATE",
                (
                    "manifest containers must use the non-self-hashed "
                    f"container state exclusively: {component_id}"
                ),
            )
        if has_container_hash_state and (
            component["binding_kind"] != "container_excluded"
            or component["binding_scope"] != "container_excluded"
            or component["expected_sha256"] is not None
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_CONTAINER_HASH_STATE",
                (
                    "container-excluded hash state requires an excluded "
                    f"binding and null byte hash: {component_id}"
                ),
            )

        if not component["required_at_b"]:
            expected_post_gate_state = (
                component["expected_absent_at_b"]
                and component["binding_kind"] == "post_gate_deferred"
                and component["binding_scope"] == "post_gate_runtime"
                and component["lifecycle"]
                in {"post_gate_append_only", "post_gate_runtime"}
                and component["hash_state"] == "post_gate_not_materialized"
                and component["dependency_state"] == "not_applicable"
                and not dependencies
            )
            if not expected_post_gate_state:
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_POST_GATE_STATE",
                    (
                        "post-gate components must remain absent, deferred, "
                        f"unhashed, and dependency-free at B: {component_id}"
                    ),
                )

        if dependencies != sorted(dependencies) or len(dependencies) != len(
            set(dependencies)
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_DEPENDENCY_ORDER",
                f"dependency list differs: {component_id}",
            )
        missing = [item for item in dependencies if item not in by_id]
        if missing:
            raise DeltaContractError(
                "REQUIRED_COMPONENT_DEPENDENCY_MISSING",
                f"{component_id} references unknown dependencies: {missing}",
            )
        if component["dependency_state"] == "closed" and not dependencies:
            raise DeltaContractError(
                "REQUIRED_COMPONENT_DEPENDENCY_EMPTY",
                f"closed dependency set is empty: {component_id}",
            )
        if is_manifest_container and dependencies:
            raise DeltaContractError(
                "REQUIRED_COMPONENT_CONTAINER_DEPENDENCY",
                f"manifest container has outgoing dependencies: {component_id}",
            )
        if component_id in dependencies:
            raise DeltaContractError(
                "REQUIRED_COMPONENT_DEPENDENCY_SELF_LOOP",
                f"component depends on itself: {component_id}",
            )
        for dependency in dependencies:
            target = by_id[dependency]
            if target["component_kind"] == "manifest_container":
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_CONTAINER_DEPENDENCY",
                    (
                        f"{component_id} depends on manifest container "
                        f"{dependency}"
                    ),
                )
            if component["required_at_b"] and not target["required_at_b"]:
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_DEPENDENCY_TIME_ORDER",
                    (
                        f"pre-gate component {component_id} depends on "
                        f"post-gate component {dependency}"
                    ),
                )
            if (
                component["binding_scope"]
                in {"runtime_binding", "execution_binding"}
                and target["binding_scope"] == "provenance_reference"
            ):
                raise DeltaContractError(
                    "RUNTIME_DEPENDENCY_SCOPE_VIOLATION",
                    (
                        f"{component_id} consumes provenance-only "
                        f"data component {dependency}"
                    ),
                )
            if component["dependency_state"] == "closed" and (
                target["hash_state"] == "unresolved_blocks_commit_a"
                or target["dependency_state"] == "unresolved_blocks_commit_a"
            ):
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_DEPENDENCY_TARGET_UNRESOLVED",
                    (
                        f"closed component {component_id} depends on "
                        f"unresolved component {dependency}"
                    ),
                )

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(component_id: str) -> None:
        if component_id in visited:
            return
        if component_id in visiting:
            cycle_start = stack.index(component_id)
            cycle = stack[cycle_start:] + [component_id]
            raise DeltaContractError(
                "REQUIRED_COMPONENT_DEPENDENCY_CYCLE",
                f"dependency cycle detected: {' -> '.join(cycle)}",
            )
        visiting.add(component_id)
        stack.append(component_id)
        dependencies = sorted(
            by_id[component_id]["allowed_dependency_component_ids"],
        )
        for dependency in dependencies:
            if dependency in by_id:
                visit(dependency)
        stack.pop()
        visiting.remove(component_id)
        visited.add(component_id)

    for component_id in sorted(by_id):
        visit(component_id)


def _validate_required_component_absences(
    repo_root: Path,
    registry: dict[str, Any],
) -> None:
    run_root = repo_root / Path(*CANDIDATE_RUN_ROOT.split("/"))
    prefix = f"{CANDIDATE_RUN_ROOT}/"
    for component in registry["components"]:
        if not component["expected_absent_at_b"]:
            continue
        component_id = component["component_id"]
        canonical_path = component["canonical_path"]
        if isinstance(canonical_path, str):
            target = repo_root / Path(*canonical_path.split("/"))
            if target.exists() or target.is_symlink():
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_EXPECTED_ABSENT",
                    f"post-gate component exists before A: {component_id}",
                )
            continue
        pattern = component["path_pattern"]
        if not isinstance(pattern, str) or not pattern.startswith(prefix):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_PATTERN_SCOPE",
                f"absence pattern is not candidate-scoped: {component_id}",
            )
        relative_pattern = pattern[len(prefix) :]
        matches: list[str] = []
        if run_root.exists():
            for path in run_root.rglob("*"):
                relative = path.relative_to(run_root).as_posix()
                if (
                    path.is_symlink() or path.is_file()
                ) and _path_matches(relative, relative_pattern):
                    matches.append(relative)
        if len(matches) != component["expected_instance_count_at_b"]:
            raise DeltaContractError(
                "REQUIRED_COMPONENT_PATTERN_COUNT",
                (
                    f"{component_id} expected "
                    f"{component['expected_instance_count_at_b']} matches, "
                    f"found {len(matches)}"
                ),
            )


def _unresolved_global_base_endpoints(
    document: dict[str, Any],
    registry: dict[str, Any],
) -> list[str]:
    """Return global replacements/reuses lacking a real artifact-change base."""

    changes_by_candidate_path = {
        change["candidate_artifact"]["path"]: change
        for change in document["artifact_changes"]
        if isinstance(change.get("candidate_artifact"), dict)
    }
    unresolved: list[str] = []
    for component in registry["components"]:
        if component["binding_kind"] != "global_git_bound":
            continue
        if component["change_kind"] == "candidate_added":
            continue
        component_id = component["component_id"]
        canonical_path = component["canonical_path"]
        change = changes_by_candidate_path.get(canonical_path)
        if not isinstance(change, dict):
            unresolved.append(component_id)
            continue
        base = change.get("base_artifact")
        candidate = change.get("candidate_artifact")
        if (
            not isinstance(base, dict)
            or not isinstance(candidate, dict)
            or change.get("change_kind") != component["change_kind"]
            or candidate.get("path") != canonical_path
            or candidate.get("artifact_version") != component["version"]
        ):
            unresolved.append(component_id)
            continue
        expected_sha256 = component["expected_sha256"]
        if (
            isinstance(expected_sha256, str)
            and candidate.get("sha256") != expected_sha256
        ):
            unresolved.append(component_id)
            continue
        if component["change_kind"] == "reused_unchanged" and (
            base.get("sha256") != candidate.get("sha256")
            or base.get("artifact_version")
            != candidate.get("artifact_version")
        ):
            unresolved.append(component_id)
    return unresolved


def _validate_required_components(
    repo_root: Path,
    document: dict[str, Any],
    registry: dict[str, Any],
    candidate_manifest: dict[str, Any],
    *,
    synthetic_test_profile: bool,
) -> None:
    if synthetic_test_profile:
        return
    _validate_required_component_absences(repo_root, registry)
    unresolved_hashes = [
        component["component_id"]
        for component in registry["components"]
        if component["required_at_b"]
        and component["hash_state"] == "unresolved_blocks_commit_a"
    ]
    unresolved_dependencies = [
        component["component_id"]
        for component in registry["components"]
        if component["required_at_b"]
        and component["dependency_state"] == "unresolved_blocks_commit_a"
    ]
    unresolved_base_endpoints = _unresolved_global_base_endpoints(
        document,
        registry,
    )
    if (
        unresolved_hashes
        or unresolved_dependencies
        or unresolved_base_endpoints
    ):
        raise DeltaContractError(
            "REQUIRED_COMPONENTS_UNRESOLVED",
            (
                f"{len(unresolved_hashes)} hash bindings and "
                f"{len(unresolved_dependencies)} dependency closures and "
                f"{len(unresolved_base_endpoints)} base endpoints block Commit A"
            ),
        )

    _, manifest_by_path = _manifest_indexes(candidate_manifest)
    changes_by_id = {
        change["artifact_id"]: change
        for change in document["artifact_changes"]
    }
    registry_ids = {
        component["component_id"]
        for component in registry["components"]
    }
    for component in registry["components"]:
        component_id = component["component_id"]
        canonical_path = component["canonical_path"]
        if component["expected_absent_at_b"]:
            continue
        if not component["required_at_b"]:
            continue
        if not isinstance(canonical_path, str):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_PATH_MISSING",
                f"required component lacks a canonical path: {component_id}",
            )
        target = resolve_repo_file(repo_root, canonical_path)
        expected_hash = component["expected_sha256"]
        if component["component_kind"] == "manifest_container":
            if (
                component["binding_kind"] != "container_excluded"
                or component["binding_scope"] != "container_excluded"
                or component["hash_state"] != "container_excluded"
                or expected_hash is not None
            ):
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_CONTAINER_HASH_STATE",
                    (
                        "manifest container must be present but excluded from "
                        f"its own byte-hash closure: {component_id}"
                    ),
                )
            continue
        actual_hash = sha256_path(target)
        if component["binding_kind"] == "candidate_manifest_bound":
            if (
                component["hash_state"] != "manifest_bound_at_b"
                or expected_hash is not None
            ):
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_HASH_STATE",
                    (
                        "candidate component must defer its byte hash to the "
                        f"candidate manifest: {component_id}"
                    ),
                )
            expected_hash = actual_hash
        elif (
            component["hash_state"] != "pinned"
            or not isinstance(expected_hash, str)
            or actual_hash != expected_hash
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_HASH_MISMATCH",
                f"required component hash differs: {component_id}",
            )
        if component["component_kind"] == "schema":
            value = decode_json_bytes(
                target.read_bytes(),
                label=canonical_path,
                require_canonical=False,
            )
            if not isinstance(value, dict):
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_SCHEMA_INVALID",
                    f"registered Schema is not an object: {component_id}",
                )
            try:
                Draft202012Validator.check_schema(value)
            except Exception as error:
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_SCHEMA_INVALID",
                    f"registered Schema is invalid: {component_id}: {error}",
                ) from error
            if value.get("$id") != component["schema_id"]:
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_SCHEMA_ID_MISMATCH",
                    f"registered Schema $id differs: {component_id}",
                )
        if component["binding_kind"] != "candidate_manifest_bound":
            continue
        prefix = f"{CANDIDATE_RUN_ROOT}/"
        if not canonical_path.startswith(prefix):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_MANIFEST_SCOPE",
                f"manifest-bound component escaped candidate run: {component_id}",
            )
        relative = canonical_path[len(prefix) :]
        entry = manifest_by_path.get(relative)
        manifest_id = component["manifest_artifact_id"]
        if (
            entry is None
            or entry["artifact_id"] != manifest_id
            or entry["artifact_kind"] != component["manifest_artifact_kind"]
            or entry["artifact_version"] != component["version"]
            or entry["sha256"] != expected_hash
            or entry["included_in_frozen_set"] is not True
            or entry["schema_path"] != component["schema_path"]
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_MANIFEST_BINDING",
                f"candidate manifest binding differs: {component_id}",
            )
        schema_path = component["schema_path"]
        if isinstance(schema_path, str):
            if entry["schema_sha256"] != sha256_path(
                resolve_repo_file(repo_root, schema_path)
            ):
                raise DeltaContractError(
                    "REQUIRED_COMPONENT_SCHEMA_HASH_MISMATCH",
                    f"candidate Schema binding differs: {component_id}",
                )
        change = changes_by_id.get(manifest_id)
        candidate_reference = (
            change["candidate_artifact"]
            if isinstance(change, dict)
            else None
        )
        if (
            change is None
            or not isinstance(candidate_reference, dict)
            or candidate_reference["path"] != canonical_path
            or candidate_reference["sha256"] != actual_hash
            or change["artifact_role"] != component["artifact_role"]
            or change["change_kind"] != component["change_kind"]
            or change["participant_visible"]
            is not component["participant_visible"]
            or change["reference_scope"] != component["reference_scope"]
            or change["semantic_change"] is not component["semantic_change"]
            or change["semantic_change_scope"]
            != component["semantic_change_scope"]
        ):
            raise DeltaContractError(
                "REQUIRED_COMPONENT_CHANGE_BINDING",
                f"artifact-change policy differs: {component_id}",
            )
    extra_changes = [
        change["artifact_id"]
        for change in document["artifact_changes"]
        if change["artifact_id"] not in registry_ids
        and change["artifact_id"]
        not in {
            "protected_design_source",
            "review.projection",
            "review.source",
        }
    ]
    if extra_changes:
        raise DeltaContractError(
            "REQUIRED_COMPONENT_UNREGISTERED_CHANGE",
            f"artifact changes are absent from registry: {extra_changes}",
        )


def _fill_version_matrix(
    document: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> None:
    if registry is not None:
        changes_by_path = {
            change["candidate_artifact"]["path"]: change
            for change in document["artifact_changes"]
            if isinstance(change["candidate_artifact"], dict)
        }
        rows: list[dict[str, Any]] = []
        binding_names = {
            "candidate_manifest_bound": "artifact_change",
            "container_excluded": "container_excluded",
            "global_git_bound": "registry_file",
            "post_gate_deferred": "candidate_absent_at_b",
        }
        for component in registry["components"]:
            path = component["canonical_path"]
            change = changes_by_path.get(path) if isinstance(path, str) else None
            base = change["base_artifact"] if change is not None else None
            candidate = (
                change["candidate_artifact"] if change is not None else None
            )
            legacy = VERSION_MATRIX.get(component["component_id"], {})
            rows.append(
                {
                    "artifact_change_id": (
                        change["artifact_id"] if change is not None else None
                    ),
                    "base_path": (
                        base["path"] if isinstance(base, dict) else None
                    ),
                    "base_sha256": (
                        base["sha256"] if isinstance(base, dict) else None
                    ),
                    "base_version": (
                        base["artifact_version"]
                        if isinstance(base, dict)
                        else legacy.get("base_version")
                    ),
                    "binding_kind": binding_names[
                        component["binding_kind"]
                    ],
                    "candidate_path": (
                        candidate["path"]
                        if isinstance(candidate, dict)
                        else path
                    ),
                    "candidate_sha256": (
                        candidate["sha256"]
                        if isinstance(candidate, dict)
                        else component["expected_sha256"]
                    ),
                    "candidate_version": component["version"],
                    "component_id": component["component_id"],
                }
            )
        document["version_matrix"] = rows
        return

    changes = {
        item["artifact_id"]: item
        for item in document["artifact_changes"]
    }
    rows: list[dict[str, Any]] = []
    for component, expected in sorted(VERSION_MATRIX.items()):
        binding = expected["binding_kind"]
        if binding == "protocol":
            rows.append(
                {
                    "artifact_change_id": None,
                    "base_path": None,
                    "base_sha256": None,
                    "base_version": expected["base_version"],
                    "binding_kind": binding,
                    "candidate_path": None,
                    "candidate_sha256": None,
                    "candidate_version": expected["candidate_version"],
                    "component_id": component,
                }
            )
            continue
        if binding == "container_excluded":
            rows.append(
                {
                    "artifact_change_id": None,
                    "base_path": BASE_MANIFEST,
                    "base_sha256": None,
                    "base_version": expected["base_version"],
                    "binding_kind": binding,
                    "candidate_path": CANDIDATE_MANIFEST,
                    "candidate_sha256": None,
                    "candidate_version": expected["candidate_version"],
                    "component_id": component,
                }
            )
            continue
        change = changes.get(component)
        if change is None:
            raise DeltaContractError(
                "VERSION_MATRIX_MISSING_CHANGE",
                f"version matrix lacks artifact change: {component}",
            )
        base = change["base_artifact"]
        candidate = change["candidate_artifact"]
        rows.append(
            {
                "artifact_change_id": component,
                "base_path": base["path"] if isinstance(base, dict) else None,
                "base_sha256": (
                    base["sha256"] if isinstance(base, dict) else None
                ),
                "base_version": expected["base_version"],
                "binding_kind": binding,
                "candidate_path": (
                    candidate["path"] if isinstance(candidate, dict) else None
                ),
                "candidate_sha256": (
                    candidate["sha256"] if isinstance(candidate, dict) else None
                ),
                "candidate_version": expected["candidate_version"],
                "component_id": component,
            }
        )
    document["version_matrix"] = rows


def _validate_version_matrix(
    document: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> None:
    if registry is not None:
        expected_document = copy.deepcopy(document)
        _fill_version_matrix(expected_document, registry)
        actual_rows = document["version_matrix"]
        expected_rows = expected_document["version_matrix"]
        if [row["component_id"] for row in actual_rows] != [
            row["component_id"] for row in expected_rows
        ]:
            raise DeltaContractError(
                "VERSION_MATRIX_COVERAGE",
                "version matrix component set or order differs from registry",
            )
        for actual, expected in zip(
            actual_rows,
            expected_rows,
            strict=True,
        ):
            if (
                actual["base_version"] != expected["base_version"]
                or actual["candidate_version"]
                != expected["candidate_version"]
            ):
                raise DeltaContractError(
                    "VERSION_MATRIX_VERSION",
                    (
                        "registry version transition differs: "
                        f"{actual['component_id']}"
                    ),
                )
            if actual != expected:
                raise DeltaContractError(
                    "VERSION_MATRIX_BINDING",
                    (
                        "registry component binding differs: "
                        f"{actual['component_id']}"
                    ),
                )
        return

    rows = document["version_matrix"]
    if [row["component_id"] for row in rows] != sorted(VERSION_MATRIX):
        raise DeltaContractError(
            "VERSION_MATRIX_COVERAGE",
            "version matrix component set or order differs",
        )
    changes = {
        item["artifact_id"]: item
        for item in document["artifact_changes"]
    }
    for row in rows:
        component = row["component_id"]
        expected = VERSION_MATRIX[component]
        if (
            row["base_version"] != expected["base_version"]
            or row["candidate_version"] != expected["candidate_version"]
            or row["binding_kind"] != expected["binding_kind"]
        ):
            raise DeltaContractError(
                "VERSION_MATRIX_VERSION",
                f"fixed version transition differs: {component}",
            )
        binding = expected["binding_kind"]
        if binding == "protocol":
            if any(
                row[key] is not None
                for key in (
                    "artifact_change_id",
                    "base_path",
                    "base_sha256",
                    "candidate_path",
                    "candidate_sha256",
                )
            ):
                raise DeltaContractError(
                    "VERSION_MATRIX_BINDING",
                    "protocol row contains an artifact binding",
                )
            continue
        if binding == "container_excluded":
            expected_values = {
                "artifact_change_id": None,
                "base_path": BASE_MANIFEST,
                "base_sha256": None,
                "candidate_path": CANDIDATE_MANIFEST,
                "candidate_sha256": None,
            }
            if any(row[key] != value for key, value in expected_values.items()):
                raise DeltaContractError(
                    "VERSION_MATRIX_BINDING",
                    "manifest container row differs",
                )
            continue
        change = changes.get(component)
        if change is None or change["artifact_role"] != expected["role"]:
            raise DeltaContractError(
                "VERSION_MATRIX_BINDING",
                f"matrix row binds the wrong change or role: {component}",
            )
        base = change["base_artifact"]
        candidate = change["candidate_artifact"]
        expected_row = {
            "artifact_change_id": component,
            "base_path": base["path"] if isinstance(base, dict) else None,
            "base_sha256": base["sha256"] if isinstance(base, dict) else None,
            "candidate_path": (
                candidate["path"] if isinstance(candidate, dict) else None
            ),
            "candidate_sha256": (
                candidate["sha256"] if isinstance(candidate, dict) else None
            ),
        }
        if any(row[key] != value for key, value in expected_row.items()):
            raise DeltaContractError(
                "VERSION_MATRIX_BINDING",
                f"matrix endpoint differs from artifact change: {component}",
            )
        if isinstance(base, dict):
            if base["artifact_version"] != expected["base_version"]:
                raise DeltaContractError(
                    "VERSION_MATRIX_VERSION",
                    f"base artifact version differs: {component}",
                )
        elif expected["base_version"] is not None:
            raise DeltaContractError(
                "VERSION_MATRIX_VERSION",
                f"base artifact is absent: {component}",
            )
        if not isinstance(candidate, dict) or (
            candidate["artifact_version"] != expected["candidate_version"]
        ):
            raise DeltaContractError(
                "VERSION_MATRIX_VERSION",
                f"candidate artifact version differs: {component}",
            )
        expected_kind = (
            "candidate_added"
            if expected["base_version"] is None
            else (
                "run_rematerialized"
                if expected["base_version"] == expected["candidate_version"]
                else "versioned_replacement"
            )
        )
        if change["change_kind"] != expected_kind:
            raise DeltaContractError(
                "VERSION_MATRIX_CHANGE_KIND",
                f"change kind differs: {component}",
            )


def _validate_manifest_closure(
    document: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    by_path: dict[str, dict[str, Any]],
) -> None:
    candidate_changes: dict[str, dict[str, Any]] = {}
    for change in document["artifact_changes"]:
        reference = change["candidate_artifact"]
        if not isinstance(reference, dict):
            continue
        relative = reference["path"][len(CANDIDATE_RUN_ROOT) + 1 :]
        if relative in candidate_changes:
            raise DeltaContractError(
                "CLOSURE_DUPLICATE_CANDIDATE",
                f"two changes bind the same candidate path: {relative}",
            )
        entry = by_path.get(relative)
        if entry is None:
            raise DeltaContractError(
                "CLOSURE_FORWARD_MISSING",
                f"candidate change is absent from manifest: {relative}",
            )
        if (
            entry["artifact_id"] != change["artifact_id"]
            or reference["manifest_artifact_id"] != entry["artifact_id"]
            or entry["artifact_version"] != reference["artifact_version"]
            or entry["sha256"] != reference["sha256"]
            or entry["included_in_frozen_set"] is not True
        ):
            raise DeltaContractError(
                "CLOSURE_FORWARD_MISMATCH",
                f"manifest binding differs: {relative}",
            )
        allowed_kinds = ROLE_MANIFEST_KINDS[change["artifact_role"]]
        if entry["artifact_kind"] not in allowed_kinds:
            raise DeltaContractError(
                "ROLE_MANIFEST_KIND_MISMATCH",
                (
                    f"{change['artifact_role']} cannot bind manifest kind "
                    f"{entry['artifact_kind']}: {relative}"
                ),
            )
        allowed_suffixes = ROLE_SUFFIXES.get(change["artifact_role"])
        if allowed_suffixes is not None and (
            PurePosixPath(relative).suffix.casefold() not in allowed_suffixes
        ):
            raise DeltaContractError(
                "ROLE_PATH_MISMATCH",
                (
                    f"{change['artifact_role']} has an invalid file suffix: "
                    f"{relative}"
                ),
            )
        candidate_changes[relative] = change
    for path, entry in by_path.items():
        if path == PREIMAGE_ENTRY_PATH:
            continue
        if path == DELTA_ENTRY_PATH:
            if entry["artifact_id"] != "formal-run-delta":
                raise DeltaContractError(
                    "DELTA_NOT_REGISTERED",
                    "delta manifest identity differs",
                )
            continue
        if entry["included_in_frozen_set"] is not True:
            continue
        change = candidate_changes.get(path)
        if change is None:
            raise DeltaContractError(
                "CLOSURE_REVERSE_MISSING",
                f"frozen manifest item is omitted from delta: {path}",
            )
        if by_id[entry["artifact_id"]] is not entry:
            raise DeltaContractError(
                "CLOSURE_REVERSE_MISMATCH",
                f"manifest id/path indexes disagree: {path}",
            )


def _validate_base_manifest_closure(
    document: dict[str, Any],
    base_manifest: dict[str, Any],
) -> None:
    _, base_by_path = _manifest_indexes(base_manifest)
    mapped: dict[str, str] = {}
    for change in document["artifact_changes"]:
        reference = change["base_artifact"]
        if not isinstance(reference, dict):
            continue
        relative = reference["path"][len(BASE_RUN_ROOT) + 1 :]
        if relative in mapped:
            raise DeltaContractError(
                "BASE_ARTIFACT_DUPLICATE",
                (
                    f"base manifest path is mapped by both {mapped[relative]} "
                    f"and {change['artifact_id']}: {relative}"
                ),
            )
        entry = base_by_path.get(relative)
        if (
            entry is None
            or entry.get("included_in_frozen_set") is not True
            or reference["manifest_artifact_id"] != entry.get("artifact_id")
            or reference["artifact_version"] != entry.get("artifact_version")
            or reference["sha256"] != entry.get("sha256")
        ):
            raise DeltaContractError(
                "BASE_MANIFEST_BINDING",
                f"base endpoint differs from frozen manifest: {relative}",
            )
        mapped[relative] = change["artifact_id"]
    for path, entry in base_by_path.items():
        if entry.get("included_in_frozen_set") is not True:
            continue
        if path not in mapped:
            raise DeltaContractError(
                "BASE_CLOSURE_MISSING",
                (
                    "frozen base manifest member has no replacement, reuse, "
                    f"or retirement declaration: {path}"
                ),
            )


def _json_pointer_value(document: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise DeltaContractError(
            "POINTER_INVALID",
            f"JSON Pointer must begin with '/': {pointer!r}",
        )
    current = document
    for raw_token in pointer.split("/")[1:]:
        if re.search(r"~(?![01])", raw_token):
            raise DeltaContractError(
                "POINTER_INVALID",
                f"invalid JSON Pointer escape: {pointer!r}",
            )
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise DeltaContractError(
                    "POINTER_MISSING",
                    f"JSON Pointer does not resolve: {pointer!r}",
                )
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                raise DeltaContractError(
                    "POINTER_MISSING",
                    f"array index does not resolve: {pointer!r}",
                )
            current = current[int(token)]
        else:
            raise DeltaContractError(
                "POINTER_MISSING",
                f"JSON Pointer crosses a scalar: {pointer!r}",
            )
    return current


def _source_value_sha256(
    repo_root: Path,
    manager: ModuleType,
    anchor: str,
    locator: dict[str, Any],
    *,
    base: bool,
) -> str:
    path = locator["path"]
    if base:
        raw = _base_bytes(manager, repo_root, anchor, path)
    else:
        raw = _candidate_path(repo_root, path).read_bytes()
    extraction = locator["extraction"]
    selector = locator["selector"]
    if extraction == "whole_file":
        if selector is not None:
            raise DeltaContractError(
                "SOURCE_SELECTOR",
                "whole_file requires selector=null",
            )
        return sha256_bytes(raw)
    if extraction != "canonical_json_pointer" or not isinstance(selector, str):
        raise DeltaContractError(
            "SOURCE_SELECTOR",
            "canonical_json_pointer requires a selector",
        )
    source = decode_json_bytes(
        raw,
        label=path,
        require_canonical=True,
    )
    value = _json_pointer_value(source, selector)
    return sha256_bytes(canonical_value_bytes(value))


def _fill_source_locator(
    repo_root: Path,
    manager: ModuleType,
    anchor: str,
    locator: dict[str, Any],
    *,
    base: bool,
) -> None:
    actual = _source_value_sha256(
        repo_root,
        manager,
        anchor,
        locator,
        base=base,
    )
    declared = locator.get("value_sha256")
    if declared is not None and declared != actual:
        raise DeltaContractError(
            "PROTECTED_VALUE_HASH_MISMATCH",
            f"protected source value differs: {locator['path']}",
        )
    locator["value_sha256"] = actual


def _semantic_review_input(
    document: dict[str, Any],
    candidate_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review_component_ids = {
        "formal_run_delta_projection_review_instance",
        "formal_run_delta_source_review_instance",
    }
    normalized_changes: list[dict[str, Any]] = []
    for item in document["artifact_changes"]:
        if item["artifact_id"] in {"review.projection", "review.source"}:
            continue
        normalized_changes.append(copy.deepcopy(item))
    manifest_projection: list[dict[str, Any]] = []
    if candidate_manifest is not None:
        manifest_projection = [
            copy.deepcopy(entry)
            for entry in candidate_manifest["artifacts"]
            if entry["artifact_id"]
            not in {
                "formal-run-delta",
                "frozen-set-preimage",
                "review.projection",
                "review.source",
            }
        ]
    return {
        "artifact_changes": normalized_changes,
        "base_run": document["base_run"],
        "base_completion_inventory": document[
            "base_completion_inventory"
        ],
        "base_completion_inventory_digest": document[
            "base_completion_inventory_digest"
        ],
        "candidate_run": {
            key: document["candidate_run"][key]
            for key in (
                "manifest_path",
                "manifest_schema_version",
                "run_id",
                "status_at_audit",
            )
        },
        "protected_design_assertions": [
            {
                "base_source": item["base_source"],
                "candidate_source": item["candidate_source"],
                "domain": item["domain"],
            }
            for item in document["protected_design_assertions"]
        ],
        "protocol_transition": document["protocol_transition"],
        "candidate_manifest_projection": manifest_projection,
        "gate_policy": document["gate_policy"],
        "forbidden_reuse_family_summary": document[
            "forbidden_reuse_family_summary"
        ],
        "reference_policy": document["reference_policy"],
        "reference_scan": document["reference_scan"],
        "required_component_registry": document[
            "required_component_registry"
        ],
        "required_component_registry_digest": document[
            "required_component_registry_digest"
        ],
        "repository_absence": {
            key: document["repository_absence"][key]
            for key in (
                "denylist_contract",
                "observed_head",
                "repository_scope",
                "status",
            )
        },
        # The two review artifacts contain this input digest. Their own byte
        # hashes would therefore create an unsatisfiable self-reference if
        # retained in the reviewed projection.
        "version_matrix": [
            copy.deepcopy(row)
            for row in document["version_matrix"]
            if row["component_id"] not in review_component_ids
        ],
    }


def semantic_review_input_sha256(
    document: dict[str, Any],
    candidate_manifest: dict[str, Any] | None = None,
) -> str:
    return sha256_bytes(
        canonical_value_bytes(
            _semantic_review_input(document, candidate_manifest)
        )
    )


def _validate_protected_design(
    repo_root: Path,
    manager: ModuleType,
    anchor: str,
    document: dict[str, Any],
) -> None:
    assertions = document["protected_design_assertions"]
    protected_changes = [
        change
        for change in document["artifact_changes"]
        if change["artifact_id"] == "protected_design_source"
    ]
    if len(protected_changes) != 1:
        raise DeltaContractError(
            "PROTECTED_SOURCE_BINDING",
            "protected design source must have exactly one artifact change",
        )
    protected_change = protected_changes[0]
    base_reference = protected_change["base_artifact"]
    candidate_reference = protected_change["candidate_artifact"]
    if (
        protected_change["artifact_role"] != "source_note"
        or not isinstance(base_reference, dict)
        or not isinstance(candidate_reference, dict)
        or base_reference["path"]
        != f"{BASE_RUN_ROOT}/source/source-packet.json"
    ):
        raise DeltaContractError(
            "PROTECTED_SOURCE_BINDING",
            "protected design source change differs from the fixed source",
        )
    domains = [item["domain"] for item in assertions]
    if domains != list(PROTECTED_DOMAINS):
        raise DeltaContractError(
            "PROTECTED_DOMAIN_COVERAGE",
            "protected design domains are incomplete, duplicated, or unordered",
        )
    for assertion in assertions:
        domain = assertion["domain"]
        base = assertion["base_source"]
        candidate = assertion["candidate_source"]
        expected_selector = f"/{domain}"
        if (
            base["path"] != base_reference["path"]
            or candidate["path"] != candidate_reference["path"]
            or base["extraction"] != "canonical_json_pointer"
            or candidate["extraction"] != "canonical_json_pointer"
            or base["selector"] != expected_selector
            or candidate["selector"] != expected_selector
        ):
            raise DeltaContractError(
                "PROTECTED_SOURCE_BINDING",
                f"protected locator is not canonical for domain: {domain}",
            )
        base_actual = _source_value_sha256(
            repo_root,
            manager,
            anchor,
            base,
            base=True,
        )
        candidate_actual = _source_value_sha256(
            repo_root,
            manager,
            anchor,
            candidate,
            base=False,
        )
        if (
            base_actual != base["value_sha256"]
            or candidate_actual != candidate["value_sha256"]
        ):
            raise DeltaContractError(
                "PROTECTED_VALUE_HASH_MISMATCH",
                f"protected value hash differs: {domain}",
            )
        if base_actual != candidate_actual:
            raise DeltaContractError(
                "PROTECTED_DESIGN_CHANGED",
                f"protected design changed: {domain}",
            )
        expected_claims = [
            {
                "claim_id": f"projection.{domain}",
                "review_id": "projection",
            },
            {
                "claim_id": f"source.{domain}",
                "review_id": "source",
            },
        ]
        if assertion["review_claims"] != expected_claims:
            raise DeltaContractError(
                "REVIEW_CLAIM_BINDING",
                f"protected assertion review claims differ: {domain}",
            )


def _change_for_candidate_reference(
    document: dict[str, Any],
    reference: dict[str, Any],
) -> dict[str, Any]:
    matches = [
        change
        for change in document["artifact_changes"]
        if change.get("candidate_artifact") == reference
    ]
    if len(matches) != 1:
        raise DeltaContractError(
            "REFERENCE_CHANGE_BINDING",
            f"candidate reference has {len(matches)} change bindings",
        )
    return matches[0]


def _validate_semantic_reviews(
    repo_root: Path,
    document: dict[str, Any],
    candidate_manifest: dict[str, Any],
) -> None:
    schema = _load_trusted_schema(repo_root, REVIEW_SCHEMA_PATH)
    expected_input = semantic_review_input_sha256(
        document,
        candidate_manifest,
    )
    reviewer_identifiers: list[str] = []
    reviewer_sessions: list[str] = []
    for review_id, review_kind in (
        ("projection", "projection_audit"),
        ("source", "source_audit"),
    ):
        binding = document["semantic_reviews"][review_id]
        reference = binding["artifact"]
        if (
            binding["review_id"] != review_id
            or binding["input_set_sha256"] != expected_input
        ):
            raise DeltaContractError(
                "REVIEW_INPUT_HASH_MISMATCH",
                (
                    f"delta review binding differs: {review_id}; "
                    f"declared={binding['input_set_sha256']}; "
                    f"expected={expected_input}"
                ),
            )
        change = _change_for_candidate_reference(document, reference)
        if (
            change["artifact_role"] != "audit_record"
            or change["artifact_id"] != f"review.{review_id}"
        ):
            raise DeltaContractError(
                "REVIEW_CHANGE_BINDING",
                f"review is not an audit_record: {review_id}",
            )
        path = _candidate_path(repo_root, reference["path"])
        review, _ = read_json_object(path, require_canonical=True)
        _schema_validate(
            schema,
            review,
            code="REVIEW_SCHEMA_MISMATCH",
        )
        if (
            review["review_id"] != review_id
            or review["review_kind"] != review_kind
            or review["input_set_sha256"] != expected_input
            or review["base_run_id"] != BASE_RUN_ID
            or review["candidate_run_id"] != CANDIDATE_RUN_ID
            or review["base_freeze_commit"]
            != document["base_run"]["freeze_commit"]
            or review["base_finalize_commit"]
            != document["base_run"]["finalize_commit"]
            or review["candidate_observed_head"]
            != document["repository_absence"]["observed_head"]
        ):
            raise DeltaContractError(
                "REVIEW_INPUT_HASH_MISMATCH",
                f"review inputs differ: {review_id}",
            )
        decision = _json_pointer_value(
            review,
            binding["decision_pointer"],
        )
        if decision != binding["required_decision"]:
            raise DeltaContractError(
                "REVIEW_DECISION_FAILED",
                f"semantic review did not pass: {review_id}",
            )
        expected_claims = [
            {
                "claim_id": f"{review_id}.{domain}",
                "decision": "passed",
                "domain": domain,
            }
            for domain in PROTECTED_DOMAINS
        ]
        actual_claims = [
            {
                "claim_id": claim["claim_id"],
                "decision": claim["decision"],
                "domain": claim["domain"],
            }
            for claim in review["claims"]
        ]
        if actual_claims != expected_claims:
            raise DeltaContractError(
                "REVIEW_CLAIM_COVERAGE",
                f"review claims are incomplete or failed: {review_id}",
            )
        reviewer_identifiers.append(review["reviewer"]["identifier"])
        reviewer_sessions.append(review["reviewer"]["session_id"])
    if (
        len(set(reviewer_identifiers)) != 2
        or len(set(reviewer_sessions)) != 2
    ):
        raise DeltaContractError(
            "REVIEWER_NOT_INDEPENDENT",
            "source and projection reviews reuse reviewer identity or session",
        )


def _pointer(path: tuple[str, ...]) -> str:
    if not path:
        return "/"
    return "/" + "/".join(
        token.replace("~", "~0").replace("/", "~1")
        for token in path
    )


def _token_count(value: str, token: str) -> int:
    return value.casefold().count(token.casefold())


def _json_occurrences(
    artifact_id: str,
    value: Any,
    path: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            for token in LEGACY_TOKENS:
                count = _token_count(key, token)
                if count:
                    occurrences.append(
                        {
                            "artifact_id": artifact_id,
                            "count": count,
                            "location": _pointer(path + (key,)),
                            "location_kind": "json_key",
                            "token": token,
                        }
                    )
            occurrences.extend(
                _json_occurrences(artifact_id, child, path + (key,))
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            occurrences.extend(
                _json_occurrences(
                    artifact_id,
                    child,
                    path + (str(index),),
                )
            )
    elif isinstance(value, str):
        for token in LEGACY_TOKENS:
            count = _token_count(value, token)
            if count:
                occurrences.append(
                    {
                        "artifact_id": artifact_id,
                        "count": count,
                        "location": _pointer(path),
                        "location_kind": "json_value",
                        "token": token,
                    }
                )
    return occurrences


def _text_occurrences(
    artifact_id: str,
    text: str,
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    folded = text.casefold()
    for token in LEGACY_TOKENS:
        token_folded = token.casefold()
        start = 0
        while True:
            index = folded.find(token_folded, start)
            if index < 0:
                break
            occurrences.append(
                {
                    "artifact_id": artifact_id,
                    "count": 1,
                    "location": f"char:{index}",
                    "location_kind": "text",
                    "token": token,
                }
            )
            start = index + len(token_folded)
    return occurrences


def _binding_occurrences(
    artifact_id: str,
    value: str,
    location: str,
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for token in LEGACY_TOKENS:
        count = _token_count(value, token)
        if count:
            occurrences.append(
                {
                    "artifact_id": artifact_id,
                    "count": count,
                    "location": location,
                    "location_kind": "binding_metadata",
                    "token": token,
                }
            )
    return occurrences


def _binding_tree_occurrences(
    artifact_id: str,
    value: Any,
    location: str,
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            occurrences.extend(
                _binding_occurrences(
                    artifact_id,
                    str(key),
                    f"{location}/{key}:key",
                )
            )
            occurrences.extend(
                _binding_tree_occurrences(
                    artifact_id,
                    child,
                    f"{location}/{key}",
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            occurrences.extend(
                _binding_tree_occurrences(
                    artifact_id,
                    child,
                    f"{location}/{index}",
                )
            )
    elif isinstance(value, str):
        occurrences.extend(
            _binding_occurrences(
                artifact_id,
                value,
                location,
            )
        )
    return occurrences


def _fold_python_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _fold_python_string(node.left)
        right = _fold_python_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        values: list[str] = []
        for value in node.values:
            folded = _fold_python_string(value)
            if folded is None:
                return None
            values.append(folded)
        return "".join(values)
    return None


def _python_static_occurrences(
    artifact_id: str,
    text: str,
) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        raise DeltaContractError(
            "PYTHON_SYNTAX_INVALID",
            f"candidate Python cannot be parsed: {artifact_id}: {error}",
        ) from error
    literal_folded = text.casefold()
    occurrences: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Constant, ast.BinOp, ast.JoinedStr)):
            continue
        value = _fold_python_string(node)
        if value is None:
            continue
        for token in LEGACY_TOKENS:
            count = _token_count(value, token)
            if count and token.casefold() not in literal_folded:
                occurrences.append(
                    {
                        "artifact_id": artifact_id,
                        "count": count,
                        "location": f"python-ast:line:{getattr(node, 'lineno', 0)}",
                        "location_kind": "static_expression",
                        "token": token,
                    }
                )
    return occurrences


def _reference_occurrences(
    repo_root: Path,
    document: dict[str, Any],
    candidate_by_path: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    occurrences: list[dict[str, Any]] = []
    for change in document["artifact_changes"]:
        reference = change["candidate_artifact"]
        if not isinstance(reference, dict):
            continue
        path = _candidate_path(repo_root, reference["path"])
        raw = path.read_bytes()
        if path.suffix.casefold() == ".json":
            value = decode_json_bytes(
                raw,
                label=reference["path"],
                require_canonical=True,
            )
            found = _json_occurrences(change["artifact_id"], value)
        else:
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as error:
                raise DeltaContractError(
                    "BYTES_INVALID_UTF8",
                    f"candidate text is not UTF-8: {reference['path']}",
                ) from error
            found = _text_occurrences(change["artifact_id"], text)
            if path.suffix.casefold() == ".py":
                found.extend(
                    _python_static_occurrences(change["artifact_id"], text)
                )
        # The change rationale is delta provenance, even when the endpoint is
        # consumed at runtime.  Do not launder runtime bindings through that
        # prose, but also do not reject an honest explanation such as
        # "replaces continuous-001".  Runtime hard fields and provenance prose
        # are therefore scanned as two different scopes.
        candidate_change_metadata = {
            key: change[key]
            for key in (
                "artifact_id",
                "artifact_role",
                "candidate_artifact",
                "reference_scope",
                "semantic_change_scope",
            )
        }
        found.extend(
            _binding_tree_occurrences(
                change["artifact_id"],
                candidate_change_metadata,
                "artifact_change",
            )
        )
        if candidate_by_path is not None:
            relative = reference["path"][len(CANDIDATE_RUN_ROOT) + 1 :]
            entry = candidate_by_path.get(relative)
            if entry is None:
                raise DeltaContractError(
                    "CLOSURE_FORWARD_MISSING",
                    f"candidate change is absent from manifest: {relative}",
                )
            found.extend(
                _binding_tree_occurrences(
                    change["artifact_id"],
                    entry,
                    "candidate_manifest_entry",
                )
            )
        for occurrence in found:
            if change["artifact_role"] not in PROVENANCE_REFERENCE_ROLES:
                raise DeltaContractError(
                    "REFERENCE_SCOPE_VIOLATION",
                    (
                        f"legacy token in {change['artifact_role']}: "
                        f"{reference['path']}"
                    ),
                )
        occurrences.extend(found)
        occurrences.extend(
            _binding_occurrences(
                change["artifact_id"],
                change["rationale"],
                "artifact_change/rationale",
            )
        )
    return sorted(
        occurrences,
        key=lambda item: (
            item["artifact_id"],
            item["location_kind"],
            item["location"],
            item["token"],
        ),
    )


def _validate_reference_scan(
    repo_root: Path,
    document: dict[str, Any],
    candidate_by_path: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    observed = _reference_occurrences(
        repo_root,
        document,
        candidate_by_path,
    )
    allowlist = document["reference_policy"][
        "provenance_occurrence_allowlist"
    ]
    if len(
        {
            canonical_value_bytes(item)
            for item in allowlist
        }
    ) != len(allowlist):
        raise DeltaContractError(
            "REFERENCE_ALLOWLIST_DUPLICATE",
            "provenance occurrence allowlist contains duplicates",
        )
    if allowlist != observed:
        raise DeltaContractError(
            "REFERENCE_ALLOWLIST_MISMATCH",
            "observed legacy references differ from the frozen allowlist",
        )
    expected_scan = {
        "observed_occurrences": observed,
        "status": "passed",
        "violations": [],
    }
    if document["reference_scan"] != expected_scan:
        raise DeltaContractError(
            "REFERENCE_SCAN_MISMATCH",
            "recorded reference scan differs",
        )
    return observed


def _reuse_family(entry: dict[str, Any]) -> str | None:
    text = " ".join(
        str(entry.get(key, ""))
        for key in ("artifact_id", "artifact_kind", "path")
    ).casefold()
    if "authorization" in text:
        return "authorization"
    if "execution-permit" in text or "execution_permit" in text:
        return "execution_permit"
    if "dispatch-receipt" in text or "dispatch_receipt" in text:
        return "dispatch_receipt"
    if "prediction-set-preimage" in text or "prediction_preimage" in text:
        return "prediction_preimage"
    if (
        entry.get("artifact_kind") == "actor_descriptor"
        or "actor-descriptor" in text
        or "actor_descriptor" in text
        or "session" in text
    ):
        return "actor_or_session"
    if (
        entry.get("artifact_kind") == "response_payload"
        or "raw-response" in text
        or "raw_response" in text
        or "blind-response" in text
    ):
        return "blind_response"
    if (
        entry.get("artifact_kind")
        in {
            "execution_raw",
            "submission",
            "submission_envelope",
            "trace",
        }
        or "/raw/" in text
        or "trace-bundle" in text
    ):
        return "runtime_bound_artifact"
    if (
        entry.get("artifact_kind") == "truth"
        or "sealed-truth" in text
        or "truth-commitment" in text
    ):
        return "truth_commitment"
    return None


def _verify_completion_inventory_objects(
    repo_root: Path,
    document: dict[str, Any],
    inventory: dict[str, Any],
    module: ModuleType,
) -> None:
    finalize = document["base_run"]["finalize_commit"]
    completion = document["base_run"]["completion_commit"]
    parent_line = (
        _git(
            repo_root,
            ["rev-list", "--parents", "-n", "1", completion],
        )
        .stdout.decode("ascii", errors="strict")
        .strip()
        .split()
    )
    if parent_line != [completion, finalize]:
        raise DeltaContractError(
            "BASE_COMPLETION_PARENT_MISMATCH",
            "base completion is not the direct child of Commit B",
        )
    tree_oid = (
        _git(repo_root, ["rev-parse", f"{completion}^{{tree}}"])
        .stdout.decode("ascii", errors="strict")
        .strip()
    )
    if inventory["base_tree_oid"] != tree_oid:
        raise DeltaContractError(
            "BASE_INVENTORY_TREE_MISMATCH",
            "base completion inventory tree OID differs",
        )
    status_lines = (
        _git(
            repo_root,
            [
                "diff-tree",
                "--no-commit-id",
                "--name-status",
                "-r",
                "--no-renames",
                finalize,
                completion,
                "--",
                f"{BASE_RUN_ROOT}/",
            ],
        )
        .stdout.decode("utf-8", errors="strict")
        .splitlines()
    )
    changed_paths: list[str] = []
    for line in status_lines:
        parts = line.split("\t")
        if len(parts) != 2 or parts[0] != "A":
            raise DeltaContractError(
                "BASE_INVENTORY_NON_ADDITION",
                f"base completion contains a non-addition: {line}",
            )
        changed_paths.append(parts[1])
    changed_paths.sort()
    inventory_paths = sorted(
        artifact["path"]
        for family in inventory["families"]
        for artifact in family["artifacts"]
    )
    if changed_paths != inventory_paths:
        raise DeltaContractError(
            "BASE_INVENTORY_PATH_CLOSURE",
            "base completion Git diff and inventory paths differ",
        )
    for family in inventory["families"]:
        for artifact in family["artifacts"]:
            path = artifact["path"]
            try:
                actual_family = module.classify_post_gate_path(path)
                raw = _git(
                    repo_root,
                    ["cat-file", "blob", f"{completion}:{path}"],
                ).stdout
                tree_entry = (
                    _git(
                        repo_root,
                        ["ls-tree", completion, "--", path],
                    )
                    .stdout.decode("utf-8", errors="strict")
                    .strip()
                )
                header, actual_path = tree_entry.split("\t", 1)
                mode, object_type, blob_oid = header.split()
                media_type, canonical_digest, artifact_type, artifact_version = (
                    module._payload_metadata(path, raw)
                )
                protected = module.protected_payload_fingerprint(
                    raw,
                    run_id=BASE_RUN_ID,
                )
            except Exception as error:
                raise DeltaContractError(
                    "BASE_INVENTORY_GIT_OBJECT",
                    f"cannot recompute inventory artifact {path}: {error}",
                ) from error
            expected = {
                "artifact_type": artifact_type,
                "artifact_version": artifact_version,
                "byte_length": len(raw),
                "byte_sha256": sha256_bytes(raw),
                "canonical_payload_sha256": canonical_digest,
                "git_blob_oid": blob_oid,
                "media_type": media_type,
                "path": path,
                "protected_payload_fingerprint": protected,
            }
            if (
                actual_family != family["family_id"]
                or actual_path != path
                or object_type != "blob"
                or mode not in {"100644", "100755"}
                or artifact != expected
            ):
                raise DeltaContractError(
                    "BASE_INVENTORY_ARTIFACT_MISMATCH",
                    f"inventory artifact differs from Git object: {path}",
                )


def _completion_inventory(
    repo_root: Path,
    document: dict[str, Any],
    *,
    synthetic_test_profile: bool,
) -> tuple[dict[str, Any], ModuleType]:
    reference = document["base_completion_inventory"]
    if (
        reference["path"] != INVENTORY_INSTANCE_PATH
        or reference["artifact_version"] != "0.1.0"
        or reference["manifest_artifact_id"] != "inventory.base-post-run"
        or document["base_completion_inventory_digest"]
        != reference["sha256"]
    ):
        raise DeltaContractError(
            "BASE_INVENTORY_BINDING",
            "base completion inventory reference differs from fixed binding",
        )
    change = _change_for_candidate_reference(document, reference)
    if (
        change["artifact_id"] != "inventory.base-post-run"
        or change["artifact_role"] != "audit_record"
        or change["change_kind"] != "candidate_added"
        or change["base_artifact"] is not None
        or change["participant_visible"] is not False
        or change["reference_scope"] != "provenance_reference"
        or change["semantic_change"] is not False
        or change["semantic_change_scope"] != "none"
    ):
        raise DeltaContractError(
            "BASE_INVENTORY_BINDING",
            "base completion inventory artifact-change policy differs",
        )
    path = _candidate_path(repo_root, reference["path"])
    value, raw = read_json_object(path, require_canonical=True)
    schema = _load_trusted_schema(repo_root, INVENTORY_SCHEMA_PATH)
    _schema_validate(
        schema,
        value,
        code="BASE_INVENTORY_SCHEMA_MISMATCH",
    )
    if sha256_bytes(raw) != reference["sha256"]:
        raise DeltaContractError(
            "BASE_INVENTORY_HASH_MISMATCH",
            "base completion inventory bytes differ from reference",
        )
    expected_metadata = {
        "$schema": INVENTORY_SCHEMA_ID,
        "artifact_type": "base_post_run_completion_inventory",
        "artifact_version": "0.1.0",
        "base_completion_commit": document["base_run"]["completion_commit"],
        "base_finalize_commit": document["base_run"]["finalize_commit"],
        "base_freeze_commit": document["base_run"]["freeze_commit"],
        "base_frozen_artifact_set_digest": document["base_run"][
            "frozen_artifact_set_digest"
        ],
        "base_run_id": BASE_RUN_ID,
        "classifier_profile": "continuous-action-post-run-v1",
        "formal_input_executed": False,
        "formal_result_created": False,
        "run_outcome": "invalid_before_prediction_set",
        "status": "passed",
        "unclassified_post_gate_paths": [],
    }
    for key, expected in expected_metadata.items():
        if value.get(key) != expected:
            raise DeltaContractError(
                "BASE_INVENTORY_BINDING",
                f"base completion inventory {key} differs",
            )
    module = _load_inventory_contract(repo_root)
    try:
        module._validate_inventory_mechanics(value)
        _verify_completion_inventory_objects(
            repo_root,
            document,
            value,
            module,
        )
        if not synthetic_test_profile:
            module.verify_inventory_bytes(
                repo_root,
                raw,
                require_canonical_bytes=True,
            )
    except DeltaContractError:
        raise
    except Exception as error:
        raise DeltaContractError(
            "BASE_INVENTORY_RECOMPUTATION_MISMATCH",
            f"base completion inventory verification failed: {error}",
        ) from error
    return value, module


def _reuse_family_summary(
    inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "artifact_count": family["artifact_count"],
            "family_id": family["family_id"],
            "state": family["state"],
        }
        for family in inventory["families"]
    ]


def _derive_forbidden_reuse(
    base_manifest: dict[str, Any],
    anchor: str,
    inventory: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for entry in base_manifest["artifacts"]:
        family = _reuse_family(entry)
        if family is None:
            continue
        evidence.append(
            {
                "artifact_id": entry["artifact_id"],
                "base_commit": anchor,
                "canonical_payload_sha256": None,
                "family": family,
                "git_blob_oid": None,
                "path": f"{BASE_RUN_ROOT}/{entry['path']}",
                "protected_payload_fingerprint": None,
                "sha256": entry["sha256"],
                "source_kind": "manifest_artifact",
            }
        )
    truth = base_manifest.get("truth_commitment")
    if isinstance(truth, dict):
        commitment = truth.get("commitment")
        if isinstance(commitment, str) and re.fullmatch(
            r"[0-9a-f]{64}",
            commitment,
        ):
            evidence.append(
                {
                    "artifact_id": None,
                    "base_commit": anchor,
                    "canonical_payload_sha256": None,
                    "family": "truth_commitment",
                    "git_blob_oid": None,
                    "path": None,
                    "protected_payload_fingerprint": None,
                    "sha256": commitment,
                    "source_kind": "manifest_truth_commitment",
                }
            )
    for family in inventory["families"]:
        for artifact in family["artifacts"]:
            evidence.append(
                {
                    "artifact_id": None,
                    "base_commit": inventory["base_completion_commit"],
                    "canonical_payload_sha256": artifact[
                        "canonical_payload_sha256"
                    ],
                    "family": family["family_id"],
                    "git_blob_oid": artifact["git_blob_oid"],
                    "path": artifact["path"],
                    "protected_payload_fingerprint": artifact[
                        "protected_payload_fingerprint"
                    ],
                    "sha256": artifact["byte_sha256"],
                    "source_kind": "completion_inventory_artifact",
                }
            )
    return sorted(
        evidence,
        key=lambda item: (
            item["family"],
            item["artifact_id"] or "",
            item["path"] or "",
            item["sha256"],
        ),
    )


def _candidate_truth_commitment(manifest: dict[str, Any]) -> str:
    truth = manifest.get("truth_commitment")
    if not isinstance(truth, dict):
        raise DeltaContractError(
            "CANDIDATE_STATE_INVALID",
            "candidate truth commitment is absent",
        )
    commitment = truth.get("commitment")
    if not isinstance(commitment, str) or not re.fullmatch(
        r"[0-9a-f]{64}",
        commitment,
    ):
        raise DeltaContractError(
            "CANDIDATE_STATE_INVALID",
            "candidate truth commitment is malformed",
        )
    return commitment


def _validate_forbidden_reuse(
    repo_root: Path,
    document: dict[str, Any],
    base_manifest: dict[str, Any],
    candidate_manifest: dict[str, Any],
    inventory: dict[str, Any],
    inventory_module: ModuleType,
) -> list[dict[str, Any]]:
    expected = _derive_forbidden_reuse(
        base_manifest,
        document["base_run"]["freeze_commit"],
        inventory,
    )
    if document["forbidden_reuse_evidence"] != expected:
        raise DeltaContractError(
            "FORBIDDEN_REUSE_EVIDENCE_MISMATCH",
            "recorded prohibited-reuse set differs from frozen base evidence",
        )
    expected_summary = _reuse_family_summary(inventory)
    if document["forbidden_reuse_family_summary"] != expected_summary:
        raise DeltaContractError(
            "FORBIDDEN_REUSE_SUMMARY_MISMATCH",
            "recorded completion-family summary differs from inventory",
        )
    forbidden_hashes = {item["sha256"] for item in expected}
    forbidden_canonical = {
        item["canonical_payload_sha256"]
        for item in expected
        if item["canonical_payload_sha256"] is not None
    }
    forbidden_protected = {
        item["protected_payload_fingerprint"]
        for item in expected
        if item["protected_payload_fingerprint"] is not None
    }
    for entry in candidate_manifest["artifacts"]:
        if entry["path"] in {DELTA_ENTRY_PATH, PREIMAGE_ENTRY_PATH}:
            continue
        candidate_path = resolve_repo_file(
            repo_root,
            f"{CANDIDATE_RUN_ROOT}/{entry['path']}",
        )
        raw = candidate_path.read_bytes()
        byte_digest = sha256_bytes(raw)
        if entry["sha256"] in forbidden_hashes:
            raise DeltaContractError(
                "FORBIDDEN_REUSE_DETECTED",
                f"candidate reuses prohibited base bytes: {entry['path']}",
            )
        try:
            payload = inventory_module.strict_json_bytes(raw)
            canonical_digest = sha256_bytes(
                inventory_module.canonical_json_value_bytes(payload)
            )
        except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
            canonical_digest = byte_digest
        protected_digest = inventory_module.protected_payload_fingerprint(
            raw,
            run_id=CANDIDATE_RUN_ID,
        )
        if canonical_digest in forbidden_canonical:
            raise DeltaContractError(
                "FORBIDDEN_REUSE_DETECTED",
                (
                    "candidate reuses a prohibited canonical payload: "
                    f"{entry['path']}"
                ),
            )
        if protected_digest in forbidden_protected:
            raise DeltaContractError(
                "FORBIDDEN_REUSE_DETECTED",
                (
                    "candidate reuses a prohibited protected payload: "
                    f"{entry['path']}"
                ),
            )
    candidate_commitment = _candidate_truth_commitment(candidate_manifest)
    if candidate_commitment in forbidden_hashes:
        raise DeltaContractError(
            "FORBIDDEN_REUSE_DETECTED",
            "candidate reuses the base truth commitment",
        )
    return expected


def _contains_candidate_binding(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _contains_candidate_binding(key)
            or _contains_candidate_binding(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_candidate_binding(child) for child in value)
    return isinstance(value, str) and (
        value.casefold() == CANDIDATE_RUN_ID.casefold()
        or CANDIDATE_RUN_ID.casefold() in value.casefold()
    )


def _load_denylist_contract(
    repo_root: Path,
    document: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    schema = _load_trusted_schema(repo_root, DENYLIST_SCHEMA_PATH)
    reference = document["repository_absence"]["denylist_contract"]
    change = _change_for_candidate_reference(document, reference)
    if change["artifact_role"] != "research_contract":
        raise DeltaContractError(
            "DENYLIST_CHANGE_BINDING",
            "absence denylist is not a research_contract",
        )
    contract, _ = read_json_object(
        _candidate_path(repo_root, reference["path"]),
        require_canonical=True,
    )
    _schema_validate(
        schema,
        contract,
        code="DENYLIST_SCHEMA_MISMATCH",
    )
    trusted_rules = schema["properties"]["rules"]["const"]
    if contract["rules"] != trusted_rules:
        raise DeltaContractError(
            "DENYLIST_RULE_MISMATCH",
            "denylist rules differ from the trusted Schema",
        )
    return contract, trusted_rules


def _candidate_relative(path: Path, run_root: Path) -> str | None:
    absolute = path.absolute()
    root = run_root.absolute()
    if not absolute.is_relative_to(root):
        return None
    return absolute.relative_to(root).as_posix()


def _path_matches(relative: str, pattern: str) -> bool:
    """Match the admitted repo-relative gitwildmatch subset without path drift.

    ``PurePosixPath.match`` gives ``**`` semantics that differ from gitwildmatch
    for trailing descendant patterns.  The contract currently admits ``*``,
    ``**``, and ``?`` only; unsupported gitwildmatch syntax fails closed until
    its semantics are implemented and covered by controls.
    """

    if (
        pattern.startswith(("!", "/"))
        or "\\" in pattern
        or "[" in pattern
        or "]" in pattern
    ):
        raise DeltaContractError(
            "PATH_PATTERN_UNSUPPORTED",
            f"path pattern uses unsupported gitwildmatch syntax: {pattern!r}",
        )
    _path_segments(
        pattern.replace("**", "wildcard")
        .replace("*", "wildcard")
        .replace("?", "wildcard")
    )

    folded = pattern.casefold()
    expression = ["^"]
    index = 0
    while index < len(folded):
        character = folded[index]
        if character == "*":
            star_end = index
            while star_end < len(folded) and folded[star_end] == "*":
                star_end += 1
            star_count = star_end - index
            full_segment = (
                star_count == 2
                and (index == 0 or folded[index - 1] == "/")
                and (star_end == len(folded) or folded[star_end] == "/")
            )
            if full_segment and star_end < len(folded):
                expression.append("(?:[^/]+/)*")
                index = star_end + 1
                continue
            expression.append(".*" if full_segment else "[^/]*")
            index = star_end
            continue
        if character == "?":
            expression.append("[^/]")
        else:
            expression.append(re.escape(character))
        index += 1
    expression.append("$")
    return re.fullmatch("".join(expression), relative.casefold()) is not None


def _candidate_suffix_from_repository_path(relative: str) -> str | None:
    parts = relative.split("/")
    for index, part in enumerate(parts):
        if part.casefold() == CANDIDATE_RUN_ID.casefold():
            suffix = "/".join(parts[index + 1 :])
            return suffix or None
    return None


def _post_gate_path_family(
    relative: str,
    manager: ModuleType,
) -> str | None:
    folded = relative.casefold()
    for exact in manager.POST_GATE_PATHS:
        if folded == str(exact).casefold():
            return "trusted_manager_post_gate_path"
    for prefix in manager.POST_GATE_PREFIXES:
        if folded.startswith(str(prefix).casefold()):
            return "trusted_manager_post_gate_prefix"
    return None


def _permissive_json_value(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8-sig")
        return json.loads(
            text,
            object_pairs_hook=_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        DeltaContractError,
    ):
        return None


def _repository_absence_scan(
    repo_root: Path,
    run_root: Path,
    rules: list[dict[str, Any]],
    candidate_manifest: dict[str, Any],
    manager: ModuleType,
) -> tuple[list[dict[str, Any]], str]:
    forbidden_types = {
        artifact_type
        for rule in rules
        for artifact_type in rule["artifact_types"]
    }
    forbidden_text_signatures = {
        value.casefold()
        for value in forbidden_types
    }
    for rule in rules:
        for pattern in rule["path_patterns"]:
            stem = PurePosixPath(pattern).name
            stem = stem.replace("*", "").removesuffix(".json")
            if stem:
                forbidden_text_signatures.add(stem.casefold())
    matches: list[dict[str, Any]] = []
    snapshot: list[dict[str, Any]] = []
    tracked_head_paths = set(
        _git(
            repo_root,
            ["ls-tree", "-r", "--name-only", "HEAD"],
        )
        .stdout.decode("utf-8", errors="strict")
        .splitlines()
    )
    container_paths = {
        "manifest.json",
        DELTA_ENTRY_PATH,
        PREIMAGE_ENTRY_PATH,
    }
    _, manifest_by_path = _manifest_indexes(candidate_manifest)
    for path in run_root.rglob("*"):
        if path.is_symlink():
            raise DeltaContractError(
                "PATH_SYMLINK",
                f"symlink in candidate namespace: {path}",
            )
        if not path.is_file():
            continue
        relative = path.relative_to(run_root).as_posix()
        artifact_type: str | None = None
        if path.suffix.casefold() == ".json":
            value = decode_json_bytes(
                path.read_bytes(),
                label=relative,
                require_canonical=True,
            )
            if isinstance(value, dict) and isinstance(
                value.get("artifact_type"),
                str,
            ):
                artifact_type = value["artifact_type"]
        else:
            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = ""
            folded_text = text.casefold()
            if (
                CANDIDATE_RUN_ID.casefold() in folded_text
                and any(
                    signature in folded_text
                    for signature in forbidden_text_signatures
                )
            ):
                matches.append(
                    {
                        "absence_type": "candidate_bound_non_json",
                        "match_kind": "text_signature",
                        "path": relative,
                    }
                )
        broad_family = _post_gate_path_family(relative, manager)
        if broad_family is not None:
            matches.append(
                {
                    "absence_type": broad_family,
                    "match_kind": "broad_path",
                    "path": relative,
                }
            )
        for rule in rules:
            if any(
                _path_matches(relative, pattern)
                for pattern in rule["path_patterns"]
            ):
                matches.append(
                    {
                        "absence_type": rule["absence_type"],
                        "match_kind": "path",
                        "path": relative,
                    }
                )
            if artifact_type in rule["artifact_types"]:
                matches.append(
                    {
                        "absence_type": rule["absence_type"],
                        "artifact_type": artifact_type,
                        "match_kind": "artifact_type",
                        "path": relative,
                    }
                )
        manifest_entry = manifest_by_path.get(relative)
        if manifest_entry is not None:
            forbidden_kind = POST_GATE_MANIFEST_KINDS.get(
                manifest_entry["artifact_kind"]
            )
            if forbidden_kind is not None:
                matches.append(
                    {
                        "absence_type": forbidden_kind,
                        "artifact_type": artifact_type,
                        "match_kind": "manifest_artifact_kind",
                        "path": relative,
                    }
                )
        if relative not in container_paths:
            snapshot.append(
                {
                    "artifact_type": artifact_type,
                    "path": relative,
                    "sha256": sha256_path(path),
                }
            )

    # Candidate-bound spillover is checked repository-wide, for every file
    # extension. JSON decoding is permissive here so BOM/CRLF cannot hide a
    # forbidden type; malformed candidate-bound JSON fails closed.
    for path in repo_root.rglob("*"):
        relative_repo = path.relative_to(repo_root).as_posix()
        if any(part.casefold() == ".git" for part in path.parts):
            continue
        if _candidate_relative(path, run_root) is not None:
            continue
        suffix = _candidate_suffix_from_repository_path(relative_repo)
        if path.is_symlink():
            if suffix is not None:
                matches.append(
                    {
                        "absence_type": "candidate_bound_symlink",
                        "match_kind": "repository_symlink",
                        "path": relative_repo,
                    }
                )
            continue
        if not path.is_file():
            continue
        if suffix is not None:
            broad_family = _post_gate_path_family(suffix, manager)
            if broad_family is not None:
                matches.append(
                    {
                        "absence_type": broad_family,
                        "match_kind": "repository_broad_path",
                        "path": relative_repo,
                    }
                )
            for rule in rules:
                if any(
                    _path_matches(suffix, pattern)
                    for pattern in rule["path_patterns"]
                ):
                    matches.append(
                        {
                            "absence_type": rule["absence_type"],
                            "match_kind": "repository_path",
                            "path": relative_repo,
                        }
                    )
        raw = path.read_bytes()
        if path.suffix.casefold() != ".json":
            # A tracked source/tool/document may legitimately describe the
            # candidate protocol and post-gate artifact types.  The text
            # signature heuristic is for untracked spillover, or for a file
            # whose repository path itself binds the candidate namespace.
            # JSON remains structurally inspected regardless of tracked state.
            if suffix is None and relative_repo in tracked_head_paths:
                continue
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                if CANDIDATE_RUN_ID.encode("ascii") in raw:
                    matches.append(
                        {
                            "absence_type": "candidate_bound_binary",
                            "match_kind": "repository_binary_binding",
                            "path": relative_repo,
                        }
                    )
                continue
            folded_text = text.casefold()
            if (
                CANDIDATE_RUN_ID.casefold() in folded_text
                and any(
                    signature in folded_text
                    for signature in forbidden_text_signatures
                )
            ):
                matches.append(
                    {
                        "absence_type": "candidate_bound_non_json",
                        "match_kind": "repository_text_signature",
                        "path": relative_repo,
                    }
                )
            continue
        value = _permissive_json_value(raw)
        raw_text = raw.decode("utf-8", errors="ignore")
        candidate_hint = (
            suffix is not None
            or CANDIDATE_RUN_ID.casefold() in raw_text.casefold()
        )
        if value is None:
            if candidate_hint:
                matches.append(
                    {
                        "absence_type": "candidate_bound_unreadable_json",
                        "match_kind": "repository_json_decode",
                        "path": relative_repo,
                    }
                )
            continue
        artifact_type = (
            value.get("artifact_type") if isinstance(value, dict) else None
        )
        if (
            artifact_type in forbidden_types
            and (
                candidate_hint
                or _contains_candidate_binding(value)
            )
        ):
            matches.append(
                {
                    "artifact_type": artifact_type,
                    "match_kind": "candidate_bound_repository_json",
                    "path": relative_repo,
                }
            )
    matches.sort(key=canonical_value_bytes)
    snapshot.sort(key=lambda item: item["path"])
    return matches, sha256_bytes(canonical_value_bytes(snapshot))


def _validate_repository_absence(
    repo_root: Path,
    run_root: Path,
    document: dict[str, Any],
    head: str,
    candidate_manifest: dict[str, Any],
    manager: ModuleType,
) -> None:
    _, rules = _load_denylist_contract(repo_root, document)
    matches, snapshot = _repository_absence_scan(
        repo_root,
        run_root,
        rules,
        candidate_manifest,
        manager,
    )
    recorded = document["repository_absence"]
    if recorded["observed_head"] != head:
        raise DeltaContractError(
            "OBSERVED_HEAD_MISMATCH",
            "repository absence observed_head differs from Git HEAD",
        )
    if recorded["scan_snapshot_sha256"] != snapshot:
        raise DeltaContractError(
            "ABSENCE_SNAPSHOT_MISMATCH",
            "repository absence snapshot differs",
        )
    if matches:
        first = matches[0]
        raise DeltaContractError(
            "ABSENCE_MATCH",
            f"forbidden pre-A artifact exists: {first['path']}",
        )
    if recorded["matches"] != []:
        raise DeltaContractError(
            "ABSENCE_RECORDED_MATCH",
            "recorded repository absence matches are not empty",
        )


def _validate_gate_policy(
    repo_root: Path,
    document: dict[str, Any],
) -> None:
    reference = document["gate_policy"][
        "external_dispatch_attestation_contract"
    ]
    change = _change_for_candidate_reference(document, reference)
    if change["artifact_role"] != "research_contract":
        raise DeltaContractError(
            "EXTERNAL_CONTRACT_BINDING",
            "external attestation contract is not a research_contract",
        )
    value, _ = read_json_object(
        _candidate_path(repo_root, reference["path"]),
        require_canonical=True,
    )
    if (
        value.get("artifact_type")
        != "external_dispatch_attestation_contract"
        or value.get("artifact_version") != "0.1.0"
    ):
        raise DeltaContractError(
            "EXTERNAL_CONTRACT_BINDING",
            "external attestation contract identity differs",
        )


def _validate_preimage_binding(
    repo_root: Path,
    manager: ModuleType,
    manifest: dict[str, Any],
    run_root: Path,
    delta_path: Path,
) -> tuple[str, list[str]]:
    def read_artifact(path: str) -> bytes:
        target = resolve_repo_file(
            repo_root,
            (run_root / Path(*path.split("/")))
            .relative_to(repo_root)
            .as_posix(),
        )
        return target.read_bytes()

    try:
        expected_preimage, members = manager.build_preimage(
            manifest,
            read_artifact,
        )
        preimage_entry = manager.preimage_entry(manifest)
    except Exception as error:
        raise DeltaContractError(
            "PREIMAGE_BUILD_FAILED",
            f"cannot build canonical candidate preimage: {error}",
        ) from error
    actual_preimage = resolve_repo_file(
        repo_root,
        PREIMAGE_REPO_PATH,
    ).read_bytes()
    if actual_preimage != expected_preimage:
        raise DeltaContractError(
            "PREIMAGE_BYTES_NONCANONICAL",
            "candidate preimage bytes differ from the manifest projection",
        )
    digest = sha256_bytes(expected_preimage)
    if preimage_entry.get("sha256") != digest:
        raise DeltaContractError(
            "PREIMAGE_SHA_MISMATCH",
            "preimage manifest hash differs from its bytes",
        )
    if manifest.get("frozen_artifact_set_digest") != digest:
        raise DeltaContractError(
            "FROZEN_ROOT_MISMATCH",
            "candidate frozen root differs from canonical preimage",
        )
    delta_hash = sha256_path(delta_path)
    delta_entry = [
        entry
        for entry in manifest["artifacts"]
        if entry.get("path") == DELTA_ENTRY_PATH
    ]
    if len(delta_entry) != 1 or delta_entry[0].get("sha256") != delta_hash:
        raise DeltaContractError(
            "DELTA_SHA_MISMATCH",
            "manifest does not bind the exact delta bytes",
        )
    expected_line = f"{DELTA_ENTRY_PATH}\t{delta_hash}\n".encode("utf-8")
    if expected_preimage.count(expected_line) != 1:
        raise DeltaContractError(
            "DELTA_PREIMAGE_BINDING",
            "canonical preimage does not contain exactly one delta line",
        )
    if PREIMAGE_ENTRY_PATH in members or (
        PREIMAGE_ENTRY_PATH.encode("utf-8") + b"\t"
    ) in expected_preimage:
        raise DeltaContractError(
            "PREIMAGE_SELF_INCLUDED",
            "frozen-set preimage includes itself",
        )
    return digest, members


def _validate_static_policy(document: dict[str, Any]) -> None:
    if document["verification_scope"] != "pre_commit_a_only":
        raise DeltaContractError(
            "VERIFICATION_SCOPE",
            "formal-run-delta verifier is pre-Commit-A only",
        )
    if document["delta_instance_path"] != DELTA_INSTANCE_PATH:
        raise DeltaContractError(
            "DELTA_PATH",
            "formal-run-delta instance path differs",
        )
    if document["candidate_run"]["frozen_set_preimage_path"] != (
        PREIMAGE_REPO_PATH
    ):
        raise DeltaContractError(
            "PREIMAGE_PATH",
            "candidate preimage path differs",
        )
    if document["reference_policy"]["provenance_reference_roles"] != list(
        PROVENANCE_REFERENCE_ROLES
    ):
        raise DeltaContractError(
            "PROVENANCE_SCOPE",
            "provenance roles differ from the fixed policy",
        )
    if document["reference_policy"]["runtime_binding_roles"] != list(
        RUNTIME_BINDING_ROLES
    ):
        raise DeltaContractError(
            "RUNTIME_SCOPE",
            "runtime roles differ from the fixed policy",
        )
    if document["protocol_transition"] != {
        "from": "0.1.0",
        "to": "0.1.1",
    }:
        raise DeltaContractError(
            "PROTOCOL_VERSION",
            "protocol transition differs",
        )


def _validate_delta_path(
    repo_root: Path,
    document: dict[str, Any],
    delta_path: Path | None,
) -> Path:
    if delta_path is None:
        raise DeltaContractError(
            "DELTA_PATH",
            "formal-run-delta path is required",
        )
    expected = repo_root / Path(*DELTA_INSTANCE_PATH.split("/"))
    if delta_path.resolve() != expected.resolve():
        raise DeltaContractError(
            "DELTA_PATH",
            "formal-run-delta path is not the fixed candidate path",
        )
    if document["delta_instance_path"] != DELTA_INSTANCE_PATH:
        raise DeltaContractError(
            "DELTA_PATH",
            "delta document declares a different path",
        )
    return delta_path


def validate_document(
    repo_root: Path,
    document: dict[str, Any],
    *,
    delta_path: Path | None,
    materializing: bool,
    synthetic_test_profile: bool = False,
    require_semantic_reviews: bool = True,
) -> dict[str, Any]:
    validate_schema(repo_root, document)
    _validate_static_policy(document)
    delta_path = _validate_delta_path(repo_root, document, delta_path)

    manager, base_manifest, head = _verify_base_freeze(
        repo_root,
        document,
        synthetic_test_profile=synthetic_test_profile,
    )
    _validate_candidate_namespace_not_in_head(repo_root, head)
    _, base_by_path = _manifest_indexes(base_manifest)
    candidate_manifest, run_root = _candidate_manifest(
        repo_root,
        manager,
        document["base_run"]["finalize_commit"],
    )
    _validate_candidate_state(
        candidate_manifest,
        materializing=materializing,
    )
    if document["repository_absence"]["observed_head"] != head:
        raise DeltaContractError(
            "OBSERVED_HEAD_MISMATCH",
            "repository absence observed_head differs from Git HEAD",
        )
    if (
        document["candidate_run"]["freeze_commit_at_audit"] is not None
        or document["candidate_run"]["status_at_audit"] != "preparing"
    ):
        raise DeltaContractError(
            "CANDIDATE_STATE_INVALID",
            "delta candidate state is not pre-A preparing",
        )

    ids = [item["artifact_id"] for item in document["artifact_changes"]]
    if len(ids) != len(set(ids)):
        raise DeltaContractError(
            "ARTIFACT_ID_DUPLICATE",
            "artifact change IDs are not unique",
        )
    candidate_paths = [
        item["candidate_artifact"]["path"]
        for item in document["artifact_changes"]
        if isinstance(item["candidate_artifact"], dict)
    ]
    if len(candidate_paths) != len(
        {path.casefold() for path in candidate_paths}
    ):
        raise DeltaContractError(
            "PATH_DUPLICATE_CASEFOLD",
            "candidate paths collide after casefold",
        )
    for change in document["artifact_changes"]:
        _validate_change(
            repo_root,
            manager,
            document["base_run"]["freeze_commit"],
            base_by_path,
            change,
        )
    for _, reference, base in _iter_artifact_references(document):
        if base:
            actual = sha256_bytes(
                _base_bytes(
                    manager,
                    repo_root,
                    document["base_run"]["freeze_commit"],
                    reference["path"],
                )
            )
        else:
            actual = sha256_path(
                _candidate_path(repo_root, reference["path"])
            )
        if reference["sha256"] != actual:
            raise DeltaContractError(
                "ARTIFACT_HASH_MISMATCH",
                f"artifact reference hash differs: {reference['path']}",
            )

    registry = _load_required_component_registry(repo_root, document)
    _validate_version_matrix(document, registry)
    by_id, by_path = _validate_manifest_files(
        repo_root,
        manager,
        candidate_manifest,
        run_root,
        delta_path=delta_path,
        materializing=materializing,
    )
    _validate_manifest_closure(document, by_id, by_path)
    _validate_base_manifest_closure(document, base_manifest)
    _validate_required_components(
        repo_root,
        document,
        registry,
        candidate_manifest,
        synthetic_test_profile=synthetic_test_profile,
    )
    _validate_protected_design(
        repo_root,
        manager,
        document["base_run"]["freeze_commit"],
        document,
    )
    if require_semantic_reviews:
        _validate_semantic_reviews(repo_root, document, candidate_manifest)
    _validate_reference_scan(repo_root, document, by_path)
    inventory, inventory_module = _completion_inventory(
        repo_root,
        document,
        synthetic_test_profile=synthetic_test_profile,
    )
    _validate_forbidden_reuse(
        repo_root,
        document,
        base_manifest,
        candidate_manifest,
        inventory,
        inventory_module,
    )
    _validate_repository_absence(
        repo_root,
        run_root,
        document,
        head,
        candidate_manifest,
        manager,
    )
    _validate_gate_policy(repo_root, document)

    binding: dict[str, Any] = {
        "base_finalize_commit": document["base_run"]["finalize_commit"],
        "candidate_status": "preparing",
        "observed_head": head,
        "trust_profile": (
            "synthetic_test"
            if synthetic_test_profile
            else "canonical_continuous_001"
        ),
        "verification_scope": "pre_commit_a_only",
    }
    if not materializing:
        root, members = _validate_preimage_binding(
            repo_root,
            manager,
            candidate_manifest,
            run_root,
            delta_path,
        )
        binding.update(
            {
                "frozen_artifact_count": len(members),
                "frozen_artifact_set_digest": root,
            }
        )
    return binding


def materialize_document(
    repo_root: Path,
    draft: dict[str, Any],
    *,
    output_path: Path,
    synthetic_test_profile: bool = False,
    require_semantic_reviews: bool = True,
) -> dict[str, Any]:
    document = copy.deepcopy(draft)
    document.setdefault("$schema", SCHEMA_ID)
    document["materialization_status"] = "materialized_unbound"

    # The base pair is verified before it is permitted to supply any bytes.
    manager, base_manifest, head = _verify_base_freeze(
        repo_root,
        document,
        synthetic_test_profile=synthetic_test_profile,
    )
    anchor = document["base_run"]["freeze_commit"]
    for _, reference, base in _iter_artifact_references(document):
        _fill_artifact_reference(
            repo_root,
            manager,
            anchor,
            reference,
            base=base,
        )
    for assertion in document["protected_design_assertions"]:
        _fill_source_locator(
            repo_root,
            manager,
            anchor,
            assertion["base_source"],
            base=True,
        )
        _fill_source_locator(
            repo_root,
            manager,
            anchor,
            assertion["candidate_source"],
            base=False,
        )
    registry = _load_required_component_registry(repo_root, document)
    _fill_version_matrix(document, registry)
    inventory, _ = _completion_inventory(
        repo_root,
        document,
        synthetic_test_profile=synthetic_test_profile,
    )
    document["forbidden_reuse_evidence"] = _derive_forbidden_reuse(
        base_manifest,
        anchor,
        inventory,
    )
    document["forbidden_reuse_family_summary"] = (
        _reuse_family_summary(inventory)
    )
    candidate_manifest, run_root = _candidate_manifest(
        repo_root,
        manager,
        document["base_run"]["finalize_commit"],
    )
    _, candidate_by_path = _manifest_indexes(candidate_manifest)
    occurrences = _reference_occurrences(
        repo_root,
        document,
        candidate_by_path,
    )
    document["reference_scan"] = {
        "observed_occurrences": occurrences,
        "status": "passed",
        "violations": [],
    }
    _, rules = _load_denylist_contract(repo_root, document)
    matches, snapshot = _repository_absence_scan(
        repo_root,
        run_root,
        rules,
        candidate_manifest,
        manager,
    )
    if matches:
        raise DeltaContractError(
            "ABSENCE_MATCH",
            f"forbidden pre-A artifact exists: {matches[0]['path']}",
        )
    document["repository_absence"]["observed_head"] = head
    document["repository_absence"]["scan_snapshot_sha256"] = snapshot
    document["repository_absence"]["matches"] = []
    review_input = semantic_review_input_sha256(
        document,
        candidate_manifest,
    )
    for review_id in ("projection", "source"):
        document["semantic_reviews"][review_id][
            "input_set_sha256"
        ] = review_input
    validate_document(
        repo_root,
        document,
        delta_path=output_path,
        materializing=True,
        synthetic_test_profile=synthetic_test_profile,
        require_semantic_reviews=require_semantic_reviews,
    )
    return document


def prepare_semantic_review_packet(
    repo_root: Path,
    draft: dict[str, Any],
    *,
    delta_output_path: Path,
    synthetic_test_profile: bool = False,
) -> dict[str, Any]:
    """Build the immutable input shared by two independent reviewers.

    The candidate package must already contain fail-closed review stubs that
    are registered in its manifest. Their own content and hashes are excluded
    from the reviewed projection, preventing circular review dependencies.
    This function never returns a materializable delta: final materialization
    still requires two valid review artifacts bound to the returned digest.
    """

    document = materialize_document(
        repo_root,
        draft,
        output_path=delta_output_path,
        synthetic_test_profile=synthetic_test_profile,
        require_semantic_reviews=False,
    )
    manager = _load_frozen_manager(repo_root)
    candidate_manifest, _ = _candidate_manifest(
        repo_root,
        manager,
        document["base_run"]["finalize_commit"],
    )
    input_set = _semantic_review_input(document, candidate_manifest)
    input_set_sha256 = sha256_bytes(canonical_value_bytes(input_set))
    if any(
        binding["input_set_sha256"] != input_set_sha256
        for binding in document["semantic_reviews"].values()
    ):
        raise DeltaContractError(
            "REVIEW_PACKET_BINDING",
            "prepared review bindings differ from the review input",
        )
    return {
        "artifact_type": "formal_run_delta_semantic_review_input",
        "artifact_version": "0.1.0",
        "base_completion_commit": document["base_run"]["completion_commit"],
        "base_finalize_commit": document["base_run"]["finalize_commit"],
        "base_freeze_commit": document["base_run"]["freeze_commit"],
        "base_run_id": BASE_RUN_ID,
        "candidate_observed_head": document["repository_absence"][
            "observed_head"
        ],
        "candidate_run_id": CANDIDATE_RUN_ID,
        "delta_schema": {
            "path": SCHEMA_PATH.as_posix(),
            "sha256": TRUSTED_SCHEMA_SHA256[SCHEMA_PATH.as_posix()],
        },
        "generation_policy": "ephemeral_review_input_not_candidate_artifact",
        "input_set": input_set,
        "input_set_sha256": input_set_sha256,
        "required_review_ids": ["projection", "source"],
        "status": "ready_for_independent_semantic_reviews",
    }


def verify_delta(
    repo_root: Path,
    delta_path: Path,
    *,
    synthetic_test_profile: bool = False,
) -> tuple[dict[str, Any], bytes, dict[str, Any]]:
    document, raw = read_json_object(
        delta_path,
        require_canonical=True,
    )
    binding = validate_document(
        repo_root,
        document,
        delta_path=delta_path,
        materializing=False,
        synthetic_test_profile=synthetic_test_profile,
    )
    return document, raw, binding
