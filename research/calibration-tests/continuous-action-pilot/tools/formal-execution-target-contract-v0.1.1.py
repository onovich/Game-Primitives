"""Single path/role contract for continuous-002 formal execution targets.

This module is data only. Formal permit materialization and fixture-lock
assembly both import it so that the executable surface cannot drift between
the two gates. Raw-trace schemas are permit-bound but intentionally excluded
from the fixture lock because they live outside the run directory.

This 0.1.1 reissue is deliberately round-bound. It replaces the prior run root
and the three raw-trace Schema paths without generalizing the contract into a
cross-round profile.
"""

from __future__ import annotations

from typing import Any


CONTRACT_VERSION = "0.1.1"
RUN_ID = "continuous-002"
CASES = ("CA-R1", "CA-R2", "CA-R3")
BASE = "research/calibration-tests/continuous-action-pilot"
RUN = f"{BASE}/runs/{RUN_ID}"
SCHEMA = f"{BASE}/schema"

RAW_TRACE_SCHEMA_PATHS = {
    "CA-R1": f"{SCHEMA}/ca-r1-raw-trace-0.1.1.schema.json",
    "CA-R2": f"{SCHEMA}/ca-r2-raw-trace-0.1.1.schema.json",
    "CA-R3": f"{SCHEMA}/ca-r3-raw-trace-0.1.1.schema.json",
}

