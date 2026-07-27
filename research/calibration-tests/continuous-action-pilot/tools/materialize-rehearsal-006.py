#!/usr/bin/env python3
"""Create the synthetic, pre-actor artifacts for rehearsal-006."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


RUN_ID = "rehearsal-006"
CREATED_AT = "2026-07-28T01:00:00Z"
PILOT_ROOT = Path(
    "research/calibration-tests/continuous-action-pilot"
)
REHEARSAL_ROOT = PILOT_ROOT / "rehearsals" / RUN_ID
INTERFACE_PATH = PILOT_ROOT / "schema" / (
    "blind-response-interface-0.1.1.schema.json"
)
ROLE_011_PATH = PILOT_ROOT / "schema" / (
    "role-submission-0.1.1.schema.json"
)
ROLE_012_PATH = PILOT_ROOT / "schema" / (
    "role-submission-0.1.2.schema.json"
)
PREDICTION_TOOL_PATH = PILOT_ROOT / "tools" / (
    "verify-prediction-template-contract-v0.1.1.py"
)
RECONSTRUCTION_TOOL_PATH = PILOT_ROOT / "tools" / (
    "verify-reconstruction-template-contract-v0.1.1.py"
)


class MaterializeError(RuntimeError):
    """Raised when rehearsal material would overwrite or escape its root."""


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise MaterializeError(f"expected JSON object: {path}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MaterializeError(f"cannot import materializer dependency: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(repo_root: Path, relative: Path, value: dict[str, Any]) -> None:
    path = (repo_root / relative).resolve()
    if not path.is_relative_to((repo_root / REHEARSAL_ROOT).resolve()):
        raise MaterializeError(f"output escapes rehearsal root: {relative}")
    if path.exists():
        raise MaterializeError(f"refusing to overwrite artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def artifact_reference(
    repo_root: Path,
    artifact_id: str,
    path: Path,
) -> dict[str, str]:
    raw = (repo_root / path).read_bytes()
    return {
        "artifact_id": artifact_id,
        "path": path.as_posix(),
        "sha256": sha256_bytes(raw),
    }


def common_task_fields(
    repo_root: Path,
    *,
    artifact_type: str,
    case_ids: list[str],
    condition_id: str | None,
    instructions: list[str],
    input_artifacts: list[dict[str, str]],
    stage1_submission_required: bool,
    task_id: str,
) -> dict[str, Any]:
    return {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "task-packet-0.1.1.schema.json"
        ),
        "allowed_configurations": [],
        "allowed_observations": [],
        "artifact_type": artifact_type,
        "artifact_version": "0.1.1",
        "assembled_output_schema": {
            "path": ROLE_012_PATH.as_posix(),
            "sha256": sha256_bytes(
                (repo_root / ROLE_012_PATH).read_bytes()
            ),
        },
        "behavior_scope": "structural_only",
        "case_ids": case_ids,
        "condition_id": condition_id,
        "created_at": CREATED_AT,
        "forbidden_actions": [
            "access_other_condition",
            "access_other_submission",
            "access_package_outside_dispatch",
            "access_truth_or_result",
            "create_child_task",
            "external_search",
            "read_shared_workspace",
            "tool_call",
        ],
        "input_artifacts": input_artifacts,
        "instructions": instructions,
        "output_schema": {
            "path": INTERFACE_PATH.as_posix(),
            "sha256": sha256_bytes(
                (repo_root / INTERFACE_PATH).read_bytes()
            ),
        },
        "representation_version": "CA-SR 0.1",
        "required_audit_checks": [],
        "run_id": RUN_ID,
        "stage1_submission_required": stage1_submission_required,
        "stop_boundary_refs": [
            "stop.after-step-2",
        ],
        "target_encoding_sha256": None,
        "target_view_sha256": None,
        "task_id": task_id,
        "tolerance_rule_refs": [],
        "variant_interventions": [],
    }


def reconstruction_instructions() -> list[str]:
    return [
        (
            "只根据本条件视图、任务和模板回答；不得使用工具、网络、"
            "共享工作区、其他条件、真值、结果或既有项目上下文。"
        ),
        (
            "模板是 typed_choice_template。阅读 participant_contract，"
            "最终只返回 template_payload 对应的单一 JSON 对象；不要返回"
            "模板外壳、代码围栏或附加文字。"
        ),
        (
            "所有新建 fact_id、branch_id 和 supporting_record_ids 都必须"
            "符合 participant_contract.local_id_pattern；大写字母不合法。"
        ),
        (
            "confidence_percent 是类型化选择槽；必须把 <integer-0-100> "
            "替换为 0 至 100 的 JSON 整数。"
        ),
        (
            "integrity_exposures 可以保持空数组，也可以依照契约给出的"
            "完整 item shape 追加记录。"
        ),
        (
            "只依照 participant_contract.template_choice_semantics."
            "mutable_array_rules 清空、保留或扩展数组；尖括号表示必须"
            "选择或替换的槽位，其他值保持冻结。"
        ),
        (
            "每个任务 case 恰好回答一次；无法恢复结构时可以清空模板中"
            "的 recovered_facts 与 compatible_branches，并明确选择"
            " insufficient_information。"
        ),
        (
            "不要填写运行、任务、条件、actor、session、提交时间、输入"
            "散列、前阶段散列或审核字段；这些字段由保管工具生成。"
        ),
    ]


def prediction_instructions() -> list[str]:
    return [
        (
            "继续只使用自己的冻结重构、本任务、中性变体信封和模板；"
            "不得使用工具、网络、共享工作区、其他条件、真值、结果或"
            "他人提交。"
        ),
        (
            "模板是 typed_choice_template。阅读 participant_contract，"
            "最终只返回 template_payload 对应的单一 JSON 对象；尖括号"
            "槽位可以选择字符串值或真正的 JSON null。"
        ),
        (
            "若 prediction_status=indeterminate，主 expectations 必须"
            "使用 expectation_kind=status、serialized_value="
            "indeterminate、value_type=status、unit=null。"
        ),
        (
            "confidence_percent 是类型化选择槽；必须把 <integer-0-100> "
            "替换为 0 至 100 的 JSON 整数。"
        ),
        (
            "有量纲主预测的 <null|count> 是类型化选择：不确定分支选择"
            "真正的 JSON null，确定分支选择字符串 count。"
        ),
        (
            "compatible_alternatives 在不确定分支至少保留两个；每个"
            "替代都必须完整覆盖配置—观察量笛卡尔积，使用具体值、"
            "具体类型和声明单位，而且各替代至少一项预测不同。"
        ),
        (
            "确定分支可以清空 compatible_alternatives，也可以保留完整"
            "且具体的相容替代；主 expectations 仍必须使用允许的具体"
            "类型、声明单位和匹配的 expectation_kind。"
        ),
        (
            "integrity_exposures 可以保持空数组，也可以依照契约给出的"
            "完整 item shape 追加记录。"
        ),
        (
            "不要填写运行、任务、条件、actor、session、提交时间、输入"
            "散列、前阶段散列或审核字段；这些字段由保管工具生成。"
        ),
    ]


def view_v01() -> dict[str, Any]:
    return {
        "artifact_type": "rehearsal_condition_view",
        "artifact_version": "0.1.0",
        "behavior_scope": "structural_only",
        "case_id": "CA-R2",
        "condition_id": "condition-v01",
        "initial_state": [
            {
                "field_id": "state.total",
                "value": 0,
            }
        ],
        "input_trace": [
            {
                "raw_value": 2,
                "step": 1,
            },
            {
                "raw_value": 5,
                "step": 2,
            },
        ],
        "opaque_configuration": {
            "active_value": 0,
            "allowed_values": [
                0,
                1,
            ],
            "variable_id": "v-q",
        },
        "operational_records": [
            {
                "record_id": "rec.sampling-policy",
                "record_type": "input_sampling_policy",
                "rules": [
                    {
                        "configuration_value": 0,
                        "read_semantics": (
                            "在每次更新开始时读取当前步骤的原始输入"
                        ),
                    },
                    {
                        "configuration_value": 1,
                        "read_semantics": (
                            "在片段入口读取第一步的原始输入，此后每次更新"
                            "复用该值"
                        ),
                    },
                ],
                "sampled_value_id": "value.sampled",
            },
            {
                "record_id": "rec.accumulator-process",
                "record_type": "state_update_process",
                "update_rule": (
                    "state.total := state.total + value.sampled"
                ),
                "write_field_id": "state.total",
            },
            {
                "ordering": [
                    "读取 value.sampled",
                    "执行 state.total 更新",
                ],
                "record_id": "rec.step-order",
                "record_type": "within_step_order",
            },
        ],
        "operation_trace": [
            {
                "operation_id": "op.accumulate",
                "record_refs": [
                    "rec.sampling-policy",
                    "rec.accumulator-process",
                    "rec.step-order",
                ],
                "step": 1,
            },
            {
                "operation_id": "op.accumulate",
                "record_refs": [
                    "rec.sampling-policy",
                    "rec.accumulator-process",
                    "rec.step-order",
                ],
                "step": 2,
            },
        ],
        "output_contract": {
            "observation_id": "obs.total-at-stop",
            "read_field_id": "state.total",
            "stop_boundary_id": "stop.after-step-2",
        },
        "run_id": RUN_ID,
        "time_base": {
            "ordered_steps": [
                1,
                2,
            ],
            "time_base_id": "time.discrete-step",
        },
    }


def view_v02() -> dict[str, Any]:
    return {
        "artifact_type": "rehearsal_condition_view",
        "artifact_version": "0.1.0",
        "behavior_scope": "structural_only",
        "case_id": "CA-R2",
        "condition_id": "condition-v02",
        "initial_state": [
            {
                "field_id": "state.total",
                "value": 0,
            }
        ],
        "input_trace": [
            {
                "raw_value": 2,
                "step": 1,
            },
            {
                "raw_value": 5,
                "step": 2,
            },
        ],
        "opaque_configuration": {
            "active_value": 0,
            "allowed_values": [
                0,
                1,
            ],
            "variable_id": "v-q",
        },
        "operation_trace": [
            {
                "operation_id": "op.accumulate",
                "step": 1,
                "writes": [
                    "state.total",
                ],
            },
            {
                "operation_id": "op.accumulate",
                "step": 2,
                "writes": [
                    "state.total",
                ],
            },
        ],
        "output_contract": {
            "observation_id": "obs.total-at-stop",
            "read_field_id": "state.total",
            "stop_boundary_id": "stop.after-step-2",
        },
        "projection_notice": (
            "本视图只声明操作发生、原始输入与可观察字段；未声明配置"
            "变量、输入读取和状态更新之间的关系。"
        ),
        "run_id": RUN_ID,
    }


def variant_envelope() -> dict[str, Any]:
    return {
        "artifact_type": "rehearsal_variant_envelope",
        "artifact_version": "0.1.0",
        "behavior_scope": "structural_only",
        "case_id": "CA-R2",
        "invariants": [
            "initial_state",
            "input_trace",
            "operation_count",
            "operation_identity",
            "step_order",
            "output_contract",
            "stop_boundary",
        ],
        "observation": {
            "comparison": "exact",
            "observation_id": "obs.total-at-stop",
            "unit": "count",
        },
        "run_id": RUN_ID,
        "stop_boundary_id": "stop.after-step-2",
        "variable_intervention": {
            "baseline_value": 0,
            "variable_id": "v-q",
            "variant_value": 1,
        },
    }


def pollution() -> dict[str, Any]:
    return {
        "familiarity": {
            "exact_result_knowledge": "none",
            "exact_rule_knowledge": "none",
            "exact_variant_knowledge": "none",
            "project_exposure": "none",
            "recognition_status": "none",
            "recognized_family": None,
            "recognized_work": None,
            "related_genre_experience": "unknown",
        },
        "integrity_exposures": [],
        "stage_update_note": None,
    }


def reconstruction_payload() -> dict[str, Any]:
    return {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "blind-response-interface-0.1.1.schema.json"
        ),
        "artifact_type": "reconstruction_response_payload",
        "artifact_version": "0.1.1",
        "pollution": pollution(),
        "reconstruction_answers": [
            {
                "ambiguities": [],
                "assumptions": [],
                "case_id": "CA-R2",
                "compatible_branches": [],
                "confidence_percent": 0,
                "recovered_facts": [],
                "uniqueness": "insufficient_information",
            }
        ],
    }


def expectation(
    configuration_id: str,
    value: str,
) -> dict[str, Any]:
    return {
        "configuration_id": configuration_id,
        "expectation_kind": "exact",
        "observation_id": "obs.total-at-stop",
        "tolerance_rule_id": "tol.synthetic.exact",
        "value": {
            "serialized_value": value,
            "unit": "count",
            "value_type": "integer",
        },
    }


def status_expectation(configuration_id: str) -> dict[str, Any]:
    return {
        "configuration_id": configuration_id,
        "expectation_kind": "status",
        "observation_id": "obs.total-at-stop",
        "tolerance_rule_id": "tol.synthetic.exact",
        "value": {
            "serialized_value": "indeterminate",
            "unit": None,
            "value_type": "status",
        },
    }


def prediction_determinate_payload() -> dict[str, Any]:
    return {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "blind-response-interface-0.1.1.schema.json"
        ),
        "artifact_type": "prediction_response_payload",
        "artifact_version": "0.1.1",
        "pollution": pollution(),
        "prediction_answers": [
            {
                "assumptions": [],
                "case_id": "CA-R2",
                "compatible_alternatives": [],
                "confidence_percent": 100,
                "expectations": [
                    expectation("config.baseline", "7"),
                    expectation("config.variant", "4"),
                ],
                "prediction_status": "determinate",
                "reasoning": (
                    "配置 0 每步读取 2、5，配置 1 两步复用入口值 2。"
                ),
                "supporting_record_ids": [
                    "rec.sampling-policy",
                    "rec.accumulator-process",
                    "rec.step-order",
                    "obs.total-at-stop",
                    "config.baseline",
                    "config.variant",
                ],
            }
        ],
    }


def prediction_indeterminate_payload() -> dict[str, Any]:
    return {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "blind-response-interface-0.1.1.schema.json"
        ),
        "artifact_type": "prediction_response_payload",
        "artifact_version": "0.1.1",
        "pollution": pollution(),
        "prediction_answers": [
            {
                "assumptions": [],
                "case_id": "CA-R2",
                "compatible_alternatives": [
                    {
                        "alternative_id": "raw-input-addition",
                        "description": (
                            "配置变量不影响读取，两种配置都累计为 7。"
                        ),
                        "expectations": [
                            expectation("config.baseline", "7"),
                            expectation("config.variant", "7"),
                        ],
                    },
                    {
                        "alternative_id": "binary-input-gate",
                        "description": (
                            "配置 0 抑制输入，配置 1 传递输入。"
                        ),
                        "expectations": [
                            expectation("config.baseline", "0"),
                            expectation("config.variant", "7"),
                        ],
                    },
                ],
                "confidence_percent": 100,
                "expectations": [
                    status_expectation("config.baseline"),
                    status_expectation("config.variant"),
                ],
                "prediction_status": "indeterminate",
                "reasoning": (
                    "条件视图没有给出配置变量、输入采样与状态更新之间的"
                    "关系，存在多个预测不同的相容结构。"
                ),
                "supporting_record_ids": [
                    "v-q",
                    "op.accumulate",
                    "obs.total-at-stop",
                    "config.baseline",
                    "config.variant",
                ],
            }
        ],
    }


def reconstruction_template(
    contract: dict[str, Any],
    task_id: str,
    condition_id: str,
    response_schema: dict[str, Any],
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
        "created_at": CREATED_AT,
        "participant_contract": contract,
        "run_id": RUN_ID,
        "stage": "reconstruction",
        "target_response_schema": {
            "artifact_id": "schema.blind-response-interface-0.1.1",
            "path": INTERFACE_PATH.as_posix(),
            "sha256": response_schema_sha256,
        },
        "template_id": f"template.reconstruction.{condition_id}.{RUN_ID}",
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


def template_expectation(
    configuration_id: str,
    *,
    alternative: bool,
) -> dict[str, Any]:
    return {
        "configuration_id": configuration_id,
        "expectation_kind": "<exact>" if alternative else "<exact|status>",
        "observation_id": "obs.total-at-stop",
        "tolerance_rule_id": "tol.synthetic.exact",
        "value": {
            "serialized_value": "<required-string>",
            "unit": "count" if alternative else "<null|count>",
            "value_type": (
                "<integer>" if alternative else "<integer|status>"
            ),
        },
    }


def prediction_template(
    contract: dict[str, Any],
    response_schema: dict[str, Any],
    response_schema_sha256: str,
) -> dict[str, Any]:
    alternatives = []
    for index in (1, 2):
        alternatives.append(
            {
                "alternative_id": f"<required-local-id-{index}>",
                "description": (
                    f"<required-compatible-world-description-{index}>"
                ),
                "expectations": [
                    template_expectation(
                        "config.baseline", alternative=True
                    ),
                    template_expectation(
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
        "created_at": CREATED_AT,
        "participant_contract": contract,
        "run_id": RUN_ID,
        "stage": "prediction",
        "target_response_schema": {
            "artifact_id": "schema.blind-response-interface-0.1.1",
            "path": INTERFACE_PATH.as_posix(),
            "sha256": response_schema_sha256,
        },
        "template_id": f"template.prediction.{RUN_ID}",
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
                    "case_id": "CA-R2",
                    "compatible_alternatives": alternatives,
                    "confidence_percent": "<integer-0-100>",
                    "expectations": [
                        template_expectation(
                            "config.baseline", alternative=False
                        ),
                        template_expectation(
                            "config.variant", alternative=False
                        ),
                    ],
                    "prediction_status": "<determinate|indeterminate>",
                    "reasoning": "<required-explanation>",
                    "supporting_record_ids": [],
                }
            ],
        },
    }


def materialize(repo_root: Path) -> None:
    rehearsal_root = (repo_root / REHEARSAL_ROOT).resolve()
    if rehearsal_root.exists():
        raise MaterializeError(
            f"refusing to overwrite existing rehearsal: {rehearsal_root}"
        )
    if "runs" in REHEARSAL_ROOT.parts:
        raise MaterializeError("rehearsal output may not enter runs/")

    response_schema = read_json(repo_root / INTERFACE_PATH)
    role_schema = read_json(repo_root / ROLE_011_PATH)
    response_sha = sha256_bytes((repo_root / INTERFACE_PATH).read_bytes())
    role_sha = sha256_bytes((repo_root / ROLE_011_PATH).read_bytes())
    prediction_module = load_module(
        repo_root / PREDICTION_TOOL_PATH,
        "prediction_contract_v011",
    )
    reconstruction_module = load_module(
        repo_root / RECONSTRUCTION_TOOL_PATH,
        "reconstruction_contract_v011",
    )
    common = reconstruction_module.load_common(repo_root)

    view_paths = {
        "condition-v01": REHEARSAL_ROOT / "inputs" / "view-v01.json",
        "condition-v02": REHEARSAL_ROOT / "inputs" / "view-v02.json",
    }
    write_json(repo_root, view_paths["condition-v01"], view_v01())
    write_json(repo_root, view_paths["condition-v02"], view_v02())
    variant_path = REHEARSAL_ROOT / "inputs" / "variant-envelope.json"
    write_json(repo_root, variant_path, variant_envelope())

    for condition_id in ("condition-v01", "condition-v02"):
        suffix = condition_id[-3:]
        task_id = f"task.reconstruct.{suffix}"
        template_path = (
            REHEARSAL_ROOT
            / "inputs"
            / f"reconstruction-response-{suffix}.template.json"
        )
        task_path = (
            REHEARSAL_ROOT
            / "inputs"
            / f"reconstruction-{condition_id}.task.json"
        )
        base_task = common_task_fields(
            repo_root,
            artifact_type="reconstruction_task_packet",
            case_ids=["CA-R2"],
            condition_id=condition_id,
            instructions=reconstruction_instructions(),
            input_artifacts=[],
            stage1_submission_required=False,
            task_id=task_id,
        )
        base_task["target_view_sha256"] = sha256_bytes(
            (repo_root / view_paths[condition_id]).read_bytes()
        )
        contract = reconstruction_module.derive_participant_contract(
            common,
            base_task,
            response_schema,
            role_schema,
            response_schema_sha256=response_sha,
            role_schema_sha256=role_sha,
        )
        template = reconstruction_template(
            contract,
            task_id,
            condition_id,
            response_schema,
            response_sha,
        )
        write_json(repo_root, template_path, template)
        task = copy.deepcopy(base_task)
        task["input_artifacts"] = [
            artifact_reference(
                repo_root,
                f"view.{suffix}",
                view_paths[condition_id],
            ),
            artifact_reference(
                repo_root,
                template["template_id"],
                template_path,
            ),
        ]
        write_json(repo_root, task_path, task)

    prediction_task_path = (
        REHEARSAL_ROOT / "inputs" / "prediction-neutral.task.json"
    )
    prediction_template_path = (
        REHEARSAL_ROOT / "inputs" / "prediction-response.template.json"
    )
    prediction_task = common_task_fields(
        repo_root,
        artifact_type="prediction_task_packet",
        case_ids=["CA-R2"],
        condition_id=None,
        instructions=prediction_instructions(),
        input_artifacts=[],
        stage1_submission_required=True,
        task_id="task.predict.neutral",
    )
    prediction_task["allowed_configurations"] = [
        "config.baseline",
        "config.variant",
    ]
    prediction_task["allowed_observations"] = [
        {
            "allowed_value_types": [
                "integer",
                "status",
            ],
            "description": (
                "第二步更新完成后的 state.total 精确计数"
            ),
            "observation_id": "obs.total-at-stop",
            "tolerance_rule_id": "tol.synthetic.exact",
            "unit": "count",
        }
    ]
    prediction_task["tolerance_rule_refs"] = [
        "tol.synthetic.exact",
    ]
    prediction_task["variant_interventions"] = [
        {
            "baseline_value": {
                "serialized_value": "0",
                "unit": None,
                "value_type": "integer",
            },
            "case_id": "CA-R2",
            "invariant_ids": [
                "inv.initial-state",
                "inv.input-trace",
                "inv.operation-count",
                "inv.operation-identity",
                "inv.step-order",
                "inv.output-contract",
                "inv.stop-boundary",
            ],
            "observation_ids": [
                "obs.total-at-stop",
            ],
            "stop_boundary_id": "stop.after-step-2",
            "variable_id": "v-q",
            "variant_value": {
                "serialized_value": "1",
                "unit": None,
                "value_type": "integer",
            },
        }
    ]
    contract = prediction_module.derive_participant_contract(
        prediction_task,
        response_schema,
        role_schema,
        response_schema_sha256=response_sha,
        role_schema_sha256=role_sha,
    )
    prediction_template_value = prediction_template(
        contract,
        response_schema,
        response_sha,
    )
    write_json(
        repo_root,
        prediction_template_path,
        prediction_template_value,
    )
    prediction_task["input_artifacts"] = [
        artifact_reference(
            repo_root,
            "envelope.rehearsal-006.stage2",
            variant_path,
        ),
        artifact_reference(
            repo_root,
            prediction_template_value["template_id"],
            prediction_template_path,
        ),
    ]
    write_json(repo_root, prediction_task_path, prediction_task)

    positive_root = REHEARSAL_ROOT / "fixtures" / "positive"
    negative_root = REHEARSAL_ROOT / "fixtures" / "negative"
    minimal = reconstruction_payload()
    write_json(
        repo_root,
        positive_root / "reconstruction-minimal.payload.json",
        minimal,
    )
    exposure = reconstruction_payload()
    exposure["pollution"]["integrity_exposures"] = [
        {
            "affected_case_ids": [
                "CA-R2",
            ],
            "description": "synthetic rehearsal exposure",
            "evidence": "fixture-only evidence",
            "exposure_type": "other_condition",
            "occurred_at": None,
            "stage": "reconstruction",
            "status": "confirmed",
        }
    ]
    write_json(
        repo_root,
        positive_root / "reconstruction-with-exposure.payload.json",
        exposure,
    )
    write_json(
        repo_root,
        positive_root / "prediction-determinate.payload.json",
        prediction_determinate_payload(),
    )
    indeterminate = prediction_indeterminate_payload()
    write_json(
        repo_root,
        positive_root
        / "prediction-indeterminate-two-alternatives.payload.json",
        indeterminate,
    )
    uppercase = reconstruction_payload()
    uppercase["reconstruction_answers"][0]["recovered_facts"] = [
        {
            "claim": "synthetic invalid local ID",
            "fact_id": "Fact.Uppercase",
            "recovery_status": "recovered",
            "supporting_record_ids": [],
        }
    ]
    write_json(
        repo_root,
        negative_root / "reconstruction-uppercase-local-id.payload.json",
        uppercase,
    )
    incomplete = copy.deepcopy(indeterminate)
    incomplete["prediction_answers"][0]["compatible_alternatives"][1][
        "expectations"
    ].pop()
    write_json(
        repo_root,
        negative_root / "prediction-incomplete-alternative.payload.json",
        incomplete,
    )
    fixed_template = copy.deepcopy(prediction_template_value)
    for expectation_item in fixed_template["template_payload"][
        "prediction_answers"
    ][0]["expectations"]:
        expectation_item["value"]["unit"] = "count"
    write_json(
        repo_root,
        negative_root / "prediction-fixed-unit.template.json",
        fixed_template,
    )
    write_json(
        repo_root,
        REHEARSAL_ROOT / "fixtures" / "expected-results.json",
        {
            "artifact_type": "rehearsal_fixture_expectations",
            "artifact_version": "0.1.0",
            "checks": [
                {
                    "expected": "pass",
                    "fixture": (
                        "positive/reconstruction-minimal.payload.json"
                    ),
                },
                {
                    "expected": "pass",
                    "fixture": (
                        "positive/reconstruction-with-exposure.payload.json"
                    ),
                },
                {
                    "expected": "pass",
                    "fixture": (
                        "positive/prediction-determinate.payload.json"
                    ),
                },
                {
                    "expected": "pass",
                    "fixture": (
                        "positive/prediction-indeterminate-two-"
                        "alternatives.payload.json"
                    ),
                },
                {
                    "expected": "fail",
                    "failure_contains": "does not match",
                    "fixture": (
                        "negative/reconstruction-uppercase-local-id."
                        "payload.json"
                    ),
                },
                {
                    "expected": "fail",
                    "failure_contains": (
                        "must cover each configuration/observation pair"
                    ),
                    "fixture": (
                        "negative/prediction-incomplete-alternative."
                        "payload.json"
                    ),
                },
                {
                    "expected": "fail",
                    "failure_contains": "value/unit",
                    "fixture": (
                        "negative/prediction-fixed-unit.template.json"
                    ),
                },
            ],
            "formal_input_access": "forbidden",
            "run_id": RUN_ID,
        },
    )


def main() -> int:
    repo_root = Path.cwd().resolve()
    try:
        materialize(repo_root)
    except (
        MaterializeError,
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
    print(
        json.dumps(
            {
                "rehearsal_root": REHEARSAL_ROOT.as_posix(),
                "status": "materialized",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
