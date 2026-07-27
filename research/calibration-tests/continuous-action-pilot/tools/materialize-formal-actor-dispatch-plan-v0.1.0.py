#!/usr/bin/env python3
"""Preview or materialize the inert continuous-002 actor-dispatch plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from formal_actor_dispatch_plan_contract import (
    DispatchPlanError,
    PLAN_PATH,
    assert_runtime_artifact_binding,
    expected_outputs,
    sha256_bytes,
    write_outputs_exclusive,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preview", "materialize"):
        command = commands.add_parser(name)
        command.add_argument("--repo-root", required=True, type=Path)
        command.add_argument("--created-at", required=True)
        if name == "materialize":
            command.add_argument("--write", action="store_true")
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
            "materializer",
            Path(__file__),
        )
        outputs = expected_outputs(
            repo_root,
            created_at=args.created_at,
        )
        plan_raw = outputs[PLAN_PATH.as_posix()]
        if args.command == "preview":
            status = "previewed_inert"
        else:
            if not args.write:
                raise DispatchPlanError(
                    "WRITE_FLAG_REQUIRED",
                    "materialize requires the explicit --write flag",
                )
            write_outputs_exclusive(repo_root, outputs)
            status = "materialized_inert"
        print(
            json.dumps(
                {
                    "actual_actor_created": False,
                    "actual_dispatch_performed": False,
                    "actual_receipt_created": False,
                    "actual_session_created": False,
                    "actual_thread_created": False,
                    "artifact_count": len(outputs),
                    "plan_path": PLAN_PATH.as_posix(),
                    "plan_sha256": sha256_bytes(plan_raw),
                    "runner_or_comparator_executed": False,
                    "status": status,
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
            else f"MATERIALIZE_INPUT: {error}"
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
