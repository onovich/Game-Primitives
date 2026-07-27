#!/usr/bin/env python3
"""Materialize and verify the second, independent projection-audit task.

This tool is deliberately fail-closed. It only writes the task after every
contract-required input exists. It hashes declarative artifacts; it never
invokes a fixture, comparator, formal runner, or formal input.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA = PILOT / "schema"
TOOLS = PILOT / "tools"
EXPECTED_RUN = PILOT / "runs/continuous-001"
EXPECTED_OUTPUT = Path("inputs/projection-audit.task.json")
OUTPUT_SCHEMA_PATH = SCHEMA / "role-submission-0.1.2.schema.json"
READINESS_VERIFIER_PATH = TOOLS / "verify-formal-readiness.py"
PACKAGE_VERIFIER_PATH = TOOLS / "verify-run-package.py"
FIXTURE_ASSEMBLER_PATH = TOOLS / "materialize-fixture-assembly.py"
FINAL_PLAN_MATERIALIZER_PATH = TOOLS / "materialize-final-execution-plan.py"
TARGET_CONTRACT_PATH = TOOLS / "formal_execution_target_contract.py"
EXECUTION_PLAN_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "execution-artifact-0.1.1.schema.json"
)
FIXTURE_LOCK_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "fixture-lock-0.1.0.schema.json"
)
BUILD_READINESS_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "formal-build-readiness-0.1.0.schema.json"
)
PROTOCOL_INCIDENT_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "protocol-incident-0.1.0.schema.json"
)
PROTOCOL_INCIDENT_RUN_PATH = (
    "source/protocol-incident-r3-byte-integrity-read-v0.1.0.json"
)
TASK_SCHEMA_ID = (
    "https://github.com/onovich/Game-Primitives/blob/main/"
    "research/calibration-tests/continuous-action-pilot/schema/"
    "task-packet-0.1.2.schema.json"
)
CREATED_AT_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"
)


class ProjectionAuditTaskError(RuntimeError):
    """A deterministic projection-audit task failure."""


@dataclass(frozen=True)
class InputSpec:
    artifact_id: str
    path: str
    run_relative: bool = False


# Keep these paths exactly synchronized with REQUIRED_AUDIT_INPUTS in the
# read-only readiness verifier. The self-test checks that invariant.
INPUT_SPECS = (
    InputSpec(
        "schema.execution-artifact-v0.1.0",
        f"{SCHEMA.as_posix()}/execution-artifact-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.execution-artifact-v0.1.1",
        f"{SCHEMA.as_posix()}/execution-artifact-0.1.1.schema.json",
    ),
    InputSpec(
        "schema.fixture-assembly-fragment-v0.1.0",
        f"{SCHEMA.as_posix()}/fixture-assembly-fragment-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.fixture-lock-v0.1.0",
        f"{SCHEMA.as_posix()}/fixture-lock-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.formal-build-readiness-v0.1.0",
        f"{SCHEMA.as_posix()}/formal-build-readiness-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.role-submission-v0.1.1",
        f"{SCHEMA.as_posix()}/role-submission-0.1.1.schema.json",
    ),
    InputSpec(
        "schema.task-packet-v0.1.0",
        f"{SCHEMA.as_posix()}/task-packet-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.task-packet-v0.1.2",
        f"{SCHEMA.as_posix()}/task-packet-0.1.2.schema.json",
    ),
    InputSpec(
        "schema.variant-envelope-v0.1.0",
        f"{SCHEMA.as_posix()}/variant-envelope-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.raw-trace.ca-r1-v0.1.0",
        f"{SCHEMA.as_posix()}/ca-r1-raw-trace-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.raw-trace.ca-r2-v0.1.0",
        f"{SCHEMA.as_posix()}/ca-r2-raw-trace-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.raw-trace.ca-r3-v0.1.0",
        f"{SCHEMA.as_posix()}/ca-r3-raw-trace-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.formal-comparator-output-v0.1.0",
        f"{SCHEMA.as_posix()}/formal-comparator-output-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.formal-execution-permit-v0.1.0",
        f"{SCHEMA.as_posix()}/formal-execution-permit-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.formal-human-gate-authorization-v0.1.0",
        f"{SCHEMA.as_posix()}/formal-human-gate-authorization-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.r1-standalone-build-evidence-v0.1.0",
        f"{SCHEMA.as_posix()}/r1-standalone-build-evidence-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.r2-build-readiness-evidence-v0.1.0",
        f"{SCHEMA.as_posix()}/r2-build-readiness-evidence-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.python-runtime-evidence-v0.1.0",
        f"{SCHEMA.as_posix()}/python-runtime-evidence-0.1.0.schema.json",
    ),
    InputSpec(
        "schema.protocol-incident-v0.1.0",
        f"{SCHEMA.as_posix()}/protocol-incident-0.1.0.schema.json",
    ),
    InputSpec(
        "tool.build-role-submission-v0.1.0",
        f"{TOOLS.as_posix()}/build-role-submission.py",
    ),
    InputSpec(
        "tool.materialize-execution-permit-v0.1.0",
        f"{TOOLS.as_posix()}/materialize-execution-permit.py",
    ),
    InputSpec(
        "tool.materialize-dispatch-v0.1.0",
        f"{TOOLS.as_posix()}/materialize-dispatch.py",
    ),
    InputSpec(
        "tool.verify-formal-execution-permit-v0.1.0",
        f"{TOOLS.as_posix()}/verify-formal-execution-permit.py",
    ),
    InputSpec(
        "tool.verify-formal-raw-trace-v0.1.0",
        f"{TOOLS.as_posix()}/verify-formal-raw-trace.py",
    ),
    InputSpec(
        "tool.formal-execution-target-contract-v0.1.0",
        TARGET_CONTRACT_PATH.as_posix(),
    ),
    InputSpec(
        "tool.materialize-fixture-assembly-v0.1.0",
        FIXTURE_ASSEMBLER_PATH.as_posix(),
    ),
    InputSpec(
        "tool.materialize-final-execution-plan-v0.1.0",
        FINAL_PLAN_MATERIALIZER_PATH.as_posix(),
    ),
    InputSpec(
        "tool.materialize-python-runtime-evidence-v0.1.0",
        f"{TOOLS.as_posix()}/materialize-python-runtime-evidence.py",
    ),
    InputSpec(
        "tool.materialize-projection-audit-task-v0.1.0",
        f"{TOOLS.as_posix()}/materialize-projection-audit-task.py",
    ),
    InputSpec(
        "tool.verify-formal-readiness-v0.1.0",
        READINESS_VERIFIER_PATH.as_posix(),
    ),
    InputSpec(
        "tool.verify-run-package-v0.1.0",
        PACKAGE_VERIFIER_PATH.as_posix(),
    ),
    InputSpec(
        "execution.plan.continuous-001",
        "execution/execution-plan.json",
        run_relative=True,
    ),
    InputSpec(
        "evidence.python-runtime.continuous-001",
        "fixtures/python-runtime-evidence-v0.1.0.json",
        run_relative=True,
    ),
    InputSpec(
        "fixture.lock-v0.1.0",
        "fixtures/fixture-lock.json",
        run_relative=True,
    ),
    InputSpec(
        "build.formal-readiness-v0.1.0",
        "fixtures/formal-build-readiness-v0.1.0.json",
        run_relative=True,
    ),
    InputSpec(
        "fixture.assembly-fragment.ca-r1-v0.1.0",
        "fixtures/r1/r1-fixture-assembly-fragment-v0.1.0.json",
        run_relative=True,
    ),
    InputSpec(
        "fixture.assembly-fragment.ca-r2-v0.1.0",
        "fixtures/r2/r2-fixture-assembly-fragment-v0.1.0.json",
        run_relative=True,
    ),
    InputSpec(
        "fixture.assembly-fragment.ca-r3-v0.1.0",
        "fixtures/r3/r3-fixture-assembly-fragment-v0.1.0.json",
        run_relative=True,
    ),
    InputSpec(
        "actor-plan.continuous-001",
        "inputs/actor-plan.md",
        run_relative=True,
    ),
    InputSpec(
        "projection.generator-v0.1.0",
        "inputs/generate-continuous-views-v0.1.0.py",
        run_relative=True,
    ),
    InputSpec(
        "generator.stage2-envelope-v0.1.0",
        "inputs/generate-stage2-envelope-v0.1.0.py",
        run_relative=True,
    ),
    InputSpec(
        "generator.stage2-task-v0.1.0",
        "inputs/generate-stage2-prediction-task-v0.1.0.py",
        run_relative=True,
    ),
    InputSpec(
        "template.prediction-response-v0.1.0",
        "inputs/prediction-response.template.json",
        run_relative=True,
    ),
    InputSpec(
        "projection.spec-v0.1.0",
        "inputs/projection-spec.json",
        run_relative=True,
    ),
    InputSpec(
        "template.reconstruction-response-v0.1.0",
        "inputs/reconstruction-response.template.json",
        run_relative=True,
    ),
    InputSpec(
        "dispatch-template.stage1.p01",
        "inputs/stage1-dispatch-p01.template.json",
        run_relative=True,
    ),
    InputSpec(
        "dispatch-template.stage1.p02",
        "inputs/stage1-dispatch-p02.template.json",
        run_relative=True,
    ),
    InputSpec(
        "dispatch-template.stage1.p03",
        "inputs/stage1-dispatch-p03.template.json",
        run_relative=True,
    ),
    InputSpec(
        "dispatch-template.stage1.p04",
        "inputs/stage1-dispatch-p04.template.json",
        run_relative=True,
    ),
    InputSpec(
        "task.reconstruction.condition-v01",
        "inputs/stage1-condition-v01.task.json",
        run_relative=True,
    ),
    InputSpec(
        "task.reconstruction.condition-v02",
        "inputs/stage1-condition-v02.task.json",
        run_relative=True,
    ),
    InputSpec(
        "view.stage1-condition-v01-v0.1.0",
        "inputs/stage1-view-v01.json",
        run_relative=True,
    ),
    InputSpec(
        "view.stage1-condition-v02-v0.1.0",
        "inputs/stage1-view-v02.json",
        run_relative=True,
    ),
    InputSpec(
        "dispatch-template.stage2.p01",
        "inputs/stage2-dispatch-p01.template.json",
        run_relative=True,
    ),
    InputSpec(
        "dispatch-template.stage2.p02",
        "inputs/stage2-dispatch-p02.template.json",
        run_relative=True,
    ),
    InputSpec(
        "dispatch-template.stage2.p03",
        "inputs/stage2-dispatch-p03.template.json",
        run_relative=True,
    ),
    InputSpec(
        "dispatch-template.stage2.p04",
        "inputs/stage2-dispatch-p04.template.json",
        run_relative=True,
    ),
    InputSpec(
        "task.prediction.continuous-001",
        "inputs/stage2-prediction.task.json",
        run_relative=True,
    ),
    InputSpec(
        "envelope.variant.stage2-v0.1.0",
        "inputs/stage2-variant-envelope.json",
        run_relative=True,
    ),
    InputSpec(
        "source.canonical-encoding-v0.1.0",
        "source/canonical-encoding-v0.1.0.json",
        run_relative=True,
    ),
    InputSpec(
        "audit.protocol-incident.r3-byte-integrity-read-v0.1.0",
        PROTOCOL_INCIDENT_RUN_PATH,
        run_relative=True,
    ),
)

REQUIRED_AUDIT_CHECKS = (
    "answer_hint_scan",
    "atomic_projection_equivalence",
    "dispatch_symmetry",
    "formal_build_readiness_integrity",
    "identity_leak_scan",
    "invariant_integrity",
    "projection_fidelity",
    "protocol_incident_disposition",
    "reference_closure",
    "single_variable_isolation",
    "stage2_input_closure",
)

INSTRUCTIONS = (
    (
        "只使用本任务 input_artifacts 明列并绑定散列的制品；不得搜索外部资料、"
        "读取共享工作区的其他文件、访问其他提交或提交结果、真值、预测与正式结果。"
    ),
    (
        "开始实质审核前，逐项复算 input_artifacts 的 SHA-256；任一路径缺失、越界、"
        "散列不符或引用不闭合，都必须停止审核并将 audit_decision 记为 blocked。"
    ),
    (
        "独立核对规范编码、机械投影生成器、投影规范与两份中性视图，确认 rich 与 "
        "atomic 投影忠实表达同一编码，且 atomic 的删边仅来自明列投影规则。"
    ),
    (
        "逐案核对 controlled_variable_id 的唯一职责、基线／变体隔离、不变量、"
        "正式输入接口、停止边界、时间基准、初态字段及观察量引用闭包；不得运行正式输入。"
    ),
    (
        "核对第二阶段中性信封、预测任务、两类回答模板以及八份派发模板的输入闭包"
        "与派发对称性；不得把来源专用夹具或作品身份加入盲测派发。"
    ),
    (
        "formal_build_readiness_integrity 只审核最终构建准备记录、夹具锁与执行计划的"
        "声明、散列和引用；不得启动夹具、构建器、正式 runner、轨迹校验器或比较器。"
    ),
    (
        "protocol_incident_disposition 必须审核绑定的 CA-R3 字节完整性读取事件："
        "区分字节读取与语义解释，拒绝任何轮次级 formal_input_read=false 声明，"
        "并确认该例外仍须在人工门获得显式接受。"
    ),
    (
        "identity_leak_scan 与 answer_hint_scan 必须覆盖任务、视图、信封、模板及派发"
        "边界；作品名、来源函数名、rich／atomic 身份或控制条件答案均不得泄漏给参与者。"
    ),
    (
        "每个 required_audit_checks 项必须生成一个同名 check_id 的 audit_checks 记录；"
        "记录精确目标 artifact_id、定位、发现、严重性与所需修改，不能以总评替代逐项审核。"
    ),
    (
        "任一检查未通过、材料不足或无法独立复核时，audit_decision 必须为 "
        "revision_required 或 blocked；只有十一项检查全部 passed 才可记为 approved。"
    ),
    (
        "输出 artifact_type=source_fidelity_audit、artifact_version=0.1.2、"
        "stage=source_audit 的 role submission；actor.role 必须为 source_auditor，"
        "packaging、pollution、prior_stage_submission_sha256 与 raw_payload 为 null，"
        "prediction_answers 与 reconstruction_answers 为空数组。"
    ),
    (
        "输出只包含一个通过声明 Schema 的 JSON 对象，使用 UTF-8 无 BOM、LF、"
        "两空格缩进、递归键排序和单一末尾换行；本任务本身不构成审核结论或放行。"
    ),
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProjectionAuditTaskError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_nonfinite(value: str) -> None:
    raise ProjectionAuditTaskError(f"non-finite JSON number: {value}")


def resolve_within(root: Path, relative: Path | str) -> Path:
    root = root.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ProjectionAuditTaskError(
            f"path escapes repository root: {relative}"
        )
    return candidate


def strict_json_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ProjectionAuditTaskError(f"UTF-8 BOM is forbidden: {path}")
    if b"\r\n" in raw or b"\r" in raw:
        raise ProjectionAuditTaskError(f"CRLF/CR is forbidden: {path}")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ProjectionAuditTaskError,
    ) as exc:
        raise ProjectionAuditTaskError(f"invalid UTF-8 JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ProjectionAuditTaskError(f"expected JSON object: {path}")
    if raw != canonical_bytes(value):
        raise ProjectionAuditTaskError(f"non-canonical JSON bytes: {path}")
    return value


def strict_schema_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ProjectionAuditTaskError(f"UTF-8 BOM is forbidden: {path}")
    if b"\r\n" in raw or b"\r" in raw:
        raise ProjectionAuditTaskError(f"CRLF/CR is forbidden: {path}")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ProjectionAuditTaskError,
    ) as exc:
        raise ProjectionAuditTaskError(
            f"invalid UTF-8 schema JSON: {path}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ProjectionAuditTaskError(f"expected schema JSON object: {path}")
    return value


def normalized_roots(
    repo_root: Path, run_dir: Path
) -> tuple[Path, Path, str]:
    repo_root = repo_root.resolve()
    if run_dir.is_absolute():
        run_dir = run_dir.resolve()
    else:
        run_dir = (repo_root / run_dir).resolve()
    if not run_dir.is_relative_to(repo_root):
        raise ProjectionAuditTaskError("run directory escapes repository root")
    run_relative = run_dir.relative_to(repo_root)
    if run_relative != EXPECTED_RUN:
        raise ProjectionAuditTaskError(
            f"expected run directory {EXPECTED_RUN.as_posix()}, "
            f"got {run_relative.as_posix()}"
        )
    return repo_root, run_dir, run_relative.as_posix()


def task_reference_path(spec: InputSpec, run_prefix: str) -> str:
    if spec.run_relative:
        return f"{run_prefix}/{spec.path}"
    return spec.path


def filesystem_path(
    repo_root: Path, run_dir: Path, spec: InputSpec
) -> Path:
    if spec.run_relative:
        path = (run_dir / spec.path).resolve()
        if not path.is_relative_to(repo_root):
            raise ProjectionAuditTaskError(
                f"input path escapes repository root: {spec.path}"
            )
        return path
    return resolve_within(repo_root, spec.path)


def readiness_required_paths(repo_root: Path) -> set[str]:
    verifier = resolve_within(repo_root, READINESS_VERIFIER_PATH)
    if not verifier.is_file():
        raise ProjectionAuditTaskError(
            f"missing readiness verifier: {READINESS_VERIFIER_PATH.as_posix()}"
        )
    module = ast.parse(
        verifier.read_text(encoding="utf-8"), filename=str(verifier)
    )
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name)
            and target.id == "REQUIRED_AUDIT_INPUTS"
            for target in node.targets
        ):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, set) or not all(
            isinstance(item, str) for item in value
        ):
            break
        return value
    raise ProjectionAuditTaskError(
        "cannot read REQUIRED_AUDIT_INPUTS from readiness verifier"
    )


def assert_readiness_sync(repo_root: Path) -> None:
    artifact_ids = [spec.artifact_id for spec in INPUT_SPECS]
    paths = [spec.path for spec in INPUT_SPECS]
    if len(artifact_ids) != len(set(artifact_ids)):
        duplicates = sorted(
            value for value in set(artifact_ids) if artifact_ids.count(value) > 1
        )
        raise ProjectionAuditTaskError(
            f"duplicate projection-audit artifact_id(s): {duplicates}"
        )
    if len(paths) != len(set(paths)):
        duplicates = sorted(
            value for value in set(paths) if paths.count(value) > 1
        )
        raise ProjectionAuditTaskError(
            f"duplicate projection-audit input path(s): {duplicates}"
        )
    local_paths = {spec.path for spec in INPUT_SPECS}
    readiness_paths = readiness_required_paths(repo_root)
    if local_paths != readiness_paths:
        missing = sorted(readiness_paths - local_paths)
        extra = sorted(local_paths - readiness_paths)
        raise ProjectionAuditTaskError(
            "projection-audit materializer/readiness input drift: "
            f"missing={missing}, extra={extra}"
        )


def external_schema_ref_bases(value: Any) -> set[str]:
    bases: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref" and isinstance(child, str):
                base = child.split("#", 1)[0]
                if base:
                    bases.add(base)
            else:
                bases.update(external_schema_ref_bases(child))
    elif isinstance(value, list):
        for child in value:
            bases.update(external_schema_ref_bases(child))
    return bases


def assert_audit_schema_dependency_closure(
    repo_root: Path,
    *,
    input_specs: tuple[InputSpec, ...] = INPUT_SPECS,
) -> None:
    authorized_paths = {
        spec.path
        for spec in input_specs
        if spec.path.endswith(".schema.json") and not spec.run_relative
    }
    authorized_paths.add(OUTPUT_SCHEMA_PATH.as_posix())

    schema_dir = resolve_within(repo_root, SCHEMA)
    schemas_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
    for path in sorted(schema_dir.glob("*.schema.json")):
        schema = strict_schema_object(path)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ProjectionAuditTaskError(f"schema has no $id: {path}")
        relative = path.relative_to(repo_root).as_posix()
        schemas_by_id[schema_id] = (relative, schema)

    pending = list(sorted(authorized_paths))
    visited: set[str] = set()
    gaps: set[str] = set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        visited.add(relative)
        path = resolve_within(repo_root, relative)
        if not path.is_file():
            gaps.add(f"missing authorized schema {relative}")
            continue
        schema = strict_schema_object(path)
        for ref_base in sorted(external_schema_ref_bases(schema)):
            target = schemas_by_id.get(ref_base)
            if target is None:
                gaps.add(f"unresolved external $ref {ref_base}")
                continue
            target_relative, _ = target
            if target_relative not in authorized_paths:
                gaps.add(
                    f"unbound schema dependency {target_relative} "
                    f"referenced by {relative}"
                )
                continue
            pending.append(target_relative)

    if gaps:
        raise ProjectionAuditTaskError(
            "projection-audit schema dependency closure incomplete: "
            + "; ".join(sorted(gaps))
        )


def load_schema_registry(
    schema_repo_root: Path,
) -> tuple[Registry, dict[str, dict[str, Any]]]:
    schema_dir = resolve_within(schema_repo_root, SCHEMA)
    registry = Registry()
    by_id: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir.glob("*.schema.json")):
        try:
            schema = strict_schema_object(path)
        except ProjectionAuditTaskError as exc:
            raise ProjectionAuditTaskError(
                f"cannot load local schema: {path}: {exc}"
            ) from exc
        if not isinstance(schema, dict) or not isinstance(
            schema.get("$id"), str
        ):
            raise ProjectionAuditTaskError(f"schema has no $id: {path}")
        Draft202012Validator.check_schema(schema)
        schema_id = schema["$id"]
        if schema_id in by_id:
            raise ProjectionAuditTaskError(f"duplicate schema $id: {schema_id}")
        by_id[schema_id] = schema
        registry = registry.with_resource(
            schema_id, Resource.from_contents(schema)
        )
    return registry, by_id


def validate_document_schema(
    document: dict[str, Any],
    schema_id: str,
    schema_repo_root: Path,
    *,
    label: str,
) -> None:
    registry, schemas = load_schema_registry(schema_repo_root)
    schema = schemas.get(schema_id)
    if schema is None:
        raise ProjectionAuditTaskError(
            f"{label} schema is not locally registered: {schema_id}"
        )
    errors = sorted(
        Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        ).iter_errors(document),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        rendered = "; ".join(
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: "
            f"{error.message}"
            for error in errors[:5]
        )
        raise ProjectionAuditTaskError(
            f"{label} schema validation failed: {rendered}"
        )


def validate_task_schema(
    task: dict[str, Any], schema_repo_root: Path
) -> None:
    validate_document_schema(
        task,
        TASK_SCHEMA_ID,
        schema_repo_root,
        label="projection-audit task",
    )


def validate_protocol_incident(
    incident: dict[str, Any], schema_repo_root: Path
) -> None:
    validate_document_schema(
        incident,
        PROTOCOL_INCIDENT_SCHEMA_ID,
        schema_repo_root,
        label="protocol incident",
    )
    if "formal_input_read" in incident.get("aggregate_state", {}):
        raise ProjectionAuditTaskError(
            "protocol incident must not make an ambiguous aggregate "
            "formal_input_read assertion"
        )


def load_fixture_assembly_module() -> Any:
    module_path = Path(__file__).resolve().with_name(
        FIXTURE_ASSEMBLER_PATH.name
    )
    module_name = "_game_primitives_fixture_assembly_for_projection_audit"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ProjectionAuditTaskError(
            f"cannot load fixture assembler: {module_path}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def load_final_plan_module() -> Any:
    module_path = Path(__file__).resolve().with_name(
        FINAL_PLAN_MATERIALIZER_PATH.name
    )
    module_name = "_game_primitives_final_plan_for_projection_audit"
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ProjectionAuditTaskError(
            f"cannot load final-plan materializer: {module_path}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def verify_fixture_assembly(repo_root: Path) -> dict[str, Any]:
    module = load_fixture_assembly_module()
    try:
        result = module.verify(repo_root)
    except Exception as exc:
        raise ProjectionAuditTaskError(
            f"fixture assembly verification failed: {exc}"
        ) from exc
    if (
        not isinstance(result, dict)
        or result.get("status") != "verified"
        or result.get("formal_input_executed") is not False
        or result.get("formal_result_produced") is not False
    ):
        raise ProjectionAuditTaskError(
            "fixture assembly verifier did not return a no-execution verified result"
        )
    return result


def verify_final_plan_materialization(repo_root: Path) -> dict[str, Any]:
    module = load_final_plan_module()
    try:
        result = module.verify(repo_root)
    except Exception as exc:
        raise ProjectionAuditTaskError(
            f"final execution-plan verification failed: {exc}"
        ) from exc
    if (
        not isinstance(result, dict)
        or result.get("status") != "verified"
        or result.get("formal_input_executed") is not False
        or result.get("formal_result_produced") is not False
    ):
        raise ProjectionAuditTaskError(
            "final-plan materializer did not return a no-execution verified result"
        )
    return result


def reference_key(reference: dict[str, Any]) -> tuple[str, str, str]:
    return (
        reference.get("artifact_id"),
        reference.get("path"),
        reference.get("sha256"),
    )


def validate_final_execution_plan(
    *,
    plan: dict[str, Any],
    fixture_lock: dict[str, Any],
    fixture_lock_sha256: str,
    repo_root: Path,
    run_prefix: str,
) -> None:
    validate_document_schema(
        plan,
        EXECUTION_PLAN_SCHEMA_ID,
        repo_root,
        label="final execution plan",
    )
    expected_fixture_reference = {
        "artifact_id": "fixture.lock-v0.1.0",
        "path": f"{run_prefix}/fixtures/fixture-lock.json",
        "sha256": fixture_lock_sha256,
    }
    if plan.get("fixture_lock") != expected_fixture_reference:
        raise ProjectionAuditTaskError(
            "final execution plan does not exactly bind the fixture lock"
        )

    plan_cases = plan.get("cases", [])
    plan_case_ids = [
        case.get("case_id") for case in plan_cases if isinstance(case, dict)
    ]
    expected_case_ids = ["CA-R1", "CA-R2", "CA-R3", "NEG-01"]
    if (
        len(plan_case_ids) != len(expected_case_ids)
        or set(plan_case_ids) != set(expected_case_ids)
    ):
        raise ProjectionAuditTaskError(
            "final execution plan does not contain exactly CA-R1, CA-R2, "
            "CA-R3, and NEG-01"
        )
    lock_by_case = {
        case["case_id"]: case for case in fixture_lock.get("cases", [])
    }
    if set(lock_by_case) != {"CA-R1", "CA-R2", "CA-R3"}:
        raise ProjectionAuditTaskError(
            "fixture lock does not contain exactly the three formal cases"
        )
    plan_by_case = {case["case_id"]: case for case in plan_cases}

    for case_id in ("CA-R1", "CA-R2", "CA-R3"):
        case_plan = plan_by_case[case_id]
        case_lock = lock_by_case[case_id]
        if case_plan.get("negative_control") is not False:
            raise ProjectionAuditTaskError(
                f"{case_id} is not marked as a formal plan case"
            )
        if (
            case_plan.get("source_commit")
            != case_lock["source_identity"]["commit_sha"]
        ):
            raise ProjectionAuditTaskError(
                f"{case_id} plan source commit differs from fixture lock"
            )
        formal_inputs = case_lock.get("formal_input_artifacts", [])
        if (
            len(formal_inputs) != 1
            or case_plan.get("formal_input") != formal_inputs[0]
        ):
            raise ProjectionAuditTaskError(
                f"{case_id} plan formal input differs from fixture lock"
            )
        if (
            case_plan.get("stop_boundary_id")
            != case_lock.get("stop_boundary_id")
        ):
            raise ProjectionAuditTaskError(
                f"{case_id} plan stop boundary differs from fixture lock"
            )
        plan_invariants = {
            invariant.get("invariant_id")
            for invariant in case_plan.get("invariants", [])
        }
        if plan_invariants != set(case_lock.get("invariant_ids", [])):
            raise ProjectionAuditTaskError(
                f"{case_id} plan invariants differ from fixture lock"
            )

        configurations = case_plan.get("configurations", [])
        configuration_pairs = {
            (
                configuration.get("configuration_id"),
                configuration.get("semantic_role"),
            )
            for configuration in configurations
        }
        if configuration_pairs != {
            ("config.baseline", "baseline"),
            ("config.variant", "variant"),
        }:
            raise ProjectionAuditTaskError(
                f"{case_id} plan configurations are not exact baseline/variant"
            )

        locked_execution_surface = {
            reference_key(reference)
            for reference in case_lock.get("fixture_artifacts", [])
        }
        for patch_set_name in (
            "compatibility_patch_set",
            "observation_patch_set",
            "variant_patch_set",
        ):
            patch_set = case_lock.get(patch_set_name, {})
            locked_execution_surface.update(
                reference_key(reference)
                for reference in (
                    patch_set.get("artifacts", [])
                    + patch_set.get("configuration_artifacts", [])
                )
            )
        planned_execution_surface = {
            reference_key(reference)
            for configuration in configurations
            for reference in configuration.get("fixture_artifacts", [])
        }
        if planned_execution_surface != locked_execution_surface:
            raise ProjectionAuditTaskError(
                f"{case_id} plan execution surface differs from fixture lock"
            )

        locked_comparators = {
            reference_key(reference)
            for reference in case_lock.get("comparator_artifacts", [])
        }
        planned_comparators = {
            reference_key(comparator.get("implementation", {}))
            for comparator in case_plan.get("comparators", [])
        }
        if planned_comparators != locked_comparators:
            raise ProjectionAuditTaskError(
                f"{case_id} plan comparators differ from fixture lock"
            )
        planned_tolerances = {
            tolerance.get("tolerance_rule_id")
            for comparator in case_plan.get("comparators", [])
            for tolerance in comparator.get("tolerance_rules", [])
        }
        if planned_tolerances != set(
            case_lock.get("tolerance_rule_ids", [])
        ):
            raise ProjectionAuditTaskError(
                f"{case_id} plan tolerances differ from fixture lock"
            )

    negative = plan_by_case["NEG-01"]
    r3 = plan_by_case["CA-R3"]
    if negative.get("negative_control") is not True:
        raise ProjectionAuditTaskError("NEG-01 is not a negative control")
    negative_pairs = {
        (
            configuration.get("configuration_id"),
            configuration.get("semantic_role"),
        )
        for configuration in negative.get("configurations", [])
    }
    if negative_pairs != {
        ("config.negative-a", "negative_control_a"),
        ("config.negative-b", "negative_control_b"),
    }:
        raise ProjectionAuditTaskError(
            "NEG-01 configurations are not the exact negative-control pair"
        )
    for field_name in (
        "formal_input",
        "source_commit",
        "stop_boundary_id",
        "time_base_ids",
    ):
        if negative.get(field_name) != r3.get(field_name):
            raise ProjectionAuditTaskError(
                f"NEG-01 {field_name} differs from CA-R3"
            )
    if {
        invariant.get("invariant_id")
        for invariant in negative.get("invariants", [])
    } != {
        invariant.get("invariant_id")
        for invariant in r3.get("invariants", [])
    }:
        raise ProjectionAuditTaskError(
            "NEG-01 invariants differ from CA-R3"
        )


def build_task(
    repo_root: Path,
    run_dir: Path,
    created_at: str,
    *,
    enforce_readiness_sync: bool = True,
) -> dict[str, Any]:
    repo_root, run_dir, run_prefix = normalized_roots(repo_root, run_dir)
    if not CREATED_AT_PATTERN.fullmatch(created_at):
        raise ProjectionAuditTaskError(
            "created_at must be canonical UTC seconds: YYYY-MM-DDTHH:MM:SSZ"
        )
    if enforce_readiness_sync:
        assert_readiness_sync(repo_root)
    assert_audit_schema_dependency_closure(repo_root)

    missing: list[str] = []
    references: list[dict[str, str]] = []
    for spec in INPUT_SPECS:
        path = filesystem_path(repo_root, run_dir, spec)
        if not path.is_file():
            missing.append(task_reference_path(spec, run_prefix))
            continue
        references.append(
            {
                "artifact_id": spec.artifact_id,
                "path": task_reference_path(spec, run_prefix),
                "sha256": sha256(path),
            }
        )

    output_schema = resolve_within(repo_root, OUTPUT_SCHEMA_PATH)
    if not output_schema.is_file():
        missing.append(OUTPUT_SCHEMA_PATH.as_posix())
    if missing:
        raise ProjectionAuditTaskError(
            "missing prerequisite(s); task was not materialized: "
            + ", ".join(sorted(missing))
        )

    assembly_result = verify_fixture_assembly(repo_root)

    fixture_lock_path = run_dir / "fixtures/fixture-lock.json"
    fixture_lock = strict_json_object(fixture_lock_path)
    validate_document_schema(
        fixture_lock,
        FIXTURE_LOCK_SCHEMA_ID,
        repo_root,
        label="fixture lock",
    )
    if (
        fixture_lock.get("artifact_type") != "fixture_lock"
        or fixture_lock.get("artifact_version") != "0.1.0"
        or fixture_lock.get("fixture_state") != "locked"
        or fixture_lock.get("formal_execution_authorized") is not False
        or fixture_lock.get("formal_input_executed") is not False
        or fixture_lock.get("run_id") != "continuous-001"
    ):
        raise ProjectionAuditTaskError(
            "fixture lock is not a locked, pre-authorization continuous-001 artifact"
        )

    build_readiness_path = (
        run_dir / "fixtures/formal-build-readiness-v0.1.0.json"
    )
    build_readiness = strict_json_object(build_readiness_path)
    validate_document_schema(
        build_readiness,
        BUILD_READINESS_SCHEMA_ID,
        repo_root,
        label="formal build readiness",
    )
    if (
        build_readiness.get("artifact_type") != "formal_build_readiness"
        or build_readiness.get("artifact_version") != "0.1.0"
        or build_readiness.get("overall_status") != "passed"
        or build_readiness.get("readiness_scope") != "build_only"
        or build_readiness.get("formal_input_executed") is not False
        or build_readiness.get("formal_result_produced") is not False
        or build_readiness.get("run_id") != "continuous-001"
    ):
        raise ProjectionAuditTaskError(
            "formal build readiness is not a passed build-only, no-execution artifact"
        )
    if (
        assembly_result.get("fixture_lock_sha256")
        != sha256(fixture_lock_path)
        or assembly_result.get("formal_build_readiness_sha256")
        != sha256(build_readiness_path)
    ):
        raise ProjectionAuditTaskError(
            "fixture assembly verifier hashes differ from final artifacts"
        )

    incident_path = run_dir / PROTOCOL_INCIDENT_RUN_PATH
    incident = strict_json_object(incident_path)
    validate_protocol_incident(incident, repo_root)

    execution_plan_path = run_dir / "execution/execution-plan.json"
    execution_plan = strict_json_object(execution_plan_path)
    if (
        execution_plan.get("$schema") != EXECUTION_PLAN_SCHEMA_ID
        or execution_plan.get("artifact_type") != "execution_plan"
        or execution_plan.get("artifact_version") != "0.1.1"
        or execution_plan.get("run_id") != "continuous-001"
    ):
        raise ProjectionAuditTaskError(
            "execution plan is not the final continuous-001 0.1.1 plan"
        )
    validate_final_execution_plan(
        plan=execution_plan,
        fixture_lock=fixture_lock,
        fixture_lock_sha256=sha256(fixture_lock_path),
        repo_root=repo_root,
        run_prefix=run_prefix,
    )
    final_plan_result = verify_final_plan_materialization(repo_root)
    if final_plan_result.get("sha256") != sha256(execution_plan_path):
        raise ProjectionAuditTaskError(
            "final-plan materializer hash differs from execution plan"
        )

    canonical_encoding = next(
        reference
        for reference in references
        if reference["artifact_id"] == "source.canonical-encoding-v0.1.0"
    )
    return {
        "$schema": TASK_SCHEMA_ID,
        "allowed_configurations": [],
        "allowed_observations": [],
        "artifact_type": "projection_audit_task_packet",
        "artifact_version": "0.1.2",
        "assembled_output_schema": None,
        "behavior_scope": "structural_only",
        "case_ids": ["CA-R1", "CA-R2", "CA-R3"],
        "condition_id": None,
        "created_at": created_at,
        "forbidden_actions": [
            "access_other_submission",
            "access_package_outside_dispatch",
            "access_truth_or_result",
            "create_child_task",
            "external_search",
            "read_shared_workspace",
        ],
        "input_artifacts": references,
        "instructions": list(INSTRUCTIONS),
        "output_schema": {
            "path": OUTPUT_SCHEMA_PATH.as_posix(),
            "sha256": sha256(output_schema),
        },
        "representation_version": "CA-SR 0.1",
        "required_audit_checks": list(REQUIRED_AUDIT_CHECKS),
        "run_id": "continuous-001",
        "stage1_submission_required": False,
        "stop_boundary_refs": [
            "stop.r1.update-6",
            "stop.r2.200-ms",
            "stop.r3.result-committed",
        ],
        "target_encoding_sha256": canonical_encoding["sha256"],
        "target_view_sha256": None,
        "task_id": "task.projection-audit.continuous-001",
        "tolerance_rule_refs": [],
        "variant_interventions": [],
    }


def expected_output_path(repo_root: Path, run_dir: Path) -> Path:
    repo_root = repo_root.resolve()
    run_dir = run_dir.resolve()
    output = (run_dir / EXPECTED_OUTPUT).resolve()
    if (
        not output.is_relative_to(repo_root)
        or not output.is_relative_to(run_dir)
    ):
        raise ProjectionAuditTaskError(
            "projection-audit output path escapes the repository or run directory"
        )
    unresolved_output = run_dir / EXPECTED_OUTPUT
    if unresolved_output.is_symlink():
        raise ProjectionAuditTaskError(
            "projection-audit output path must not be a symbolic link"
        )
    return output


def materialize(
    repo_root: Path, run_dir: Path, created_at: str
) -> dict[str, Any]:
    repo_root, run_dir, _ = normalized_roots(repo_root, run_dir)
    task = build_task(repo_root, run_dir, created_at)
    validate_task_schema(task, repo_root)
    output = expected_output_path(repo_root, run_dir)
    payload = canonical_bytes(task)
    if output.exists():
        existing = output.read_bytes()
        if existing != payload:
            raise ProjectionAuditTaskError(
                "refusing to overwrite a different projection-audit task"
            )
        changed = False
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(f".{output.name}.tmp")
        if temporary.exists():
            raise ProjectionAuditTaskError(
                f"refusing to reuse stale temporary path: {temporary}"
            )
        temporary.write_bytes(payload)
        temporary.replace(output)
        changed = True
    return {
        "changed": changed,
        "formal_input_executed": False,
        "formal_result_created": False,
        "input_artifact_count": len(task["input_artifacts"]),
        "status": "materialized",
        "task_path": output.relative_to(repo_root).as_posix(),
        "task_sha256": hashlib.sha256(payload).hexdigest(),
    }


def verify_task(
    repo_root: Path,
    run_dir: Path,
    *,
    schema_repo_root: Path | None = None,
    enforce_readiness_sync: bool = True,
) -> dict[str, Any]:
    repo_root, run_dir, _ = normalized_roots(repo_root, run_dir)
    task_path = expected_output_path(repo_root, run_dir)
    if not task_path.is_file():
        raise ProjectionAuditTaskError(
            f"projection-audit task does not exist: "
            f"{task_path.relative_to(repo_root).as_posix()}"
        )
    task = strict_json_object(task_path)
    created_at = task.get("created_at")
    if not isinstance(created_at, str):
        raise ProjectionAuditTaskError("task created_at is missing")
    expected = build_task(
        repo_root,
        run_dir,
        created_at,
        enforce_readiness_sync=enforce_readiness_sync,
    )
    if task != expected:
        raise ProjectionAuditTaskError(
            "task payload is stale or differs from deterministic materialization"
        )
    validate_task_schema(task, schema_repo_root or repo_root)
    return {
        "formal_input_executed": False,
        "formal_result_created": False,
        "input_artifact_count": len(task["input_artifacts"]),
        "status": "passed",
        "task_path": task_path.relative_to(repo_root).as_posix(),
        "task_sha256": sha256(task_path),
    }


def populate_synthetic_repo(root: Path, actual_repo_root: Path) -> Path:
    run_dir = root / EXPECTED_RUN
    actual_schema_dir = resolve_within(actual_repo_root, SCHEMA)
    synthetic_schema_dir = resolve_within(root, SCHEMA)
    synthetic_schema_dir.mkdir(parents=True, exist_ok=True)
    for source in actual_schema_dir.glob("*.schema.json"):
        shutil.copy2(source, synthetic_schema_dir / source.name)

    for spec in INPUT_SPECS:
        if spec.run_relative:
            continue
        source = filesystem_path(actual_repo_root, actual_repo_root / EXPECTED_RUN, spec)
        destination = filesystem_path(root, run_dir, spec)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    assembler = load_fixture_assembly_module()
    probe_path = root / assembler.SUPERSEDES_PATH
    probe_path.parent.mkdir(parents=True, exist_ok=True)
    probe_path.write_bytes(b'{"synthetic_probe":true}\n')
    prepared_times = {
        "CA-R1": "2026-07-27T00:00:01Z",
        "CA-R2": "2026-07-27T00:00:02Z",
        "CA-R3": "2026-07-27T00:00:03Z",
    }
    for case_id in ("CA-R1", "CA-R2", "CA-R3"):
        fragment = assembler.synthetic_fragment(
            root,
            case_id,
            prepared_at=prepared_times[case_id],
        )
        fragment_path = root / assembler.FRAGMENT_PATHS[case_id]
        fragment_path.parent.mkdir(parents=True, exist_ok=True)
        fragment_path.write_bytes(assembler.canonical_bytes(fragment))
    assembler.materialize(root)

    fixture_lock_path = run_dir / "fixtures/fixture-lock.json"
    fixture_lock = strict_json_object(fixture_lock_path)
    lock_by_case = {
        case["case_id"]: case for case in fixture_lock["cases"]
    }
    envelope_source = (
        actual_repo_root
        / EXPECTED_RUN
        / "inputs/stage2-variant-envelope.json"
    )
    task_source = (
        actual_repo_root
        / EXPECTED_RUN
        / "inputs/stage2-prediction.task.json"
    )
    envelope = strict_json_object(envelope_source)
    for intervention in envelope["case_interventions"]:
        case_lock = lock_by_case[intervention["case_id"]]
        intervention["invariant_ids"] = copy.deepcopy(
            case_lock["invariant_ids"]
        )
        intervention["invariant_specs"] = [
            {
                "description": (
                    f"Synthetic no-execution invariant for "
                    f"{intervention['case_id']}."
                ),
                "invariant_id": invariant_id,
            }
            for invariant_id in case_lock["invariant_ids"]
        ]
        intervention["stop_boundary_id"] = case_lock["stop_boundary_id"]
        intervention["stop_boundary_spec"]["stop_boundary_id"] = (
            case_lock["stop_boundary_id"]
        )
        intervention["tolerance_rule_ids"] = copy.deepcopy(
            case_lock["tolerance_rule_ids"]
        )
        intervention["tolerance_specs"] = [
            {
                "comparison_kind": "exact",
                "threshold": None,
                "tolerance_rule_id": tolerance_id,
            }
            for tolerance_id in case_lock["tolerance_rule_ids"]
        ]
    envelope_path = run_dir / "inputs/stage2-variant-envelope.json"
    envelope_path.parent.mkdir(parents=True, exist_ok=True)
    envelope_path.write_bytes(canonical_bytes(envelope))
    prediction_task_path = run_dir / "inputs/stage2-prediction.task.json"
    prediction_task = strict_json_object(task_source)
    tolerance_by_observation = {
        observation_id: intervention["tolerance_rule_ids"][0]
        for intervention in envelope["case_interventions"]
        for observation_id in intervention["observation_ids"]
    }
    for observation in prediction_task["allowed_observations"]:
        observation["tolerance_rule_id"] = tolerance_by_observation[
            observation["observation_id"]
        ]
    prediction_task_path.write_bytes(canonical_bytes(prediction_task))

    incident_source = (
        actual_repo_root / EXPECTED_RUN / PROTOCOL_INCIDENT_RUN_PATH
    )
    incident_destination = run_dir / PROTOCOL_INCIDENT_RUN_PATH
    incident_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(incident_source, incident_destination)

    execution_plan_relative = "execution/execution-plan.json"
    for index, spec in enumerate(INPUT_SPECS, start=1):
        if not spec.run_relative or spec.path == execution_plan_relative:
            continue
        path = filesystem_path(root, run_dir, spec)
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"synthetic prerequisite {index}\n".encode("utf-8"))

    execution_plan_path = run_dir / execution_plan_relative
    execution_plan_path.parent.mkdir(parents=True, exist_ok=True)
    final_plan_module = load_final_plan_module()
    execution_plan_path.write_bytes(
        final_plan_module.canonical_bytes(
            final_plan_module.build_expected_plan(root)
        )
    )
    return run_dir


def self_test(actual_repo_root: Path) -> dict[str, Any]:
    actual_repo_root = actual_repo_root.resolve()
    assert_readiness_sync(actual_repo_root)
    positive = 0
    negative = 0
    without_role_submission_base = tuple(
        spec
        for spec in INPUT_SPECS
        if spec.path
        != f"{SCHEMA.as_posix()}/role-submission-0.1.1.schema.json"
    )
    try:
        assert_audit_schema_dependency_closure(
            actual_repo_root,
            input_specs=without_role_submission_base,
        )
    except ProjectionAuditTaskError as exc:
        if "schema dependency closure incomplete" not in str(exc):
            raise
        negative += 1
    else:
        raise ProjectionAuditTaskError(
            "self-test accepted an unbound output-schema dependency"
        )
    with tempfile.TemporaryDirectory(
        prefix="game-primitives-projection-audit-"
    ) as temporary:
        root = Path(temporary).resolve()
        run_dir = populate_synthetic_repo(root, actual_repo_root)
        task = build_task(
            root,
            run_dir,
            "2026-07-27T00:00:00Z",
            enforce_readiness_sync=False,
        )
        validate_task_schema(task, actual_repo_root)
        task_path = expected_output_path(root, run_dir)
        task_path.parent.mkdir(parents=True, exist_ok=True)
        valid_task_bytes = canonical_bytes(task)
        task_path.write_bytes(valid_task_bytes)
        verify_task(
            root,
            run_dir,
            schema_repo_root=actual_repo_root,
            enforce_readiness_sync=False,
        )
        positive += 1

        fixture_lock = run_dir / "fixtures/fixture-lock.json"
        saved_fixture_lock = fixture_lock.read_bytes()
        fixture_lock.unlink()
        try:
            build_task(
                root,
                run_dir,
                "2026-07-27T00:00:00Z",
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if "fixtures/fixture-lock.json" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted a missing fixture lock"
            )
        fixture_lock.write_bytes(saved_fixture_lock)

        incident_path = run_dir / PROTOCOL_INCIDENT_RUN_PATH
        saved_incident = incident_path.read_bytes()
        incident = strict_json_object(incident_path)
        incident["aggregate_state"]["formal_input_byte_read"] = False
        incident_path.write_bytes(canonical_bytes(incident))
        try:
            build_task(
                root,
                run_dir,
                "2026-07-27T00:00:00Z",
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if "protocol incident schema validation failed" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted an incident that denied the byte read"
            )
        incident_path.write_bytes(saved_incident)

        projection_spec = run_dir / "inputs/projection-spec.json"
        saved_projection_spec = projection_spec.read_bytes()
        projection_spec.write_bytes(b"tampered synthetic projection spec\n")
        try:
            verify_task(
                root,
                run_dir,
                schema_repo_root=actual_repo_root,
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if "stale or differs" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted a changed prerequisite"
            )
        projection_spec.write_bytes(saved_projection_spec)

        execution_plan = run_dir / "execution/execution-plan.json"
        saved_execution_plan = execution_plan.read_bytes()
        execution_plan.write_bytes(
            canonical_bytes(
                {
                    "$schema": (
                        "https://github.com/onovich/Game-Primitives/blob/main/"
                        "research/calibration-tests/continuous-action-pilot/"
                        "schema/execution-plan-preparation-0.1.0.schema.json"
                    ),
                    "artifact_type": "execution_plan_preparation",
                    "artifact_version": "0.1.0",
                    "run_id": "continuous-001",
                }
            )
        )
        try:
            build_task(
                root,
                run_dir,
                "2026-07-27T00:00:00Z",
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if "not the final continuous-001 0.1.1 plan" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted a preparation plan as the final plan"
            )
        execution_plan.write_bytes(saved_execution_plan)

        tampered = strict_json_object(task_path)
        tampered["task_id"] = "task.projection-audit.tampered"
        task_path.write_bytes(canonical_bytes(tampered))
        try:
            verify_task(
                root,
                run_dir,
                schema_repo_root=actual_repo_root,
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if "stale or differs" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted a tampered task"
            )
        task_path.write_bytes(valid_task_bytes)

        polluted = strict_json_object(task_path)
        polluted["input_artifacts"].append(
            {
                "artifact_id": "polluted.truth-or-result",
                "path": OUTPUT_SCHEMA_PATH.as_posix(),
                "sha256": sha256(resolve_within(root, OUTPUT_SCHEMA_PATH)),
            }
        )
        task_path.write_bytes(canonical_bytes(polluted))
        try:
            verify_task(
                root,
                run_dir,
                schema_repo_root=actual_repo_root,
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if "stale or differs" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted a task with an extra polluted input"
            )
        task_path.write_bytes(valid_task_bytes)

        plan_document = strict_json_object(execution_plan)
        r1_plan = next(
            case
            for case in plan_document["cases"]
            if case["case_id"] == "CA-R1"
        )
        r1_variant = next(
            configuration
            for configuration in r1_plan["configurations"]
            if configuration["configuration_id"] == "config.variant"
        )
        r1_lock = next(
            case
            for case in strict_json_object(fixture_lock)["cases"]
            if case["case_id"] == "CA-R1"
        )
        variant_patch = r1_lock["variant_patch_set"]["artifacts"][0]
        r1_variant["fixture_artifacts"] = [
            reference
            for reference in r1_variant["fixture_artifacts"]
            if reference_key(reference) != reference_key(variant_patch)
        ]
        execution_plan.write_bytes(canonical_bytes(plan_document))
        try:
            build_task(
                root,
                run_dir,
                "2026-07-27T00:00:00Z",
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if "execution surface differs" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted a plan with an incomplete execution surface"
            )
        execution_plan.write_bytes(saved_execution_plan)

        build_readiness = (
            run_dir / "fixtures/formal-build-readiness-v0.1.0.json"
        )
        saved_readiness = build_readiness.read_bytes()
        incomplete_readiness = strict_json_object(build_readiness)
        incomplete_readiness.pop("cases")
        build_readiness.write_bytes(canonical_bytes(incomplete_readiness))
        try:
            build_task(
                root,
                run_dir,
                "2026-07-27T00:00:00Z",
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if "fixture assembly verification failed" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted incomplete formal build readiness"
            )
        build_readiness.write_bytes(saved_readiness)

        schema_path = resolve_within(
            root, SCHEMA / "fixture-lock-0.1.0.schema.json"
        )
        saved_schema = schema_path.read_bytes()
        schema_path.write_bytes(
            saved_schema.replace(
                b"{\n",
                b'{\n  "$id": "https://duplicate.invalid/schema.json",\n',
                1,
            )
        )
        try:
            build_task(
                root,
                run_dir,
                "2026-07-27T00:00:00Z",
                enforce_readiness_sync=False,
            )
        except ProjectionAuditTaskError as exc:
            if (
                "duplicate JSON key" not in str(exc)
                and "fixture assembly verification failed" not in str(exc)
            ):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted a schema with a duplicate JSON key"
            )
        schema_path.write_bytes(saved_schema)

        original_specs = INPUT_SPECS
        duplicate = InputSpec(
            "duplicate.alias",
            original_specs[0].path,
            original_specs[0].run_relative,
        )
        globals()["INPUT_SPECS"] = original_specs + (duplicate,)
        try:
            assert_readiness_sync(actual_repo_root)
        except ProjectionAuditTaskError as exc:
            if "duplicate projection-audit input path" not in str(exc):
                raise
            negative += 1
        else:
            raise ProjectionAuditTaskError(
                "self-test accepted a duplicate input path"
            )
        finally:
            globals()["INPUT_SPECS"] = original_specs

        task_path.unlink()
        with tempfile.TemporaryDirectory(
            prefix="game-primitives-projection-audit-outside-"
        ) as outside_name:
            outside_target = Path(outside_name).resolve() / "escaped.json"
            task_path.symlink_to(outside_target)
            try:
                expected_output_path(root, run_dir)
            except ProjectionAuditTaskError as exc:
                if "output path escapes" not in str(exc):
                    raise
                negative += 1
            else:
                raise ProjectionAuditTaskError(
                    "self-test accepted a symlinked output path"
                )
            finally:
                task_path.unlink()

    return {
        "formal_input_executed": False,
        "formal_result_created": False,
        "negative_controls_passed": negative,
        "positive_controls_passed": positive,
        "status": "passed",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    materialize_parser = subparsers.add_parser("materialize")
    materialize_parser.add_argument("--repo-root", type=Path, required=True)
    materialize_parser.add_argument("--run-dir", type=Path, required=True)
    materialize_parser.add_argument("--created-at", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--repo-root", type=Path, required=True)
    verify_parser.add_argument("--run-dir", type=Path, required=True)

    self_test_parser = subparsers.add_parser("self-test")
    self_test_parser.add_argument("--repo-root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "materialize":
            result = materialize(
                args.repo_root,
                args.run_dir,
                args.created_at,
            )
        elif args.command == "verify":
            result = verify_task(args.repo_root, args.run_dir)
        else:
            result = self_test(args.repo_root)
    except ProjectionAuditTaskError as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "formal_input_executed": False,
                    "formal_result_created": False,
                    "status": "failed",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
