#!/usr/bin/env python3
"""Generate the two deterministic continuous-action blind views.

The generator deliberately treats the canonical encoding as the only semantic
input.  The projection specification selects the two fixed projections and
binds the exact generator file through the SHA-256 suffix of each projection
identifier.  No execution result or prediction artifact is read.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


GENERATOR_ID = "generate-continuous-views"
GENERATOR_VERSION = "0.1.0"
SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "ca-sr-artifact-0.1.0.schema.json"
)
V01_PREFIX = "projection-v01.gsha256-"
V02_PREFIX = "projection-v02.gsha256-"
CANONICAL_JSON_KWARGS = {
    "ensure_ascii": False,
    "indent": 2,
    "sort_keys": True,
}

V01_RULE_SIGNATURES = (
    ("include_path", "/cases"),
    ("redact_text", "/cases/references/audit_identity"),
    ("remove_path", "/cases/provenance_refs"),
    ("remove_path", "/cases/source_issues"),
    ("rename_id", "/cases"),
)
V02_RULE_SIGNATURES = (
    ("include_path", "/cases/case_scope"),
    ("include_path", "/cases/references"),
    ("include_path", "/cases/state_channels"),
    ("include_path", "/cases/trace_contract"),
    ("remove_path", "/cases/composition_edges"),
    ("remove_path", "/cases/operational_edges"),
    ("remove_path", "/cases/operational_records"),
    ("remove_path", "/cases/rules"),
    ("remove_path", "/cases/source_issues"),
    ("remove_path", "/cases/temporal_edges"),
    ("remove_path", "/cases/time_bases"),
    ("rename_id", "/cases"),
    ("retain_endpoint", "/cases/case_scope/observation_start"),
    ("retain_endpoint", "/cases/case_scope/observation_stop"),
)
REQUIRED_FORBIDDEN_TOKENS = frozenset(
    {
        "AllJudged",
        "ApplyResult",
        "ArmedState",
        "CanBeHit",
        "Clock",
        "CommonActionID",
        "DifficultyRange",
        "DrawableHitCircle",
        "DrawableHitObject",
        "F00",
        "FOOTSIES",
        "Fight",
        "GameplayRate",
        "HitCircle",
        "HitReceptor",
        "HitResult",
        "HitWindows",
        "InputManager",
        "JudgementResult",
        "N_ATTACK",
        "N_SPECIAL",
        "OD5",
        "OnNewResult",
        "OnPressed",
        "PM_AirMove",
        "PM_NORMAL",
        "Pmove",
        "PmoveSingle",
        "Quake",
        "Quake III",
        "RawTime",
        "RequestAction",
        "STAND",
        "SnapVector",
        "StartTime",
        "Time.Current",
        "UpdateFightState",
        "canCancelOnWhiff",
        "cmd.serverTime",
        "commandTime",
        "finalTime",
        "frametime",
        "hifight",
        "id-Software",
        "lazer",
        "osu!",
        "osu!lazer",
        "playerState",
        "playerState_t",
        "pm->cmd",
        "pmove_t",
        "ppy",
        "r1.",
        "r2.",
        "r3.",
        "raw_cmd",
        "rich",
        "serverTime",
        "atomic",
        "used_cmd",
        "usercmd",
        "wishspeed",
    }
)

STRUCTURAL_STRING_KEYS = {
    "$schema",
    "allowed_kinds",
    "artifact_type",
    "artifact_version",
    "base_type",
    "case_id",
    "condition_id",
    "coordinate_type",
    "kind",
    "projection_id",
    "record_type",
    "representation_version",
    "role_id",
    "run_id",
    "stage_kind",
    "status",
    "test_role",
    "value_type",
}
DIRECT_ID_KEYS = {
    "channel_id",
    "controlled_variable_id",
    "derivation_algorithm_id",
    "edge_id",
    "formal_input_ref",
    "from_id",
    "from_milestone_id",
    "issue_id",
    "milestone_id",
    "permission_id",
    "raw_trace_ref",
    "record_id",
    "rule_id",
    "stage_id",
    "target_time_base_id",
    "time_base_id",
    "to_id",
    "to_milestone_id",
    "transition_id",
}
DIRECT_ID_LIST_KEYS = {
    "condition_ids",
    "from_ids",
    "locator_refs",
    "scope_ids",
    "stop_condition_refs",
    "subject_ids",
    "time_base_refs",
    "to_ids",
    "tolerance_rule_refs",
}
REFERENCE_ID_KEYS = {
    "action_instance_ref",
    "action_ref",
    "adjudicator_ref",
    "candidate_occurrence_ref",
    "candidate_output_ref",
    "controlled_entity_ref",
    "effect_ref",
    "formal_event_ref",
    "implementation_medium_ref",
    "input_ref",
    "observer_ref",
    "output_ref",
    "owner_ref",
    "presentation_medium_ref",
    "process_ref",
    "resolution_ref",
    "scope_ref",
    "semantic_ref",
    "signal_ref",
    "source_ref",
    "time_base_ref",
}
TEXT_REPLACEMENTS = (
    ("canCancelOnWhiff", "失误取消许可"),
    ("CommonActionID", "动作类别"),
    ("N_ATTACK", "动作甲"),
    ("N_SPECIAL", "动作乙"),
    ("RequestAction", "动作请求入口"),
    ("UpdateFightState", "规则更新入口"),
    ("InputManager", "输入提供者"),
    ("Fighter", "受控实体"),
    ("FOOTSIES", "来源作品"),
    ("PM_AirMove", "空中运动更新"),
    ("PmoveSingle", "单步运动更新"),
    ("Pmove", "运动更新"),
    ("PM_NORMAL", "普通运动状态"),
    ("pmove_t", "运动上下文"),
    ("playerState_t", "受控状态"),
    ("playerState", "受控状态"),
    ("SnapVector", "数值量化"),
    ("usercmd", "输入命令"),
    ("serverTime", "命令时间"),
    ("commandTime", "状态时间"),
    ("finalTime", "终止时间"),
    ("raw_cmd", "原始命令"),
    ("used_cmd", "本步命令"),
    ("wishspeed", "期望速度"),
    ("frametime", "步长时间"),
    ("origin", "位置"),
    ("velocity", "速度"),
    ("accel", "加速度系数"),
    ("msec", "毫秒步长"),
    ("Quake III", "来源作品"),
    ("Quake", "来源作品"),
    ("DrawableHitCircle", "受裁定对象"),
    ("DrawableHitObject", "受裁定对象"),
    ("HitReceptor", "候选输入入口"),
    ("JudgementResult", "裁定结果"),
    ("HitWindows", "裁定窗口"),
    ("HitResult", "裁定结果"),
    ("AllJudged", "全部裁定状态"),
    ("CanBeHit", "输入许可检查"),
    ("OnPressed", "候选输入入口"),
    ("ApplyResult", "结果提交入口"),
    ("RawTime", "原始时间记录"),
    ("GameplayRate", "规则速率记录"),
    ("ArmedState", "对象准备状态"),
    ("OnNewResult", "结果通知"),
    ("Time.Current", "当前规则时间"),
    ("DifficultyRange", "难度范围"),
    ("StartTime", "起始规则时间"),
    ("osu!lazer", "来源作品"),
    ("osu!", "来源作品"),
    ("lazer", "来源作品"),
    ("F00", "受控实体"),
    ("STAND", "待机状态"),
    ("Fight", "规则更新"),
    ("buffer", "缓冲"),
    ("execute", "执行"),
    ("millisecond", "毫秒"),
    (" ms", " 毫秒"),
)
ASCII_CODE_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_.!:/<>-]*(?:->[A-Za-z0-9_.!:/<>-]+)?")
SOURCE_LOCATOR_TOKEN = re.compile(r"(?<![a-z0-9])r[123]\.[a-z0-9]", re.IGNORECASE)
ORIGINAL_INTERNAL_ID = re.compile(
    r"(?<![a-z0-9])(?:action|algorithm|channel|condition|effect|edge|entity|"
    r"event|input|lifecycle|medium|milestone|outcome|path|permission|process|"
    r"resolution|rule|scope|signal|state|stop|tb|time|transition|variable)"
    r"\.r[123]\.",
    re.IGNORECASE,
)


class ProjectionError(RuntimeError):
    """A deterministic input, projection, identity, or closure failure."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, **CANONICAL_JSON_KWARGS) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_canonical_json(path: Path, label: str) -> tuple[Any, bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ProjectionError(f"{label} must be UTF-8 without BOM")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    expected = canonical_bytes(value)
    if raw != expected:
        raise ProjectionError(f"{label} is not canonical JSON bytes")
    return value, raw


