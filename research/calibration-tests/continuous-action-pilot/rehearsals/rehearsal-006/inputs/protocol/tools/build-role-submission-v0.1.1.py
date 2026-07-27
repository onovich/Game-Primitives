#!/usr/bin/env python3
"""Validate raw protocol 0.1.1 replies and assemble role submissions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


INTERFACE_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "blind-response-interface-0.1.1.schema.json"
)
PREDICTION_CONTRACT_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "prediction-participant-response-contract-0.1.1.schema.json"
)
PREDICTION_TEMPLATE_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "response-template-0.1.1.schema.json"
)
RECONSTRUCTION_CONTRACT_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "reconstruction-participant-response-contract-0.1.1.schema.json"
)
RECONSTRUCTION_TEMPLATE_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "reconstruction-response-template-0.1.1.schema.json"
)
ROLE_011_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "role-submission-0.1.1.schema.json"
)
ROLE_012_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "role-submission-0.1.2.schema.json"
)
TASK_SCHEMA_PATHS = (
    Path(
        "research/calibration-tests/continuous-action-pilot/schema/"
        "task-packet-0.1.0.schema.json"
    ),
    Path(
        "research/calibration-tests/continuous-action-pilot/schema/"
        "task-packet-0.1.1.schema.json"
    ),
    Path(
        "research/calibration-tests/continuous-action-pilot/schema/"
        "task-packet-0.1.2.schema.json"
    ),
)
TOOL_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/tools/"
    "build-role-submission-v0.1.1.py"
)
VARIANT_SCHEMA_PATH = Path(
    "research/calibration-tests/continuous-action-pilot/schema/"
    "variant-envelope-0.1.0.schema.json"
)
LOCAL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
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


class BuildError(RuntimeError):
    """Raised when participant material cannot be safely assembled."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def read_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r\n" in raw:
        raise BuildError(f"non-canonical UTF-8 JSON: {path}")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise BuildError(f"expected JSON object: {path}")
    return value, raw


