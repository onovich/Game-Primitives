#!/usr/bin/env python3
"""Read-only verifier for external dispatch attestation 0.1.0.

The verifier validates a frozen empty template and post-B append-only
attestations. It never lists, creates, mutates, dispatches, or executes an
external task, thread, session, runner, comparator, or reveal flow.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA_PATH = PILOT / (
    "schema/external-dispatch-attestation-0.1.0.schema.json"
)
TEMPLATE_PATH = PILOT / (
    "contracts/external-dispatch-attestation.template-0.1.0.json"
)
VERIFIER_PATH = PILOT / (
    "tools/verify-external-dispatch-attestation-v0.1.0.py"
)
MANIFEST_PATH = (
    PILOT / "runs/continuous-002/manifest.json"
).as_posix()
DELTA_PATH = (
    PILOT / "runs/continuous-002/inputs/"
    "formal-run-delta-v0.1.0.json"
).as_posix()
DENYLIST_PATH = (
    PILOT / "contracts/"
    "formal-post-gate-absence-denylist-0.1.0.json"
).as_posix()
ATTESTATION_PREFIX = (
    PILOT / "runs/continuous-002/gate/"
    "external-dispatch-attestations"
).as_posix() + "/"
TRUSTED_SCHEMA_SHA256 = (
    "4717ee62dc85ab5ea0f1609acb08ad724d030ec06462d9ef468d1634f05e3799"
)
TRUSTED_TEMPLATE_SHA256 = (
    "d73c5c6083c66964af5a1ad307da0d6ff7a1d8842e09947ebfbe8ee1d1489c94"
)
FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
ATTESTATION_ID_PATTERN = re.compile(
    r"^eda-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}$"
)
UTC_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)
ALLOWED_B_MANIFEST_CHANGES = {
    "freeze_commit",
    "status",
    "updated_at",
}


class AttestationError(ValueError):
    """A deterministic fail-closed verification error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AttestationError(
                "JSON_DUPLICATE_KEY",
                f"duplicate JSON key: {key}",
            )
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> Any:
    raise AttestationError(
        "JSON_NONFINITE_NUMBER",
        f"non-finite JSON number: {value}",
    )


def decode_json_bytes(
    raw: bytes,
    *,
    label: str,
    require_canonical: bool = True,
) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AttestationError(
            "JSON_BYTES_BOM",
            f"UTF-8 BOM is forbidden: {label}",
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AttestationError(
            "JSON_BYTES_INVALID_UTF8",
            f"invalid UTF-8 JSON: {label}",
        ) from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except json.JSONDecodeError as error:
        raise AttestationError(
            "JSON_SYNTAX",
            f"invalid JSON syntax: {label}: {error}",
        ) from error
    if require_canonical and canonical_bytes(value) != raw:
        raise AttestationError(
            "JSON_BYTES_NONCANONICAL",
            f"JSON bytes are not canonical: {label}",
        )
    return value


def _git(
    repo_root: Path,
    arguments: list[str],
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[bytes]:
    forbidden_git_environment = {
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_REPLACE_REF_BASE",
        "GIT_SHALLOW_FILE",
        "GIT_WORK_TREE",
    }
    inherited_git_environment = sorted(
        key
        for key in os.environ
        if key.upper() in forbidden_git_environment
    )
    if inherited_git_environment:
        raise AttestationError(
            "GIT_ENVIRONMENT_OVERRIDE",
            "ambient Git control variables are forbidden: "
            + ", ".join(inherited_git_environment),
        )
    environment = {
        key: os.environ[key]
        for key in (
            "COMSPEC",
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "WINDIR",
        )
        if key in os.environ
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LANG": "C",
            "LC_ALL": "C",
        }
    )
    completed = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "--no-replace-objects",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.preloadIndex=false",
            "-c",
            "core.untrackedCache=false",
            "-C",
            str(repo_root),
            *arguments,
        ],
        check=False,
        capture_output=True,
        env=environment,
        timeout=30,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr.decode(
            "utf-8",
            errors="replace",
        ).strip()
        raise AttestationError(
            "GIT_QUERY_FAILED",
            f"git {' '.join(arguments)} failed: "
            f"{stderr or completed.returncode}",
        )
    return completed