EXECUTION_TARGET_PATHS: dict[str, dict[str, Any]] = {
    "CA-R1": {
        "comparator": f"{RUN}/fixtures/r1/compare-footsies-r1-v0.1.0.ps1",
        "formal_input": f"{RUN}/fixtures/r1/footsies-r1-formal-input-v0.1.0.json",
        "formal_runner": (
            f"{RUN}/fixtures/r1/"
            "run-footsies-r1-standalone-formal-v0.1.0.ps1"
        ),
        "raw_trace_schema": RAW_TRACE_SCHEMA_PATHS["CA-R1"],
        "support_artifacts": {
            "asset_loader": (
                f"{RUN}/fixtures/r1/standalone/UnityYamlAssetLoader.cs"
            ),
            "build_evidence": (
                f"{RUN}/fixtures/r1/r1-standalone-build-evidence-v0.1.0.json"
            ),
            "build_runner": (
                f"{RUN}/fixtures/r1/"
                "run-footsies-r1-standalone-build-smoke-v0.1.0.ps1"
            ),
            "build_readiness_verifier": (
                f"{RUN}/fixtures/r1/"
                "verify-r1-build-readiness-v0.1.0.py"
            ),
            "formal_project": (
                f"{RUN}/fixtures/r1/standalone/FootsiesR1Formal.csproj"
            ),
            "nuget_config": f"{RUN}/fixtures/r1/standalone/NuGet.config",
            "output_boundary": (
                f"{RUN}/fixtures/r1/"
                "r1-formal-output-boundary-v0.1.0.ps1"
            ),
            "process_boundary": (
                f"{RUN}/fixtures/r1/r1-process-boundary-v0.1.0.ps1"
            ),
            "source_contract": (
                f"{RUN}/fixtures/r1/standalone/FrozenSourceContract.cs"
            ),
            "unity_compatibility": (
                f"{RUN}/fixtures/r1/standalone/UnityCompatibility.cs"
            ),
            "variant_patch": (
                f"{RUN}/fixtures/r1/footsies-r1-whiff-cancel-v0.1.0.patch"
            ),
        },
        "test_body": f"{RUN}/fixtures/r1/standalone/FormalProgram.cs",
    },
    "CA-R2": {
        "comparator": f"{RUN}/fixtures/r2/compare-q3-formal-traces-v0.1.0.ps1",
        "formal_input": f"{RUN}/fixtures/r2/r2-formal-input-v0.1.0.json",
        "formal_runner": f"{RUN}/fixtures/r2/run-q3-formal-guarded-v0.1.0.ps1",
        "raw_trace_schema": RAW_TRACE_SCHEMA_PATHS["CA-R2"],
        "support_artifacts": {
            "build_readiness_evidence": (
                f"{RUN}/fixtures/r2/"
                "r2-build-readiness-evidence-v0.1.0.json"
            ),
            "build_readiness_verifier": (
                f"{RUN}/fixtures/r2/"
                "verify-r2-build-readiness-v0.1.0.py"
            ),
            "build_runner": (
                f"{RUN}/fixtures/r2/build-q3-formal-fixture-v0.1.0.ps1"
            ),
            "compatibility_patch": (
                f"{RUN}/fixtures/r2/q3-msvc-x64-compatibility-v0.1.0.patch"
            ),
            "compatibility_source": (
                f"{RUN}/fixtures/r2/q3-formal-compatibility-v0.1.0.c"
            ),
            "harness_header": (
                f"{RUN}/fixtures/r2/q3-formal-fixture-v0.1.0.h"
            ),
            "observation_patch": f"{RUN}/fixtures/r2/q3-observation-v0.1.0.patch",
            "variant_patch": (
                f"{RUN}/fixtures/r2/q3-entry-latch-variant-v0.1.0.patch"
            ),
        },
        "test_body": f"{RUN}/fixtures/r2/q3-formal-harness-v0.1.0.c",
    },
    "CA-R3": {
        "comparator": f"{RUN}/fixtures/r3/compare-osu-r3-formal-v0.1.0.ps1",
        "formal_input": f"{RUN}/fixtures/r3/formal-input-r3-v0.1.0.json",
        "formal_runner": f"{RUN}/fixtures/r3/run-osu-r3-formal-v0.1.0.ps1",
        "raw_trace_schema": RAW_TRACE_SCHEMA_PATHS["CA-R3"],
        "support_artifacts": {
            "build_list_evidence": (
                f"{RUN}/fixtures/r3/r3-build-list-evidence-v0.1.0.json"
            ),
            "build_runner": (
                f"{RUN}/fixtures/r3/run-osu-r3-build-list-v0.1.0.ps1"
            ),
            "dependency_lock_set": (
                f"{RUN}/fixtures/r3/dependency-lock-set-v0.1.0.json"
            ),
            "deterministic_build_targets": (
                f"{RUN}/fixtures/r3/"
                "r3-deterministic-build-v0.1.0.targets"
            ),
            "fixture_spec": f"{RUN}/fixtures/r3/r3-fixture-spec-v0.1.0.json",
            "safety_guards": (
                f"{RUN}/fixtures/r3/r3-safety-guards-v0.1.0.ps1"
            ),
        },
        "test_body": f"{RUN}/fixtures/r3/TestSceneGamePrimitivesR3.cs",
    },
}