def read_schema_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ProjectionError("CA-SR artifact schema must be UTF-8 without BOM")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"CA-SR artifact schema is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ProjectionError("CA-SR artifact schema root must be an object")
    return value


def validate_schema(instance: Any, schema: dict[str, Any], label: str) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors[:8]
        )
        raise ProjectionError(f"{label} failed schema validation: {details}")


def projection_by_prefix(spec: dict[str, Any], prefix: str) -> dict[str, Any]:
    matches = [
        projection
        for projection in spec["projections"]
        if projection["projection_id"].startswith(prefix)
    ]
    if len(matches) != 1:
        raise ProjectionError(f"expected exactly one projection with prefix {prefix!r}")
    return matches[0]


def rule_signatures(projection: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple((rule["operation"], rule["path"]) for rule in projection["rules"])


def validate_projection_spec(
    spec: dict[str, Any],
    canonical_sha256: str,
    generator_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if spec["artifact_type"] != "projection_spec":
        raise ProjectionError("unknown projection-spec artifact type")
    if spec["generator_id"] != GENERATOR_ID:
        raise ProjectionError("projection spec names an unknown generator")
    if spec["generator_version"] != GENERATOR_VERSION:
        raise ProjectionError("projection spec names an unsupported generator version")
    if spec["canonical_encoding_sha256"] != canonical_sha256:
        raise ProjectionError("canonical encoding hash does not match projection spec")
    if len(spec["projections"]) != 2:
        raise ProjectionError("projection spec must contain exactly two projections")
    provided_forbidden = {token.casefold() for token in spec["forbidden_tokens"]}
    missing_forbidden = sorted(
        token
        for token in REQUIRED_FORBIDDEN_TOKENS
        if token.casefold() not in provided_forbidden
    )
    if missing_forbidden:
        raise ProjectionError(
            "projection spec omits required forbidden token(s): "
            + ", ".join(missing_forbidden)
        )

    view_one_spec = projection_by_prefix(spec, V01_PREFIX)
    view_two_spec = projection_by_prefix(spec, V02_PREFIX)
    expected_v01_id = V01_PREFIX + generator_sha256
    expected_v02_id = V02_PREFIX + generator_sha256
    if view_one_spec["projection_id"] != expected_v01_id:
        raise ProjectionError("v01 projection does not bind the exact generator hash")
    if view_two_spec["projection_id"] != expected_v02_id:
        raise ProjectionError("v02 projection does not bind the exact generator hash")
    if rule_signatures(view_one_spec) != V01_RULE_SIGNATURES:
        raise ProjectionError("v01 projection rule set or order is unknown")
    if rule_signatures(view_two_spec) != V02_RULE_SIGNATURES:
        raise ProjectionError("v02 projection rule set or order is unknown")
    return view_one_spec, view_two_spec


def sanitize_text(value: str) -> str:
    result = value
    for source, replacement in TEXT_REPLACEMENTS:
        result = re.sub(re.escape(source), replacement, result, flags=re.IGNORECASE)
    result = ASCII_CODE_TOKEN.sub("内部标识", result)
    result = re.sub(r"(?:内部标识[\s、，；：/|-]*){2,}", "内部标识", result)
    result = re.sub(r"[ \t]+", " ", result).strip()
    return result or "已声明文本。"


def fact_has_id_values(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "provenance_refs" in value
        and "status" in value
        and "values" in value
        and isinstance(value["values"], list)
    )


def fact_has_single_id(parent_key: str | None, value: Any) -> bool:
    return (
        parent_key in REFERENCE_ID_KEYS
        and isinstance(value, dict)
        and "provenance_refs" in value
        and "status" in value
        and "value" in value
    )


def collect_case_ids_in_order(
    node: Any,
    parent_key: str | None = None,
) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(candidate: Any) -> None:
        if isinstance(candidate, str) and candidate not in seen:
            seen.add(candidate)
            found.append(candidate)

    def visit(value: Any, key_from_parent: str | None = None) -> None:
        if fact_has_id_values(value):
            for candidate in value["values"]:
                add(candidate)
        if fact_has_single_id(key_from_parent, value):
            add(value["value"])
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"provenance_refs", "locator_refs"}:
                    continue
                if key in DIRECT_ID_KEYS:
                    add(child)
                elif key in DIRECT_ID_LIST_KEYS and isinstance(child, list):
                    for candidate in child:
                        add(candidate)
                elif key == "serialized_value" and value.get("value_type") in {
                    "id",
                    "id_set",
                }:
                    add(child)
                visit(child, key)
        elif isinstance(value, list):
            for child in value:
                visit(child, key_from_parent)

    visit(node, parent_key)
    return found


def collect_case_ids(node: Any, parent_key: str | None = None) -> set[str]:
    return set(collect_case_ids_in_order(node, parent_key))


def build_opaque_map(case: dict[str, Any], case_ordinal: int) -> dict[str, str]:
    original_ids = collect_case_ids_in_order(case)
    mapped: dict[str, str] = {}
    reverse: dict[str, str] = {}
    for opaque_ordinal, original in enumerate(original_ids, start=1):
        if opaque_ordinal > 9999:
            raise ProjectionError("case has more than 9999 internal identifiers")
        opaque = f"o.{chr(96 + case_ordinal)}.{opaque_ordinal:04d}"
        if opaque in reverse and reverse[opaque] != original:
            raise ProjectionError("opaque identifier collision")
        mapped[original] = opaque
        reverse[opaque] = original
    return mapped


def build_opaque_value_map(
    case: dict[str, Any],
    case_ordinal: int,
) -> dict[str, str]:
    values: list[str] = []
    seen: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if set(node) >= {
                "coordinate_system",
                "serialized_value",
                "time_base_id",
                "unit",
                "value_type",
            }:
                serialized = node["serialized_value"]
                if (
                    isinstance(serialized, str)
                    and node["value_type"] in {"status", "string"}
                    and serialized not in seen
                ):
                    seen.add(serialized)
                    values.append(serialized)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(case)
    return {
        original: f"value.{chr(96 + case_ordinal)}.{ordinal:04d}"
        for ordinal, original in enumerate(values, start=1)
    }


def rewrite_typed_value(
    value: dict[str, Any],
    id_map: dict[str, str],
    value_map: dict[str, str],
) -> dict[str, Any]:
    rewritten = copy.deepcopy(value)
    time_base_id = rewritten.get("time_base_id")
    if isinstance(time_base_id, str):
        rewritten["time_base_id"] = id_map[time_base_id]
    coordinate_system = rewritten.get("coordinate_system")
    if isinstance(coordinate_system, str):
        rewritten["coordinate_system"] = sanitize_text(coordinate_system)
    unit = rewritten.get("unit")
    if isinstance(unit, str):
        rewritten["unit"] = sanitize_text(unit)
    serialized = rewritten.get("serialized_value")
    if isinstance(serialized, str):
        if serialized in id_map:
            rewritten["serialized_value"] = id_map[serialized]
        elif serialized in value_map:
            rewritten["serialized_value"] = value_map[serialized]
    return rewritten


def rewrite_v01_node(
    node: Any,
    id_map: dict[str, str],
    value_map: dict[str, str],
    parent_key: str | None = None,
) -> Any:
    if fact_has_id_values(node):
        rewritten = copy.deepcopy(node)
        rewritten["provenance_refs"] = []
        rewritten["values"] = [id_map[value] for value in node["values"]]
        return rewritten
    if fact_has_single_id(parent_key, node):
        rewritten = copy.deepcopy(node)
        rewritten["provenance_refs"] = []
        candidate = node["value"]
        rewritten["value"] = id_map[candidate] if isinstance(candidate, str) else None
        return rewritten
    if isinstance(node, dict):
        if set(node) >= {
            "coordinate_system",
            "serialized_value",
            "time_base_id",
            "unit",
            "value_type",
        }:
            return rewrite_typed_value(node, id_map, value_map)
        rewritten: dict[str, Any] = {}
        for key, value in node.items():
            if key == "provenance_refs":
                rewritten[key] = []
            elif key == "audit_identity":
                rewritten[key] = None
            elif key in DIRECT_ID_KEYS and isinstance(value, str):
                rewritten[key] = id_map[value]
            elif key in DIRECT_ID_LIST_KEYS and isinstance(value, list):
                if key == "locator_refs":
                    rewritten[key] = []
                else:
                    rewritten[key] = [id_map[item] for item in value]
            elif key == "source_issues":
                rewritten[key] = []
            else:
                rewritten[key] = rewrite_v01_node(value, id_map, value_map, key)
        return rewritten
    if isinstance(node, list):
        return [
            rewrite_v01_node(value, id_map, value_map, parent_key) for value in node
        ]
    if isinstance(node, str) and parent_key not in STRUCTURAL_STRING_KEYS:
        return sanitize_text(node)
    return node


def make_v01_cases(
    canonical: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    v01_cases: list[dict[str, Any]] = []
    maps: dict[str, dict[str, str]] = {}
    for ordinal, case in enumerate(canonical["cases"], start=1):
        case_id = case["case_scope"]["case_id"]
        id_map = build_opaque_map(case, ordinal)
        value_map = build_opaque_value_map(case, ordinal)
        maps[case_id] = id_map
        rewritten = rewrite_v01_node(case, id_map, value_map)
        rewritten["source_issues"] = []
        v01_cases.append(rewritten)
    return v01_cases, maps


def generic_fact(status: str, value: str | None) -> dict[str, Any]:
    return {"provenance_refs": [], "status": status, "value": value}


def generic_id_fact(status: str = "scope_excluded") -> dict[str, Any]:
    return {"provenance_refs": [], "status": status, "value": None}


def generic_id_list_fact(status: str = "scope_excluded") -> dict[str, Any]:
    return {"provenance_refs": [], "status": status, "values": []}


def v02_endpoint_text(
    original_case: dict[str, Any],
    endpoint: str,
) -> str:
    if endpoint == "start":
        return "观察起点：规则相对时间 0；应用已声明初始字段。"
    stop = original_case["case_scope"]["observation_stop"]
    millisecond_match = re.search(r"(\d+)\s*ms\b", stop, flags=re.IGNORECASE)
    if millisecond_match:
        return (
            f"观察终点：规则相对时间 {millisecond_match.group(1)} 毫秒；"
            "读取已声明终止字段。"
        )
    update_match = re.search(r"更新\s*(\d+)", stop)
    if update_match:
        return (
            f"观察终点：规则相对时间 {update_match.group(1)}；"
            "读取已声明终止字段。"
        )
    return "观察终点：首个声明终止条件满足；读取已声明终止字段。"


def normalize_v02_reference(
    record_id: str,
    ordinal: int,
    kind: str,
    source_status: str = "encoded",
) -> dict[str, Any]:
    if kind == "action":
        description = f"不带结构标注的动作 {ordinal:02d}"
        base_type = "action"
        test_role = "rule_action"
        statement = "该动作标识由规范输入机械保留；中间边界未公开。"
    else:
        description = f"允许效果类型 {ordinal:02d}"
        base_type = "state"
        test_role = "effect"
        statement = "该效果类型被允许出现在终止输出；本轮实际结果值未公开。"
    value = statement if source_status == "encoded" else None
    return {
        "audit_identity": None,
        "base_type": base_type,
        "blind_description": description,
        "record_id": record_id,
        "source_fact": generic_fact(source_status, value),
        "test_role": test_role,
    }


def encoded_value(value: dict[str, Any] | None, channel_label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    rewritten = copy.deepcopy(value)
    rewritten["coordinate_system"] = channel_label
    rewritten["time_base_id"] = None
    unit = rewritten.get("unit")
    if isinstance(unit, str):
        rewritten["unit"] = sanitize_text(unit)
    return rewritten


def v02_value_fact(
    fact: dict[str, Any],
    channel_label: str,
) -> dict[str, Any]:
    return {
        "provenance_refs": [],
        "status": fact["status"],
        "value": encoded_value(fact["value"], channel_label),
    }


def v02_channel(
    channel: dict[str, Any],
    ordinal: int,
) -> dict[str, Any]:
    label = f"输出通道 {ordinal:02d}"
    unit = copy.deepcopy(channel["unit"])
    unit["provenance_refs"] = []
    if isinstance(unit["value"], str):
        unit["value"] = sanitize_text(unit["value"])
    return {
        "channel_id": channel["channel_id"],
        "coordinate_system": generic_fact("encoded", label),
        "equivalence_tolerance": generic_fact("scope_excluded", None),
        "initial_value": v02_value_fact(channel["initial_value"], label),
        "precision": generic_fact("scope_excluded", None),
        "reader_refs": generic_id_list_fact(),
        "semantic_ref": generic_id_fact(),
        "snapshot_boundary": generic_fact("scope_excluded", None),
        "stop_value": v02_value_fact(channel["stop_value"], label),
        "unit": unit,
        "value_type": channel["value_type"],
        "writer_refs": generic_id_list_fact(),
    }


def reference_index(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {reference["record_id"]: reference for reference in case["references"]}


def effect_ids(case: dict[str, Any]) -> list[str]:
    found = {
        reference["record_id"]
        for reference in case["references"]
        if reference["test_role"] == "effect"
    }
    for record in case["operational_records"]:
        if record["record_type"] in {"action_lifecycle", "adjudication_path"}:
            effect = record["effect_ref"]
            if effect["status"] == "encoded" and isinstance(effect["value"], str):
                found.add(effect["value"])
    return sorted(found)


def is_input_semantic(
    channel: dict[str, Any],
    references: dict[str, dict[str, Any]],
) -> bool:
    semantic = channel["semantic_ref"]
    if semantic["status"] != "encoded" or not isinstance(semantic["value"], str):
        return False
    reference = references.get(semantic["value"])
    return reference is not None and reference["test_role"] == "input"


def make_v02_cases(
    original_cases: list[dict[str, Any]],
    v01_cases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for original, v01_case in zip(original_cases, v01_cases, strict=True):
        v01_references = reference_index(v01_case)
        formal_action_id = v01_case["case_scope"]["formal_input_ref"]
        formal_reference = v01_references.get(formal_action_id)
        action_status = (
            formal_reference["source_fact"]["status"]
            if formal_reference is not None
            else "encoded"
        )
        references = [
            normalize_v02_reference(formal_action_id, 1, "action", action_status)
        ]
        for ordinal, effect_id in enumerate(effect_ids(v01_case), start=1):
            source_reference = v01_references.get(effect_id)
            effect_status = (
                source_reference["source_fact"]["status"]
                if source_reference is not None
                else "encoded"
            )
            references.append(
                normalize_v02_reference(effect_id, ordinal, "effect", effect_status)
            )

        output_channels = [
            channel
            for channel in v01_case["state_channels"]
            if not is_input_semantic(channel, v01_references)
        ]
        channels = [
            v02_channel(channel, ordinal)
            for ordinal, channel in enumerate(output_channels, start=1)
        ]
        allowed = [
            kind
            for kind in v01_case["trace_contract"]["allowed_kinds"]
            if kind in {"scope_started", "scope_ended", "state_committed"}
        ]
        if not allowed:
            raise ProjectionError(
                f"{v01_case['case_scope']['case_id']} has no boundary-only trace kind"
            )
        scope = {
            "case_id": v01_case["case_scope"]["case_id"],
            "controlled_variable_id": v01_case["case_scope"]["controlled_variable_id"],
            "formal_input_ref": formal_action_id,
            "observation_start": v02_endpoint_text(original, "start"),
            "observation_stop": v02_endpoint_text(original, "stop"),
            "role_id": v01_case["case_scope"]["role_id"],
            "scope_exclusions": [],
        }
        result.append(
            {
                "case_scope": scope,
                "composition_edges": [],
                "operational_edges": [],
                "operational_records": [],
                "references": references,
                "rules": [],
                "source_issues": [],
                "state_channels": channels,
                "temporal_edges": [],
                "time_bases": [],
                "trace_contract": {
                    "allowed_kinds": allowed,
                    "derivation_algorithm_id": v01_case["trace_contract"][
                        "derivation_algorithm_id"
                    ],
                    "raw_trace_ref": formal_action_id,
                    "stop_condition_refs": v01_case["trace_contract"][
                        "stop_condition_refs"
                    ],
                    "tolerance_rule_refs": [],
                },
            }
        )
    return result


def all_strings(node: Any) -> list[str]:
    values: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            values.append(key)
            values.extend(all_strings(value))
    elif isinstance(node, list):
        for value in node:
            values.extend(all_strings(value))
    elif isinstance(node, str):
        values.append(node)
    return values


def validate_blinding(view: dict[str, Any], forbidden_tokens: list[str]) -> None:
    serialized = canonical_bytes(view).decode("utf-8")
    folded = serialized.casefold()
    leaked = [token for token in forbidden_tokens if token.casefold() in folded]
    if leaked:
        raise ProjectionError(
            "view contains forbidden token(s): " + ", ".join(sorted(leaked))
        )
    if SOURCE_LOCATOR_TOKEN.search(serialized):
        raise ProjectionError("view contains a source-locator-shaped token")
    if ORIGINAL_INTERNAL_ID.search(serialized):
        raise ProjectionError("view contains a canonical internal identifier")
    for case in view["cases"]:
        for reference in case["references"]:
            if reference["audit_identity"] is not None:
                raise ProjectionError("view exposes an audit identity")
        if case["source_issues"]:
            raise ProjectionError("view exposes source issues or locator references")

    def check_provenance(node: Any) -> None:
        if isinstance(node, dict):
            if "provenance_refs" in node and node["provenance_refs"]:
                raise ProjectionError("view exposes source provenance locators")
            for value in node.values():
                check_provenance(value)
        elif isinstance(node, list):
            for value in node:
                check_provenance(value)

    check_provenance(view)


def declared_case_ids(case: dict[str, Any]) -> set[str]:
    declared = {
        case["case_scope"]["controlled_variable_id"],
        case["case_scope"]["formal_input_ref"],
        case["trace_contract"]["derivation_algorithm_id"],
        case["trace_contract"]["raw_trace_ref"],
        *case["trace_contract"]["stop_condition_refs"],
        *case["trace_contract"]["tolerance_rule_refs"],
    }
    declared.update(reference["record_id"] for reference in case["references"])
    declared.update(rule["rule_id"] for rule in case["rules"])
    declared.update(time_base["time_base_id"] for time_base in case["time_bases"])
    declared.update(channel["channel_id"] for channel in case["state_channels"])
    for record in case["operational_records"]:
        declared.add(record["record_id"])
        for milestone in record.get("milestones", []):
            declared.add(milestone["milestone_id"])
        for transition in record.get("transitions", []):
            declared.add(transition["transition_id"])
        for permission in record.get("permission_changes", []):
            declared.add(permission["permission_id"])
        for stage in record.get("stages", []):
            declared.add(stage["stage_id"])
    for family in ("composition_edges", "operational_edges", "temporal_edges"):
        declared.update(edge["edge_id"] for edge in case[family])
    return declared


def referenced_case_ids(node: Any, parent_key: str | None = None) -> set[str]:
    found: set[str] = set()
    if fact_has_id_values(node):
        found.update(node["values"])
    if fact_has_single_id(parent_key, node):
        candidate = node["value"]
        if isinstance(candidate, str):
            found.add(candidate)
    if isinstance(node, dict):
        for key, value in node.items():
            if key in {"provenance_refs", "locator_refs"}:
                continue
            if key in {
                "from_id",
                "from_milestone_id",
                "target_time_base_id",
                "time_base_id",
                "to_id",
                "to_milestone_id",
            } and isinstance(value, str):
                found.add(value)
            elif key in {
                "condition_ids",
                "from_ids",
                "scope_ids",
                "time_base_refs",
                "to_ids",
            } and isinstance(value, list):
                found.update(item for item in value if isinstance(item, str))
            found.update(referenced_case_ids(value, key))
    elif isinstance(node, list):
        for value in node:
            found.update(referenced_case_ids(value, parent_key))
    return found


def validate_closure(view: dict[str, Any]) -> None:
    for case in view["cases"]:
        declared = declared_case_ids(case)
        referenced = referenced_case_ids(case)
        dangling = sorted(referenced - declared)
        if dangling:
            raise ProjectionError(
                f"{case['case_scope']['case_id']} contains dangling identifiers: "
                + ", ".join(dangling)
            )
        internal = collect_case_ids(case)
        nonopaque = sorted(
            value
            for value in internal
            if not value.startswith("o.") and value not in {"CA-R1", "CA-R2", "CA-R3"}
        )
        if nonopaque:
            raise ProjectionError(
                f"{case['case_scope']['case_id']} contains non-opaque identifiers: "
                + ", ".join(nonopaque)
            )


def write_canonical_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def build_view(
    canonical: dict[str, Any],
    canonical_sha256: str,
    spec_sha256: str,
    projection_id: str,
    condition_id: str,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "$schema": SCHEMA_ID,
        "artifact_type": "generated_view",
        "artifact_version": "0.1.0",
        "canonical_encoding_sha256": canonical_sha256,
        "cases": cases,
        "condition_id": condition_id,
        "generated_at": canonical["created_at"],
        "projection_id": projection_id,
        "projection_spec_sha256": spec_sha256,
        "run_id": canonical["run_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--view-v01-output", type=Path, required=True)
    parser.add_argument("--view-v02-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    canonical, canonical_raw = read_canonical_json(args.canonical, "canonical encoding")
    spec, spec_raw = read_canonical_json(args.spec, "projection spec")
    schema = read_schema_json(args.schema)
    if schema.get("$id") != SCHEMA_ID:
        raise ProjectionError("CA-SR artifact schema $id is not the expected identity")
    for label, artifact in (("canonical encoding", canonical), ("projection spec", spec)):
        if artifact.get("$schema") != schema["$id"]:
            raise ProjectionError(f"{label} $schema does not match the schema $id")
    validate_schema(canonical, schema, "canonical encoding")
    validate_schema(spec, schema, "projection spec")

    canonical_sha256 = sha256_bytes(canonical_raw)
    spec_sha256 = sha256_bytes(spec_raw)
    generator_sha256 = sha256_bytes(Path(__file__).resolve().read_bytes())
    v01_projection, v02_projection = validate_projection_spec(
        spec,
        canonical_sha256,
        generator_sha256,
    )
    if canonical["run_id"] != spec["run_id"]:
        raise ProjectionError("canonical run_id does not match projection spec")

    v01_cases, _ = make_v01_cases(canonical)
    v02_cases = make_v02_cases(canonical["cases"], v01_cases)
    v01_view = build_view(
        canonical,
        canonical_sha256,
        spec_sha256,
        v01_projection["projection_id"],
        "condition-v01",
        v01_cases,
    )
    v02_view = build_view(
        canonical,
        canonical_sha256,
        spec_sha256,
        v02_projection["projection_id"],
        "condition-v02",
        v02_cases,
    )
    for label, view in (
        ("condition-v01 view", v01_view),
        ("condition-v02 view", v02_view),
    ):
        validate_schema(view, schema, label)
        validate_blinding(view, spec["forbidden_tokens"])
        validate_closure(view)
        if canonical_bytes(view) != canonical_bytes(json.loads(canonical_bytes(view))):
            raise ProjectionError(f"{label} failed canonical round-trip")

    for path, view, label in (
        (args.view_v01_output, v01_view, "condition-v01 output"),
        (args.view_v02_output, v02_view, "condition-v02 output"),
    ):
        expected = canonical_bytes(view)
        write_canonical_json(path, view)
        if path.read_bytes() != expected:
            raise ProjectionError(f"{label} is not canonical JSON after write")
    print(
        json.dumps(
            {
                "canonical_encoding_sha256": canonical_sha256,
                "generator_sha256": generator_sha256,
                "projection_spec_sha256": spec_sha256,
                "view_v01_output_sha256": sha256_bytes(canonical_bytes(v01_view)),
                "view_v02_output_sha256": sha256_bytes(canonical_bytes(v02_view)),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProjectionError as exc:
        print(f"projection error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