def _git_config_keys(repo_root: Path, scope: str) -> set[str]:
    completed = _git(
        repo_root,
        [
            "config",
            f"--{scope}",
            "--no-includes",
            "--null",
            "--name-only",
            "--list",
        ],
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode(
            "utf-8",
            errors="replace",
        ).strip()
        raise AttestationError(
            "GIT_CONFIG_QUERY_FAILED",
            f"could not inspect {scope} Git configuration: "
            f"{stderr or completed.returncode}",
        )
    try:
        keys = {
            item.decode("utf-8", errors="strict")
            for item in completed.stdout.split(b"\x00")
            if item
        }
    except UnicodeDecodeError as error:
        raise AttestationError(
            "GIT_CONFIG_ENCODING",
            f"{scope} Git configuration contains a non-UTF-8 key",
        ) from error
    return keys


def _verify_repository_configuration(
    repo_root: Path,
    git_directory: Path,
) -> None:
    scopes = [("local", git_directory / "config")]
    worktree_config = git_directory / "config.worktree"
    if worktree_config.exists():
        scopes.append(("worktree", worktree_config))
    keys: set[str] = set()
    for scope, config_path in scopes:
        if (
            _is_link_or_junction(config_path)
            or not config_path.is_file()
        ):
            raise AttestationError(
                "GIT_CONFIG_BOUNDARY",
                "Git configuration must be a direct repository file",
            )
        keys.update(_git_config_keys(repo_root, scope))
    folded = {key.casefold() for key in keys}
    if any(
        key == "include.path"
        or (key.startswith("includeif.") and key.endswith(".path"))
        for key in folded
    ):
        raise AttestationError(
            "GIT_CONFIG_INCLUDE",
            "repository Git configuration includes are forbidden",
        )
    if any(
        key.startswith("filter.")
        and key.rsplit(".", 1)[-1] in {"clean", "process", "smudge"}
        for key in folded
    ):
        raise AttestationError(
            "GIT_EXTERNAL_FILTER_CONFIG",
            "repository clean, process, and smudge filters are forbidden",
        )
    if any(
        key == "extensions.partialclone"
        or (
            key.startswith("remote.")
            and key.rsplit(".", 1)[-1]
            in {"partialclonefilter", "promisor"}
        )
        for key in folded
    ):
        raise AttestationError(
            "GIT_PARTIAL_CLONE_CONFIG",
            "partial-clone and promisor configuration is forbidden",
        )


def _is_link_or_junction(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or (
        callable(is_junction) and bool(is_junction())
    )


def _verify_repository_boundary(repo_root: Path) -> None:
    dot_git = repo_root / ".git"
    if _is_link_or_junction(dot_git) or not dot_git.is_dir():
        raise AttestationError(
            "GIT_DIRECTORY_BOUNDARY",
            "repository must use a direct .git directory at repo_root",
        )
    _verify_repository_configuration(repo_root, dot_git)
    top_level_raw = _git(
        repo_root,
        ["rev-parse", "--show-toplevel"],
    ).stdout
    git_directory_raw = _git(
        repo_root,
        ["rev-parse", "--absolute-git-dir"],
    ).stdout
    try:
        top_level = Path(
            top_level_raw.decode("utf-8", errors="strict").strip()
        ).resolve(strict=True)
        git_directory = Path(
            git_directory_raw.decode("utf-8", errors="strict").strip()
        ).resolve(strict=True)
    except (UnicodeDecodeError, OSError) as error:
        raise AttestationError(
            "GIT_DIRECTORY_BOUNDARY",
            "Git repository paths are not valid local UTF-8 paths",
        ) from error
    if top_level != repo_root or git_directory != dot_git.resolve(strict=True):
        raise AttestationError(
            "GIT_DIRECTORY_BOUNDARY",
            "Git top-level or object database differs from repo_root",
        )
    object_directory = git_directory / "objects"
    if (
        _is_link_or_junction(object_directory)
        or not object_directory.is_dir()
        or not object_directory.resolve(strict=True).is_relative_to(
            git_directory
        )
    ):
        raise AttestationError(
            "GIT_OBJECT_DIRECTORY_BOUNDARY",
            "Git object directory must remain inside the root .git directory",
        )
    if any(
        (object_directory / "info" / name).exists()
        for name in ("alternates", "http-alternates")
    ):
        raise AttestationError(
            "GIT_OBJECT_ALTERNATES_PRESENT",
            "Git object alternates are forbidden during verification",
        )
    if (git_directory / "info" / "grafts").exists():
        raise AttestationError(
            "GIT_GRAFTS_PRESENT",
            "legacy Git grafts are forbidden during verification",
        )
    replace_refs = _git(
        repo_root,
        ["for-each-ref", "--format=%(refname)", "refs/replace/"],
    ).stdout
    if replace_refs:
        raise AttestationError(
            "GIT_REPLACE_REFS_PRESENT",
            "Git replace refs are forbidden during verification",
        )


def _git_oid(repo_root: Path, revision: str) -> str:
    completed = _git(
        repo_root,
        ["rev-parse", "--verify", f"{revision}^{{commit}}"],
    )
    value = completed.stdout.decode("ascii").strip()
    if not FULL_SHA_PATTERN.fullmatch(value):
        raise AttestationError(
            "GIT_OID",
            f"revision did not resolve to a full commit: {revision}",
        )
    return value


def _commit_parents(repo_root: Path, commit: str) -> list[str]:
    line = _git(
        repo_root,
        ["rev-list", "--parents", "-n", "1", commit],
    ).stdout.decode("ascii").strip()
    parts = line.split()
    if not parts or parts[0] != commit:
        raise AttestationError(
            "GIT_PARENT_QUERY",
            f"unexpected parent query result for {commit}",
        )
    return parts[1:]


def _git_blob(repo_root: Path, commit: str, relative: str) -> bytes:
    return _git(
        repo_root,
        ["cat-file", "blob", f"{commit}:{relative}"],
    ).stdout


def _git_path_absent(
    repo_root: Path,
    commit: str,
    relative: str,
) -> bool:
    completed = _git(
        repo_root,
        ["cat-file", "-e", f"{commit}:{relative}"],
        check=False,
    )
    if completed.returncode == 0:
        return False
    if completed.returncode in (1, 128):
        return True
    raise AttestationError(
        "GIT_QUERY_FAILED",
        f"could not test path absence at {commit}: {relative}",
    )


def _diff_entries(
    repo_root: Path,
    parent: str,
    commit: str,
) -> list[tuple[str, tuple[str, ...]]]:
    raw = _git(
        repo_root,
        [
            "diff-tree",
            "--no-commit-id",
            "--name-status",
            "-r",
            "-z",
            parent,
            commit,
        ],
    ).stdout
    parts = raw.split(b"\x00")
    if parts and parts[-1] == b"":
        parts.pop()
    entries: list[tuple[str, tuple[str, ...]]] = []
    index = 0
    while index < len(parts):
        try:
            status = parts[index].decode("ascii")
        except UnicodeDecodeError as error:
            raise AttestationError(
                "GIT_DIFF_ENCODING",
                "diff status is not ASCII",
            ) from error
        index += 1
        path_count = 2 if status[:1] in {"R", "C"} else 1
        if index + path_count > len(parts):
            raise AttestationError(
                "GIT_DIFF_SHAPE",
                "truncated NUL-delimited diff entry",
            )
        try:
            paths = tuple(
                item.decode("utf-8", errors="strict")
                for item in parts[index : index + path_count]
            )
        except UnicodeDecodeError as error:
            raise AttestationError(
                "GIT_DIFF_ENCODING",
                "diff path is not UTF-8",
            ) from error
        entries.append((status, paths))
        index += path_count
    return entries


def _resolve_repo_file(repo_root: Path, relative: str) -> Path:
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise AttestationError(
            "PATH_INVALID",
            f"invalid repository-relative path: {relative}",
        )
    current = repo_root
    for part in pure.parts:
        current = current / part
        if _is_link_or_junction(current):
            raise AttestationError(
                "PATH_SYMLINK",
                f"symlink or junction is forbidden: {relative}",
            )
    try:
        resolved = current.resolve(strict=True)
    except FileNotFoundError as error:
        raise AttestationError(
            "PATH_MISSING",
            f"required path is absent: {relative}",
        ) from error
    if not resolved.is_relative_to(repo_root) or not resolved.is_file():
        raise AttestationError(
            "PATH_ESCAPE",
            f"path escaped repository: {relative}",
        )
    return resolved


def _validate_schema(schema: dict[str, Any], value: Any) -> None:
    from jsonschema import Draft202012Validator, FormatChecker

    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).validate(value)
    except Exception as error:
        raise AttestationError(
            "SCHEMA_VALIDATION",
            str(error),
        ) from error


def _load_trusted_contracts(
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    schema_path = _resolve_repo_file(
        repo_root,
        SCHEMA_PATH.as_posix(),
    )
    template_path = _resolve_repo_file(
        repo_root,
        TEMPLATE_PATH.as_posix(),
    )
    schema_raw = schema_path.read_bytes()
    template_raw = template_path.read_bytes()
    if sha256_bytes(schema_raw) != TRUSTED_SCHEMA_SHA256:
        raise AttestationError(
            "TRUSTED_SCHEMA_HASH_MISMATCH",
            "external attestation Schema bytes differ",
        )
    if sha256_bytes(template_raw) != TRUSTED_TEMPLATE_SHA256:
        raise AttestationError(
            "TRUSTED_TEMPLATE_HASH_MISMATCH",
            "external attestation template bytes differ",
        )
    schema = decode_json_bytes(
        schema_raw,
        label=SCHEMA_PATH.as_posix(),
    )
    template = decode_json_bytes(
        template_raw,
        label=TEMPLATE_PATH.as_posix(),
    )
    if not isinstance(schema, dict) or not isinstance(template, dict):
        raise AttestationError(
            "CONTRACT_SHAPE",
            "Schema and template must be JSON objects",
        )
    _validate_schema(schema, template)
    return schema, template


def _parse_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or not UTC_PATTERN.fullmatch(value):
        raise AttestationError(
            "TIME_FORMAT",
            f"{label} must be second-resolution UTC Z time",
        )
    try:
        parsed = datetime.strptime(
            value,
            "%Y-%m-%dT%H:%M:%SZ",
        )
    except ValueError as error:
        raise AttestationError(
            "TIME_FORMAT",
            f"invalid timestamp for {label}: {value}",
        ) from error
    return parsed.replace(tzinfo=timezone.utc)


def _expected_attestation_id(document: dict[str, Any]) -> str:
    completed = _parse_utc(
        document["external_query"]["query_completed_at"],
        "external_query.query_completed_at",
    )
    timestamp = completed.strftime("%Y%m%dT%H%M%SZ")
    digest = document["external_query"]["result_summary"][
        "normalized_listing_sha256"
    ]
    return f"eda-{timestamp}-{digest[:12]}"


def _validate_times(
    document: dict[str, Any],
    verification_time: datetime,
) -> None:
    checked = _parse_utc(
        document["repository_absence_evidence"]["checked_at"],
        "repository_absence_evidence.checked_at",
    )
    started = _parse_utc(
        document["external_query"]["query_started_at"],
        "external_query.query_started_at",
    )
    completed = _parse_utc(
        document["external_query"]["query_completed_at"],
        "external_query.query_completed_at",
    )
    attested = _parse_utc(
        document["observer"]["attested_at"],
        "observer.attested_at",
    )
    valid_from = _parse_utc(
        document["validity"]["valid_from"],
        "validity.valid_from",
    )
    valid_until = _parse_utc(
        document["validity"]["valid_until"],
        "validity.valid_until",
    )
    if not checked <= started <= completed <= attested:
        raise AttestationError(
            "TIME_ORDER",
            "absence, query, and attestation timestamps are out of order",
        )
    if (started - checked).total_seconds() > 120:
        raise AttestationError(
            "ABSENCE_EVIDENCE_STALE",
            "repository absence evidence is older than 120 seconds",
        )
    if (completed - started).total_seconds() > 120:
        raise AttestationError(
            "QUERY_DURATION",
            "external query exceeded 120 seconds",
        )
    if valid_from != completed:
        raise AttestationError(
            "VALIDITY_START",
            "valid_from must equal query_completed_at",
        )
    if valid_until != completed + timedelta(seconds=600):
        raise AttestationError(
            "VALIDITY_WINDOW",
            "valid_until must be exactly 600 seconds after completion",
        )
    if not attested <= verification_time <= valid_until:
        raise AttestationError(
            "ATTESTATION_EXPIRED",
            "current verifier time is outside the attestation window",
        )


def _validate_instance_fields(
    document: dict[str, Any],
    relative: str,
    expected_verifier_sha256: str,
    verification_time: datetime,
) -> None:
    if document["attestation_id"] != _expected_attestation_id(document):
        raise AttestationError(
            "ATTESTATION_ID",
            "attestation_id does not bind query time and listing digest",
        )
    expected_path = (
        f"{ATTESTATION_PREFIX}{document['attestation_id']}.json"
    )
    if relative != expected_path or document["instance_path"] != expected_path:
        raise AttestationError(
            "INSTANCE_PATH",
            "attestation path does not match attestation_id",
        )
    binding = document["commit_binding"]
    evidence = document["repository_absence_evidence"]
    if evidence["observed_head"] != binding["observed_head"]:
        raise AttestationError(
            "OBSERVED_HEAD_BINDING",
            "repository evidence and commit binding disagree",
        )
    if evidence["verifier_sha256"] != expected_verifier_sha256:
        raise AttestationError(
            "VERIFIER_HASH_BINDING",
            "attestation does not bind the trusted verifier bytes",
        )
    _validate_times(document, verification_time)


def _validate_commit_b(
    repo_root: Path,
    document: dict[str, Any],
    expected_verifier_sha256: str,
    expected_finalize_commit_b: str,
    expected_frozen_artifact_set_digest: str,
) -> None:
    binding = document["commit_binding"]
    commit_a = binding["freeze_anchor_commit_a"]
    commit_b = binding["finalize_commit_b"]
    if binding["finalize_commit_b"] != expected_finalize_commit_b:
        raise AttestationError(
            "EXPECTED_COMMIT_B_MISMATCH",
            "attestation commit B differs from the caller trust anchor",
        )
    if (
        binding["frozen_artifact_set_digest"]
        != expected_frozen_artifact_set_digest
    ):
        raise AttestationError(
            "EXPECTED_FROZEN_ROOT_MISMATCH",
            "attestation frozen root differs from the caller trust anchor",
        )
    if _git_oid(repo_root, commit_a) != commit_a:
        raise AttestationError(
            "COMMIT_A_BINDING",
            "freeze anchor does not resolve exactly",
        )
    if _git_oid(repo_root, commit_b) != commit_b:
        raise AttestationError(
            "COMMIT_B_BINDING",
            "finalize commit does not resolve exactly",
        )
    if _commit_parents(repo_root, commit_b) != [commit_a]:
        raise AttestationError(
            "COMMIT_B_PARENT",
            "finalize commit B must be the direct child of commit A",
        )
    if _diff_entries(repo_root, commit_a, commit_b) != [
        ("M", (MANIFEST_PATH,))
    ]:
        raise AttestationError(
            "COMMIT_B_DELTA",
            "commit B must only modify the candidate manifest",
        )
    manifest_a_raw = _git_blob(
        repo_root,
        commit_a,
        MANIFEST_PATH,
    )
    manifest_b_raw = _git_blob(
        repo_root,
        commit_b,
        MANIFEST_PATH,
    )
    manifest_a = decode_json_bytes(
        manifest_a_raw,
        label=f"{commit_a}:{MANIFEST_PATH}",
    )
    manifest_b = decode_json_bytes(
        manifest_b_raw,
        label=f"{commit_b}:{MANIFEST_PATH}",
    )
    if (
        not isinstance(manifest_a, dict)
        or not isinstance(manifest_b, dict)
    ):
        raise AttestationError(
            "MANIFEST_SHAPE",
            "candidate manifests must be JSON objects",
        )
    before = copy.deepcopy(manifest_a)
    after = copy.deepcopy(manifest_b)
    for key in ALLOWED_B_MANIFEST_CHANGES:
        before.pop(key, None)
        after.pop(key, None)
    if before != after:
        raise AttestationError(
            "COMMIT_B_MANIFEST_SCOPE",
            "manifest changed outside the three frozen transition fields",
        )
    if (
        manifest_a.get("run_id") != "continuous-002"
        or manifest_a.get("status") != "preparing"
        or manifest_a.get("freeze_commit") is not None
        or manifest_b.get("run_id") != "continuous-002"
        or manifest_b.get("status") != "frozen"
        or manifest_b.get("freeze_commit") != commit_a
    ):
        raise AttestationError(
            "COMMIT_B_MANIFEST_STATE",
            "manifest A/B transition is not the fixed freeze transition",
        )
    if (
        sha256_bytes(manifest_b_raw)
        != binding["frozen_manifest_sha256"]
        or manifest_b.get("frozen_artifact_set_digest")
        != binding["frozen_artifact_set_digest"]
    ):
        raise AttestationError(
            "FROZEN_ROOT_BINDING",
            "attestation does not bind the frozen B manifest and root",
        )
    for relative, expected_hash, code in (
        (
            SCHEMA_PATH.as_posix(),
            TRUSTED_SCHEMA_SHA256,
            "COMMIT_B_SCHEMA_HASH",
        ),
        (
            TEMPLATE_PATH.as_posix(),
            TRUSTED_TEMPLATE_SHA256,
            "COMMIT_B_TEMPLATE_HASH",
        ),
        (
            VERIFIER_PATH.as_posix(),
            expected_verifier_sha256,
            "COMMIT_B_VERIFIER_HASH",
        ),
    ):
        if sha256_bytes(_git_blob(repo_root, commit_b, relative)) != (
            expected_hash
        ):
            raise AttestationError(
                code,
                f"commit B does not contain trusted bytes: {relative}",
            )
    evidence = document["repository_absence_evidence"]
    delta_raw = _git_blob(repo_root, commit_b, DELTA_PATH)
    if sha256_bytes(delta_raw) != evidence["formal_run_delta_sha256"]:
        raise AttestationError(
            "DELTA_HASH_BINDING",
            "formal-run-delta hash differs at commit B",
        )
    delta = decode_json_bytes(
        delta_raw,
        label=f"{commit_b}:{DELTA_PATH}",
    )
    try:
        absence = delta["repository_absence"]
        denylist = absence["denylist_contract"]
        gate_policy = delta["gate_policy"]
    except (KeyError, TypeError) as error:
        raise AttestationError(
            "DELTA_EVIDENCE_SHAPE",
            "formal-run-delta lacks required absence evidence",
        ) from error
    if (
        delta.get("candidate_run_id") != "continuous-002"
        or absence.get("status") != "passed"
        or absence.get("matches") != []
        or absence.get("scan_snapshot_sha256")
        != evidence["pre_b_scan_snapshot_sha256"]
        or denylist != evidence["denylist_contract"]
        or gate_policy.get(
            "external_dispatch_attestation_instances_allowed"
        )
        is not False
        or gate_policy.get(
            "external_dispatch_attestation_required_after_b"
        )
        is not True
    ):
        raise AttestationError(
            "DELTA_EVIDENCE_BINDING",
            "formal-run-delta absence or gate policy is not closed",
        )
    denylist_raw = _git_blob(repo_root, commit_b, DENYLIST_PATH)
    if sha256_bytes(denylist_raw) != denylist["sha256"]:
        raise AttestationError(
            "DENYLIST_HASH_BINDING",
            "denylist bytes differ at commit B",
        )


def _validate_attestation_history(
    repo_root: Path,
    document: dict[str, Any],
    schema: dict[str, Any],
    observed_head: str,
    expected_verifier_sha256: str,
    expected_finalize_commit_b: str,
    expected_frozen_artifact_set_digest: str,
) -> list[tuple[str, dict[str, Any]]]:
    binding = document["commit_binding"]
    commit_b = binding["finalize_commit_b"]
    ancestor = _git(
        repo_root,
        ["merge-base", "--is-ancestor", commit_b, observed_head],
        check=False,
    )
    if ancestor.returncode != 0:
        raise AttestationError(
            "OBSERVED_HEAD_ANCESTRY",
            "observed_head is not commit B or its descendant",
        )
    if observed_head == commit_b:
        commits: list[str] = []
    else:
        commits = (
            _git(
                repo_root,
                ["rev-list", "--reverse", f"{commit_b}..{observed_head}"],
            )
            .stdout.decode("ascii")
            .splitlines()
        )
    history: list[tuple[str, dict[str, Any]]] = []
    expected_parent = commit_b
    expected_sequence = 1
    previous_query_time: datetime | None = None
    for commit in commits:
        if not FULL_SHA_PATTERN.fullmatch(commit):
            raise AttestationError(
                "HISTORY_COMMIT",
                "history contains a non-full commit id",
            )
        if _commit_parents(repo_root, commit) != [expected_parent]:
            raise AttestationError(
                "HISTORY_PARENT",
                "post-B history is not a linear append-only chain",
            )
        entries = _diff_entries(repo_root, expected_parent, commit)
        if (
            len(entries) != 1
            or entries[0][0] != "A"
            or len(entries[0][1]) != 1
            or not entries[0][1][0].startswith(ATTESTATION_PREFIX)
        ):
            raise AttestationError(
                "HISTORY_DELTA",
                "post-B commit is not one attestation file addition",
            )
        relative = entries[0][1][0]
        prior_raw = _git_blob(repo_root, commit, relative)
        prior = decode_json_bytes(
            prior_raw,
            label=f"{commit}:{relative}",
        )
        _validate_schema(schema, prior)
        if prior.get("artifact_type") != "external_dispatch_attestation":
            raise AttestationError(
                "HISTORY_ARTIFACT_TYPE",
                "post-B added file is not an attestation instance",
            )
        prior_gate = _parse_utc(
            prior["observer"]["attested_at"],
            "prior observer.attested_at",
        )
        _validate_instance_fields(
            prior,
            relative,
            expected_verifier_sha256,
            prior_gate,
        )
        _validate_commit_b(
            repo_root,
            prior,
            expected_verifier_sha256,
            expected_finalize_commit_b,
            expected_frozen_artifact_set_digest,
        )
        prior_binding = prior["commit_binding"]
        if (
            prior["instance_path"] != relative
            or prior_binding["finalize_commit_b"] != commit_b
            or prior_binding["freeze_anchor_commit_a"]
            != binding["freeze_anchor_commit_a"]
            or prior_binding["frozen_artifact_set_digest"]
            != binding["frozen_artifact_set_digest"]
            or prior_binding["observed_head"] != expected_parent
            or prior_binding["previous_attestation_commit"]
            != (None if expected_sequence == 1 else expected_parent)
            or prior_binding["sequence"] != expected_sequence
            or prior["repository_absence_evidence"]["verifier_sha256"]
            != expected_verifier_sha256
            or prior["attestation_id"] != _expected_attestation_id(prior)
        ):
            raise AttestationError(
                "HISTORY_BINDING",
                "prior attestation does not continue the frozen chain",
            )
        query_time = _parse_utc(
            prior["external_query"]["query_completed_at"],
            "prior query_completed_at",
        )
        if (
            previous_query_time is not None
            and query_time <= previous_query_time
        ):
            raise AttestationError(
                "HISTORY_TIME_ORDER",
                "attestation query times are not strictly increasing",
            )
        history.append((commit, prior))
        previous_query_time = query_time
        expected_parent = commit
        expected_sequence += 1
    if expected_parent != observed_head:
        raise AttestationError(
            "HISTORY_HEAD",
            "history did not terminate at observed_head",
        )
    if binding["sequence"] != len(history) + 1:
        raise AttestationError(
            "ATTESTATION_SEQUENCE",
            "current attestation sequence is not the next append",
        )
    expected_previous = None if not history else observed_head
    if binding["previous_attestation_commit"] != expected_previous:
        raise AttestationError(
            "PREVIOUS_ATTESTATION",
            "previous_attestation_commit does not match history",
        )
    if history:
        current_query_time = _parse_utc(
            document["external_query"]["query_completed_at"],
            "external_query.query_completed_at",
        )
        prior_query_time = _parse_utc(
            history[-1][1]["external_query"]["query_completed_at"],
            "prior query_completed_at",
        )
        if current_query_time <= prior_query_time:
            raise AttestationError(
                "ATTESTATION_TIME_ORDER",
                "current query is not newer than the prior attestation",
            )
    return history


def _verify_self_hash(
    repo_root: Path,
    expected_verifier_sha256: str,
) -> str:
    if not SHA256_PATTERN.fullmatch(expected_verifier_sha256):
        raise AttestationError(
            "VERIFIER_HASH_ARGUMENT",
            "expected verifier hash must be lowercase SHA-256",
        )
    expected_path = _resolve_repo_file(
        repo_root,
        VERIFIER_PATH.as_posix(),
    )
    if Path(__file__).resolve() != expected_path:
        raise AttestationError(
            "VERIFIER_PATH_MISMATCH",
            "running verifier is not the repository-bound verifier",
        )
    actual = sha256_bytes(expected_path.read_bytes())
    if actual != expected_verifier_sha256:
        raise AttestationError(
            "VERIFIER_HASH_MISMATCH",
            "running verifier bytes differ from caller trust root",
        )
    return actual


def verify_template(
    repo_root: Path,
    expected_verifier_sha256: str,
) -> dict[str, Any]:
    verifier_sha256 = _verify_self_hash(
        repo_root,
        expected_verifier_sha256,
    )
    _, template = _load_trusted_contracts(repo_root)
    forbidden_keys = {"task_id", "thread_id", "session_id"}
    if forbidden_keys & set(template.get("dynamic_slots", {})):
        raise AttestationError(
            "TEMPLATE_RUNTIME_IDENTIFIER",
            "template exposes a real external object identifier slot",
        )
    if any(
        value is not None
        for value in template.get("dynamic_slots", {}).values()
    ):
        raise AttestationError(
            "TEMPLATE_NOT_EMPTY",
            "pre-gate template has populated dynamic evidence",
        )
    return {
        "actual_dispatch_performed": False,
        "artifact": TEMPLATE_PATH.as_posix(),
        "artifact_sha256": TRUSTED_TEMPLATE_SHA256,
        "external_query_performed": False,
        "runner_or_comparator_executed": False,
        "schema_sha256": TRUSTED_SCHEMA_SHA256,
        "status": "template_verified",
        "verifier_sha256": verifier_sha256,
    }


def _load_instance(
    repo_root: Path,
    relative: str,
    schema: dict[str, Any],
) -> tuple[Path, bytes, dict[str, Any]]:
    if not relative.startswith(ATTESTATION_PREFIX):
        raise AttestationError(
            "INSTANCE_PATH",
            "attestation is outside the append-only path family",
        )
    path = _resolve_repo_file(repo_root, relative)
    raw = path.read_bytes()
    document = decode_json_bytes(raw, label=relative)
    if not isinstance(document, dict):
        raise AttestationError(
            "INSTANCE_SHAPE",
            "attestation must be a JSON object",
        )
    _validate_schema(schema, document)
    if document.get("artifact_type") != "external_dispatch_attestation":
        raise AttestationError(
            "INSTANCE_ARTIFACT_TYPE",
            "expected a real attestation instance",
        )
    return path, raw, document


def _verify_common(
    repo_root: Path,
    relative: str,
    expected_verifier_sha256: str,
    expected_finalize_commit_b: str,
    expected_frozen_artifact_set_digest: str,
    verification_time: datetime,
) -> tuple[dict[str, Any], bytes, dict[str, Any], str]:
    verifier_sha256 = _verify_self_hash(
        repo_root,
        expected_verifier_sha256,
    )
    schema, _ = _load_trusted_contracts(repo_root)
    _, raw, document = _load_instance(
        repo_root,
        relative,
        schema,
    )
    _validate_instance_fields(
        document,
        relative,
        verifier_sha256,
        verification_time,
    )
    _validate_commit_b(
        repo_root,
        document,
        verifier_sha256,
        expected_finalize_commit_b,
        expected_frozen_artifact_set_digest,
    )
    observed_head = document["commit_binding"]["observed_head"]
    _validate_attestation_history(
        repo_root,
        document,
        schema,
        observed_head,
        verifier_sha256,
        expected_finalize_commit_b,
        expected_frozen_artifact_set_digest,
    )
    return schema, raw, document, verifier_sha256


def verify_draft(
    repo_root: Path,
    relative: str,
    expected_verifier_sha256: str,
    expected_finalize_commit_b: str,
    expected_frozen_artifact_set_digest: str,
    verification_time: datetime,
) -> dict[str, Any]:
    _, raw, document, verifier_sha256 = _verify_common(
        repo_root,
        relative,
        expected_verifier_sha256,
        expected_finalize_commit_b,
        expected_frozen_artifact_set_digest,
        verification_time,
    )
    observed_head = document["commit_binding"]["observed_head"]
    if _git_oid(repo_root, "HEAD") != observed_head:
        raise AttestationError(
            "DRAFT_HEAD",
            "draft must be generated directly on observed_head",
        )
    if not _git_path_absent(repo_root, observed_head, relative):
        raise AttestationError(
            "DRAFT_OVERWRITE",
            "draft path already exists at observed_head",
        )
    status = _git(
        repo_root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    ).stdout
    expected_status = f"?? {relative}\x00".encode("utf-8")
    if status != expected_status:
        raise AttestationError(
            "DRAFT_WORKTREE",
            "worktree must contain only the untracked attestation draft",
        )
    return {
        "actual_dispatch_performed": False,
        "artifact": relative,
        "artifact_sha256": sha256_bytes(raw),
        "external_query_performed": False,
        "observed_head": observed_head,
        "runner_or_comparator_executed": False,
        "status": "draft_verified",
        "verifier_sha256": verifier_sha256,
    }


def verify_committed(
    repo_root: Path,
    relative: str,
    attestation_commit: str,
    expected_verifier_sha256: str,
    expected_finalize_commit_b: str,
    expected_frozen_artifact_set_digest: str,
    verification_time: datetime,
) -> dict[str, Any]:
    _, raw, document, verifier_sha256 = _verify_common(
        repo_root,
        relative,
        expected_verifier_sha256,
        expected_finalize_commit_b,
        expected_frozen_artifact_set_digest,
        verification_time,
    )
    commit = _git_oid(repo_root, attestation_commit)
    if commit != attestation_commit or _git_oid(repo_root, "HEAD") != commit:
        raise AttestationError(
            "LATEST_ATTESTATION_COMMIT",
            "gate must reference the latest attestation commit at HEAD",
        )
    if _git(
        repo_root,
        ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
    ).stdout:
        raise AttestationError(
            "COMMITTED_WORKTREE",
            "committed verification requires a clean worktree",
        )
    observed_head = document["commit_binding"]["observed_head"]
    if _commit_parents(repo_root, commit) != [observed_head]:
        raise AttestationError(
            "SAVE_COMMIT_PARENT",
            "attestation commit parent differs from observed_head",
        )
    if _diff_entries(repo_root, observed_head, commit) != [
        ("A", (relative,))
    ]:
        raise AttestationError(
            "SAVE_COMMIT_DELTA",
            "attestation commit must add exactly the current proof",
        )
    if _git_blob(repo_root, commit, relative) != raw:
        raise AttestationError(
            "SAVE_COMMIT_BYTES",
            "working tree proof differs from committed proof bytes",
        )
    return {
        "actual_dispatch_performed": False,
        "artifact": relative,
        "artifact_sha256": sha256_bytes(raw),
        "attestation_commit": commit,
        "external_query_performed": False,
        "observed_head": observed_head,
        "runner_or_comparator_executed": False,
        "status": "committed_attestation_verified",
        "verifier_sha256": verifier_sha256,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("verify-template", "verify-draft", "verify-committed"),
    )
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--attestation-path")
    parser.add_argument("--attestation-commit")
    parser.add_argument("--expected-finalize-commit-b")
    parser.add_argument("--expected-frozen-artifact-set-digest")
    parser.add_argument("--gate-presented-at", help=argparse.SUPPRESS)
    parser.add_argument("--expected-verifier-sha256", required=True)
    parser.add_argument(
        "--allow-repository-and-git-object-byte-reads",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if not sys.flags.isolated:
            raise AttestationError(
                "ISOLATED_INTERPRETER_REQUIRED",
                "invoke this verifier with python -I",
            )
        if not args.allow_repository_and_git_object_byte_reads:
            raise AttestationError(
                "REPOSITORY_BYTE_READ_ACK_REQUIRED",
                "repository and Git-object reads require acknowledgement",
            )
        repo_root = args.repo_root.resolve()
        if not repo_root.is_dir():
            raise AttestationError(
                "REPO_ROOT",
                f"repository root is not a directory: {repo_root}",
            )
        _verify_repository_boundary(repo_root)
        if args.gate_presented_at is not None:
            raise AttestationError(
                "CALLER_TIME_OVERRIDE_FORBIDDEN",
                "production verification uses the verifier host UTC clock",
            )
        if args.command == "verify-template":
            if (
                args.attestation_path is not None
                or args.attestation_commit is not None
                or args.expected_finalize_commit_b is not None
                or args.expected_frozen_artifact_set_digest is not None
            ):
                raise AttestationError(
                    "CLI_ARGUMENT_SCOPE",
                    "template verification does not accept instance fields",
                )
            result = verify_template(
                repo_root,
                args.expected_verifier_sha256,
            )
        else:
            if (
                not args.attestation_path
                or not args.expected_finalize_commit_b
                or not args.expected_frozen_artifact_set_digest
            ):
                raise AttestationError(
                    "CLI_ARGUMENT_SCOPE",
                    "instance verification needs path, expected B, and root",
                )
            if not FULL_SHA_PATTERN.fullmatch(
                args.expected_finalize_commit_b
            ):
                raise AttestationError(
                    "EXPECTED_COMMIT_B_ARGUMENT",
                    "expected commit B must be a lowercase full Git OID",
                )
            if (
                not SHA256_PATTERN.fullmatch(
                    args.expected_frozen_artifact_set_digest
                )
                or args.expected_frozen_artifact_set_digest == "0" * 64
            ):
                raise AttestationError(
                    "EXPECTED_FROZEN_ROOT_ARGUMENT",
                    "expected frozen root must be a nonzero lowercase SHA-256",
                )
            verification_time = datetime.now(timezone.utc).replace(
                microsecond=0
            )
            if args.command == "verify-draft":
                if args.attestation_commit is not None:
                    raise AttestationError(
                        "CLI_ARGUMENT_SCOPE",
                        "draft verification rejects a save commit",
                    )
                result = verify_draft(
                    repo_root,
                    args.attestation_path,
                    args.expected_verifier_sha256,
                    args.expected_finalize_commit_b,
                    args.expected_frozen_artifact_set_digest,
                    verification_time,
                )
            else:
                if not args.attestation_commit:
                    raise AttestationError(
                        "CLI_ARGUMENT_SCOPE",
                        "committed verification needs its save commit",
                    )
                result = verify_committed(
                    repo_root,
                    args.attestation_path,
                    args.attestation_commit,
                    args.expected_verifier_sha256,
                    args.expected_finalize_commit_b,
                    args.expected_frozen_artifact_set_digest,
                    verification_time,
                )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        AttestationError,
        KeyError,
        OSError,
        subprocess.SubprocessError,
        TypeError,
        ValueError,
    ) as error:
        message = (
            str(error)
            if isinstance(error, AttestationError)
            else f"VERIFY_INPUT: {error}"
        )
        print(
            json.dumps(
                {
                    "actual_dispatch_performed": False,
                    "error": message,
                    "external_query_performed": False,
                    "runner_or_comparator_executed": False,
                    "status": "failed_closed",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