# Exact fields reject both missing and additional execution-surface artifacts.
# preparation_probe_artifacts is a required closure because neutral probes and
# the generated final build-readiness reference are legitimate extra evidence.
LOCK_EXACT_ROLE_PLACEMENTS = {
    "CA-R1": {
        "comparator_artifacts": ("comparator",),
        "compatibility_patch_set.artifacts": (),
        "compatibility_patch_set.configuration_artifacts": (),
        "fixture_artifacts": (
            "formal_runner",
            "test_body",
            "support.asset_loader",
            "support.build_runner",
            "support.formal_project",
            "support.nuget_config",
            "support.output_boundary",
            "support.process_boundary",
            "support.source_contract",
            "support.unity_compatibility",
        ),
        "formal_input_artifacts": ("formal_input",),
        "observation_patch_set.artifacts": (),
        "observation_patch_set.configuration_artifacts": (),
        "variant_patch_set.artifacts": ("support.variant_patch",),
        "variant_patch_set.configuration_artifacts": (),
    },
    "CA-R2": {
        "comparator_artifacts": ("comparator",),
        "compatibility_patch_set.artifacts": ("support.compatibility_patch",),
        "compatibility_patch_set.configuration_artifacts": (),
        "fixture_artifacts": (
            "formal_runner",
            "test_body",
            "support.build_runner",
            "support.compatibility_source",
            "support.harness_header",
        ),
        "formal_input_artifacts": ("formal_input",),
        "observation_patch_set.artifacts": ("support.observation_patch",),
        "observation_patch_set.configuration_artifacts": (),
        "variant_patch_set.artifacts": ("support.variant_patch",),
        "variant_patch_set.configuration_artifacts": (),
    },
    "CA-R3": {
        "comparator_artifacts": ("comparator",),
        "compatibility_patch_set.artifacts": (),
        "compatibility_patch_set.configuration_artifacts": (),
        "fixture_artifacts": (
            "formal_runner",
            "test_body",
            "support.build_runner",
            "support.dependency_lock_set",
            "support.deterministic_build_targets",
            "support.fixture_spec",
            "support.safety_guards",
        ),
        "formal_input_artifacts": ("formal_input",),
        "observation_patch_set.artifacts": ("test_body",),
        "observation_patch_set.configuration_artifacts": (),
        "variant_patch_set.artifacts": (),
        "variant_patch_set.configuration_artifacts": ("support.fixture_spec",),
    },
}

LOCK_REQUIRED_ROLE_PLACEMENTS = {
    "CA-R1": {
        "preparation_probe_artifacts": (
            "support.build_evidence",
            "support.build_readiness_verifier",
        ),
    },
    "CA-R2": {
        "preparation_probe_artifacts": (
            "support.build_readiness_evidence",
            "support.build_readiness_verifier",
        ),
    },
    "CA-R3": {
        "preparation_probe_artifacts": ("support.build_list_evidence",),
    },
}

BUILD_READINESS_IDENTITIES = {
    "CA-R1": {
        "config.baseline": {
            "build_attempt_ids": (
                "build.ca-r1.standalone-reproducible.baseline",
            ),
            "output_ids": ("output.ca-r1.baseline-formal-assembly",),
        },
        "config.variant": {
            "build_attempt_ids": (
                "build.ca-r1.standalone-reproducible.variant",
            ),
            "output_ids": ("output.ca-r1.variant-formal-assembly",),
        },
    },
    "CA-R2": {
        "config.baseline": {
            "build_attempt_ids": (
                "build.ca-r2.binding-selftest-20260727-02.baseline",
            ),
            "output_ids": ("output.ca-r2.baseline-executable",),
        },
        "config.variant": {
            "build_attempt_ids": (
                "build.ca-r2.binding-selftest-20260727-02.variant",
            ),
            "output_ids": ("output.ca-r2.variant-executable",),
        },
    },
    "CA-R3": {
        "config.baseline": {
            "build_attempt_ids": (
                "build.ca-r3.formal-prep-replay-a",
                "build.ca-r3.formal-prep-replay-b",
            ),
            "output_ids": ("output.ca-r3.osu-tests-assembly",),
        },
        "config.variant": {
            "build_attempt_ids": (
                "build.ca-r3.formal-prep-replay-a",
                "build.ca-r3.formal-prep-replay-b",
            ),
            "output_ids": ("output.ca-r3.osu-tests-assembly",),
        },
    },
}


def resolve_target_role(case_id: str, role: str) -> str:
    target = EXECUTION_TARGET_PATHS[case_id]
    if role.startswith("support."):
        return target["support_artifacts"][role.removeprefix("support.")]
    return target[role]


def expected_lock_paths(
    case_id: str,
    placements: dict[str, tuple[str, ...]],
) -> dict[str, tuple[str, ...]]:
    return {
        field: tuple(resolve_target_role(case_id, role) for role in roles)
        for field, roles in placements.items()
    }
