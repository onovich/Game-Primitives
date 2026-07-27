#!/usr/bin/env python3
"""Build and verify the frozen continuous-001 post-run inventory.

This module is deliberately independent from the formal-run-delta producer
and verifier.  Its source of truth is the Git object database:

* Commit B is the last frozen pre-gate state.
* The completion commit is its direct child.
* Only files added below the continuous-001 run root are inventory members.
* A modification, deletion, rename, non-blob entry, case-colliding path, or
  path outside the fixed eight-family classifier fails closed.

The module never reads the continuous-001 working-tree package and never
imports, opens, or executes a formal runner, comparator, input, trace, or
result.  JSON parsing is used only to fingerprint inert Git blob bytes.

Fingerprint algorithms
----------------------

``byte_sha256``
    SHA-256 over the exact Git blob bytes.

``canonical_payload_sha256``
    For strict UTF-8 JSON with no duplicate object member and no non-finite
    number, SHA-256 over compact, key-sorted UTF-8 JSON.  For every other
    blob it is the byte SHA-256.  Consequently malformed or non-JSON content
    can never gain a semantic equivalence weaker than exact byte equality.

``protected_payload_fingerprint``
    For strict JSON, recursively removes only the explicit operational
    rebinding projection defined by ``REBINDABLE_EXACT_KEYS`` plus timestamp,
    Git-anchor, and cryptographic-reference fields.  It normalizes the fixed
    run-id token to ``{run_id}``, retains list order and every other value,
    canonically serializes the projection, and hashes it with SHA-256.  The
    removal of reference hashes is intentionally conservative: it can create
    extra reuse suspicions, but cannot make copied semantic payload disappear.
    A blob that cannot be parsed as strict JSON falls back to its byte SHA-256.

The inventory format is
``base-post-run-completion-inventory-0.1.0.schema.json``.  Exact verification
is stronger than Schema validation: a supplied inventory must equal a fresh
recomputation from the fixed Git objects, including family order and artifact
order.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Callable


BASE_RUN_ID = "continuous-001"
BASE_FREEZE_COMMIT = "bbea296b019ea1b5f5f3bb8cfe5937b0ff276f5b"
BASE_FINALIZE_COMMIT = "972589c6fb716932e01e09c7cefa92f59953336b"
BASE_COMPLETION_COMMIT = "c42013d5cad89811e8838696c4072f6f71a859fb"

# These values make the tree and frozen root explicit trust anchors rather
# than values supplied by the inventory author.
BASE_COMPLETION_TREE_OID = "f8aae165fcf9620b8ba9cee64766e39f642d8d4c"
BASE_FROZEN_ARTIFACT_SET_DIGEST = (
    "05ecfdb1e88db74e6839c1a443e6cb09a7a9e89754131b018e13ed04f7ff3c69"
)

PILOT_ROOT = "research/calibration-tests/continuous-action-pilot"
BASE_RUN_ROOT = f"{PILOT_ROOT}/runs/{BASE_RUN_ID}"
BASE_MANIFEST_PATH = f"{BASE_RUN_ROOT}/manifest.json"
SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    f"{PILOT_ROOT}/schema/"
    "base-post-run-completion-inventory-0.1.0.schema.json"
)

ARTIFACT_TYPE = "base_post_run_completion_inventory"
ARTIFACT_VERSION = "0.1.0"
CLASSIFIER_PROFILE = "continuous-action-post-run-v1"
RUN_OUTCOME = "invalid_before_prediction_set"

FAMILY_IDS = (
    "actors_sessions",
    "authorization",
    "blind_response_chain",
    "dispatch_and_cohort",
    "execution_evidence",
    "execution_permit",
    "prediction_set",
    "reveal_and_closure",
)

REPO_PATH_RE = re.compile(
    r"^(?!/)(?!.*\\)(?!.*(?:^|/)\.\.(?:/|$))"
    r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_OID_RE = re.compile(r"^[0-9a-f]{40}$")
TOP_LEVEL_BLIND_RESPONSE_RE = re.compile(
    r"^submissions/p[0-9]{2}-stage[12]\.json$"
)
ACTOR_SESSION_RE = re.compile(
    r"^submissions/actors/p[0-9]{2}(?:-attempt-[0-9]{2})?\.json$"
)
DISPATCH_AND_COHORT_RE = re.compile(
    r"^submissions/dispatch/(?:"
    r"stage1-cohort-lock|stage[12]-p[0-9]{2}"
    r")\.json$"
)
BLIND_ENVELOPE_RE = re.compile(
    r"^submissions/(?:envelopes|raw)/p[0-9]{2}-stage[12]\.json$"
)
BLIND_INVALID_ATTEMPT_RE = re.compile(
    r"^submissions/invalid-attempts/"
    r"p[0-9]{2}-attempt-[0-9]{2}/(?:"
    r"failure|"
    r"p[0-9]{2}-stage[12]\.(?:envelope|raw-response)|"
    r"stage[12]-p[0-9]{2}\.dispatch-receipt"
    r")\.json$"
)
EXECUTION_RAW_RE = re.compile(
    r"^execution/raw/[A-Za-z0-9._-]+\.json$"
)
EXECUTION_EVIDENCE_REPORT_RE = re.compile(
    r"^reports/(?:formal-comparator-output|execution-evidence)"
    r"(?:-[A-Za-z0-9._-]+)?\.json$"
)
REVEAL_RE = re.compile(r"^reveal/[A-Za-z0-9._-]+\.json$")
CLOSURE_REPORT_PATHS = frozenset(
    {
        "reports/README.md",
        "reports/prediction-template-contract-check-v0.1.0.json",
        "reports/stage2-template-schema-unit-incident-v0.1.0.json",
    }
)
PREDICTION_SET_PATHS = frozenset(
    {
        "submissions/prediction-set-preimage.tsv",
        "submissions/prediction-set.json",
    }
)
EXECUTION_EVIDENCE_PATHS = frozenset(
    {
        "execution/execution-result.json",
        "execution/trace-bundle.json",
    }
)

# Only operational identity/binding data is projected away.  Case,
# condition, seat, branch, configuration, role, model, authorization scope,
# authorization phrase, response, observation, result, and truth content are
# deliberately not in this set.
REBINDABLE_EXACT_KEYS = frozenset(
    {
        "actor",
        "actor_id",
        "actor_identifier",
        "actor_object_sha256",
        "actor_path",
        "attempt_id",
        "authorization_id",
        "authorization_receipt",
        "base_run_id",
        "candidate_run_id",
        "dispatch_receipt",
        "envelope_path",
        "envelope_sha256",
        "lock_id",
        "prior_stage_submission_sha256",
        "receipt_id",
        "run_id",
        "session_id",
        "submission_id",
        "task_sha256",
        "thread_id",
    }
)

TEXT_SUFFIXES = frozenset(
    {".csv", ".log", ".md", ".text", ".tsv", ".txt"}
)


class InventoryContractError(RuntimeError):
    """A stable fail-closed inventory contract failure."""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class _DuplicateJsonMember(ValueError):
    pass


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json_value_bytes(value: Any) -> bytes:
    """Return the fingerprint canonicalization, not the document rendering."""

    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_inventory_bytes(inventory: Mapping[str, Any]) -> bytes:
    """Return the one accepted human-readable inventory representation."""

    return (
        json.dumps(
            inventory,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite JSON number: {value}")
    return parsed


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonMember(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def strict_json_bytes(raw: bytes) -> Any:
    """Parse strict UTF-8 JSON, rejecting BOM, duplicates, and NaN/Infinity."""

    text = raw.decode("utf-8", errors="strict")
    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
    )


def _is_timestamp_key(key: str) -> bool:
    return key == "timestamp" or key.endswith("_at")


def _is_git_anchor_key(key: str) -> bool:
    return (
        key in {"anchor_commit", "commit_oid", "freeze_commit"}
        or key.endswith("_commit")
        or key.endswith("_tree_oid")
    )


def _is_reference_hash_key(key: str) -> bool:
    return (
        key == "sha256"
        or key.endswith("_sha256")
        or key == "frozen_artifact_set_digest"
    )


def _normalize_run_token(value: str, run_id: str) -> str:
    # The run identifier is intentionally normalized in all retained strings.
    # It is a long, project-specific token; replacing it cannot erase an actor
    # answer such as "continuous" or a numeric observation.
    return value.replace(run_id, "{run_id}")


def _protected_projection(
    value: Any,
    *,
    run_id: str,
    parent_key: str | None = None,
) -> Any:
    if isinstance(value, dict):
        projected: dict[str, Any] = {}
        for key in sorted(value):
            child = value[key]
            normalized_key = key.casefold()
            if normalized_key in REBINDABLE_EXACT_KEYS:
                # Authorization and dispatch receipts can be structured.  In
                # that case preserve their semantic fields and strip only the
                # nested operational identifiers.
                if normalized_key in {
                    "authorization_receipt",
                    "dispatch_receipt",
                } and isinstance(child, (dict, list)):
                    nested = _protected_projection(
                        child,
                        run_id=run_id,
                        parent_key=key,
                    )
                    projected[key] = nested
                continue
            if (
                _is_timestamp_key(normalized_key)
                or _is_git_anchor_key(normalized_key)
                or _is_reference_hash_key(normalized_key)
            ):
                continue
            nested = _protected_projection(
                child,
                run_id=run_id,
                parent_key=key,
            )
            projected[key] = nested
        return projected
    if isinstance(value, list):
        return [
            _protected_projection(
                item,
                run_id=run_id,
                parent_key=parent_key,
            )
            for item in value
        ]
    if isinstance(value, str):
        return _normalize_run_token(value, run_id)
    return value


def protected_payload_fingerprint(
    raw: bytes,
    *,
    run_id: str = BASE_RUN_ID,
) -> str:
    """Hash the stable semantic projection, falling back to exact bytes.

    A candidate-side caller should pass its own run identifier so embedded
    repository paths normalize to the same ``{run_id}`` token as the base.
    """

    if not isinstance(run_id, str) or not run_id:
        raise InventoryContractError(
            "FINGERPRINT_RUN_ID_INVALID",
            "protected fingerprint run_id must be a non-empty string",
        )
    try:
        value = strict_json_bytes(raw)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return sha256_bytes(raw)
    projection = _protected_projection(value, run_id=run_id)
    return sha256_bytes(canonical_json_value_bytes(projection))


def _json_metadata(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, dict):
        return None, None
    artifact_type = value.get("artifact_type")
    artifact_version = value.get("artifact_version")
    return (
        artifact_type if isinstance(artifact_type, str) else None,
        artifact_version if isinstance(artifact_version, str) else None,
    )


def _payload_metadata(
    path: str,
    raw: bytes,
) -> tuple[str, str, str | None, str | None]:
    """Return media type, canonical digest, artifact type, and version."""

    try:
        value = strict_json_bytes(raw)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        value = None
    else:
        artifact_type, artifact_version = _json_metadata(value)
        return (
            "application/json",
            sha256_bytes(canonical_json_value_bytes(value)),
            artifact_type,
            artifact_version,
        )

    suffix = PurePosixPath(path).suffix.casefold()
    if suffix in TEXT_SUFFIXES:
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            media_type = "application/octet-stream"
        else:
            media_type = (
                "text/plain"
                if "\x00" not in text
                else "application/octet-stream"
            )
    else:
        media_type = "application/octet-stream"
    digest = sha256_bytes(raw)
    return media_type, digest, None, None


def _run_git(repo_root: Path, arguments: Sequence[str]) -> bytes:
    environment = dict(os.environ)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["LC_ALL"] = "C"
    try:
        completed = subprocess.run(
            ["git", "-c", "core.quotepath=false", "-C", str(repo_root), *arguments],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )
    except OSError as exc:
        raise InventoryContractError(
            "GIT_UNAVAILABLE",
            f"could not start git: {exc}",
        ) from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise InventoryContractError(
            "GIT_COMMAND_FAILED",
            f"git {' '.join(arguments)} failed: {detail}",
        )
    return completed.stdout


def _git_text(repo_root: Path, arguments: Sequence[str]) -> str:
    raw = _run_git(repo_root, arguments)
    try:
        return raw.decode("utf-8", errors="strict").strip()
    except UnicodeDecodeError as exc:
        raise InventoryContractError(
            "GIT_OUTPUT_ENCODING",
            f"git {' '.join(arguments)} emitted non-UTF-8 text",
        ) from exc


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(
        str(right.resolve())
    )


def _validate_repository(repo_root: Path) -> Path:
    try:
        resolved = repo_root.resolve(strict=True)
    except OSError as exc:
        raise InventoryContractError(
            "REPOSITORY_MISSING",
            f"repository root does not exist: {repo_root}",
        ) from exc
    top = Path(_git_text(resolved, ["rev-parse", "--show-toplevel"]))
    if not _same_path(resolved, top):
        raise InventoryContractError(
            "REPOSITORY_ROOT_REQUIRED",
            f"expected Git top-level {top}, received {resolved}",
        )
    return resolved


def _verify_commit_anchors(repo_root: Path) -> str:
    for expected in (
        BASE_FREEZE_COMMIT,
        BASE_FINALIZE_COMMIT,
        BASE_COMPLETION_COMMIT,
    ):
        actual = _git_text(
            repo_root,
            ["rev-parse", "--verify", f"{expected}^{{commit}}"],
        )
        if actual != expected:
            raise InventoryContractError(
                "COMMIT_ANCHOR_MISMATCH",
                f"expected commit {expected}, found {actual}",
            )

    finalize_line = _git_text(
        repo_root,
        ["rev-list", "--parents", "-n", "1", BASE_FINALIZE_COMMIT],
    ).split()
    if finalize_line != [BASE_FINALIZE_COMMIT, BASE_FREEZE_COMMIT]:
        raise InventoryContractError(
            "FINALIZE_PARENT_MISMATCH",
            "Commit B is not the direct single-parent child of Commit A",
        )
    completion_line = _git_text(
        repo_root,
        ["rev-list", "--parents", "-n", "1", BASE_COMPLETION_COMMIT],
    ).split()
    if completion_line != [BASE_COMPLETION_COMMIT, BASE_FINALIZE_COMMIT]:
        raise InventoryContractError(
            "COMPLETION_PARENT_MISMATCH",
            "completion is not the direct single-parent child of Commit B",
        )

    tree_oid = _git_text(
        repo_root,
        ["rev-parse", f"{BASE_COMPLETION_COMMIT}^{{tree}}"],
    )
    if tree_oid != BASE_COMPLETION_TREE_OID:
        raise InventoryContractError(
            "COMPLETION_TREE_MISMATCH",
            f"expected tree {BASE_COMPLETION_TREE_OID}, found {tree_oid}",
        )
    return tree_oid


def _read_git_blob(repo_root: Path, commit: str, path: str) -> bytes:
    return _run_git(repo_root, ["cat-file", "blob", f"{commit}:{path}"])


def _base_frozen_root(repo_root: Path) -> str:
    raw = _read_git_blob(repo_root, BASE_FINALIZE_COMMIT, BASE_MANIFEST_PATH)
    try:
        manifest = strict_json_bytes(raw)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise InventoryContractError(
            "BASE_MANIFEST_INVALID",
            "Commit B manifest is not strict JSON",
        ) from exc
    if not isinstance(manifest, dict):
        raise InventoryContractError(
            "BASE_MANIFEST_INVALID",
            "Commit B manifest is not an object",
        )
    if (
        manifest.get("run_id") != BASE_RUN_ID
        or manifest.get("freeze_commit") != BASE_FREEZE_COMMIT
        or manifest.get("status") != "frozen"
    ):
        raise InventoryContractError(
            "BASE_MANIFEST_BINDING_MISMATCH",
            "Commit B manifest is not the fixed frozen continuous-001 package",
        )
    digest = manifest.get("frozen_artifact_set_digest")
    if (
        not isinstance(digest, str)
        or not SHA256_RE.fullmatch(digest)
        or digest != BASE_FROZEN_ARTIFACT_SET_DIGEST
    ):
        raise InventoryContractError(
            "BASE_FROZEN_ROOT_MISMATCH",
            "Commit B frozen artifact set digest differs from the trust anchor",
        )
    return digest


def _decode_diff_tokens(raw: bytes) -> list[tuple[str, str]]:
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    changes: list[tuple[str, str]] = []
    index = 0
    while index < len(fields):
        try:
            field = fields[index].decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise InventoryContractError(
                "NON_UTF8_DIFF_PATH",
                "Git diff contains a non-UTF-8 status or path",
            ) from exc
        index += 1
        if "\t" in field:
            status, path = field.split("\t", 1)
        else:
            status = field
            if index >= len(fields):
                raise InventoryContractError(
                    "MALFORMED_GIT_DIFF",
                    "Git name-status output ended before its path",
                )
            try:
                path = fields[index].decode("utf-8", errors="strict")
            except UnicodeDecodeError as exc:
                raise InventoryContractError(
                    "NON_UTF8_DIFF_PATH",
                    "Git diff contains a non-UTF-8 path",
                ) from exc
            index += 1
        changes.append((status, path))
    return changes


def _completion_changes(repo_root: Path) -> list[str]:
    raw = _run_git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            "-z",
            "--no-renames",
            BASE_FINALIZE_COMMIT,
            BASE_COMPLETION_COMMIT,
            "--",
            f"{BASE_RUN_ROOT}/",
        ],
    )
    changes = _decode_diff_tokens(raw)
    paths: list[str] = []
    casefolded: dict[str, str] = {}
    for status, path in changes:
        if status != "A":
            raise InventoryContractError(
                "NON_ADDITION_POST_GATE_CHANGE",
                f"{status} change is forbidden for post-gate path {path}",
            )
        _validate_repo_path(path)
        if not path.startswith(f"{BASE_RUN_ROOT}/"):
            raise InventoryContractError(
                "POST_GATE_PATH_OUTSIDE_RUN",
                f"post-gate path escaped continuous-001: {path}",
            )
        folded = path.casefold()
        prior = casefolded.get(folded)
        if prior is not None and prior != path:
            raise InventoryContractError(
                "CASE_COLLIDING_POST_GATE_PATHS",
                f"{prior} and {path} collide under case-insensitive lookup",
            )
        casefolded[folded] = path
        paths.append(path)
    if not paths:
        raise InventoryContractError(
            "EMPTY_POST_GATE_INVENTORY",
            "Commit B to completion added no continuous-001 post-gate files",
        )
    return sorted(paths)


def _validate_repo_path(path: str) -> None:
    if not REPO_PATH_RE.fullmatch(path):
        raise InventoryContractError(
            "NON_CANONICAL_REPOSITORY_PATH",
            f"not a canonical repository file path: {path!r}",
        )


def classify_post_gate_path(repository_path: str) -> str:
    """Return one fixed family or fail closed for an unknown path."""

    _validate_repo_path(repository_path)
    prefix = f"{BASE_RUN_ROOT}/"
    if not repository_path.startswith(prefix):
        raise InventoryContractError(
            "POST_GATE_PATH_OUTSIDE_RUN",
            f"path is outside the fixed continuous-001 root: {repository_path}",
        )
    relative = repository_path[len(prefix) :]

    if ACTOR_SESSION_RE.fullmatch(relative):
        family = "actors_sessions"
    elif relative == "submissions/dispatch/human-gate-authorization.json":
        family = "authorization"
    elif DISPATCH_AND_COHORT_RE.fullmatch(relative):
        family = "dispatch_and_cohort"
    elif (
        BLIND_ENVELOPE_RE.fullmatch(relative)
        or BLIND_INVALID_ATTEMPT_RE.fullmatch(relative)
        or TOP_LEVEL_BLIND_RESPONSE_RE.fullmatch(relative)
    ):
        family = "blind_response_chain"
    elif relative in PREDICTION_SET_PATHS:
        family = "prediction_set"
    elif relative == "execution/formal-execution-permit.json":
        family = "execution_permit"
    elif (
        EXECUTION_RAW_RE.fullmatch(relative)
        or relative in EXECUTION_EVIDENCE_PATHS
        or EXECUTION_EVIDENCE_REPORT_RE.fullmatch(relative)
    ):
        family = "execution_evidence"
    elif REVEAL_RE.fullmatch(relative) or relative in CLOSURE_REPORT_PATHS:
        family = "reveal_and_closure"
    else:
        raise InventoryContractError(
            "UNCLASSIFIED_POST_GATE_PATH",
            f"no {CLASSIFIER_PROFILE} family for {repository_path}",
        )

    if family not in FAMILY_IDS:
        raise AssertionError(f"internal classifier returned unknown family: {family}")
    return family


def _git_blob_entry(
    repo_root: Path,
    commit: str,
    repository_path: str,
) -> tuple[str, bytes]:
    raw_entry = _run_git(
        repo_root,
        ["ls-tree", "-z", commit, "--", repository_path],
    )
    entries = [entry for entry in raw_entry.split(b"\0") if entry]
    if len(entries) != 1:
        raise InventoryContractError(
            "GIT_TREE_ENTRY_COUNT",
            f"expected one completion-tree entry for {repository_path}",
        )
    try:
        header, encoded_path = entries[0].split(b"\t", 1)
        mode, object_type, oid = header.decode(
            "ascii", errors="strict"
        ).split()
        actual_path = encoded_path.decode("utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise InventoryContractError(
            "MALFORMED_GIT_TREE_ENTRY",
            f"could not parse completion-tree entry for {repository_path}",
        ) from exc
    if (
        actual_path != repository_path
        or object_type != "blob"
        or mode not in {"100644", "100755"}
        or not GIT_OID_RE.fullmatch(oid)
    ):
        raise InventoryContractError(
            "NON_REGULAR_POST_GATE_BLOB",
            f"post-gate entry is not one exact regular blob: {repository_path}",
        )
    raw = _read_git_blob(repo_root, commit, repository_path)
    expected_oid = hashlib.sha1(  # noqa: S324 - Git SHA-1 object identity.
        f"blob {len(raw)}\0".encode("ascii") + raw
    ).hexdigest()
    if oid != expected_oid:
        raise InventoryContractError(
            "GIT_BLOB_OID_MISMATCH",
            f"Git blob identity mismatch for {repository_path}",
        )
    return oid, raw


def _artifact_record(
    repo_root: Path,
    repository_path: str,
) -> tuple[str, dict[str, Any]]:
    family = classify_post_gate_path(repository_path)
    oid, raw = _git_blob_entry(
        repo_root,
        BASE_COMPLETION_COMMIT,
        repository_path,
    )
    media_type, canonical_digest, artifact_type, artifact_version = (
        _payload_metadata(repository_path, raw)
    )
    return family, {
        "artifact_type": artifact_type,
        "artifact_version": artifact_version,
        "byte_length": len(raw),
        "byte_sha256": sha256_bytes(raw),
        "canonical_payload_sha256": canonical_digest,
        "git_blob_oid": oid,
        "media_type": media_type,
        "path": repository_path,
        "protected_payload_fingerprint": protected_payload_fingerprint(raw),
    }


def _validate_inventory_mechanics(inventory: Mapping[str, Any]) -> None:
    """Enforce ordering, cardinality, uniqueness, and classifier closure."""

    families = inventory.get("families")
    if not isinstance(families, list):
        raise InventoryContractError(
            "FAMILIES_NOT_ARRAY",
            "families must be an array",
        )
    if len(families) != len(FAMILY_IDS):
        raise InventoryContractError(
            "FAMILY_CARDINALITY_MISMATCH",
            f"expected exactly {len(FAMILY_IDS)} families",
        )

    observed_family_ids: list[str] = []
    global_paths: set[str] = set()
    for expected_family_id, family in zip(FAMILY_IDS, families, strict=True):
        if not isinstance(family, dict):
            raise InventoryContractError(
                "FAMILY_NOT_OBJECT",
                f"family slot {expected_family_id} is not an object",
            )
        family_id = family.get("family_id")
        if not isinstance(family_id, str):
            raise InventoryContractError(
                "FAMILY_ID_INVALID",
                f"family slot {expected_family_id} lacks a string family_id",
            )
        observed_family_ids.append(family_id)
        if family_id != expected_family_id:
            raise InventoryContractError(
                "FAMILY_ORDER_MISMATCH",
                f"expected {expected_family_id}, found {family_id}",
            )

        artifacts = family.get("artifacts")
        artifact_count = family.get("artifact_count")
        state = family.get("state")
        if not isinstance(artifacts, list):
            raise InventoryContractError(
                "FAMILY_ARTIFACTS_NOT_ARRAY",
                f"{family_id}.artifacts must be an array",
            )
        if (
            not isinstance(artifact_count, int)
            or isinstance(artifact_count, bool)
            or artifact_count != len(artifacts)
        ):
            raise InventoryContractError(
                "FAMILY_COUNT_MISMATCH",
                f"{family_id}.artifact_count must equal len(artifacts)",
            )
        expected_state = "present" if artifacts else "absent"
        if state != expected_state:
            raise InventoryContractError(
                "FAMILY_STATE_MISMATCH",
                f"{family_id} with {len(artifacts)} artifacts must be "
                f"{expected_state}",
            )

        paths: list[str] = []
        unique_fields: dict[str, set[str]] = {
            "path": set(),
            "byte_sha256": set(),
            "canonical_payload_sha256": set(),
            "git_blob_oid": set(),
        }
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                raise InventoryContractError(
                    "ARTIFACT_NOT_OBJECT",
                    f"{family_id}.artifacts[{index}] is not an object",
                )
            path = artifact.get("path")
            if not isinstance(path, str):
                raise InventoryContractError(
                    "ARTIFACT_PATH_INVALID",
                    f"{family_id}.artifacts[{index}].path is not a string",
                )
            _validate_repo_path(path)
            if not path.startswith(f"{BASE_RUN_ROOT}/"):
                raise InventoryContractError(
                    "POST_GATE_PATH_OUTSIDE_RUN",
                    f"inventory path escaped continuous-001: {path}",
                )
            actual_family = classify_post_gate_path(path)
            if actual_family != family_id:
                raise InventoryContractError(
                    "ARTIFACT_FAMILY_MISMATCH",
                    f"{path} classifies as {actual_family}, not {family_id}",
                )
            if path in global_paths:
                raise InventoryContractError(
                    "DUPLICATE_INVENTORY_PATH",
                    f"artifact path occurs more than once: {path}",
                )
            global_paths.add(path)
            paths.append(path)

            for field, seen in unique_fields.items():
                value = artifact.get(field)
                pattern = (
                    GIT_OID_RE if field == "git_blob_oid" else SHA256_RE
                )
                if field == "path":
                    value = path
                    pattern = None
                if not isinstance(value, str) or (
                    pattern is not None and not pattern.fullmatch(value)
                ):
                    raise InventoryContractError(
                        "ARTIFACT_IDENTITY_INVALID",
                        f"{path} has invalid {field}",
                    )
                if value in seen:
                    raise InventoryContractError(
                        "DUPLICATE_FAMILY_ARTIFACT_IDENTITY",
                        f"{family_id} repeats {field} value at {path}",
                    )
                seen.add(value)

            protected = artifact.get("protected_payload_fingerprint")
            if (
                not isinstance(protected, str)
                or not SHA256_RE.fullmatch(protected)
            ):
                raise InventoryContractError(
                    "PROTECTED_FINGERPRINT_INVALID",
                    f"{path} has an invalid protected payload fingerprint",
                )

        if paths != sorted(paths):
            raise InventoryContractError(
                "FAMILY_ARTIFACT_ORDER_MISMATCH",
                f"{family_id} artifacts are not sorted by repository path",
            )

    if (
        tuple(observed_family_ids) != FAMILY_IDS
        or len(set(observed_family_ids)) != len(FAMILY_IDS)
    ):
        raise InventoryContractError(
            "FAMILY_CLOSURE_MISMATCH",
            "the eight fixed families must occur exactly once in order",
        )


def build_inventory(repo_root: Path) -> dict[str, Any]:
    """Recompute the canonical inventory exclusively from fixed Git objects."""

    root = _validate_repository(repo_root)
    tree_oid = _verify_commit_anchors(root)
    frozen_digest = _base_frozen_root(root)
    grouped: dict[str, list[dict[str, Any]]] = {
        family: [] for family in FAMILY_IDS
    }
    for path in _completion_changes(root):
        family, record = _artifact_record(root, path)
        grouped[family].append(record)

    families: list[dict[str, Any]] = []
    for family_id in FAMILY_IDS:
        artifacts = sorted(grouped[family_id], key=lambda item: item["path"])
        families.append(
            {
                "artifact_count": len(artifacts),
                "artifacts": artifacts,
                "family_id": family_id,
                "state": "present" if artifacts else "absent",
            }
        )

    inventory = {
        "$schema": SCHEMA_ID,
        "artifact_type": ARTIFACT_TYPE,
        "artifact_version": ARTIFACT_VERSION,
        "base_completion_commit": BASE_COMPLETION_COMMIT,
        "base_finalize_commit": BASE_FINALIZE_COMMIT,
        "base_freeze_commit": BASE_FREEZE_COMMIT,
        "base_frozen_artifact_set_digest": frozen_digest,
        "base_run_id": BASE_RUN_ID,
        "base_tree_oid": tree_oid,
        "classifier_profile": CLASSIFIER_PROFILE,
        "families": families,
        "formal_input_executed": False,
        "formal_result_created": False,
        "run_outcome": RUN_OUTCOME,
        "status": "passed",
        "unclassified_post_gate_paths": [],
    }
    _validate_inventory_mechanics(inventory)
    return inventory


def _first_difference(actual: Any, expected: Any, path: str = "$") -> str:
    if type(actual) is not type(expected):  # noqa: E721 - exact JSON types.
        return (
            f"{path}: type {type(actual).__name__} != "
            f"{type(expected).__name__}"
        )
    if isinstance(expected, dict):
        actual_keys = set(actual)
        expected_keys = set(expected)
        if actual_keys != expected_keys:
            missing = sorted(expected_keys - actual_keys)
            extra = sorted(actual_keys - expected_keys)
            return f"{path}: missing keys {missing}, extra keys {extra}"
        for key in sorted(expected):
            difference = _first_difference(
                actual[key],
                expected[key],
                f"{path}.{key}",
            )
            if difference:
                return difference
        return ""
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return f"{path}: length {len(actual)} != {len(expected)}"
        for index, expected_item in enumerate(expected):
            difference = _first_difference(
                actual[index],
                expected_item,
                f"{path}[{index}]",
            )
            if difference:
                return difference
        return ""
    if actual != expected:
        return f"{path}: value differs"
    return ""


def verify_inventory(
    repo_root: Path,
    inventory: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify exact equality with an independent Git-object recomputation."""

    if not isinstance(inventory, Mapping):
        raise InventoryContractError(
            "INVENTORY_NOT_OBJECT",
            "inventory must be a JSON object",
        )
    actual = dict(inventory)
    _validate_inventory_mechanics(actual)
    expected = build_inventory(repo_root)
    difference = _first_difference(actual, expected)
    if difference:
        raise InventoryContractError(
            "INVENTORY_RECOMPUTATION_MISMATCH",
            difference,
        )
    counts = {
        family["family_id"]: family["artifact_count"]
        for family in expected["families"]
    }
    return {
        "artifact_count": sum(counts.values()),
        "base_completion_commit": BASE_COMPLETION_COMMIT,
        "base_tree_oid": BASE_COMPLETION_TREE_OID,
        "family_counts": counts,
        "inventory_sha256": sha256_bytes(canonical_inventory_bytes(expected)),
        "status": "passed",
    }


