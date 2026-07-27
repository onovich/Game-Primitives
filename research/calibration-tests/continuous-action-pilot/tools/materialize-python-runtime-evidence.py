#!/usr/bin/env python3
"""Bind and test the Python runtime used by every formal PowerShell surface.

This pre-gate tool never opens a formal input.  It proves that all three
runners and all three comparators require the same explicit, hash-pinned
Python executable before they can invoke a repository verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


BASE = Path("research/calibration-tests/continuous-action-pilot")
RUN = BASE / "runs/continuous-001"
SCHEMA = BASE / "schema/python-runtime-evidence-0.1.0.schema.json"
OUTPUT = RUN / "fixtures/python-runtime-evidence-v0.1.0.json"
SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "python-runtime-evidence-0.1.0.schema.json"
)
PYTHON_PATH = Path(r"C:\Python314\python.exe")
PYTHON_DISPLAY_PATH = "C:/Python314/python.exe"
PYTHON_SHA256 = (
    "cce21c0e8710e304273e98ac4b2b0f5aceb639acbcd2343cbaa5c4e81619c45b"
)
PYTHON_BYTES = 106328
PYTHON_VERSION = "Python 3.14.3"
POWERSHELL = Path(
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)
FORMAL_OUTPUT_ROOT = r"D:\GamePrimitivesFormalOutputs"

TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        (
            RUN
            / "fixtures/r1/run-footsies-r1-standalone-formal-v0.1.0.ps1"
        ).as_posix(),
        (
            "-ConfigurationId",
            "config.baseline",
            "-RepetitionIndex",
            "1",
            "-SourceRoot",
            r"D:\__gp_python_probe_missing_footsies__",
            "-DotnetPath",
            r"D:\__gp_python_probe_missing_dotnet__\dotnet.exe",
            "-FormalOutputRoot",
            FORMAL_OUTPUT_ROOT,
        ),
    ),
    (
        (RUN / "fixtures/r1/compare-footsies-r1-v0.1.0.ps1").as_posix(),
        (
            "-FormalOutputRoot",
            FORMAL_OUTPUT_ROOT,
            "-SourceRoot",
            r"D:\__gp_python_probe_missing_footsies__",
            "-DotnetPath",
            r"D:\__gp_python_probe_missing_dotnet__\dotnet.exe",
        ),
    ),
    (
        (RUN / "fixtures/r2/run-q3-formal-guarded-v0.1.0.ps1").as_posix(),
        (
            "-BuildEvidencePath",
            (RUN / "fixtures/r2/r2-build-readiness-evidence-v0.1.0.json").as_posix(),
            "-ConfigurationId",
            "config.baseline",
            "-RepetitionIndex",
            "1",
            "-FormalOutputRoot",
            FORMAL_OUTPUT_ROOT,
            "-SourceRoot",
            r"D:\__gp_python_probe_missing_quake3__",
            "-ToolchainRoot",
            r"D:\__gp_python_probe_missing_msvc__",
        ),
    ),
    (
        (RUN / "fixtures/r2/compare-q3-formal-traces-v0.1.0.ps1").as_posix(),
        ("-FormalOutputRoot", FORMAL_OUTPUT_ROOT),
    ),
    (
        (RUN / "fixtures/r3/run-osu-r3-formal-v0.1.0.ps1").as_posix(),
        (
            "-ConfigurationId",
            "config.baseline",
            "-RepetitionIndex",
            "1",
            "-SourcePath",
            r"D:\__gp_python_probe_missing_osu__",
            "-DotnetPath",
            r"D:\__gp_python_probe_missing_dotnet__\dotnet.exe",
            "-FormalOutputRoot",
            FORMAL_OUTPUT_ROOT,
        ),
    ),
    (
        (RUN / "fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1").as_posix(),
        ("-FormalOutputRoot", FORMAL_OUTPUT_ROOT),
    ),
)


class RuntimeEvidenceError(RuntimeError):
    """A fail-closed runtime-evidence error."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_object(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeEvidenceError(f"UTF-8 BOM is forbidden: {path}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeEvidenceError(f"invalid UTF-8 JSON: {path}") from error
    if not isinstance(value, dict):
        raise RuntimeEvidenceError(f"expected a JSON object: {path}")
    return value, raw


