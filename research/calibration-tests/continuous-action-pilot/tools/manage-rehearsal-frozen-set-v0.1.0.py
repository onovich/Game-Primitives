#!/usr/bin/env python3
"""Prepare and verify a strict two-commit rehearsal freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PILOT = Path("research/calibration-tests/continuous-action-pilot")
RUN_SCHEMA = PILOT / "schema/run-manifest-0.1.0.schema.json"
MARKDOWN_SCHEMA = PILOT / "schema/markdown-document-0.1.0.schema.json"
TEXT_SCHEMA = PILOT / "schema/text-artifact-0.1.0.schema.json"
PREIMAGE_SCHEMA = PILOT / "schema/frozen-set-preimage-0.1.0.schema.json"
REHEARSAL_SCHEMA = PILOT / "schema/rehearsal-input-0.1.1.schema.json"
LOCAL_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
VERSION_IN_FILENAME = re.compile(
    r"(?:^|[-_.])v?([0-9]+\.[0-9]+\.[0-9]+)(?=[-_.]|$)"
)


class FreezeError(RuntimeError):
    """Raised when the rehearsal cannot be frozen safely."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def repo_path(repo_root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(repo_root.resolve()):
        raise FreezeError(f"path escapes repository root: {value}")
    return resolved


def relative(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def parse_json_bytes(
    raw: bytes,
    *,
    source: str,
) -> dict[str, Any]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r\n" in raw:
        raise FreezeError(f"non-canonical UTF-8 JSON: {source}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise FreezeError(f"expected JSON object: {source}")
    return value


def parse_canonical_json_bytes(
    raw: bytes,
    *,
    source: str,
) -> dict[str, Any]:
    value = parse_json_bytes(raw, source=source)
    if raw != canonical_bytes(value):
        raise FreezeError(
            f"JSON is not canonical sorted two-space JSON with final LF: "
            f"{source}"
        )
    return value


def read_json(path: Path) -> dict[str, Any]:
    return parse_canonical_json_bytes(
        path.read_bytes(),
        source=str(path),
    )


def read_schema_json(path: Path) -> dict[str, Any]:
    return parse_json_bytes(
        path.read_bytes(),
        source=str(path),
    )


def git(repo_root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if result.returncode:
        raise FreezeError(
            f"git {' '.join(arguments)} failed: "
            f"{(result.stdout + result.stderr).strip()}"
        )
    return result.stdout


def git_bytes(repo_root: Path, revision: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=repo_root,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise FreezeError(
            f"git show cannot read {revision}:{path}: "
            + result.stderr.decode("utf-8", errors="replace").strip()
        )
    return result.stdout


def schema_path_from_id(schema_id: str) -> Path | None:
    prefix = "https://github.com/onovich/Game-Primitives/blob/main/"
    if not schema_id.startswith(prefix):
        return None
    value = Path(schema_id[len(prefix) :])
    if (
        value.parent != PILOT / "schema"
        or not value.name.endswith(".schema.json")
    ):
        return None
    return value


def artifact_schema(
    run_relative: str,
    artifact_path: Path,
) -> Path:
    if run_relative == "README.md":
        return MARKDOWN_SCHEMA
    if run_relative == "inputs/frozen-set-preimage.tsv":
        return PREIMAGE_SCHEMA
    if run_relative in {
        "inputs/variant-envelope.json",
        "inputs/view-v01.json",
        "inputs/view-v02.json",
    }:
        return REHEARSAL_SCHEMA
    if (
        run_relative.startswith("inputs/protocol/")
        or run_relative.startswith("fixtures/negative/")
        or run_relative.startswith("fixtures/actors/")
        or run_relative == "fixtures/expected-results.json"
        or artifact_path.suffix != ".json"
    ):
        return TEXT_SCHEMA
    value = read_json(artifact_path)
    schema_id = value.get("$schema")
    if isinstance(schema_id, str):
        resolved = schema_path_from_id(schema_id)
        if resolved is not None:
            return resolved
    return TEXT_SCHEMA


def artifact_kind(run_relative: str, artifact_path: Path) -> str:
    if run_relative == "README.md":
        return "documentation"
    if run_relative.startswith("inputs/protocol/"):
        return "source"
    if run_relative.startswith("inputs/audits/"):
        return "audit"
    if run_relative == "inputs/dispatch/actor-dispatch-plan.json":
        return "execution_plan"
    if run_relative.startswith("inputs/dispatch/stage"):
        return "source"
    if ".submission." in artifact_path.name:
        return "submission"
    if artifact_path.suffix == ".json":
        try:
            value = read_json(artifact_path)
        except (FreezeError, json.JSONDecodeError):
            return "fixture"
        artifact_type = value.get("artifact_type")
        if isinstance(artifact_type, str):
            if artifact_type.endswith("_task_packet"):
                return "task_packet"
            if artifact_type == "participant_interface_readiness":
                return "audit"
    return "fixture"


def artifact_version(artifact_path: Path) -> str:
    if artifact_path.suffix == ".json":
        try:
            value = read_json(artifact_path)
        except (FreezeError, json.JSONDecodeError):
            pass
        else:
            version = value.get("artifact_version")
            if isinstance(version, str) and re.fullmatch(
                r"[0-9]+\.[0-9]+\.[0-9]+", version
            ):
                return version
    filename_version = VERSION_IN_FILENAME.search(artifact_path.name)
    if filename_version is not None:
        return filename_version.group(1)
    return "0.1.0"


def audience(run_relative: str) -> list[str]:
    if (
        "condition-v01" in run_relative
        or "response-v01" in run_relative
        or run_relative == "inputs/view-v01.json"
        or run_relative == "inputs/dispatch/stage1-v01.prompt.txt"
    ):
        return ["condition-v01", "custodian", "public_archive"]
    if (
        "condition-v02" in run_relative
        or "response-v02" in run_relative
        or run_relative == "inputs/view-v02.json"
        or run_relative == "inputs/dispatch/stage1-v02.prompt.txt"
    ):
        return ["condition-v02", "custodian", "public_archive"]
    if run_relative in {
        "inputs/prediction-neutral.task.json",
        "inputs/prediction-response.template.json",
        "inputs/variant-envelope.json",
        "inputs/dispatch/stage2-neutral.prompt.txt",
    }:
        return ["all_blind_testers", "custodian", "public_archive"]
    return ["custodian", "public_archive"]


def release_stage(run_relative: str) -> str:
    if (
        run_relative.startswith("fixtures/")
        or run_relative.startswith("inputs/audits/")
        or run_relative.startswith("inputs/protocol/")
    ):
        return "preparation"
    if "prediction" in run_relative or run_relative.endswith(
        "variant-envelope.json"
    ) or run_relative == "inputs/dispatch/stage2-neutral.prompt.txt":
        return "prediction"
    if (
        "reconstruction" in run_relative
        or run_relative.startswith("inputs/view-")
        or run_relative.startswith("inputs/dispatch/stage1-")
    ):
        return "reconstruction"
    return "preparation"


def artifact_id(run_relative: str) -> str:
    value = run_relative.lower()
    value = re.sub(r"[^a-z0-9._-]+", ".", value)
    value = value.strip(".")
    value = re.sub(r"\.(?:json|md|py|tsv|txt)$", "", value)
    identifier = f"rehearsal-006.{value}"
    if not LOCAL_ID.fullmatch(identifier):
        raise FreezeError(f"cannot derive local artifact ID: {run_relative}")
    return identifier


def inventory(run_dir: Path) -> list[Path]:
    paths = [run_dir / "README.md"]
    for directory in ("fixtures", "inputs"):
        root = run_dir / directory
        if root.is_dir():
            paths.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(
        (
            path
            for path in paths
            if path.name != "frozen-set-preimage.tsv"
        ),
        key=lambda path: path.relative_to(run_dir).as_posix(),
    )


def artifact_entry(
    repo_root: Path,
    run_dir: Path,
    artifact_path: Path,
    *,
    included: bool,
) -> dict[str, Any]:
    run_relative = artifact_path.relative_to(run_dir).as_posix()
    schema_path = artifact_schema(run_relative, artifact_path)
    schema = repo_path(repo_root, schema_path)
    return {
        "artifact_id": artifact_id(run_relative),
        "artifact_kind": artifact_kind(run_relative, artifact_path),
        "artifact_version": artifact_version(artifact_path),
        "audience": audience(run_relative),
        "decision_relevant": True,
        "included_in_frozen_set": included,
        "path": run_relative,
        "release_stage": release_stage(run_relative),
        "schema_path": schema_path.as_posix(),
        "schema_sha256": sha256(schema.read_bytes()),
        "sha256": sha256(artifact_path.read_bytes()),
        "supersedes_artifact_id": None,
    }


def validate_manifest(repo_root: Path, manifest: dict[str, Any]) -> None:
    schema = read_schema_json(repo_path(repo_root, RUN_SCHEMA))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(manifest),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        raise FreezeError(
            "manifest failed its Schema: "
            + "; ".join(error.message for error in errors)
        )
    ids = [entry["artifact_id"] for entry in manifest["artifacts"]]
    paths = [entry["path"] for entry in manifest["artifacts"]]
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise FreezeError("manifest contains duplicate artifact IDs or paths")


def preimage_bytes(entries: list[dict[str, Any]]) -> bytes:
    lines = [
        f"{entry['path']}\t{entry['sha256']}\n"
        for entry in entries
        if entry["included_in_frozen_set"]
    ]
    return "".join(sorted(lines)).encode("utf-8")


def prepare_manifest(
    repo_root: Path,
    manifest_path: Path,
    *,
    created_at: str,
    updated_at: str,
    write_preimage: bool,
) -> tuple[dict[str, Any], bytes | None]:
    run_dir = manifest_path.parent
    entries = [
        artifact_entry(
            repo_root,
            run_dir,
            path,
            included=True,
        )
        for path in inventory(run_dir)
    ]
    raw_preimage = preimage_bytes(entries)
    digest = sha256(raw_preimage)
    preimage_path = run_dir / "inputs/frozen-set-preimage.tsv"
    if preimage_path.exists() and not write_preimage:
        raise FreezeError(
            "existing preimage requires --write-preimage"
        )
    if write_preimage:
        preimage_schema = repo_path(repo_root, PREIMAGE_SCHEMA)
        entries.append(
            {
                "artifact_id": artifact_id(
                    "inputs/frozen-set-preimage.tsv"
                ),
                "artifact_kind": "audit",
                "artifact_version": "0.1.0",
                "audience": ["custodian", "public_archive"],
                "decision_relevant": True,
                "included_in_frozen_set": False,
                "path": "inputs/frozen-set-preimage.tsv",
                "release_stage": "preparation",
                "schema_path": PREIMAGE_SCHEMA.as_posix(),
                "schema_sha256": sha256(preimage_schema.read_bytes()),
                "sha256": digest,
                "supersedes_artifact_id": None,
            }
        )
    entries.sort(key=lambda entry: entry["path"])
    existing_created_at = created_at
    if manifest_path.exists():
        existing = read_json(manifest_path)
        if existing.get("status") not in {"preparing", None}:
            raise FreezeError("refusing to replace a non-preparing manifest")
        existing_created_at = existing.get("created_at", created_at)
    manifest = {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "run-manifest-0.1.0.schema.json"
        ),
        "artifact_type": "rehearsal_manifest",
        "artifact_version": "0.1.0",
        "artifacts": entries,
        "created_at": existing_created_at,
        "freeze_commit": None,
        "frozen_artifact_set_digest": digest,
        "protocol_version": "0.1.1",
        "run_id": "rehearsal-006",
        "schema_version": "0.1.0",
        "stage": "preparation",
        "stage_digests": [],
        "status": "preparing",
        "truth_commitment": None,
        "updated_at": updated_at,
    }
    validate_manifest(repo_root, manifest)
    return manifest, raw_preimage if write_preimage else None


def write_preparing(
    manifest_path: Path,
    manifest: dict[str, Any],
    raw_preimage: bytes | None,
) -> None:
    if raw_preimage is not None:
        preimage_path = manifest_path.parent / "inputs/frozen-set-preimage.tsv"
        preimage_path.parent.mkdir(parents=True, exist_ok=True)
        preimage_path.write_bytes(raw_preimage)
    manifest_path.write_bytes(canonical_bytes(manifest))


def verify_manifest_files(
    repo_root: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> None:
    run_dir = manifest_path.parent
    for entry in manifest["artifacts"]:
        artifact = run_dir / entry["path"]
        if sha256(artifact.read_bytes()) != entry["sha256"]:
            raise FreezeError(f"artifact hash differs: {entry['path']}")
        schema = repo_path(repo_root, entry["schema_path"])
        if sha256(schema.read_bytes()) != entry["schema_sha256"]:
            raise FreezeError(
                f"artifact Schema hash differs: {entry['schema_path']}"
            )
    expected = preimage_bytes(manifest["artifacts"])
    if sha256(expected) != manifest["frozen_artifact_set_digest"]:
        raise FreezeError("frozen artifact set digest differs")
    preimage = run_dir / "inputs/frozen-set-preimage.tsv"
    if preimage.read_bytes() != expected:
        raise FreezeError("frozen-set preimage differs")


def command_prepare(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    manifest_path = repo_path(repo_root, args.manifest)
    manifest, raw_preimage = prepare_manifest(
        repo_root,
        manifest_path,
        created_at=args.created_at,
        updated_at=args.updated_at,
        write_preimage=args.write_preimage,
    )
    if args.write:
        write_preparing(manifest_path, manifest, raw_preimage)
    print(
        json.dumps(
            {
                "artifact_count": len(manifest["artifacts"]),
                "frozen_artifact_set_digest": manifest[
                    "frozen_artifact_set_digest"
                ],
                "preimage_written": bool(
                    args.write and args.write_preimage
                ),
                "status": "prepared",
                "written": args.write,
            },
            sort_keys=True,
        )
    )
    return 0


def command_finalize(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    manifest_path = repo_path(repo_root, args.manifest)
    if not COMMIT.fullmatch(args.anchor_commit):
        raise FreezeError("anchor commit must be a full lowercase SHA")
    head = git(repo_root, "rev-parse", "HEAD").strip()
    if head != args.anchor_commit:
        raise FreezeError("anchor commit is not the current HEAD")
    if git(repo_root, "status", "--porcelain").strip():
        raise FreezeError("working tree must be clean before finalization")
    manifest = read_json(manifest_path)
    validate_manifest(repo_root, manifest)
    verify_manifest_files(repo_root, manifest_path, manifest)
    if (
        manifest["status"] != "preparing"
        or manifest["freeze_commit"] is not None
        or manifest["stage_digests"] != []
    ):
        raise FreezeError("manifest is not in the preparing anchor state")
    manifest["freeze_commit"] = args.anchor_commit
    manifest["status"] = "frozen"
    manifest["updated_at"] = args.updated_at
    validate_manifest(repo_root, manifest)
    if args.write:
        manifest_path.write_bytes(canonical_bytes(manifest))
    print(
        json.dumps(
            {
                "freeze_commit": args.anchor_commit,
                "status": "finalized",
                "written": args.write,
            },
            sort_keys=True,
        )
    )
    return 0


def command_verify_a(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    if not COMMIT.fullmatch(args.anchor_commit):
        raise FreezeError("anchor commit must be a full lowercase SHA")
    head = git(repo_root, "rev-parse", "HEAD").strip()
    if head != args.anchor_commit:
        raise FreezeError("anchor commit is not the current HEAD")
    manifest_relative = Path(args.manifest_relative).as_posix()
    manifest = parse_canonical_json_bytes(
        git_bytes(repo_root, args.anchor_commit, manifest_relative),
        source=f"{args.anchor_commit}:{manifest_relative}",
    )
    artifact_count = verify_preparing_commit(
        repo_root,
        args.anchor_commit,
        manifest_relative,
        manifest,
    )
    print(
        json.dumps(
            {
                "anchor_commit": args.anchor_commit,
                "artifact_count": artifact_count,
                "status": "commit_a_verified",
            },
            sort_keys=True,
        )
    )
    return 0


def verify_preparing_commit(
    repo_root: Path,
    anchor_commit: str,
    manifest_relative: str,
    manifest: dict[str, Any],
) -> int:
    validate_manifest(repo_root, manifest)
    if (
        manifest["status"] != "preparing"
        or manifest["freeze_commit"] is not None
        or manifest["stage_digests"] != []
    ):
        raise FreezeError("commit A does not contain a preparing manifest")
    expected = preimage_bytes(manifest["artifacts"])
    if sha256(expected) != manifest["frozen_artifact_set_digest"]:
        raise FreezeError("commit A frozen artifact digest differs")
    run_relative = str(Path(manifest_relative).parent).replace("\\", "/")
    for entry in manifest["artifacts"]:
        artifact_path = f"{run_relative}/{entry['path']}"
        if sha256(
            git_bytes(repo_root, anchor_commit, artifact_path)
        ) != entry["sha256"]:
            raise FreezeError(f"commit A artifact differs: {entry['path']}")
        if sha256(
            git_bytes(
                repo_root,
                anchor_commit,
                entry["schema_path"],
            )
        ) != entry["schema_sha256"]:
            raise FreezeError(
                f"commit A Schema differs: {entry['schema_path']}"
            )
    preimage_path = f"{run_relative}/inputs/frozen-set-preimage.tsv"
    if git_bytes(repo_root, anchor_commit, preimage_path) != expected:
        raise FreezeError("commit A preimage differs")
    return len(manifest["artifacts"])


def command_verify_b(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    for name, value in (
        ("anchor", args.anchor_commit),
        ("finalize", args.finalize_commit),
    ):
        if not COMMIT.fullmatch(value):
            raise FreezeError(f"{name} commit must be a full lowercase SHA")
    parents = git(
        repo_root,
        "rev-list",
        "--parents",
        "-n",
        "1",
        args.finalize_commit,
    ).strip().split()
    if parents != [args.finalize_commit, args.anchor_commit]:
        raise FreezeError("commit B is not a single-parent child of commit A")
    manifest_relative = Path(args.manifest_relative).as_posix()
    changed = [
        line
        for line in git(
            repo_root,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            args.finalize_commit,
        ).splitlines()
        if line
    ]
    if changed != [manifest_relative]:
        raise FreezeError(
            "commit B must modify only the rehearsal manifest"
        )
    before = parse_canonical_json_bytes(
        git_bytes(repo_root, args.anchor_commit, manifest_relative),
        source=f"{args.anchor_commit}:{manifest_relative}",
    )
    verify_preparing_commit(
        repo_root,
        args.anchor_commit,
        manifest_relative,
        before,
    )
    after = parse_canonical_json_bytes(
        git_bytes(repo_root, args.finalize_commit, manifest_relative),
        source=f"{args.finalize_commit}:{manifest_relative}",
    )
    differences = {
        key
        for key in set(before) | set(after)
        if before.get(key) != after.get(key)
    }
    if differences != {"freeze_commit", "status", "updated_at"}:
        raise FreezeError(
            f"commit B changed forbidden manifest fields: {differences}"
        )
    if (
        after["freeze_commit"] != args.anchor_commit
        or after["status"] != "frozen"
        or after["stage_digests"] != []
    ):
        raise FreezeError("commit B freeze fields are invalid")
    validate_manifest(repo_root, after)
    if (
        sha256(preimage_bytes(after["artifacts"]))
        != after["frozen_artifact_set_digest"]
    ):
        raise FreezeError("commit B frozen artifact digest differs")
    print(
        json.dumps(
            {
                "anchor_commit": args.anchor_commit,
                "finalize_commit": args.finalize_commit,
                "status": "commit_b_verified",
            },
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    subcommands = value.add_subparsers(dest="command", required=True)
    prepare = subcommands.add_parser("prepare-manifest")
    prepare.add_argument("--repo-root", required=True, type=Path)
    prepare.add_argument("--manifest", required=True, type=Path)
    prepare.add_argument("--created-at", required=True)
    prepare.add_argument("--updated-at", required=True)
    prepare.add_argument("--write", action="store_true")
    prepare.add_argument("--write-preimage", action="store_true")
    prepare.set_defaults(func=command_prepare)
    finalize = subcommands.add_parser("finalize-manifest")
    finalize.add_argument("--repo-root", required=True, type=Path)
    finalize.add_argument("--manifest", required=True, type=Path)
    finalize.add_argument("--anchor-commit", required=True)
    finalize.add_argument("--updated-at", required=True)
    finalize.add_argument("--write", action="store_true")
    finalize.set_defaults(func=command_finalize)
    verify_a = subcommands.add_parser("verify-commit-a")
    verify_a.add_argument("--repo-root", required=True, type=Path)
    verify_a.add_argument("--manifest-relative", required=True)
    verify_a.add_argument("--anchor-commit", required=True)
    verify_a.set_defaults(func=command_verify_a)
    verify_b = subcommands.add_parser("verify-commit-b")
    verify_b.add_argument("--repo-root", required=True, type=Path)
    verify_b.add_argument("--manifest-relative", required=True)
    verify_b.add_argument("--anchor-commit", required=True)
    verify_b.add_argument("--finalize-commit", required=True)
    verify_b.set_defaults(func=command_verify_b)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (
        FreezeError,
        json.JSONDecodeError,
        OSError,
        subprocess.SubprocessError,
    ) as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "status": "failed_closed",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
