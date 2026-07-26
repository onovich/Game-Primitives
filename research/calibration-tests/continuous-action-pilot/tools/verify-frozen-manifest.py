#!/usr/bin/env python3
"""Verify one continuous-action rehearsal manifest without modifying it."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--preimage", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest.resolve()
    run_dir = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    failures: list[dict[str, str]] = []
    frozen_lines: list[str] = []

    for entry in manifest["artifacts"]:
        artifact_path = run_dir / entry["path"]
        actual_artifact_hash = sha256(artifact_path.read_bytes())
        if actual_artifact_hash != entry["sha256"]:
            failures.append(
                {
                    "kind": "artifact_sha256",
                    "path": entry["path"],
                    "expected": entry["sha256"],
                    "actual": actual_artifact_hash,
                }
            )

        schema_path = repo_root / entry["schema_path"]
        actual_schema_hash = sha256(schema_path.read_bytes())
        if actual_schema_hash != entry["schema_sha256"]:
            failures.append(
                {
                    "kind": "schema_sha256",
                    "path": entry["schema_path"],
                    "expected": entry["schema_sha256"],
                    "actual": actual_schema_hash,
                }
            )

        if entry["included_in_frozen_set"]:
            frozen_lines.append(f"{entry['path']}\t{entry['sha256']}\n")

    preimage_bytes = "".join(sorted(frozen_lines)).encode("utf-8")
    actual_digest = sha256(preimage_bytes)
    expected_digest = manifest["frozen_artifact_set_digest"]

    if actual_digest != expected_digest:
        failures.append(
            {
                "kind": "frozen_artifact_set_digest",
                "path": str(manifest_path),
                "expected": expected_digest,
                "actual": actual_digest,
            }
        )

    if args.preimage is not None:
        actual_preimage = args.preimage.resolve().read_bytes()
        if actual_preimage != preimage_bytes:
            failures.append(
                {
                    "kind": "frozen_set_preimage",
                    "path": str(args.preimage),
                    "expected": sha256(preimage_bytes),
                    "actual": sha256(actual_preimage),
                }
            )

    result = {
        "artifact_count": len(manifest["artifacts"]),
        "frozen_artifact_count": len(frozen_lines),
        "frozen_artifact_set_digest": actual_digest,
        "manifest": str(manifest_path),
        "status": "failed" if failures else "passed",
        "failures": failures,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
