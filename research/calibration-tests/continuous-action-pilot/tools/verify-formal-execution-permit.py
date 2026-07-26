#!/usr/bin/env python3
"""Stable verify-only entry point for the continuous-001 execution permit."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

MATERIALIZER_NAME = "materialize-execution-permit.py"


def load_materializer() -> Any:
    path = Path(__file__).resolve().with_name(MATERIALIZER_NAME)
    spec = importlib.util.spec_from_file_location(
        "continuous_action_execution_permit_materializer",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bound permit materializer: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "verify":
        arguments = arguments[1:]
    materializer = load_materializer()
    return materializer.run_cli(["verify", *arguments])


if __name__ == "__main__":
    raise SystemExit(main())
