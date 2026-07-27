#!/usr/bin/env python3
"""Verify stage-one participant constructability without stage-two leakage."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


class ContractError(RuntimeError):
    """Raised when a reconstruction-template contract cannot be verified."""


CHECK_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "reconstruction-template-contract-check-0.1.1.schema.json"
)
CHECK_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "reconstruction-template-contract-check-0.1.1.schema.json"
)
COMMON_TOOL_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/tools/"
    "verify-prediction-template-contract-v0.1.1.py"
)
PARTICIPANT_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "reconstruction-participant-response-contract-0.1.1.schema.json"
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
    "reconstruction-response-template-0.1.1.schema.json"
)


def load_common(repo_root: Path) -> Any:
    path = (repo_root / COMMON_TOOL_PATH).resolve()
    spec = importlib.util.spec_from_file_location(
        "participant_contract_common_v011",
        path,
    )
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot import common contract logic: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def uniqueness_values(role_schema: dict[str, Any]) -> list[str]:
    try:
        values = role_schema["$defs"]["reconstructionAnswer"][
            "properties"
        ]["uniqueness"]["enum"]
    except (KeyError, TypeError) as exc:
        raise ContractError(
            "role schema has no reconstruction uniqueness enum"
        ) from exc
    if not isinstance(values, list) or not all(
        isinstance(item, str) for item in values
    ):
        raise ContractError("invalid reconstruction uniqueness enum")
    return list(values)


def derive_participant_contract(
    common: Any,
    task: dict[str, Any],
    response_schema: dict[str, Any],
    role_schema: dict[str, Any],
    *,
    response_schema_sha256: str,
    role_schema_sha256: str,
) -> dict[str, Any]:
    if task.get("artifact_type") != "reconstruction_task_packet":
        raise ContractError("task is not a reconstruction_task_packet")
    case_ids = task.get("case_ids")
    if not isinstance(case_ids, list) or not case_ids or not all(
        isinstance(item, str) for item in case_ids
    ):
        raise ContractError("reconstruction task has no case_ids")
    if len(case_ids) != len(set(case_ids)):
        raise ContractError("reconstruction task contains duplicate case_ids")
    try:
        local_id_pattern = role_schema["$defs"]["localId"]["pattern"]
        integrity_shape = role_schema["$defs"]["integrityExposure"]
    except (KeyError, TypeError) as exc:
        raise ContractError(
            "role schema does not expose local ID and integrity contracts"
        ) from exc

    return {
        "artifact_type": "reconstruction_participant_response_contract",
        "artifact_version": "0.1.1",
        "confidence_percent_rule": {
            "maximum": 100,
            "minimum": 0,
            "template_slot": "<integer-0-100>",
            "type": "integer",
        },
        "integrity_exposure_item_shape": copy.deepcopy(integrity_shape),
        "local_id_pattern": local_id_pattern,
        "pollution_enums": {
            "exact_result_knowledge": common.resolved_enum(
                role_schema, "familiarity", "exact_result_knowledge"
            ),
            "exact_rule_knowledge": common.resolved_enum(
                role_schema, "familiarity", "exact_rule_knowledge"
            ),
            "exact_variant_knowledge": common.resolved_enum(
                role_schema, "familiarity", "exact_variant_knowledge"
            ),
            "integrity_exposure_type": common.resolved_enum(
                role_schema, "integrityExposure", "exposure_type"
            ),
            "integrity_stage": common.resolved_enum(
                role_schema, "integrityExposure", "stage"
            ),
            "integrity_status": common.resolved_enum(
                role_schema, "integrityExposure", "status"
            ),
            "project_exposure": common.resolved_enum(
                role_schema, "familiarity", "project_exposure"
            ),
            "recognition_status": common.resolved_enum(
                role_schema, "familiarity", "recognition_status"
            ),
            "related_genre_experience": common.resolved_enum(
                role_schema, "familiarity", "related_genre_experience"
            ),
        },
        "reconstruction_rules": {
            "case_ids": list(case_ids),
            "case_occurrence": "exactly_once",
            "local_id_fields": [
                "compatible_branches[].branch_id",
                "recovered_facts[].fact_id",
                "supporting_record_ids[]",
            ],
            "uniqueness_values": uniqueness_values(role_schema),
        },
        "required_fields": {
            "compatible_branch": common.definition_required(
                response_schema, role_schema, "compatibleBranch"
            ),
            "familiarity": common.definition_required(
                response_schema, role_schema, "familiarity"
            ),
            "integrity_exposure": common.definition_required(
                response_schema, role_schema, "integrityExposure"
            ),
            "pollution": common.definition_required(
                response_schema, role_schema, "pollution"
            ),
            "reconstruction_answer": common.definition_required(
                response_schema, role_schema, "reconstructionAnswer"
            ),
            "reconstruction_payload": common.definition_required(
                response_schema, role_schema, "reconstructionPayload"
            ),
            "recovered_fact": common.definition_required(
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
        "stage": "reconstruction",
        "template_choice_semantics": {
            "choice_placeholder_pattern": "^<[^<>]+>$",
            "frozen_value_rule": (
                "non_placeholder_values_are_frozen_except_declared_"
                "mutable_arrays"
            ),
            "mutable_array_rules": [
                {
                    "array": "pollution.integrity_exposures",
                    "allowed_action": (
                        "keep_empty_or_append_schema_valid_items"
                    ),
                },
                {
                    "array": "reconstruction_answers[].ambiguities",
                    "allowed_action": (
                        "keep_empty_or_append_nonempty_strings"
                    ),
                },
                {
                    "array": "reconstruction_answers[].assumptions",
                    "allowed_action": (
                        "keep_empty_or_append_nonempty_strings"
                    ),
                },
                {
                    "array": (
                        "reconstruction_answers[].compatible_branches"
                    ),
                    "allowed_action": (
                        "clear_retain_or_expand_complete_items"
                    ),
                },
                {
                    "array": "reconstruction_answers[].recovered_facts",
                    "allowed_action": (
                        "clear_retain_or_expand_complete_items"
                    ),
                },
                {
                    "array": "supporting_record_ids",
                    "allowed_action": (
                        "keep_empty_or_append_valid_local_ids"
                    ),
                },
            ],
            "template_kind": "typed_choice_template",
        },
    }


def verify_template_slots(
    task: dict[str, Any],
    template: dict[str, Any],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    payload = template.get("template_payload")
    if not isinstance(payload, dict):
        raise ContractError("template_payload must be an object")
    answers = payload.get("reconstruction_answers")
    if not isinstance(answers, list):
        raise ContractError("reconstruction_answers must be an array")
    actual_case_ids = [
        item.get("case_id") for item in answers if isinstance(item, dict)
    ]
    if (
        len(actual_case_ids) != len(answers)
        or len(actual_case_ids) != len(set(actual_case_ids))
        or set(actual_case_ids) != set(task["case_ids"])
    ):
        issues.append(
            {
                "path": "template_payload/reconstruction_answers",
                "problem": (
                    "template must contain each dispatched case exactly once"
                ),
            }
        )
    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            continue
        expected = {
            "ambiguities": [],
            "assumptions": [],
            "compatible_branches": [
                {
                    "branch_id": "<required-local-id>",
                    "description": (
                        "<required-compatible-structure-description>"
                    ),
                    "supporting_record_ids": [],
                }
            ],
            "confidence_percent": "<integer-0-100>",
            "recovered_facts": [
                {
                    "claim": "<required-fact-claim>",
                    "fact_id": "<required-local-id>",
                    "recovery_status": (
                        "<inferred_with_assumption|not_recoverable|recovered>"
                    ),
                    "supporting_record_ids": [],
                }
            ],
            "uniqueness": (
                "<insufficient_information|multiple_compatible_structures|"
                "uniquely_recoverable>"
            ),
        }
        actual = {
            key: answer.get(key)
            for key in expected
        }
        difference = common_first_difference(
            actual,
            expected,
            (
                "template_payload/reconstruction_answers/"
                f"{index}"
            ),
        )
        if difference is not None:
            issues.append(difference)
    return issues


def common_first_difference(
    actual: Any,
    expected: Any,
    path: str,
) -> dict[str, str] | None:
    if type(actual) is not type(expected):
        return {
            "path": path,
            "problem": (
                f"template slot type differs: expected "
                f"{type(expected).__name__}, got {type(actual).__name__}"
            ),
        }
    if isinstance(expected, dict):
        if set(actual) != set(expected):
            return {
                "path": path,
                "problem": "template slot fields differ",
            }
        for key in expected:
            result = common_first_difference(
                actual[key], expected[key], f"{path}/{key}"
            )
            if result is not None:
                return result
        return None
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return {
                "path": path,
                "problem": "template slot array length differs",
            }
        for index, item in enumerate(expected):
            result = common_first_difference(
                actual[index], item, f"{path}/{index}"
            )
            if result is not None:
                return result
        return None
    if actual != expected:
        return {
            "path": path,
            "problem": (
                f"template slot differs: expected {expected!r}, "
                f"got {actual!r}"
            ),
        }
    return None


def verify_contract(
    common: Any,
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
    if task.get("artifact_type") != "reconstruction_task_packet":
        raise ContractError("task is not a reconstruction_task_packet")
    if (
        template.get("artifact_type") != "reconstruction_response_template"
        or template.get("artifact_version") != "0.1.1"
        or template.get("stage") != "reconstruction"
    ):
        raise ContractError(
            "template is not a protocol 0.1.1 reconstruction template"
        )
    issues: list[dict[str, str]] = []
    if material_bindings is not None:
        issues.extend(
            common.verify_material_bindings(
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
    for error in common.schema_errors(
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
        for error in common.schema_errors(
            participant_contract, participant_schema
        ):
            issues.append(
                {
                    "path": "participant_contract_schema",
                    "problem": error,
                }
            )
        expected = derive_participant_contract(
            common,
            task,
            response_schema,
            role_schema,
            response_schema_sha256=response_schema_sha256,
            role_schema_sha256=role_schema_sha256,
        )
        difference = common.first_difference(
            participant_contract, expected
        )
        if difference is not None:
            issues.append(difference)

    payload = template.get("template_payload")
    if not isinstance(payload, dict):
        raise ContractError("template_payload must be an object")
    if payload.get("$schema") != response_schema.get("$id"):
        issues.append(
            {
                "path": "template_payload/$schema",
                "problem": "payload Schema ID differs from supplied Schema",
            }
        )
    instruction_text = "\n".join(
        item for item in task.get("instructions", []) if isinstance(item, str)
    ).lower()
    for required_token in (
        "confidence_percent",
        "typed_choice_template",
        "integrity_exposures",
        "local_id_pattern",
        "mutable_array_rules",
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
    issues.extend(verify_template_slots(task, template))
    unique = {
        (item["path"], item["problem"]): item for item in issues
    }
    return list(unique.values())


def synthetic_task() -> dict[str, Any]:
    return {
        "artifact_type": "reconstruction_task_packet",
        "case_ids": [
            "CA-R2",
        ],
        "instructions": [
            "Use the typed_choice_template and participant_contract.",
            "Replace confidence_percent with an integer from 0 through 100.",
            "All local IDs must match local_id_pattern.",
            "Keep integrity_exposures empty or append complete items.",
            "Follow mutable_array_rules when changing template arrays.",
        ],
        "run_id": "rehearsal-006",
        "task_id": "task.reconstruct.synthetic",
    }


def synthetic_template(
    contract: dict[str, Any],
    response_schema: dict[str, Any],
    *,
    response_schema_sha256: str,
) -> dict[str, Any]:
    return {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "reconstruction-response-template-0.1.1.schema.json"
        ),
        "artifact_type": "reconstruction_response_template",
        "artifact_version": "0.1.1",
        "created_at": "2026-07-28T00:00:00Z",
        "participant_contract": contract,
        "run_id": "rehearsal-006",
        "stage": "reconstruction",
        "target_response_schema": {
            "artifact_id": "schema.blind-response-interface-0.1.1",
            "path": RESPONSE_SCHEMA_PATH.as_posix(),
            "sha256": response_schema_sha256,
        },
        "template_id": "template.reconstruction.rehearsal-006",
        "template_payload": {
            "$schema": response_schema["$id"],
            "artifact_type": "reconstruction_response_payload",
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
            "reconstruction_answers": [
                {
                    "ambiguities": [],
                    "assumptions": [],
                    "case_id": "CA-R2",
                    "compatible_branches": [
                        {
                            "branch_id": "<required-local-id>",
                            "description": (
                                "<required-compatible-structure-description>"
                            ),
                            "supporting_record_ids": [],
                        }
                    ],
                "confidence_percent": "<integer-0-100>",
                    "recovered_facts": [
                        {
                            "claim": "<required-fact-claim>",
                            "fact_id": "<required-local-id>",
                            "recovery_status": (
                                "<inferred_with_assumption|not_recoverable|"
                                "recovered>"
                            ),
                            "supporting_record_ids": [],
                        }
                    ],
                    "uniqueness": (
                        "<insufficient_information|"
                        "multiple_compatible_structures|"
                        "uniquely_recoverable>"
                    ),
                }
            ],
        },
    }


def load_protocol_schemas(
    common: Any,
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
    response_path = common.repo_path(
        repo_root,
        args.response_schema if args is not None else RESPONSE_SCHEMA_PATH,
    )
    role_path = common.repo_path(
        repo_root,
        args.role_schema if args is not None else ROLE_SCHEMA_PATH,
    )
    participant_path = common.repo_path(
        repo_root,
        (
            args.participant_contract_schema
            if args is not None
            else PARTICIPANT_SCHEMA_PATH
        ),
    )
    template_path = common.repo_path(
        repo_root,
        args.template_schema if args is not None else TEMPLATE_SCHEMA_PATH,
    )
    return (
        response_path,
        common.read_json(response_path),
        role_path,
        common.read_json(role_path),
        participant_path,
        common.read_json(participant_path),
        template_path,
        common.read_json(template_path),
    )


def command_derive(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    common = load_common(repo_root)
    task_path = common.repo_path(repo_root, args.task)
    (
        response_path,
        response_schema,
        role_path,
        role_schema,
        _,
        _,
        _,
        _,
    ) = load_protocol_schemas(common, repo_root, args)
    contract = derive_participant_contract(
        common,
        common.read_json(task_path),
        response_schema,
        role_schema,
        response_schema_sha256=common.sha256(response_path),
        role_schema_sha256=common.sha256(role_path),
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
    common = load_common(repo_root)
    task_path = common.repo_path(repo_root, args.task)
    template_path = common.repo_path(repo_root, args.template)
    (
        response_path,
        response_schema,
        role_path,
        role_schema,
        participant_path,
        participant_schema,
        template_schema_path,
        template_schema,
    ) = load_protocol_schemas(common, repo_root, args)
    issues = verify_contract(
        common,
        common.read_json(task_path),
        common.read_json(template_path),
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=common.sha256(response_path),
        role_schema_sha256=common.sha256(role_path),
        material_bindings={
            "response_schema_path": response_path.relative_to(
                repo_root
            ).as_posix(),
            "template_path": template_path.relative_to(
                repo_root
            ).as_posix(),
            "template_sha256": common.sha256(template_path),
        },
    )
    result = {
        "$schema": CHECK_SCHEMA_ID,
        "artifact_type": "reconstruction_template_contract_check",
        "artifact_version": "0.1.1",
        "issue_count": len(issues),
        "issues": issues,
        "participant_contract_schema_sha256": common.sha256(
            participant_path
        ),
        "response_schema_sha256": common.sha256(response_path),
        "role_schema_sha256": common.sha256(role_path),
        "status": "failed" if issues else "passed",
        "task_sha256": common.sha256(task_path),
        "template_schema_sha256": common.sha256(template_schema_path),
        "template_sha256": common.sha256(template_path),
    }
    check_schema_path = common.repo_path(repo_root, CHECK_SCHEMA_PATH)
    output_errors = common.schema_errors(
        result, common.read_json(check_schema_path)
    )
    if output_errors:
        raise ContractError(
            "contract-check output failed its Schema: "
            + "; ".join(output_errors)
        )
    if args.output is not None:
        output_path = common.repo_path(repo_root, args.output)
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
    common = load_common(repo_root)
    (
        response_path,
        response_schema,
        role_path,
        role_schema,
        _,
        participant_schema,
        _,
        template_schema,
    ) = load_protocol_schemas(common, repo_root)
    task = synthetic_task()
    contract = derive_participant_contract(
        common,
        task,
        response_schema,
        role_schema,
        response_schema_sha256=common.sha256(response_path),
        role_schema_sha256=common.sha256(role_path),
    )
    template = synthetic_template(
        contract,
        response_schema,
        response_schema_sha256=common.sha256(response_path),
    )
    bindings = {
        "response_schema_path": RESPONSE_SCHEMA_PATH.as_posix(),
        "template_path": "synthetic/reconstruction-template.json",
        "template_sha256": "0" * 64,
    }
    task["output_schema"] = {
        "path": bindings["response_schema_path"],
        "sha256": common.sha256(response_path),
    }
    task["input_artifacts"] = [
        {
            "artifact_id": template["template_id"],
            "path": bindings["template_path"],
            "sha256": bindings["template_sha256"],
        }
    ]
    good = verify_contract(
        common,
        task,
        template,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=common.sha256(response_path),
        role_schema_sha256=common.sha256(role_path),
        material_bindings=bindings,
    )
    if good:
        raise ContractError(f"synthetic valid contract failed: {good}")

    fixed_confidence = copy.deepcopy(template)
    fixed_confidence["template_payload"]["reconstruction_answers"][0][
        "confidence_percent"
    ] = -1
    confidence_issues = verify_contract(
        common,
        task,
        fixed_confidence,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=common.sha256(response_path),
        role_schema_sha256=common.sha256(role_path),
    )
    if not any(
        item["path"].endswith("/confidence_percent")
        for item in confidence_issues
    ):
        raise ContractError("fixed-confidence defect was not detected")

    contract_drift = copy.deepcopy(template)
    contract_drift["participant_contract"]["local_id_pattern"] = ".*"
    drift_issues = verify_contract(
        common,
        task,
        contract_drift,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=common.sha256(response_path),
        role_schema_sha256=common.sha256(role_path),
    )
    if not any(
        item["path"] == "participant_contract/local_id_pattern"
        for item in drift_issues
    ):
        raise ContractError("local ID contract drift was not detected")

    leaked = copy.deepcopy(template)
    leaked["participant_contract"]["observation_rules"] = []
    leakage_issues = verify_contract(
        common,
        task,
        leaked,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=common.sha256(response_path),
        role_schema_sha256=common.sha256(role_path),
    )
    if not any(
        item["path"] in {
            "participant_contract",
            "participant_contract_schema",
        }
        for item in leakage_issues
    ):
        raise ContractError("stage-two contract leakage was not detected")

    missing_instruction = copy.deepcopy(task)
    missing_instruction["instructions"] = ["Return one JSON object."]
    instruction_issues = verify_contract(
        common,
        missing_instruction,
        template,
        response_schema,
        role_schema,
        participant_schema,
        template_schema,
        response_schema_sha256=common.sha256(response_path),
        role_schema_sha256=common.sha256(role_path),
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
                "contract_drift_detected": True,
                "instruction_visibility_defects": 5,
                "stage_two_contract_leakage_detected": True,
                "status": "self_test_passed",
                "synthetic_good_issue_count": 0,
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
