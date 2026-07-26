#!/usr/bin/env python3
"""Synchronize the stage-two prediction task with its neutral envelope."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


TASK_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "task-packet-0.1.2.schema.json"
)


class TaskBuildError(RuntimeError):
    """A deterministic task-build failure."""


def read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r\n" in raw:
        raise TaskBuildError(f"non-canonical UTF-8 input: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise TaskBuildError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def intervention_for_task(value: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "baseline_value",
        "case_id",
        "formal_input_spec",
        "initial_state_specs",
        "invariant_ids",
        "invariant_specs",
        "observation_ids",
        "stop_boundary_id",
        "stop_boundary_spec",
        "tolerance_specs",
        "variable_id",
        "variant_value",
    }
    result = {
        key: copy.deepcopy(child)
        for key, child in value.items()
        if key in allowed
    }
    if set(result) != allowed:
        raise TaskBuildError(
            f"envelope intervention is incomplete for {value.get('case_id')}"
        )
    return result


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-task", type=Path, required=True)
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--response-template", type=Path, required=True)
    parser.add_argument("--response-schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    task = read_json(args.base_task)
    envelope = read_json(args.envelope)
    response_template = read_json(args.response_template)
    response_schema = read_json(args.response_schema)
    if envelope.get("artifact_type") != "variant_envelope":
        raise TaskBuildError("unexpected envelope artifact type")
    if (
        response_template.get("artifact_type") != "prediction_response_template"
        or response_template.get("stage") != "prediction"
    ):
        raise TaskBuildError("unexpected response-template kind")
    if not response_schema.get("$id"):
        raise TaskBuildError("response schema has no canonical $id")
    target_response_schema = response_template.get("target_response_schema")
    if not isinstance(target_response_schema, dict) or target_response_schema.get(
        "sha256"
    ) != sha256(args.response_schema):
        raise TaskBuildError(
            "response template is not bound to the supplied response schema"
        )

    interventions = envelope["case_interventions"]
    task["$schema"] = TASK_SCHEMA_ID
    task["artifact_version"] = "0.1.2"
    task["input_artifacts"] = [
        {
            "artifact_id": envelope["envelope_id"],
            "path": (
                "research/calibration-tests/continuous-action-pilot/runs/"
                "continuous-001/inputs/stage2-variant-envelope.json"
            ),
            "sha256": sha256(args.envelope),
        },
        {
            "artifact_id": "template.prediction.continuous-001",
            "path": (
                "research/calibration-tests/continuous-action-pilot/runs/"
                "continuous-001/inputs/prediction-response.template.json"
            ),
            "sha256": sha256(args.response_template),
        },
    ]
    task["instructions"] = [
        (
            "在完成并冻结第一阶段后，继续只使用原会话的条件视图、自己的冻结重构、"
            "本任务、中性变体信封和回答模板；不得使用工具、网络、共享工作区、包外"
            "文件、另一条件、其他提交、真值或结果。"
        ),
        (
            "复制回答模板中的 template_payload，替换全部尖括号占位符，返回一个符合"
            "回答 Schema 的单一 JSON 对象；不要返回模板外壳、Markdown 代码围栏或附加文字。"
        ),
        (
            "每案的主 expectations 必须恰好覆盖中性信封给出的两个配置与全部 "
            "observation_id 的笛卡尔积，不得遗漏、重复或增加配置—观察量组合。"
        ),
        (
            "变量 ID 与数值本身不解释因果职责；预测只能由第一阶段允许材料、自己的"
            "冻结重构和信封所列干预与不变量推出。"
        ),
        (
            "tol.a.0001、tol.b.0001 与 tol.c.0001 使用精确离散值、标识或计数相等；"
            "tol.b.0002 只比较冻结数值量化后的 negative、zero、positive 三种方向类别，"
            "正零和负零都编码为 zero；tol.c.0002 的绝对毫秒差阈值为零。"
        ),
        (
            "prediction_status 只能是 determinate 或 indeterminate。若为 indeterminate，"
            "主 expectations 使用 status/indeterminate，并至少给出两个仍符合材料、但对"
            "同一配置—观察量产生不同预测的完整 compatible_alternatives。"
        ),
        (
            "每个 compatible_alternatives 项必须给出完整的两个配置与全部观察量组合；"
            "不能用一个猜测结果代替缺失的结构推导。"
        ),
        (
            "不变量和停止点由执行设施按信封定义核验；参与者需要声明其推导依赖与"
            "无法判定条件，但不预测运行后的 held 或 violated 值。"
        ),
        (
            "confidence_percent 必须是零至一百的整数；推导引用只使用允许记录、关系、"
            "变量、不变量、观察量、时间基准、容差和停止边界 ID。"
        ),
        (
            "污染自报枚举与第一阶段相同；stage_update_note 只记录本阶段实际新增暴露，"
            "不得写入未见内容。"
        ),
        (
            "不要填写运行、任务、条件、actor、session、提交时间、输入散列、前阶段散列"
            "或审核字段；这些字段由保管工具机械生成。"
        ),
    ]
    task["output_schema"] = {
        "path": (
            "research/calibration-tests/continuous-action-pilot/schema/"
            "blind-response-interface-0.1.0.schema.json"
        ),
        "sha256": sha256(args.response_schema),
    }
    assembled_schema = task.get("assembled_output_schema")
    if not isinstance(assembled_schema, dict) or assembled_schema.get("path") != (
        "research/calibration-tests/continuous-action-pilot/schema/"
        "role-submission-0.1.2.schema.json"
    ):
        raise TaskBuildError(
            "base task must retain the mechanical role-submission assembly schema"
        )
    task["stop_boundary_refs"] = [
        value["stop_boundary_id"]
        for value in interventions
    ]
    task["tolerance_rule_refs"] = [
        spec["tolerance_rule_id"]
        for value in interventions
        for spec in value["tolerance_specs"]
    ]
    task["variant_interventions"] = [
        intervention_for_task(value)
        for value in interventions
    ]
    output = canonical_bytes(task)
    args.output.write_bytes(output)
    print(
        json.dumps(
            {
                "formal_input_executed": False,
                "formal_result_created": False,
                "task_sha256": hashlib.sha256(output).hexdigest(),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
