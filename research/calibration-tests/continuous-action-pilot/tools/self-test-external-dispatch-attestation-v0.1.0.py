#!/usr/bin/env python3
"""Disposable black-box controls for external dispatch attestation 0.1.0.

Every control uses synthetic Git repositories in the system temporary
directory. No real runs/ path, external query, dispatcher, runner, comparator,
or reveal flow is opened or executed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


PILOT = Path("research/calibration-tests/continuous-action-pilot")
SCHEMA = PILOT / (
    "schema/external-dispatch-attestation-0.1.0.schema.json"
)
TEMPLATE = PILOT / (
    "contracts/external-dispatch-attestation.template-0.1.0.json"
)
VERIFIER = PILOT / (
    "tools/verify-external-dispatch-attestation-v0.1.0.py"
)
DENYLIST = PILOT / (
    "contracts/formal-post-gate-absence-denylist-0.1.0.json"
)
MANIFEST = PILOT / "runs/continuous-002/manifest.json"
DELTA = PILOT / (
    "runs/continuous-002/inputs/formal-run-delta-v0.1.0.json"
)
ATTESTATION_DIRECTORY = PILOT / (
    "runs/continuous-002/gate/external-dispatch-attestations"
)
EXPECTED_POSITIVE_IDS = (
    "P01_TEMPLATE_SCHEMA_AND_EMPTY_SLOTS",
    "P02_INITIAL_DRAFT",
    "P03_INITIAL_COMMITTED",
    "P04_SUBSEQUENT_DRAFT",
    "P05_SUBSEQUENT_COMMITTED",
    "P06_DETERMINISTIC_READ_ONLY_NO_EXTERNAL_ACTION",
    "P07_HOSTILE_FSMONITOR_DISABLED",
)
EXPECTED_NEGATIVE_IDS = (
    "N-CLI01_ISOLATED_REQUIRED",
    "N-CLI02_BYTE_READ_ACK_REQUIRED",
    "N-CLI03_CALLER_TIME_OVERRIDE_FORBIDDEN",
    "N-GIT01_AMBIENT_GIT_DIR",
    "N-GIT02_REPLACE_REF",
    "N-GIT03_LEGACY_GRAFT",
    "N-GIT04_OBJECT_ALTERNATES",
    "N-GIT05_CLEAN_FILTER",
    "N-GIT06_PROCESS_FILTER",
    "N-GIT07_PARTIAL_PROMISOR_CONFIG",
    "N-TRUST01_SCHEMA_TAMPER",
    "N-TRUST02_TEMPLATE_TAMPER",
    "N-BYTES01_INSTANCE_BOM",
    "N-BYTES02_INSTANCE_CRLF",
    "N-BYTES03_INSTANCE_DUPLICATE_KEY",
    "N-BYTES04_INSTANCE_NONFINITE",
    "N-ANCHOR01_EXPECTED_B_MISMATCH",
    "N-ANCHOR02_EXPECTED_ROOT_MISMATCH",
    "N-COMMIT01_WRONG_FINALIZE_B",
    "N-COMMIT02_FROZEN_ROOT_DRIFT",
    "N-COMMIT03_MANIFEST_HASH_DRIFT",
    "N-DELTA01_DELTA_HASH_DRIFT",
    "N-DENY01_DENYLIST_HASH_DRIFT",
    "N-HEAD01_DRAFT_HEAD_DRIFT",
    "N-HISTORY01_ORDINARY_POST_B_COMMIT",
    "N-HISTORY02_INVALID_PRIOR_ATTESTATION",
    "N-HISTORY03_MERGE_POST_B_COMMIT",
    "N-SAVE01_MULTI_FILE_COMMIT",
    "N-SAVE02_OVERWRITE_OLD_ATTESTATION",
    "N-LATEST01_STALE_ATTESTATION_COMMIT",
    "N-SEQ01_SEQUENCE_DRIFT",
    "N-SEQ02_PREVIOUS_COMMIT_DRIFT",
    "N-TIME01_REVERSED_QUERY",
    "N-TIME02_STALE_ABSENCE",
    "N-TIME03_QUERY_TOO_LONG",
    "N-TIME04_GATE_EXPIRED",
    "N-SCOPE01_GLOBAL_SCOPE",
    "N-SCOPE02_ABSOLUTE_DISPATCH_CLAIM",
    "N-CAP01_DISPATCH_CAPABILITY",
    "N-CAP02_SESSION_INVENTORY_CLAIM",
    "N-QUERY01_MATCH_RULE_DRIFT",
    "N-QUERY02_LISTING_CONTRACT_DRIFT",
    "N-RESULT01_MATCHING_OBJECT",
    "N-ID01_ID_DIGEST_DRIFT",
    "N-WORKTREE01_EXTRA_DIRTY_PATH",
    "N-VERIFIER01_TRUST_ROOT_DRIFT",
    "N-PATH01_INSTANCE_PATH_DRIFT",
)


class SelfTestFailure(RuntimeError):
    """Raised when a fixed synthetic control behaves unexpectedly."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise SelfTestFailure(
            f"git {' '.join(arguments)} failed: {completed.stderr}"
        )
    return completed.stdout.strip()


