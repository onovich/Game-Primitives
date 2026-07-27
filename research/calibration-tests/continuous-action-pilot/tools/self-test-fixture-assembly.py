#!/usr/bin/env python3
"""Run the isolated synthetic self-test for fixture assembly."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[4]
    materializer = Path(__file__).with_name("materialize-fixture-assembly.py")
    completed = subprocess.run(
        [
            sys.executable,
            str(materializer),
            "self-test",
            "--repo-root",
            str(repo_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        sys.stderr.write(completed.stdout)
        return completed.returncode
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"materializer self-test did not emit JSON: {error}") from error
    expected = {
        "build_attempt_id_negative_control_passed": True,
        "formal_input_executed": False,
        "formal_outputs_created_in_repository": False,
        "missing_build_runner_negative_control_passed": True,
        "missing_r1_negative_control_passed": True,
        "missing_runner_negative_control_passed": True,
        "missing_support_negative_control_passed": True,
        "missing_test_body_negative_control_passed": True,
        "output_sha256_negative_control_passed": True,
        "status": "synthetic_self_test_passed",
    }
    for key, value in expected.items():
        if report.get(key) != value:
            raise SystemExit(
                f"unexpected self-test field {key}: "
                f"expected {value!r}, got {report.get(key)!r}"
            )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
