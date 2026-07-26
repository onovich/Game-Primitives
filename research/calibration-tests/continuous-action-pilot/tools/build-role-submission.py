#!/usr/bin/env python3
"""Render blind-response forms and package raw payloads without semantic repair."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
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
    "task-packet-0.1.2.schema.json"
)
TASK_010_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "task-packet-0.1.0.schema.json"
)
VARIANT_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "variant-envelope-0.1.0.schema.json"
)
RESPONSE_TEMPLATE_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "response-template-0.1.0.schema.json"
)
DISPATCH_TOOL_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/tools/"
    "materialize-dispatch.py"
)
LOCAL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


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
    for name in ("role_011", "task_010", "variant"):
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
    variant, _ = load_json(repo_path(repo_root, VARIANT_SCHEMA_PATH))
    response_template, _ = load_json(
        repo_path(repo_root, RESPONSE_TEMPLATE_SCHEMA_PATH)
    )
    Draft202012Validator.check_schema(role_011)
    Draft202012Validator.check_schema(role_012)
    Draft202012Validator.check_schema(interface)
    Draft202012Validator.check_schema(task_schema)
    Draft202012Validator.check_schema(task_010)
    Draft202012Validator.check_schema(variant)
    Draft202012Validator.check_schema(response_template)
    return {
        "role_011": role_011,
        "role_012": role_012,
        "interface": interface,
        "task": task_schema,
        "task_010": task_010,
        "variant": variant,
        "response_template": response_template,
    }


def load_dispatch_tool(repo_root: Path) -> Any:
    path = repo_path(repo_root, DISPATCH_TOOL_PATH)
    spec = importlib.util.spec_from_file_location(
        "continuous_action_dispatch_contract",
        path,
    )
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load dispatch verifier: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

def observations_by_case(task: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    observations = {
        observation["observation_id"]: observation
        for observation in task["allowed_observations"]
    }
    if len(observations) != len(task["allowed_observations"]):
        raise ValueError("task contains duplicate observation_id values")

    intervention_by_case = {
        intervention["case_id"]: intervention
        for intervention in task["variant_interventions"]
    }
    if set(intervention_by_case) != set(task["case_ids"]):
        raise ValueError(
            "prediction task must contain exactly one intervention per case"
        )

    claimed: set[str] = set()
    result: dict[str, list[dict[str, Any]]] = {}
    for case_id in task["case_ids"]:
        requested = intervention_by_case[case_id]["observation_ids"]
        if len(requested) != len(set(requested)):
            raise ValueError(f"{case_id} contains duplicate observation_ids")
        unknown = set(requested) - set(observations)
        if unknown:
            raise ValueError(
                f"{case_id} references unknown observations: {sorted(unknown)}"
            )
        overlap = claimed & set(requested)
        if overlap:
            raise ValueError(
                "observation_ids must belong to exactly one case: "
                f"{sorted(overlap)}"
            )
        claimed.update(requested)
        requested_set = set(requested)
        result[case_id] = [
            observation
            for observation in task["allowed_observations"]
            if observation["observation_id"] in requested_set
        ]

    unclaimed = set(observations) - claimed
    if unclaimed:
        raise ValueError(
            f"task contains observations outside every case: {sorted(unclaimed)}"
        )
    return result


def declared_local_ids(value: Any) -> set[str]:
    result: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if (
                    key.endswith("_id")
                    and isinstance(child, str)
                    and LOCAL_ID_PATTERN.fullmatch(child)
                ):
                    result.add(child)
                elif key.endswith("_ids") and isinstance(child, list):
                    result.update(
                        item
                        for item in child
                        if isinstance(item, str)
                        and LOCAL_ID_PATTERN.fullmatch(item)
                    )
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return result


def load_bound_artifact(
    repo_root: Path,
    task: dict[str, Any],
    artifact_id_prefix: str,
) -> dict[str, Any]:
    matches = [
        artifact
        for artifact in task["input_artifacts"]
        if artifact["artifact_id"].startswith(artifact_id_prefix)
    ]
    if len(matches) != 1:
        raise ValueError(
            f"task must bind exactly one {artifact_id_prefix} artifact"
        )
    artifact = matches[0]
    path = repo_path(repo_root, artifact["path"])
    value, raw = load_json(path)
    if sha256(raw) != artifact["sha256"]:
        raise ValueError(
            f"task-bound artifact hash mismatch: {artifact['artifact_id']}"
        )
    return value


def permitted_support_ids(
    repo_root: Path,
    task: dict[str, Any],
    prior_task_path: Path | None,
    prior_submission: dict[str, Any] | None,
) -> set[str]:
    stage = task_stage(task)
    if stage == "reconstruction":
        view = load_bound_artifact(repo_root, task, "view.")
        return declared_local_ids(view)

    if prior_task_path is None or prior_submission is None:
        raise ValueError(
            "prediction support scope requires the verified prior task/submission"
        )
    prior_task, _ = load_json(prior_task_path)
    view = load_bound_artifact(repo_root, prior_task, "view.")
    view_artifact = next(
        artifact
        for artifact in prior_task["input_artifacts"]
        if artifact["artifact_id"].startswith("view.")
    )
    expected_prior_ref = {
        "artifact_id": view_artifact["artifact_id"],
        "sha256": view_artifact["sha256"],
    }
    if expected_prior_ref not in prior_submission["input_artifacts"]:
        raise ValueError("verified prior does not bind its exact condition view")

    envelope = load_bound_artifact(repo_root, task, "envelope.")
    result = declared_local_ids(view)
    result.update(declared_local_ids(envelope))
    result.update(declared_local_ids(task))
    result.update(declared_local_ids(prior_submission["reconstruction_answers"]))
    return result


def verify_support_scope(
    task: dict[str, Any],
    payload: dict[str, Any],
    allowed_ids: set[str],
) -> None:
    stage = task_stage(task)
    references: list[tuple[str, list[str]]] = []
    if stage == "reconstruction":
        for answer in payload["reconstruction_answers"]:
            for fact in answer["recovered_facts"]:
                references.append(
                    (
                        f"{answer['case_id']} fact {fact['fact_id']}",
                        fact["supporting_record_ids"],
                    )
                )
            for branch in answer["compatible_branches"]:
                references.append(
                    (
                        f"{answer['case_id']} branch {branch['branch_id']}",
                        branch["supporting_record_ids"],
                    )
                )
    else:
        references.extend(
            (
                f"{answer['case_id']} prediction",
                answer["supporting_record_ids"],
            )
            for answer in payload["prediction_answers"]
        )

    for label, record_ids in references:
        forbidden = sorted(set(record_ids) - allowed_ids)
        if forbidden:
            raise ValueError(
                f"{label} cites IDs outside its dispatched materials: {forbidden}"
            )


def render_template(
    repo_root: Path,
    task: dict[str, Any],
    schemas: dict[str, Any],
) -> dict[str, Any]:
    stage = task_stage(task)
    expected_id = f"template.{stage}.continuous-001"
    matches = [
        artifact
        for artifact in task["input_artifacts"]
        if artifact["artifact_id"] == expected_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"task must bind exactly one frozen {stage} response template"
        )

    artifact = matches[0]
    template_path = repo_path(repo_root, artifact["path"])
    template, template_bytes = load_json(template_path)
    if sha256(template_bytes) != artifact["sha256"]:
        raise ValueError("frozen response-template hash does not match task")
    validate(
        template,
        schemas["response_template"],
        schema_registry(schemas),
    )
    if (
        template["run_id"] != task["run_id"]
        or template["stage"] != stage
        or template["artifact_type"] != f"{stage}_response_template"
    ):
        raise ValueError("frozen response template does not match task stage")

    target_schema = template["target_response_schema"]
    interface_bytes = repo_path(repo_root, INTERFACE_PATH).read_bytes()
    if (
        target_schema["path"].replace("\\", "/")
        != INTERFACE_PATH.as_posix()
        or target_schema["sha256"] != sha256(interface_bytes)
    ):
        raise ValueError(
            "frozen response template is not bound to the current raw interface"
        )
    return copy.deepcopy(template["template_payload"])


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

    if stage == "reconstruction":
        for answer in answers:
            fact_ids = [
                fact["fact_id"] for fact in answer["recovered_facts"]
            ]
            if len(fact_ids) != len(set(fact_ids)):
                raise ValueError(
                    f"{answer['case_id']} contains duplicate fact_id values"
                )
            branch_ids = [
                branch["branch_id"]
                for branch in answer["compatible_branches"]
            ]
            if len(branch_ids) != len(set(branch_ids)):
                raise ValueError(
                    f"{answer['case_id']} contains duplicate branch_id values"
                )
        return

    case_observations = observations_by_case(task)

    def verify_expectations(
        case_id: str, label: str, expectations: list[dict[str, Any]]
    ) -> None:
        observations = {
            observation["observation_id"]: observation
            for observation in case_observations[case_id]
        }
        required_pairs = {
            (configuration_id, observation_id)
            for observation_id in observations
            for configuration_id in task["allowed_configurations"]
        }
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
        if answer["prediction_status"] == "indeterminate":
            signatures = []
            for alternative in answer["compatible_alternatives"]:
                ordered = sorted(
                    alternative["expectations"],
                    key=lambda item: (
                        item["configuration_id"],
                        item["observation_id"],
                    ),
                )
                signatures.append(
                    [
                        {
                            "configuration_id": item["configuration_id"],
                            "expectation_kind": item["expectation_kind"],
                            "observation_id": item["observation_id"],
                            "value": item["value"],
                        }
                        for item in ordered
                    ]
                )
            canonical_signatures = {
                json.dumps(signature, ensure_ascii=False, sort_keys=True)
                for signature in signatures
            }
            if len(canonical_signatures) < 2:
                raise ValueError(
                    f"{answer['case_id']} indeterminate alternatives must "
                    "differ on at least one configuration/observation prediction"
                )


def validate_actor(actor: dict[str, Any], schemas: dict[str, Any]) -> None:
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": schemas["role_011"]["$id"] + "#/$defs/testActor",
    }
    validate(actor, wrapper, schema_registry(schemas))


def verify_dispatch_receipt(
    repo_root: Path,
    task_path: Path,
    task: dict[str, Any],
    actor: dict[str, Any],
    condition_id: str,
    receipt_path: Path,
    prior_dispatch_receipt_path: Path | None,
    prior_submission_path: Path | None,
) -> tuple[dict[str, Any], dict[str, str]]:
    dispatch = load_dispatch_tool(repo_root)
    stage = task_stage(task)
    if stage == "reconstruction":
        if (
            prior_dispatch_receipt_path is not None
            or prior_submission_path is not None
        ):
            raise ValueError(
                "reconstruction dispatch cannot bind prior-stage artifacts"
            )
        receipt = dispatch.verify_stage1_receipt(repo_root, receipt_path)
    else:
        if (
            prior_dispatch_receipt_path is None
            or prior_submission_path is None
        ):
            raise ValueError(
                "prediction dispatch requires its prior receipt and submission"
            )
        receipt = dispatch.verify_stage2_receipt(repo_root, receipt_path)

    expected_actor_binding = {
        "actor_identifier": actor["identifier"],
        "actor_object_sha256": dispatch.actor_object_sha256(actor),
        "session_id": actor["session_id"],
    }
    if receipt["actor_binding"] != expected_actor_binding:
        raise ValueError("dispatch receipt actor differs from packaging actor")
    if receipt["run_id"] != task["run_id"]:
        raise ValueError("dispatch receipt run differs from task")
    if receipt["stage"] != stage:
        raise ValueError("dispatch receipt stage differs from task")
    if receipt["condition_binding"]["condition_id"] != condition_id:
        raise ValueError("dispatch receipt condition differs from task chain")
    if (
        receipt["dispatch_status"] != "ready_for_dispatch"
        or receipt["release_authorized"] is not True
    ):
        raise ValueError("dispatch receipt is not release-authorized")

    task_reference = {
        "path": relative_path(repo_root, task_path),
        "sha256": sha256(task_path.read_bytes()),
    }
    if stage == "reconstruction":
        if {
            "path": receipt["condition_binding"]["task_path"],
            "sha256": receipt["condition_binding"]["task_sha256"],
        } != task_reference:
            raise ValueError("stage1 dispatch receipt binds a different task")
    else:
        participant_tasks = [
            {
                "path": item["path"],
                "sha256": item["sha256"],
            }
            for item in receipt["participant_files"]
            if item["path"] == task_reference["path"]
        ]
        if participant_tasks != [task_reference]:
            raise ValueError("stage2 dispatch receipt binds a different task")
        expected_prior_receipt = dispatch.artifact_reference(
            repo_root,
            prior_dispatch_receipt_path,
        )
        expected_prior_submission = dispatch.artifact_reference(
            repo_root,
            prior_submission_path,
        )
        if receipt["stage1_dispatch_receipt"] != expected_prior_receipt:
            raise ValueError("stage2 receipt binds a different prior receipt")
        if receipt["stage1_submission"] != expected_prior_submission:
            raise ValueError("stage2 receipt binds a different prior submission")

    return receipt, {
        "artifact_id": receipt["receipt_id"],
        "sha256": sha256(receipt_path.read_bytes()),
    }


def dispatch_artifacts(
    repo_root: Path,
    task_path: Path,
    task: dict[str, Any],
    dispatch_receipt_reference: dict[str, str],
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
    artifacts.append(dispatch_receipt_reference)

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
    dispatch_receipt_path: Path,
    prior_path: Path | None,
    prior_task_path: Path | None,
    prior_dispatch_receipt_path: Path | None,
    schemas: dict[str, Any],
) -> dict[str, Any]:
    stage = task_stage(task)
    if stage == "reconstruction":
        if (
            prior_path is not None
            or prior_task_path is not None
            or prior_dispatch_receipt_path is not None
        ):
            raise ValueError("reconstruction packaging cannot have a prior submission")
        resolved_condition = task["condition_id"]
        if condition_id is not None and condition_id != resolved_condition:
            raise ValueError("condition_id conflicts with reconstruction task")
    else:
        if (
            prior_path is None
            or prior_task_path is None
            or prior_dispatch_receipt_path is None
        ):
            raise ValueError(
                "prediction packaging requires the prior task, receipt, and "
                "reconstruction submission"
            )
        resolved_condition = condition_id
        if resolved_condition is None:
            raise ValueError("prediction packaging requires --condition-id")

    verified_prior = None
    if prior_path is not None and prior_task_path is not None:
        verified_prior = verify_submission_chain(
            repo_root,
            prior_task_path,
            prior_path,
            prior_dispatch_receipt_path,
            schemas,
        )

    _, dispatch_receipt_reference = verify_dispatch_receipt(
        repo_root,
        task_path,
        task,
        actor,
        resolved_condition,
        dispatch_receipt_path,
        prior_dispatch_receipt_path,
        prior_path,
    )
    artifacts, prior, prior_sha = dispatch_artifacts(
        repo_root,
        task_path,
        task,
        dispatch_receipt_reference,
        prior_path,
    )
    if prior != verified_prior:
        raise AssertionError("verified prior changed during envelope capture")

    if stage == "prediction":
        if prior is None or prior_sha is None:
            raise AssertionError("verified prediction prior disappeared")
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
    prior_reference = (
        {
            "artifact_id": prior["submission_id"],
            "sha256": prior_sha,
        }
        if prior is not None and prior_sha is not None
        else None
    )
    verify_envelope_task(
        task_path,
        task,
        envelope,
        dispatch_receipt_reference,
        prior_reference,
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


def verify_submission_chain(
    repo_root: Path,
    task_path: Path,
    submission_path: Path,
    dispatch_receipt_path: Path | None,
    schemas: dict[str, Any],
) -> dict[str, Any]:
    if dispatch_receipt_path is None:
        raise ValueError("submission-chain verification requires its dispatch receipt")
    task, _ = load_json(task_path)
    submission, submission_bytes = load_json(submission_path)
    verify_task_contract(repo_root, task_path, task, schemas)
    validate(
        submission,
        schemas["role_012"],
        schema_registry(schemas),
    )
    if submission_bytes != json_bytes(submission):
        raise ValueError("prior submission is not in canonical JSON byte form")
    if submission["task_id"] != task["task_id"]:
        raise ValueError("prior submission task_id differs from prior task")
    if submission["stage"] != task_stage(task):
        raise ValueError("prior submission stage differs from prior task")
    if task_stage(task) != "reconstruction":
        raise ValueError("only a reconstruction submission can be a prior stage")

    envelope_path = repo_path(
        repo_root,
        submission["packaging"]["envelope_path"],
    )
    payload_path = repo_path(repo_root, submission["raw_payload"]["path"])
    envelope, envelope_bytes = load_json(envelope_path)
    payload, payload_bytes = load_json(payload_path)
    if sha256(envelope_bytes) != submission["packaging"]["envelope_sha256"]:
        raise ValueError("prior machine-envelope hash mismatch")
    if sha256(payload_bytes) != submission["raw_payload"]["sha256"]:
        raise ValueError("prior raw-payload hash mismatch")

    registry = schema_registry(schemas)
    validate(envelope, schemas["interface"], registry)
    validate(payload, schemas["interface"], registry)
    _, dispatch_reference = verify_dispatch_receipt(
        repo_root,
        task_path,
        task,
        submission["actor"],
        submission["condition_id"],
        dispatch_receipt_path,
        None,
        None,
    )
    verify_envelope_task(
        task_path,
        task,
        envelope,
        dispatch_reference,
    )
    verify_answer_scope(task, payload)
    verify_support_scope(
        task,
        payload,
        permitted_support_ids(repo_root, task, None, None),
    )
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
        raise ValueError(
            "prior submission differs from deterministic raw-payload reassembly"
        )
    return submission


def verify_current_prior(
    repo_root: Path,
    task: dict[str, Any],
    envelope: dict[str, Any],
    prior_task_path: Path | None,
    prior_dispatch_receipt_path: Path | None,
    prior_submission_path: Path | None,
    schemas: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, str] | None]:
    stage = task_stage(task)
    if stage == "reconstruction":
        if (
            prior_task_path is not None
            or prior_dispatch_receipt_path is not None
            or prior_submission_path is not None
        ):
            raise ValueError("reconstruction chain cannot accept a prior submission")
        return None, None
    if (
        prior_task_path is None
        or prior_dispatch_receipt_path is None
        or prior_submission_path is None
    ):
        raise ValueError(
            "prediction chain requires prior task, dispatch receipt, and submission"
        )

    prior = verify_submission_chain(
        repo_root,
        prior_task_path,
        prior_submission_path,
        prior_dispatch_receipt_path,
        schemas,
    )
    prior_bytes = prior_submission_path.read_bytes()
    prior_sha = sha256(prior_bytes)
    if envelope["prior_stage_submission_sha256"] != prior_sha:
        raise ValueError("prediction envelope prior hash mismatch")
    if (
        prior["artifact_type"] != "reconstruction_submission"
        or prior["run_id"] != task["run_id"]
        or prior["condition_id"] != envelope["condition_id"]
        or prior["actor"] != envelope["actor"]
    ):
        raise ValueError(
            "prediction prior does not preserve stage, run, condition, and actor"
        )
    return prior, {
        "artifact_id": prior["submission_id"],
        "sha256": prior_sha,
    }


def command_render(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    schemas = load_schemas(repo_root)
    task_path = repo_path(repo_root, args.task)
    task, _ = load_json(task_path)
    verify_task_contract(repo_root, task_path, task, schemas)
    output_path = ensure_new_output(repo_root, args.output)
    template = render_template(repo_root, task, schemas)
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
    dispatch_receipt_path = repo_path(repo_root, args.dispatch_receipt)
    prior_path = (
        repo_path(repo_root, args.prior_stage_submission)
        if args.prior_stage_submission is not None
        else None
    )
    prior_task_path = (
        repo_path(repo_root, args.prior_stage_task)
        if args.prior_stage_task is not None
        else None
    )
    prior_dispatch_receipt_path = (
        repo_path(repo_root, args.prior_stage_dispatch_receipt)
        if args.prior_stage_dispatch_receipt is not None
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
        dispatch_receipt_path,
        prior_path,
        prior_task_path,
        prior_dispatch_receipt_path,
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
    dispatch_receipt_reference: dict[str, str],
    prior_reference: dict[str, str] | None = None,
) -> None:
    expected_artifacts = [
        {
            "artifact_id": task["task_id"],
            "sha256": sha256(task_path.read_bytes()),
        }
    ]
    expected_artifacts.extend(
        {
            "artifact_id": item["artifact_id"],
            "sha256": item["sha256"],
        }
        for item in task["input_artifacts"]
    )
    expected_artifacts.append(dispatch_receipt_reference)
    stage = task_stage(task)
    if stage == "prediction":
        if prior_reference is None:
            raise ValueError(
                "prediction envelope verification requires its exact prior"
            )
        expected_artifacts.append(prior_reference)
    elif prior_reference is not None:
        raise ValueError("reconstruction envelope cannot bind a prior submission")
    if envelope["dispatch_artifacts"] != expected_artifacts:
        raise ValueError(
            "envelope dispatch artifacts differ from the exact ordered task set"
        )
    if envelope["run_id"] != task["run_id"]:
        raise ValueError("envelope run_id differs from task")
    if envelope["task_id"] != task["task_id"]:
        raise ValueError("envelope task_id differs from task")
    if envelope["stage"] != stage:
        raise ValueError("envelope stage differs from task type")
    if stage == "reconstruction":
        if envelope["condition_id"] != task["condition_id"]:
            raise ValueError(
                "reconstruction envelope condition differs from task condition"
            )
        if envelope["prior_stage_submission_sha256"] is not None:
            raise ValueError("reconstruction envelope unexpectedly binds a prior")
    elif envelope["condition_id"] not in {"condition-v01", "condition-v02"}:
        raise ValueError("prediction envelope has no valid condition binding")


def command_assemble(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    schemas = load_schemas(repo_root)
    task_path = repo_path(repo_root, args.task)
    envelope_path = repo_path(repo_root, args.envelope)
    payload_path = repo_path(repo_root, args.payload)
    dispatch_receipt_path = repo_path(repo_root, args.dispatch_receipt)
    prior_task_path = (
        repo_path(repo_root, args.prior_stage_task)
        if args.prior_stage_task is not None
        else None
    )
    prior_submission_path = (
        repo_path(repo_root, args.prior_stage_submission)
        if args.prior_stage_submission is not None
        else None
    )
    prior_dispatch_receipt_path = (
        repo_path(repo_root, args.prior_stage_dispatch_receipt)
        if args.prior_stage_dispatch_receipt is not None
        else None
    )
    submission_output = ensure_new_output(repo_root, args.submission_output)

    task, _ = load_json(task_path)
    envelope, _ = load_json(envelope_path)
    payload, payload_bytes = load_json(payload_path)
    registry = schema_registry(schemas)
    verify_task_contract(repo_root, task_path, task, schemas)
    validate(envelope, schemas["interface"], registry)
    validate(payload, schemas["interface"], registry)
    _, dispatch_reference = verify_dispatch_receipt(
        repo_root,
        task_path,
        task,
        envelope["actor"],
        envelope["condition_id"],
        dispatch_receipt_path,
        prior_dispatch_receipt_path,
        prior_submission_path,
    )
    prior, prior_reference = verify_current_prior(
        repo_root,
        task,
        envelope,
        prior_task_path,
        prior_dispatch_receipt_path,
        prior_submission_path,
        schemas,
    )
    verify_envelope_task(
        task_path,
        task,
        envelope,
        dispatch_reference,
        prior_reference,
    )
    verify_answer_scope(task, payload)
    verify_support_scope(
        task,
        payload,
        permitted_support_ids(
            repo_root,
            task,
            prior_task_path,
            prior,
        ),
    )

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
    task_path = repo_path(repo_root, args.task)
    envelope_path = repo_path(repo_root, args.envelope)
    payload_path = repo_path(repo_root, args.payload)
    submission_path = repo_path(repo_root, args.submission)
    dispatch_receipt_path = repo_path(repo_root, args.dispatch_receipt)
    prior_task_path = (
        repo_path(repo_root, args.prior_stage_task)
        if args.prior_stage_task is not None
        else None
    )
    prior_submission_path = (
        repo_path(repo_root, args.prior_stage_submission)
        if args.prior_stage_submission is not None
        else None
    )
    prior_dispatch_receipt_path = (
        repo_path(repo_root, args.prior_stage_dispatch_receipt)
        if args.prior_stage_dispatch_receipt is not None
        else None
    )
    task, _ = load_json(task_path)
    envelope, _ = load_json(envelope_path)
    payload, payload_bytes = load_json(payload_path)
    submission, submission_bytes = load_json(submission_path)

    registry = schema_registry(schemas)
    verify_task_contract(repo_root, task_path, task, schemas)
    validate(envelope, schemas["interface"], registry)
    validate(payload, schemas["interface"], registry)
    _, dispatch_reference = verify_dispatch_receipt(
        repo_root,
        task_path,
        task,
        envelope["actor"],
        envelope["condition_id"],
        dispatch_receipt_path,
        prior_dispatch_receipt_path,
        prior_submission_path,
    )
    prior, prior_reference = verify_current_prior(
        repo_root,
        task,
        envelope,
        prior_task_path,
        prior_dispatch_receipt_path,
        prior_submission_path,
        schemas,
    )
    verify_envelope_task(
        task_path,
        task,
        envelope,
        dispatch_reference,
        prior_reference,
    )
    verify_answer_scope(task, payload)
    verify_support_scope(
        task,
        payload,
        permitted_support_ids(
            repo_root,
            task,
            prior_task_path,
            prior,
        ),
    )
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
    capture.add_argument("--dispatch-receipt", required=True, type=Path)
    capture.add_argument("--submission-id", required=True)
    capture.add_argument("--condition-id")
    capture.add_argument("--prior-stage-dispatch-receipt", type=Path)
    capture.add_argument("--prior-stage-submission", type=Path)
    capture.add_argument("--prior-stage-task", type=Path)
    capture.add_argument("--envelope-output", required=True, type=Path)
    capture.set_defaults(func=command_capture)

    assemble = subcommands.add_parser("assemble")
    assemble.add_argument("--repo-root", required=True, type=Path)
    assemble.add_argument("--task", required=True, type=Path)
    assemble.add_argument("--envelope", required=True, type=Path)
    assemble.add_argument("--payload", required=True, type=Path)
    assemble.add_argument("--dispatch-receipt", required=True, type=Path)
    assemble.add_argument("--prior-stage-dispatch-receipt", type=Path)
    assemble.add_argument("--prior-stage-submission", type=Path)
    assemble.add_argument("--prior-stage-task", type=Path)
    assemble.add_argument("--submission-output", required=True, type=Path)
    assemble.set_defaults(func=command_assemble)

    verify = subcommands.add_parser("verify")
    verify.add_argument("--repo-root", required=True, type=Path)
    verify.add_argument("--task", required=True, type=Path)
    verify.add_argument("--envelope", required=True, type=Path)
    verify.add_argument("--payload", required=True, type=Path)
    verify.add_argument("--dispatch-receipt", required=True, type=Path)
    verify.add_argument("--prior-stage-dispatch-receipt", type=Path)
    verify.add_argument("--prior-stage-submission", type=Path)
    verify.add_argument("--prior-stage-task", type=Path)
    verify.add_argument("--submission", required=True, type=Path)
    verify.set_defaults(func=command_verify)
    return root


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