def copy_inputs(source_root: Path, root: Path) -> None:
    for relative in (SCHEMA, TEMPLATE, VERIFIER, DENYLIST):
        source = source_root / relative
        if not source.is_file():
            raise SelfTestFailure(f"required source is absent: {source}")
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def build_repository(source_root: Path, root: Path) -> dict[str, Any]:
    copy_inputs(source_root, root)
    git(root, "init", "--quiet")
    git(root, "config", "user.email", "synthetic@example.invalid")
    git(root, "config", "user.name", "Synthetic Self Test")
    git(root, "config", "core.autocrlf", "false")
    denylist_reference = {
        "artifact_version": "0.1.0",
        "path": DENYLIST.as_posix(),
        "sha256": sha256_path(root / DENYLIST),
    }
    scan_snapshot = "a" * 64
    delta = {
        "artifact_type": "formal_run_delta",
        "candidate_run_id": "continuous-002",
        "gate_policy": {
            "external_dispatch_attestation_instances_allowed": False,
            "external_dispatch_attestation_required_after_b": True,
        },
        "repository_absence": {
            "denylist_contract": denylist_reference,
            "matches": [],
            "scan_snapshot_sha256": scan_snapshot,
            "status": "passed",
        },
    }
    write_json(root / DELTA, delta)
    frozen_root = "b" * 64
    manifest = {
        "artifact_type": "formal_run_manifest",
        "freeze_commit": None,
        "frozen_artifact_set_digest": frozen_root,
        "run_id": "continuous-002",
        "status": "preparing",
        "updated_at": "2026-07-29T00:00:00Z",
    }
    write_json(root / MANIFEST, manifest)
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "-m", "synthetic commit A")
    commit_a = git(root, "rev-parse", "HEAD")
    manifest["freeze_commit"] = commit_a
    manifest["status"] = "frozen"
    manifest["updated_at"] = "2026-07-29T00:00:01Z"
    write_json(root / MANIFEST, manifest)
    git(root, "add", MANIFEST.as_posix())
    git(root, "commit", "--quiet", "-m", "synthetic commit B")
    commit_b = git(root, "rev-parse", "HEAD")
    return {
        "clock_base": datetime.now(timezone.utc).replace(
            microsecond=0
        ) - timedelta(seconds=120),
        "commit_a": commit_a,
        "commit_b": commit_b,
        "denylist_reference": denylist_reference,
        "frozen_root": frozen_root,
        "scan_snapshot": scan_snapshot,
        "verifier_sha256": sha256_path(root / VERIFIER),
    }


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def shift_utc(value: str, seconds: int) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    return utc_text(parsed + timedelta(seconds=seconds))


def build_instance(
    root: Path,
    fixture: dict[str, Any],
    *,
    observed_head: str,
    sequence: int,
) -> tuple[dict[str, Any], str]:
    base = fixture["clock_base"] + timedelta(seconds=30 * (sequence - 1))
    checked = base
    started = base + timedelta(seconds=10)
    completed = base + timedelta(seconds=20)
    attested = base + timedelta(seconds=25)
    valid_until = completed + timedelta(seconds=600)
    project_locator = "git@github.com:onovich/Game-Primitives.git"
    normalized_listing = [
        {
            "archived": False,
            "object_kind": "task_thread",
            "project_locator": project_locator,
            "status": "active",
            "title": f"synthetic unrelated thread {sequence}",
        }
    ]
    listing_digest = sha256_bytes(canonical_bytes(normalized_listing))
    attestation_id = (
        f"eda-{completed.strftime('%Y%m%dT%H%M%SZ')}-"
        f"{listing_digest[:12]}"
    )
    relative = (
        f"{ATTESTATION_DIRECTORY.as_posix()}/{attestation_id}.json"
    )
    template = json.loads((root / TEMPLATE).read_text(encoding="utf-8"))
    previous = None if sequence == 1 else observed_head
    relation = (
        "equals_finalize_commit_b"
        if sequence == 1
        else "attestation_only_descendant_of_finalize_commit_b"
    )
    document = {
        "$schema": (
            "https://github.com/onovich/Game-Primitives/blob/main/"
            "research/calibration-tests/continuous-action-pilot/schema/"
            "external-dispatch-attestation-0.1.0.schema.json"
        ),
        "artifact_type": "external_dispatch_attestation",
        "artifact_version": "0.1.0",
        "attestation_id": attestation_id,
        "candidate_run_id": "continuous-002",
        "commit_binding": {
            "finalize_commit_b": fixture["commit_b"],
            "freeze_anchor_commit_a": fixture["commit_a"],
            "frozen_artifact_set_digest": fixture["frozen_root"],
            "frozen_manifest_path": MANIFEST.as_posix(),
            "frozen_manifest_sha256": sha256_path(root / MANIFEST),
            "observed_head": observed_head,
            "observed_head_relation": relation,
            "previous_attestation_commit": previous,
            "sequence": sequence,
        },
        "conclusion": {
            "claim_scope": (
                "current_authenticated_account_current_project_"
                "visible_objects"
            ),
            "global_absence_claimed": False,
            "matching_formal_dispatch_object_observed": False,
            "status": "no_matching_formal_dispatch_objects_observed",
        },
        "document_state": "post_b_observation",
        "external_query": {
            "capability_limits": {
                "archive": False,
                "archived_objects_in_scope": True,
                "create": False,
                "delete": False,
                "deleted_objects_visible": False,
                "dispatch": False,
                "execute": False,
                "global_search": False,
                "inaccessible_objects_visible": False,
                "message_body_read": False,
                "metadata_listing": True,
                "objects_outside_current_account_visible": False,
                "provider_signed_result": False,
                "send": False,
                "standalone_session_inventory": False,
                "update": False,
            },
            "claim_scope": (
                "current_authenticated_account_current_project_"
                "visible_objects"
            ),
            "interface": "codex_project_task_listing",
            "listing_contract": {
                "input_record_scope": (
                    "all_visible_active_and_archived_task_threads_"
                    "in_exact_project"
                ),
                "listing_serialization": (
                    "canonical_json_array_utf8_no_bom_lf"
                ),
                "normalization_version": (
                    "codex_project_task_listing_v0.1.0"
                ),
                "pagination_required": "complete",
                "projection_fields": [
                    "archived",
                    "object_kind",
                    "project_locator",
                    "status",
                    "title",
                ],
                "record_sort": (
                    "ascending_by_canonical_record_utf8_bytes"
                ),
                "record_serialization": (
                    "canonical_json_object_utf8_no_bom_lf"
                ),
                "string_normalization": "unicode_nfc",
            },
            "matching_rule": {
                "candidate_token": "[continuous-002]",
                "case_handling": "unicode_casefold",
                "field": "title",
                "formal_dispatch_marker": "[formal-dispatch]",
                "match_operator": (
                    "contains_both_literal_tokens_after_unicode_nfc"
                ),
                "rule_version": (
                    "continuous_002_formal_dispatch_title_marker_v0.1.0"
                ),
            },
            "project_scope": {
                "candidate_run_id": "continuous-002",
                "pagination_complete": True,
                "project_locator": project_locator,
                "resource_kinds": [
                    "task_thread",
                ],
                "scope_kind": (
                    "current_authenticated_account_current_project"
                ),
                "states_requested": [
                    "active",
                    "archived",
                ],
            },
            "provider": "openai_codex",
            "query_completed_at": utc_text(completed),
            "query_started_at": utc_text(started),
            "result_summary": {
                "matching_formal_dispatch_object_count": 0,
                "normalized_listing_sha256": listing_digest,
                "visible_object_count": len(normalized_listing),
            },
        },
        "instance_path": relative,
        "observer": {
            "attested_at": utc_text(attested),
            "identifier": "synthetic-custodian",
            "observation_basis": "direct_project_management_query",
            "role": "project_state_custodian",
        },
        "policy": template["policy"],
        "repository_absence_evidence": {
            "checked_at": utc_text(checked),
            "denylist_contract": fixture["denylist_reference"],
            "formal_run_delta_path": DELTA.as_posix(),
            "formal_run_delta_sha256": sha256_path(root / DELTA),
            "method": "frozen_b_absence_plus_append_only_history",
            "observed_head": observed_head,
            "post_b_history_status": "attestation_additions_only",
            "pre_b_scan_snapshot_sha256": fixture["scan_snapshot"],
            "status": "passed",
            "verifier_path": VERIFIER.as_posix(),
            "verifier_sha256": fixture["verifier_sha256"],
            "worktree_clean_before_query": True,
        },
        "validity": {
            "freshness_window_seconds": 600,
            "valid_from": utc_text(completed),
            "valid_until": utc_text(valid_until),
        },
    }
    return document, relative