def repo_file(repo_root: Path, relative: str | Path) -> Path:
    path = (repo_root / relative).resolve()
    if not path.is_relative_to(repo_root) or not path.is_file():
        raise RuntimeEvidenceError(f"required repository file is missing: {relative}")
    return path


def runtime_identity() -> dict[str, Any]:
    if not PYTHON_PATH.is_file():
        raise RuntimeEvidenceError(f"frozen Python runtime is missing: {PYTHON_PATH}")
    if PYTHON_PATH.stat().st_size != PYTHON_BYTES:
        raise RuntimeEvidenceError("frozen Python runtime byte count differs")
    if sha256_path(PYTHON_PATH) != PYTHON_SHA256:
        raise RuntimeEvidenceError("frozen Python runtime SHA-256 differs")
    version = subprocess.run(
        [str(PYTHON_PATH), "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    output = (version.stdout + version.stderr).strip()
    if version.returncode != 0 or output != PYTHON_VERSION:
        raise RuntimeEvidenceError("frozen Python runtime version differs")
    return {
        "bytes": PYTHON_BYTES,
        "executable_path": PYTHON_DISPLAY_PATH,
        "platform": "windows-x64",
        "runtime_id": "python-3.14.3-windows-x64",
        "sha256": PYTHON_SHA256,
        "version_stdout": PYTHON_VERSION,
    }


def verify_target_source(path: Path) -> None:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RuntimeEvidenceError(f"UTF-8 BOM is forbidden: {path}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeEvidenceError(f"target is not UTF-8: {path}") from error
    required = (
        "$PythonPath",
        "Resolve-FixedPythonRuntime",
        PYTHON_SHA256,
        r"C:\Python314\python.exe",
        "$PythonExecutablePath",
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise RuntimeEvidenceError(
            f"{path} lacks fixed-Python controls: {', '.join(missing)}"
        )
    forbidden = (
        r"(?i)Get-Command\s+python(?:\.exe)?",
        r"(?i)&\s*python(?:\.exe)?\s",
    )
    for pattern in forbidden:
        if re.search(pattern, text):
            raise RuntimeEvidenceError(
                f"{path} still performs a PATH-based Python lookup"
            )


def target_command(
    repo_root: Path,
    relative: str,
    base_arguments: tuple[str, ...],
    *,
    python_path: Path,
    permit_path: Path,
) -> list[str]:
    return [
        str(POWERSHELL),
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(repo_file(repo_root, relative)),
        *base_arguments,
        "-ExecutionPermitPath",
        str(permit_path),
        "-PythonPath",
        str(python_path),
    ]


def run_negative_controls(repo_root: Path) -> tuple[int, int]:
    if not POWERSHELL.is_file():
        raise RuntimeEvidenceError(f"PowerShell executable is missing: {POWERSHELL}")
    wrong_rejections = 0
    shim_bypasses = 0
    with tempfile.TemporaryDirectory(prefix="gp-python-runtime-") as temporary:
        temporary_root = Path(temporary).resolve()
        sentinel = temporary_root / "path-shim-invoked.txt"
        shim = temporary_root / "python.cmd"
        shim.write_text(
            "@echo off\r\n"
            f'echo invoked>"{sentinel}"\r\n'
            "echo PATH_SHIM_WAS_INVOKED 1>&2\r\n"
            "exit /b 99\r\n",
            encoding="ascii",
        )
        missing_permit = temporary_root / "missing-formal-execution-permit.json"
        wrong_runtime = Path(r"C:\Windows\System32\cmd.exe")
        environment = dict(os.environ)
        environment["PATH"] = os.pathsep.join(
            (
                str(temporary_root),
                r"C:\Windows\System32",
                r"C:\Windows",
                r"C:\Windows\System32\WindowsPowerShell\v1.0",
            )
        )
        environment["PYTHONPATH"] = ""
        environment["PYTHONHOME"] = ""

        for relative, arguments in TARGETS:
            wrong = subprocess.run(
                target_command(
                    repo_root,
                    relative,
                    arguments,
                    python_path=wrong_runtime,
                    permit_path=missing_permit,
                ),
                cwd=repo_root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )
            wrong_text = wrong.stdout + wrong.stderr
            if (
                wrong.returncode == 0
                or "PythonPath must resolve to the frozen Python 3.14.3 runtime."
                not in wrong_text
            ):
                raise RuntimeEvidenceError(
                    f"{relative} did not reject the wrong Python runtime first"
                )
            wrong_rejections += 1

            sentinel.unlink(missing_ok=True)
            shim_probe = subprocess.run(
                target_command(
                    repo_root,
                    relative,
                    arguments,
                    python_path=PYTHON_PATH,
                    permit_path=missing_permit,
                ),
                cwd=repo_root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
            )
            shim_text = shim_probe.stdout + shim_probe.stderr
            if (
                shim_probe.returncode == 0
                or sentinel.exists()
                or "PATH_SHIM_WAS_INVOKED" in shim_text
                or not any(
                    marker in shim_text
                    for marker in (
                        "Execution-permit verification failed",
                        "execution permit error:",
                    )
                )
            ):
                raise RuntimeEvidenceError(
                    f"{relative} did not bypass the PATH shim with explicit Python; "
                    f"exit={shim_probe.returncode}; output={shim_text[-1200:]!r}"
                )
            shim_bypasses += 1
    return wrong_rejections, shim_bypasses


def expected_document(repo_root: Path) -> dict[str, Any]:
    runtime = runtime_identity()
    bindings = []
    for relative, _ in TARGETS:
        path = repo_file(repo_root, relative)
        verify_target_source(path)
        bindings.append({"path": relative, "sha256": sha256_path(path)})
    wrong_rejections, shim_bypasses = run_negative_controls(repo_root)
    return {
        "$schema": SCHEMA_ID,
        "artifact_type": "formal_python_runtime_evidence",
        "artifact_version": "0.1.0",
        "controls": {
            "explicit_python_path_required": True,
            "path_lookup_forbidden": True,
            "path_shim_bypasses": shim_bypasses,
            "target_count": len(bindings),
            "wrong_runtime_rejections": wrong_rejections,
        },
        "formal_input_executed": False,
        "formal_input_read": False,
        "formal_result_created": False,
        "run_id": "continuous-001",
        "runtime": runtime,
        "target_bindings": bindings,
    }


def validate(repo_root: Path, document: dict[str, Any]) -> None:
    schema, _ = read_object(repo_file(repo_root, SCHEMA))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(document),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(item) for item in first.absolute_path) or "$"
        raise RuntimeEvidenceError(
            f"Python runtime evidence schema failure at {location}: {first.message}"
        )


def materialize(repo_root: Path) -> dict[str, Any]:
    output = (repo_root / OUTPUT).resolve()
    if output.exists():
        raise RuntimeEvidenceError(f"refusing to overwrite existing evidence: {OUTPUT}")
    document = expected_document(repo_root)
    validate(repo_root, document)
    raw = canonical_bytes(document)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {
        "formal_input_read": False,
        "path": OUTPUT.as_posix(),
        "sha256": sha256_bytes(raw),
        "status": "python_runtime_evidence_materialized",
    }


def verify(repo_root: Path) -> dict[str, Any]:
    output = repo_file(repo_root, OUTPUT)
    document, raw = read_object(output)
    if raw != canonical_bytes(document):
        raise RuntimeEvidenceError("Python runtime evidence is not canonical JSON")
    validate(repo_root, document)
    expected = expected_document(repo_root)
    if document != expected:
        raise RuntimeEvidenceError(
            "Python runtime evidence differs from current runtime and targets"
        )
    return {
        "formal_input_read": False,
        "path": OUTPUT.as_posix(),
        "runtime": document["runtime"],
        "sha256": sha256_bytes(raw),
        "status": "python_runtime_evidence_verified",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("materialize", "verify"))
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        repo_root = args.repo_root.resolve()
        if not repo_root.is_dir():
            raise RuntimeEvidenceError("repository root is not a directory")
        result = (
            materialize(repo_root)
            if args.command == "materialize"
            else verify(repo_root)
        )
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
