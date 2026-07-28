#!/usr/bin/env python3
"""Disposable black-box controls for post-gate absence verification 0.1.0.

Only a synthetic Git repository in the system temporary directory is scanned.
No real runs/ path, formal input, runner, comparator, dispatch, or reveal flow
is opened or executed.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA = PILOT / (
    "schema/formal-post-gate-absence-denylist-0.1.0.schema.json"
)
CONTRACT = PILOT / (
    "contracts/formal-post-gate-absence-denylist-0.1.0.json"
)
VERIFIER = PILOT / (
    "tools/verify-formal-post-gate-absence-v0.1.0.py"
)
CANDIDATE_ROOT = PILOT / "runs/continuous-002"

EXPECTED_POSITIVE_IDS = (
    "P01_SCHEMA_CONTRACT_AND_CLEAN_SCAN",
    "P02_DETERMINISTIC_READ_ONLY",
    "P03_TRACKED_CONTROL_TEXT_ALLOWED",
    "P04_NO_FORMAL_EXECUTION",
)
EXPECTED_NEGATIVE_IDS = (
    "N-CLI01_ISOLATED_REQUIRED",
    "N-CLI02_BYTE_READ_ACK_REQUIRED",
    "N-CLI03_ARGUMENT_ERROR_IS_TWO",
    "N-TRUST01_SCHEMA_TAMPER",
    "N-CONTRACT01_NONCANONICAL_BYTES",
    "N-CONTRACT02_EMPTY_GLOB",
    "N-CONTRACT03_WRONG_RUN_ID",
    "N-PATH01_CANDIDATE_FORBIDDEN_PATH",
    "N-PATH02_OUTSIDE_NAMESPACE_SUFFIX",
    "N-PATH03_CASE_VARIANT",
    "N-PATH04_NESTED_DOT_GIT_NOT_EXEMPT",
    "N-PATH05_MANAGER_BROAD_PATH",
    "N-TYPE01_FORBIDDEN_TYPE_SAFE_PATH",
    "N-TYPE02_ESCAPED_FORBIDDEN_TYPE",
    "N-TYPE03_CASEFOLD_FORBIDDEN_TYPE",
    "N-TYPE04_NESTED_FORBIDDEN_TYPE",
    "N-TYPE05_UTF16_FORBIDDEN_TYPE",
    "N-TYPE06_UTF32_FORBIDDEN_TYPE",
    "N-MANIFEST01_POST_GATE_KIND",
    "N-JSON01_CANDIDATE_BOUND_MALFORMED",
    "N-TEXT01_UNTRACKED_CANDIDATE_SIGNATURE",
    "N-TEXT02_MODIFIED_TRACKED_CANDIDATE_SIGNATURE",
    "N-TEXT03_TRACKED_EOL_NORMALIZATION",
)


class SelfTestFailure(RuntimeError):
    """Raised when a control behaves differently from its fixed expectation."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise SelfTestFailure(
            f"git {' '.join(arguments)} failed: {completed.stderr}"
        )
    return completed.stdout.strip()


def copy_inputs(source_root: Path, target_root: Path) -> None:
    for relative in (SCHEMA, CONTRACT, VERIFIER):
        source = source_root / relative
        if not source.is_file():
            raise SelfTestFailure(f"required source file is absent: {relative}")
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def verifier_command(
    root: Path,
    *,
    isolated: bool = True,
    acknowledge_reads: bool = True,
) -> list[str]:
    command = [sys.executable]
    if isolated:
        command.append("-I")
    command.extend(
        [
            str(root / VERIFIER),
            "verify",
            "--repo-root",
            str(root),
        ]
    )
    if acknowledge_reads:
        command.append("--allow-repository-wide-byte-reads")
    return command


