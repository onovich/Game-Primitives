#!/usr/bin/env python3
"""Fail closed when a prediction template cannot express every allowed branch."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


class ContractError(RuntimeError):
    """Raised when the static prediction-template contract is invalid."""


CHECK_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "prediction-template-contract-check-0.1.0.schema.json"
)


def read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r\n" in raw:
        raise ContractError(f"non-canonical UTF-8 JSON: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ContractError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_path(repo_root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def is_placeholder(value: Any) -> bool:
    return (
        isinstance(value, str)
        and value.startswith("<")
        and value.endswith(">")
    )


def unit_schema_accepts_null_only(response_schema: dict[str, Any]) -> bool:
    try:
        unit_schema = response_schema["$defs"]["indeterminateExpectation"][
            "properties"
        ]["value"]["properties"]["unit"]
    except (KeyError, TypeError) as exc:
        raise ContractError(
            "response schema has no indeterminateExpectation unit contract"
        ) from exc
    return unit_schema == {"type": "null"}


def declared_observations(
    task: dict[str, Any],
) -> tuple[dict[str, str | None], dict[str, list[str]]]:
    units: dict[str, str | None] = {}
    for item in task.get("allowed_observations", []):
        if not isinstance(item, dict):
            raise ContractError("allowed_observations must contain objects")
        observation_id = item.get("observation_id")
        unit = item.get("unit")
        if not isinstance(observation_id, str):
            raise ContractError("observation_id must be a string")
        if unit is not None and not isinstance(unit, str):
            raise ContractError(f"invalid unit for {observation_id}")
        if observation_id in units:
            raise ContractError(f"duplicate observation_id: {observation_id}")
        units[observation_id] = unit

    by_case: dict[str, list[str]] = {}
    for intervention in task.get("variant_interventions", []):
        if not isinstance(intervention, dict):
            raise ContractError("variant_interventions must contain objects")
        case_id = intervention.get("case_id")
        observation_ids = intervention.get("observation_ids")
        if not isinstance(case_id, str) or not isinstance(
            observation_ids, list
        ):
            raise ContractError("invalid intervention observation mapping")
        if case_id in by_case:
            raise ContractError(f"duplicate intervention case: {case_id}")
        if any(item not in units for item in observation_ids):
            raise ContractError(
                f"{case_id} references an undeclared observation"
            )
        by_case[case_id] = list(observation_ids)
    return units, by_case


def expectation_product(
    expectations: Any,
    *,
    case_id: str,
    configurations: list[str],
    observation_ids: list[str],
    location: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    if not isinstance(expectations, list):
        return [], [
            {
                "path": location,
                "problem": "expectations must be an array",
            }
        ]
    objects = [item for item in expectations if isinstance(item, dict)]
    expected = {
        (configuration_id, observation_id)
        for configuration_id in configurations
        for observation_id in observation_ids
    }
    actual = [
        (item.get("configuration_id"), item.get("observation_id"))
        for item in objects
    ]
    if len(objects) != len(expectations):
        issues.append(
            {
                "path": location,
                "problem": "expectations contains a non-object item",
            }
        )
    if len(actual) != len(set(actual)):
        issues.append(
            {
                "path": location,
                "problem": "configuration-observation pairs are not unique",
            }
        )
    if set(actual) != expected:
        issues.append(
            {
                "path": location,
                "problem": (
                    f"{case_id} does not contain the exact configuration-"
                    "observation Cartesian product"
                ),
            }
        )
    return objects, issues


def verify_contract(
    task: dict[str, Any],
    template: dict[str, Any],
    response_schema: dict[str, Any],
    *,
    response_schema_sha256: str,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if task.get("artifact_type") != "prediction_task_packet":
        raise ContractError("task is not a prediction_task_packet")
    if (
        template.get("artifact_type") != "prediction_response_template"
        or template.get("stage") != "prediction"
    ):
        raise ContractError("template is not a prediction response template")

    target = template.get("target_response_schema")
    if not isinstance(target, dict):
        raise ContractError("template has no target_response_schema")
    if target.get("sha256") != response_schema_sha256:
        issues.append(
            {
                "path": "target_response_schema/sha256",
                "problem": "template is not bound to the supplied Schema bytes",
            }
        )
    payload = template.get("template_payload")
    if not isinstance(payload, dict):
        raise ContractError("template_payload must be an object")
    if payload.get("$schema") != response_schema.get("$id"):
        issues.append(
            {
                "path": "template_payload/$schema",
                "problem": "payload Schema ID differs from the supplied Schema",
            }
        )

    configurations = task.get("allowed_configurations")
    if not isinstance(configurations, list) or not all(
        isinstance(item, str) for item in configurations
    ):
        raise ContractError("allowed_configurations must be a string array")
    units, observations_by_case = declared_observations(task)
    answers = payload.get("prediction_answers")
    if not isinstance(answers, list):
        raise ContractError("prediction_answers must be an array")
    answer_map = {
        answer.get("case_id"): answer
        for answer in answers
        if isinstance(answer, dict)
    }
    if set(answer_map) != set(observations_by_case):
        issues.append(
            {
                "path": "template_payload/prediction_answers",
                "problem": "answer cases differ from intervention cases",
            }
        )

    null_only = unit_schema_accepts_null_only(response_schema)
    instruction_text = "\n".join(
        item for item in task.get("instructions", []) if isinstance(item, str)
    ).lower()
    if null_only and not (
        "indeterminate" in instruction_text
        and "unit" in instruction_text
        and "null" in instruction_text
    ):
        issues.append(
            {
                "path": "task/instructions",
                "problem": (
                    "Schema requires unit=null for indeterminate expectations, "
                    "but the participant instructions do not state that rule"
                ),
            }
        )

    for case_id, observation_ids in observations_by_case.items():
        answer = answer_map.get(case_id)
        if not isinstance(answer, dict):
            continue
        main, product_issues = expectation_product(
            answer.get("expectations"),
            case_id=case_id,
            configurations=configurations,
            observation_ids=observation_ids,
            location=f"template_payload/{case_id}/expectations",
        )
        issues.extend(product_issues)
        for index, expectation in enumerate(main):
            observation_id = expectation.get("observation_id")
            declared_unit = units.get(observation_id)
            unit = expectation.get("value", {}).get("unit")
            path = (
                f"template_payload/{case_id}/expectations/{index}/value/unit"
            )
            if declared_unit is None:
                if unit is not None:
                    issues.append(
                        {
                            "path": path,
                            "problem": "unitless observation must keep unit=null",
                        }
                    )
            elif null_only:
                if not (
                    is_placeholder(unit)
                    and "null" in unit.lower()
                    and declared_unit in unit
                ):
                    issues.append(
                        {
                            "path": path,
                            "problem": (
                                "fixed measurement unit makes the Schema-valid "
                                "indeterminate branch unreachable; use a "
                                f"placeholder containing null and {declared_unit}"
                            ),
                        }
                    )

        alternatives = answer.get("compatible_alternatives")
        if not isinstance(alternatives, list):
            issues.append(
                {
                    "path": (
                        f"template_payload/{case_id}/compatible_alternatives"
                    ),
                    "problem": "compatible_alternatives must be an array",
                }
            )
            continue
        for alternative_index, alternative in enumerate(alternatives):
            if not isinstance(alternative, dict):
                issues.append(
                    {
                        "path": (
                            f"template_payload/{case_id}/"
                            f"compatible_alternatives/{alternative_index}"
                        ),
                        "problem": "alternative must be an object",
                    }
                )
                continue
            child, child_issues = expectation_product(
                alternative.get("expectations"),
                case_id=case_id,
                configurations=configurations,
                observation_ids=observation_ids,
                location=(
                    f"template_payload/{case_id}/compatible_alternatives/"
                    f"{alternative_index}/expectations"
                ),
            )
            issues.extend(child_issues)
            for expectation_index, expectation in enumerate(child):
                observation_id = expectation.get("observation_id")
                if observation_id not in units:
                    continue
                actual_unit = expectation.get("value", {}).get("unit")
                if actual_unit != units[observation_id]:
                    issues.append(
                        {
                            "path": (
                                f"template_payload/{case_id}/"
                                f"compatible_alternatives/{alternative_index}/"
                                f"expectations/{expectation_index}/value/unit"
                            ),
                            "problem": (
                                "alternative must retain the declared "
                                "observation unit"
                            ),
                        }
                    )
    return issues


def command_verify(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    task_path = repo_path(repo_root, args.task)
    template_path = repo_path(repo_root, args.template)
    response_schema_path = repo_path(repo_root, args.response_schema)
    issues = verify_contract(
        read_json(task_path),
        read_json(template_path),
        read_json(response_schema_path),
        response_schema_sha256=sha256(response_schema_path),
    )
    result = {
        "$schema": CHECK_SCHEMA_ID,
        "artifact_type": "prediction_template_contract_check",
        "artifact_version": "0.1.0",
        "issue_count": len(issues),
        "issues": issues,
        "response_schema_sha256": sha256(response_schema_path),
        "status": "failed" if issues else "passed",
        "task_sha256": sha256(task_path),
        "template_sha256": sha256(template_path),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if issues else 0


def synthetic_documents() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any]
]:
    response_schema = {
        "$id": "urn:synthetic:blind-response",
        "$defs": {
            "indeterminateExpectation": {
                "properties": {
                    "value": {
                        "properties": {
                            "unit": {
                                "type": "null",
                            }
                        }
                    }
                }
            }
        },
    }
    task = {
        "allowed_configurations": [
            "config.baseline",
            "config.variant",
        ],
        "allowed_observations": [
            {
                "observation_id": "obs.a.0001",
                "unit": "count",
            }
        ],
        "artifact_type": "prediction_task_packet",
        "instructions": [
            "If prediction_status is indeterminate, use "
            "status/indeterminate and set unit=null."
        ],
        "variant_interventions": [
            {
                "case_id": "CA-R1",
                "observation_ids": [
                    "obs.a.0001",
                ],
            }
        ],
    }
    expectation = {
        "configuration_id": "config.baseline",
        "expectation_kind": "<exact|status>",
        "observation_id": "obs.a.0001",
        "tolerance_rule_id": "tol.a.0001",
        "value": {
            "serialized_value": "<required-string>",
            "unit": "<null|count>",
            "value_type": "<integer|status>",
        },
    }
    variant_expectation = copy.deepcopy(expectation)
    variant_expectation["configuration_id"] = "config.variant"
    alternative_expectation = copy.deepcopy(expectation)
    alternative_expectation["expectation_kind"] = "exact"
    alternative_expectation["value"] = {
        "serialized_value": "<required-string>",
        "unit": "count",
        "value_type": "integer",
    }
    alternative_variant = copy.deepcopy(alternative_expectation)
    alternative_variant["configuration_id"] = "config.variant"
    template = {
        "artifact_type": "prediction_response_template",
        "stage": "prediction",
        "target_response_schema": {
            "sha256": "0" * 64,
        },
        "template_payload": {
            "$schema": response_schema["$id"],
            "prediction_answers": [
                {
                    "case_id": "CA-R1",
                    "compatible_alternatives": [
                        {
                            "alternative_id": "<required-local-id>",
                            "expectations": [
                                copy.deepcopy(alternative_expectation),
                                copy.deepcopy(alternative_variant),
                            ],
                        },
                        {
                            "alternative_id": "<required-local-id>",
                            "expectations": [
                                copy.deepcopy(alternative_expectation),
                                copy.deepcopy(alternative_variant),
                            ],
                        },
                    ],
                    "expectations": [
                        expectation,
                        variant_expectation,
                    ],
                }
            ],
        },
    }
    return task, template, response_schema


def command_self_test(_: argparse.Namespace) -> int:
    task, template, response_schema = synthetic_documents()
    good = verify_contract(
        task,
        template,
        response_schema,
        response_schema_sha256="0" * 64,
    )
    if good:
        raise ContractError(f"synthetic valid contract failed: {good}")

    bad_template = copy.deepcopy(template)
    for expectation in bad_template["template_payload"][
        "prediction_answers"
    ][0]["expectations"]:
        expectation["value"]["unit"] = "count"
    bad = verify_contract(
        task,
        bad_template,
        response_schema,
        response_schema_sha256="0" * 64,
    )
    if len(
        [
            item
            for item in bad
            if "indeterminate branch unreachable" in item["problem"]
        ]
    ) != 2:
        raise ContractError("synthetic fixed-unit defect was not detected")

    bad_task = copy.deepcopy(task)
    bad_task["instructions"] = [
        "Return a prediction object.",
    ]
    missing_instruction = verify_contract(
        bad_task,
        template,
        response_schema,
        response_schema_sha256="0" * 64,
    )
    if not any(
        item["path"] == "task/instructions"
        for item in missing_instruction
    ):
        raise ContractError("missing unit=null instruction was not detected")
    print(
        json.dumps(
            {
                "status": "self_test_passed",
                "synthetic_bad_fixed_unit_issues": 2,
                "synthetic_good_issue_count": 0,
            },
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    subparsers = value.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--task", required=True)
    verify.add_argument("--template", required=True)
    verify.add_argument("--response-schema", required=True)
    verify.set_defaults(func=command_verify)
    self_test = subparsers.add_parser("self-test")
    self_test.set_defaults(func=command_self_test)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (ContractError, KeyError, TypeError, ValueError) as exc:
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
