#!/usr/bin/env python3
"""Materialize and verify exact projectless actor prompts for rehearsal-006."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


PILOT = Path("research/calibration-tests/continuous-action-pilot")
REHEARSAL = PILOT / "rehearsals/rehearsal-006"
OUTPUTS = REHEARSAL / "inputs/dispatch"
DISPATCH_SCHEMA = (
    PILOT / "schema/rehearsal-actor-dispatch-plan-0.1.0.schema.json"
)


class PromptError(RuntimeError):
    """Raised when dispatch prompts cannot be reproduced exactly."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def repo_path(repo_root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(repo_root.resolve()):
        raise PromptError(f"path escapes repository root: {value}")
    return resolved


def canonical_json_text(path: Path) -> str:
    raw = path.read_bytes()
    if (
        raw.startswith(b"\xef\xbb\xbf")
        or b"\r\n" in raw
        or not raw.endswith(b"\n")
    ):
        raise PromptError(f"non-canonical JSON bytes: {path}")
    value = json.loads(raw.decode("utf-8"))
    expected = canonical_bytes(value)
    if raw != expected:
        raise PromptError(f"JSON key order or indentation differs: {path}")
    return raw.decode("utf-8").rstrip("\n")


def validate_plan(repo_root: Path, plan: dict[str, Any]) -> None:
    schema_path = repo_path(repo_root, DISPATCH_SCHEMA)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        ).iter_errors(plan),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        first = errors[0]
        location = "/".join(str(part) for part in first.absolute_path)
        raise PromptError(
            f"dispatch plan fails Schema at {location or '<root>'}: "
            f"{first.message}"
        )


def fenced(label: str, content: str) -> str:
    return f"## {label}\n\n```json\n{content}\n```"


def stage1_prompt(
    repo_root: Path,
    *,
    condition: str,
) -> bytes:
    task = canonical_json_text(
        repo_path(
            repo_root,
            REHEARSAL
            / f"inputs/reconstruction-condition-{condition}.task.json",
        )
    )
    view = canonical_json_text(
        repo_path(
            repo_root,
            REHEARSAL / f"inputs/view-{condition}.json",
        )
    )
    template = canonical_json_text(
        repo_path(
            repo_root,
            REHEARSAL
            / f"inputs/reconstruction-response-{condition}.template.json",
        )
    )
    text = "\n\n".join(
        [
            "# rehearsal-006：第一阶段结构重构",
            (
                "你是一个全新的空白盲测参与者。只根据本消息内联的三份材料完成"
                "结构重构；不要使用任何既往项目知识来补全材料没有给出的事实。"
            ),
            "\n".join(
                [
                    "必须遵守：",
                    "- 不调用任何工具，不访问文件、网络、共享工作区或其他会话。",
                    "- 不创建子任务，不询问澄清，不等待追加说明。",
                    "- 不发送 commentary 或中间答案。",
                    "- 阅读模板中的 participant_contract，并完成 template_payload。",
                    "- 不填写运行、任务、条件、actor、session、时间、散列或审核元数据。",
                    "- 你的第一条 assistant final 必须且只能是一个 JSON 对象；不要使用 Markdown 代码围栏，也不要在 JSON 前后添加文字。",
                ]
            ),
            fenced("任务", task),
            fenced("条件视图", view),
            fenced("重构回答模板", template),
        ]
    )
    return (text + "\n").encode("utf-8")


def stage2_prompt(repo_root: Path) -> bytes:
    task = canonical_json_text(
        repo_path(
            repo_root,
            REHEARSAL / "inputs/prediction-neutral.task.json",
        )
    )
    envelope = canonical_json_text(
        repo_path(
            repo_root,
            REHEARSAL / "inputs/variant-envelope.json",
        )
    )
    template = canonical_json_text(
        repo_path(
            repo_root,
            REHEARSAL / "inputs/prediction-response.template.json",
        )
    )
    text = "\n\n".join(
        [
            "# rehearsal-006：第二阶段中性变体预测",
            (
                "继续使用你在本会话第一阶段形成的重构；除此之外，只根据本消息"
                "内联的三份材料完成预测。不要查看或推断其他参与者的回答。"
            ),
            "\n".join(
                [
                    "必须遵守：",
                    "- 不调用任何工具，不访问文件、网络、共享工作区或其他会话。",
                    "- 不创建子任务，不询问澄清，不等待追加说明。",
                    "- 不发送 commentary 或中间答案。",
                    "- 阅读模板中的 participant_contract，并完成 template_payload。",
                    "- 严格区分字符串选择和真正的 JSON null；相容替代必须满足契约中的完整笛卡尔积规则。",
                    "- 不填写运行、任务、条件、actor、session、时间、散列或审核元数据。",
                    "- 你的本阶段第一条 assistant final 必须且只能是一个 JSON 对象；不要使用 Markdown 代码围栏，也不要在 JSON 前后添加文字。",
                ]
            ),
            fenced("预测任务", task),
            fenced("中性变体信封", envelope),
            fenced("预测回答模板", template),
        ]
    )
    return (text + "\n").encode("utf-8")


