#!/usr/bin/env python3
"""Shared contract for the inert continuous-002 actor-dispatch plan.

This module only builds and verifies pre-gate files.  It does not create an
actor, thread, session, dispatch receipt, or network request.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


PILOT = Path("research/calibration-tests/continuous-action-pilot")
RUN = PILOT / "runs/continuous-002"
DISPATCH_INPUTS = RUN / "inputs/dispatch"
PROMPT_DIRECTORY = DISPATCH_INPUTS / "prompts"
PROMPT_BODY_DIRECTORY = RUN / "source/dispatch-bodies"
PROMPT_BODY_PATHS = {
    "stage1_atomic": PROMPT_BODY_DIRECTORY / "stage1-atomic.body.txt",
    "stage1_rich": PROMPT_BODY_DIRECTORY / "stage1-rich.body.txt",
    "stage2": PROMPT_BODY_DIRECTORY / "stage2.body.txt",
}

SCHEMA_PATH = PILOT / "schema/formal-actor-dispatch-plan-0.1.0.schema.json"
CORE_PATH = PILOT / "tools/formal_actor_dispatch_plan_contract.py"
MATERIALIZER_PATH = (
    PILOT / "tools/materialize-formal-actor-dispatch-plan-v0.1.0.py"
)
VERIFIER_PATH = PILOT / "tools/verify-formal-actor-dispatch-plan-v0.1.0.py"
PLAN_PATH = DISPATCH_INPUTS / "actor-dispatch-plan.json"

SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-actor-dispatch-plan-0.1.0.schema.json"
)
SCHEMA_SHA256 = "208e12288bc7ec32f09d7cbc76bf2b23d40c122ddf3903df9029f5b541d2efa3"

SEATS = ("p01", "p02", "p03", "p04")
CONDITION_BY_SEAT = {
    "p01": "rich",
    "p02": "rich",
    "p03": "atomic",
    "p04": "atomic",
}
CONTRACT_ARTIFACT_PATHS = {
    "contract_core": CORE_PATH,
    "materializer": MATERIALIZER_PATH,
    "schema": SCHEMA_PATH,
    "verifier": VERIFIER_PATH,
}

_RUNTIME_ASSIGNMENT = re.compile(
    r"""(?ix)
    \b(
      thread_id|threadId|
      session_id|sessionId|
      receipt_id|receiptId|dispatch_receipt|
      stage1_dispatch_receipt|stage2_dispatch_receipt|
      actor_identifier|actorIdentifier|actor_descriptor|actorDescriptor
    )
    \b\s*["']?\s*[:=]
    """
)
_RUNTIME_PLACEHOLDER_LINE = re.compile(
    r"""(?ix)
    \s*
    (?:
      (?P<quote>["'])
      (?:
        none|null|unknown|
        template(?:_[a-z0-9._:/-]+)?|
        planned(?:_[a-z0-9._:/-]+)?
      )
      (?P=quote)
      |
      (?:
        none|null|unknown|
        template(?:_[a-z0-9._:/-]+)?|
        planned(?:_[a-z0-9._:/-]+)?
      )
    )
    \s*[\]}]*\s*
    """
)
_ASCII_ESCAPE = re.compile(
    r"""(?ix)
    \\+
    (?:
      u(?P<unicode>[0-9a-f]{4})
      |
      x(?P<hex>[0-9a-f]{2})
    )
    """
)
_RECEIPT_ARTIFACT = re.compile(
    r"""(?ix)
    ["']artifact_type["']\s*:\s*["']
    (?:stage[12]_seat_dispatch_receipt|external_dispatch_attestation)
    ["']
    """
)


class DispatchPlanError(RuntimeError):
    """Fail-closed error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def canonical_bytes(value: Any) -> bytes:
    """Return the repository canonical JSON representation."""

    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _relative_text(value: str | Path) -> str:
    text = value.as_posix() if isinstance(value, Path) else value
    if (
        not text
        or "\\" in text
        or text.startswith("/")
        or re.match(r"^[A-Za-z]:", text)
    ):
        raise DispatchPlanError(
            "PATH_NOT_REPOSITORY_RELATIVE",
            f"path must be a non-empty POSIX repository-relative path: {text!r}",
        )
    pure = PurePosixPath(text)
    canonical = pure.as_posix()
    if (
        canonical != text
        or any(part in ("", ".", "..") for part in pure.parts)
    ):
        raise DispatchPlanError(
            "PATH_NOT_CANONICAL",
            f"path contains an empty, dot, or parent segment: {text!r}",
        )
    return canonical


def _reject_symlink_components(repo_root: Path, relative: str) -> None:
    current = repo_root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise DispatchPlanError(
                "SYMLINK_FORBIDDEN",
                f"repository artifact traverses a symbolic link: {relative}",
            )


def resolve_repo_path(
    repo_root: Path,
    value: str | Path,
    *,
    require_file: bool,
) -> Path:
    """Resolve a repository-relative path without accepting path aliases."""

    root = repo_root.resolve()
    relative = _relative_text(value)
    _reject_symlink_components(root, relative)
    path = root.joinpath(*PurePosixPath(relative).parts)
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise DispatchPlanError(
            "PATH_ESCAPE",
            f"path escapes repository root: {relative}",
        ) from error
    if require_file and not resolved.is_file():
        raise DispatchPlanError(
            "FILE_MISSING",
            f"required repository file is missing: {relative}",
        )
    return resolved


def assert_runtime_artifact_binding(
    repo_root: Path,
    role: str,
    runtime_path: Path,
) -> None:
    """Bind the executing artifact to the file declared by ``repo_root``."""

    try:
        expected_relative = CONTRACT_ARTIFACT_PATHS[role]
    except KeyError as error:
        raise DispatchPlanError(
            "RUNTIME_ARTIFACT_ROLE",
            f"unknown runtime artifact role: {role}",
        ) from error
    expected = resolve_repo_path(
        repo_root,
        expected_relative,
        require_file=True,
    ).resolve(strict=True)
    lexical_runtime = runtime_path.absolute()
    lexical_root = repo_root.resolve()
    try:
        runtime_relative = lexical_runtime.relative_to(lexical_root)
    except ValueError as error:
        raise DispatchPlanError(
            "RUNTIME_ARTIFACT_BINDING",
            f"executing {role} is outside the declared repository root",
        ) from error
    if runtime_relative.as_posix() != expected_relative.as_posix():
        raise DispatchPlanError(
            "RUNTIME_ARTIFACT_BINDING",
            f"executing {role} path differs from the declared contract path",
        )
    _reject_symlink_components(repo_root, runtime_relative.as_posix())
    try:
        actual = lexical_runtime.resolve(strict=True)
    except OSError as error:
        raise DispatchPlanError(
            "RUNTIME_ARTIFACT_BINDING",
            f"cannot resolve executing {role}: {runtime_path}",
        ) from error
    if actual != expected:
        raise DispatchPlanError(
            "RUNTIME_ARTIFACT_BINDING",
            f"executing {role} does not resolve to the declared contract file",
        )


def read_canonical_json(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    if (
        raw.startswith(b"\xef\xbb\xbf")
        or b"\r" in raw
        or not raw.endswith(b"\n")
    ):
        raise DispatchPlanError(
            "JSON_BYTES_NOT_CANONICAL",
            f"JSON must be UTF-8 without BOM, use LF, and end in LF: {path}",
        )
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DispatchPlanError(
            "JSON_PARSE",
            f"invalid UTF-8 JSON: {path}: {error}",
        ) from error
    if not isinstance(value, dict):
        raise DispatchPlanError(
            "JSON_OBJECT_REQUIRED",
            f"top-level JSON value must be an object: {path}",
        )
    if raw != canonical_bytes(value):
        raise DispatchPlanError(
            "JSON_BYTES_NOT_CANONICAL",
            f"JSON key order, indentation, or trailing bytes differ: {path}",
        )
    return value, raw


def _strict_text(raw: bytes, *, label: str) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise DispatchPlanError(
            "TEXT_BOM_FORBIDDEN",
            f"{label} must not contain a UTF-8 BOM",
        )
    if b"\r" in raw or b"\x00" in raw:
        raise DispatchPlanError(
            "TEXT_BYTES_NOT_CANONICAL",
            f"{label} must use LF and contain no NUL byte",
        )
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise DispatchPlanError(
            "TEXT_TRAILING_NEWLINE",
            f"{label} must end in exactly one LF",
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise DispatchPlanError(
            "TEXT_UTF8",
            f"{label} is not strict UTF-8: {error}",
        ) from error
    return text


def _reject_runtime_bindings(text: str, *, label: str) -> None:
    scan_text = text

    def replace_ascii_escape(match: re.Match[str]) -> str:
        digits = match.group("unicode") or match.group("hex")
        codepoint = int(digits, 16)
        if codepoint <= 0x7F:
            return chr(codepoint)
        return match.group(0)

    for _index in range(len(scan_text) + 1):
        normalized = re.sub(r"\\([\"'])", r"\1", scan_text)
        normalized = _ASCII_ESCAPE.sub(replace_ascii_escape, normalized)
        if normalized == scan_text:
            break
        if len(normalized) >= len(scan_text):
            raise DispatchPlanError(
                "RUNTIME_BINDING_NORMALIZATION",
                f"{label} runtime-binding normalization did not contract",
            )
        scan_text = normalized
    else:
        raise DispatchPlanError(
            "RUNTIME_BINDING_NORMALIZATION",
            f"{label} runtime-binding normalization did not converge",
        )

    for match in _RUNTIME_ASSIGNMENT.finditer(scan_text):
        line_end = scan_text.find("\n", match.end())
        value_text = scan_text[
            match.end() : len(scan_text) if line_end == -1 else line_end
        ]
        if _RUNTIME_PLACEHOLDER_LINE.fullmatch(value_text):
            continue
        raise DispatchPlanError(
            "ACTUAL_RUNTIME_BINDING_FORBIDDEN",
            f"{label} contains a non-template {match.group(1)} assignment",
        )
    if _RECEIPT_ARTIFACT.search(scan_text):
        raise DispatchPlanError(
            "ACTUAL_RECEIPT_FORBIDDEN",
            f"{label} contains an actual receipt artifact",
        )


def _read_prompt_body_source(
    repo_root: Path,
    value: str | Path,
) -> tuple[str, dict[str, Any]]:
    relative = _relative_text(value)
    allowed = {
        path.as_posix()
        for path in PROMPT_BODY_PATHS.values()
    }
    if relative not in allowed:
        raise DispatchPlanError(
            "PROMPT_BODY_SOURCE_NOT_ALLOWED",
            f"prompt body is outside the fixed continuous-002 sources: {relative}",
        )
    path = resolve_repo_path(repo_root, relative, require_file=True)
    raw = path.read_bytes()
    text = _strict_text(raw, label=relative)
    if "[formal_actor_dispatch_policy" in text.lower():
        raise DispatchPlanError(
            "NESTED_POLICY_BLOCK",
            f"prompt body must not supply its own dispatch policy: {value}",
        )
    _reject_runtime_bindings(text, label=relative)
    return text, {
        "byte_length": len(raw),
        "path": relative,
        "sha256": sha256_bytes(raw),
    }


def read_prompt_body(repo_root: Path, value: str | Path) -> str:
    return _read_prompt_body_source(repo_root, value)[0]


def _policy_block(*, stage: str, condition: str | None) -> str:
    common = [
        "[formal_actor_dispatch_policy 0.1.0]",
        "run_id=continuous-002",
        f"stage={stage}",
        "target_type=projectless",
        "blank_context_required=true",
        "fork_existing_thread=false",
        "tool_calls_allowed=false",
        "network_access_allowed=false",
        "shared_workspace_allowed=false",
        "other_conditions_or_submissions_visible=false",
        "commentary_allowed=false",
        "visible_analysis_allowed=false",
        "attachments_allowed=false",
        "assistant_event_contract=first_and_only_event_is_final_json",
        "markdown_wrapper_allowed=false",
        "corrective_followup_allowed=false",
    ]
    if stage == "stage1":
        if condition not in ("rich", "atomic"):
            raise DispatchPlanError(
                "CONDITION",
                f"unsupported stage1 condition: {condition!r}",
            )
        common.extend(
            [
                f"condition={condition}",
                "new_session_required=true",
                "same_session_for_stage2_required=true",
                "invalid_stage1_blocks_stage2=true",
            ]
        )
    elif stage == "stage2":
        if condition is not None:
            raise DispatchPlanError(
                "CONDITION",
                "stage2 prompt must be condition-neutral",
            )
        common.extend(
            [
                "same_session_as_stage1_required=true",
                "valid_stage1_required=true",
                "valid_stage2_cannot_retroactively_invalidate_stage1=true",
            ]
        )
    else:
        raise DispatchPlanError("STAGE", f"unsupported stage: {stage!r}")
    common.append("[/formal_actor_dispatch_policy]")
    return "\n".join(common)


def build_prompt(
    body: str,
    *,
    stage: str,
    condition: str | None,
) -> bytes:
    if not body.endswith("\n") or body.endswith("\n\n"):
        raise DispatchPlanError(
            "PROMPT_BODY_NEWLINE",
            "prompt body must end in exactly one LF",
        )
    raw = (_policy_block(stage=stage, condition=condition) + "\n\n" + body).encode(
        "utf-8"
    )
    _validate_prompt_bytes(raw, stage=stage, condition=condition)
    return raw


def _validate_prompt_bytes(
    raw: bytes,
    *,
    stage: str,
    condition: str | None,
) -> None:
    text = _strict_text(raw, label=f"{stage} prompt")
    expected_prefix = _policy_block(stage=stage, condition=condition) + "\n\n"
    if not text.startswith(expected_prefix):
        raise DispatchPlanError(
            "PROMPT_POLICY_MISMATCH",
            f"{stage} prompt does not begin with the exact policy block",
        )
    if text.count("[formal_actor_dispatch_policy 0.1.0]") != 1:
        raise DispatchPlanError(
            "PROMPT_POLICY_COUNT",
            f"{stage} prompt must contain exactly one policy block",
        )
    _reject_runtime_bindings(text, label=f"{stage} prompt")


def _created_at(value: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DispatchPlanError(
            "CREATED_AT",
            "created_at must be an RFC 3339 UTC timestamp ending in Z",
        )
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as error:
        raise DispatchPlanError(
            "CREATED_AT",
            f"invalid created_at timestamp: {value!r}",
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise DispatchPlanError(
            "CREATED_AT",
            "created_at must be UTC",
        )
    return value


def artifact_reference(repo_root: Path, relative: str | Path) -> dict[str, Any]:
    relative_text = _relative_text(relative)
    path = resolve_repo_path(repo_root, relative_text, require_file=True)
    raw = path.read_bytes()
    return {
        "byte_length": len(raw),
        "path": relative_text,
        "sha256": sha256_bytes(raw),
    }


def _prompt_path(stage: str, seat: str) -> Path:
    return PROMPT_DIRECTORY / f"{stage}-{seat}.prompt.txt"


def _prompt_reference(relative: Path, raw: bytes) -> dict[str, Any]:
    return {
        "byte_length": len(raw),
        "encoding": "utf-8",
        "path": relative.as_posix(),
        "sha256": sha256_bytes(raw),
    }


def _load_schema(repo_root: Path) -> dict[str, Any]:
    schema_path = resolve_repo_path(repo_root, SCHEMA_PATH, require_file=True)
    schema, raw = read_canonical_json(schema_path)
    if sha256_bytes(raw) != SCHEMA_SHA256:
        raise DispatchPlanError(
            "SCHEMA_HASH",
            "formal actor dispatch Schema differs from the pinned 0.1.0 bytes",
        )
    if schema.get("$id") != SCHEMA_ID:
        raise DispatchPlanError(
            "SCHEMA_ID",
            "formal actor dispatch Schema has the wrong $id",
        )
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as error:
        raise DispatchPlanError(
            "SCHEMA_INVALID",
            f"formal actor dispatch Schema is invalid: {error}",
        ) from error
    return schema


def validate_schema_document(repo_root: Path, plan: Mapping[str, Any]) -> None:
    schema = _load_schema(repo_root)
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(plan),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "/".join(str(part) for part in error.absolute_path)
        raise DispatchPlanError(
            "PLAN_SCHEMA",
            f"{location or '<root>'}: {error.message}",
        )


def expected_plan(
    repo_root: Path,
    *,
    created_at: str,
    prompt_bytes: Mapping[str, bytes],
    prompt_body_sources: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build the deterministic pre-gate plan around eight prompt byte strings."""

    _created_at(created_at)
    seats: list[dict[str, Any]] = []
    for seat in SEATS:
        stage1_path = _prompt_path("stage1", seat)
        stage2_path = _prompt_path("stage2", seat)
        seats.append(
            {
                "actor_role": "blind_reconstructor_predictor",
                "condition": CONDITION_BY_SEAT[seat],
                "runtime_binding": {
                    "actor_descriptor": None,
                    "session_id": None,
                    "stage1_dispatch_receipt": None,
                    "stage2_dispatch_receipt": None,
                    "thread_id": None,
                },
                "seat_id": seat,
                "stage1_prompt": _prompt_reference(
                    stage1_path,
                    prompt_bytes[stage1_path.as_posix()],
                ),
                "stage2_prompt": _prompt_reference(
                    stage2_path,
                    prompt_bytes[stage2_path.as_posix()],
                ),
            }
        )
    plan = {
        "$schema": SCHEMA_ID,
        "actor_configuration": {
            "observed_model_build": None,
            "observed_model_build_status": "unknown",
            "requested_model_alias": "gpt-5.6-sol",
            "requested_reasoning_effort": "high",
        },
        "artifact_type": "formal_actor_dispatch_plan",
        "artifact_version": "0.1.0",
        "capability_boundary": {
            "actual_identifiers_or_receipts_present": False,
            "actual_runtime_compliance_verified": False,
            "pre_gate_assertions_are_static_plan_only": True,
            "release_state": (
                "blocked_pending_post_b_human_authorization_and_runtime_attestation"
            ),
            "stage1_validity_enforcement_available_at_gate": False,
            "unavailable_authentication_disposition": "fail_closed",
        },
        "contract_artifacts": {
            role: artifact_reference(repo_root, path)
            for role, path in CONTRACT_ARTIFACT_PATHS.items()
        },
        "created_at": created_at,
        "isolation_policy": {
            "blank_context_required": True,
            "fork_existing_thread": False,
            "network_access_allowed": False,
            "other_conditions_or_submissions_visible": False,
            "shared_workspace_allowed": False,
            "target_type": "projectless",
            "tool_calls_allowed": False,
        },
        "plan_state": "pre_gate_template_only",
        "prompt_body_sources": {
            source_id: dict(reference)
            for source_id, reference in prompt_body_sources.items()
        },
        "post_gate_attestation_requirements": {
            "actual_actor_descriptor_required": True,
            "actual_dispatch_receipt_required": True,
            "actual_thread_and_session_ids_required": True,
            "observed_model_build_required": True,
            "platform_capability_failure_blocks_progression": True,
            "readback_sha256_required": True,
            "source_sha256_required": True,
            "stage1_response_schema_validation_required": True,
            "stage1_transcript_event_validation_required": True,
            "transcript_audit_required": True,
        },
        "response_capture_policy": {
            "attachments_allowed": False,
            "commentary_allowed": False,
            "corrective_followup_allowed": False,
            "first_and_only_assistant_event_must_be_final_json": True,
            "invalid_stage1_blocks_stage2": True,
            "second_final_allowed": False,
            "stage1_assistant_event_count_between_user_messages": 1,
            "stage2_assistant_event_count_after_user_message": 1,
            "tool_events_allowed": False,
            "valid_stage2_cannot_retroactively_invalidate_stage1": True,
            "visible_analysis_allowed": False,
        },
        "run_id": "continuous-002",
        "seats": seats,
        "session_policy": {
            "cross_seat_session_reuse_allowed": False,
            "new_session_per_seat_required": True,
            "same_session_for_stage1_and_stage2_required": True,
            "stage2_dispatch_requires_valid_stage1": True,
            "stage2_enforcement_status": (
                "blocked_until_post_gate_stage1_validator_is_authenticated"
            ),
        },
        "transport_policy": {
            "frozen_file_encoding": "utf-8",
            "post_dispatch_user_message_readback_required": True,
            "readback_capability_status_at_gate": "unknown",
            "source_to_api_unicode_equality_required": True,
            "wire_byte_identity_claimed": False,
        },
    }
    validate_schema_document(repo_root, plan)
    validate_plan_semantics(repo_root, plan, prompt_bytes=prompt_bytes)
    return plan


def expected_outputs(
    repo_root: Path,
    *,
    created_at: str,
) -> dict[str, bytes]:
    """Return all eight prompts and the plan without writing the repository."""

    source_values = {
        source_id: _read_prompt_body_source(repo_root, path)
        for source_id, path in PROMPT_BODY_PATHS.items()
    }
    rich = source_values["stage1_rich"][0]
    atomic = source_values["stage1_atomic"][0]
    stage2 = source_values["stage2"][0]
    stage1_raw = {
        "rich": build_prompt(rich, stage="stage1", condition="rich"),
        "atomic": build_prompt(atomic, stage="stage1", condition="atomic"),
    }
    stage2_raw = build_prompt(stage2, stage="stage2", condition=None)
    outputs: dict[str, bytes] = {}
    for seat in SEATS:
        outputs[_prompt_path("stage1", seat).as_posix()] = stage1_raw[
            CONDITION_BY_SEAT[seat]
        ]
        outputs[_prompt_path("stage2", seat).as_posix()] = stage2_raw
    plan = expected_plan(
        repo_root,
        created_at=created_at,
        prompt_bytes=outputs,
        prompt_body_sources={
            source_id: value[1]
            for source_id, value in source_values.items()
        },
    )
    outputs[PLAN_PATH.as_posix()] = canonical_bytes(plan)
    return outputs


def _expected_contract_references(repo_root: Path) -> dict[str, dict[str, Any]]:
    assert_runtime_artifact_binding(
        repo_root,
        "contract_core",
        Path(__file__),
    )
    return {
        role: artifact_reference(repo_root, path)
        for role, path in CONTRACT_ARTIFACT_PATHS.items()
    }


def validate_plan_semantics(
    repo_root: Path,
    plan: Mapping[str, Any],
    *,
    prompt_bytes: Mapping[str, bytes] | None = None,
) -> None:
    """Check invariants that JSON Schema cannot express across array members."""

    _created_at(plan["created_at"])
    expected_contracts = _expected_contract_references(repo_root)
    if plan["contract_artifacts"] != expected_contracts:
        raise DispatchPlanError(
            "CONTRACT_ARTIFACT_CLOSURE",
            "contract artifact path, byte length, or SHA-256 differs",
        )
    observed_sources = {
        source_id: _read_prompt_body_source(repo_root, path)
        for source_id, path in PROMPT_BODY_PATHS.items()
    }
    expected_source_references = {
        source_id: value[1]
        for source_id, value in observed_sources.items()
    }
    if plan["prompt_body_sources"] != expected_source_references:
        raise DispatchPlanError(
            "PROMPT_BODY_SOURCE_CLOSURE",
            "fixed prompt body source path, byte length, or SHA-256 differs",
        )
    seats = plan["seats"]
    conditions = [seat["condition"] for seat in seats]
    if conditions.count("rich") != 2 or conditions.count("atomic") != 2:
        raise DispatchPlanError(
            "CONDITION_BALANCE",
            "dispatch plan must contain exactly two rich and two atomic seats",
        )

    observed: dict[str, bytes] = {}
    expected_prompt_bytes = {
        "stage1_atomic": build_prompt(
            observed_sources["stage1_atomic"][0],
            stage="stage1",
            condition="atomic",
        ),
        "stage1_rich": build_prompt(
            observed_sources["stage1_rich"][0],
            stage="stage1",
            condition="rich",
        ),
        "stage2": build_prompt(
            observed_sources["stage2"][0],
            stage="stage2",
            condition=None,
        ),
    }
    for seat in seats:
        for stage in ("stage1", "stage2"):
            reference = seat[f"{stage}_prompt"]
            relative = _relative_text(reference["path"])
            if prompt_bytes is None:
                path = resolve_repo_path(repo_root, relative, require_file=True)
                raw = path.read_bytes()
            else:
                try:
                    raw = prompt_bytes[relative]
                except KeyError as error:
                    raise DispatchPlanError(
                        "PROMPT_CLOSURE",
                        f"prompt bytes are absent from materialization set: {relative}",
                    ) from error
            if len(raw) != reference["byte_length"]:
                raise DispatchPlanError(
                    "PROMPT_BYTE_LENGTH",
                    f"prompt byte length differs: {relative}",
                )
            if sha256_bytes(raw) != reference["sha256"]:
                raise DispatchPlanError(
                    "PROMPT_HASH",
                    f"prompt SHA-256 differs: {relative}",
                )
            condition = seat["condition"] if stage == "stage1" else None
            _validate_prompt_bytes(raw, stage=stage, condition=condition)
            expected_key = (
                f"stage1_{condition}" if stage == "stage1" else "stage2"
            )
            if raw != expected_prompt_bytes[expected_key]:
                raise DispatchPlanError(
                    "PROMPT_SOURCE_DERIVATION",
                    f"prompt bytes do not derive from the fixed source: {relative}",
                )
            observed[relative] = raw

    rich_stage1 = [
        observed[seat["stage1_prompt"]["path"]]
        for seat in seats
        if seat["condition"] == "rich"
    ]
    atomic_stage1 = [
        observed[seat["stage1_prompt"]["path"]]
        for seat in seats
        if seat["condition"] == "atomic"
    ]
    stage2_all = [observed[seat["stage2_prompt"]["path"]] for seat in seats]
    if len(set(rich_stage1)) != 1:
        raise DispatchPlanError(
            "RICH_STAGE1_NOT_IDENTICAL",
            "rich stage1 prompt bytes must be identical across both seats",
        )
    if len(set(atomic_stage1)) != 1:
        raise DispatchPlanError(
            "ATOMIC_STAGE1_NOT_IDENTICAL",
            "atomic stage1 prompt bytes must be identical across both seats",
        )
    if len(set(stage2_all)) != 1:
        raise DispatchPlanError(
            "STAGE2_NOT_IDENTICAL",
            "all four stage2 prompt byte strings must be identical",
        )
    if rich_stage1[0] == atomic_stage1[0]:
        raise DispatchPlanError(
            "CONDITION_PROMPTS_NOT_DISTINCT",
            "rich and atomic stage1 prompts must remain distinguishable",
        )


def verify_plan(repo_root: Path) -> tuple[dict[str, Any], bytes]:
    plan_path = resolve_repo_path(repo_root, PLAN_PATH, require_file=True)
    plan, raw = read_canonical_json(plan_path)
    validate_schema_document(repo_root, plan)
    validate_plan_semantics(repo_root, plan)
    return plan, raw


def write_outputs_exclusive(repo_root: Path, outputs: Mapping[str, bytes]) -> None:
    """Write one prevalidated output set and roll back only files created here."""

    paths: list[tuple[str, Path, bytes]] = []
    for relative, raw in outputs.items():
        path = resolve_repo_path(repo_root, relative, require_file=False)
        if path.exists():
            raise DispatchPlanError(
                "OUTPUT_EXISTS",
                f"refusing to overwrite dispatch artifact: {relative}",
            )
        paths.append((relative, path, raw))
    created: list[Path] = []
    try:
        for relative, path, raw in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                stream = path.open("xb")
            except FileExistsError as error:
                raise DispatchPlanError(
                    "OUTPUT_EXISTS",
                    f"refusing to overwrite dispatch artifact: {relative}",
                ) from error
            created.append(path)
            with stream:
                written = stream.write(raw)
                if written != len(raw):
                    raise DispatchPlanError(
                        "OUTPUT_PARTIAL_WRITE",
                        f"dispatch artifact was only partially written: {relative}",
                    )
        _, verified_raw = verify_plan(repo_root)
        if verified_raw != outputs[PLAN_PATH.as_posix()]:
            raise DispatchPlanError(
                "POST_WRITE_VERIFICATION",
                "written plan bytes differ from the prevalidated bytes",
            )
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
