#!/usr/bin/env python3
"""Strictly verify permit-bound CA-R1 standalone build-readiness evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


BASE = Path("research/calibration-tests/continuous-action-pilot")
RUN = BASE / "runs/continuous-001"
EVIDENCE = RUN / "fixtures/r1/r1-standalone-build-evidence-v0.1.0.json"
SCHEMA = BASE / "schema/r1-standalone-build-evidence-0.1.0.schema.json"
DISPATCH = BASE / "tools/materialize-dispatch.py"
CONFIGURATIONS = ("config.baseline", "config.variant")
FORMAL_OUTPUT_IDS = {
    "config.baseline": "output.ca-r1.baseline-formal-assembly",
    "config.variant": "output.ca-r1.variant-formal-assembly",
}


class EvidenceError(RuntimeError):
    """A fail-closed CA-R1 readiness-evidence error."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise EvidenceError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def reject_nonfinite(value: str) -> None:
    raise EvidenceError(f"non-finite JSON number: {value}")


def read_object(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise EvidenceError(f"UTF-8 BOM is forbidden: {path}")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EvidenceError(f"invalid UTF-8 JSON: {path}") from error
    if not isinstance(value, dict):
        raise EvidenceError(f"expected JSON object: {path}")
    return value, raw


def load_dispatch(repo_root: Path) -> Any:
    path = (repo_root / DISPATCH).resolve()
    if not path.is_file() or not path.is_relative_to(repo_root):
        raise EvidenceError("schema-registry validator is missing")
    spec = importlib.util.spec_from_file_location("gp_r1_dispatch", path)
    if spec is None or spec.loader is None:
        raise EvidenceError("could not load schema-registry validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def external_path(value: str) -> Path:
    path = Path(value.replace("/", "\\"))
    if not path.is_absolute():
        raise EvidenceError(f"external path is not absolute: {value}")
    return path


def verify_external(reference: dict[str, Any], label: str) -> Path:
    path = external_path(str(reference["external_path"]))
    if not path.is_file():
        raise EvidenceError(f"{label} is missing: {path}")
    if path.stat().st_size != int(reference["bytes"]):
        raise EvidenceError(f"{label} byte count mismatch")
    if sha256(path) != reference["sha256"]:
        raise EvidenceError(f"{label} SHA-256 mismatch")
    return path


def verify_repo_reference(
    repo_root: Path,
    reference: dict[str, Any],
    label: str,
) -> Path:
    path = (repo_root / str(reference["path"])).resolve()
    if not path.is_relative_to(repo_root) or not path.is_file():
        raise EvidenceError(f"{label} is missing or escapes the repository")
    if sha256(path) != reference["sha256"]:
        raise EvidenceError(f"{label} SHA-256 mismatch")
    return path


def verify(repo_root: Path, evidence_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    expected_path = (repo_root / EVIDENCE).resolve()
    evidence_path = evidence_path.resolve()
    if evidence_path != expected_path or not evidence_path.is_file():
        raise EvidenceError("evidence must use the fixed CA-R1 repository path")
    evidence, _ = read_object(evidence_path)
    dispatch = load_dispatch(repo_root)
    try:
        dispatch.validate_against_repo_schema_registry(
            repo_root,
            evidence,
            SCHEMA.as_posix(),
        )
    except Exception as error:
        raise EvidenceError(f"CA-R1 evidence schema check failed: {error}") from error

    if (
        evidence.get("build_gate_status") != "passed"
        or evidence.get("formal_execution", {}).get("formal_input_read") is not False
        or evidence.get("formal_execution", {}).get("formal_input_executed")
        is not False
        or evidence.get("formal_execution", {}).get("formal_result_created")
        is not False
        or evidence.get("reproducibility", {}).get("verified") is not True
        or evidence.get("reproducibility", {}).get("formal_pdb_files_found") != 0
    ):
        raise EvidenceError("CA-R1 evidence is not a clean reproducible build pass")

    # The formal input is intentionally excluded from this build-only verifier.
    # Its permit-bound hash is checked by the runner after authorization.
    for surface_name in ("formal_execution", "synthetic_smoke_only"):
        for reference in evidence["fixture_surfaces"][surface_name]:
            if str(reference["path"]).endswith(
                "/footsies-r1-formal-input-v0.1.0.json"
            ):
                continue
            verify_repo_reference(
                repo_root,
                reference,
                f"{surface_name} surface {reference['path']}",
            )

    verify_repo_reference(
        repo_root,
        evidence["source_identity"]["frozen_source_contract"],
        "frozen source contract",
    )
    verify_external(evidence["external_evidence"], "primary external evidence")
    verify_external(
        evidence["toolchain"]["dotnet_executable"],
        "portable dotnet executable",
    )
    for index, reference in enumerate(
        evidence["reproducibility"]["evidence_files"],
        start=1,
    ):
        verify_external(reference, f"reproducibility evidence {index}")

    outputs: dict[str, dict[str, Any]] = {}
    for configuration_id in CONFIGURATIONS:
        configurations = [
            item
            for item in evidence["configurations"]
            if item["configuration_id"] == configuration_id
        ]
        if len(configurations) != 1:
            raise EvidenceError(f"{configuration_id} is not unique")
        formal_outputs = [
            item
            for item in configurations[0]["outputs"]
            if item["output_kind"] == "formal_execution"
        ]
        if (
            len(formal_outputs) != 1
            or formal_outputs[0]["output_id"]
            != FORMAL_OUTPUT_IDS[configuration_id]
        ):
            raise EvidenceError(f"{configuration_id} formal output differs")
        output = formal_outputs[0]
        verify_external(output, f"{configuration_id} formal assembly")
        expected_hash = evidence["reproducibility"]["formal_outputs"][
            configuration_id.removeprefix("config.") + "_sha256"
        ]
        if output["sha256"] != expected_hash:
            raise EvidenceError(
                f"{configuration_id} formal output lacks reproducible binding"
            )
        outputs[configuration_id] = {
            "external_path": output["external_path"],
            "output_id": output["output_id"],
            "sha256": output["sha256"],
        }

    if outputs["config.baseline"]["sha256"] != outputs["config.variant"]["sha256"]:
        raise EvidenceError("baseline and variant formal assemblies differ")
    return {
        "artifact_type": evidence["artifact_type"],
        "evidence_sha256": sha256(evidence_path),
        "formal_input_read": False,
        "outputs": outputs,
        "reproducibility": "two_independent_roots_byte_identical",
        "status": "r1_build_readiness_verified",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("verify",))
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--evidence-path", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.repo_root, args.evidence_path)
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