def expected_outputs(
    repo_root: Path,
    *,
    created_at: str,
) -> dict[Path, bytes]:
    stage1_v01 = stage1_prompt(repo_root, condition="v01")
    stage1_v02 = stage1_prompt(repo_root, condition="v02")
    stage2 = stage2_prompt(repo_root)
    prompt_paths = {
        "v01": OUTPUTS / "stage1-v01.prompt.txt",
        "v02": OUTPUTS / "stage1-v02.prompt.txt",
        "stage2": OUTPUTS / "stage2-neutral.prompt.txt",
    }
    seats = []
    for condition in ("v01", "v02"):
        for suffix in ("a", "b"):
            seats.append(
                {
                    "actor_id": f"r006-{condition}-{suffix}",
                    "condition_id": f"condition-{condition}",
                    "directory_name": f"gp-r006-{condition}-{suffix}",
                    "stage1_prompt": {
                        "path": prompt_paths[condition].as_posix(),
                        "sha256": sha256(
                            stage1_v01
                            if condition == "v01"
                            else stage1_v02
                        ),
                    },
                    "stage2_prompt": {
                        "path": prompt_paths["stage2"].as_posix(),
                        "sha256": sha256(stage2),
                    },
                }
            )
    plan = {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "rehearsal-actor-dispatch-plan-0.1.0.schema.json"
        ),
        "actor_configuration": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
            "role": "blind_reconstructor_predictor",
        },
        "artifact_type": "rehearsal_actor_dispatch_plan",
        "artifact_version": "0.1.0",
        "created_at": created_at,
        "dispatch_rules": {
            "corrective_followup_allowed": False,
            "first_answer_only": True,
            "fork_existing_thread": False,
            "same_thread_for_stage2": True,
            "target_type": "projectless",
            "tool_calls_allowed": False,
        },
        "run_id": "rehearsal-006",
        "seats": seats,
    }
    validate_plan(repo_root, plan)
    return {
        repo_path(repo_root, prompt_paths["v01"]): stage1_v01,
        repo_path(repo_root, prompt_paths["v02"]): stage1_v02,
        repo_path(repo_root, prompt_paths["stage2"]): stage2,
        repo_path(repo_root, OUTPUTS / "actor-dispatch-plan.json"): (
            canonical_bytes(plan)
        ),
    }


def command_materialize(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    outputs = expected_outputs(repo_root, created_at=args.created_at)
    for path in outputs:
        if path.exists():
            raise PromptError(f"refusing to overwrite dispatch artifact: {path}")
    output_root = repo_path(repo_root, OUTPUTS)
    output_root.mkdir(parents=True, exist_ok=True)
    for path, raw in outputs.items():
        path.write_bytes(raw)
    print(
        json.dumps(
            {
                "artifacts": {
                    relative.as_posix(): sha256(raw)
                    for path, raw in outputs.items()
                    for relative in [
                        path.relative_to(repo_root),
                    ]
                },
                "status": "materialized",
            },
            sort_keys=True,
        )
    )
    return 0


def command_verify(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    outputs = expected_outputs(repo_root, created_at=args.created_at)
    for path, expected in outputs.items():
        if path.read_bytes() != expected:
            raise PromptError(f"dispatch artifact differs: {path}")
    print(
        json.dumps(
            {
                "artifact_count": len(outputs),
                "status": "verified",
            },
            sort_keys=True,
        )
    )
    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    subcommands = value.add_subparsers(dest="command", required=True)
    for name, function in (
        ("materialize", command_materialize),
        ("verify", command_verify),
    ):
        command = subcommands.add_parser(name)
        command.add_argument("--repo-root", required=True, type=Path)
        command.add_argument("--created-at", required=True)
        command.set_defaults(func=function)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (PromptError, json.JSONDecodeError, OSError) as exc:
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