def run_verifier(
    root: Path,
    command: str,
    fixture: dict[str, Any],
    *,
    relative: str | None = None,
    commit: str | None = None,
    isolated: bool = True,
    acknowledge_reads: bool = True,
    verifier_hash: str | None = None,
    expected_b: str | None = None,
    expected_root: str | None = None,
    caller_time_override: str | None = None,
    environment_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    arguments = [sys.executable]
    if isolated:
        arguments.append("-I")
    arguments.extend(
        [
            str(root / VERIFIER),
            command,
            "--repo-root",
            str(root),
            "--expected-verifier-sha256",
            verifier_hash or fixture["verifier_sha256"],
        ]
    )
    if acknowledge_reads:
        arguments.append(
            "--allow-repository-and-git-object-byte-reads"
        )
    if relative is not None:
        arguments.extend(["--attestation-path", relative])
    if command != "verify-template":
        arguments.extend(
            [
                "--expected-finalize-commit-b",
                expected_b or fixture["commit_b"],
                "--expected-frozen-artifact-set-digest",
                expected_root or fixture["frozen_root"],
            ]
        )
    if caller_time_override is not None:
        arguments.extend(
            ["--gate-presented-at", caller_time_override]
        )
    if commit is not None:
        arguments.extend(["--attestation-commit", commit])
    environment = None
    if environment_overrides is not None:
        environment = os.environ.copy()
        environment.update(environment_overrides)
    return subprocess.run(
        arguments,
        cwd=root,
        check=False,
        capture_output=True,
        env=environment,
        text=True,
        timeout=90,
    )


def require_success(
    completed: subprocess.CompletedProcess[str],
    *,
    label: str,
    status: str,
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
            f"{label} returned non-JSON stdout: {completed.stdout!r}"
        ) from error
    if result.get("status") != status:
        raise SelfTestFailure(f"{label} returned wrong status: {result!r}")
    return result


def require_failure(
    completed: subprocess.CompletedProcess[str],
    *,
    code: str,
    label: str,
) -> None:
    if completed.returncode != 1:
        raise SelfTestFailure(
            f"{label} returned {completed.returncode}: "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    try:
        result = json.loads(completed.stderr)
    except json.JSONDecodeError as error:
        raise SelfTestFailure(
            f"{label} returned non-JSON stderr: {completed.stderr!r}"
        ) from error
    if (
        result.get("status") != "failed_closed"
        or code not in result.get("error", "")
    ):
        raise SelfTestFailure(
            f"{label} returned the wrong failure: {result!r}"
        )


def add_and_commit(root: Path, relative: str, message: str) -> str:
    git(root, "add", "--", relative)
    git(root, "commit", "--quiet", "-m", message)
    return git(root, "rev-parse", "HEAD")


def non_git_fingerprint(root: Path) -> str:
    rows: list[tuple[str, str]] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if (
            not path.is_file()
            or (
                relative.parts
                and relative.parts[0].casefold() == ".git"
            )
        ):
            continue
        rows.append((relative.as_posix(), sha256_path(path)))
    rows.sort()
    return sha256_bytes(canonical_bytes(rows))


def fresh_case(
    source_root: Path,
    case_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    fixture = build_repository(source_root, case_root)
    document, relative = build_instance(
        case_root,
        fixture,
        observed_head=fixture["commit_b"],
        sequence=1,
    )
    write_json(case_root / Path(relative), document)
    return fixture, document, relative


def json_negative(
    source_root: Path,
    parent: Path,
    name: str,
    mutator: Callable[[dict[str, Any]], None],
    *,
    code: str,
    expected_b: str | None = None,
    expected_root: str | None = None,
) -> None:
    root = parent / name
    fixture, document, relative = fresh_case(source_root, root)
    mutator(document)
    write_json(root / Path(relative), document)
    require_failure(
        run_verifier(
            root,
            "verify-draft",
            fixture,
            relative=relative,
            expected_b=expected_b,
            expected_root=expected_root,
        ),
        code=code,
        label=name,
    )


def run_self_test(source_root: Path) -> dict[str, Any]:
    positives: list[str] = []
    negatives: list[str] = []
    with tempfile.TemporaryDirectory(
        prefix="game-primitives-external-attestation-"
    ) as directory:
        parent = Path(directory)
        root = parent / "positive"
        fixture = build_repository(source_root, root)
        template_result = require_success(
            run_verifier(root, "verify-template", fixture),
            label="empty template",
            status="template_verified",
        )
        template = json.loads((root / TEMPLATE).read_text(encoding="utf-8"))
        if (
            any(
                value is not None
                for value in template["dynamic_slots"].values()
            )
            or {"task_id", "thread_id", "session_id"}
            & set(template["dynamic_slots"])
        ):
            raise SelfTestFailure("template contains runtime identifiers")
        positives.append("P01_TEMPLATE_SCHEMA_AND_EMPTY_SLOTS")

        first, first_relative = build_instance(
            root,
            fixture,
            observed_head=fixture["commit_b"],
            sequence=1,
        )
        write_json(root / Path(first_relative), first)
        require_success(
            run_verifier(
                root,
                "verify-draft",
                fixture,
                relative=first_relative,
            ),
            label="initial draft",
            status="draft_verified",
        )
        positives.append("P02_INITIAL_DRAFT")
        first_commit = add_and_commit(
            root,
            first_relative,
            "append first synthetic attestation",
        )
        first_result = require_success(
            run_verifier(
                root,
                "verify-committed",
                fixture,
                relative=first_relative,
                commit=first_commit,
            ),
            label="initial committed attestation",
            status="committed_attestation_verified",
        )
        positives.append("P03_INITIAL_COMMITTED")

        second, second_relative = build_instance(
            root,
            fixture,
            observed_head=first_commit,
            sequence=2,
        )
        write_json(root / Path(second_relative), second)
        require_success(
            run_verifier(
                root,
                "verify-draft",
                fixture,
                relative=second_relative,
            ),
            label="subsequent draft",
            status="draft_verified",
        )
        positives.append("P04_SUBSEQUENT_DRAFT")
        second_commit = add_and_commit(
            root,
            second_relative,
            "append second synthetic attestation",
        )
        before = non_git_fingerprint(root)
        second_result = require_success(
            run_verifier(
                root,
                "verify-committed",
                fixture,
                relative=second_relative,
                commit=second_commit,
            ),
            label="subsequent committed attestation",
            status="committed_attestation_verified",
        )
        after = non_git_fingerprint(root)
        positives.append("P05_SUBSEQUENT_COMMITTED")
        repeat = require_success(
            run_verifier(
                root,
                "verify-committed",
                fixture,
                relative=second_relative,
                commit=second_commit,
            ),
            label="deterministic repeat",
            status="committed_attestation_verified",
        )
        if (
            before != after
            or second_result != repeat
            or template_result.get("actual_dispatch_performed") is not False
            or first_result.get("external_query_performed") is not False
            or second_result.get("runner_or_comparator_executed")
            is not False
        ):
            raise SelfTestFailure(
                "verifier was not deterministic, read-only, or inert"
            )
        positives.append(
            "P06_DETERMINISTIC_READ_ONLY_NO_EXTERNAL_ACTION"
        )

        fsmonitor_root = parent / "hostile-fsmonitor"
        fsmonitor_fixture = build_repository(source_root, fsmonitor_root)
        fsmonitor_marker = fsmonitor_root / "fsmonitor-ran.txt"
        fsmonitor_hook = fsmonitor_root / ".git" / "malicious-fsmonitor"
        quoted_marker = fsmonitor_marker.as_posix().replace(
            "'",
            "'\"'\"'",
        )
        fsmonitor_hook.write_text(
            "#!/bin/sh\n"
            f"printf touched > '{quoted_marker}'\n"
            "printf '\\n'\n",
            encoding="utf-8",
            newline="\n",
        )
        fsmonitor_hook.chmod(0o755)
        git(
            fsmonitor_root,
            "config",
            "core.fsmonitor",
            fsmonitor_hook.as_posix(),
        )
        fsmonitor_document, fsmonitor_relative = build_instance(
            fsmonitor_root,
            fsmonitor_fixture,
            observed_head=fsmonitor_fixture["commit_b"],
            sequence=1,
        )
        write_json(
            fsmonitor_root / Path(fsmonitor_relative),
            fsmonitor_document,
        )
        require_success(
            run_verifier(
                fsmonitor_root,
                "verify-draft",
                fsmonitor_fixture,
                relative=fsmonitor_relative,
            ),
            label="hostile fsmonitor disabled",
            status="draft_verified",
        )
        if fsmonitor_marker.exists():
            raise SelfTestFailure("repository fsmonitor command executed")
        positives.append("P07_HOSTILE_FSMONITOR_DISABLED")

        case_root = parent / "cli-isolation"
        cli_fixture = build_repository(source_root, case_root)
        require_failure(
            run_verifier(
                case_root,
                "verify-template",
                cli_fixture,
                isolated=False,
            ),
            code="ISOLATED_INTERPRETER_REQUIRED",
            label="non-isolated CLI",
        )
        negatives.append("N-CLI01_ISOLATED_REQUIRED")
        require_failure(
            run_verifier(
                case_root,
                "verify-template",
                cli_fixture,
                acknowledge_reads=False,
            ),
            code="REPOSITORY_BYTE_READ_ACK_REQUIRED",
            label="missing byte-read acknowledgement",
        )
        negatives.append("N-CLI02_BYTE_READ_ACK_REQUIRED")
        require_failure(
            run_verifier(
                case_root,
                "verify-template",
                cli_fixture,
                caller_time_override="2000-01-01T00:00:00Z",
            ),
            code="CALLER_TIME_OVERRIDE_FORBIDDEN",
            label="caller supplied verification time",
        )
        negatives.append("N-CLI03_CALLER_TIME_OVERRIDE_FORBIDDEN")

        require_failure(
            run_verifier(
                case_root,
                "verify-template",
                cli_fixture,
                environment_overrides={
                    "GIT_DIR": str(case_root / ".git")
                },
            ),
            code="GIT_ENVIRONMENT_OVERRIDE",
            label="ambient GIT_DIR override",
        )
        negatives.append("N-GIT01_AMBIENT_GIT_DIR")

        replace_root = parent / "replace-ref"
        replace_fixture = build_repository(source_root, replace_root)
        git(
            replace_root,
            "replace",
            replace_fixture["commit_b"],
            replace_fixture["commit_a"],
        )
        require_failure(
            run_verifier(
                replace_root,
                "verify-template",
                replace_fixture,
            ),
            code="GIT_REPLACE_REFS_PRESENT",
            label="Git replace ref",
        )
        negatives.append("N-GIT02_REPLACE_REF")

        graft_root = parent / "legacy-graft"
        graft_fixture = build_repository(source_root, graft_root)
        graft_path = graft_root / ".git" / "info" / "grafts"
        graft_path.parent.mkdir(parents=True, exist_ok=True)
        graft_path.write_bytes(
            (
                f"{graft_fixture['commit_b']} "
                f"{graft_fixture['commit_a']}\n"
            ).encode("ascii")
        )
        require_failure(
            run_verifier(
                graft_root,
                "verify-template",
                graft_fixture,
            ),
            code="GIT_GRAFTS_PRESENT",
            label="legacy Git graft",
        )
        negatives.append("N-GIT03_LEGACY_GRAFT")

        alternate_root = parent / "object-alternates"
        alternate_fixture = build_repository(source_root, alternate_root)
        alternates_path = (
            alternate_root / ".git" / "objects" / "info" / "alternates"
        )
        alternates_path.parent.mkdir(parents=True, exist_ok=True)
        alternates_path.write_text(
            str(alternate_root / ".git" / "objects") + "\n",
            encoding="utf-8",
            newline="\n",
        )
        require_failure(
            run_verifier(
                alternate_root,
                "verify-template",
                alternate_fixture,
            ),
            code="GIT_OBJECT_ALTERNATES_PRESENT",
            label="Git object alternates",
        )
        negatives.append("N-GIT04_OBJECT_ALTERNATES")

        for filter_kind, control_id in (
            ("clean", "N-GIT05_CLEAN_FILTER"),
            ("process", "N-GIT06_PROCESS_FILTER"),
        ):
            filter_root = parent / f"hostile-{filter_kind}-filter"
            filter_fixture = build_repository(source_root, filter_root)
            filter_marker = filter_root / f"{filter_kind}-filter-ran.txt"
            filter_command = (
                f"printf touched > '{filter_marker.as_posix()}'"
            )
            git(
                filter_root,
                "config",
                f"filter.hostile.{filter_kind}",
                filter_command,
            )
            require_failure(
                run_verifier(
                    filter_root,
                    "verify-template",
                    filter_fixture,
                ),
                code="GIT_EXTERNAL_FILTER_CONFIG",
                label=f"hostile {filter_kind} filter",
            )
            if filter_marker.exists():
                raise SelfTestFailure(
                    f"repository {filter_kind} filter command executed"
                )
            negatives.append(control_id)

        promisor_root = parent / "partial-promisor-config"
        promisor_fixture = build_repository(source_root, promisor_root)
        git(
            promisor_root,
            "config",
            "remote.origin.promisor",
            "true",
        )
        git(
            promisor_root,
            "config",
            "remote.origin.partialCloneFilter",
            "blob:none",
        )
        require_failure(
            run_verifier(
                promisor_root,
                "verify-template",
                promisor_fixture,
            ),
            code="GIT_PARTIAL_CLONE_CONFIG",
            label="partial/promisor Git configuration",
        )
        negatives.append("N-GIT07_PARTIAL_PROMISOR_CONFIG")

        schema_root = parent / "schema-tamper"
        schema_fixture = build_repository(source_root, schema_root)
        (schema_root / SCHEMA).write_bytes(
            (schema_root / SCHEMA).read_bytes() + b" "
        )
        require_failure(
            run_verifier(schema_root, "verify-template", schema_fixture),
            code="TRUSTED_SCHEMA_HASH_MISMATCH",
            label="Schema tamper",
        )
        negatives.append("N-TRUST01_SCHEMA_TAMPER")

        template_root = parent / "template-tamper"
        template_fixture = build_repository(source_root, template_root)
        (template_root / TEMPLATE).write_bytes(
            (template_root / TEMPLATE).read_bytes() + b" "
        )
        require_failure(
            run_verifier(
                template_root,
                "verify-template",
                template_fixture,
            ),
            code="TRUSTED_TEMPLATE_HASH_MISMATCH",
            label="template tamper",
        )
        negatives.append("N-TRUST02_TEMPLATE_TAMPER")

        bom_root = parent / "instance-bom"
        bom_fixture, bom_document, bom_relative = fresh_case(
            source_root,
            bom_root,
        )
        (bom_root / Path(bom_relative)).write_bytes(
            b"\xef\xbb\xbf" + canonical_bytes(bom_document)
        )
        require_failure(
            run_verifier(
                bom_root,
                "verify-draft",
                bom_fixture,
                relative=bom_relative,
            ),
            code="JSON_BYTES_BOM",
            label="instance BOM",
        )
        negatives.append("N-BYTES01_INSTANCE_BOM")

        crlf_root = parent / "instance-crlf"
        crlf_fixture, crlf_document, crlf_relative = fresh_case(
            source_root,
            crlf_root,
        )
        (crlf_root / Path(crlf_relative)).write_bytes(
            canonical_bytes(crlf_document).replace(b"\n", b"\r\n")
        )
        require_failure(
            run_verifier(
                crlf_root,
                "verify-draft",
                crlf_fixture,
                relative=crlf_relative,
            ),
            code="JSON_BYTES_NONCANONICAL",
            label="instance CRLF",
        )
        negatives.append("N-BYTES02_INSTANCE_CRLF")

        duplicate_root = parent / "instance-duplicate-key"
        duplicate_fixture, duplicate_document, duplicate_relative = fresh_case(
            source_root,
            duplicate_root,
        )
        duplicate_raw = canonical_bytes(duplicate_document)
        duplicate_needle = (
            b'  "artifact_type": "external_dispatch_attestation",\n'
        )
        if duplicate_raw.count(duplicate_needle) != 1:
            raise SelfTestFailure("duplicate-key fixture needle drifted")
        (duplicate_root / Path(duplicate_relative)).write_bytes(
            duplicate_raw.replace(
                duplicate_needle,
                duplicate_needle + duplicate_needle,
                1,
            )
        )
        require_failure(
            run_verifier(
                duplicate_root,
                "verify-draft",
                duplicate_fixture,
                relative=duplicate_relative,
            ),
            code="JSON_DUPLICATE_KEY",
            label="instance duplicate key",
        )
        negatives.append("N-BYTES03_INSTANCE_DUPLICATE_KEY")

        nonfinite_root = parent / "instance-nonfinite"
        nonfinite_fixture, nonfinite_document, nonfinite_relative = fresh_case(
            source_root,
            nonfinite_root,
        )
        nonfinite_raw = canonical_bytes(nonfinite_document)
        nonfinite_needle = b'      "visible_object_count": 1\n'
        if nonfinite_raw.count(nonfinite_needle) != 1:
            raise SelfTestFailure("nonfinite fixture needle drifted")
        (nonfinite_root / Path(nonfinite_relative)).write_bytes(
            nonfinite_raw.replace(
                nonfinite_needle,
                b'      "visible_object_count": NaN\n',
                1,
            )
        )
        require_failure(
            run_verifier(
                nonfinite_root,
                "verify-draft",
                nonfinite_fixture,
                relative=nonfinite_relative,
            ),
            code="JSON_NONFINITE_NUMBER",
            label="instance nonfinite number",
        )
        negatives.append("N-BYTES04_INSTANCE_NONFINITE")

        json_negative(
            source_root,
            parent,
            "expected-b-mismatch",
            lambda value: None,
            code="EXPECTED_COMMIT_B_MISMATCH",
            expected_b="c" * 40,
        )
        negatives.append("N-ANCHOR01_EXPECTED_B_MISMATCH")
        json_negative(
            source_root,
            parent,
            "expected-root-mismatch",
            lambda value: None,
            code="EXPECTED_FROZEN_ROOT_MISMATCH",
            expected_root="c" * 64,
        )
        negatives.append("N-ANCHOR02_EXPECTED_ROOT_MISMATCH")

        json_negative(
            source_root,
            parent,
            "wrong-finalize-b",
            lambda value: value["commit_binding"].update(
                {"finalize_commit_b": value["commit_binding"][
                    "freeze_anchor_commit_a"
                ]}
            ),
            code="EXPECTED_COMMIT_B_MISMATCH",
        )
        negatives.append("N-COMMIT01_WRONG_FINALIZE_B")
        json_negative(
            source_root,
            parent,
            "frozen-root-drift",
            lambda value: value["commit_binding"].update(
                {"frozen_artifact_set_digest": "c" * 64}
            ),
            code="FROZEN_ROOT_BINDING",
            expected_root="c" * 64,
        )
        negatives.append("N-COMMIT02_FROZEN_ROOT_DRIFT")
        json_negative(
            source_root,
            parent,
            "manifest-hash-drift",
            lambda value: value["commit_binding"].update(
                {"frozen_manifest_sha256": "c" * 64}
            ),
            code="FROZEN_ROOT_BINDING",
        )
        negatives.append("N-COMMIT03_MANIFEST_HASH_DRIFT")
        json_negative(
            source_root,
            parent,
            "delta-hash-drift",
            lambda value: value["repository_absence_evidence"].update(
                {"formal_run_delta_sha256": "c" * 64}
            ),
            code="DELTA_HASH_BINDING",
        )
        negatives.append("N-DELTA01_DELTA_HASH_DRIFT")
        json_negative(
            source_root,
            parent,
            "denylist-hash-drift",
            lambda value: value["repository_absence_evidence"][
                "denylist_contract"
            ].update({"sha256": "c" * 64}),
            code="DELTA_EVIDENCE_BINDING",
        )
        negatives.append("N-DENY01_DENYLIST_HASH_DRIFT")

        head_root = parent / "draft-head-drift"
        head_fixture, _, head_relative = fresh_case(
            source_root,
            head_root,
        )
        extra = head_root / "notes/ordinary.txt"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_bytes(b"ordinary\n")
        add_and_commit(head_root, "notes/ordinary.txt", "ordinary commit")
        require_failure(
            run_verifier(
                head_root,
                "verify-draft",
                head_fixture,
                relative=head_relative,
            ),
            code="DRAFT_HEAD",
            label="draft head drift",
        )
        negatives.append("N-HEAD01_DRAFT_HEAD_DRIFT")

        history_root = parent / "ordinary-post-b"
        history_fixture = build_repository(source_root, history_root)
        ordinary = history_root / "notes/ordinary.txt"
        ordinary.parent.mkdir(parents=True, exist_ok=True)
        ordinary.write_bytes(b"ordinary\n")
        ordinary_commit = add_and_commit(
            history_root,
            "notes/ordinary.txt",
            "ordinary post-B commit",
        )
        history_document, history_relative = build_instance(
            history_root,
            history_fixture,
            observed_head=ordinary_commit,
            sequence=2,
        )
        write_json(
            history_root / Path(history_relative),
            history_document,
        )
        require_failure(
            run_verifier(
                history_root,
                "verify-draft",
                history_fixture,
                relative=history_relative,
            ),
            code="HISTORY_DELTA",
            label="ordinary post-B history",
        )
        negatives.append("N-HISTORY01_ORDINARY_POST_B_COMMIT")

        invalid_prior_root = parent / "invalid-prior"
        invalid_prior_fixture = build_repository(
            source_root,
            invalid_prior_root,
        )
        invalid_prior, invalid_prior_relative = build_instance(
            invalid_prior_root,
            invalid_prior_fixture,
            observed_head=invalid_prior_fixture["commit_b"],
            sequence=1,
        )
        invalid_prior["external_query"]["capability_limits"][
            "dispatch"
        ] = True
        write_json(
            invalid_prior_root / Path(invalid_prior_relative),
            invalid_prior,
        )
        invalid_prior_commit = add_and_commit(
            invalid_prior_root,
            invalid_prior_relative,
            "append invalid prior proof",
        )
        after_invalid, after_invalid_relative = (
            build_instance(
                invalid_prior_root,
                invalid_prior_fixture,
                observed_head=invalid_prior_commit,
                sequence=2,
            )
        )
        write_json(
            invalid_prior_root / Path(after_invalid_relative),
            after_invalid,
        )
        require_failure(
            run_verifier(
                invalid_prior_root,
                "verify-draft",
                invalid_prior_fixture,
                relative=after_invalid_relative,
            ),
            code="SCHEMA_VALIDATION",
            label="invalid prior attestation",
        )
        negatives.append("N-HISTORY02_INVALID_PRIOR_ATTESTATION")

        merge_root = parent / "merge-post-b"
        merge_fixture = build_repository(source_root, merge_root)
        main_branch = git(merge_root, "branch", "--show-current")
        git(
            merge_root,
            "checkout",
            "--quiet",
            "-b",
            "synthetic-side",
            merge_fixture["commit_a"],
        )
        side_path = merge_root / "notes" / "side.txt"
        side_path.parent.mkdir(parents=True, exist_ok=True)
        side_path.write_bytes(b"side\n")
        add_and_commit(
            merge_root,
            "notes/side.txt",
            "synthetic side commit",
        )
        git(merge_root, "checkout", "--quiet", main_branch)
        git(
            merge_root,
            "merge",
            "--quiet",
            "--no-ff",
            "synthetic-side",
            "-m",
            "synthetic non-linear merge",
        )
        merge_head = git(merge_root, "rev-parse", "HEAD")
        merge_document, merge_relative = build_instance(
            merge_root,
            merge_fixture,
            observed_head=merge_head,
            sequence=2,
        )
        write_json(merge_root / Path(merge_relative), merge_document)
        require_failure(
            run_verifier(
                merge_root,
                "verify-draft",
                merge_fixture,
                relative=merge_relative,
            ),
            code="HISTORY_PARENT",
            label="non-linear post-B merge",
        )
        negatives.append("N-HISTORY03_MERGE_POST_B_COMMIT")

        multi_root = parent / "multi-file-save"
        multi_fixture, _, multi_relative = fresh_case(
            source_root,
            multi_root,
        )
        multi_extra = multi_root / "notes/extra.txt"
        multi_extra.parent.mkdir(parents=True, exist_ok=True)
        multi_extra.write_bytes(b"extra\n")
        git(
            multi_root,
            "add",
            "--",
            multi_relative,
            "notes/extra.txt",
        )
        git(
            multi_root,
            "commit",
            "--quiet",
            "-m",
            "invalid multi-file save",
        )
        multi_commit = git(multi_root, "rev-parse", "HEAD")
        require_failure(
            run_verifier(
                multi_root,
                "verify-committed",
                multi_fixture,
                relative=multi_relative,
                commit=multi_commit,
            ),
            code="SAVE_COMMIT_DELTA",
            label="multi-file save commit",
        )
        negatives.append("N-SAVE01_MULTI_FILE_COMMIT")

        overwrite_root = parent / "overwrite-old"
        overwrite_fixture, overwrite_document, overwrite_relative = (
            fresh_case(source_root, overwrite_root)
        )
        first_overwrite_commit = add_and_commit(
            overwrite_root,
            overwrite_relative,
            "first proof",
        )
        overwrite_document["observer"]["identifier"] = (
            "modified-custodian"
        )
        write_json(
            overwrite_root / Path(overwrite_relative),
            overwrite_document,
        )
        git(overwrite_root, "add", "--", overwrite_relative)
        git(
            overwrite_root,
            "commit",
            "--quiet",
            "-m",
            "invalid proof overwrite",
        )
        overwrite_commit = git(overwrite_root, "rev-parse", "HEAD")
        if overwrite_commit == first_overwrite_commit:
            raise SelfTestFailure("overwrite commit did not advance")
        require_failure(
            run_verifier(
                overwrite_root,
                "verify-committed",
                overwrite_fixture,
                relative=overwrite_relative,
                commit=overwrite_commit,
            ),
            code="SAVE_COMMIT_PARENT",
            label="old proof overwrite",
        )
        negatives.append("N-SAVE02_OVERWRITE_OLD_ATTESTATION")

        stale_root = parent / "stale-proof"
        stale_fixture, _, stale_relative = fresh_case(
            source_root,
            stale_root,
        )
        stale_commit = add_and_commit(
            stale_root,
            stale_relative,
            "valid proof",
        )
        stale_extra = stale_root / "notes/later.txt"
        stale_extra.parent.mkdir(parents=True, exist_ok=True)
        stale_extra.write_bytes(b"later\n")
        add_and_commit(stale_root, "notes/later.txt", "later commit")
        require_failure(
            run_verifier(
                stale_root,
                "verify-committed",
                stale_fixture,
                relative=stale_relative,
                commit=stale_commit,
            ),
            code="LATEST_ATTESTATION_COMMIT",
            label="stale attestation commit",
        )
        negatives.append("N-LATEST01_STALE_ATTESTATION_COMMIT")

        json_negative(
            source_root,
            parent,
            "sequence-drift",
            lambda value: value["commit_binding"].update({"sequence": 2}),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-SEQ01_SEQUENCE_DRIFT")
        json_negative(
            source_root,
            parent,
            "previous-drift",
            lambda value: value["commit_binding"].update(
                {
                    "observed_head_relation": (
                        "attestation_only_descendant_of_finalize_commit_b"
                    ),
                    "previous_attestation_commit": "c" * 40,
                    "sequence": 2,
                }
            ),
            code="ATTESTATION_SEQUENCE",
        )
        negatives.append("N-SEQ02_PREVIOUS_COMMIT_DRIFT")
        json_negative(
            source_root,
            parent,
            "reversed-query",
            lambda value: value["external_query"].update(
                {
                    "query_started_at": shift_utc(
                        value["external_query"]["query_completed_at"],
                        10,
                    )
                }
            ),
            code="TIME_ORDER",
        )
        negatives.append("N-TIME01_REVERSED_QUERY")
        json_negative(
            source_root,
            parent,
            "stale-absence",
            lambda value: value["repository_absence_evidence"].update(
                {
                    "checked_at": shift_utc(
                        value["external_query"]["query_started_at"],
                        -121,
                    )
                }
            ),
            code="ABSENCE_EVIDENCE_STALE",
        )
        negatives.append("N-TIME02_STALE_ABSENCE")
        json_negative(
            source_root,
            parent,
            "query-too-long",
            lambda value: (
                value["repository_absence_evidence"].update(
                    {
                        "checked_at": shift_utc(
                            value["external_query"]["query_completed_at"],
                            -131,
                        )
                    }
                ),
                value["external_query"].update(
                    {
                        "query_started_at": shift_utc(
                            value["external_query"]["query_completed_at"],
                            -121,
                        )
                    }
                ),
            ),
            code="QUERY_DURATION",
        )
        negatives.append("N-TIME03_QUERY_TOO_LONG")
        expired_root = parent / "expired-verifier-time"
        expired_fixture = build_repository(source_root, expired_root)
        expired_fixture["clock_base"] = datetime.now(
            timezone.utc
        ).replace(microsecond=0) - timedelta(seconds=900)
        expired_document, expired_relative = build_instance(
            expired_root,
            expired_fixture,
            observed_head=expired_fixture["commit_b"],
            sequence=1,
        )
        write_json(expired_root / Path(expired_relative), expired_document)
        require_failure(
            run_verifier(
                expired_root,
                "verify-draft",
                expired_fixture,
                relative=expired_relative,
            ),
            code="ATTESTATION_EXPIRED",
            label="expired verifier time",
        )
        negatives.append("N-TIME04_GATE_EXPIRED")
        json_negative(
            source_root,
            parent,
            "global-scope",
            lambda value: value["conclusion"].update(
                {"global_absence_claimed": True}
            ),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-SCOPE01_GLOBAL_SCOPE")
        json_negative(
            source_root,
            parent,
            "absolute-dispatch-claim",
            lambda value: (
                value["conclusion"].pop(
                    "matching_formal_dispatch_object_observed"
                ),
                value["conclusion"].update(
                    {"formal_dispatch_performed": False}
                ),
            ),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-SCOPE02_ABSOLUTE_DISPATCH_CLAIM")
        json_negative(
            source_root,
            parent,
            "dispatch-capability",
            lambda value: value["external_query"][
                "capability_limits"
            ].update({"dispatch": True}),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-CAP01_DISPATCH_CAPABILITY")
        json_negative(
            source_root,
            parent,
            "session-inventory",
            lambda value: value["external_query"][
                "capability_limits"
            ].update({"standalone_session_inventory": True}),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-CAP02_SESSION_INVENTORY_CLAIM")
        json_negative(
            source_root,
            parent,
            "match-rule-drift",
            lambda value: value["external_query"]["matching_rule"].update(
                {"formal_dispatch_marker": "[other-marker]"}
            ),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-QUERY01_MATCH_RULE_DRIFT")
        json_negative(
            source_root,
            parent,
            "listing-contract-drift",
            lambda value: value["external_query"][
                "listing_contract"
            ].update({"normalization_version": "unfrozen-version"}),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-QUERY02_LISTING_CONTRACT_DRIFT")
        json_negative(
            source_root,
            parent,
            "matching-object",
            lambda value: value["external_query"]["result_summary"].update(
                {"matching_formal_dispatch_object_count": 1}
            ),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-RESULT01_MATCHING_OBJECT")
        json_negative(
            source_root,
            parent,
            "id-digest-drift",
            lambda value: value.update(
                {
                    "attestation_id": (
                        value["attestation_id"][:-12] + "c" * 12
                    )
                }
            ),
            code="ATTESTATION_ID",
        )
        negatives.append("N-ID01_ID_DIGEST_DRIFT")

        dirty_root = parent / "extra-dirty"
        dirty_fixture, _, dirty_relative = fresh_case(
            source_root,
            dirty_root,
        )
        dirty_extra = dirty_root / "notes/extra.txt"
        dirty_extra.parent.mkdir(parents=True, exist_ok=True)
        dirty_extra.write_bytes(b"extra\n")
        require_failure(
            run_verifier(
                dirty_root,
                "verify-draft",
                dirty_fixture,
                relative=dirty_relative,
            ),
            code="DRAFT_WORKTREE",
            label="extra dirty path",
        )
        negatives.append("N-WORKTREE01_EXTRA_DIRTY_PATH")

        verifier_root = parent / "verifier-trust"
        verifier_fixture = build_repository(source_root, verifier_root)
        require_failure(
            run_verifier(
                verifier_root,
                "verify-template",
                verifier_fixture,
                verifier_hash="c" * 64,
            ),
            code="VERIFIER_HASH_MISMATCH",
            label="verifier trust root drift",
        )
        negatives.append("N-VERIFIER01_TRUST_ROOT_DRIFT")

        json_negative(
            source_root,
            parent,
            "instance-path-drift",
            lambda value: value.update(
                {
                    "instance_path": (
                        ATTESTATION_DIRECTORY / "different.json"
                    ).as_posix()
                }
            ),
            code="SCHEMA_VALIDATION",
        )
        negatives.append("N-PATH01_INSTANCE_PATH_DRIFT")

        if tuple(positives) != EXPECTED_POSITIVE_IDS:
            raise SelfTestFailure(
                f"positive control set drifted: {positives!r}"
            )
        if tuple(negatives) != EXPECTED_NEGATIVE_IDS:
            raise SelfTestFailure(
                f"negative control set drifted: {negatives!r}"
            )
        return {
            "external_query_performed": False,
            "formal_input_access": False,
            "negative_controls": negatives,
            "negative_controls_passed": len(negatives),
            "positive_controls": positives,
            "positive_controls_passed": len(positives),
            "runner_or_comparator_executed": False,
            "status": "synthetic_self_test_passed",
            "temporary_repository_only": True,
        }


def main() -> int:
    source_root = Path.cwd().resolve()
    try:
        result = run_self_test(source_root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        KeyError,
        OSError,
        SelfTestFailure,
        subprocess.SubprocessError,
        TypeError,
        ValueError,
    ) as error:
        print(
            json.dumps(
                {
                    "error": str(error),
                    "external_query_performed": False,
                    "formal_input_access": False,
                    "runner_or_comparator_executed": False,
                    "status": "synthetic_self_test_failed",
                    "temporary_repository_only": True,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
