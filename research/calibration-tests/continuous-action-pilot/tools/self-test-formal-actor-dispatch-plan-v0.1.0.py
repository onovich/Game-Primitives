#!/usr/bin/env python3
"""Black-box, disposable self-test for formal actor dispatch plan 0.1.0."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA = PILOT / "schema/formal-actor-dispatch-plan-0.1.0.schema.json"
CORE = PILOT / "tools/formal_actor_dispatch_plan_contract.py"
MATERIALIZER = (
    PILOT / "tools/materialize-formal-actor-dispatch-plan-v0.1.0.py"
)
VERIFIER = PILOT / "tools/verify-formal-actor-dispatch-plan-v0.1.0.py"
PLAN = (
    PILOT
    / "runs/continuous-002/inputs/dispatch/actor-dispatch-plan.json"
)
PROMPTS = PILOT / "runs/continuous-002/inputs/dispatch/prompts"
BODY_SOURCES = PILOT / "runs/continuous-002/source/dispatch-bodies"
SEATS = ("p01", "p02", "p03", "p04")
PRODUCTION_OUTPUTS = (
    PLAN,
    *(
        PROMPTS / f"{stage}-{seat}.prompt.txt"
        for stage in ("stage1", "stage2")
        for seat in SEATS
    ),
)


class SelfTestFailure(RuntimeError):
    """Raised when a positive or negative control does not behave as expected."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def load_contract_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        "formal_actor_dispatch_plan_contract_under_test",
        path,
    )
    if spec is None or spec.loader is None:
        raise SelfTestFailure(f"cannot load contract module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_contract_files(source_root: Path, target_root: Path) -> None:
    for relative in (SCHEMA, CORE, MATERIALIZER, VERIFIER):
        source = source_root / relative
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def write_sources(root: Path) -> dict[str, str]:
    source_directory = root / BODY_SOURCES
    source_directory.mkdir(parents=True, exist_ok=True)
    sources = {
        "rich": (BODY_SOURCES / "stage1-rich.body.txt").as_posix(),
        "atomic": (BODY_SOURCES / "stage1-atomic.body.txt").as_posix(),
        "stage2": (BODY_SOURCES / "stage2.body.txt").as_posix(),
    }
    (root / sources["rich"]).write_bytes(
        (
            "SYNTHETIC SELF-TEST ONLY.\n"
            "Return the rich reconstruction as one JSON object.\n"
        ).encode("utf-8")
    )
    (root / sources["atomic"]).write_bytes(
        (
            "SYNTHETIC SELF-TEST ONLY.\n"
            "Return the atomic reconstruction as one JSON object.\n"
        ).encode("utf-8")
    )
    (root / sources["stage2"]).write_bytes(
        (
            "SYNTHETIC SELF-TEST ONLY.\n"
            "Return the neutral prediction as one JSON object.\n"
        ).encode("utf-8")
    )
    return sources


def materializer_command(
    host_root: Path,
    repo_root: Path,
    _sources: dict[str, str],
    *,
    action: str,
    write: bool,
    use_host_tool: bool = False,
) -> list[str]:
    tool_root = host_root if use_host_tool else repo_root
    command = [
        sys.executable,
        str(tool_root / MATERIALIZER),
        action,
        "--repo-root",
        str(repo_root),
        "--created-at",
        "2026-07-28T00:00:00Z",
    ]
    if write:
        command.append("--write")
    return command


def verifier_command(
    host_root: Path,
    repo_root: Path,
    *,
    use_host_tool: bool = False,
) -> list[str]:
    tool_root = host_root if use_host_tool else repo_root
    return [
        sys.executable,
        str(tool_root / VERIFIER),
        "verify",
        "--repo-root",
        str(repo_root),
    ]


def require_success(
    completed: subprocess.CompletedProcess[str],
    *,
    label: str,
) -> dict[str, Any]:
    if completed.returncode != 0:
        raise SelfTestFailure(
            f"{label} failed: stdout={completed.stdout!r} "
            f"stderr={completed.stderr!r}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SelfTestFailure(
            f"{label} did not return JSON: {completed.stdout!r}"
        ) from error
    return result


def require_failure(
    completed: subprocess.CompletedProcess[str],
    *,
    label: str,
) -> None:
    if completed.returncode == 0:
        raise SelfTestFailure(
            f"negative control unexpectedly succeeded: {label}: "
            f"{completed.stdout!r}"
        )
    output = completed.stderr or completed.stdout
    try:
        result = json.loads(output)
    except json.JSONDecodeError as error:
        raise SelfTestFailure(
            f"negative control did not return JSON: {label}: {output!r}"
        ) from error
    if result.get("status") != "failed_closed":
        raise SelfTestFailure(
            f"negative control did not fail closed: {label}: {result!r}"
        )


def mutate_plan(
    plan: dict[str, Any],
    operation: Callable[[dict[str, Any]], None],
) -> bytes:
    candidate = copy.deepcopy(plan)
    operation(candidate)
    return canonical_bytes(candidate)


def main() -> int:
    source_root = Path(__file__).resolve().parents[4]
    before_exists = {
        relative.as_posix(): (source_root / relative).exists()
        for relative in PRODUCTION_OUTPUTS
    }
    positive_controls = 0
    negative_controls = 0
    skipped_controls: list[str] = []

    with tempfile.TemporaryDirectory(
        prefix="formal-actor-dispatch-plan-self-test-",
        dir=tempfile.gettempdir(),
    ) as temporary:
        synthetic_root = (Path(temporary) / "synthetic-repository").resolve()
        synthetic_root.mkdir(parents=True)
        copy_contract_files(source_root, synthetic_root)
        sources = write_sources(synthetic_root)

        require_failure(
            run(
                materializer_command(
                    source_root,
                    synthetic_root,
                    sources,
                    action="preview",
                    write=False,
                    use_host_tool=True,
                )
            ),
            label="cross-repository-runtime-binding",
        )
        negative_controls += 1

        preview = require_success(
            run(
                materializer_command(
                    source_root,
                    synthetic_root,
                    sources,
                    action="preview",
                    write=False,
                )
            ),
            label="preview",
        )
        if preview.get("status") != "previewed_inert":
            raise SelfTestFailure(f"unexpected preview result: {preview!r}")
        if (synthetic_root / PLAN).exists():
            raise SelfTestFailure("preview wrote the dispatch plan")
        positive_controls += 1

        materialized = require_success(
            run(
                materializer_command(
                    source_root,
                    synthetic_root,
                    sources,
                    action="materialize",
                    write=True,
                )
            ),
            label="materialization",
        )
        if materialized.get("status") != "materialized_inert":
            raise SelfTestFailure(
                f"unexpected materialization result: {materialized!r}"
            )
        positive_controls += 1

        require_failure(
            run(
                verifier_command(
                    source_root,
                    synthetic_root,
                    use_host_tool=True,
                )
            ),
            label="cross-repository-verifier-runtime-binding",
        )
        negative_controls += 1

        verified = require_success(
            run(verifier_command(source_root, synthetic_root)),
            label="verification",
        )
        if verified.get("status") != "verified_inert":
            raise SelfTestFailure(f"unexpected verification result: {verified!r}")
        if verified.get("seat_count") != 4 or verified.get("prompt_count") != 8:
            raise SelfTestFailure(f"wrong verified cardinality: {verified!r}")
        positive_controls += 1

        plan_path = synthetic_root / PLAN
        original_plan_raw = plan_path.read_bytes()
        plan = json.loads(original_plan_raw.decode("utf-8"))
        if original_plan_raw != canonical_bytes(plan):
            raise SelfTestFailure("materialized plan is not canonical JSON")
        positive_controls += 1

        prompt_raw = {
            (stage, seat): (
                synthetic_root / PROMPTS / f"{stage}-{seat}.prompt.txt"
            ).read_bytes()
            for stage in ("stage1", "stage2")
            for seat in SEATS
        }
        if prompt_raw["stage1", "p01"] != prompt_raw["stage1", "p02"]:
            raise SelfTestFailure("rich stage1 prompts differ")
        if prompt_raw["stage1", "p03"] != prompt_raw["stage1", "p04"]:
            raise SelfTestFailure("atomic stage1 prompts differ")
        if len({prompt_raw["stage2", seat] for seat in SEATS}) != 1:
            raise SelfTestFailure("stage2 prompts differ")
        if prompt_raw["stage1", "p01"] == prompt_raw["stage1", "p03"]:
            raise SelfTestFailure("rich and atomic stage1 prompts are identical")
        positive_controls += 4

        for seat in plan["seats"]:
            if any(value is not None for value in seat["runtime_binding"].values()):
                raise SelfTestFailure("pre-gate plan contains a runtime binding")
        positive_controls += 1

        def expect_plan_failure(
            label: str,
            operation: Callable[[dict[str, Any]], None],
        ) -> None:
            nonlocal negative_controls
            plan_path.write_bytes(mutate_plan(plan, operation))
            try:
                require_failure(
                    run(verifier_command(source_root, synthetic_root)),
                    label=label,
                )
            finally:
                plan_path.write_bytes(original_plan_raw)
            negative_controls += 1

        plan_path.write_bytes(original_plan_raw + b" ")
        try:
            require_failure(
                run(verifier_command(source_root, synthetic_root)),
                label="noncanonical-plan-bytes",
            )
        finally:
            plan_path.write_bytes(original_plan_raw)
        negative_controls += 1

        expect_plan_failure(
            "wrong-run-id",
            lambda value: value.__setitem__("run_id", "continuous-001"),
        )
        expect_plan_failure(
            "requested-model-changed",
            lambda value: value["actor_configuration"].__setitem__(
                "requested_model_alias", "some-other-model"
            ),
        )
        expect_plan_failure(
            "requested-effort-changed",
            lambda value: value["actor_configuration"].__setitem__(
                "requested_reasoning_effort", "medium"
            ),
        )
        expect_plan_failure(
            "observed-build-filled-pre-gate",
            lambda value: value["actor_configuration"].__setitem__(
                "observed_model_build", "untrusted-build"
            ),
        )
        expect_plan_failure(
            "observed-build-status-claimed",
            lambda value: value["actor_configuration"].__setitem__(
                "observed_model_build_status", "observed"
            ),
        )
        expect_plan_failure(
            "projectless-disabled",
            lambda value: value["isolation_policy"].__setitem__(
                "target_type", "workspace"
            ),
        )
        expect_plan_failure(
            "tools-enabled",
            lambda value: value["isolation_policy"].__setitem__(
                "tool_calls_allowed", True
            ),
        )
        expect_plan_failure(
            "network-enabled",
            lambda value: value["isolation_policy"].__setitem__(
                "network_access_allowed", True
            ),
        )
        expect_plan_failure(
            "shared-workspace-enabled",
            lambda value: value["isolation_policy"].__setitem__(
                "shared_workspace_allowed", True
            ),
        )
        expect_plan_failure(
            "cross-seat-session-reuse-enabled",
            lambda value: value["session_policy"].__setitem__(
                "cross_seat_session_reuse_allowed", True
            ),
        )
        expect_plan_failure(
            "same-session-disabled",
            lambda value: value["session_policy"].__setitem__(
                "same_session_for_stage1_and_stage2_required", False
            ),
        )
        expect_plan_failure(
            "invalid-stage1-does-not-block-stage2",
            lambda value: value["response_capture_policy"].__setitem__(
                "invalid_stage1_blocks_stage2", False
            ),
        )
        expect_plan_failure(
            "stage2-retroactively-invalidates-stage1",
            lambda value: value["response_capture_policy"].__setitem__(
                "valid_stage2_cannot_retroactively_invalidate_stage1", False
            ),
        )
        expect_plan_failure(
            "first-only-event-disabled",
            lambda value: value["response_capture_policy"].__setitem__(
                "first_and_only_assistant_event_must_be_final_json", False
            ),
        )
        expect_plan_failure(
            "commentary-enabled",
            lambda value: value["response_capture_policy"].__setitem__(
                "commentary_allowed", True
            ),
        )
        expect_plan_failure(
            "second-final-enabled",
            lambda value: value["response_capture_policy"].__setitem__(
                "second_final_allowed", True
            ),
        )
        expect_plan_failure(
            "actual-runtime-claimed-pre-gate",
            lambda value: value["capability_boundary"].__setitem__(
                "actual_runtime_compliance_verified", True
            ),
        )
        expect_plan_failure(
            "thread-id-filled-pre-gate",
            lambda value: value["seats"][0]["runtime_binding"].__setitem__(
                "thread_id", "019fffff-ffff-7fff-8fff-ffffffffffff"
            ),
        )
        expect_plan_failure(
            "session-id-filled-pre-gate",
            lambda value: value["seats"][0]["runtime_binding"].__setitem__(
                "session_id", "session-actual-0001"
            ),
        )
        expect_plan_failure(
            "receipt-filled-pre-gate",
            lambda value: value["seats"][0]["runtime_binding"].__setitem__(
                "stage1_dispatch_receipt", "submissions/dispatch/receipt.json"
            ),
        )
        expect_plan_failure(
            "condition-allocation-changed",
            lambda value: value["seats"][1].__setitem__("condition", "atomic"),
        )
        expect_plan_failure(
            "prompt-hash-mismatch",
            lambda value: value["seats"][0]["stage1_prompt"].__setitem__(
                "sha256", "0" * 64
            ),
        )
        expect_plan_failure(
            "prompt-path-mismatch",
            lambda value: value["seats"][0]["stage1_prompt"].__setitem__(
                "path",
                (
                    "research/calibration-tests/continuous-action-pilot/"
                    "runs/continuous-002/inputs/dispatch/prompts/"
                    "stage1-p04.prompt.txt"
                ),
            ),
        )
        expect_plan_failure(
            "contract-artifact-hash-mismatch",
            lambda value: value["contract_artifacts"]["verifier"].__setitem__(
                "sha256", "f" * 64
            ),
        )
        expect_plan_failure(
            "wire-byte-identity-claimed",
            lambda value: value["transport_policy"].__setitem__(
                "wire_byte_identity_claimed", True
            ),
        )
        expect_plan_failure(
            "readback-not-required",
            lambda value: value["post_gate_attestation_requirements"].__setitem__(
                "readback_sha256_required", False
            ),
        )

        rich_p02_path = synthetic_root / PROMPTS / "stage1-p02.prompt.txt"
        rich_p02_original = rich_p02_path.read_bytes()
        rich_p02_changed = rich_p02_original[:-1] + b"distinct-seat-body\n"
        changed_plan = copy.deepcopy(plan)
        changed_plan["seats"][1]["stage1_prompt"]["byte_length"] = len(
            rich_p02_changed
        )
        changed_plan["seats"][1]["stage1_prompt"]["sha256"] = hashlib.sha256(
            rich_p02_changed
        ).hexdigest()
        rich_p02_path.write_bytes(rich_p02_changed)
        plan_path.write_bytes(canonical_bytes(changed_plan))
        try:
            require_failure(
                run(verifier_command(source_root, synthetic_root)),
                label="same-condition-stage1-bytes-differ",
            )
        finally:
            rich_p02_path.write_bytes(rich_p02_original)
            plan_path.write_bytes(original_plan_raw)
        negative_controls += 1

        stage1_p01_path = synthetic_root / PROMPTS / "stage1-p01.prompt.txt"
        stage1_p01_original = stage1_p01_path.read_bytes()
        forged_rich_prompt = (
            stage1_p01_original[:-1] + b"forged-source-derivation-body\n"
        )
        changed_plan = copy.deepcopy(plan)
        for seat_index in (0, 1):
            changed_plan["seats"][seat_index]["stage1_prompt"]["byte_length"] = len(
                forged_rich_prompt
            )
            changed_plan["seats"][seat_index]["stage1_prompt"][
                "sha256"
            ] = hashlib.sha256(forged_rich_prompt).hexdigest()
        stage1_p01_path.write_bytes(forged_rich_prompt)
        rich_p02_path.write_bytes(forged_rich_prompt)
        plan_path.write_bytes(canonical_bytes(changed_plan))
        try:
            require_failure(
                run(verifier_command(source_root, synthetic_root)),
                label="same-condition-prompts-forged-away-from-source",
            )
        finally:
            stage1_p01_path.write_bytes(stage1_p01_original)
            rich_p02_path.write_bytes(rich_p02_original)
            plan_path.write_bytes(original_plan_raw)
        negative_controls += 1

        stage2_p04_path = synthetic_root / PROMPTS / "stage2-p04.prompt.txt"
        stage2_p04_original = stage2_p04_path.read_bytes()
        stage2_p04_changed = stage2_p04_original[:-1] + b"distinct-stage2-body\n"
        changed_plan = copy.deepcopy(plan)
        changed_plan["seats"][3]["stage2_prompt"]["byte_length"] = len(
            stage2_p04_changed
        )
        changed_plan["seats"][3]["stage2_prompt"]["sha256"] = hashlib.sha256(
            stage2_p04_changed
        ).hexdigest()
        stage2_p04_path.write_bytes(stage2_p04_changed)
        plan_path.write_bytes(canonical_bytes(changed_plan))
        try:
            require_failure(
                run(verifier_command(source_root, synthetic_root)),
                label="stage2-bytes-differ",
            )
        finally:
            stage2_p04_path.write_bytes(stage2_p04_original)
            plan_path.write_bytes(original_plan_raw)
        negative_controls += 1

        stage1_p01_path.unlink()
        try:
            require_failure(
                run(verifier_command(source_root, synthetic_root)),
                label="prompt-missing",
            )
        finally:
            stage1_p01_path.write_bytes(stage1_p01_original)
        negative_controls += 1

        schema_path = synthetic_root / SCHEMA
        schema_original = schema_path.read_bytes()
        schema_document = json.loads(schema_original.decode("utf-8"))
        schema_document["title"] = "tampered"
        schema_path.write_bytes(canonical_bytes(schema_document))
        try:
            require_failure(
                run(verifier_command(source_root, synthetic_root)),
                label="schema-hash-mismatch",
            )
        finally:
            schema_path.write_bytes(schema_original)
        negative_controls += 1

        require_failure(
            run(
                materializer_command(
                    source_root,
                    synthetic_root,
                    sources,
                    action="materialize",
                    write=True,
                )
            ),
            label="overwrite-refused",
        )
        negative_controls += 1

        require_failure(
            run(
                materializer_command(
                    source_root,
                    synthetic_root,
                    sources,
                    action="materialize",
                    write=False,
                )
            ),
            label="write-flag-required",
        )
        negative_controls += 1

        rollback_root = synthetic_root / "synthetic-write-failure-repository"
        rollback_root.mkdir()
        contract_module = load_contract_module(source_root / CORE)
        rollback_first = Path("synthetic/rollback/first.bin")
        rollback_current = Path("synthetic/rollback/current.bin")
        try:
            contract_module.write_outputs_exclusive(
                rollback_root,
                {
                    rollback_first.as_posix(): b"first\n",
                    rollback_current.as_posix(): None,
                },
            )
        except Exception:
            pass
        else:
            raise SelfTestFailure("write-failure control unexpectedly succeeded")
        rollback_residue = [
            relative.as_posix()
            for relative in (rollback_first, rollback_current)
            if (rollback_root / relative).exists()
        ]
        if rollback_residue:
            raise SelfTestFailure(
                "write failure left output residue: "
                + ", ".join(rollback_residue)
            )
        negative_controls += 1

        class FaultyWriter:
            def __init__(
                self,
                handle: Any,
                *,
                raise_after_write: bool,
            ) -> None:
                self.handle = handle
                self.raise_after_write = raise_after_write

            def __enter__(self) -> "FaultyWriter":
                return self

            def __exit__(self, *_args: Any) -> None:
                self.handle.close()

            def write(self, raw: bytes) -> int:
                written = self.handle.write(raw[: max(1, len(raw) // 2)])
                if self.raise_after_write:
                    raise OSError("synthetic partial-write failure")
                return written

        original_path_open = Path.open
        for suffix, raise_after_write in (
            ("short", False),
            ("partial-exception", True),
        ):
            fault_root = synthetic_root / f"synthetic-{suffix}-repository"
            fault_root.mkdir()
            first = fault_root / "outputs/first.bin"
            current = fault_root / "outputs/current.bin"

            def faulty_open(
                target: Path,
                mode: str = "r",
                *args: Any,
                should_raise: bool = raise_after_write,
                **kwargs: Any,
            ) -> Any:
                handle = original_path_open(target, mode, *args, **kwargs)
                if target == current and mode == "xb":
                    return FaultyWriter(
                        handle,
                        raise_after_write=should_raise,
                    )
                return handle

            with patch.object(Path, "open", new=faulty_open):
                try:
                    contract_module.write_outputs_exclusive(
                        fault_root,
                        {
                            "outputs/first.bin": b"first\n",
                            "outputs/current.bin": b"second\n",
                        },
                    )
                except Exception:
                    pass
                else:
                    raise SelfTestFailure(
                        f"{suffix} write control unexpectedly succeeded"
                    )
            if first.exists() or current.exists():
                raise SelfTestFailure(
                    f"{suffix} write control left output residue"
                )
            negative_controls += 1

        bad_source_path = synthetic_root / sources["rich"]
        good_source = bad_source_path.read_bytes()
        bad_source_path.write_bytes(b"\xef\xbb\xbf" + good_source)
        try:
            require_failure(
                run(
                    materializer_command(
                        source_root,
                        synthetic_root,
                        sources,
                        action="preview",
                        write=False,
                    )
                ),
                label="source-bom",
            )
        finally:
            bad_source_path.write_bytes(good_source)
        negative_controls += 1

        bad_source_path.write_bytes(
            (
                "SYNTHETIC SELF-TEST ONLY.\n"
                '{"\\u005cu0074hread_id":"019fffff-ffff-7fff-8fff-ffffffffffff"}\n'
            ).encode("utf-8")
        )
        try:
            require_failure(
                run(
                    materializer_command(
                        source_root,
                        synthetic_root,
                        sources,
                        action="preview",
                        write=False,
                    )
                ),
                label="nested-unicode-escaped-source-runtime-field",
            )
        finally:
            bad_source_path.write_bytes(good_source)
        negative_controls += 1

        bad_source_path.write_bytes(
            (
                "SYNTHETIC SELF-TEST ONLY.\n"
                "thread_id=/*template*/019fffff-ffff-7fff-8fff-ffffffffffff\n"
            ).encode("utf-8")
        )
        try:
            require_failure(
                run(
                    materializer_command(
                        source_root,
                        synthetic_root,
                        sources,
                        action="preview",
                        write=False,
                    )
                ),
                label="comment-prefixed-source-runtime-binding",
            )
        finally:
            bad_source_path.write_bytes(good_source)
        negative_controls += 1

        bad_source_path.write_bytes(
            (
                "SYNTHETIC SELF-TEST ONLY.\n"
                '{"\\u0074hread_id":"019fffff-ffff-7fff-8fff-ffffffffffff"}\n'
            ).encode("utf-8")
        )
        try:
            require_failure(
                run(
                    materializer_command(
                        source_root,
                        synthetic_root,
                        sources,
                        action="preview",
                        write=False,
                    )
                ),
                label="unicode-escaped-source-runtime-field",
            )
        finally:
            bad_source_path.write_bytes(good_source)
        negative_controls += 1

        bad_source_path.write_bytes(
            (
                "SYNTHETIC SELF-TEST ONLY.\n"
                "thread_id=(\n"
                "019fffff-ffff-7fff-8fff-ffffffffffff)\n"
            ).encode("utf-8")
        )
        try:
            require_failure(
                run(
                    materializer_command(
                        source_root,
                        synthetic_root,
                        sources,
                        action="preview",
                        write=False,
                    )
                ),
                label="multiline-parenthesized-source-runtime-binding",
            )
        finally:
            bad_source_path.write_bytes(good_source)
        negative_controls += 1

        bad_source_path.write_bytes(
            (
                "SYNTHETIC SELF-TEST ONLY.\n"
                "thread_id=(019fffff-ffff-7fff-8fff-ffffffffffff)\n"
            ).encode("utf-8")
        )
        try:
            require_failure(
                run(
                    materializer_command(
                        source_root,
                        synthetic_root,
                        sources,
                        action="preview",
                        write=False,
                    )
                ),
                label="parenthesized-source-runtime-binding",
            )
        finally:
            bad_source_path.write_bytes(good_source)
        negative_controls += 1

        bad_source_path.write_bytes(
            b"SYNTHETIC SELF-TEST ONLY.\nthread_id=actual-thread-0001\n"
        )
        try:
            require_failure(
                run(
                    materializer_command(
                        source_root,
                        synthetic_root,
                        sources,
                        action="preview",
                        write=False,
                    )
                ),
                label="source-runtime-binding",
            )
        finally:
            bad_source_path.write_bytes(good_source)
        negative_controls += 1

        bad_source_path.write_bytes(
            (
                "SYNTHETIC SELF-TEST ONLY.\n"
                "{\\\"sessionId\\\":\\\"actual-session-0001\\\"}\n"
            ).encode("utf-8")
        )
        try:
            require_failure(
                run(
                    materializer_command(
                        source_root,
                        synthetic_root,
                        sources,
                        action="preview",
                        write=False,
                    )
                ),
                label="escaped-source-runtime-binding",
            )
        finally:
            bad_source_path.write_bytes(good_source)
        negative_controls += 1

        source_link_target = synthetic_root / "synthetic/outside.body.txt"
        source_link_target.parent.mkdir(parents=True, exist_ok=True)
        source_link_target.write_bytes(good_source)
        bad_source_path.unlink()
        try:
            try:
                os.symlink(source_link_target, bad_source_path)
            except (NotImplementedError, OSError):
                skipped_controls.append("body-source-symlink")
            else:
                require_failure(
                    run(
                        materializer_command(
                            source_root,
                            synthetic_root,
                            sources,
                            action="preview",
                            write=False,
                        )
                    ),
                    label="body-source-symlink",
                )
                negative_controls += 1
        finally:
            if bad_source_path.is_symlink():
                bad_source_path.unlink()
            if not bad_source_path.exists():
                bad_source_path.write_bytes(good_source)

        link_path = synthetic_root / PROMPTS / "stage1-p01.prompt.txt"
        link_target = synthetic_root / "synthetic/link-target.prompt.txt"
        link_target.parent.mkdir(parents=True, exist_ok=True)
        link_target.write_bytes(stage1_p01_original)
        link_path.unlink()
        try:
            try:
                os.symlink(link_target, link_path)
            except (NotImplementedError, OSError):
                skipped_controls.append("prompt-symlink")
            else:
                require_failure(
                    run(verifier_command(source_root, synthetic_root)),
                    label="prompt-symlink",
                )
                negative_controls += 1
        finally:
            if link_path.is_symlink():
                link_path.unlink()
            if not link_path.exists():
                link_path.write_bytes(stage1_p01_original)

        require_success(
            run(verifier_command(source_root, synthetic_root)),
            label="post-negative-restoration-verification",
        )
        positive_controls += 1

    after_exists = {
        relative.as_posix(): (source_root / relative).exists()
        for relative in PRODUCTION_OUTPUTS
    }
    if after_exists != before_exists:
        raise SelfTestFailure(
            "self-test changed production continuous-002 output existence"
        )

    print(
        json.dumps(
            {
                "actual_codex_tasks_created": 0,
                "actual_dispatches_performed": 0,
                "actual_sessions_created": 0,
                "actual_threads_created": 0,
                "formal_inputs_read": False,
                "negative_control_count": negative_controls,
                "node_processes_started": 0,
                "positive_control_count": positive_controls,
                "production_outputs_touched": False,
                "runner_or_comparator_executed": False,
                "skipped_controls": skipped_controls,
                "status": "synthetic_self_test_passed",
                "temporary_workspace_removed": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SelfTestFailure, OSError, subprocess.SubprocessError) as error:
        print(
            json.dumps(
                {
                    "actual_dispatches_performed": 0,
                    "error": str(error),
                    "status": "synthetic_self_test_failed_closed",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)
