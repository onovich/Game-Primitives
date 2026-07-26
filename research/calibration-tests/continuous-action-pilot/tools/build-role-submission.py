#!/usr/bin/env python3
"""Render blind-response forms and package raw payloads without semantic repair."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROLE_011_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "role-submission-0.1.1.schema.json"
)
ROLE_012_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "role-submission-0.1.2.schema.json"
)
INTERFACE_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "blind-response-interface-0.1.0.schema.json"
)
TASK_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "task-packet-0.1.1.schema.json"
)
TASK_010_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "task-packet-0.1.0.schema.json"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value, data


def json_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def repo_path(repo_root: Path, value: str | Path) -> Path:
    candidate = (repo_root / value).resolve()
    if not candidate.is_relative_to(repo_root):
        raise ValueError(f"path escapes repository root: {value}")
    return candidate


def relative_path(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root).as_posix()


def ensure_new_output(repo_root: Path, value: str | Path) -> Path:
    output = repo_path(repo_root, value)
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {output.parent}")
    return output


def schema_registry(schemas: dict[str, Any]) -> Registry:
    registry = Registry()
    for name in ("role_011", "task_010"):
        schema = schemas[name]
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )
    return registry


def validate(
    instance: dict[str, Any],
    schema: dict[str, Any],
    registry: Registry | None = None,
) -> None:
    validator = Draft202012Validator(
        schema,
        registry=registry if registry is not None else Registry(),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(instance), key=lambda error: list(error.path))
    if errors:
        lines = []
        for error in errors[:12]:
            location = "/".join(str(part) for part in error.absolute_path) or "<root>"
            lines.append(f"{location}: {error.message}")
        raise ValueError("schema validation failed:\n" + "\n".join(lines))


def load_schemas(repo_root: Path) -> dict[str, Any]:
    role_011, _ = load_json(repo_path(repo_root, ROLE_011_PATH))
    role_012, _ = load_json(repo_path(repo_root, ROLE_012_PATH))
    interface, _ = load_json(repo_path(repo_root, INTERFACE_PATH))
    task_schema, _ = load_json(repo_path(repo_root, TASK_SCHEMA_PATH))
    task_010, _ = load_json(repo_path(repo_root, TASK_010_SCHEMA_PATH))
    Draft202012Validator.check_schema(role_011)
    Draft202012Validator.check_schema(role_012)
    Draft202012Validator.check_schema(interface)
    Draft202012Validator.check_schema(task_schema)
    Draft202012Validator.check_schema(task_010)
    return {
        "role_011": role_011,
        "role_012": role_012,
        "interface": interface,
        "task": task_schema,
        "task_010": task_010,
    }


def verify_task_contract(
    repo_root: Path,
    task_path: Path,
    task: dict[str, Any],
    schemas: dict[str, Any],
) -> None:
    validate(task, schemas["task"], schema_registry(schemas))
    expected_schema_path = relative_path(repo_root, repo_path(repo_root, INTERFACE_PATH))
    output_schema = task["output_schema"]
    if output_schema["path"].replace("\\", "/") != expected_schema_path:
        raise ValueError(
            "task output_schema must point to blind-response-interface-0.1.0"
        )
    interface_bytes = repo_path(repo_root, INTERFACE_PATH).read_bytes()
    if output_schema["sha256"] != sha256(interface_bytes):
        raise ValueError("task output_schema hash does not match exact schema bytes")

    expected_assembled_path = relative_path(
        repo_root, repo_path(repo_root, ROLE_012_PATH)
    )
    assembled_schema = task["assembled_output_schema"]
    if assembled_schema["path"].replace("\\", "/") != expected_assembled_path:
        raise ValueError(
            "task assembled_output_schema must point to role-submission-0.1.2"
        )
    role_012_bytes = repo_path(repo_root, ROLE_012_PATH).read_bytes()
    if assembled_schema["sha256"] != sha256(role_012_bytes):
        raise ValueError(
            "task assembled_output_schema hash does not match exact schema bytes"
        )

    for artifact in task["input_artifacts"]:
        path = repo_path(repo_root, artifact["path"])
        actual = sha256(path.read_bytes())
        if actual != artifact["sha256"]:
            raise ValueError(
                f"task input hash mismatch for {artifact['artifact_id']}: "
                f"expected {artifact['sha256']}, got {actual}"
            )

def placeholder_pollution() -> dict[str, Any]:
    return {
        "familiarity": {
            "exact_result_knowledge": "<none|suspected|known|unknown>",
            "exact_rule_knowledge": "<none|suspected|known|unknown>",
            "exact_variant_knowledge": "<none|suspected|known|unknown>",
            "project_exposure": "<none|limited|substantial|unknown>",
            "recognized_family": None,
            "recognized_work": None,
            "recognition_status": "<none|suspected|identified>",
            "related_genre_experience": "<none|limited|extensive|unknown>",
        },
        "integrity_exposures": [],
        "stage_update_note": None,
    }


def render_template(task: dict[str, Any], interface_id: str) -> dict[str, Any]:
    if task["artifact_type"] == "reconstruction_task_packet":
        answers = []
        for case_id in task["case_ids"]:
            answers.append(
                {
                    "ambiguities": [],
                    "assumptions": [],
                    "case_id": case_id,
                    "compatible_branches": [],
                    "confidence_percent": -1,
                    "recovered_facts": [],
                    "uniqueness": (
                        "<insufficient_information|multiple_compatible_structures|"
                        "uniquely_recoverable>"
                    ),
                }
            )
        return {
            "$schema": interface_id,
            "artifact_type": "reconstruction_response_payload",
            "artifact_version": "0.1.0",
            "pollution": placeholder_pollution(),
            "reconstruction_answers": answers,
        }

    if task["artifact_type"] != "prediction_task_packet":
        raise ValueError("only reconstruction and prediction tasks are supported")

    answers = []
    for case_id in task["case_ids"]:
        expectations = []
        for observation in task["allowed_observations"]:
            for configuration_id in task["allowed_configurations"]:
                expectations.append(
                    {
                        "configuration_id": configuration_id,
                        "expectation_kind": "<direction|exact|set|status>",
                        "observation_id": observation["observation_id"],
                        "tolerance_rule_id": observation["tolerance_rule_id"],
                        "value": {
                            "serialized_value": "<required-string>",
                            "unit": observation["unit"],
                            "value_type": (
                                "<boolean|decimal|direction|id|id_set|integer|"
                                "rational|status|string>"
                            ),
                        },
                    }
                )
        answers.append(
            {
                "assumptions": [],
                "case_id": case_id,
                "compatible_alternatives": [],
                "confidence_percent": -1,
                "expectations": expectations,
                "prediction_status": "<determinate|indeterminate>",
                "reasoning": "<required-explanation>",
                "supporting_record_ids": [],
            }
        )
    return {
        "$schema": interface_id,
        "artifact_type": "prediction_response_payload",
        "artifact_version": "0.1.0",
        "pollution": placeholder_pollution(),
        "prediction_answers": answers,
    }


def task_stage(task: dict[str, Any]) -> str:
    if task["artifact_type"] == "reconstruction_task_packet":
        return "reconstruction"
    if task["artifact_type"] == "prediction_task_packet":
        return "prediction"
    raise ValueError("only reconstruction and prediction tasks are supported")


def verify_answer_scope(task: dict[str, Any], payload: dict[str, Any]) -> None:
    stage = task_stage(task)
    answer_key = f"{stage}_answers"
    answers = payload[answer_key]
    actual_case_ids = [answer["case_id"] for answer in answers]
    if len(actual_case_ids) != len(set(actual_case_ids)):
        raise ValueError("payload contains duplicate case_id values")
    if set(actual_case_ids) != set(task["case_ids"]):
        raise ValueError(
            f"payload case_ids {actual_case_ids} do not match task {task['case_ids']}"
        )

    if stage != "prediction":
        return

    observations = {
        observation["observation_id"]: observation
        for observation in task["allowed_observations"]
    }
    required_pairs = {
        (configuration_id, observation_id)
        for observation_id in observations
        for configuration_id in task["allowed_configurations"]
    }

    def verify_expectations(
        case_id: str, label: str, expectations: list[dict[str, Any]]
    ) -> None:
        actual_pairs = [
            (item["configuration_id"], item["observation_id"])
            for item in expectations
        ]
        if (
            len(actual_pairs) != len(required_pairs)
            or set(actual_pairs) != required_pairs
        ):
            raise ValueError(
                f"{case_id} {label} must cover each "
                "configuration/observation pair exactly once"
            )
        for item in expectations:
            observation = observations[item["observation_id"]]
            if item["tolerance_rule_id"] != observation["tolerance_rule_id"]:
                raise ValueError(
                    f"{case_id} {label} changes the frozen tolerance rule for "
                    f"{item['observation_id']}"
                )
            allowed_types = set(observation["allowed_value_types"]) | {"status"}
            if item["value"]["value_type"] not in allowed_types:
                raise ValueError(
                    f"{case_id} {label} uses disallowed value_type "
                    f"{item['value']['value_type']} for {item['observation_id']}"
                )

    for answer in answers:
        verify_expectations(
            answer["case_id"], "expectations", answer["expectations"]
        )
        alternative_ids = [
            alternative["alternative_id"]
            for alternative in answer["compatible_alternatives"]
        ]
        if len(alternative_ids) != len(set(alternative_ids)):
            raise ValueError(
                f"{answer['case_id']} contains duplicate alternative_id values"
            )
        if (
            answer["prediction_status"] == "indeterminate"
            and len(alternative_ids) < 2
        ):
            raise ValueError(
                f"{answer['case_id']} indeterminate prediction requires "
                "at least two compatible alternatives"
            )
        for alternative in answer["compatible_alternatives"]:
            verify_expectations(
                answer["case_id"],
                f"alternative {alternative['alternative_id']}",
                alternative["expectations"],
            )


def validate_actor(actor: dict[str, Any], schemas: dict[str, Any]) -> None:
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": schemas["role_011"]["$id"] + "#/$defs/testActor",
    }
    validate(actor, wrapper, schema_registry(schemas))


def dispatch_artifacts(
    repo_root: Path,
    task_path: Path,
    task: dict[str, Any],
    prior_path: Path | None,
) -> tuple[list[dict[str, str]], dict[str, Any] | None, str | None]:
    artifacts = [
        {
            "artifact_id": task["task_id"],
            "sha256": sha256(task_path.read_bytes()),
        }
    ]
    artifacts.extend(
        {
            "artifact_id": item["artifact_id"],
            "sha256": item["sha256"],
        }
        for item in task["input_artifacts"]
    )

    prior = None
    prior_sha = None
    if prior_path is not None:
        prior, prior_bytes = load_json(prior_path)
        prior_sha = sha256(prior_bytes)
        artifacts.append(
            {
                "artifact_id": prior["submission_id"],
                "sha256": prior_sha,
            }
        )

    artifact_ids = [item["artifact_id"] for item in artifacts]
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ValueError("dispatch artifact IDs must be unique")
    return artifacts, prior, prior_sha


def build_envelope(
    repo_root: Path,
    task_path: Path,
    task: dict[str, Any],
    actor: dict[str, Any],
    submission_id: str,
    condition_id: str | None,
    prior_path: Path | None,
    schemas: dict[str, Any],
) -> dict[str, Any]:
    stage = task_stage(task)
    artifacts, prior, prior_sha = dispatch_artifacts(
        repo_root, task_path, task, prior_path
    )

    if stage == "reconstruction":
        if prior_path is not None:
            raise ValueError("reconstruction packaging cannot have a prior submission")
        resolved_condition = task["condition_id"]
        if condition_id is not None and condition_id != resolved_condition:
            raise ValueError("condition_id conflicts with reconstruction task")
    else:
        if prior is None or prior_sha is None:
            raise ValueError("prediction packaging requires prior reconstruction")
        resolved_condition = condition_id
        if resolved_condition is None:
            raise ValueError("prediction packaging requires --condition-id")
        if prior["artifact_type"] != "reconstruction_submission":
            raise ValueError("prior submission is not a reconstruction submission")
        if prior["run_id"] != task["run_id"]:
            raise ValueError("prior submission run_id differs from prediction task")
        if prior["condition_id"] != resolved_condition:
            raise ValueError("prior submission condition_id differs from requested one")
        if prior["actor"] != actor:
            raise ValueError("prediction actor must exactly match reconstruction actor")

    tool_path = Path(__file__).resolve()
    interface_path = repo_path(repo_root, INTERFACE_PATH)
    output_schema_path = repo_path(
        repo_root, task["assembled_output_schema"]["path"]
    )
    envelope = {
        "$schema": schemas["interface"]["$id"],
        "actor": actor,
        "artifact_type": "role_submission_envelope",
        "artifact_version": "0.1.0",
        "condition_id": resolved_condition,
        "dispatch_artifacts": artifacts,
        "first_submission": True,
        "output_schema": {
            "path": relative_path(repo_root, output_schema_path),
            "sha256": sha256(output_schema_path.read_bytes()),
        },
        "packager": {
            "path": relative_path(repo_root, tool_path),
            "sha256": sha256(tool_path.read_bytes()),
        },
        "prior_stage_submission_sha256": prior_sha,
        "received_at": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "response_schema": {
            "path": relative_path(repo_root, interface_path),
            "sha256": sha256(interface_path.read_bytes()),
        },
        "run_id": task["run_id"],
        "stage": stage,
        "submission_id": submission_id,
        "target_artifact_type": f"{stage}_submission",
        "target_artifact_version": "0.1.2",
        "task_id": task["task_id"],
    }
    validate(
        envelope,
        schemas["interface"],
        schema_registry(schemas),
    )
    return envelope


def build_submission(
    repo_root: Path,
    envelope_path: Path,
    envelope: dict[str, Any],
    payload_path: Path,
    payload: dict[str, Any],
    payload_bytes: bytes,
    schemas: dict[str, Any],
) -> dict[str, Any]:
    stage = envelope["stage"]
    expected_payload_type = f"{stage}_response_payload"
    if payload["artifact_type"] != expected_payload_type:
        raise ValueError(
            f"payload type {payload['artifact_type']} does not match stage {stage}"
        )

    response_schema_path = repo_path(
        repo_root, envelope["response_schema"]["path"]
    )
    output_schema_path = repo_path(repo_root, envelope["output_schema"]["path"])
    tool_path = repo_path(repo_root, envelope["packager"]["path"])
    checks = (
        (
            response_schema_path,
            envelope["response_schema"]["sha256"],
            "response schema",
        ),
        (output_schema_path, envelope["output_schema"]["sha256"], "output schema"),
        (tool_path, envelope["packager"]["sha256"], "packager"),
    )
    for path, expected, label in checks:
        actual = sha256(path.read_bytes())
        if actual != expected:
            raise ValueError(f"{label} hash mismatch: expected {expected}, got {actual}")

    answer_key = f"{stage}_answers"
    copied_fields = ["pollution", answer_key]
    submission = {
        "$schema": schemas["role_012"]["$id"],
        "actor": envelope["actor"],
        "artifact_type": envelope["target_artifact_type"],
        "artifact_version": envelope["target_artifact_version"],
        "audit_checks": [],
        "audit_decision": None,
        "condition_id": envelope["condition_id"],
        "findings": [],
        "first_submission": envelope["first_submission"],
        "input_artifacts": envelope["dispatch_artifacts"],
        "packaging": {
            "copied_fields": copied_fields,
            "envelope_path": relative_path(repo_root, envelope_path),
            "envelope_sha256": sha256(envelope_path.read_bytes()),
            "mode": "deterministic_field_copy",
            "semantic_copy_verified": True,
            "tool_path": envelope["packager"]["path"],
            "tool_sha256": envelope["packager"]["sha256"],
        },
        "pollution": payload["pollution"],
        "prediction_answers": (
            payload["prediction_answers"] if stage == "prediction" else []
        ),
        "prior_stage_submission_sha256": envelope[
            "prior_stage_submission_sha256"
        ],
        "raw_payload": {
            "artifact_id": f"payload.{envelope['submission_id']}",
            "path": relative_path(repo_root, payload_path),
            "schema_path": envelope["response_schema"]["path"],
            "schema_sha256": envelope["response_schema"]["sha256"],
            "sha256": sha256(payload_bytes),
        },
        "reconstruction_answers": (
            payload["reconstruction_answers"] if stage == "reconstruction" else []
        ),
        "run_id": envelope["run_id"],
        "stage": stage,
        "submission_id": envelope["submission_id"],
        "submitted_at": envelope["received_at"],
        "task_id": envelope["task_id"],
    }
    validate(
        submission,
        schemas["role_012"],
        schema_registry(schemas),
    )

    if submission["pollution"] != payload["pollution"]:
        raise AssertionError("pollution field was not copied exactly")
    if submission[answer_key] != payload[answer_key]:
        raise AssertionError(f"{answer_key} field was not copied exactly")
    return submission


def command_render(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    schemas = load_schemas(repo_root)
    task_path = repo_path(repo_root, args.task)
    task, _ = load_json(task_path)
    verify_task_contract(repo_root, task_path, task, schemas)
    output_path = ensure_new_output(repo_root, args.output)
    template = render_template(task, schemas["interface"]["$id"])
    output_path.write_bytes(json_bytes(template))
    print(
        json.dumps(
            {
                "artifact": relative_path(repo_root, output_path),
                "sha256": sha256(output_path.read_bytes()),
                "status": "template_rendered",
                "warning": "template intentionally contains invalid placeholders",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def command_capture(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    schemas = load_schemas(repo_root)
    task_path = repo_path(repo_root, args.task)
    actor_path = repo_path(repo_root, args.actor)
    prior_path = (
        repo_path(repo_root, args.prior_stage_submission)
        if args.prior_stage_submission is not None
        else None
    )
    envelope_output = ensure_new_output(repo_root, args.envelope_output)

    task, _ = load_json(task_path)
    actor, _ = load_json(actor_path)
    verify_task_contract(repo_root, task_path, task, schemas)
    validate_actor(actor, schemas)

    envelope = build_envelope(
        repo_root,
        task_path,
        task,
        actor,
        args.submission_id,
        args.condition_id,
        prior_path,
        schemas,
    )
    envelope_bytes = json_bytes(envelope)
    envelope_output.write_bytes(envelope_bytes)

    print(
        json.dumps(
            {
                "envelope_sha256": sha256(envelope_bytes),
                "status": "envelope_captured",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def verify_envelope_task(
    task_path: Path,
    task: dict[str, Any],
    envelope: dict[str, Any],
) -> None:
    expected_task_ref = {
        "artifact_id": task["task_id"],
        "sha256": sha256(task_path.read_bytes()),
    }
    if expected_task_ref not in envelope["dispatch_artifacts"]:
        raise ValueError("envelope does not bind the exact task packet")
    for item in task["input_artifacts"]:
        expected = {
            "artifact_id": item["artifact_id"],
            "sha256": item["sha256"],
        }
        if expected not in envelope["dispatch_artifacts"]:
            raise ValueError(
                f"envelope does not bind task input {item['artifact_id']}"
            )
    if envelope["run_id"] != task["run_id"]:
        raise ValueError("envelope run_id differs from task")
    if envelope["task_id"] != task["task_id"]:
        raise ValueError("envelope task_id differs from task")
    if envelope["stage"] != task_stage(task):
        raise ValueError("envelope stage differs from task type")


def command_assemble(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    schemas = load_schemas(repo_root)
    task_path = repo_path(repo_root, args.task)
    envelope_path = repo_path(repo_root, args.envelope)
    payload_path = repo_path(repo_root, args.payload)
    submission_output = ensure_new_output(repo_root, args.submission_output)

    task, _ = load_json(task_path)
    envelope, _ = load_json(envelope_path)
    payload, payload_bytes = load_json(payload_path)
    registry = schema_registry(schemas)
    verify_task_contract(repo_root, task_path, task, schemas)
    validate(envelope, schemas["interface"], registry)
    validate(payload, schemas["interface"], registry)
    verify_envelope_task(task_path, task, envelope)
    verify_answer_scope(task, payload)

    submission = build_submission(
        repo_root,
        envelope_path,
        envelope,
        payload_path,
        payload,
        payload_bytes,
        schemas,
    )
    submission_bytes = json_bytes(submission)
    submission_output.write_bytes(submission_bytes)
    print(
        json.dumps(
            {
                "payload_sha256": sha256(payload_bytes),
                "status": "assembled",
                "submission_sha256": sha256(submission_bytes),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def command_verify(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    schemas = load_schemas(repo_root)
    envelope_path = repo_path(repo_root, args.envelope)
    payload_path = repo_path(repo_root, args.payload)
    submission_path = repo_path(repo_root, args.submission)
    envelope, _ = load_json(envelope_path)
    payload, payload_bytes = load_json(payload_path)
    submission, submission_bytes = load_json(submission_path)

    registry = schema_registry(schemas)
    validate(envelope, schemas["interface"], registry)
    validate(payload, schemas["interface"], registry)
    expected = build_submission(
        repo_root,
        envelope_path,
        envelope,
        payload_path,
        payload,
        payload_bytes,
        schemas,
    )
    if submission != expected:
        raise ValueError("packaged submission differs from deterministic rebuild")
    if submission_bytes != json_bytes(submission):
        raise ValueError("packaged submission is not in canonical JSON byte form")
    print(
        json.dumps(
            {
                "payload_sha256": sha256(payload_bytes),
                "status": "verified",
                "submission_sha256": sha256(submission_bytes),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    subcommands = root.add_subparsers(dest="command", required=True)

    render = subcommands.add_parser("render-template")
    render.add_argument("--repo-root", required=True, type=Path)
    render.add_argument("--task", required=True, type=Path)
    render.add_argument("--output", required=True, type=Path)
    render.set_defaults(func=command_render)

    capture = subcommands.add_parser("capture-envelope")
    capture.add_argument("--repo-root", required=True, type=Path)
    capture.add_argument("--task", required=True, type=Path)
    capture.add_argument("--actor", required=True, type=Path)
    capture.add_argument("--submission-id", required=True)
    capture.add_argument("--condition-id")
    capture.add_argument("--prior-stage-submission", type=Path)
    capture.add_argument("--envelope-output", required=True, type=Path)
    capture.set_defaults(func=command_capture)

    assemble = subcommands.add_parser("assemble")
    assemble.add_argument("--repo-root", required=True, type=Path)
    assemble.add_argument("--task", required=True, type=Path)
    assemble.add_argument("--envelope", required=True, type=Path)
    assemble.add_argument("--payload", required=True, type=Path)
    assemble.add_argument("--submission-output", required=True, type=Path)
    assemble.set_defaults(func=command_assemble)

    verify = subcommands.add_parser("verify")
    verify.add_argument("--repo-root", required=True, type=Path)
    verify.add_argument("--envelope", required=True, type=Path)
    verify.add_argument("--payload", required=True, type=Path)
    verify.add_argument("--submission", required=True, type=Path)
    verify.set_defaults(func=command_verify)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
