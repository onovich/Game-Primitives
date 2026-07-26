#!/usr/bin/env python3
"""Build the identity-neutral stage-two fixture envelope.

The script verifies the three frozen formal-input files, translates only
structural identifiers through the same opaque-ID map as the view generator,
and emits no prediction or execution result.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "variant-envelope-0.1.0.schema.json"
)
CREATED_AT = "2026-07-26T21:30:00Z"


class EnvelopeError(RuntimeError):
    """A frozen-input, identifier, or validation failure."""


def read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise EnvelopeError(f"UTF-8 BOM is forbidden: {path}")
    if b"\r\n" in raw:
        raise EnvelopeError(f"CRLF is forbidden: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise EnvelopeError(f"expected a JSON object: {path}")
    return value


def scalar(value: str, value_type: str, unit: str | None = None) -> dict[str, Any]:
    return {
        "serialized_value": value,
        "unit": unit,
        "value_type": value_type,
    }


def field(
    field_id: str,
    value: str,
    value_type: str,
    unit: str | None = None,
) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "value": scalar(value, value_type, unit),
    }


def load_view_generator(path: Path) -> Any:
    module_name = "continuous_action_view_generator_for_envelope"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise EnvelopeError(f"cannot load view generator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case_index(canonical: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {
        case["case_scope"]["case_id"]: case
        for case in canonical.get("cases", [])
    }
    if set(result) != {"CA-R1", "CA-R2", "CA-R3"}:
        raise EnvelopeError("canonical encoding must contain CA-R1, CA-R2, and CA-R3")
    return result


def id_maps(canonical: dict[str, Any], generator: Any) -> dict[str, dict[str, str]]:
    return {
        case["case_scope"]["case_id"]: generator.build_opaque_map(case, ordinal)
        for ordinal, case in enumerate(canonical["cases"], start=1)
    }


def require_map(mapping: dict[str, str], *identifiers: str) -> None:
    missing = [identifier for identifier in identifiers if identifier not in mapping]
    if missing:
        raise EnvelopeError(f"canonical-to-blind ID map is missing: {missing}")


def field_value_map(event: dict[str, Any]) -> dict[str, str]:
    return {
        item["field_id"]: item["value"]["serialized_value"]
        for item in event["fields"]
    }


def verify_r1(value: dict[str, Any]) -> None:
    if value.get("case_id") != "CA-R1":
        raise EnvelopeError("R1 formal input has the wrong case_id")
    initial = {
        item["field_id"]: item["value"]["serialized_value"]
        for item in value["fixture_configuration_fields"]
    }
    expected_initial = {
        "ai-enabled": "false",
        "initial.buffered-action": "none",
        "initial.current-action": "action.stand",
        "initial.hit-count": "0",
        "initial.hit-stun-frames": "0",
        "opponent-contact-enabled": "false",
    }
    if initial != expected_initial:
        raise EnvelopeError("R1 frozen initial state changed")
    events = value["input_events"]
    expected_attack = ["true", "false", "true", "false", "false", "false", "false"]
    if len(events) != 7:
        raise EnvelopeError("R1 must contain seven ordered fixture updates")
    for index, event in enumerate(events):
        fields = field_value_map(event)
        if event["sequence_index"] != index:
            raise EnvelopeError("R1 sequence index changed")
        if event["at"]["serialized_value"] != str(index):
            raise EnvelopeError("R1 fixture-update coordinate changed")
        if fields != {
            "input.attack-held": expected_attack[index],
            "input.horizontal": "0",
        }:
            raise EnvelopeError("R1 frozen input event changed")


def verify_r2(value: dict[str, Any]) -> None:
    if value.get("case_id") != "CA-R2":
        raise EnvelopeError("R2 formal input has the wrong case_id")
    initial = {
        item["field_id"]: item["value"]["serialized_value"]
        for item in value["fixture_configuration_fields"]
    }
    expected_subset = {
        "fixture.collision-world": "empty",
        "fixture.gravity": "800",
        "fixture.origin": "0,0,4096",
        "fixture.platform-scope": "MSVC-x64",
        "fixture.pmove-fixed": "true",
        "fixture.pmove-msec": "8",
        "fixture.speed": "320",
        "fixture.velocity": "0,0,0",
        "fixture.yaw": "0",
    }
    for key, expected in expected_subset.items():
        if initial.get(key) != expected:
            raise EnvelopeError(f"R2 frozen initial field changed: {key}")
    events = value["input_events"]
    if len(events) != 25:
        raise EnvelopeError("R2 must contain twenty-five ordered steps")
    for index, event in enumerate(events):
        fields = field_value_map(event)
        if event["sequence_index"] != index:
            raise EnvelopeError("R2 sequence index changed")
        if event["at"]["serialized_value"] != str((index + 1) * 8):
            raise EnvelopeError("R2 command time changed")
        expected_pair = ("127", "0") if index < 5 else ("0", "127")
        if (
            fields.get("cmd.forwardmove"),
            fields.get("cmd.rightmove"),
        ) != expected_pair:
            raise EnvelopeError("R2 direction trace changed")


def verify_r3(value: dict[str, Any]) -> None:
    if value.get("case_id") != "CA-R3":
        raise EnvelopeError("R3 formal input has the wrong case_id")
    initial = {
        item["field_id"]: item["value"]["serialized_value"]
        for item in value["fixture_configuration_fields"]
    }
    if initial != {
        "input.candidate-count": "1",
        "object.start-time": "1000",
        "object.type": "hit-circle",
        "rules.overall-difficulty": "5",
    }:
        raise EnvelopeError("R3 frozen initial state changed")
    events = value["input_events"]
    if len(events) != 1 or events[0]["sequence_index"] != 0:
        raise EnvelopeError("R3 must contain one candidate event")
    if events[0]["at"]["serialized_value"] != "1000":
        raise EnvelopeError("R3 candidate coordinate changed")
    if field_value_map(events[0]) != {
        "action": "left-button",
        "position.x": "256",
        "position.y": "192",
        "target": "single-hit-area",
    }:
        raise EnvelopeError("R3 candidate event changed")


def verify_neutral_bindings(
    mappings: dict[str, dict[str, str]],
    formal_inputs: dict[str, dict[str, Any]],
) -> None:
    canonical_ids = {
        "CA-R1": (
            "input.r1.fixed-update-trace",
            "tb.r1.fixed-update",
            "stop.r1.update-6",
        ),
        "CA-R2": (
            "input.r2.usercmd-trace",
            "tb.r2.command-time",
            "stop.r2.200-ms",
        ),
        "CA-R3": (
            "input.r3.single-candidate",
            "tb.r3.gameplay-clock",
            "stop.r3.result-committed",
        ),
    }
    for case_id, (input_id, time_base_id, stop_id) in canonical_ids.items():
        mapping = mappings[case_id]
        formal_input = formal_inputs[case_id]
        actual = (
            formal_input.get("formal_input_id"),
            formal_input.get("time_base", {}).get("time_base_id"),
            formal_input.get("stop_boundary_id"),
        )
        expected = (
            mapping[input_id],
            mapping[time_base_id],
            mapping[stop_id],
        )
        if actual != expected:
            raise EnvelopeError(
                f"{case_id} neutral input/time/stop binding changed: "
                f"expected {expected}, got {actual}"
            )


def invariant(invariant_id: str, description: str) -> dict[str, str]:
    return {
        "description": description,
        "invariant_id": invariant_id,
    }


def tolerance(
    tolerance_rule_id: str,
    comparison_kind: str,
    threshold: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "comparison_kind": comparison_kind,
        "threshold": threshold,
        "tolerance_rule_id": tolerance_rule_id,
    }


def make_event(
    event_id: str,
    sequence_index: int,
    at_value: str,
    at_unit: str,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "at": scalar(at_value, "integer", at_unit),
        "event_id": event_id,
        "fields": fields,
        "sequence_index": sequence_index,
    }


def build_envelope(
    canonical: dict[str, Any],
    mappings: dict[str, dict[str, str]],
) -> dict[str, Any]:
    cases = case_index(canonical)
    r1 = mappings["CA-R1"]
    r2 = mappings["CA-R2"]
    r3 = mappings["CA-R3"]
    require_map(
        r1,
        "variable.r1.whiff-cancel-permission",
        "input.r1.fixed-update-trace",
        "tb.r1.fixed-update",
        "stop.r1.update-6",
        "medium.r1.fighter-state-machine",
        "signal.r1.attack-button",
    )
    require_map(
        r2,
        "variable.r2.input-sampling-policy",
        "input.r2.usercmd-trace",
        "tb.r2.command-time",
        "stop.r2.200-ms",
        "channel.r2.origin",
        "channel.r2.velocity",
        "input.r2.raw-command",
    )
    require_map(
        r3,
        "variable.r3.adjudication-schedule",
        "input.r3.single-candidate",
        "tb.r3.gameplay-clock",
        "stop.r3.result-committed",
        "process.r3.drawable-adjudicator",
        "channel.r3.input-permission",
        "input.r3.candidate-press",
    )
    if cases["CA-R1"]["case_scope"]["controlled_variable_id"] not in r1:
        raise EnvelopeError("R1 controlled variable is not encoded")

    r1_events = []
    for index, attack in enumerate(
        ("true", "false", "true", "false", "false", "false", "false")
    ):
        r1_events.append(
            make_event(
                f"event.a.{index + 1:04d}",
                index,
                str(index),
                "fixture_update",
                [field(r1["signal.r1.attack-button"], attack, "boolean")],
            )
        )

    r2_events = []
    for index in range(25):
        pair = "axis1_127_axis2_0" if index < 5 else "axis1_0_axis2_127"
        r2_events.append(
            make_event(
                f"event.b.{index + 1:04d}",
                index,
                str((index + 1) * 8),
                "millisecond",
                [field(r2["input.r2.raw-command"], pair, "status", "direction_pair")],
            )
        )

    r3_events = [
        make_event(
            "event.c.0001",
            0,
            "1000",
            "millisecond",
            [field(r3["input.r3.candidate-press"], "accepted_candidate", "status")],
        )
    ]

    r1_invariants = [
        invariant("inv.a.0001", "两配置使用同一冻结构建、初始状态与观察仪器。"),
        invariant("inv.a.0002", "两配置的两个动作定义、动作帧与映射关系完全相同。"),
        invariant("inv.a.0003", "两配置的请求缓存窗口、执行窗口与更新顺序完全相同。"),
        invariant("inv.a.0004", "两配置接收逐字节相同的七次输入更新。"),
        invariant("inv.a.0005", "整个片段无接触、无命中，另一实体与人工控制均不参与。"),
        invariant("inv.a.0006", "两配置使用同一停止点、观察字段与记录粒度。"),
    ]
    r2_invariants = [
        invariant("inv.b.0001", "两配置使用同一冻结构建、兼容层与观察仪器。"),
        invariant("inv.b.0002", "两配置接收逐字节相同的二十五步原始方向序列。"),
        invariant("inv.b.0003", "两配置的初始位置、速度、朝向与过程模式完全相同。"),
        invariant("inv.b.0004", "两配置使用相同的八毫秒固定子步与二百毫秒停止点。"),
        invariant("inv.b.0005", "两配置的加速、摩擦、重力、量化与写回公式完全相同。"),
        invariant("inv.b.0006", "整个片段保持在声明过程内，碰撞世界为空且接触数为零。"),
        invariant("inv.b.0007", "除控制变量指定的输入选取关系外，不改变任何规则关系。"),
    ]
    r3_invariants = [
        invariant("inv.c.0001", "两配置使用同一冻结构建与同一观察仪器。"),
        invariant("inv.c.0002", "两配置都只有一个对象，其难度值为五，起始时刻为一千毫秒。"),
        invariant("inv.c.0003", "两配置都在对象中心于起始时刻接受一次相同候选。"),
        invariant("inv.c.0004", "两配置都恰好一次调用同一裁定路径。"),
        invariant("inv.c.0005", "两配置使用同一手动规则时钟，只允许控制变量改变调用延迟。"),
        invariant("inv.c.0006", "分类半窗固定为四十九点五毫秒与九十九点五毫秒。"),
        invariant("inv.c.0007", "主试验的呈现开关保持开启；呈现负对照与主试验分离。"),
    ]

    return {
        "$schema": SCHEMA_ID,
        "artifact_type": "variant_envelope",
        "artifact_version": "0.1.0",
        "behavior_scope": "structural_only",
        "blinding_assertions": {
            "condition_mapping_included": False,
            "expected_results_included": False,
            "source_identity_included": False,
            "source_paths_included": False,
        },
        "case_interventions": [
            {
                "allowed_configuration_ids": ["config.baseline", "config.variant"],
                "baseline_value": scalar("0", "integer"),
                "case_id": "CA-R1",
                "formal_input_spec": {
                    "events": r1_events,
                    "formal_input_id": r1["input.r1.fixed-update-trace"],
                    "time_base": {
                        "origin": scalar("0", "integer", "fixture_update"),
                        "tick_unit": "fixture_update",
                        "time_base_id": r1["tb.r1.fixed-update"],
                    },
                },
                "initial_state_specs": [
                    field(
                        r1["medium.r1.fighter-state-machine"],
                        "idle_no_stun_no_buffer_zero_hits_no_contact",
                        "status",
                    )
                ],
                "invariant_ids": [item["invariant_id"] for item in r1_invariants],
                "invariant_specs": r1_invariants,
                "observation_ids": [
                    "obs.a.0001",
                    "obs.a.0002",
                    "obs.a.0003",
                    "obs.a.0004",
                    "obs.a.0005",
                ],
                "stop_boundary_id": r1["stop.r1.update-6"],
                "stop_boundary_spec": {
                    "boundary_kind": "after_event",
                    "coordinate": scalar("6", "integer", "fixture_update"),
                    "description": "第七次输入更新完成并记录全部声明观察量后停止。",
                    "stop_boundary_id": r1["stop.r1.update-6"],
                },
                "tolerance_rule_ids": ["tol.a.0001"],
                "tolerance_specs": [tolerance("tol.a.0001", "exact")],
                "variable_id": r1["variable.r1.whiff-cancel-permission"],
                "variant_value": scalar("1", "integer"),
            },
            {
                "allowed_configuration_ids": ["config.baseline", "config.variant"],
                "baseline_value": scalar("0", "integer"),
                "case_id": "CA-R2",
                "formal_input_spec": {
                    "events": r2_events,
                    "formal_input_id": r2["input.r2.usercmd-trace"],
                    "time_base": {
                        "origin": scalar("0", "integer", "millisecond"),
                        "tick_unit": "millisecond",
                        "time_base_id": r2["tb.r2.command-time"],
                    },
                },
                "initial_state_specs": [
                    field(
                        r2["channel.r2.origin"],
                        "axis1_0_axis2_0_altitude_4096",
                        "status",
                        "coordinate_triplet",
                    ),
                    field(
                        r2["channel.r2.velocity"],
                        "axis1_0_axis2_0_vertical_0",
                        "status",
                        "velocity_triplet",
                    ),
                ],
                "invariant_ids": [item["invariant_id"] for item in r2_invariants],
                "invariant_specs": r2_invariants,
                "observation_ids": [
                    "obs.b.0001",
                    "obs.b.0002",
                    "obs.b.0003",
                    "obs.b.0004",
                    "obs.b.0005",
                ],
                "stop_boundary_id": r2["stop.r2.200-ms"],
                "stop_boundary_spec": {
                    "boundary_kind": "rule_time_reached",
                    "coordinate": scalar("200", "integer", "millisecond"),
                    "description": "第二十五个八毫秒子步完成并记录声明状态后停止。",
                    "stop_boundary_id": r2["stop.r2.200-ms"],
                },
                "tolerance_rule_ids": ["tol.b.0001", "tol.b.0002"],
                "tolerance_specs": [
                    tolerance("tol.b.0001", "exact"),
                    tolerance("tol.b.0002", "zero_or_nonzero_direction"),
                ],
                "variable_id": r2["variable.r2.input-sampling-policy"],
                "variant_value": scalar("1", "integer"),
            },
            {
                "allowed_configuration_ids": ["config.baseline", "config.variant"],
                "baseline_value": scalar("0", "integer", "millisecond"),
                "case_id": "CA-R3",
                "formal_input_spec": {
                    "events": r3_events,
                    "formal_input_id": r3["input.r3.single-candidate"],
                    "time_base": {
                        "origin": scalar("0", "integer", "millisecond"),
                        "tick_unit": "millisecond",
                        "time_base_id": r3["tb.r3.gameplay-clock"],
                    },
                },
                "initial_state_specs": [
                    field(
                        r3["process.r3.drawable-adjudicator"],
                        "single_object_difficulty5_start1000_centered",
                        "status",
                    ),
                    field(
                        r3["channel.r3.input-permission"],
                        "open",
                        "status",
                    ),
                ],
                "invariant_ids": [item["invariant_id"] for item in r3_invariants],
                "invariant_specs": r3_invariants,
                "observation_ids": [
                    "obs.c.0001",
                    "obs.c.0002",
                    "obs.c.0003",
                    "obs.c.0004",
                    "obs.c.0005",
                    "obs.c.0006",
                ],
                "stop_boundary_id": r3["stop.r3.result-committed"],
                "stop_boundary_spec": {
                    "boundary_kind": "first_declared_condition",
                    "coordinate": None,
                    "description": "正式结果、结果通知与同一对象的许可关闭均记录后立即停止。",
                    "stop_boundary_id": r3["stop.r3.result-committed"],
                },
                "tolerance_rule_ids": ["tol.c.0001", "tol.c.0002"],
                "tolerance_specs": [
                    tolerance("tol.c.0001", "exact"),
                    tolerance(
                        "tol.c.0002",
                        "absolute_delta",
                        scalar("0", "integer", "millisecond"),
                    ),
                ],
                "variable_id": r3["variable.r3.adjudication-schedule"],
                "variant_value": scalar("75", "integer", "millisecond"),
            },
        ],
        "created_at": CREATED_AT,
        "envelope_id": "envelope.continuous-001.stage2.v0.1.0",
        "run_id": "continuous-001",
    }


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--view-generator", type=Path, required=True)
    parser.add_argument("--r1-input", type=Path, required=True)
    parser.add_argument("--r2-input", type=Path, required=True)
    parser.add_argument("--r3-input", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    canonical = read_json(args.canonical)
    r1_input = read_json(args.r1_input)
    r2_input = read_json(args.r2_input)
    r3_input = read_json(args.r3_input)
    verify_r1(r1_input)
    verify_r2(r2_input)
    verify_r3(r3_input)
    generator = load_view_generator(args.view_generator)
    mappings = id_maps(canonical, generator)
    verify_neutral_bindings(
        mappings,
        {
            "CA-R1": r1_input,
            "CA-R2": r2_input,
            "CA-R3": r3_input,
        },
    )
    envelope = build_envelope(canonical, mappings)
    schema = read_json(args.schema)
    Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    ).validate(envelope)
    output = canonical_bytes(envelope)
    args.output.write_bytes(output)
    print(
        json.dumps(
            {
                "envelope_sha256": hashlib.sha256(output).hexdigest(),
                "formal_input_executed": False,
                "formal_result_created": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
