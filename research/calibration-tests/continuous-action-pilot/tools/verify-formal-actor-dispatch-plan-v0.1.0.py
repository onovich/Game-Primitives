#!/usr/bin/env python3
"""Read-only verifier for formal-actor-dispatch-plan 0.1.0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from formal_actor_dispatch_plan_contract import (
    DispatchPlanError,
    PLAN_PATH,
    assert_runtime_artifact_binding,
    sha256_bytes,
    verify_plan,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--repo-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        repo_root = args.repo_root.resolve()
        if not repo_root.is_dir():
            raise DispatchPlanError(
                "REPO_ROOT",
                f"repository root is not a directory: {repo_root}",
            )
        assert_runtime_artifact_binding(
            repo_root,
            "verifier",
            Path(__file__),
        )
        plan, raw = verify_plan(repo_root)
        print(
            json.dumps(
                {
                    "actual_actor_created": False,
                    "actual_dispatch_performed": False,
                    "actual_runtime_compliance_verified": plan[
                        "capability_boundary"
                    ]["actual_runtime_compliance_verified"],
                    "artifact": PLAN_PATH.as_posix(),
                    "capability_boundary": (
                        "static_pre_gate_plan_only_fail_closed_until_attested"
                    ),
                    "prompt_count": sum(
                        2 for _seat in plan["seats"]
                    ),
                    "runner_or_comparator_executed": False,
                    "seat_count": len(plan["seats"]),
                    "sha256": sha256_bytes(raw),
                    "status": "verified_inert",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (DispatchPlanError, KeyError, OSError, TypeError, ValueError) as error:
        message = (
            str(error)
            if isinstance(error, DispatchPlanError)
            else f"VERIFY_INPUT: {error}"
        )
        print(
            json.dumps(
                {
                    "actual_dispatch_performed": False,
                    "error": message,
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
