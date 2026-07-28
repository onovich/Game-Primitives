#!/usr/bin/env python3
"""Read-only verifier for formal post-gate absence denylist 0.1.0.

The verifier is intentionally self-contained. It does not import or execute
any candidate tool, runner, comparator, dispatcher, or reveal component.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA_PATH = PILOT / (
    "schema/formal-post-gate-absence-denylist-0.1.0.schema.json"
)
CONTRACT_PATH = PILOT / (
    "contracts/formal-post-gate-absence-denylist-0.1.0.json"
)
VERIFIER_PATH = PILOT / (
    "tools/verify-formal-post-gate-absence-v0.1.0.py"
)
TRUSTED_SCHEMA_SHA256 = (
    "5a8c16e7dc82c9517e35e20f06d5d64d4cc8b5eac406fc62ea7c46c8ee0a1f7d"
)
TRUSTED_CONTRACT_SHA256 = (
    "ab4218109a8c29076d0ab95d2932b734725f83e836a1c2de60bc0cacf8cc926f"
)
CANDIDATE_RUN_ID = "continuous-002"
CANDIDATE_RUN_ROOT = (
    PILOT / "runs" / CANDIDATE_RUN_ID
).as_posix()
POST_GATE_PREFIXES = (
    "execution/raw/",
    "reports/",
    "reveal/",
    "submissions/",
)
POST_GATE_PATHS = {
    "execution/execution-result.json",
    "execution/trace-bundle.json",
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


class AbsenceError(ValueError):
    """A deterministic fail-closed verification error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def canonical_value_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AbsenceError(
                "JSON_DUPLICATE_KEY",
                f"duplicate JSON key: {key}",
            )
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> Any:
    raise AbsenceError(
        "JSON_NONFINITE_NUMBER",
        f"non-finite JSON number: {value}",
    )


