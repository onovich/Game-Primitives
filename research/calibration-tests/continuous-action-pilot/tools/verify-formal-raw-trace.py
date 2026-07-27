#!/usr/bin/env python3
"""Verify one continuous-001 formal raw trace against its execution permit.

The verify command is deliberately ordered: it verifies the post-prediction
execution permit before opening the trace, selects the permit-bound execution
target, verifies that target's raw-trace schema by path and hash, and only then
parses trace bytes. It never executes a formal input, fixture, comparator, or
test body.

CA-R1 is compact canonical JSON whose frozen serializable fields are declared
in lexicographic order. CA-R2 is a strict 27-record JSONL stream normalized in
memory to the CA-R2 schema object. CA-R3 is two-space canonical JSON produced
from sorted dictionaries. The reported ``formal_trace_sha256`` binds the
original trace file bytes, while ``normalized_trace_sha256`` binds the common
two-space canonical parsed object.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker


sys.dont_write_bytecode = True

RUN_ID = "continuous-001"
BASE = "research/calibration-tests/continuous-action-pilot"
SCHEMA_ROOT = f"{BASE}/schema"
TOOLS_ROOT = f"{BASE}/tools"
PERMIT_VERIFIER_PATH = f"{TOOLS_ROOT}/verify-formal-execution-permit.py"
SCHEMA_PATHS = {
    "CA-R1": f"{SCHEMA_ROOT}/ca-r1-raw-trace-0.1.0.schema.json",
    "CA-R2": f"{SCHEMA_ROOT}/ca-r2-raw-trace-0.1.0.schema.json",
    "CA-R3": f"{SCHEMA_ROOT}/ca-r3-raw-trace-0.1.0.schema.json",
}
SCHEMA_IDS = {
    case_id: ("https://github.com/onovich/Game-Primitives/blob/main/" + relative)
    for case_id, relative in SCHEMA_PATHS.items()
}
CONFIGURATIONS = {
    "CA-R1": ("config.baseline", "config.variant"),
    "CA-R2": ("config.baseline", "config.variant"),
    "CA-R3": (
        "config.baseline",
        "config.variant",
        "config.negative-a",
        "config.negative-b",
    ),
}
NONZERO_SHA256 = "1" * 64
PREDICTION_SHA256 = "2" * 64
FORMAL_INPUT_SHA256 = "3" * 64


class RawTraceError(RuntimeError):
    """A fail-closed formal raw-trace verification error."""


def canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise RawTraceError("trace cannot be represented as canonical JSON") from error
    return (text + "\n").encode("utf-8")


def compact_canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as error:
        raise RawTraceError(
            "trace cannot be represented as compact canonical JSON"
        ) from error
    return (text + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def repo_file(repo_root: Path, relative: str) -> Path:
    path = (repo_root / relative).resolve()
    if not path.is_relative_to(repo_root):
        raise RawTraceError(f"path escapes repository root: {relative}")
    if not path.is_file():
        raise RawTraceError(f"required repository file does not exist: {relative}")
    return path


def reject_constant(value: str) -> None:
    raise RawTraceError(f"non-finite JSON numeric constant is forbidden: {value}")


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RawTraceError(f"duplicate JSON object key is forbidden: {key}")
        value[key] = item
    return value


def strict_json_object(raw: bytes, label: str) -> dict[str, Any]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RawTraceError(f"UTF-8 BOM is forbidden in {label}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RawTraceError(f"{label} is not valid UTF-8") from error
    try:
        value = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except RawTraceError:
        raise
    except json.JSONDecodeError as error:
        raise RawTraceError(f"{label} is not valid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise RawTraceError(f"{label} must contain one JSON object")
    return value


def read_canonical_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = strict_json_object(raw, label)
    if raw != canonical_bytes(value):
        raise RawTraceError(
            f"{label} must be UTF-8 canonical JSON with sorted keys, "
            "two-space indentation, LF endings, and one final newline"
        )
    return value, raw


def schema_error_path(error: Any) -> str:
    path = "$"
    for item in error.absolute_path:
        if isinstance(item, int):
            path += f"[{item}]"
        else:
            path += f".{item}"
    return path


def validate_schema(schema: dict[str, Any], value: dict[str, Any], label: str) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise RawTraceError(f"{label} schema is invalid: {error}") from error
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(value),
        key=lambda item: (
            tuple(str(part) for part in item.absolute_path),
            item.message,
        ),
    )
    if errors:
        first = errors[0]
        raise RawTraceError(
            f"{label} schema validation failed at "
            f"{schema_error_path(first)}: {first.message}"
        )


def verified_schema(
    repo_root: Path,
    execution_target: dict[str, Any],
    case_id: str,
) -> dict[str, Any]:
    reference = execution_target.get("raw_trace_schema")
    if not isinstance(reference, dict):
        raise RawTraceError("execution target lacks raw_trace_schema")
    expected_path = SCHEMA_PATHS[case_id]
    if reference.get("path") != expected_path:
        raise RawTraceError(
            f"execution target selects the wrong raw-trace schema for {case_id}"
        )
    expected_hash = reference.get("sha256")
    if not isinstance(expected_hash, str):
        raise RawTraceError("execution target raw-trace schema lacks SHA-256")
    path = repo_file(repo_root, expected_path)
    raw = path.read_bytes()
    if sha256_bytes(raw) != expected_hash:
        raise RawTraceError("execution target raw-trace schema hash mismatch")
    schema = strict_json_object(raw, f"{case_id} raw-trace schema")
    if schema.get("$id") != SCHEMA_IDS[case_id]:
        raise RawTraceError(f"{case_id} raw-trace schema has the wrong $id")
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise RawTraceError(
            f"{case_id} raw-trace schema is invalid: {error}"
        ) from error
    return schema


def exact_keys(
    value: dict[str, Any],
    expected: set[str],
    label: str,
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise RawTraceError(f"{label} fields differ; missing={missing}, extra={extra}")


def normalize_r2_jsonl(raw: bytes) -> dict[str, Any]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RawTraceError("UTF-8 BOM is forbidden in CA-R2 JSONL")
    if b"\r" in raw:
        raise RawTraceError("CA-R2 JSONL must use LF line endings")
    if not raw.endswith(b"\n"):
        raise RawTraceError("CA-R2 JSONL must end with exactly one LF")

    parts = raw.split(b"\n")
    if parts[-1] != b"":
        raise RawTraceError("CA-R2 JSONL has an invalid final record boundary")
    records_raw = parts[:-1]
    if len(records_raw) != 27:
        raise RawTraceError(
            "CA-R2 JSONL must contain exactly 27 records (1 header, 25 steps, 1 stop)"
        )
    if any(not line for line in records_raw):
        raise RawTraceError("CA-R2 JSONL forbids empty lines")

    records: list[dict[str, Any]] = []
    for index, line in enumerate(records_raw):
        if line != line.strip():
            raise RawTraceError(f"CA-R2 JSONL record {index} has outer whitespace")
        records.append(strict_json_object(line, f"CA-R2 JSONL record {index}"))

    record_types = [record.get("record_type") for record in records]
    allowed = {"run_header", "step", "stop"}
    unknown = [value for value in record_types if value not in allowed]
    if unknown:
        raise RawTraceError(f"CA-R2 JSONL has unknown record_type: {unknown[0]}")
    if (
        record_types[0] != "run_header"
        or record_types[1:26] != ["step"] * 25
        or record_types[26] != "stop"
    ):
        raise RawTraceError("CA-R2 JSONL order must be header, steps 0..24, then stop")

    header = records[0]
    exact_keys(
        header,
        {
            "record_type",
            "run_id",
            "case_id",
            "configuration_id",
            "source_commit",
            "input_sha256",
            "execution_permit_sha256",
            "prediction_set_digest",
            "platform_scope",
            "step_count",
            "step_ms",
        },
        "CA-R2 run_header",
    )
    steps = records[1:26]
    stop = records[26]
    normalized = {
        "artifact_type": "ca_r2_raw_trace",
        "artifact_version": "0.1.0",
        "case_id": header["case_id"],
        "configuration_id": header["configuration_id"],
        "execution_permit_sha256": header["execution_permit_sha256"],
        "formal_input_sha256": header["input_sha256"],
        "platform_scope": header["platform_scope"],
        "prediction_set_digest": header["prediction_set_digest"],
        "run_id": header["run_id"],
        "source_commit": header["source_commit"],
        "step_count": header["step_count"],
        "step_ms": header["step_ms"],
        "steps": steps,
        "stop": stop,
    }
    return normalized


def verify_r2_semantics(value: dict[str, Any]) -> None:
    steps = value["steps"]
    first_raw = steps[0]["raw_cmd"]
    preserved = (
        "serverTime",
        "angles",
        "buttons",
        "weapon",
        "upmove",
    )
    for index, step in enumerate(steps):
        if step["step_index"] != index:
            raise RawTraceError(f"CA-R2 step_index is not ordered at {index}")
        expected_time = (index + 1) * 8
        raw_command = step["raw_cmd"]
        used_command = step["used_cmd"]
        if (
            raw_command["serverTime"] != expected_time
            or used_command["serverTime"] != expected_time
            or step["commandTime"] != expected_time
        ):
            raise RawTraceError(f"CA-R2 command time differs at step {index}")
        for field in preserved:
            if raw_command[field] != used_command[field]:
                raise RawTraceError(
                    f"CA-R2 preserved command field {field} differs at step {index}"
                )
        if value["configuration_id"] == "config.baseline":
            expected_direction = (
                raw_command["forwardmove"],
                raw_command["rightmove"],
            )
        else:
            expected_direction = (
                first_raw["forwardmove"],
                first_raw["rightmove"],
            )
        actual_direction = (
            used_command["forwardmove"],
            used_command["rightmove"],
        )
        if actual_direction != expected_direction:
            raise RawTraceError(f"CA-R2 direction policy differs at step {index}")


def parse_trace(
    trace_path: Path,
    case_id: str,
) -> tuple[dict[str, Any], bytes]:
    raw = trace_path.read_bytes()
    if case_id == "CA-R2":
        return normalize_r2_jsonl(raw), raw
    value = strict_json_object(raw, f"{case_id} raw trace")
    if case_id == "CA-R1" and raw != compact_canonical_bytes(value):
        raise RawTraceError("CA-R1 raw trace must be compact canonical JSON bytes")
    if case_id == "CA-R3" and raw != canonical_bytes(value):
        raise RawTraceError("CA-R3 raw trace must be two-space canonical JSON bytes")
    return value, raw


def assert_bindings(
    value: dict[str, Any],
    case_id: str,
    configuration_id: str,
    execution_permit_sha256: str,
    prediction_set_digest: str,
    formal_input_sha256: str,
) -> None:
    expected = {
        "case_id": case_id,
        "configuration_id": configuration_id,
        "execution_permit_sha256": execution_permit_sha256,
        "formal_input_sha256": formal_input_sha256,
        "prediction_set_digest": prediction_set_digest,
        "run_id": RUN_ID,
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            raise RawTraceError(
                f"formal raw trace {field} does not match the verified "
                "execution permit target"
            )


def trace_summary(value: dict[str, Any], case_id: str) -> dict[str, Any]:
    if case_id == "CA-R1":
        return {
            "record_kind": "compact_canonical_json",
            "trace_entry_count": len(value["trace_entries"]),
        }
    if case_id == "CA-R2":
        return {
            "normalized_record_kind": "strict_jsonl",
            "source_record_count": 27,
            "step_count": len(value["steps"]),
        }
    return {
        "event_count": len(value["observation"]["event_trace"]),
        "record_kind": "canonical_json",
    }


def verify_trace_content(
    repo_root: Path,
    execution_target: dict[str, Any],
    case_id: str,
    configuration_id: str,
    trace_path: Path,
    execution_permit_sha256: str,
    prediction_set_digest: str,
) -> dict[str, Any]:
    if configuration_id not in CONFIGURATIONS[case_id]:
        raise RawTraceError(
            f"configuration-id is not allowed for {case_id}: {configuration_id}"
        )
    if execution_target.get("case_id") != case_id:
        raise RawTraceError("execution target case_id mismatch")
    formal_input = execution_target.get("formal_input")
    if not isinstance(formal_input, dict):
        raise RawTraceError("execution target lacks formal_input")
    formal_input_sha256 = formal_input.get("sha256")
    if not isinstance(formal_input_sha256, str):
        raise RawTraceError("execution target formal_input lacks SHA-256")

    schema = verified_schema(repo_root, execution_target, case_id)
    value, raw = parse_trace(trace_path, case_id)
    validate_schema(schema, value, f"{case_id} raw trace")
    if case_id == "CA-R2":
        verify_r2_semantics(value)
    assert_bindings(
        value,
        case_id,
        configuration_id,
        execution_permit_sha256,
        prediction_set_digest,
        formal_input_sha256,
    )
    normalized = canonical_bytes(value)
    return {
        "formal_trace_sha256": sha256_bytes(raw),
        "normalized_trace_summary": trace_summary(value, case_id),
        "normalized_trace_sha256": sha256_bytes(normalized),
    }


def load_permit_materializer(repo_root: Path) -> Any:
    verifier_path = repo_file(repo_root, PERMIT_VERIFIER_PATH)
    spec = importlib.util.spec_from_file_location(
        "continuous_action_formal_execution_permit_verifier",
        verifier_path,
    )
    if spec is None or spec.loader is None:
        raise RawTraceError("cannot load formal execution-permit verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        return module.load_materializer()
    except Exception as error:
        raise RawTraceError(
            "cannot load formal execution-permit materializer"
        ) from error


def verify_execution_permit(
    repo_root: Path,
    permit_path: Path,
    case_id: str,
) -> dict[str, Any]:
    materializer = load_permit_materializer(repo_root)
    try:
        result = materializer.verify_permit(repo_root, permit_path, case_id)
    except Exception as error:
        raise RawTraceError(
            f"formal execution-permit verification failed: {error}"
        ) from error
    if (
        not isinstance(result, dict)
        or result.get("status") != "formal_execution_permit_verified"
        or result.get("case_id") != case_id
        or result.get("run_id") != RUN_ID
        or not isinstance(result.get("execution_target"), dict)
    ):
        raise RawTraceError(
            "formal execution-permit verifier returned an invalid target"
        )
    return result


def command_verify(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    permit = verify_execution_permit(
        repo_root,
        args.permit_path,
        args.case_id,
    )
    trace_path = (
        args.trace_path
        if args.trace_path.is_absolute()
        else repo_root / args.trace_path
    ).resolve()
    if not trace_path.is_file():
        raise RawTraceError(f"trace path is not an existing file: {trace_path}")
    result = verify_trace_content(
        repo_root,
        permit["execution_target"],
        args.case_id,
        args.configuration_id,
        trace_path,
        permit["execution_permit_sha256"],
        permit["prediction_set_digest"],
    )
    return {
        "case_id": args.case_id,
        "configuration_id": args.configuration_id,
        "execution_target": permit["execution_target"],
        "formal_input": permit["execution_target"]["formal_input"],
        "formal_trace_sha256": result["formal_trace_sha256"],
        "normalized_trace_summary": result["normalized_trace_summary"],
        "normalized_trace_sha256": result["normalized_trace_sha256"],
        "run_id": RUN_ID,
        "status": "formal_raw_trace_verified",
    }


def synthetic_target(repo_root: Path, case_id: str) -> dict[str, Any]:
    schema_path = repo_file(repo_root, SCHEMA_PATHS[case_id])
    return {
        "case_id": case_id,
        "formal_input": {
            "path": f"synthetic/{case_id.lower()}-formal-input.json",
            "sha256": FORMAL_INPUT_SHA256,
        },
        "raw_trace_schema": {
            "path": SCHEMA_PATHS[case_id],
            "sha256": sha256_bytes(schema_path.read_bytes()),
        },
    }


def synthetic_r1(configuration_id: str) -> dict[str, Any]:
    entries = []
    for index in range(7):
        entries.append(
            {
                "after_action_frame": index + 1,
                "after_action_id": 10 + index,
                "after_buffer_action_id": 20 + index,
                "attack_held": 1 if index in (0, 2) else 0,
                "before_action_frame": index,
                "before_action_id": 9 + index,
                "before_buffer_action_id": 19 + index,
                "cancel_eligible_before": 1 if index >= 2 else 0,
                "contact_count": 0,
                "event_id": f"event.ca-r1.update-{index}",
                "hit_count": 0,
                "input_down": 1 if index in (0, 2) else 0,
                "input_value": 8 if index in (0, 2) else 0,
                "sequence_index": index,
            }
        )
    return {
        "artifact_type": "ca_r1_raw_trace",
        "case_id": "CA-R1",
        "configuration_id": configuration_id,
        "controlled_value": 0 if configuration_id == "config.baseline" else 1,
        "execution_permit_sha256": NONZERO_SHA256,
        "formal_input_id": "o.a.0002",
        "formal_input_sha256": FORMAL_INPUT_SHA256,
        "invariant_first_request_recognized": 1,
        "invariant_second_request_buffered": 1,
        "invariant_zero_contacts": 1,
        "invariant_zero_hits": 1,
        "prediction_set_digest": PREDICTION_SHA256,
        "run_id": RUN_ID,
        "stop_boundary_id": "o.a.0042",
        "trace_entries": entries,
    }


def synthetic_command(time_ms: int, forward: int, right: int) -> dict[str, Any]:
    return {
        "serverTime": time_ms,
        "angles": [0, 0, 0],
        "buttons": 0,
        "weapon": 0,
        "forwardmove": forward,
        "rightmove": right,
        "upmove": 0,
    }


def synthetic_r2_records(configuration_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = [
        {
            "record_type": "run_header",
            "run_id": RUN_ID,
            "case_id": "CA-R2",
            "configuration_id": configuration_id,
            "source_commit": "dbe4ddb10315479fc00086f08e25d968b4b43c49",
            "input_sha256": FORMAL_INPUT_SHA256,
            "execution_permit_sha256": NONZERO_SHA256,
            "prediction_set_digest": PREDICTION_SHA256,
            "platform_scope": "MSVC-x64",
            "step_count": 25,
            "step_ms": 8,
        }
    ]
    first_forward = 0
    first_right = 127
    for index in range(25):
        time_ms = (index + 1) * 8
        raw_forward = 0 if index % 2 == 0 else 127
        raw_right = 127 if index % 2 == 0 else 0
        if configuration_id == "config.baseline":
            used_forward = raw_forward
            used_right = raw_right
        else:
            used_forward = first_forward
            used_right = first_right
        records.append(
            {
                "record_type": "step",
                "step_index": index,
                "raw_cmd": synthetic_command(
                    time_ms,
                    raw_forward,
                    raw_right,
                ),
                "used_cmd": synthetic_command(
                    time_ms,
                    used_forward,
                    used_right,
                ),
                "branch_id": 6,
                "branch_calls": 1,
                "air_move_calls": 1,
                "air_fmove": float(used_forward),
                "air_smove": float(used_right),
                "wishdir": [0.0, 1.0, 0.0],
                "wishspeed": 127.0,
                "trace_calls": 1,
                "pointcontents_calls": 1,
                "event_calls": 0,
                "printf_calls": 0,
                "snap_calls": 1,
                "trace_violation": 0,
                "numtouch": 0,
                "watertype": 0,
                "waterlevel": 0,
                "groundEntityNum": 1023,
                "commandTime": time_ms,
                "origin": [0.0, float(index), 0.0],
                "velocity": [0.0, 1.0, 0.0],
            }
        )
    records.append(
        {
            "record_type": "stop",
            "rule_time_ms": 200,
            "steps_completed": 25,
            "invariants_passed": True,
        }
    )
    return records


def jsonl_bytes(records: list[dict[str, Any]]) -> bytes:
    return (
        "\n".join(
            json.dumps(
                record,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            for record in records
        )
        + "\n"
    ).encode("utf-8")


def synthetic_r3(configuration_id: str) -> dict[str, Any]:
    if configuration_id == "config.variant":
        delay = 75
        hit_animations = True
    elif configuration_id == "config.negative-b":
        delay = 0
        hit_animations = False
    else:
        delay = 0
        hit_animations = True
    event_time = 1000 + delay
    event_names = (
        "candidate",
        "adjudication",
        "result_notification",
        "scoring_notification",
        "reentry_closed",
    )
    event_trace = [
        {
            "event": event,
            "ordinal": index,
            "time_ms": 1000 if index == 0 else event_time,
        }
        for index, event in enumerate(event_names)
    ]
    return {
        "artifact_type": "continuous_action_r3_trace",
        "artifact_version": "0.1.0",
        "case_id": "CA-R3",
        "configuration_id": configuration_id,
        "execution_permit_sha256": NONZERO_SHA256,
        "formal_input_sha256": FORMAL_INPUT_SHA256,
        "input": {
            "adjudication_delay_ms": delay,
            "candidate_count": 1,
            "candidate_time_ms": 1000,
            "hit_animations": hit_animations,
            "object_start_time_ms": 1000,
            "overall_difficulty": 5,
        },
        "observation": {
            "adjudication_time_ms": event_time,
            "candidate_accepted": True,
            "candidate_time_ms": 1000,
            "event_trace": event_trace,
            "hit_action": "LeftButton",
            "judged": True,
            "notification_count": 1,
            "notification_time_ms": event_time,
            "production_can_be_hit_after_result": False,
            "production_delegate_method": "DrawableHitCircle.Hit",
            "production_delegate_target_type": "DrawableHitCircle+HitReceptor",
            "raw_time_ms": event_time,
            "reentry_allowed_after_candidate": delay > 0,
            "reentry_allowed_at_notification": False,
            "reentry_closed_time_ms": event_time,
            "result": "Great",
            "score_combo": 1,
            "score_judged_hits": 1,
            "score_notification_count": 1,
            "score_notification_time_ms": event_time,
            "score_total": 1000000,
            "time_offset_ms": delay,
        },
        "prediction_set_digest": PREDICTION_SHA256,
        "run_id": RUN_ID,
        "window_snapshot_ms": {
            "great": 50,
            "meh": 100,
            "ok": 75,
        },
    }


def expect_rejected(operation: Callable[[], Any], label: str) -> None:
    try:
        operation()
    except RawTraceError:
        return
    raise RawTraceError(f"negative control was accepted: {label}")


def self_test_one(
    repo_root: Path,
    target: dict[str, Any],
    case_id: str,
    configuration_id: str,
    path: Path,
    raw: bytes,
) -> dict[str, Any]:
    path.write_bytes(raw)
    return verify_trace_content(
        repo_root,
        target,
        case_id,
        configuration_id,
        path,
        NONZERO_SHA256,
        PREDICTION_SHA256,
    )


def run_self_test(repo_root: Path) -> dict[str, Any]:
    positives = 0
    negatives = 0
    with tempfile.TemporaryDirectory(
        prefix="game-primitives-raw-trace-self-test-"
    ) as temporary:
        root = Path(temporary)
        targets = {
            case_id: synthetic_target(repo_root, case_id) for case_id in CONFIGURATIONS
        }

        for configuration_id in CONFIGURATIONS["CA-R1"]:
            value = synthetic_r1(configuration_id)
            self_test_one(
                repo_root,
                targets["CA-R1"],
                "CA-R1",
                configuration_id,
                root / f"r1-{configuration_id}.json",
                compact_canonical_bytes(value),
            )
            positives += 1

        for configuration_id in CONFIGURATIONS["CA-R2"]:
            records = synthetic_r2_records(configuration_id)
            self_test_one(
                repo_root,
                targets["CA-R2"],
                "CA-R2",
                configuration_id,
                root / f"r2-{configuration_id}.jsonl",
                jsonl_bytes(records),
            )
            positives += 1

        for configuration_id in CONFIGURATIONS["CA-R3"]:
            value = synthetic_r3(configuration_id)
            self_test_one(
                repo_root,
                targets["CA-R3"],
                "CA-R3",
                configuration_id,
                root / f"r3-{configuration_id}.json",
                canonical_bytes(value),
            )
            positives += 1

        noncompact = root / "r1-noncompact.json"
        noncompact.write_bytes(canonical_bytes(synthetic_r1("config.baseline")))
        expect_rejected(
            lambda: verify_trace_content(
                repo_root,
                targets["CA-R1"],
                "CA-R1",
                "config.baseline",
                noncompact,
                NONZERO_SHA256,
                PREDICTION_SHA256,
            ),
            "CA-R1 noncompact bytes",
        )
        negatives += 1

        extra_r1 = synthetic_r1("config.baseline")
        extra_r1["unexpected"] = True
        expect_rejected(
            lambda: self_test_one(
                repo_root,
                targets["CA-R1"],
                "CA-R1",
                "config.baseline",
                root / "r1-extra.json",
                canonical_bytes(extra_r1),
            ),
            "CA-R1 extra field",
        )
        negatives += 1

        blank_r2 = jsonl_bytes(synthetic_r2_records("config.baseline")).replace(
            b"\n",
            b"\n\n",
            1,
        )
        expect_rejected(
            lambda: self_test_one(
                repo_root,
                targets["CA-R2"],
                "CA-R2",
                "config.baseline",
                root / "r2-blank.jsonl",
                blank_r2,
            ),
            "CA-R2 blank line",
        )
        negatives += 1

        unknown_r2 = synthetic_r2_records("config.baseline")
        unknown_r2[7]["record_type"] = "unknown"
        expect_rejected(
            lambda: self_test_one(
                repo_root,
                targets["CA-R2"],
                "CA-R2",
                "config.baseline",
                root / "r2-unknown.jsonl",
                jsonl_bytes(unknown_r2),
            ),
            "CA-R2 unknown record_type",
        )
        negatives += 1

        extra_r2 = synthetic_r2_records("config.baseline")
        extra_r2.append(copy.deepcopy(extra_r2[-1]))
        expect_rejected(
            lambda: self_test_one(
                repo_root,
                targets["CA-R2"],
                "CA-R2",
                "config.baseline",
                root / "r2-extra.jsonl",
                jsonl_bytes(extra_r2),
            ),
            "CA-R2 extra record",
        )
        negatives += 1

        wrong_policy = synthetic_r2_records("config.variant")
        wrong_policy[9]["used_cmd"]["rightmove"] = 0
        expect_rejected(
            lambda: self_test_one(
                repo_root,
                targets["CA-R2"],
                "CA-R2",
                "config.variant",
                root / "r2-policy.jsonl",
                jsonl_bytes(wrong_policy),
            ),
            "CA-R2 wrong direction policy",
        )
        negatives += 1

        extra_r3 = synthetic_r3("config.baseline")
        extra_r3["unexpected"] = True
        expect_rejected(
            lambda: self_test_one(
                repo_root,
                targets["CA-R3"],
                "CA-R3",
                "config.baseline",
                root / "r3-extra.json",
                canonical_bytes(extra_r3),
            ),
            "CA-R3 extra field",
        )
        negatives += 1

        wrong_digest = synthetic_r3("config.baseline")
        wrong_digest["formal_input_sha256"] = "4" * 64
        expect_rejected(
            lambda: self_test_one(
                repo_root,
                targets["CA-R3"],
                "CA-R3",
                "config.baseline",
                root / "r3-digest.json",
                canonical_bytes(wrong_digest),
            ),
            "CA-R3 wrong formal-input digest",
        )
        negatives += 1

    return {
        "formal_comparator_executed": False,
        "formal_input_executed": False,
        "formal_test_body_executed": False,
        "negative_controls_checked": negatives,
        "positive_traces_checked": positives,
        "run_id": RUN_ID,
        "status": "synthetic_formal_raw_trace_self_test_passed",
        "temporary_artifacts_removed": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, required=True)
    verify.add_argument("--permit-path", type=Path, required=True)
    verify.add_argument("--case-id", choices=tuple(CONFIGURATIONS), required=True)
    verify.add_argument("--trace-path", type=Path, required=True)
    verify.add_argument("--configuration-id", required=True)

    self_test = subparsers.add_parser("self-test")
    self_test.add_argument("--repo-root", type=Path, required=True)
    return parser


def run_cli(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "verify":
            result = command_verify(args)
        else:
            result = run_self_test(args.repo_root.resolve())
    except (RawTraceError, OSError, ValueError, KeyError) as error:
        print(f"formal raw trace error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
