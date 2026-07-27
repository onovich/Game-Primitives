#!/usr/bin/env python3
"""Read-only verification for formal-run-delta 0.1.0."""

from __future__ import annotations

import sys

if not sys.flags.isolated:
    sys.stderr.write(
        '{"error":"PYTHON_ISOLATION_REQUIRED: invoke this externally pinned '
        'entry point with python -I","status":"failed_closed"}\n'
    )
    raise SystemExit(1)

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType


PILOT = Path("research/calibration-tests/continuous-action-pilot")
CORE_RELATIVE = PILOT / "tools/formal_run_delta_contract.py"
WRAPPER_RELATIVE = PILOT / "tools/verify-formal-run-delta-v0.1.0.py"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class BootstrapError(RuntimeError):
    """A stable failure raised before the pinned contract core is imported."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _resolve_exact_repo_file(repo_root: Path, relative: Path) -> Path:
    if relative.is_absolute() or not relative.parts:
        raise BootstrapError(
            "RUNTIME_PATH_INVALID",
            f"runtime path must be repository-relative: {relative}",
        )
    current = repo_root
    for part in relative.parts:
        if part in ("", ".", ".."):
            raise BootstrapError(
                "RUNTIME_PATH_INVALID",
                f"runtime path contains a forbidden component: {relative}",
            )
        if not current.is_dir():
            raise BootstrapError(
                "RUNTIME_PATH_MISSING",
                f"runtime parent is not a directory: {current}",
            )
        matches = [
            child
            for child in current.iterdir()
            if child.name.casefold() == part.casefold()
        ]
        if len(matches) != 1 or matches[0].name != part:
            raise BootstrapError(
                "RUNTIME_PATH_CASE",
                f"runtime path is missing or has non-canonical case: {relative}",
            )
        current = matches[0]
        if current.is_symlink():
            raise BootstrapError(
                "RUNTIME_PATH_SYMLINK",
                f"runtime path must not traverse a symlink: {relative}",
            )
    resolved = current.resolve(strict=True)
    try:
        resolved.relative_to(repo_root)
    except ValueError as error:
        raise BootstrapError(
            "RUNTIME_PATH_ESCAPE",
            f"runtime path escapes repository root: {relative}",
        ) from error
    if not resolved.is_file():
        raise BootstrapError(
            "RUNTIME_PATH_NOT_FILE",
            f"runtime path is not a file: {relative}",
        )
    return resolved


def _assert_wrapper_binding(repo_root: Path) -> None:
    expected = _resolve_exact_repo_file(repo_root, WRAPPER_RELATIVE)
    runtime_lexical = Path(__file__).absolute()
    try:
        runtime_relative = runtime_lexical.relative_to(repo_root)
    except ValueError as error:
        raise BootstrapError(
            "RUNTIME_WRAPPER_BINDING",
            "the executing wrapper is outside the declared repository root",
        ) from error
    if runtime_relative.as_posix() != WRAPPER_RELATIVE.as_posix():
        raise BootstrapError(
            "RUNTIME_WRAPPER_BINDING",
            (
                "the executing wrapper is not at its canonical repository "
                f"path: {runtime_relative.as_posix()}"
            ),
        )
    try:
        runtime_resolved = runtime_lexical.resolve(strict=True)
    except OSError as error:
        raise BootstrapError(
            "RUNTIME_WRAPPER_BINDING",
            f"the executing wrapper cannot be resolved: {runtime_lexical}",
        ) from error
    if runtime_resolved != expected:
        raise BootstrapError(
            "RUNTIME_WRAPPER_BINDING",
            "the executing wrapper does not match the declared repository",
        )


def _load_pinned_core(
    repo_root: Path,
    expected_sha256: str,
) -> ModuleType:
    if not SHA256_PATTERN.fullmatch(expected_sha256):
        raise BootstrapError(
            "RUNTIME_CORE_PIN_INVALID",
            "expected core SHA-256 must be 64 lowercase hexadecimal digits",
    )
    _assert_wrapper_binding(repo_root)
    core_path = _resolve_exact_repo_file(repo_root, CORE_RELATIVE)
    core_raw = core_path.read_bytes()
    actual_sha256 = hashlib.sha256(core_raw).hexdigest()
    if actual_sha256 != expected_sha256:
        raise BootstrapError(
            "RUNTIME_CORE_PIN_MISMATCH",
            (
                "contract core SHA-256 does not match the caller-provided "
                f"pin: expected {expected_sha256}, observed {actual_sha256}"
            ),
        )

    module_name = "formal_run_delta_contract_pinned"
    try:
        spec = importlib.util.spec_from_file_location(module_name, core_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Python did not provide a module loader")
        code = compile(core_raw, str(core_path), "exec")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        exec(code, module.__dict__)
    except Exception as error:
        sys.modules.pop(module_name, None)
        raise BootstrapError(
            "RUNTIME_CORE_LOAD_FAILED",
            f"verified contract core could not be imported: {error}",
        ) from error
    return module


def _emit_failure(message: str) -> int:
    print(
        json.dumps(
            {
                "error": message,
                "status": "failed_closed",
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--delta", required=True)
    parser.add_argument("--expected-core-sha256", required=True)
    parser.add_argument(
        "--allow-repository-wide-byte-reads",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    contract: ModuleType | None = None
    try:
        try:
            repo_root = args.repo_root.resolve(strict=True)
        except OSError as error:
            raise BootstrapError(
                "REPO_ROOT",
                f"repository root cannot be resolved: {args.repo_root}",
            ) from error
        if not repo_root.is_dir():
            raise BootstrapError(
                "REPO_ROOT",
                f"repository root is not a directory: {repo_root}",
            )
        if not args.allow_repository_wide_byte_reads:
            raise BootstrapError(
                "REPOSITORY_WIDE_BYTE_READS_NOT_ACKNOWLEDGED",
                (
                    "this command may read every repository file outside "
                    ".git, including historical run artifacts; pass "
                    "--allow-repository-wide-byte-reads explicitly"
                ),
            )
        contract = _load_pinned_core(
            repo_root,
            args.expected_core_sha256,
        )
        delta_path = contract.resolve_repo_file(repo_root, args.delta)
        _, raw, binding = contract.verify_delta(
            repo_root,
            delta_path,
        )
        print(
            json.dumps(
                {
                    "artifact": args.delta,
                    "candidate_artifact_bytes_read": True,
                    "formal_input_access": True,
                    "isolated_interpreter": True,
                    "repository_wide_bytes_read": True,
                    "runner_or_comparator_executed": False,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "status": "verified",
                    "trust_profile": "canonical_continuous_001",
                    "verified_binding": binding,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except BootstrapError as error:
        return _emit_failure(str(error))
    except (KeyError, OSError, TypeError) as error:
        return _emit_failure(f"VERIFY_INPUT: {error}")
    except Exception as error:
        if (
            contract is not None
            and isinstance(error, contract.DeltaContractError)
        ):
            return _emit_failure(str(error))
        raise


if __name__ == "__main__":
    raise SystemExit(main())
