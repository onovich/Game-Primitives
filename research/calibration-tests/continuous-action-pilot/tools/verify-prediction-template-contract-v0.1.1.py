#!/usr/bin/env python3
"""Verify branch closure and participant constructability for protocol 0.1.1."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


class ContractError(RuntimeError):
    """Raised when a prediction-template contract cannot be verified."""


CHECK_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "prediction-template-contract-check-0.1.1.schema.json"
)
CHECK_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "prediction-template-contract-check-0.1.1.schema.json"
)
PARTICIPANT_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "prediction-participant-response-contract-0.1.1.schema.json"
)
RESPONSE_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "blind-response-interface-0.1.1.schema.json"
)
ROLE_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "role-submission-0.1.1.schema.json"
)
TEMPLATE_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "response-template-0.1.1.schema.json"
)
VALUE_TYPE_ORDER = (
    "boolean",
    "decimal",
    "direction",
    "id",
    "id_set",
    "integer",
    "rational",
    "status",
    "string",
)
KIND_BY_VALUE_TYPE = {
    "boolean": "exact",
    "decimal": "exact",
    "direction": "direction",
    "id": "exact",
    "id_set": "set",
    "integer": "exact",
    "rational": "exact",
    "string": "exact",
}


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
    resolved = candidate.resolve()
    if not resolved.is_relative_to(repo_root.resolve()):
        raise ContractError(f"path escapes repository root: {value}")
    return resolved


def schema_errors(
    instance: dict[str, Any],
    schema: dict[str, Any],
    *,
    registry: Registry | None = None,
) -> list[str]:
    validator = Draft202012Validator(
        schema,
        registry=registry if registry is not None else Registry(),
        format_checker=FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: [str(part) for part in error.absolute_path],
    )
    result: list[str] = []
    for error in errors:
        location = "/".join(
            str(part) for part in error.absolute_path
        ) or "<root>"
        result.append(f"{location}: {error.message}")
    return result


def ordered_values(values: list[str]) -> list[str]:
    unknown = set(values) - set(VALUE_TYPE_ORDER)
    if unknown:
        raise ContractError(f"unknown value types: {sorted(unknown)}")
    return [value for value in VALUE_TYPE_ORDER if value in values]


def placeholder(values: list[str]) -> str:
    if not values:
        raise ContractError("cannot construct an empty choice placeholder")
    return "<" + "|".join(values) + ">"


def definition_required(
    response_schema: dict[str, Any],
    role_schema: dict[str, Any],
    definition_name: str,
) -> list[str]:
    response_definition = response_schema.get("$defs", {}).get(
        definition_name
    )
    source = (
        response_schema
        if isinstance(response_definition, dict)
        and "required" in response_definition
        else role_schema
    )
    try:
        required = source["$defs"][definition_name]["required"]
    except (KeyError, TypeError) as exc:
        raise ContractError(
            f"missing required-field contract for {definition_name}"
        ) from exc
    if not isinstance(required, list) or not all(
        isinstance(item, str) for item in required
    ):
        raise ContractError(
            f"invalid required-field contract for {definition_name}"
        )
    return list(required)


def resolved_enum(
    role_schema: dict[str, Any],
    definition_name: str,
    property_name: str,
) -> list[str]:
    try:
        rule = role_schema["$defs"][definition_name]["properties"][
            property_name
        ]
    except (KeyError, TypeError) as exc:
        raise ContractError(
            f"missing enum source {definition_name}.{property_name}"
        ) from exc
    if "$ref" in rule:
        ref = rule["$ref"]
        prefix = "#/$defs/"
        if not isinstance(ref, str) or not ref.startswith(prefix):
            raise ContractError(f"unsupported local enum reference: {ref}")
        rule = role_schema["$defs"][ref[len(prefix) :]]
    values = rule.get("enum")
    if not isinstance(values, list) or not all(
        isinstance(item, str) for item in values
    ):
        raise ContractError(
            f"{definition_name}.{property_name} is not a string enum"
        )
    return list(values)


def declared_observations(
    task: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, list[str]]]:
    observations: dict[str, dict[str, Any]] = {}
    for item in task.get("allowed_observations", []):
        if not isinstance(item, dict):
            raise ContractError("allowed_observations must contain objects")
        observation_id = item.get("observation_id")
        if not isinstance(observation_id, str):
            raise ContractError("observation_id must be a string")
        if observation_id in observations:
            raise ContractError(f"duplicate observation_id: {observation_id}")
        allowed = item.get("allowed_value_types")
        if not isinstance(allowed, list) or not all(
            isinstance(value, str) for value in allowed
        ):
            raise ContractError(
                f"{observation_id} has no allowed_value_types"
            )
        if "status" not in allowed:
            raise ContractError(
                f"{observation_id} does not expose the status branch"
            )
        if not [value for value in allowed if value != "status"]:
            raise ContractError(
                f"{observation_id} has no determinate value type"
            )
        unit = item.get("unit")
        if unit is not None and not isinstance(unit, str):
            raise ContractError(f"invalid unit for {observation_id}")
        tolerance = item.get("tolerance_rule_id")
        if tolerance is not None and not isinstance(tolerance, str):
            raise ContractError(
                f"invalid tolerance_rule_id for {observation_id}"
            )
        observations[observation_id] = item

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
        if not observation_ids or not all(
            isinstance(item, str) for item in observation_ids
        ):
            raise ContractError(f"{case_id} has no observation mapping")
        if any(item not in observations for item in observation_ids):
            raise ContractError(
                f"{case_id} references an undeclared observation"
            )
        if len(observation_ids) != len(set(observation_ids)):
            raise ContractError(
                f"{case_id} contains duplicate observation IDs"
            )
        by_case[case_id] = list(observation_ids)
    if not by_case:
        raise ContractError("task has no variant intervention")
    return observations, by_case


def derive_participant_contract(
    task: dict[str, Any],
    response_schema: dict[str, Any],
    role_schema: dict[str, Any],
    *,
    response_schema_sha256: str,
    role_schema_sha256: str,
) -> dict[str, Any]:
    observations, by_case = declared_observations(task)
    try:
        local_id_pattern = role_schema["$defs"]["localId"]["pattern"]
        integrity_shape = role_schema["$defs"]["integrityExposure"]
    except (KeyError, TypeError) as exc:
        raise ContractError(
            "role schema does not expose local ID and integrity contracts"
        ) from exc
    if not isinstance(local_id_pattern, str) or not isinstance(
        integrity_shape, dict
    ):
        raise ContractError("invalid role schema participant contract")

    observation_rules: list[dict[str, Any]] = []
    for case_id, observation_ids in by_case.items():
        for observation_id in observation_ids:
            observation = observations[observation_id]
            allowed = ordered_values(
                list(dict.fromkeys(observation["allowed_value_types"]))
            )
            determinate = [
                value for value in allowed if value != "status"
            ]
            unit = observation["unit"]
            observation_rules.append(
                {
                    "allowed_value_types": allowed,
                    "case_id": case_id,
                    "compatible_alternative_unit": unit,
                    "declared_unit": unit,
                    "determinate_value_types": determinate,
                    "main_unit_options": (
                        [None] if unit is None else [None, unit]
                    ),
                    "observation_id": observation_id,
                    "tolerance_rule_id": observation[
                        "tolerance_rule_id"
                    ],
                }
            )

    return {
        "artifact_type": "prediction_participant_response_contract",
        "artifact_version": "0.1.1",
        "cartesian_product_rule": {
            "applies_to": [
                "main_expectations",
                "each_compatible_alternative",
            ],
            "case_observations": [
                {
                    "case_id": case_id,
                    "observation_ids": observation_ids,
                }
                for case_id, observation_ids in by_case.items()
            ],
            "configuration_ids": list(task["allowed_configurations"]),
            "indeterminate_minimum_alternatives": 2,
            "pair_occurrence": "exactly_once",
        },
        "confidence_percent_rule": {
            "maximum": 100,
            "minimum": 0,
            "template_slot": "<integer-0-100>",
            "type": "integer",
        },
        "integrity_exposure_item_shape": copy.deepcopy(integrity_shape),
        "local_id_pattern": local_id_pattern,
        "observation_rules": observation_rules,
        "pollution_enums": {
            "exact_result_knowledge": resolved_enum(
                role_schema, "familiarity", "exact_result_knowledge"
            ),
            "exact_rule_knowledge": resolved_enum(
                role_schema, "familiarity", "exact_rule_knowledge"
            ),
            "exact_variant_knowledge": resolved_enum(
                role_schema, "familiarity", "exact_variant_knowledge"
            ),
            "integrity_exposure_type": resolved_enum(
                role_schema, "integrityExposure", "exposure_type"
            ),
            "integrity_stage": resolved_enum(
                role_schema, "integrityExposure", "stage"
            ),
            "integrity_status": resolved_enum(
                role_schema, "integrityExposure", "status"
            ),
            "project_exposure": resolved_enum(
                role_schema, "familiarity", "project_exposure"
            ),
            "recognition_status": resolved_enum(
                role_schema, "familiarity", "recognition_status"
            ),
            "related_genre_experience": resolved_enum(
                role_schema, "familiarity", "related_genre_experience"
            ),
        },
        "prediction_branch_rules": {
            "determinate": {
                "compatible_alternatives_action": (
                    "clear_or_retain_complete_concrete_alternatives"
                ),
                "expectation_kind_rule": (
                    "match_selected_determinate_value_type"
                ),
                "prediction_status": "determinate",
                "unit_rule": "use_declared_observation_unit",
                "value_type_rule": (
                    "select_allowed_non_status_value_type"
                ),
            },
            "indeterminate": {
                "compatible_alternatives_action": (
                    "retain_at_least_two_complete_concrete_alternatives"
                ),
                "expectation_kind": "status",
                "prediction_status": "indeterminate",
                "serialized_value": "indeterminate",
                "unit": None,
                "value_type": "status",
            },
        },
        "required_fields_by_stage": {
            "compatible_branch": definition_required(
                response_schema, role_schema, "compatibleBranch"
            ),
            "familiarity": definition_required(
                response_schema, role_schema, "familiarity"
            ),
            "integrity_exposure": definition_required(
                response_schema, role_schema, "integrityExposure"
            ),
            "pollution": definition_required(
                response_schema, role_schema, "pollution"
            ),
            "prediction_answer": definition_required(
                response_schema, role_schema, "predictionAnswer"
            ),
            "prediction_alternative": definition_required(
                response_schema, role_schema, "predictionAlternative"
            ),
            "prediction_expectation": definition_required(
                response_schema, role_schema, "predictionExpectation"
            ),
            "prediction_payload": definition_required(
                response_schema, role_schema, "predictionPayload"
            ),
            "reconstruction_answer": definition_required(
                response_schema, role_schema, "reconstructionAnswer"
            ),
            "reconstruction_payload": definition_required(
                response_schema, role_schema, "reconstructionPayload"
            ),
            "recovered_fact": definition_required(
                response_schema, role_schema, "recoveredFact"
            ),
        },
        "source_bindings": {
            "response_schema": {
                "schema_id": response_schema["$id"],
                "sha256": response_schema_sha256,
            },
            "role_schema": {
                "schema_id": role_schema["$id"],
                "sha256": role_schema_sha256,
            },
            "run_id": task["run_id"],
            "task_id": task["task_id"],
        },
        "stage": "prediction",
        "template_choice_semantics": {
            "choice_placeholder_pattern": "^<[^<>]+>$",
            "frozen_value_rule": (
                "non_placeholder_values_are_frozen_except_declared_"
                "mutable_arrays"
            ),
            "mutable_array_rules": [
                {
                    "array": "compatible_alternatives",
                    "allowed_action": (
                        "clear_or_retain_for_determinate_and_retain_"
                        "expand_for_indeterminate"
                    ),
                },
                {
                    "array": "pollution.integrity_exposures",
                    "allowed_action": (
                        "keep_empty_or_append_schema_valid_items"
                    ),
                },
            ],
            "template_kind": "typed_choice_template",
        },
    }


def expectation_product(
    expectations: Any,
    *,
    case_id: str,
    configurations: list[str],
    observation_ids: list[str],
    location: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not isinstance(expectations, list):
        return [], [
            {
                "path": location,
                "problem": "expectations must be an array",
            }
        ]
    objects = [item for item in expectations if isinstance(item, dict)]
    issues: list[dict[str, str]] = []
    if len(objects) != len(expectations):
        issues.append(
            {
                "path": location,
                "problem": "expectations contains a non-object item",
            }
        )
    expected = {
        (configuration_id, observation_id)
        for configuration_id in configurations
        for observation_id in observation_ids
    }
    actual = [
        (item.get("configuration_id"), item.get("observation_id"))
        for item in objects
    ]
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


def first_difference(
    actual: Any,
    expected: Any,
    path: str = "participant_contract",
) -> dict[str, str] | None:
    if type(actual) is not type(expected):
        return {
            "path": path,
            "problem": (
                f"derived contract type differs: expected "
                f"{type(expected).__name__}, got {type(actual).__name__}"
            ),
        }
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            return {
                "path": path,
                "problem": (
                    "derived contract keys differ: "
                    f"expected {sorted(expected)}, got {sorted(actual)}"
                ),
            }
        for key in expected:
            difference = first_difference(
                actual[key], expected[key], f"{path}/{key}"
            )
            if difference is not None:
                return difference
        return None
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return {
                "path": path,
                "problem": (
                    f"derived contract list length differs: expected "
                    f"{len(expected)}, got {len(actual)}"
                ),
            }
        for index, item in enumerate(expected):
            difference = first_difference(
                actual[index], item, f"{path}/{index}"
            )
            if difference is not None:
                return difference
        return None
    if actual != expected:
        return {
            "path": path,
            "problem": (
                f"derived contract value differs: expected "
                f"{expected!r}, got {actual!r}"
            ),
        }
    return None


def verify_material_bindings(
    task: dict[str, Any],
    template: dict[str, Any],
    *,
    response_schema_path: str,
    response_schema_sha256: str,
    template_path: str,
    template_sha256: str,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if template.get("run_id") != task.get("run_id"):
        issues.append(
            {
                "path": "run_id",
                "problem": "template run_id differs from task run_id",
            }
        )
    target = template.get("target_response_schema")
    if not isinstance(target, dict):
        raise ContractError("template has no target_response_schema")
    if target.get("path", "").replace("\\", "/") != response_schema_path:
        issues.append(
            {
                "path": "target_response_schema/path",
                "problem": (
                    "template target path differs from the supplied "
                    "response Schema"
                ),
            }
        )
    if target.get("sha256") != response_schema_sha256:
        issues.append(
            {
                "path": "target_response_schema/sha256",
                "problem": "template is not bound to the supplied Schema bytes",
            }
        )
    artifact_id = target.get("artifact_id")
    if not isinstance(artifact_id, str) or not artifact_id.startswith(
        "schema.blind-response-interface-"
    ):
        issues.append(
            {
                "path": "target_response_schema/artifact_id",
                "problem": (
                    "template target artifact ID does not identify the "
                    "blind-response interface"
                ),
            }
        )

    output_schema = task.get("output_schema")
    if not isinstance(output_schema, dict):
        issues.append(
            {
                "path": "task/output_schema",
                "problem": "task has no response Schema binding",
            }
        )
    else:
        if (
            output_schema.get("path", "").replace("\\", "/")
            != response_schema_path
        ):
            issues.append(
                {
                    "path": "task/output_schema/path",
                    "problem": (
                        "task output path differs from the supplied "
                        "response Schema"
                    ),
                }
            )
        if output_schema.get("sha256") != response_schema_sha256:
            issues.append(
                {
                    "path": "task/output_schema/sha256",
                    "problem": (
                        "task is not bound to the supplied response "
                        "Schema bytes"
                    ),
                }
            )

    input_artifacts = task.get("input_artifacts")
    if not isinstance(input_artifacts, list):
        issues.append(
            {
                "path": "task/input_artifacts",
                "problem": "task has no input artifact list",
            }
        )
        return issues
    matches = [
        item
        for item in input_artifacts
        if isinstance(item, dict)
        and item.get("path", "").replace("\\", "/") == template_path
    ]
    if len(matches) != 1:
        issues.append(
            {
                "path": "task/input_artifacts",
                "problem": (
                    "task must bind the supplied template path exactly once"
                ),
            }
        )
    else:
        binding = matches[0]
        if binding.get("sha256") != template_sha256:
            issues.append(
                {
                    "path": "task/input_artifacts/template/sha256",
                    "problem": (
                        "task template binding differs from supplied "
                        "template bytes"
                    ),
                }
            )
        if binding.get("artifact_id") != template.get("template_id"):
            issues.append(
                {
                    "path": "task/input_artifacts/template/artifact_id",
                    "problem": (
                        "task template artifact ID differs from template_id"
                    ),
                }
            )
    return issues


def expected_slots(
    observation: dict[str, Any],
    *,
    alternative: bool,
) -> tuple[str, str, str | None]:
    allowed = ordered_values(
        list(dict.fromkeys(observation["allowed_value_types"]))
    )
    determinate = [value for value in allowed if value != "status"]
    if alternative:
        value_types = determinate
        kinds = list(
            dict.fromkeys(KIND_BY_VALUE_TYPE[value] for value in determinate)
        )
        unit = observation["unit"]
    else:
        value_types = allowed
        kinds = list(
            dict.fromkeys(
                [
                    *(
                        KIND_BY_VALUE_TYPE[value]
                        for value in determinate
                    ),
                    "status",
                ]
            )
        )
        unit = (
            None
            if observation["unit"] is None
            else placeholder(["null", observation["unit"]])
        )
    return placeholder(kinds), placeholder(value_types), unit


def verify_expectation_slots(
    expectations: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
    *,
    location: str,
    alternative: bool,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for index, expectation in enumerate(expectations):
        observation_id = expectation.get("observation_id")
        observation = observations.get(observation_id)
        if observation is None:
            continue
        kind, value_type, unit = expected_slots(
            observation, alternative=alternative
        )
        expected = {
            "expectation_kind": kind,
            "tolerance_rule_id": observation["tolerance_rule_id"],
            "value": {
                "serialized_value": "<required-string>",
                "unit": unit,
                "value_type": value_type,
            },
        }
        actual = {
            "expectation_kind": expectation.get("expectation_kind"),
            "tolerance_rule_id": expectation.get("tolerance_rule_id"),
            "value": expectation.get("value"),
        }
        difference = first_difference(
            actual, expected, f"{location}/{index}"
        )
        if difference is not None:
            issues.append(difference)
    return issues


def verify_contract(
    task: dict[str, Any],
    template: dict[str, Any],
    response_schema: dict[str, Any],
    role_schema: dict[str, Any],
    participant_schema: dict[str, Any],
    template_schema: dict[str, Any],
    *,
    response_schema_sha256: str,
    role_schema_sha256: str,
    material_bindings: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if task.get("artifact_type") != "prediction_task_packet":
        raise ContractError("task is not a prediction_task_packet")
    if (
        template.get("artifact_type") != "prediction_response_template"
        or template.get("artifact_version") != "0.1.1"
        or template.get("stage") != "prediction"
    ):
        raise ContractError(
            "template is not a protocol 0.1.1 prediction template"
        )
    if material_bindings is not None:
        issues.extend(
            verify_material_bindings(
                task,
                template,
                response_schema_path=material_bindings[
                    "response_schema_path"
                ],
                response_schema_sha256=response_schema_sha256,
                template_path=material_bindings["template_path"],
                template_sha256=material_bindings["template_sha256"],
            )
        )

    Draft202012Validator.check_schema(participant_schema)
    Draft202012Validator.check_schema(template_schema)
    registry = Registry().with_resource(
        participant_schema["$id"],
        Resource.from_contents(participant_schema),
    )
    for error in schema_errors(
        template, template_schema, registry=registry
    ):
        issues.append(
            {
                "path": "template_schema",
                "problem": error,
            }
        )
    participant_contract = template.get("participant_contract")
    if not isinstance(participant_contract, dict):
        issues.append(
            {
                "path": "participant_contract",
                "problem": "template has no participant contract object",
            }
        )
    else:
        for error in schema_errors(
            participant_contract, participant_schema
        ):
            issues.append(
                {
                    "path": "participant_contract_schema",
                    "problem": error,
                }
            )
        expected_contract = derive_participant_contract(
            task,
            response_schema,
            role_schema,
            response_schema_sha256=response_schema_sha256,
            role_schema_sha256=role_schema_sha256,
        )
        difference = first_difference(
            participant_contract, expected_contract
        )
        if difference is not None:
            issues.append(difference)

    target = template.get("target_response_schema")
    if not isinstance(target, dict):
        raise ContractError("template has no target_response_schema")
    if (
        material_bindings is None
        and target.get("sha256") != response_schema_sha256
    ):
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
    observations, observations_by_case = declared_observations(task)
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

    instruction_text = "\n".join(
        item for item in task.get("instructions", []) if isinstance(item, str)
    ).lower()
    for required_token in (
        "confidence_percent",
        "typed_choice_template",
        "unit=null",
        "compatible_alternatives",
        "integrity_exposures",
    ):
        if required_token not in instruction_text:
            issues.append(
                {
                    "path": "task/instructions",
                    "problem": (
                        "participant instructions do not expose required "
                        f"protocol token: {required_token}"
                    ),
                }
            )

    for case_id, observation_ids in observations_by_case.items():
        answer = answer_map.get(case_id)
        if not isinstance(answer, dict):
            continue
        if answer.get("confidence_percent") != "<integer-0-100>":
            issues.append(
                {
                    "path": (
                        f"template_payload/{case_id}/confidence_percent"
                    ),
                    "problem": (
                        "confidence_percent must be the typed "
                        "<integer-0-100> choice slot"
                    ),
                }
            )
        main_location = f"template_payload/{case_id}/expectations"
        main, product_issues = expectation_product(
            answer.get("expectations"),
            case_id=case_id,
            configurations=configurations,
            observation_ids=observation_ids,
            location=main_location,
        )
        issues.extend(product_issues)
        issues.extend(
            verify_expectation_slots(
                main,
                observations,
                location=main_location,
                alternative=False,
            )
        )

        alternatives = answer.get("compatible_alternatives")
        if not isinstance(alternatives, list) or len(alternatives) != 2:
            issues.append(
                {
                    "path": (
                        f"template_payload/{case_id}/"
                        "compatible_alternatives"
                    ),
                    "problem": (
                        "typed choice template must provide exactly two "
                        "complete alternative stubs"
                    ),
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
            location = (
                f"template_payload/{case_id}/compatible_alternatives/"
                f"{alternative_index}/expectations"
            )
            child, child_issues = expectation_product(
                alternative.get("expectations"),
                case_id=case_id,
                configurations=configurations,
                observation_ids=observation_ids,
                location=location,
            )
            issues.extend(child_issues)
            issues.extend(
                verify_expectation_slots(
                    child,
                    observations,
                    location=location,
                    alternative=True,
                )
            )
    unique = {
        (item["path"], item["problem"]): item for item in issues
    }
    return list(unique.values())


def synthetic_task() -> dict[str, Any]:
    return {
        "allowed_configurations": [
            "config.baseline",
            "config.variant",
        ],
        "allowed_observations": [
            {
                "allowed_value_types": [
                    "integer",
                    "status",
                ],
                "description": "synthetic measured count",
                "observation_id": "obs.synthetic.count",
                "tolerance_rule_id": "tol.synthetic.exact",
                "unit": "count",
            }
        ],
        "artifact_type": "prediction_task_packet",
        "instructions": [
            "Use the typed_choice_template and its participant_contract.",
            "Replace confidence_percent with an integer from 0 through 100.",
            "For indeterminate expectations use status/indeterminate and "
            "unit=null.",
            "For determinate predictions replace compatible_alternatives "
            "with []; otherwise retain at least two complete alternatives.",
            "Keep integrity_exposures empty or append complete contract "
            "items.",
        ],
        "run_id": "rehearsal-006",
        "task_id": "task.predict.synthetic",
        "variant_interventions": [
            {
                "case_id": "CA-R1",
                "observation_ids": [
                    "obs.synthetic.count",
                ],
            }
        ],
    }


def synthetic_expectation(
    configuration_id: str,
    *,
    alternative: bool,
) -> dict[str, Any]:
    return {
        "configuration_id": configuration_id,
        "expectation_kind": "<exact>" if alternative else "<exact|status>",
        "observation_id": "obs.synthetic.count",
        "tolerance_rule_id": "tol.synthetic.exact",
        "value": {
            "serialized_value": "<required-string>",
            "unit": "count" if alternative else "<null|count>",
            "value_type": (
                "<integer>" if alternative else "<integer|status>"
            ),
        },
    }


def synthetic_template(
    contract: dict[str, Any],
    response_schema: dict[str, Any],
    *,
    response_schema_sha256: str,
) -> dict[str, Any]:
    main = [
        synthetic_expectation("config.baseline", alternative=False),
        synthetic_expectation("config.variant", alternative=False),
    ]
    alternatives = []
    for index in (1, 2):
        alternatives.append(
            {
                "alternative_id": f"<required-local-id-{index}>",
                "description": (
                    f"<required-compatible-world-description-{index}>"
                ),
                "expectations": [
                    synthetic_expectation(
                        "config.baseline", alternative=True
                    ),
                    synthetic_expectation(
                        "config.variant", alternative=True
                    ),
                ],
            }
        )
    return {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "response-template-0.1.1.schema.json"
        ),
        "artifact_type": "prediction_response_template",
        "artifact_version": "0.1.1",
        "created_at": "2026-07-28T00:00:00Z",
        "participant_contract": contract,
        "run_id": "rehearsal-006",
        "stage": "prediction",
        "target_response_schema": {
            "artifact_id": "schema.blind-response-interface-0.1.1",
            "path": RESPONSE_SCHEMA_PATH.as_posix(),
            "sha256": response_schema_sha256,
        },
        "template_id": "template.prediction.rehearsal-006",
        "template_payload": {
            "$schema": response_schema["$id"],
            "artifact_type": "prediction_response_payload",
            "artifact_version": "0.1.1",
            "pollution": {
                "familiarity": {
                    "exact_result_knowledge": (
                        "<none|suspected|known|unknown>"
                    ),
                    "exact_rule_knowledge": (
                        "<none|suspected|known|unknown>"
                    ),
                    "exact_variant_knowledge": (
                        "<none|suspected|known|unknown>"
                    ),
                    "project_exposure": (
                        "<none|limited|substantial|unknown>"
                    ),
                    "recognition_status": (
                        "<none|suspected|identified>"
                    ),
                    "recognized_family": None,
                    "recognized_work": None,
                    "related_genre_experience": (
                        "<none|limited|extensive|unknown>"
                    ),
                },
                "integrity_exposures": [],
                "stage_update_note": None,
            },
            "prediction_answers": [
                {
                    "assumptions": [],
                    "case_id": "CA-R1",
                    "compatible_alternatives": alternatives,
                    "confidence_percent": "<integer-0-100>",
                    "expectations": main,
                    "prediction_status": "<determinate|indeterminate>",
                    "reasoning": "<required-explanation>",
                    "supporting_record_ids": [],
                }
            ],
        },
    }


def load_protocol_schemas(
    repo_root: Path,
    args: argparse.Namespace | None = None,
) -> tuple[
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
]:
    response_path = repo_path(
        repo_root,
        args.response_schema if args is not None else RESPONSE_SCHEMA_PATH,
    )
    role_path = repo_path(
        repo_root,
        args.role_schema if args is not None else ROLE_SCHEMA_PATH,
    )
    participant_path = repo_path(
        repo_root,
        (
            args.participant_contract_schema
            if args is not None
            else PARTICIPANT_SCHEMA_PATH
        ),
    )
    template_path = repo_path(
        repo_root,
        args.template_schema if args is not None else TEMPLATE_SCHEMA_PATH,
    )
    return (
        response_path,
        read_json(response_path),
        role_path,
        read_json(role_path),
        participant_path,
        read_json(participant_path),
        template_path,
        read_json(template_path),
    )


def command_derive(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    task_path = repo_path(repo_root, args.task)
    (
        response_path,
        response_schema,
        role_path,
        role_schema,
        _,
        _,
        _,
        _,
    ) = load_protocol_schemas(repo_root, args)
    contract = derive_participant_contract(
        read_json(task_path),
        response_schema,
        role_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
    )
    print(
        json.dumps(
            contract,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_verify(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    task_path = repo_path(repo_root, args.task)
    template_path = repo_path(repo_root, args.template)
    (
        response_path,
        response_schema,
        role_path,
        role_schema,
        participant_path,
        participant_schema,
        template_schema_path,
        template_schema,
    ) = load_protocol_schemas(repo_root, args)
    issues = verify_contract(
        read_json(task_path),
        read_json(template_path),
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
        material_bindings={
            "response_schema_path": response_path.relative_to(
                repo_root
            ).as_posix(),
            "template_path": template_path.relative_to(
                repo_root
            ).as_posix(),
            "template_sha256": sha256(template_path),
        },
    )
    result = {
        "$schema": CHECK_SCHEMA_ID,
        "artifact_type": "prediction_template_contract_check",
        "artifact_version": "0.1.1",
        "issue_count": len(issues),
        "issues": issues,
        "participant_contract_schema_sha256": sha256(participant_path),
        "response_schema_sha256": sha256(response_path),
        "role_schema_sha256": sha256(role_path),
        "status": "failed" if issues else "passed",
        "task_sha256": sha256(task_path),
        "template_schema_sha256": sha256(template_schema_path),
        "template_sha256": sha256(template_path),
    }
    check_schema_path = repo_path(repo_root, CHECK_SCHEMA_PATH)
    check_schema = read_json(check_schema_path)
    output_errors = schema_errors(result, check_schema)
    if output_errors:
        raise ContractError(
            "contract-check output failed its Schema: "
            + "; ".join(output_errors)
        )
    if args.output is not None:
        output_path = repo_path(repo_root, args.output)
        if output_path.exists():
            raise ContractError(
                f"refusing to overwrite contract check: {output_path}"
            )
        if not output_path.parent.is_dir():
            raise ContractError(
                f"output directory does not exist: {output_path.parent}"
            )
        output_path.write_bytes(
            (
                json.dumps(
                    result,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8")
        )
        print(
            json.dumps(
                {
                    "artifact": output_path.relative_to(
                        repo_root
                    ).as_posix(),
                    "issue_count": len(issues),
                    "status": result["status"],
                },
                sort_keys=True,
            )
        )
    else:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if issues else 0


def command_self_test(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    (
        response_path,
        response_schema,
        role_path,
        role_schema,
        _,
        participant_schema,
        _,
        template_schema,
    ) = load_protocol_schemas(repo_root)
    task = synthetic_task()
    contract = derive_participant_contract(
        task,
        response_schema,
        role_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
    )
    template = synthetic_template(
        contract,
        response_schema,
        response_schema_sha256=sha256(response_path),
    )
    bindings = {
        "response_schema_path": RESPONSE_SCHEMA_PATH.as_posix(),
        "template_path": "synthetic/template.json",
        "template_sha256": "0" * 64,
    }
    task["output_schema"] = {
        "path": bindings["response_schema_path"],
        "sha256": sha256(response_path),
    }
    task["input_artifacts"] = [
        {
            "artifact_id": template["template_id"],
            "path": bindings["template_path"],
            "sha256": bindings["template_sha256"],
        }
    ]
    good = verify_contract(
        task,
        template,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
        material_bindings=bindings,
    )
    if good:
        raise ContractError(f"synthetic valid contract failed: {good}")

    wrong_binding = copy.deepcopy(task)
    wrong_binding["input_artifacts"][0]["sha256"] = "f" * 64
    binding_issues = verify_contract(
        wrong_binding,
        template,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
        material_bindings=bindings,
    )
    if not any(
        item["path"] == "task/input_artifacts/template/sha256"
        for item in binding_issues
    ):
        raise ContractError("task-template hash drift was not detected")

    fixed_unit = copy.deepcopy(template)
    fixed_unit["template_payload"]["prediction_answers"][0][
        "expectations"
    ][0]["value"]["unit"] = "count"
    fixed_issues = verify_contract(
        task,
        fixed_unit,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
    )
    if not any(
        item["path"].endswith("/0/value/unit")
        for item in fixed_issues
    ):
        raise ContractError("fixed-unit defect was not detected")

    fixed_confidence = copy.deepcopy(template)
    fixed_confidence["template_payload"]["prediction_answers"][0][
        "confidence_percent"
    ] = -1
    confidence_issues = verify_contract(
        task,
        fixed_confidence,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
    )
    if not any(
        item["path"].endswith("/confidence_percent")
        for item in confidence_issues
    ):
        raise ContractError("fixed-confidence defect was not detected")

    contract_drift = copy.deepcopy(template)
    contract_drift["participant_contract"]["local_id_pattern"] = ".*"
    drift_issues = verify_contract(
        task,
        contract_drift,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
    )
    if not any(
        item["path"] == "participant_contract/local_id_pattern"
        for item in drift_issues
    ):
        raise ContractError("participant-contract drift was not detected")

    broad_slot = copy.deepcopy(template)
    broad_slot["template_payload"]["prediction_answers"][0][
        "expectations"
    ][0]["value"]["value_type"] = "<integer|status|string>"
    broad_issues = verify_contract(
        task,
        broad_slot,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
    )
    if not any(
        item["path"].endswith("/0/value/value_type")
        for item in broad_issues
    ):
        raise ContractError("observation-specific slot drift was not detected")

    missing_instruction = copy.deepcopy(task)
    missing_instruction["instructions"] = ["Return one JSON object."]
    instruction_issues = verify_contract(
        missing_instruction,
        template,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=sha256(response_path),
        role_schema_sha256=sha256(role_path),
    )
    if len(
        [
            item
            for item in instruction_issues
            if item["path"] == "task/instructions"
        ]
    ) != 5:
        raise ContractError(
            "participant instruction visibility defects were not detected"
        )

    print(
        json.dumps(
            {
                "bad_fixed_confidence_detected": True,
                "bad_fixed_unit_detected": True,
                "contract_drift_detected": True,
                "instruction_visibility_defects": 5,
                "observation_specific_slot_drift_detected": True,
                "status": "self_test_passed",
                "synthetic_good_issue_count": 0,
                "task_template_binding_drift_detected": True,
            },
            sort_keys=True,
        )
    )
    return 0


def add_schema_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--participant-contract-schema",
        default=PARTICIPANT_SCHEMA_PATH,
    )
    command.add_argument(
        "--response-schema",
        default=RESPONSE_SCHEMA_PATH,
    )
    command.add_argument(
        "--role-schema",
        default=ROLE_SCHEMA_PATH,
    )
    command.add_argument(
        "--template-schema",
        default=TEMPLATE_SCHEMA_PATH,
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    subparsers = value.add_subparsers(dest="command", required=True)
    derive = subparsers.add_parser("derive-contract")
    derive.add_argument("--repo-root", type=Path, required=True)
    derive.add_argument("--task", required=True)
    add_schema_arguments(derive)
    derive.set_defaults(func=command_derive)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--task", required=True)
    verify.add_argument("--template", required=True)
    verify.add_argument("--output")
    add_schema_arguments(verify)
    verify.set_defaults(func=command_verify)
    self_test = subparsers.add_parser("self-test")
    self_test.add_argument("--repo-root", type=Path, required=True)
    self_test.set_defaults(func=command_self_test)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (
        ContractError,
        KeyError,
        TypeError,
        ValueError,
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