def repo_path(repo_root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(repo_root.resolve()):
        raise BuildError(f"path escapes repository root: {value}")
    return resolved


def relative_path(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def new_output(repo_root: Path, value: str | Path) -> Path:
    path = repo_path(repo_root, value)
    if path.exists():
        raise BuildError(f"refusing to overwrite existing artifact: {path}")
    if not path.parent.is_dir():
        raise BuildError(f"output directory does not exist: {path.parent}")
    return path


def validate(
    instance: dict[str, Any],
    schema: dict[str, Any],
    *,
    registry: Registry,
) -> None:
    validator = Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )
    def leaves(error: Any) -> list[Any]:
        if not error.context:
            return [error]
        return [
            leaf
            for child in error.context
            for leaf in leaves(child)
        ]

    errors = sorted(
        (
            leaf
            for error in validator.iter_errors(instance)
            for leaf in leaves(error)
        ),
        key=lambda error: (
            [str(part) for part in error.absolute_path],
            error.message,
        ),
    )
    if errors:
        lines = []
        for error in errors[:16]:
            location = "/".join(
                str(part) for part in error.absolute_path
            ) or "<root>"
            lines.append(f"{location}: {error.message}")
        raise BuildError("schema validation failed:\n" + "\n".join(lines))


def load_schemas(repo_root: Path) -> dict[str, Any]:
    paths = {
        "interface": INTERFACE_PATH,
        "prediction_contract": PREDICTION_CONTRACT_SCHEMA_PATH,
        "prediction_template": PREDICTION_TEMPLATE_SCHEMA_PATH,
        "reconstruction_contract": RECONSTRUCTION_CONTRACT_SCHEMA_PATH,
        "reconstruction_template": RECONSTRUCTION_TEMPLATE_SCHEMA_PATH,
        "role_011": ROLE_011_PATH,
        "role_012": ROLE_012_PATH,
        "variant": VARIANT_SCHEMA_PATH,
    }
    schemas: dict[str, Any] = {}
    for name, path in paths.items():
        schema, _ = read_json(repo_path(repo_root, path))
        Draft202012Validator.check_schema(schema)
        schemas[name] = schema
    task_schemas = []
    for path in TASK_SCHEMA_PATHS:
        schema, _ = read_json(repo_path(repo_root, path))
        Draft202012Validator.check_schema(schema)
        task_schemas.append(schema)
    schemas["tasks"] = task_schemas

    registry = Registry()
    for schema in [
        *task_schemas,
        *(
            value
            for key, value in schemas.items()
            if key != "tasks"
        ),
    ]:
        registry = registry.with_resource(
            schema["$id"], Resource.from_contents(schema)
        )
    schemas["registry"] = registry
    return schemas


def task_stage(task: dict[str, Any]) -> str:
    artifact_type = task.get("artifact_type")
    if artifact_type == "reconstruction_task_packet":
        return "reconstruction"
    if artifact_type == "prediction_task_packet":
        return "prediction"
    raise BuildError("only reconstruction and prediction tasks are supported")


def validate_task(
    repo_root: Path,
    task: dict[str, Any],
    schemas: dict[str, Any],
) -> None:
    matches = [
        schema
        for schema in schemas["tasks"]
        if schema["$id"] == task.get("$schema")
    ]
    if len(matches) != 1:
        raise BuildError("task does not select a supported task Schema")
    validate(task, matches[0], registry=schemas["registry"])

    output_schema = task["output_schema"]
    interface_path = repo_path(repo_root, INTERFACE_PATH)
    if (
        output_schema["path"].replace("\\", "/")
        != INTERFACE_PATH.as_posix()
        or output_schema["sha256"] != sha256(interface_path.read_bytes())
    ):
        raise BuildError(
            "task output_schema is not bound to blind response 0.1.1"
        )
    assembled_schema = task["assembled_output_schema"]
    role_path = repo_path(repo_root, ROLE_012_PATH)
    if (
        assembled_schema["path"].replace("\\", "/")
        != ROLE_012_PATH.as_posix()
        or assembled_schema["sha256"] != sha256(role_path.read_bytes())
    ):
        raise BuildError(
            "task assembled_output_schema is not bound to role 0.1.2"
        )
    for artifact in task["input_artifacts"]:
        path = repo_path(repo_root, artifact["path"])
        if sha256(path.read_bytes()) != artifact["sha256"]:
            raise BuildError(
                f"task input hash mismatch: {artifact['artifact_id']}"
            )


def load_template(
    repo_root: Path,
    task: dict[str, Any],
    template_path: Path,
    schemas: dict[str, Any],
) -> dict[str, Any]:
    template, template_raw = read_json(template_path)
    stage = task_stage(task)
    schema = schemas[f"{stage}_template"]
    validate(template, schema, registry=schemas["registry"])
    if (
        template["run_id"] != task["run_id"]
        or template["stage"] != stage
        or template["artifact_type"] != f"{stage}_response_template"
    ):
        raise BuildError("response template stage/run differs from task")
    relative = relative_path(repo_root, template_path)
    matches = [
        item
        for item in task["input_artifacts"]
        if item["path"].replace("\\", "/") == relative
    ]
    if len(matches) != 1:
        raise BuildError("task does not bind the supplied response template")
    binding = matches[0]
    if (
        binding["sha256"] != sha256(template_raw)
        or binding["artifact_id"] != template["template_id"]
    ):
        raise BuildError("task/template path, ID, or hash binding differs")
    target = template["target_response_schema"]
    interface_path = repo_path(repo_root, INTERFACE_PATH)
    if (
        target["path"].replace("\\", "/") != INTERFACE_PATH.as_posix()
        or target["sha256"] != sha256(interface_path.read_bytes())
    ):
        raise BuildError("template target response Schema binding differs")
    return template


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


def allowed_support_ids(
    repo_root: Path,
    task: dict[str, Any],
    prior: dict[str, Any] | None,
    prior_task: dict[str, Any] | None,
) -> set[str]:
    result = declared_local_ids(task)
    for artifact in task["input_artifacts"]:
        path = repo_path(repo_root, artifact["path"])
        if path.suffix.lower() != ".json":
            continue
        value, _ = read_json(path)
        result.update(declared_local_ids(value))
    if prior is not None:
        result.update(declared_local_ids(prior))
    if prior_task is not None:
        result.update(declared_local_ids(prior_task))
        for artifact in prior_task["input_artifacts"]:
            path = repo_path(repo_root, artifact["path"])
            if path.suffix.lower() != ".json":
                continue
            value, _ = read_json(path)
            result.update(declared_local_ids(value))
    return result


def verify_support_scope(
    payload: dict[str, Any],
    *,
    stage: str,
    allowed_ids: set[str],
) -> None:
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
            raise BuildError(
                f"{label} cites IDs outside dispatched material: {forbidden}"
            )


def observations_by_case(
    task: dict[str, Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    observations = {
        item["observation_id"]: item
        for item in task["allowed_observations"]
    }
    if len(observations) != len(task["allowed_observations"]):
        raise BuildError("task contains duplicate observation IDs")
    result: dict[str, dict[str, dict[str, Any]]] = {}
    claimed: set[str] = set()
    for intervention in task["variant_interventions"]:
        case_id = intervention["case_id"]
        if case_id in result:
            raise BuildError(f"duplicate intervention case: {case_id}")
        observation_ids = intervention["observation_ids"]
        if len(observation_ids) != len(set(observation_ids)):
            raise BuildError(f"{case_id} repeats an observation ID")
        unknown = set(observation_ids) - set(observations)
        if unknown:
            raise BuildError(
                f"{case_id} references unknown observations: {sorted(unknown)}"
            )
        overlap = claimed & set(observation_ids)
        if overlap:
            raise BuildError(
                f"observations belong to multiple cases: {sorted(overlap)}"
            )
        claimed.update(observation_ids)
        result[case_id] = {
            observation_id: observations[observation_id]
            for observation_id in observation_ids
        }
    if claimed != set(observations):
        raise BuildError("some task observations belong to no case")
    if set(result) != set(task["case_ids"]):
        raise BuildError("intervention cases differ from task case_ids")
    return result


def verify_case_coverage(
    task: dict[str, Any],
    payload: dict[str, Any],
    *,
    stage: str,
) -> list[dict[str, Any]]:
    answers = payload[f"{stage}_answers"]
    actual = [answer["case_id"] for answer in answers]
    if len(actual) != len(set(actual)) or set(actual) != set(task["case_ids"]):
        raise BuildError(
            f"{stage} payload must contain each task case exactly once"
        )
    return answers


def verify_expectation_product(
    task: dict[str, Any],
    case_id: str,
    observations: dict[str, dict[str, Any]],
    expectations: list[dict[str, Any]],
    *,
    label: str,
    require_indeterminate: bool,
    require_concrete: bool,
) -> None:
    expected_pairs = {
        (configuration_id, observation_id)
        for configuration_id in task["allowed_configurations"]
        for observation_id in observations
    }
    actual_pairs = [
        (item["configuration_id"], item["observation_id"])
        for item in expectations
    ]
    if (
        len(actual_pairs) != len(expected_pairs)
        or set(actual_pairs) != expected_pairs
    ):
        raise BuildError(
            f"{case_id} {label} must cover each configuration/observation "
            "pair exactly once"
        )
    for expectation in expectations:
        observation = observations[expectation["observation_id"]]
        if (
            expectation["tolerance_rule_id"]
            != observation["tolerance_rule_id"]
        ):
            raise BuildError(
                f"{case_id} {label} changes tolerance for "
                f"{expectation['observation_id']}"
            )
        value = expectation["value"]
        if require_indeterminate:
            if (
                expectation["expectation_kind"] != "status"
                or value
                != {
                    "serialized_value": "indeterminate",
                    "unit": None,
                    "value_type": "status",
                }
            ):
                raise BuildError(
                    f"{case_id} {label} is not the exact indeterminate tuple"
                )
            continue
        if require_concrete and value["value_type"] == "status":
            raise BuildError(
                f"{case_id} {label} uses status in a concrete expectation"
            )
        determinate_types = {
            item
            for item in observation["allowed_value_types"]
            if item != "status"
        }
        if value["value_type"] not in determinate_types:
            raise BuildError(
                f"{case_id} {label} uses disallowed concrete value type "
                f"{value['value_type']} for {expectation['observation_id']}"
            )
        if value["unit"] != observation["unit"]:
            raise BuildError(
                f"{case_id} {label} changes declared unit for "
                f"{expectation['observation_id']}"
            )
        expected_kind = KIND_BY_VALUE_TYPE[value["value_type"]]
        if expectation["expectation_kind"] != expected_kind:
            raise BuildError(
                f"{case_id} {label} kind does not match selected value type"
            )


def prediction_signature(
    expectations: list[dict[str, Any]],
) -> str:
    ordered = sorted(
        expectations,
        key=lambda item: (
            item["configuration_id"],
            item["observation_id"],
        ),
    )
    projection = [
        {
            "configuration_id": item["configuration_id"],
            "expectation_kind": item["expectation_kind"],
            "observation_id": item["observation_id"],
            "tolerance_rule_id": item["tolerance_rule_id"],
            "value": item["value"],
        }
        for item in ordered
    ]
    return json.dumps(
        projection, ensure_ascii=False, sort_keys=True
    )


def verify_payload_scope(
    repo_root: Path,
    task: dict[str, Any],
    payload: dict[str, Any],
    *,
    prior: dict[str, Any] | None,
    prior_task: dict[str, Any] | None,
) -> None:
    stage = task_stage(task)
    answers = verify_case_coverage(
        task, payload, stage=stage
    )
    if stage == "prediction":
        case_observations = observations_by_case(task)
        for answer in answers:
            case_id = answer["case_id"]
            indeterminate = (
                answer["prediction_status"] == "indeterminate"
            )
            verify_expectation_product(
                task,
                case_id,
                case_observations[case_id],
                answer["expectations"],
                label="main expectations",
                require_indeterminate=indeterminate,
                require_concrete=not indeterminate,
            )
            signatures: list[str] = []
            alternative_ids: set[str] = set()
            for alternative in answer["compatible_alternatives"]:
                alternative_id = alternative["alternative_id"]
                if alternative_id in alternative_ids:
                    raise BuildError(
                        f"{case_id} repeats alternative_id {alternative_id}"
                    )
                alternative_ids.add(alternative_id)
                verify_expectation_product(
                    task,
                    case_id,
                    case_observations[case_id],
                    alternative["expectations"],
                    label=f"alternative {alternative_id}",
                    require_indeterminate=False,
                    require_concrete=True,
                )
                signatures.append(
                    prediction_signature(alternative["expectations"])
                )
            if indeterminate:
                if len(signatures) < 2:
                    raise BuildError(
                        f"{case_id} needs at least two complete alternatives"
                    )
                if len(set(signatures)) != len(signatures):
                    raise BuildError(
                        f"{case_id} alternatives do not predict distinct worlds"
                    )
    verify_support_scope(
        payload,
        stage=stage,
        allowed_ids=allowed_support_ids(
            repo_root, task, prior, prior_task
        ),
    )


def validate_payload(
    repo_root: Path,
    task: dict[str, Any],
    template: dict[str, Any],
    payload: dict[str, Any],
    schemas: dict[str, Any],
    *,
    prior: dict[str, Any] | None,
    prior_task: dict[str, Any] | None,
) -> None:
    stage = task_stage(task)
    validate(
        payload,
        {
            "$ref": (
                schemas["interface"]["$id"]
                + f"#/$defs/{stage}Payload"
            )
        },
        registry=schemas["registry"],
    )
    if (
        payload["artifact_type"] != f"{stage}_response_payload"
        or payload["artifact_version"] != "0.1.1"
        or payload["$schema"] != schemas["interface"]["$id"]
    ):
        raise BuildError("raw payload stage or protocol version differs")
    if template["template_payload"]["artifact_type"] != payload[
        "artifact_type"
    ]:
        raise BuildError("payload type differs from dispatched template")
    verify_payload_scope(
        repo_root,
        task,
        payload,
        prior=prior,
        prior_task=prior_task,
    )


def load_prior(
    repo_root: Path,
    task: dict[str, Any],
    actor: dict[str, Any],
    condition_id: str,
    prior_path: Path | None,
    prior_task_path: Path | None,
    schemas: dict[str, Any],
) -> tuple[
    dict[str, Any] | None,
    str | None,
    dict[str, Any] | None,
]:
    stage = task_stage(task)
    if stage == "reconstruction":
        if prior_path is not None or prior_task_path is not None:
            raise BuildError("reconstruction cannot bind a prior stage")
        if task["condition_id"] != condition_id:
            raise BuildError(
                "reconstruction task does not match the requested condition"
            )
        return None, None, None
    if prior_path is None or prior_task_path is None:
        raise BuildError(
            "prediction requires a prior reconstruction and its task"
        )
    prior_task, _ = read_json(prior_task_path)
    validate_task(repo_root, prior_task, schemas)
    if (
        task_stage(prior_task) != "reconstruction"
        or prior_task["run_id"] != task["run_id"]
        or prior_task["condition_id"] != condition_id
    ):
        raise BuildError(
            "prior task does not identify the matching reconstruction"
        )
    prior, raw = read_json(prior_path)
    validate(prior, schemas["role_012"], registry=schemas["registry"])
    if (
        prior["artifact_type"] != "reconstruction_submission"
        or prior["run_id"] != task["run_id"]
        or prior["condition_id"] != condition_id
        or prior["actor"] != actor
        or prior["task_id"] != prior_task["task_id"]
    ):
        raise BuildError(
            "prior reconstruction does not preserve actor/run/condition"
        )
    return prior, sha256(raw), prior_task


def build_envelope(
    repo_root: Path,
    task_path: Path,
    task: dict[str, Any],
    actor: dict[str, Any],
    condition_id: str,
    submission_id: str,
    received_at: str,
    prior: dict[str, Any] | None,
    prior_sha256: str | None,
    schemas: dict[str, Any],
) -> dict[str, Any]:
    stage = task_stage(task)
    artifacts = [
        {
            "artifact_id": task["task_id"],
            "sha256": sha256(task_path.read_bytes()),
        },
        *(
            {
                "artifact_id": item["artifact_id"],
                "sha256": item["sha256"],
            }
            for item in task["input_artifacts"]
        ),
    ]
    if prior is not None and prior_sha256 is not None:
        artifacts.append(
            {
                "artifact_id": prior["submission_id"],
                "sha256": prior_sha256,
            }
        )
    role_path = repo_path(repo_root, ROLE_012_PATH)
    interface_path = repo_path(repo_root, INTERFACE_PATH)
    tool_path = repo_path(repo_root, TOOL_PATH)
    envelope = {
        "$schema": schemas["interface"]["$id"],
        "actor": actor,
        "artifact_type": "role_submission_envelope",
        "artifact_version": "0.1.1",
        "condition_id": condition_id,
        "dispatch_artifacts": artifacts,
        "first_submission": True,
        "output_schema": {
            "path": ROLE_012_PATH.as_posix(),
            "sha256": sha256(role_path.read_bytes()),
        },
        "packager": {
            "path": TOOL_PATH.as_posix(),
            "sha256": sha256(tool_path.read_bytes()),
        },
        "prior_stage_submission_sha256": prior_sha256,
        "received_at": received_at,
        "response_schema": {
            "path": INTERFACE_PATH.as_posix(),
            "sha256": sha256(interface_path.read_bytes()),
        },
        "run_id": task["run_id"],
        "stage": stage,
        "submission_id": submission_id,
        "target_artifact_type": f"{stage}_submission",
        "target_artifact_version": "0.1.2",
        "task_id": task["task_id"],
    }
    validate(envelope, schemas["interface"], registry=schemas["registry"])
    return envelope


def build_submission(
    repo_root: Path,
    payload_path: Path,
    payload: dict[str, Any],
    payload_raw: bytes,
    envelope_path: Path,
    envelope_raw: bytes,
    envelope: dict[str, Any],
    schemas: dict[str, Any],
) -> dict[str, Any]:
    stage = envelope["stage"]
    answer_key = f"{stage}_answers"
    submission = {
        "$schema": schemas["role_012"]["$id"],
        "actor": envelope["actor"],
        "artifact_type": envelope["target_artifact_type"],
        "artifact_version": envelope["target_artifact_version"],
        "audit_checks": [],
        "audit_decision": None,
        "condition_id": envelope["condition_id"],
        "findings": [],
        "first_submission": True,
        "input_artifacts": envelope["dispatch_artifacts"],
        "packaging": {
            "copied_fields": [
                "pollution",
                answer_key,
            ],
            "envelope_path": relative_path(repo_root, envelope_path),
            "envelope_sha256": sha256(envelope_raw),
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
            "sha256": sha256(payload_raw),
        },
        "reconstruction_answers": (
            payload["reconstruction_answers"]
            if stage == "reconstruction"
            else []
        ),
        "run_id": envelope["run_id"],
        "stage": stage,
        "submission_id": envelope["submission_id"],
        "submitted_at": envelope["received_at"],
        "task_id": envelope["task_id"],
    }
    validate(submission, schemas["role_012"], registry=schemas["registry"])
    if submission["pollution"] != payload["pollution"]:
        raise AssertionError("pollution was not copied exactly")
    if submission[answer_key] != payload[answer_key]:
        raise AssertionError(f"{answer_key} was not copied exactly")
    return submission


def load_inputs(
    args: argparse.Namespace,
) -> tuple[
    Path,
    dict[str, Any],
    Path,
    dict[str, Any],
    dict[str, Any],
    bytes,
    dict[str, Any],
    dict[str, Any] | None,
    str | None,
    dict[str, Any] | None,
    dict[str, Any],
]:
    repo_root = args.repo_root.resolve()
    schemas = load_schemas(repo_root)
    task_path = repo_path(repo_root, args.task)
    template_path = repo_path(repo_root, args.template)
    payload_path = repo_path(repo_root, args.payload)
    actor_path = repo_path(repo_root, args.actor)
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
    task, _ = read_json(task_path)
    payload, payload_raw = read_json(payload_path)
    actor, _ = read_json(actor_path)
    validate_task(repo_root, task, schemas)
    template = load_template(
        repo_root, task, template_path, schemas
    )
    validate(
        actor,
        {
            "$ref": (
                schemas["role_011"]["$id"]
                + "#/$defs/testActor"
            )
        },
        registry=schemas["registry"],
    )
    prior, prior_sha, prior_task = load_prior(
        repo_root,
        task,
        actor,
        args.condition_id,
        prior_path,
        prior_task_path,
        schemas,
    )
    validate_payload(
        repo_root,
        task,
        template,
        payload,
        schemas,
        prior=prior,
        prior_task=prior_task,
    )
    return (
        task_path,
        task,
        payload_path,
        payload,
        payload_raw,
        actor,
        prior,
        prior_sha,
        prior_task,
        schemas,
    )


def command_validate_payload(args: argparse.Namespace) -> int:
    (
        _,
        task,
        _,
        _,
        payload_raw,
        _,
        _,
        _,
        _,
        _,
    ) = load_inputs(args)
    print(
        json.dumps(
            {
                "payload_sha256": sha256(payload_raw),
                "stage": task_stage(task),
                "status": "payload_valid",
            },
            sort_keys=True,
        )
    )
    return 0


def command_assemble(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    envelope_output = new_output(repo_root, args.envelope_output)
    submission_output = new_output(repo_root, args.submission_output)
    (
        task_path,
        task,
        payload_path,
        payload,
        payload_raw,
        actor,
        prior,
        prior_sha,
        _,
        schemas,
    ) = load_inputs(args)
    envelope = build_envelope(
        repo_root,
        task_path,
        task,
        actor,
        args.condition_id,
        args.submission_id,
        args.received_at,
        prior,
        prior_sha,
        schemas,
    )
    envelope_raw = canonical_bytes(envelope)
    submission = build_submission(
        repo_root,
        payload_path,
        payload,
        payload_raw,
        envelope_output,
        envelope_raw,
        envelope,
        schemas,
    )
    submission_raw = canonical_bytes(submission)
    try:
        envelope_output.write_bytes(envelope_raw)
        submission_output.write_bytes(submission_raw)
    except OSError:
        envelope_output.unlink(missing_ok=True)
        submission_output.unlink(missing_ok=True)
        raise
    print(
        json.dumps(
            {
                "envelope_sha256": sha256(envelope_raw),
                "payload_sha256": sha256(payload_raw),
                "status": "assembled",
                "submission_sha256": sha256(submission_raw),
            },
            sort_keys=True,
        )
    )
    return 0


def command_verify(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    envelope_path = repo_path(repo_root, args.envelope)
    submission_path = repo_path(repo_root, args.submission)
    (
        task_path,
        task,
        payload_path,
        payload,
        payload_raw,
        actor,
        prior,
        prior_sha,
        _,
        schemas,
    ) = load_inputs(args)
    envelope, envelope_raw = read_json(envelope_path)
    submission, submission_raw = read_json(submission_path)
    expected_envelope = build_envelope(
        repo_root,
        task_path,
        task,
        actor,
        args.condition_id,
        args.submission_id,
        args.received_at,
        prior,
        prior_sha,
        schemas,
    )
    if envelope != expected_envelope or envelope_raw != canonical_bytes(
        expected_envelope
    ):
        raise BuildError("envelope differs from deterministic rebuild")
    expected_submission = build_submission(
        repo_root,
        payload_path,
        payload,
        payload_raw,
        envelope_path,
        envelope_raw,
        envelope,
        schemas,
    )
    if submission != expected_submission or submission_raw != canonical_bytes(
        expected_submission
    ):
        raise BuildError("submission differs from deterministic rebuild")
    print(
        json.dumps(
            {
                "envelope_sha256": sha256(envelope_raw),
                "status": "verified",
                "submission_sha256": sha256(submission_raw),
            },
            sort_keys=True,
        )
    )
    return 0


def add_common_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--repo-root", required=True, type=Path)
    command.add_argument("--task", required=True, type=Path)
    command.add_argument("--template", required=True, type=Path)
    command.add_argument("--payload", required=True, type=Path)
    command.add_argument("--actor", required=True, type=Path)
    command.add_argument("--condition-id", required=True)
    command.add_argument("--prior-stage-submission", type=Path)
    command.add_argument("--prior-stage-task", type=Path)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    subcommands = root.add_subparsers(dest="command", required=True)
    validate_payload_parser = subcommands.add_parser("validate-payload")
    add_common_arguments(validate_payload_parser)
    validate_payload_parser.set_defaults(func=command_validate_payload)
    assemble = subcommands.add_parser("assemble")
    add_common_arguments(assemble)
    assemble.add_argument("--submission-id", required=True)
    assemble.add_argument("--received-at", required=True)
    assemble.add_argument("--envelope-output", required=True, type=Path)
    assemble.add_argument("--submission-output", required=True, type=Path)
    assemble.set_defaults(func=command_assemble)
    verify = subcommands.add_parser("verify")
    add_common_arguments(verify)
    verify.add_argument("--submission-id", required=True)
    verify.add_argument("--received-at", required=True)
    verify.add_argument("--envelope", required=True, type=Path)
    verify.add_argument("--submission", required=True, type=Path)
    verify.set_defaults(func=command_verify)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (
        BuildError,
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