def decode_json_bytes(
    raw: bytes,
    *,
    label: str,
    require_canonical: bool,
) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AbsenceError(
            "JSON_BYTES_BOM",
            f"UTF-8 BOM is forbidden: {label}",
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AbsenceError(
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
        raise AbsenceError(
            "JSON_SYNTAX",
            f"invalid JSON syntax: {label}: {error}",
        ) from error
    if require_canonical and canonical_bytes(value) != raw:
        raise AbsenceError(
            "JSON_BYTES_NONCANONICAL",
            f"JSON bytes are not canonical: {label}",
        )
    return value


def _permissive_json_value(raw: bytes) -> Any | None:
    try:
        return json.loads(
            raw,
            object_pairs_hook=_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (
        AbsenceError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return None


def _raw_contains_candidate_binding(raw: bytes) -> bool:
    for encoding in (
        "utf-8",
        "utf-16-le",
        "utf-16-be",
        "utf-32-le",
        "utf-32-be",
    ):
        if CANDIDATE_RUN_ID.encode(encoding) in raw:
            return True
    return False


def _repository_entries(repo_root: Path) -> list[Path]:
    entries: list[Path] = []
    walk_error: OSError | None = None

    def record_error(error: OSError) -> None:
        nonlocal walk_error
        walk_error = error

    for directory, dirnames, filenames in os.walk(
        repo_root,
        topdown=True,
        onerror=record_error,
        followlinks=False,
    ):
        if walk_error is not None:
            raise AbsenceError(
                "REPOSITORY_TRAVERSAL_FAILED",
                f"repository traversal failed: {walk_error}",
            )
        parent = Path(directory)
        relative_parent = parent.relative_to(repo_root)
        if not relative_parent.parts:
            dirnames[:] = [
                name for name in dirnames if name.casefold() != ".git"
            ]
            filenames = [
                name for name in filenames if name.casefold() != ".git"
            ]
        dirnames.sort(key=lambda name: (name.casefold(), name))
        filenames.sort(key=lambda name: (name.casefold(), name))
        for name in dirnames:
            entries.append(parent / name)
        for name in filenames:
            entries.append(parent / name)
    if walk_error is not None:
        raise AbsenceError(
            "REPOSITORY_TRAVERSAL_FAILED",
            f"repository traversal failed: {walk_error}",
        )
    entries.sort(
        key=lambda path: (
            path.relative_to(repo_root).as_posix().casefold(),
            path.relative_to(repo_root).as_posix(),
        )
    )
    seen: dict[str, str] = {}
    for path in entries:
        relative = path.relative_to(repo_root).as_posix()
        folded = relative.casefold()
        previous = seen.get(folded)
        if previous is not None and previous != relative:
            raise AbsenceError(
                "REPOSITORY_PATH_CASEFOLD_COLLISION",
                f"repository paths collide after casefold: "
                f"{previous!r}, {relative!r}",
            )
        seen[folded] = relative
    return entries


def resolve_repo_file(repo_root: Path, relative: Path) -> Path:
    if relative.is_absolute() or not relative.parts:
        raise AbsenceError(
            "PATH_INVALID",
            f"path is not repository-relative: {relative}",
        )
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise AbsenceError(
            "PATH_INVALID",
            f"path contains a forbidden segment: {relative}",
        )
    root = repo_root.resolve()
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise AbsenceError(
                "PATH_SYMLINK",
                f"fixed verifier input is a symlink: {relative}",
            )
    try:
        resolved = current.resolve(strict=True)
    except FileNotFoundError as error:
        raise AbsenceError(
            "PATH_MISSING",
            f"required verifier input is absent: {relative}",
        ) from error
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise AbsenceError(
            "PATH_ESCAPE",
            f"required verifier input escaped repository: {relative}",
        )
    return resolved


def _git(repo_root: Path, arguments: list[str]) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AbsenceError(
            "GIT_QUERY_FAILED",
            f"git {' '.join(arguments)} failed: {stderr}",
        )
    return completed.stdout


def _tracked_path_matches_head(
    repo_root: Path,
    relative: str,
    raw: bytes,
) -> bool:
    head_blob = _git(
        repo_root,
        ["cat-file", "blob", f"HEAD:{relative}"],
    )
    return head_blob == raw


def _load_contract(
    repo_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    schema_path = resolve_repo_file(repo_root, SCHEMA_PATH)
    schema_raw = schema_path.read_bytes()
    if sha256_bytes(schema_raw) != TRUSTED_SCHEMA_SHA256:
        raise AbsenceError(
            "TRUSTED_SCHEMA_HASH_MISMATCH",
            f"trusted Schema bytes differ: {SCHEMA_PATH.as_posix()}",
        )
    schema = decode_json_bytes(
        schema_raw,
        label=SCHEMA_PATH.as_posix(),
        require_canonical=True,
    )
    if not isinstance(schema, dict):
        raise AbsenceError(
            "TRUSTED_SCHEMA_INVALID",
            "trusted denylist Schema is not an object",
        )
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise AbsenceError(
            "TRUSTED_SCHEMA_INVALID",
            f"trusted denylist Schema is invalid: {error}",
        ) from error

    contract_path = resolve_repo_file(repo_root, CONTRACT_PATH)
    contract_raw = contract_path.read_bytes()
    contract = decode_json_bytes(
        contract_raw,
        label=CONTRACT_PATH.as_posix(),
        require_canonical=True,
    )
    if not isinstance(contract, dict):
        raise AbsenceError(
            "DENYLIST_SCHEMA_MISMATCH",
            "denylist instance is not an object",
        )
    errors = sorted(
        Draft202012Validator(schema).iter_errors(contract),
        key=lambda error: (
            tuple(str(item) for item in error.absolute_path),
            error.message,
        ),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(item) for item in first.absolute_path)
        raise AbsenceError(
            "DENYLIST_SCHEMA_MISMATCH",
            f"denylist instance differs at {location or '<root>'}: "
            f"{first.message}",
        )
    trusted_rules = schema["properties"]["rules"]["const"]
    if contract["rules"] != trusted_rules:
        raise AbsenceError(
            "DENYLIST_RULE_MISMATCH",
            "denylist rules differ from the trusted Schema",
        )
    contract_sha256 = sha256_bytes(contract_raw)
    if contract_sha256 != TRUSTED_CONTRACT_SHA256:
        raise AbsenceError(
            "TRUSTED_CONTRACT_HASH_MISMATCH",
            f"trusted denylist bytes differ: {CONTRACT_PATH.as_posix()}",
        )
    return contract, trusted_rules, contract_sha256


def _path_segments(path: str) -> list[str]:
    if not path or "\\" in path or path.startswith("/"):
        raise AbsenceError(
            "PATH_PATTERN_UNSUPPORTED",
            f"path pattern is not canonical: {path!r}",
        )
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise AbsenceError(
            "PATH_PATTERN_UNSUPPORTED",
            f"path pattern contains a forbidden segment: {path!r}",
        )
    return parts


def _path_matches(relative: str, pattern: str) -> bool:
    """Match the admitted repository-relative gitwildmatch subset."""

    if (
        pattern.startswith(("!", "/"))
        or "\\" in pattern
        or "[" in pattern
        or "]" in pattern
    ):
        raise AbsenceError(
            "PATH_PATTERN_UNSUPPORTED",
            f"unsupported gitwildmatch syntax: {pattern!r}",
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


def _candidate_suffix(relative: str) -> str | None:
    parts = relative.split("/")
    for index, part in enumerate(parts):
        if part.casefold() == CANDIDATE_RUN_ID.casefold():
            suffix = "/".join(parts[index + 1 :])
            return suffix or None
    return None


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


def _forbidden_artifact_types(
    value: Any,
    forbidden_types: dict[str, str],
    *,
    candidate_path_binding: bool,
    include_nested: bool = True,
    _depth: int = 0,
) -> list[str]:
    matches: list[str] = []
    if isinstance(value, dict):
        local_binding = (
            (candidate_path_binding and _depth == 0)
            or _contains_candidate_binding(value)
        )
        for key, child in value.items():
            if (
                isinstance(key, str)
                and key.casefold() == "artifact_type"
                and isinstance(child, str)
            ):
                canonical = forbidden_types.get(child.casefold())
                if canonical is not None and local_binding:
                    matches.append(canonical)
            if include_nested:
                matches.extend(
                    _forbidden_artifact_types(
                        child,
                        forbidden_types,
                        candidate_path_binding=False,
                        include_nested=True,
                        _depth=_depth + 1,
                    )
                )
    elif include_nested and isinstance(value, list):
        for child in value:
            matches.extend(
                _forbidden_artifact_types(
                    child,
                    forbidden_types,
                    candidate_path_binding=False,
                    include_nested=True,
                    _depth=_depth + 1,
                )
            )
    return matches


def _casefold_mapping_value(
    value: dict[str, Any],
    key: str,
) -> Any | None:
    matches = [
        child
        for candidate, child in value.items()
        if isinstance(candidate, str)
        and candidate.casefold() == key.casefold()
    ]
    if len(matches) > 1:
        raise AbsenceError(
            "JSON_CASEFOLD_KEY_COLLISION",
            f"JSON object repeats {key!r} after casefold",
        )
    return matches[0] if matches else None


def _post_gate_path_family(relative: str) -> str | None:
    folded = relative.casefold()
    for exact in POST_GATE_PATHS:
        if folded == exact.casefold():
            return "trusted_manager_post_gate_path"
    for prefix in POST_GATE_PREFIXES:
        if folded.startswith(prefix.casefold()):
            return "trusted_manager_post_gate_prefix"
    return None


def _scan_repository(
    repo_root: Path,
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    observed_head = _git(repo_root, ["rev-parse", "HEAD"]).decode(
        "ascii",
        errors="strict",
    ).strip()
    tracked_paths = set(
        _git(
            repo_root,
            ["ls-tree", "-r", "--name-only", "HEAD"],
        )
        .decode("utf-8", errors="strict")
        .splitlines()
    )
    forbidden_types = {
        artifact_type.casefold(): artifact_type
        for rule in rules
        for artifact_type in rule["artifact_types"]
    }
    signatures = set(forbidden_types)
    for rule in rules:
        for pattern in rule["path_patterns"]:
            stem = PurePosixPath(pattern).name
            stem = stem.replace("*", "").removesuffix(".json")
            if stem:
                signatures.add(stem.casefold())

    matches: list[dict[str, Any]] = []
    snapshot: list[dict[str, str]] = []
    scanned_file_count = 0
    tracked_control_text_exemptions = 0
    canonical_prefix = CANDIDATE_RUN_ROOT.casefold() + "/"

    for path in _repository_entries(repo_root):
        relative_path = path.relative_to(repo_root)
        relative = relative_path.as_posix()
        suffix = _candidate_suffix(relative)
        if path.is_symlink():
            raise AbsenceError(
                "REPOSITORY_SYMLINK",
                f"repository scan does not admit symlinks: {relative}",
            )
        if not path.is_file():
            continue

        scanned_file_count += 1
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise AbsenceError(
                "REPOSITORY_FILE_READ_FAILED",
                f"repository file cannot be read: {relative}",
            ) from error
        snapshot.append(
            {
                "path": relative,
                "sha256": sha256_bytes(raw),
            }
        )
        if suffix is not None:
            broad_family = _post_gate_path_family(suffix)
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
                    _path_matches(suffix, pattern)
                    for pattern in rule["path_patterns"]
                ):
                    matches.append(
                        {
                            "absence_type": rule["absence_type"],
                            "match_kind": "path",
                            "path": relative,
                        }
                    )

        if path.suffix.casefold() == ".json":
            value = _permissive_json_value(raw)
            candidate_hint = (
                suffix is not None
                or (
                    value is not None
                    and _contains_candidate_binding(value)
                )
                or _raw_contains_candidate_binding(raw)
            )
            if value is None:
                if candidate_hint:
                    raise AbsenceError(
                        "CANDIDATE_JSON_INVALID",
                        f"candidate-bound JSON cannot be decoded: {relative}",
                    )
                continue
            inside_canonical_run = relative.casefold().startswith(
                canonical_prefix
            )
            if inside_canonical_run and canonical_bytes(value) != raw:
                raise AbsenceError(
                    "CANDIDATE_JSON_NONCANONICAL",
                    f"candidate JSON bytes are not canonical: {relative}",
                )
            artifact_types = _forbidden_artifact_types(
                value,
                forbidden_types,
                candidate_path_binding=suffix is not None,
                include_nested=(
                    suffix is not None or relative not in tracked_paths
                ),
            )
            for artifact_type in artifact_types:
                matches.append(
                    {
                        "absence_type": artifact_type,
                        "artifact_type": artifact_type,
                        "match_kind": "candidate_bound_artifact_type",
                        "path": relative,
                    }
                )
            if (
                suffix is not None
                and suffix.casefold() == "manifest.json"
                and isinstance(value, dict)
            ):
                artifacts = _casefold_mapping_value(value, "artifacts")
                if isinstance(artifacts, list):
                    for entry in artifacts:
                        if not isinstance(entry, dict):
                            continue
                        artifact_kind = _casefold_mapping_value(
                            entry,
                            "artifact_kind",
                        )
                        forbidden_kind = (
                            POST_GATE_MANIFEST_KINDS.get(
                                artifact_kind.casefold()
                            )
                            if isinstance(artifact_kind, str)
                            else None
                        )
                        if forbidden_kind is not None:
                            matches.append(
                                {
                                    "absence_type": forbidden_kind,
                                    "match_kind": "manifest_artifact_kind",
                                    "path": relative,
                                }
                            )
            continue

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            if (
                suffix is not None
                or CANDIDATE_RUN_ID.encode("ascii") in raw
            ):
                matches.append(
                    {
                        "absence_type": "candidate_bound_binary",
                        "match_kind": "repository_binary_binding",
                        "path": relative,
                    }
                )
            continue
        folded_text = text.casefold()
        has_signature = any(
            signature in folded_text for signature in signatures
        )
        has_candidate_binding = (
            CANDIDATE_RUN_ID.casefold() in folded_text
        )
        if (
            suffix is None
            and relative in tracked_paths
            and has_candidate_binding
            and has_signature
            and _tracked_path_matches_head(repo_root, relative, raw)
        ):
            tracked_control_text_exemptions += 1
            continue
        if (
            (suffix is not None or has_candidate_binding)
            and has_signature
        ):
            matches.append(
                {
                    "absence_type": "candidate_bound_non_json",
                    "match_kind": "repository_text_signature",
                    "path": relative,
                }
            )

    matches.sort(key=canonical_value_bytes)
    snapshot.sort(key=lambda item: item["path"])
    if matches:
        first = matches[0]
        raise AbsenceError(
            "ABSENCE_MATCH",
            f"forbidden pre-A artifact exists: {first['path']} "
            f"({first['match_kind']})",
        )
    return {
        "observed_head": observed_head,
        "scan_snapshot_sha256": sha256_bytes(
            canonical_value_bytes(snapshot)
        ),
        "scanned_file_count": scanned_file_count,
        "tracked_control_text_exemptions": (
            tracked_control_text_exemptions
        ),
    }


def verify(repo_root: Path) -> dict[str, Any]:
    expected_verifier = resolve_repo_file(repo_root, VERIFIER_PATH)
    if Path(__file__).resolve() != expected_verifier:
        raise AbsenceError(
            "VERIFIER_PATH_MISMATCH",
            "running verifier is not the repository-bound verifier",
        )
    contract, rules, contract_sha256 = _load_contract(repo_root)
    scan = _scan_repository(repo_root, rules)
    return {
        "actual_dispatch_performed": False,
        "artifact": CONTRACT_PATH.as_posix(),
        "artifact_sha256": contract_sha256,
        "candidate_run_id": contract["candidate_run_id"],
        "observed_head": scan["observed_head"],
        "repository_wide_byte_reads": True,
        "runner_or_comparator_executed": False,
        "scan_snapshot_sha256": scan["scan_snapshot_sha256"],
        "scanned_file_count": scan["scanned_file_count"],
        "status": "verified_absent",
        "tracked_control_text_exemptions": scan[
            "tracked_control_text_exemptions"
        ],
        "verification_scope": contract["verification_scope"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument(
        "--allow-repository-wide-byte-reads",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if not sys.flags.isolated:
            raise AbsenceError(
                "ISOLATED_INTERPRETER_REQUIRED",
                "invoke this verifier with python -I",
            )
        if not args.allow_repository_wide_byte_reads:
            raise AbsenceError(
                "REPOSITORY_BYTE_READ_ACK_REQUIRED",
                "repository-wide byte reads require explicit acknowledgement",
            )
        repo_root = args.repo_root.resolve()
        if not repo_root.is_dir():
            raise AbsenceError(
                "REPO_ROOT",
                f"repository root is not a directory: {repo_root}",
            )
        result = verify(repo_root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        AbsenceError,
        KeyError,
        OSError,
        subprocess.SubprocessError,
        TypeError,
        ValueError,
    ) as error:
        message = (
            str(error)
            if isinstance(error, AbsenceError)
            else f"VERIFY_INPUT: {error}"
        )
        print(
            json.dumps(
                {
                    "actual_dispatch_performed": False,
                    "error": message,
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
