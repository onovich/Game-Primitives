#!/usr/bin/env python3
"""Refresh the explicit continuous-001 preparing-manifest allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


BASE = Path("research/calibration-tests/continuous-action-pilot")
RUN = BASE / "runs/continuous-001"
SCHEMA = BASE / "schema"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def repo_path(repo_root: Path, value: str | Path) -> Path:
    path = (repo_root / value).resolve()
    if not path.is_relative_to(repo_root):
        raise ValueError(f"path escapes repository root: {value}")
    return path


def artifact_spec(
    artifact_id: str,
    path: str,
    artifact_kind: str,
    schema_name: str,
    audience: list[str],
    release_stage: str,
    artifact_version: str = "0.1.0",
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "artifact_kind": artifact_kind,
        "artifact_version": artifact_version,
        "audience": audience,
        "decision_relevant": True,
        "included_in_frozen_set": False,
        "path": path,
        "release_stage": release_stage,
        "schema_path": (SCHEMA / schema_name).as_posix(),
        "supersedes_artifact_id": None,
    }


ADDITIONS = [
    artifact_spec(
        "actor-plan.continuous-001",
        "inputs/actor-plan.md",
        "actor_descriptor",
        "markdown-document-0.1.0.schema.json",
        ["custodian", "public_after_reveal"],
        "preparation",
    ),
    artifact_spec(
        "generator.stage2-envelope-v0.1.0",
        "inputs/generate-stage2-envelope-v0.1.0.py",
        "generator",
        "text-artifact-0.1.0.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "prediction",
    ),
    artifact_spec(
        "generator.stage2-task-v0.1.0",
        "inputs/generate-stage2-prediction-task-v0.1.0.py",
        "generator",
        "text-artifact-0.1.0.schema.json",
        ["custodian", "public_after_reveal", "source_auditor"],
        "prediction",
    ),
    artifact_spec(
        "template.reconstruction-response-v0.1.0",
        "inputs/reconstruction-response.template.json",
        "fixture",
        "response-template-0.1.0.schema.json",
        ["all_blind_testers", "custodian", "public_after_reveal"],
        "reconstruction",
    ),
    artifact_spec(
        "template.prediction-response-v0.1.0",
        "inputs/prediction-response.template.json",
        "fixture",
        "response-template-0.1.0.schema.json",
        ["all_blind_testers", "custodian", "public_after_reveal"],
        "prediction",
    ),
    artifact_spec(
        "task.reconstruction.condition-v01",
        "inputs/stage1-condition-v01.task.json",
        "task_packet",
        "task-packet-0.1.2.schema.json",
        ["condition-v01", "custodian", "public_after_reveal"],
        "reconstruction",
        "0.1.2",
    ),
    artifact_spec(
        "task.reconstruction.condition-v02",
        "inputs/stage1-condition-v02.task.json",
        "task_packet",
        "task-packet-0.1.2.schema.json",
        ["condition-v02", "custodian", "public_after_reveal"],
        "reconstruction",
        "0.1.2",
    ),
    artifact_spec(
        "task.prediction.continuous-001",
        "inputs/stage2-prediction.task.json",
        "task_packet",
        "task-packet-0.1.2.schema.json",
        ["all_blind_testers", "custodian", "public_after_reveal"],
        "prediction",
        "0.1.2",
    ),
    artifact_spec(
        "envelope.variant.stage2-v0.1.0",
        "inputs/stage2-variant-envelope.json",
        "fixture",
        "variant-envelope-0.1.0.schema.json",
        ["all_blind_testers", "custodian", "public_after_reveal"],
        "prediction",
    ),
]

for stage, schema_name, release_stage in (
    (
        "stage1",
        "stage1-seat-dispatch-envelope-0.1.0.schema.json",
        "reconstruction",
    ),
    (
        "stage2",
        "stage2-seat-dispatch-envelope-0.1.0.schema.json",
        "prediction",
    ),
):
    for seat in ("p01", "p02", "p03", "p04"):
        ADDITIONS.append(
            artifact_spec(
                f"dispatch-template.{stage}.{seat}",
                f"inputs/{stage}-dispatch-{seat}.template.json",
                "submission_envelope",
                schema_name,
                ["custodian", "public_after_reveal"],
                release_stage,
            )
        )

COMMON_FORMAL_AUDIENCE = [
    "custodian",
    "public_after_reveal",
    "source_auditor",
]

ADDITIONS.extend(
    [
        artifact_spec(
            "build.r1.formal-preparation-v0.1.0",
            "fixtures/r1/footsies-r1-formal-preparation-v0.1.0.md",
            "build_record",
            "markdown-document-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.observation-source-v0.1.0",
            "fixtures/r1/footsies-r1-observation-v0.1.0.cs",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.observation-meta-v0.1.0",
            "fixtures/r1/footsies-r1-observation-v0.1.0.cs.meta",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.variant-patch-v0.1.0",
            "fixtures/r1/footsies-r1-whiff-cancel-v0.1.0.patch",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r1.formal-input-v0.1.0",
            "fixtures/r1/footsies-r1-formal-input-v0.1.0.json",
            "fixture",
            "formal-input-trace-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r1.formal-runner-v0.1.0",
            "fixtures/r1/run-footsies-r1-formal-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r1.formal-comparator-v0.1.0",
            "fixtures/r1/compare-footsies-r1-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "build.r2.formal-preparation-v0.1.0",
            "fixtures/r2/q3-formal-fixture-preparation-v0.1.0.md",
            "build_record",
            "markdown-document-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.compatibility-source-v0.1.0",
            "fixtures/r2/q3-formal-compatibility-v0.1.0.c",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.harness-header-v0.1.0",
            "fixtures/r2/q3-formal-fixture-v0.1.0.h",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.harness-source-v0.1.0",
            "fixtures/r2/q3-formal-harness-v0.1.0.c",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.compatibility-patch-v0.1.0",
            "fixtures/r2/q3-msvc-x64-compatibility-v0.1.0.patch",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.observation-patch-v0.1.0",
            "fixtures/r2/q3-observation-v0.1.0.patch",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.variant-patch-v0.1.0",
            "fixtures/r2/q3-entry-latch-variant-v0.1.0.patch",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r2.formal-input-v0.1.0",
            "fixtures/r2/r2-formal-input-v0.1.0.json",
            "fixture",
            "formal-input-trace-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r2.build-runner-v0.1.0",
            "fixtures/r2/build-q3-formal-fixture-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r2.formal-runner-v0.1.0",
            "fixtures/r2/run-q3-formal-guarded-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r2.formal-comparator-v0.1.0",
            "fixtures/r2/compare-q3-formal-traces-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.spec-v0.1.0",
            "fixtures/r3/r3-fixture-spec-v0.1.0.json",
            "fixture",
            "r3-fixture-spec-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "build.r3.formal-evidence-v0.1.0",
            "fixtures/r3/r3-build-list-evidence-v0.1.0.json",
            "build_record",
            "r3-build-list-evidence-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.dependency-lock-set-v0.1.0",
            "fixtures/r3/dependency-lock-set-v0.1.0.json",
            "fixture",
            "dependency-lock-set-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.observation-source-v0.1.0",
            "fixtures/r3/TestSceneGamePrimitivesR3.cs",
            "fixture",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "fixture.r3.formal-input-v0.1.0",
            "fixtures/r3/formal-input-r3-v0.1.0.json",
            "fixture",
            "formal-input-trace-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r3.build-list-runner-v0.1.0",
            "fixtures/r3/run-osu-r3-build-list-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r3.formal-runner-v0.1.0",
            "fixtures/r3/run-osu-r3-formal-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
        artifact_spec(
            "generator.r3.formal-comparator-v0.1.0",
            "fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1",
            "generator",
            "text-artifact-0.1.0.schema.json",
            COMMON_FORMAL_AUDIENCE,
            "preparation",
        ),
    ]
)


def load_registry(
    repo_root: Path,
) -> tuple[Registry, dict[str, dict[str, Any]]]:
    registry = Registry()
    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(repo_path(repo_root, SCHEMA).glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        schemas[schema["$id"]] = schema
        registry = registry.with_resource(
            schema["$id"],
            Resource.from_contents(schema),
        )
    return registry, schemas


def refresh_entry(
    repo_root: Path,
    run_dir: Path,
    entry: dict[str, Any],
) -> dict[str, Any]:
    result = dict(entry)
    artifact_path = repo_path(run_dir, result["path"])
    schema_path = repo_path(repo_root, result["schema_path"])
    if not artifact_path.is_file():
        raise FileNotFoundError(f"manifest artifact is missing: {artifact_path}")
    if not schema_path.is_file():
        raise FileNotFoundError(f"manifest schema is missing: {schema_path}")
    if artifact_path.suffix.lower() == ".json":
        document = json.loads(artifact_path.read_text(encoding="utf-8"))
        declared_version = document.get("artifact_version")
        if isinstance(declared_version, str):
            result["artifact_version"] = declared_version
    result["sha256"] = sha256(artifact_path)
    result["schema_sha256"] = sha256(schema_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument(
        "--manifest",
        default=(RUN / "manifest.json").as_posix(),
    )
    parser.add_argument("--updated-at", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    manifest_path = repo_path(repo_root, args.manifest)
    run_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("status") != "preparing"
        or manifest.get("freeze_commit") is not None
        or manifest.get("frozen_artifact_set_digest") is not None
        or manifest.get("stage_digests") != []
    ):
        raise ValueError("refusing to refresh a non-preparing or partially frozen manifest")

    entries = {
        entry["path"]: dict(entry)
        for entry in manifest["artifacts"]
    }
    if len(entries) != len(manifest["artifacts"]):
        raise ValueError("manifest contains duplicate artifact paths")

    source_task_schema = (
        SCHEMA / "task-packet-0.1.2.schema.json"
    ).as_posix()
    for path in (
        "inputs/source-encoding-packet.json",
        "inputs/source-audit-packet.json",
    ):
        entries[path]["artifact_version"] = "0.1.2"
        entries[path]["schema_path"] = source_task_schema

    for addition in ADDITIONS:
        existing = entries.get(addition["path"])
        if existing is not None and any(
            existing.get(key) != value
            for key, value in addition.items()
        ):
            raise ValueError(
                f"allowlisted addition conflicts with existing entry: {addition['path']}"
            )
        entries[addition["path"]] = addition

    original_paths = [entry["path"] for entry in manifest["artifacts"]]
    added_paths = [
        entry["path"]
        for entry in ADDITIONS
        if entry["path"] not in original_paths
    ]
    ordered_paths = original_paths + added_paths
    manifest["artifacts"] = [
        refresh_entry(repo_root, run_dir, entries[path])
        for path in ordered_paths
    ]
    manifest["updated_at"] = args.updated_at

    registry, schemas = load_registry(repo_root)
    schema = schemas[manifest["$schema"]]
    errors = sorted(
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(manifest),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        details = "\n".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: "
            f"{error.message}"
            for error in errors[:12]
        )
        raise ValueError(f"refreshed manifest does not validate:\n{details}")

    output = canonical_bytes(manifest)
    if args.write:
        manifest_path.write_bytes(output)
    print(
        json.dumps(
            {
                "artifact_count": len(manifest["artifacts"]),
                "manifest_sha256": hashlib.sha256(output).hexdigest(),
                "status": "written" if args.write else "preview",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