def verify_inventory_bytes(
    repo_root: Path,
    raw: bytes,
    *,
    require_canonical_bytes: bool = True,
) -> dict[str, Any]:
    """Strictly parse and verify an inventory document."""

    try:
        value = strict_json_bytes(raw)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise InventoryContractError(
            "INVENTORY_JSON_INVALID",
            "inventory is not strict UTF-8 JSON",
        ) from exc
    if not isinstance(value, dict):
        raise InventoryContractError(
            "INVENTORY_NOT_OBJECT",
            "inventory must be a JSON object",
        )
    if require_canonical_bytes and raw != canonical_inventory_bytes(value):
        raise InventoryContractError(
            "INVENTORY_NOT_CANONICAL",
            "inventory bytes are not the canonical indented representation",
        )
    return verify_inventory(repo_root, value)


def self_test(repo_root: Path) -> dict[str, Any]:
    """Run bounded positive and negative checks without writing any file."""

    inventory = build_inventory(repo_root)
    raw = canonical_inventory_bytes(inventory)
    result = verify_inventory_bytes(repo_root, raw)
    positives = 3
    negatives = 0

    tampered = json.loads(raw)
    tampered["base_tree_oid"] = "0" * 40
    try:
        verify_inventory(repo_root, tampered)
    except InventoryContractError:
        negatives += 1
    else:
        raise AssertionError("tampered tree OID was accepted")

    reordered = json.loads(raw)
    reordered["families"][0], reordered["families"][1] = (
        reordered["families"][1],
        reordered["families"][0],
    )
    try:
        verify_inventory(repo_root, reordered)
    except InventoryContractError:
        negatives += 1
    else:
        raise AssertionError("reordered family array was accepted")

    false_present = json.loads(raw)
    false_present["families"][4]["state"] = "present"
    try:
        verify_inventory(repo_root, false_present)
    except InventoryContractError:
        negatives += 1
    else:
        raise AssertionError("present family with zero artifacts was accepted")

    duplicate = json.loads(raw)
    duplicate_family = duplicate["families"][0]
    duplicate_family["artifacts"].append(
        dict(duplicate_family["artifacts"][0])
    )
    duplicate_family["artifact_count"] += 1
    try:
        verify_inventory(repo_root, duplicate)
    except InventoryContractError:
        negatives += 1
    else:
        raise AssertionError("duplicate family path/hash/blob was accepted")

    misclassified = json.loads(raw)
    moved = misclassified["families"][0]["artifacts"].pop()
    misclassified["families"][0]["artifact_count"] -= 1
    misclassified["families"][1]["artifacts"].append(moved)
    misclassified["families"][1]["artifacts"].sort(
        key=lambda item: item["path"]
    )
    misclassified["families"][1]["artifact_count"] += 1
    try:
        verify_inventory(repo_root, misclassified)
    except InventoryContractError:
        negatives += 1
    else:
        raise AssertionError("artifact placed in the wrong family was accepted")

    unknown = f"{BASE_RUN_ROOT}/submissions/unknown.bin"
    try:
        classify_post_gate_path(unknown)
    except InventoryContractError:
        negatives += 1
    else:
        raise AssertionError("unknown post-gate path was accepted")

    duplicate_json = b'{"run_id":"a","run_id":"b"}'
    if protected_payload_fingerprint(duplicate_json) != sha256_bytes(
        duplicate_json
    ):
        raise AssertionError("malformed JSON did not fall back to byte hash")
    negatives += 1

    nonfinite_json = b'{"value":NaN}'
    if protected_payload_fingerprint(nonfinite_json) != sha256_bytes(
        nonfinite_json
    ):
        raise AssertionError("non-finite JSON did not fall back to byte hash")
    negatives += 1

    left = canonical_json_value_bytes(
        {
            "run_id": "continuous-001",
            "actor_identifier": "old-session",
            "case_id": "CA-R1",
            "path": "runs/continuous-001/submissions/p01-stage1.json",
            "result": {"value": 7},
        }
    )
    right = canonical_json_value_bytes(
        {
            "run_id": "continuous-002",
            "actor_identifier": "new-session",
            "case_id": "CA-R1",
            "path": "runs/continuous-002/submissions/p01-stage1.json",
            "result": {"value": 7},
        }
    )
    # Only the fixed base run token is normalized.  The run_id field itself is
    # removed, so both projections still match.
    if protected_payload_fingerprint(
        left,
        run_id="continuous-001",
    ) != protected_payload_fingerprint(
        right,
        run_id="continuous-002",
    ):
        raise AssertionError("allowed rebinding changed protected fingerprint")
    positives += 1

    changed = canonical_json_value_bytes(
        {
            "run_id": "continuous-002",
            "actor_identifier": "new-session",
            "case_id": "CA-R1",
            "path": "runs/continuous-002/submissions/p01-stage1.json",
            "result": {"value": 8},
        }
    )
    if protected_payload_fingerprint(
        left,
        run_id="continuous-001",
    ) == protected_payload_fingerprint(
        changed,
        run_id="continuous-002",
    ):
        raise AssertionError("semantic payload change escaped fingerprint")
    positives += 1

    class _FaultyWriter:
        def __init__(self, handle: Any, *, raise_after_write: bool) -> None:
            self.handle = handle
            self.raise_after_write = raise_after_write

        def __enter__(self) -> "_FaultyWriter":
            return self

        def __exit__(self, *_args: Any) -> None:
            self.handle.close()

        def write(self, raw: bytes) -> int:
            written = self.handle.write(raw[: max(1, len(raw) // 2)])
            if self.raise_after_write:
                raise OSError("synthetic partial-write failure")
            return written

    with tempfile.TemporaryDirectory(
        prefix="base-post-run-inventory-write-self-test-",
        dir=tempfile.gettempdir(),
    ) as temporary:
        output = Path(temporary) / "inventory.json"
        if _write_once(output, b"complete\n") != "written":
            raise AssertionError("normal exclusive write did not report written")
        if _write_once(output, b"complete\n") != "unchanged":
            raise AssertionError("identical exclusive write was not idempotent")
        positives += 1
        output.unlink()

        for raise_after_write, expected_code in (
            (False, "OUTPUT_PARTIAL_WRITE"),
            (True, "OUTPUT_WRITE_FAILED"),
        ):
            def faulty_opener(
                target: Path,
                mode: str,
                *,
                should_raise: bool = raise_after_write,
            ) -> _FaultyWriter:
                return _FaultyWriter(
                    target.open(mode),
                    raise_after_write=should_raise,
                )

            try:
                _write_once(
                    output,
                    b"partial-write-control\n",
                    opener=faulty_opener,
                )
            except InventoryContractError as error:
                if error.code != expected_code:
                    raise AssertionError(
                        f"expected {expected_code}, got {error.code}"
                    ) from error
            else:
                raise AssertionError(
                    f"{expected_code} control unexpectedly succeeded"
                )
            if output.exists() or output.is_symlink():
                raise AssertionError(
                    f"{expected_code} control left output residue"
                )
            negatives += 1

    return {
        **result,
        "negative_checks": negatives,
        "positive_checks": positives,
    }


def _write_once(
    path: Path,
    raw: bytes,
    *,
    opener: Callable[[Path, str], Any] | None = None,
) -> str:
    """Create an inventory once, or accept an identical existing file."""

    if path.is_symlink():
        raise InventoryContractError(
            "OUTPUT_CONFLICT",
            f"refusing to write through a symbolic link: {path}",
        )
    if path.exists():
        if not path.is_file() or path.read_bytes() != raw:
            raise InventoryContractError(
                "OUTPUT_CONFLICT",
                f"refusing to replace different existing output: {path}",
            )
        return "unchanged"
    path.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        handle = path.open("xb") if opener is None else opener(path, "xb")
        created = True
        with handle:
            written = handle.write(raw)
            if written != len(raw):
                raise InventoryContractError(
                    "OUTPUT_PARTIAL_WRITE",
                    f"inventory output was only partially written: {path}",
                )
        if path.read_bytes() != raw:
            raise InventoryContractError(
                "OUTPUT_READBACK_MISMATCH",
                f"persisted inventory differs from requested bytes: {path}",
            )
    except FileExistsError as exc:
        raise InventoryContractError(
            "OUTPUT_CONFLICT",
            f"refusing to replace existing output: {path}",
        ) from exc
    except Exception as exc:
        if created:
            path.unlink(missing_ok=True)
        if isinstance(exc, InventoryContractError):
            raise
        raise InventoryContractError(
            "OUTPUT_WRITE_FAILED",
            f"could not create inventory output {path}: {exc}",
        ) from exc
    return "written"


def _refuse_base_worktree_path(
    repo_root: Path,
    path: Path,
    *,
    operation: str,
) -> None:
    """Keep CLI I/O outside the frozen base run's working-tree namespace."""

    candidate = os.path.normcase(str(path.resolve()))
    base = os.path.normcase(str((repo_root / BASE_RUN_ROOT).resolve()))
    try:
        common = os.path.commonpath([candidate, base])
    except ValueError:
        return
    if common == base:
        raise InventoryContractError(
            "BASE_WORKTREE_IO_FORBIDDEN",
            f"refusing to {operation} a working-tree path under {BASE_RUN_ROOT}",
        )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    materialize = subparsers.add_parser(
        "materialize",
        help="recompute the inventory from fixed Git objects",
    )
    materialize.add_argument("--repo-root", type=Path, required=True)
    materialize.add_argument(
        "--output",
        type=Path,
        help="create this file once; otherwise emit canonical JSON to stdout",
    )

    verify = subparsers.add_parser(
        "verify",
        help="verify an inventory against fixed Git objects",
    )
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--inventory", type=Path, required=True)

    check = subparsers.add_parser(
        "self-test",
        help="run bounded in-memory positive and negative checks",
    )
    check.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "materialize":
            inventory = build_inventory(args.repo_root)
            raw = canonical_inventory_bytes(inventory)
            if args.output is None:
                sys.stdout.buffer.write(raw)
            else:
                _refuse_base_worktree_path(
                    args.repo_root.resolve(),
                    args.output,
                    operation="write",
                )
                status = _write_once(args.output, raw)
                print(
                    json.dumps(
                        {
                            "inventory_sha256": sha256_bytes(raw),
                            "output": str(args.output),
                            "status": status,
                        },
                        sort_keys=True,
                    )
                )
        elif args.command == "verify":
            validated_root = _validate_repository(args.repo_root)
            _refuse_base_worktree_path(
                validated_root,
                args.inventory,
                operation="read",
            )
            try:
                raw = args.inventory.read_bytes()
            except OSError as exc:
                raise InventoryContractError(
                    "INVENTORY_READ_FAILED",
                    f"could not read inventory {args.inventory}: {exc}",
                ) from exc
            result = verify_inventory_bytes(
                args.repo_root,
                raw,
                require_canonical_bytes=True,
            )
            print(json.dumps(result, sort_keys=True))
        else:
            print(json.dumps(self_test(args.repo_root), sort_keys=True))
    except InventoryContractError as exc:
        print(
            json.dumps(
                {"code": exc.code, "message": exc.message, "status": "failed"},
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
