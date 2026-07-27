#!/usr/bin/env python3
"""Verify protocol 0.1.1 participant-interface readiness in isolation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PILOT = Path("research/calibration-tests/continuous-action-pilot")
REHEARSAL = PILOT / "rehearsals/rehearsal-006"
BUILDER = PILOT / "tools/build-role-submission-v0.1.1.py"
PREDICTION_CHECKER = (
    PILOT / "tools/verify-prediction-template-contract-v0.1.1.py"
)
RECONSTRUCTION_CHECKER = (
    PILOT / "tools/verify-reconstruction-template-contract-v0.1.1.py"
)
PROMPT_GENERATOR = PILOT / "tools/materialize-rehearsal-006-prompts.py"
READINESS_SCHEMA = (
    PILOT / "schema/participant-interface-readiness-0.1.0.schema.json"
)
DISPATCH_SCHEMA = (
    PILOT / "schema/rehearsal-actor-dispatch-plan-0.1.0.schema.json"
)
EXPECTATIONS = REHEARSAL / "fixtures/expected-results.json"

ISOLATION_DEPENDENCIES = [
    BUILDER,
    PREDICTION_CHECKER,
    RECONSTRUCTION_CHECKER,
    PROMPT_GENERATOR,
    *(
        PILOT / "schema" / name
        for name in (
            "blind-response-interface-0.1.1.schema.json",
            "prediction-participant-response-contract-0.1.1.schema.json",
            "prediction-template-contract-check-0.1.1.schema.json",
            "reconstruction-participant-response-contract-0.1.1.schema.json",
            "reconstruction-response-template-0.1.1.schema.json",
            "reconstruction-template-contract-check-0.1.1.schema.json",
            "rehearsal-actor-dispatch-plan-0.1.0.schema.json",
            "response-template-0.1.1.schema.json",
            "role-submission-0.1.1.schema.json",
            "role-submission-0.1.2.schema.json",
            "task-packet-0.1.0.schema.json",
            "task-packet-0.1.1.schema.json",
            "task-packet-0.1.2.schema.json",
            "variant-envelope-0.1.0.schema.json",
        )
    ),
]

ARCHIVE_MIRRORS = {
    (
        "inputs/protocol/schema/"
        "blind-response-interface-0.1.1.schema.json"
    ): PILOT / "schema/blind-response-interface-0.1.1.schema.json",
    (
        "inputs/protocol/schema/"
        "participant-interface-readiness-0.1.0.schema.json"
    ): READINESS_SCHEMA,
    (
        "inputs/protocol/schema/"
        "prediction-participant-response-contract-0.1.1.schema.json"
    ): (
        PILOT
        / "schema/prediction-participant-response-contract-0.1.1.schema.json"
    ),
    (
        "inputs/protocol/schema/"
        "prediction-template-contract-check-0.1.1.schema.json"
    ): (
        PILOT / "schema/prediction-template-contract-check-0.1.1.schema.json"
    ),
    (
        "inputs/protocol/schema/"
        "rehearsal-actor-dispatch-plan-0.1.0.schema.json"
    ): DISPATCH_SCHEMA,
    (
        "inputs/protocol/schema/"
        "reconstruction-participant-response-contract-0.1.1.schema.json"
    ): (
        PILOT
        / "schema/reconstruction-participant-response-contract-0.1.1.schema.json"
    ),
    (
        "inputs/protocol/schema/"
        "reconstruction-response-template-0.1.1.schema.json"
    ): PILOT / "schema/reconstruction-response-template-0.1.1.schema.json",
    (
        "inputs/protocol/schema/"
        "reconstruction-template-contract-check-0.1.1.schema.json"
    ): (
        PILOT
        / "schema/reconstruction-template-contract-check-0.1.1.schema.json"
    ),
    (
        "inputs/protocol/schema/response-template-0.1.1.schema.json"
    ): PILOT / "schema/response-template-0.1.1.schema.json",
    (
        "inputs/protocol/schema/role-submission-0.1.1.schema.json"
    ): PILOT / "schema/role-submission-0.1.1.schema.json",
    (
        "inputs/protocol/schema/role-submission-0.1.2.schema.json"
    ): PILOT / "schema/role-submission-0.1.2.schema.json",
    (
        "inputs/protocol/schema/task-packet-0.1.0.schema.json"
    ): PILOT / "schema/task-packet-0.1.0.schema.json",
    (
        "inputs/protocol/schema/task-packet-0.1.1.schema.json"
    ): PILOT / "schema/task-packet-0.1.1.schema.json",
    (
        "inputs/protocol/schema/task-packet-0.1.2.schema.json"
    ): PILOT / "schema/task-packet-0.1.2.schema.json",
    (
        "inputs/protocol/schema/variant-envelope-0.1.0.schema.json"
    ): PILOT / "schema/variant-envelope-0.1.0.schema.json",
    (
        "inputs/protocol/schema/rehearsal-input-0.1.1.schema.json"
    ): PILOT / "schema/rehearsal-input-0.1.1.schema.json",
    (
        "inputs/protocol/schema/run-manifest-0.1.0.schema.json"
    ): PILOT / "schema/run-manifest-0.1.0.schema.json",
    (
        "inputs/protocol/schema/frozen-set-preimage-0.1.0.schema.json"
    ): PILOT / "schema/frozen-set-preimage-0.1.0.schema.json",
    (
        "inputs/protocol/schema/markdown-document-0.1.0.schema.json"
    ): PILOT / "schema/markdown-document-0.1.0.schema.json",
    (
        "inputs/protocol/schema/text-artifact-0.1.0.schema.json"
    ): PILOT / "schema/text-artifact-0.1.0.schema.json",
    (
        "inputs/protocol/tools/build-role-submission-v0.1.1.py"
    ): BUILDER,
    (
        "inputs/protocol/tools/materialize-rehearsal-006-prompts.py"
    ): PILOT / "tools/materialize-rehearsal-006-prompts.py",
    (
        "inputs/protocol/tools/"
        "verify-prediction-template-contract-v0.1.1.py"
    ): PREDICTION_CHECKER,
    (
        "inputs/protocol/tools/"
        "verify-reconstruction-template-contract-v0.1.1.py"
    ): RECONSTRUCTION_CHECKER,
    (
        "inputs/protocol/tools/verify-rehearsal-006.py"
    ): PILOT / "tools/verify-rehearsal-006.py",
}

REQUIRED_FROZEN_PATHS = [
    "README.md",
    "fixtures/actors/v01.json",
    "fixtures/actors/v02.json",
    "fixtures/assembled/prediction-v01.envelope.json",
    "fixtures/assembled/prediction-v01.submission.json",
    "fixtures/assembled/prediction-v02.envelope.json",
    "fixtures/assembled/prediction-v02.submission.json",
    "fixtures/assembled/reconstruction-v01.envelope.json",
    "fixtures/assembled/reconstruction-v01.submission.json",
    "fixtures/assembled/reconstruction-v02.envelope.json",
    "fixtures/assembled/reconstruction-v02.submission.json",
    "fixtures/expected-results.json",
    "fixtures/negative/prediction-fixed-unit.template.json",
    "fixtures/negative/prediction-incomplete-alternative.payload.json",
    "fixtures/negative/reconstruction-uppercase-local-id.payload.json",
    "fixtures/positive/prediction-determinate.payload.json",
    (
        "fixtures/positive/"
        "prediction-indeterminate-two-alternatives.payload.json"
    ),
    "fixtures/positive/reconstruction-minimal.payload.json",
    "fixtures/positive/reconstruction-with-exposure.payload.json",
    "inputs/audits/prediction-contract-check.json",
    "inputs/audits/reconstruction-v01-contract-check.json",
    "inputs/audits/reconstruction-v02-contract-check.json",
    "inputs/dispatch/actor-dispatch-plan.json",
    "inputs/dispatch/stage1-v01.prompt.txt",
    "inputs/dispatch/stage1-v02.prompt.txt",
    "inputs/dispatch/stage2-neutral.prompt.txt",
    "inputs/prediction-neutral.task.json",
    "inputs/prediction-response.template.json",
    "inputs/reconstruction-condition-v01.task.json",
    "inputs/reconstruction-condition-v02.task.json",
    "inputs/reconstruction-response-v01.template.json",
    "inputs/reconstruction-response-v02.template.json",
    "inputs/variant-envelope.json",
    "inputs/view-v01.json",
    "inputs/view-v02.json",
    *ARCHIVE_MIRRORS,
]


class ReadinessError(RuntimeError):
    """Raised when rehearsal readiness cannot be established."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def repo_path(repo_root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(repo_root.resolve()):
        raise ReadinessError(f"path escapes repository root: {value}")
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r\n" in raw:
        raise ReadinessError(f"non-canonical UTF-8 JSON: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ReadinessError(f"expected JSON object: {path}")
    return value


def copy_isolated_repository(source_root: Path, target_root: Path) -> None:
    rehearsal_source = repo_path(source_root, REHEARSAL)
    rehearsal_target = target_root / REHEARSAL
    shutil.copytree(rehearsal_source, rehearsal_target)
    for relative in ISOLATION_DEPENDENCIES:
        source = repo_path(source_root, relative)
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    formal_root = target_root / PILOT / "runs"
    if formal_root.exists():
        raise ReadinessError("isolated repository unexpectedly contains runs/")


def command(
    root: Path,
    tool: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(root / tool),
            *arguments,
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def require_result(
    result: subprocess.CompletedProcess[str],
    *,
    expected_exit: int,
    contains: str | None = None,
) -> None:
    combined = result.stdout + result.stderr
    if result.returncode != expected_exit:
        raise ReadinessError(
            f"unexpected exit {result.returncode}, expected {expected_exit}: "
            f"{combined.strip()}"
        )
    if contains is not None and contains not in combined:
        raise ReadinessError(
            f"expected diagnostic {contains!r} was absent: {combined.strip()}"
        )


def common(root: Path, relative: str) -> str:
    del root
    return (REHEARSAL / relative).as_posix()


def verify_positive_fixtures(root: Path) -> None:
    fixtures = [
        {
            "task": "inputs/reconstruction-condition-v01.task.json",
            "template": "inputs/reconstruction-response-v01.template.json",
            "payload": "fixtures/positive/reconstruction-minimal.payload.json",
            "actor": "fixtures/actors/v01.json",
            "condition": "condition-v01",
            "submission_id": "submission.reconstruct.fixture.v01",
            "received_at": "2026-07-28T01:10:00Z",
            "envelope": "fixtures/assembled/reconstruction-v01.envelope.json",
            "submission": (
                "fixtures/assembled/reconstruction-v01.submission.json"
            ),
        },
        {
            "task": "inputs/reconstruction-condition-v02.task.json",
            "template": "inputs/reconstruction-response-v02.template.json",
            "payload": (
                "fixtures/positive/reconstruction-with-exposure.payload.json"
            ),
            "actor": "fixtures/actors/v02.json",
            "condition": "condition-v02",
            "submission_id": "submission.reconstruct.fixture.v02",
            "received_at": "2026-07-28T01:11:00Z",
            "envelope": "fixtures/assembled/reconstruction-v02.envelope.json",
            "submission": (
                "fixtures/assembled/reconstruction-v02.submission.json"
            ),
        },
        {
            "task": "inputs/prediction-neutral.task.json",
            "template": "inputs/prediction-response.template.json",
            "payload": "fixtures/positive/prediction-determinate.payload.json",
            "actor": "fixtures/actors/v01.json",
            "condition": "condition-v01",
            "prior": (
                "fixtures/assembled/reconstruction-v01.submission.json"
            ),
            "prior_task": "inputs/reconstruction-condition-v01.task.json",
            "submission_id": "submission.predict.fixture.v01",
            "received_at": "2026-07-28T01:12:00Z",
            "envelope": "fixtures/assembled/prediction-v01.envelope.json",
            "submission": "fixtures/assembled/prediction-v01.submission.json",
        },
        {
            "task": "inputs/prediction-neutral.task.json",
            "template": "inputs/prediction-response.template.json",
            "payload": (
                "fixtures/positive/"
                "prediction-indeterminate-two-alternatives.payload.json"
            ),
            "actor": "fixtures/actors/v02.json",
            "condition": "condition-v02",
            "prior": (
                "fixtures/assembled/reconstruction-v02.submission.json"
            ),
            "prior_task": "inputs/reconstruction-condition-v02.task.json",
            "submission_id": "submission.predict.fixture.v02",
            "received_at": "2026-07-28T01:14:00Z",
            "envelope": "fixtures/assembled/prediction-v02.envelope.json",
            "submission": "fixtures/assembled/prediction-v02.submission.json",
        },
    ]
    for fixture in fixtures:
        arguments = [
            "verify",
            "--repo-root",
            str(root),
            "--task",
            common(root, fixture["task"]),
            "--template",
            common(root, fixture["template"]),
            "--payload",
            common(root, fixture["payload"]),
            "--actor",
            common(root, fixture["actor"]),
            "--condition-id",
            fixture["condition"],
            "--submission-id",
            fixture["submission_id"],
            "--received-at",
            fixture["received_at"],
            "--envelope",
            common(root, fixture["envelope"]),
            "--submission",
            common(root, fixture["submission"]),
        ]
        if "prior" in fixture:
            arguments.extend(
                [
                    "--prior-stage-submission",
                    common(root, fixture["prior"]),
                    "--prior-stage-task",
                    common(root, fixture["prior_task"]),
                ]
            )
        require_result(
            command(root, BUILDER, *arguments),
            expected_exit=0,
        )


def verify_contract_checks(root: Path) -> None:
    prompts = command(
        root,
        PROMPT_GENERATOR,
        "verify",
        "--repo-root",
        str(root),
        "--created-at",
        "2026-07-28T02:12:00Z",
    )
    require_result(prompts, expected_exit=0)

    prediction = command(
        root,
        PREDICTION_CHECKER,
        "verify",
        "--repo-root",
        str(root),
        "--task",
        common(root, "inputs/prediction-neutral.task.json"),
        "--template",
        common(root, "inputs/prediction-response.template.json"),
    )
    require_result(prediction, expected_exit=0)
    for condition in ("v01", "v02"):
        reconstruction = command(
            root,
            RECONSTRUCTION_CHECKER,
            "verify",
            "--repo-root",
            str(root),
            "--task",
            common(
                root,
                f"inputs/reconstruction-condition-{condition}.task.json",
            ),
            "--template",
            common(
                root,
                f"inputs/reconstruction-response-{condition}.template.json",
            ),
        )
        require_result(reconstruction, expected_exit=0)
    for relative in (
        "inputs/prediction-response.template.json",
        "inputs/reconstruction-response-v01.template.json",
        "inputs/reconstruction-response-v02.template.json",
    ):
        template = read_json(root / REHEARSAL / relative)
        if (
            template.get("participant_contract", {}).get(
                "local_id_pattern"
            )
            != "^[a-z0-9][a-z0-9._-]*$"
        ):
            raise ReadinessError(
                f"participant material omits local_id_pattern: {relative}"
            )


def verify_negative_fixtures(root: Path) -> None:
    condition_mismatch = command(
        root,
        BUILDER,
        "validate-payload",
        "--repo-root",
        str(root),
        "--task",
        common(root, "inputs/reconstruction-condition-v01.task.json"),
        "--template",
        common(root, "inputs/reconstruction-response-v01.template.json"),
        "--payload",
        common(root, "fixtures/positive/reconstruction-minimal.payload.json"),
        "--actor",
        common(root, "fixtures/actors/v01.json"),
        "--condition-id",
        "condition-v02",
    )
    require_result(
        condition_mismatch,
        expected_exit=1,
        contains="does not match the requested condition",
    )

    uppercase = command(
        root,
        BUILDER,
        "validate-payload",
        "--repo-root",
        str(root),
        "--task",
        common(root, "inputs/reconstruction-condition-v01.task.json"),
        "--template",
        common(root, "inputs/reconstruction-response-v01.template.json"),
        "--payload",
        common(
            root,
            "fixtures/negative/reconstruction-uppercase-local-id.payload.json",
        ),
        "--actor",
        common(root, "fixtures/actors/v01.json"),
        "--condition-id",
        "condition-v01",
    )
    require_result(
        uppercase,
        expected_exit=1,
        contains="does not match",
    )

    incomplete = command(
        root,
        BUILDER,
        "validate-payload",
        "--repo-root",
        str(root),
        "--task",
        common(root, "inputs/prediction-neutral.task.json"),
        "--template",
        common(root, "inputs/prediction-response.template.json"),
        "--payload",
        common(
            root,
            "fixtures/negative/prediction-incomplete-alternative.payload.json",
        ),
        "--actor",
        common(root, "fixtures/actors/v02.json"),
        "--condition-id",
        "condition-v02",
        "--prior-stage-submission",
        common(
            root,
            "fixtures/assembled/reconstruction-v02.submission.json",
        ),
        "--prior-stage-task",
        common(root, "inputs/reconstruction-condition-v02.task.json"),
    )
    require_result(
        incomplete,
        expected_exit=1,
        contains="must cover each configuration/observation pair",
    )

    fixed_unit = command(
        root,
        PREDICTION_CHECKER,
        "verify",
        "--repo-root",
        str(root),
        "--task",
        common(root, "inputs/prediction-neutral.task.json"),
        "--template",
        common(
            root,
            "fixtures/negative/prediction-fixed-unit.template.json",
        ),
    )
    require_result(
        fixed_unit,
        expected_exit=1,
        contains="value/unit",
    )


def scan_rehearsal_references(repo_root: Path) -> None:
    rehearsal_root = repo_path(repo_root, REHEARSAL)
    forbidden = []
    candidates = [
        *(
            path
            for path in (rehearsal_root / "inputs").rglob("*.json")
            if "protocol" not in path.relative_to(
                rehearsal_root / "inputs"
            ).parts
        ),
        *(rehearsal_root / "fixtures").rglob("*.json"),
    ]
    for path in candidates:
        raw = path.read_bytes()
        if b"/runs/" in raw or b"\\runs\\" in raw:
            forbidden.append(path.relative_to(rehearsal_root).as_posix())
    if forbidden:
        raise ReadinessError(
            "rehearsal material references a formal run: "
            + ", ".join(forbidden)
        )


def verify_manifest(repo_root: Path, manifest_path: Path) -> None:
    manifest = read_json(manifest_path)
    if (
        manifest.get("run_id") != "rehearsal-006"
        or manifest.get("stage") != "preparation"
    ):
        raise ReadinessError("manifest is not rehearsal-006 preparation")
    entries = {
        item["path"]: item
        for item in manifest.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("path"), str)
    }
    missing = [
        path
        for path in REQUIRED_FROZEN_PATHS
        if path not in entries
        or entries[path].get("included_in_frozen_set") is not True
    ]
    if missing:
        raise ReadinessError(
            "manifest omits required frozen paths: " + ", ".join(missing)
        )
    rehearsal_root = repo_path(repo_root, REHEARSAL)
    for relative in REQUIRED_FROZEN_PATHS:
        artifact = rehearsal_root / relative
        if sha256(artifact.read_bytes()) != entries[relative].get("sha256"):
            raise ReadinessError(
                f"manifest artifact hash differs: {relative}"
            )
        schema = repo_path(repo_root, entries[relative]["schema_path"])
        if sha256(schema.read_bytes()) != entries[relative].get(
            "schema_sha256"
        ):
            raise ReadinessError(
                f"manifest Schema binding differs: {relative}"
            )
    for archive_relative, source_relative in ARCHIVE_MIRRORS.items():
        archived = rehearsal_root / archive_relative
        source = repo_path(repo_root, source_relative)
        if archived.read_bytes() != source.read_bytes():
            raise ReadinessError(
                f"frozen protocol mirror differs: {archive_relative}"
            )
def validate_expectations(repo_root: Path) -> None:
    expectations = read_json(repo_path(repo_root, EXPECTATIONS))
    expected_pairs = {
        (
            item["fixture"],
            item["expected"],
            item.get("failure_contains"),
        )
        for item in expectations.get("checks", [])
    }
    required_pairs = {
        ("positive/reconstruction-minimal.payload.json", "pass", None),
        ("positive/reconstruction-with-exposure.payload.json", "pass", None),
        ("positive/prediction-determinate.payload.json", "pass", None),
        (
            "positive/prediction-indeterminate-two-alternatives.payload.json",
            "pass",
            None,
        ),
        (
            "negative/reconstruction-uppercase-local-id.payload.json",
            "fail",
            "does not match",
        ),
        (
            "negative/prediction-incomplete-alternative.payload.json",
            "fail",
            "must cover each configuration/observation pair",
        ),
        (
            "negative/prediction-fixed-unit.template.json",
            "fail",
            "value/unit",
        ),
    }
    if expected_pairs != required_pairs:
        raise ReadinessError("fixture expectation matrix has drifted")


def build_result(
    repo_root: Path,
    manifest_path: Path,
    *,
    assessed_at: str,
    verify_manifest_closure: bool = True,
) -> dict[str, Any]:
    validate_expectations(repo_root)
    scan_rehearsal_references(repo_root)
    with tempfile.TemporaryDirectory(prefix="gp-rehearsal-006-") as raw:
        isolated_root = Path(raw)
        copy_isolated_repository(repo_root, isolated_root)
        verify_contract_checks(isolated_root)
        verify_positive_fixtures(isolated_root)
        verify_negative_fixtures(isolated_root)
        if (isolated_root / PILOT / "runs").exists():
            raise ReadinessError("formal run directory appeared during checks")
    if verify_manifest_closure:
        verify_manifest(repo_root, manifest_path)

    result = {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "participant-interface-readiness-0.1.0.schema.json"
        ),
        "artifact_type": "participant_interface_readiness",
        "artifact_version": "0.1.0",
        "assessed_at": assessed_at,
        "checks": [
            {
                "acceptance_condition": 1,
                "check_id": "fixture.reconstruction-minimal",
                "evidence": [
                    "isolated deterministic assembly verification passed"
                ],
                "status": "passed",
            },
            {
                "acceptance_condition": 2,
                "check_id": "fixture.reconstruction-exposure",
                "evidence": [
                    "nonempty integrity_exposures payload passed"
                ],
                "status": "passed",
            },
            {
                "acceptance_condition": 3,
                "check_id": "negative.uppercase-local-id",
                "evidence": [
                    "uppercase fact_id rejected with visible local_id_pattern"
                ],
                "status": "passed",
            },
            {
                "acceptance_condition": 4,
                "check_id": "fixture.prediction-determinate",
                "evidence": [
                    "determinate prediction branch assembled and verified"
                ],
                "status": "passed",
            },
            {
                "acceptance_condition": 5,
                "check_id": "fixture.prediction-indeterminate",
                "evidence": [
                    "indeterminate status tuple assembled and verified"
                ],
                "status": "passed",
            },
            {
                "acceptance_condition": 6,
                "check_id": "fixture.two-complete-alternatives",
                "evidence": [
                    "two distinct complete cartesian alternatives passed"
                ],
                "status": "passed",
            },
            {
                "acceptance_condition": 7,
                "check_id": "negative.fixed-dimensional-unit",
                "evidence": [
                    "legacy fixed-unit template rejected at value/unit"
                ],
                "status": "passed",
            },
            {
                "acceptance_condition": 9,
                "check_id": "isolation.no-formal-input",
                "evidence": [
                    "all dynamic checks passed in a repository copy without runs/"
                ],
                "status": "passed",
            },
            {
                "acceptance_condition": 10,
                "check_id": "freeze.participant-contract-closure",
                "evidence": [
                    "manifest freezes templates, contract checks, Schemas, and verifiers",
                    "archived protocol bytes equal the live versioned files",
                ],
                "status": "passed",
            },
        ],
        "deferred_acceptance_conditions": [8],
        "fixture_expectations_sha256": sha256(
            repo_path(repo_root, EXPECTATIONS).read_bytes()
        ),
        "formal_input_access": False,
        "isolated_repository_check": "passed",
        "isolation_evidence": {
            "command_count": 12,
            "disallowed_path_references": [],
            "executed_tool_paths": [
                BUILDER.as_posix(),
                PROMPT_GENERATOR.as_posix(),
                PREDICTION_CHECKER.as_posix(),
                RECONSTRUCTION_CHECKER.as_posix(),
            ],
            "formal_run_directory_present": False,
            "mirror_kind": "temporary_allowlisted_repository_copy",
        },
        "manifest_missing_required_paths": [],
        "manifest_path": (
            "research/calibration-tests/continuous-action-pilot/"
            "rehearsals/rehearsal-006/manifest.json"
        ),
        "protocol_version": "0.1.1",
        "required_frozen_paths": REQUIRED_FROZEN_PATHS,
        "run_id": "rehearsal-006",
        "scope": "pre_dispatch_acceptance_conditions_1_7_9_10",
        "status": "passed",
    }
    schema = read_json(repo_path(repo_root, READINESS_SCHEMA))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(result),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    if errors:
        raise ReadinessError(
            "readiness result failed its Schema: "
            + "; ".join(error.message for error in errors)
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--assessed-at", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-output", type=Path)
    parser.add_argument(
        "--bootstrap-without-manifest",
        action="store_true",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        manifest_path = repo_path(repo_root, args.manifest)
        result = build_result(
            repo_root,
            manifest_path,
            assessed_at=args.assessed_at,
            verify_manifest_closure=(
                not args.bootstrap_without_manifest
            ),
        )
        raw = canonical_bytes(result)
        if args.output is not None and args.verify_output is not None:
            raise ReadinessError(
                "--output and --verify-output are mutually exclusive"
            )
        if args.bootstrap_without_manifest and args.output is None:
            raise ReadinessError(
                "--bootstrap-without-manifest requires --output"
            )
        if args.verify_output is not None:
            if args.bootstrap_without_manifest:
                raise ReadinessError(
                    "bootstrap mode cannot verify final evidence"
                )
            existing = repo_path(repo_root, args.verify_output)
            if existing.read_bytes() != raw:
                raise ReadinessError(
                    f"readiness evidence differs: {existing}"
                )
            print(
                json.dumps(
                    {
                        "artifact": (
                            existing.relative_to(repo_root).as_posix()
                        ),
                        "sha256": sha256(raw),
                        "status": "verified",
                    },
                    sort_keys=True,
                )
            )
            return 0
        if args.output is not None:
            output = repo_path(repo_root, args.output)
            if output.exists():
                raise ReadinessError(
                    f"refusing to overwrite readiness evidence: {output}"
                )
            if not output.parent.is_dir():
                raise ReadinessError(
                    f"output directory does not exist: {output.parent}"
                )
            output.write_bytes(raw)
            print(
                json.dumps(
                    {
                        "artifact": output.relative_to(repo_root).as_posix(),
                        "sha256": sha256(raw),
                        "status": (
                            "bootstrap_rendered_unverified_manifest"
                            if args.bootstrap_without_manifest
                            else "passed"
                        ),
                    },
                    sort_keys=True,
                )
            )
        else:
            print(raw.decode("utf-8"), end="")
        return 0
    except (
        json.JSONDecodeError,
        OSError,
        ReadinessError,
        subprocess.SubprocessError,
    ) as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "status": "failed_closed",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
