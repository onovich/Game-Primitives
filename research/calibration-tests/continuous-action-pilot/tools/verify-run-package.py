#!/usr/bin/env python3
"""Verify one continuous-action formal run package without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(
    failures: list[dict[str, Any]],
    kind: str,
    path: str,
    expected: Any,
    actual: Any,
) -> None:
    failures.append(
        {
            "actual": actual,
            "expected": expected,
            "kind": kind,
            "path": path,
        }
    )


def resolve_within(base: Path, relative_path: str) -> Path:
    candidate = (base / relative_path).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError(f"path escapes allowed root: {relative_path}")
    return candidate


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_bytes(data: bytes) -> Any:
    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def load_schema_registry(
    schema_dir: Path,
) -> tuple[Registry, dict[str, dict[str, Any]], list[dict[str, Any]]]:
    registry = Registry()
    schemas_by_id: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []

    for path in sorted(schema_dir.glob("*.schema.json")):
        relative = path.as_posix()
        try:
            schema = parse_json_bytes(path.read_bytes())
            Draft202012Validator.check_schema(schema)
            schema_id = schema.get("$id")
            if not isinstance(schema_id, str):
                fail(failures, "schema_id", relative, "string $id", schema_id)
                continue
            if schema_id in schemas_by_id:
                fail(failures, "schema_id_unique", relative, "unique $id", schema_id)
                continue
            schemas_by_id[schema_id] = schema
            registry = registry.with_resource(
                schema_id,
                Resource.from_contents(schema),
            )
        except Exception as exc:  # noqa: BLE001 - verifier must report all failures.
            fail(failures, "schema_load", relative, "valid Draft 2020-12 schema", str(exc))

    return registry, schemas_by_id, failures


def iter_file_references(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        if (
            isinstance(value.get("path"), str)
            and isinstance(value.get("sha256"), str)
        ):
            yield value
        for child in value.values():
            yield from iter_file_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_file_references(child)


def validate_schema_instance(
    *,
    instance: Any,
    schema: dict[str, Any],
    registry: Registry,
    display_path: str,
    failures: list[dict[str, Any]],
) -> None:
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path)):
        instance_path = "/".join(str(part) for part in error.path)
        suffix = f"#{instance_path}" if instance_path else ""
        fail(
            failures,
            "schema_validation",
            f"{display_path}{suffix}",
            "instance accepted by declared schema",
            error.message,
        )


def validate_file_bytes(
    *,
    path: Path,
    display_path: str,
    schema: dict[str, Any],
    registry: Registry,
    failures: list[dict[str, Any]],
) -> Any | None:
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        fail(failures, "utf8_bom", display_path, "UTF-8 without BOM", "BOM present")
    if b"\r" in data:
        fail(failures, "line_endings", display_path, "LF only", "CR byte present")
    if not data.endswith(b"\n"):
        fail(failures, "final_newline", display_path, "one final LF", "missing final LF")
    elif data.endswith(b"\n\n"):
        fail(failures, "final_newline", display_path, "one final LF", "multiple final LFs")

    if path.suffix.lower() == ".json":
        try:
            instance = parse_json_bytes(data)
        except Exception as exc:  # noqa: BLE001
            fail(failures, "json_parse", display_path, "valid UTF-8 JSON", str(exc))
            return None
        if canonical_json_bytes(instance) != data:
            fail(
                failures,
                "canonical_json",
                display_path,
                "sorted keys, two-space indent, UTF-8, one final LF",
                "byte mismatch",
            )
        declared_schema = instance.get("$schema") if isinstance(instance, dict) else None
        if declared_schema != schema.get("$id"):
            fail(
                failures,
                "declared_schema",
                display_path,
                schema.get("$id"),
                declared_schema,
            )
    else:
        try:
            instance = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            fail(failures, "utf8_decode", display_path, "valid UTF-8", str(exc))
            return None

    validate_schema_instance(
        instance=instance,
        schema=schema,
        registry=registry,
        display_path=display_path,
        failures=failures,
    )
    return instance


def verify_task_packet(
    *,
    task: dict[str, Any],
    repo_root: Path,
    display_path: str,
    failures: list[dict[str, Any]],
) -> None:
    input_hashes: set[str] = set()
    for reference in task["input_artifacts"]:
        try:
            path = resolve_within(repo_root, reference["path"])
        except ValueError as exc:
            fail(failures, "task_input_path", display_path, "path inside repo", str(exc))
            continue
        if not path.is_file():
            fail(failures, "task_input_exists", reference["path"], True, False)
            continue
        actual = sha256(path.read_bytes())
        input_hashes.add(actual)
        if actual != reference["sha256"]:
            fail(
                failures,
                "task_input_sha256",
                reference["path"],
                reference["sha256"],
                actual,
            )

    for field_name in ("target_encoding_sha256", "target_view_sha256"):
        target = task[field_name]
        if target is not None and target not in input_hashes:
            fail(
                failures,
                field_name,
                display_path,
                "one of the exact task input hashes",
                target,
            )

    for field_name in ("output_schema", "assembled_output_schema"):
        reference = task[field_name]
        if reference is None:
            continue
        try:
            path = resolve_within(repo_root, reference["path"])
        except ValueError as exc:
            fail(
                failures,
                f"task_{field_name}_path",
                display_path,
                "path inside repo",
                str(exc),
            )
            continue
        if not path.is_file():
            fail(failures, f"task_{field_name}_exists", reference["path"], True, False)
            continue
        actual = sha256(path.read_bytes())
        if actual != reference["sha256"]:
            fail(
                failures,
                f"task_{field_name}_sha256",
                reference["path"],
                reference["sha256"],
                actual,
            )


def verify_nested_references(
    *,
    instance: Any,
    repo_root: Path,
    display_path: str,
    failures: list[dict[str, Any]],
) -> None:
    seen: set[tuple[str, str]] = set()
    for reference in iter_file_references(instance):
        key = (reference["path"], reference["sha256"])
        if key in seen:
            continue
        seen.add(key)
        try:
            path = resolve_within(repo_root, reference["path"])
        except ValueError as exc:
            fail(
                failures,
                "artifact_reference_path",
                display_path,
                "repo-relative path inside repository",
                str(exc),
            )
            continue
        if not path.is_file():
            fail(failures, "artifact_reference_exists", reference["path"], True, False)
            continue
        actual = sha256(path.read_bytes())
        if actual != reference["sha256"]:
            fail(
                failures,
                "artifact_reference_sha256",
                reference["path"],
                reference["sha256"],
                actual,
            )


def git_file_bytes(repo_root: Path, commit: str, repo_relative_path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{repo_relative_path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--require-frozen", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest.resolve()
    run_dir = manifest_path.parent
    schema_dir = repo_root / "research/calibration-tests/continuous-action-pilot/schema"
    failures: list[dict[str, Any]] = []

    if not manifest_path.is_relative_to(repo_root):
        raise SystemExit("manifest must be inside repo root")
    if not manifest_path.is_file():
        raise SystemExit(f"manifest does not exist: {manifest_path}")

    registry, schemas_by_id, schema_failures = load_schema_registry(schema_dir)
    failures.extend(schema_failures)

    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = parse_json_bytes(manifest_bytes)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"cannot parse manifest: {exc}") from exc

    manifest_schema_id = manifest.get("$schema")
    manifest_schema = schemas_by_id.get(manifest_schema_id)
    if manifest_schema is None:
        fail(
            failures,
            "manifest_schema",
            manifest_path.as_posix(),
            "locally registered schema",
            manifest_schema_id,
        )
    else:
        validate_file_bytes(
            path=manifest_path,
            display_path=manifest_path.relative_to(repo_root).as_posix(),
            schema=manifest_schema,
            registry=registry,
            failures=failures,
        )

    artifact_ids: set[str] = set()
    artifact_paths: set[str] = set()
    frozen_lines: list[str] = []

    for entry in manifest.get("artifacts", []):
        artifact_id = entry["artifact_id"]
        relative_path = entry["path"]
        if artifact_id in artifact_ids:
            fail(failures, "artifact_id_unique", relative_path, "unique id", artifact_id)
        artifact_ids.add(artifact_id)
        if relative_path in artifact_paths:
            fail(failures, "artifact_path_unique", relative_path, "unique path", relative_path)
        artifact_paths.add(relative_path)

        try:
            artifact_path = resolve_within(run_dir, relative_path)
            schema_path = resolve_within(repo_root, entry["schema_path"])
        except ValueError as exc:
            fail(failures, "manifest_entry_path", relative_path, "safe path", str(exc))
            continue

        if not artifact_path.is_file():
            fail(failures, "artifact_exists", relative_path, True, False)
            continue
        actual_artifact_hash = sha256(artifact_path.read_bytes())
        if actual_artifact_hash != entry["sha256"]:
            fail(
                failures,
                "artifact_sha256",
                relative_path,
                entry["sha256"],
                actual_artifact_hash,
            )

        if not schema_path.is_file():
            fail(failures, "artifact_schema_exists", entry["schema_path"], True, False)
            continue
        actual_schema_hash = sha256(schema_path.read_bytes())
        if actual_schema_hash != entry["schema_sha256"]:
            fail(
                failures,
                "artifact_schema_sha256",
                entry["schema_path"],
                entry["schema_sha256"],
                actual_schema_hash,
            )

        try:
            schema = parse_json_bytes(schema_path.read_bytes())
            instance = validate_file_bytes(
                path=artifact_path,
                display_path=artifact_path.relative_to(repo_root).as_posix(),
                schema=schema,
                registry=registry,
                failures=failures,
            )
            if isinstance(instance, dict):
                verify_nested_references(
                    instance=instance,
                    repo_root=repo_root,
                    display_path=relative_path,
                    failures=failures,
                )
                if entry["artifact_kind"] == "task_packet":
                    verify_task_packet(
                        task=instance,
                        repo_root=repo_root,
                        display_path=relative_path,
                        failures=failures,
                    )
        except Exception as exc:  # noqa: BLE001
            fail(
                failures,
                "artifact_validation",
                relative_path,
                "valid artifact and resolvable schema",
                str(exc),
            )

        if entry["included_in_frozen_set"]:
            frozen_lines.append(f"{relative_path}\t{entry['sha256']}\n")

    frozen_preimage = "".join(sorted(frozen_lines)).encode("utf-8")
    actual_frozen_digest = sha256(frozen_preimage)
    expected_frozen_digest = manifest.get("frozen_artifact_set_digest")
    if expected_frozen_digest is not None and expected_frozen_digest != actual_frozen_digest:
        fail(
            failures,
            "frozen_artifact_set_digest",
            manifest_path.relative_to(repo_root).as_posix(),
            expected_frozen_digest,
            actual_frozen_digest,
        )

    status = manifest.get("status")
    freeze_commit = manifest.get("freeze_commit")
    if status == "frozen":
        if expected_frozen_digest is None:
            fail(failures, "frozen_digest_required", "manifest.json", "sha256", None)
        if not frozen_lines:
            fail(failures, "frozen_set_nonempty", "manifest.json", "at least one artifact", 0)
        if not isinstance(freeze_commit, str):
            fail(failures, "freeze_commit_required", "manifest.json", "40-char Git SHA", freeze_commit)
        else:
            for entry in manifest["artifacts"]:
                if not entry["included_in_frozen_set"]:
                    continue
                repo_relative = (
                    run_dir / entry["path"]
                ).relative_to(repo_root).as_posix()
                anchored = git_file_bytes(repo_root, freeze_commit, repo_relative)
                if anchored is None:
                    fail(
                        failures,
                        "freeze_anchor_path",
                        repo_relative,
                        f"file present at {freeze_commit}",
                        "missing",
                    )
                elif sha256(anchored) != entry["sha256"]:
                    fail(
                        failures,
                        "freeze_anchor_sha256",
                        repo_relative,
                        entry["sha256"],
                        sha256(anchored),
                    )

    if args.require_frozen and status != "frozen":
        fail(failures, "require_frozen", "manifest.json", "frozen", status)

    result = {
        "artifact_count": len(manifest.get("artifacts", [])),
        "failure_count": len(failures),
        "failures": failures,
        "freeze_commit": freeze_commit,
        "frozen_artifact_count": len(frozen_lines),
        "frozen_artifact_set_digest": (
            actual_frozen_digest if frozen_lines else None
        ),
        "manifest": manifest_path.relative_to(repo_root).as_posix(),
        "package_status": status,
        "schema_count": len(schemas_by_id),
        "status": "failed" if failures else "passed",
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