def run_verifier(
    root: Path,
    *,
    isolated: bool = True,
    acknowledge_reads: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        verifier_command(
            root,
            isolated=isolated,
            acknowledge_reads=acknowledge_reads,
        ),
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def require_success(
    completed: subprocess.CompletedProcess[str],
    *,
    label: str,
) -> dict[str, Any]:
    if completed.returncode != 0:
        raise SelfTestFailure(
            f"{label} failed: stdout={completed.stdout!r} "
            f"stderr={completed.stderr!r}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SelfTestFailure(
            f"{label} returned non-JSON stdout: {completed.stdout!r}"
        ) from error
    if result.get("status") != "verified_absent":
        raise SelfTestFailure(f"{label} returned wrong status: {result!r}")
    return result


def require_failure(
    completed: subprocess.CompletedProcess[str],
    *,
    code: str,
    label: str,
    returncode: int = 1,
) -> None:
    if completed.returncode != returncode:
        raise SelfTestFailure(
            f"{label} returned {completed.returncode}, expected "
            f"{returncode}: stdout={completed.stdout!r} "
            f"stderr={completed.stderr!r}"
        )
    if returncode == 2:
        if code not in completed.stderr:
            raise SelfTestFailure(
                f"{label} returned the wrong CLI error: "
                f"{completed.stderr!r}"
            )
        return
    try:
        result = json.loads(completed.stderr)
    except json.JSONDecodeError as error:
        raise SelfTestFailure(
            f"{label} returned non-JSON stderr: {completed.stderr!r}"
        ) from error
    if result.get("status") != "failed_closed" or code not in result.get(
        "error",
        "",
    ):
        raise SelfTestFailure(
            f"{label} returned the wrong failure: {result!r}"
        )


def non_git_fingerprint(root: Path) -> str:
    rows: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if (
            (relative.parts and relative.parts[0].casefold() == ".git")
            or not path.is_file()
        ):
            continue
        rows.append((relative.as_posix(), sha256_bytes(path.read_bytes())))
    rows.sort()
    return sha256_bytes(canonical_bytes(rows))


def reset_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def run_self_test(source_root: Path) -> dict[str, Any]:
    positives: list[str] = []
    negatives: list[str] = []
    with tempfile.TemporaryDirectory(
        prefix="game-primitives-post-gate-absence-"
    ) as directory:
        root = Path(directory)
        copy_inputs(source_root, root)
        write_json(
            root / CANDIDATE_ROOT / "inputs/benign.json",
            {
                "artifact_type": "synthetic_pre_gate_fixture",
                "candidate_run_id": "continuous-002",
            },
        )
        control_text = root / "notes/control-plane.md"
        control_text.parent.mkdir(parents=True, exist_ok=True)
        control_text.write_bytes(
            b"Tracked protocol text may mention continuous-002 and "
            b"truth_reveal without being a runtime artifact.\n"
        )
        git(root, "init")
        git(root, "config", "user.email", "synthetic@example.invalid")
        git(root, "config", "user.name", "Synthetic Self Test")
        git(root, "add", ".")
        git(root, "commit", "-m", "synthetic baseline")

        before = non_git_fingerprint(root)
        first = require_success(
            run_verifier(root),
            label="clean synthetic repository",
        )
        positives.append("P01_SCHEMA_CONTRACT_AND_CLEAN_SCAN")
        second = require_success(
            run_verifier(root),
            label="deterministic repeat",
        )
        after = non_git_fingerprint(root)
        if first != second or before != after:
            raise SelfTestFailure(
                "read-only deterministic verification changed repository bytes"
            )
        positives.append("P02_DETERMINISTIC_READ_ONLY")
        if first.get("tracked_control_text_exemptions", 0) < 1:
            raise SelfTestFailure(
                "tracked control-plane text exemption was not exercised"
            )
        positives.append("P03_TRACKED_CONTROL_TEXT_ALLOWED")
        if (
            first.get("actual_dispatch_performed") is not False
            or first.get("runner_or_comparator_executed") is not False
        ):
            raise SelfTestFailure("verifier claimed a runtime action")
        positives.append("P04_NO_FORMAL_EXECUTION")

        require_failure(
            run_verifier(root, isolated=False),
            code="ISOLATED_INTERPRETER_REQUIRED",
            label="non-isolated invocation",
        )
        negatives.append("N-CLI01_ISOLATED_REQUIRED")
        require_failure(
            run_verifier(root, acknowledge_reads=False),
            code="REPOSITORY_BYTE_READ_ACK_REQUIRED",
            label="missing repository byte-read acknowledgement",
        )
        negatives.append("N-CLI02_BYTE_READ_ACK_REQUIRED")
        argument_error = subprocess.run(
            [
                sys.executable,
                "-I",
                str(root / VERIFIER),
                "verify",
                "--repo-root",
                str(root),
                "--unknown-option",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        require_failure(
            argument_error,
            code="unrecognized arguments",
            label="invalid CLI argument",
            returncode=2,
        )
        negatives.append("N-CLI03_ARGUMENT_ERROR_IS_TWO")

        schema_path = root / SCHEMA
        schema_raw = schema_path.read_bytes()
        schema_path.write_bytes(schema_raw + b" ")
        require_failure(
            run_verifier(root),
            code="TRUSTED_SCHEMA_HASH_MISMATCH",
            label="tampered Schema",
        )
        negatives.append("N-TRUST01_SCHEMA_TAMPER")
        schema_path.write_bytes(schema_raw)

        contract_path = root / CONTRACT
        contract_raw = contract_path.read_bytes()
        contract_path.write_bytes(contract_raw + b" ")
        require_failure(
            run_verifier(root),
            code="JSON_BYTES_NONCANONICAL",
            label="noncanonical contract bytes",
        )
        negatives.append("N-CONTRACT01_NONCANONICAL_BYTES")
        contract_path.write_bytes(contract_raw)

        contract = json.loads(contract_raw.decode("utf-8"))
        empty_glob = json.loads(contract_raw.decode("utf-8"))
        empty_glob["rules"][0]["path_patterns"] = []
        write_json(contract_path, empty_glob)
        require_failure(
            run_verifier(root),
            code="DENYLIST_SCHEMA_MISMATCH",
            label="empty path-pattern list",
        )
        negatives.append("N-CONTRACT02_EMPTY_GLOB")
        contract_path.write_bytes(contract_raw)

        wrong_run = json.loads(contract_raw.decode("utf-8"))
        wrong_run["candidate_run_id"] = "continuous-003"
        write_json(contract_path, wrong_run)
        require_failure(
            run_verifier(root),
            code="DENYLIST_SCHEMA_MISMATCH",
            label="wrong candidate run id",
        )
        negatives.append("N-CONTRACT03_WRONG_RUN_ID")
        contract_path.write_bytes(contract_raw)

        forbidden_path = (
            root / CANDIDATE_ROOT / "reveal/truth-reveal-hidden.json"
        )
        write_json(
            forbidden_path,
            {"artifact_type": "synthetic_renamed_payload"},
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="forbidden path in candidate namespace",
        )
        negatives.append("N-PATH01_CANDIDATE_FORBIDDEN_PATH")
        forbidden_path.unlink()
        forbidden_path.parent.rmdir()

        outside_suffix = (
            root
            / "archive/continuous-002/execution/results/result.json"
        )
        write_json(
            outside_suffix,
            {"artifact_type": "synthetic_renamed_payload"},
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="candidate suffix outside canonical namespace",
        )
        negatives.append("N-PATH02_OUTSIDE_NAMESPACE_SUFFIX")
        reset_path(root / "archive")

        case_variant = (
            root
            / "Archive/CONTINUOUS-002/REVEAL/truth-reveal-X.JSON"
        )
        write_json(
            case_variant,
            {"artifact_type": "synthetic_renamed_payload"},
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="case-variant candidate suffix",
        )
        negatives.append("N-PATH03_CASE_VARIANT")
        reset_path(root / "Archive")

        nested_git = (
            root
            / "ordinary/.git/continuous-002/reveal/truth-reveal.json"
        )
        write_json(
            nested_git,
            {"artifact_type": "synthetic_renamed_payload"},
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="nested dot-git directory is ordinary repository content",
        )
        negatives.append("N-PATH04_NESTED_DOT_GIT_NOT_EXEMPT")
        reset_path(root / "ordinary")

        broad_path = (
            root / CANDIDATE_ROOT / "execution/raw/renamed.bin"
        )
        broad_path.parent.mkdir(parents=True, exist_ok=True)
        broad_path.write_bytes(b"\x00\x01synthetic")
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="manager-compatible broad post-gate path",
        )
        negatives.append("N-PATH05_MANAGER_BROAD_PATH")
        reset_path(root / CANDIDATE_ROOT / "execution")

        forbidden_type = root / CANDIDATE_ROOT / "inputs/renamed.json"
        write_json(
            forbidden_type,
            {
                "artifact_type": "execution_result",
                "candidate_run_id": "continuous-002",
            },
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="forbidden type at a safe-looking path",
        )
        negatives.append("N-TYPE01_FORBIDDEN_TYPE_SAFE_PATH")
        forbidden_type.unlink()

        escaped_type = root / "spill/encoded.json"
        escaped_type.parent.mkdir(parents=True, exist_ok=True)
        escaped_type.write_bytes(
            b'{"artifact_type":"execution_\\u0072esult",'
            b'"candidate_run_id":"continuous-002"}\n'
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="escaped forbidden artifact type",
        )
        negatives.append("N-TYPE02_ESCAPED_FORBIDDEN_TYPE")
        reset_path(root / "spill")

        casefold_type = root / "spill/casefold.json"
        write_json(
            casefold_type,
            {
                "artifact_type": "Execution_Result",
                "candidate_run_id": "continuous-002",
            },
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="casefolded forbidden artifact type",
        )
        negatives.append("N-TYPE03_CASEFOLD_FORBIDDEN_TYPE")
        reset_path(root / "spill")

        nested_type = root / "spill/nested.json"
        write_json(
            nested_type,
            {
                "payload": {
                    "Artifact_Type": "execution_result",
                    "candidate_run_id": "continuous-002",
                }
            },
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="nested candidate-bound forbidden artifact type",
        )
        negatives.append("N-TYPE04_NESTED_FORBIDDEN_TYPE")
        reset_path(root / "spill")

        utf16_type = root / "spill/utf16.json"
        utf16_type.parent.mkdir(parents=True, exist_ok=True)
        utf16_type.write_bytes(
            json.dumps(
                {
                    "artifact_type": "execution_result",
                    "candidate_run_id": "continuous-002",
                },
                sort_keys=True,
            ).encode("utf-16")
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="UTF-16 candidate-bound forbidden artifact type",
        )
        negatives.append("N-TYPE05_UTF16_FORBIDDEN_TYPE")
        reset_path(root / "spill")

        utf32_type = root / "spill/utf32.json"
        utf32_type.parent.mkdir(parents=True, exist_ok=True)
        utf32_type.write_bytes(
            json.dumps(
                {
                    "artifact_type": "execution_result",
                    "candidate_run_id": "continuous-002",
                },
                sort_keys=True,
            ).encode("utf-32")
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="UTF-32 candidate-bound forbidden artifact type",
        )
        negatives.append("N-TYPE06_UTF32_FORBIDDEN_TYPE")
        reset_path(root / "spill")

        manifest_path = root / CANDIDATE_ROOT / "manifest.json"
        write_json(
            manifest_path,
            {
                "artifacts": [
                    {
                        "artifact_kind": "execution_result",
                        "path": "renamed/output.json",
                    }
                ]
            },
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="post-gate artifact kind in candidate manifest",
        )
        negatives.append("N-MANIFEST01_POST_GATE_KIND")
        manifest_path.unlink()

        malformed = root / "spill/malformed.json"
        malformed.parent.mkdir(parents=True, exist_ok=True)
        malformed.write_bytes(
            b'{"candidate_run_id":"continuous-002",'
            b'"artifact_type":"execution_result"\n'
        )
        require_failure(
            run_verifier(root),
            code="CANDIDATE_JSON_INVALID",
            label="candidate-bound malformed JSON",
        )
        negatives.append("N-JSON01_CANDIDATE_BOUND_MALFORMED")
        reset_path(root / "spill")

        text_leak = root / "spill/leak.txt"
        text_leak.parent.mkdir(parents=True, exist_ok=True)
        text_leak.write_text(
            "continuous-002 leaked a truth_reveal payload\n",
            encoding="utf-8",
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="untracked candidate-bound text signature",
        )
        negatives.append("N-TEXT01_UNTRACKED_CANDIDATE_SIGNATURE")
        reset_path(root / "spill")

        control_text.write_bytes(
            b"Modified tracked protocol text mentions continuous-002 and "
            b"truth_reveal as a hidden runtime payload.\n"
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="modified tracked candidate-bound text signature",
        )
        negatives.append(
            "N-TEXT02_MODIFIED_TRACKED_CANDIDATE_SIGNATURE"
        )
        control_text.write_bytes(
            b"Tracked protocol text may mention continuous-002 and "
            b"truth_reveal without being a runtime artifact.\n"
        )

        control_text.write_bytes(
            b"Tracked protocol text may mention continuous-002 and "
            b"truth_reveal without being a runtime artifact.\r\n"
        )
        require_failure(
            run_verifier(root),
            code="ABSENCE_MATCH",
            label="tracked control text EOL normalization",
        )
        negatives.append("N-TEXT03_TRACKED_EOL_NORMALIZATION")
        control_text.write_bytes(
            b"Tracked protocol text may mention continuous-002 and "
            b"truth_reveal without being a runtime artifact.\n"
        )

        if tuple(positives) != EXPECTED_POSITIVE_IDS:
            raise SelfTestFailure(
                f"positive control set drifted: {positives!r}"
            )
        if tuple(negatives) != EXPECTED_NEGATIVE_IDS:
            raise SelfTestFailure(
                f"negative control set drifted: {negatives!r}"
            )
        return {
            "formal_input_access": False,
            "negative_controls": negatives,
            "negative_controls_passed": len(negatives),
            "positive_controls": positives,
            "positive_controls_passed": len(positives),
            "runner_or_comparator_executed": False,
            "status": "synthetic_self_test_passed",
            "temporary_repository_only": True,
        }


def main() -> int:
    try:
        result = run_self_test(Path.cwd().resolve())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        OSError,
        SelfTestFailure,
        subprocess.SubprocessError,
        ValueError,
    ) as error:
        print(
            json.dumps(
                {
                    "error": str(error),
                    "status": "synthetic_self_test_failed",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
