#!/usr/bin/env python3
"""Strictly verify the permit-bound CA-R2 build-readiness evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


RUN = Path("research/calibration-tests/continuous-action-pilot/runs/continuous-001")
EVIDENCE = RUN / "fixtures/r2/r2-build-readiness-evidence-v0.1.0.json"
SCHEMA = Path(
    "research/calibration-tests/continuous-action-pilot/"
    "schema/r2-build-readiness-evidence-0.1.0.schema.json"
)
CONFIGURATIONS = ("config.baseline", "config.variant")
OUTPUT_IDS = {
    "config.baseline": "output.ca-r2.baseline-executable",
    "config.variant": "output.ca-r2.variant-executable",
}


class EvidenceError(RuntimeError):
    pass


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


def read_object(path: Path) -> dict[str, Any]:
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
    return value


def external_path(value: str) -> Path:
    path = Path(value.replace("/", "\\"))
    if not path.is_absolute():
        raise EvidenceError(f"external path is not absolute: {value}")
    return path


def verify_file(reference: dict[str, Any], label: str) -> Path:
    path = external_path(reference["external_path"])
    if not path.is_file():
        raise EvidenceError(f"{label} is missing: {path}")
    if path.stat().st_size != reference["bytes"]:
        raise EvidenceError(f"{label} byte count mismatch")
    if sha256(path) != reference["sha256"]:
        raise EvidenceError(f"{label} SHA-256 mismatch")
    return path


def validate_schema(
    repo_root: Path,
    evidence: dict[str, Any],
) -> None:
    schema = read_object(repo_root / SCHEMA)
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(evidence),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(item) for item in first.absolute_path) or "$"
        raise EvidenceError(f"schema failure at {location}: {first.message}")


def verify_upstream(
    document: dict[str, Any],
    structured_outputs: dict[str, dict[str, Any]],
) -> None:
    if (
        document.get("artifact_type")
        != "q3_r2_formal_fixture_build_evidence"
        or document.get("artifact_version") != "0.1.0"
        or document.get("run_id") != "continuous-001"
        or document.get("case_id") != "CA-R2"
        or document.get("formal_input_read") is not False
        or document.get("formal_input_executed") is not False
        or document.get("formal_result_created") is not False
    ):
        raise EvidenceError("upstream evidence is not a clean CA-R2 build")
    artifacts = document.get("artifacts")
    reproducibility = document.get("reproducibility")
    self_tests = document.get("self_tests")
    if (
        not isinstance(artifacts, dict)
        or not isinstance(reproducibility, dict)
        or not isinstance(self_tests, dict)
    ):
        raise EvidenceError("upstream artifacts or reproducibility are absent")
    if (
        self_tests.get("failure_descendant_cleanup") != "passed"
        or self_tests.get("output_child_root_rejected") != "passed"
        or self_tests.get("timeout_descendant_cleanup") != "passed"
    ):
        raise EvidenceError("upstream safety controls did not pass")
    if "formal_input" in artifacts or "generated_input_header" in artifacts:
        raise EvidenceError("upstream pre-gate evidence contains input-derived artifacts")
    for configuration, artifact_name in (
        ("config.baseline", "baseline_executable"),
        ("config.variant", "variant_executable"),
    ):
        label = configuration.removeprefix("config.")
        artifact = artifacts.get(artifact_name)
        replica = reproducibility.get(label)
        structured = structured_outputs[configuration]
        if (
            not isinstance(artifact, dict)
            or not isinstance(replica, dict)
            or replica.get("algorithm") != "sha256"
            or replica.get("byte_identical") is not True
            or replica.get("sha256") != structured["sha256"]
            or artifact.get("sha256") != structured["sha256"]
        ):
            raise EvidenceError(
                f"upstream {configuration} does not prove byte identity"
            )
        primary_path = Path(str(replica.get("primary_path", "")))
        replica_path = Path(str(replica.get("replica_path", "")))
        if (
            not primary_path.is_absolute()
            or not replica_path.is_absolute()
            or primary_path == replica_path
            or not primary_path.is_file()
            or not replica_path.is_file()
            or sha256(primary_path) != structured["sha256"]
            or sha256(replica_path) != structured["sha256"]
        ):
            raise EvidenceError(
                f"upstream {configuration} replica bytes differ"
            )


def verify(repo_root: Path, evidence_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    expected = (repo_root / EVIDENCE).resolve()
    evidence_path = evidence_path.resolve()
    if evidence_path != expected or not evidence_path.is_file():
        raise EvidenceError("evidence must use the fixed CA-R2 repository path")
    evidence = read_object(evidence_path)
    validate_schema(repo_root, evidence)

    attempts = evidence["build_attempts"]
    seen_configurations = [attempt["configuration_ids"][0] for attempt in attempts]
    if seen_configurations != list(CONFIGURATIONS):
        raise EvidenceError("build attempts are not in canonical configuration order")
    structured_outputs: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        configuration = attempt["configuration_ids"][0]
        output = attempt["outputs"][0]
        if output["output_id"] != OUTPUT_IDS[configuration]:
            raise EvidenceError(f"{configuration} output id differs")
        verify_file(output, f"{configuration} executable")
        structured_outputs[configuration] = output

    roots = [
        external_path(value)
        for value in evidence["reproducibility"]["independent_build_roots"]
    ]
    if roots[0].resolve() == roots[1].resolve():
        raise EvidenceError("independent build roots resolve to the same path")

    upstream_documents = []
    for index, reference in enumerate(evidence["upstream_evidence_files"]):
        path = verify_file(reference, f"upstream evidence {index + 1}")
        if not path.resolve().is_relative_to(roots[index].resolve()):
            raise EvidenceError("upstream evidence is outside its declared build root")
        upstream_documents.append(read_object(path))
    for document in upstream_documents:
        verify_upstream(document, structured_outputs)

    return {
        "artifact_type": evidence["artifact_type"],
        "evidence_sha256": sha256(evidence_path),
        "formal_input_read": False,
        "output_boundary": "fixed_root_child_rejected",
        "outputs": {
            configuration: {
                "external_path": structured_outputs[configuration]["external_path"],
                "output_id": structured_outputs[configuration]["output_id"],
                "sha256": structured_outputs[configuration]["sha256"],
            }
            for configuration in CONFIGURATIONS
        },
        "process_tree_cleanup": "failure_and_timeout_descendants_zero",
        "reproducibility": "byte_identical",
        "status": "r2_build_readiness_verified",
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
