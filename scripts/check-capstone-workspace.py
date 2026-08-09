#!/usr/bin/env python3
"""Apply public contracts to a learner copy without changing it."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from capstone.oracle import (  # noqa: E402
    canonical_trace_digest,
    check_invariants,
    check_scenario_evidence,
    validate_trace,
)


REQUIRED_DESIGN = (
    "system-model.md", "sequential-spec.md", "invariants.md", "liveness.md",
    "trace-format.md", "membership-review.md", "sharding-review.md",
)
EXPECTED = json.loads(
    (ROOT / "capstone/expected/outcomes.json").read_text(encoding="utf-8")
)
REQUIRED_SCENARIOS = set(EXPECTED["required_scenarios"])
KNOWN_DIAGNOSTICS = set(EXPECTED["required_known_wrong"].values())
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
HISTORY_SCENARIOS = {"normal-write-read", "response-loss-retry"}
SCENARIO_INVARIANTS = {
    "normal-write-read": {"ELECTION_SAFETY", "COMMIT_MONOTONICITY", "APPLY_BOUND", "STATE_MACHINE_SAFETY", "LINEARIZABLE_HISTORY"},
    "split-vote": {"ELECTION_SAFETY", "DURABLE_ONE_VOTE"},
    "leader-crash": {"ELECTION_SAFETY", "LOG_MATCHING", "COMMIT_MONOTONICITY"},
    "one-way-partition": {"ELECTION_SAFETY", "COMMIT_MONOTONICITY"},
    "response-loss-retry": {"AT_MOST_ONCE_EFFECT", "LINEARIZABLE_HISTORY"},
    "slow-follower-snapshot": {"SNAPSHOT_EQUIVALENCE", "COMMIT_MONOTONICITY"},
    "repeated-crash-restart": {"DURABLE_ONE_VOTE", "COMMIT_MONOTONICITY"},
}


def fail(message: str) -> None:
    raise SystemExit(f"CAPSTONE CONTRACT FAIL: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        fail(f"{label} is not readable JSON: {exc}")
    require(isinstance(value, dict), f"{label} must be a JSON object")
    return value


def artifact_path(workspace: Path, raw: object, label: str) -> Path:
    require(isinstance(raw, str) and raw, f"{label} path must be non-empty")
    relative = Path(raw)
    require(not relative.is_absolute() and ".." not in relative.parts, f"{label} must use a workspace-relative path: {raw}")
    candidate = workspace
    for part in relative.parts:
        if part in {"", "."}:
            continue
        candidate = candidate / part
        require(not candidate.is_symlink(), f"{label} path contains a symlink component: {raw}")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(workspace)
    except (OSError, ValueError):
        fail(f"{label} path escapes workspace or is missing: {raw}")
    require(resolved.is_file(), f"{label} is not a regular file: {raw}")
    return resolved


def require_sha(value: object, label: str) -> str:
    require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None, f"{label} must be lowercase SHA-256")
    return value


def validate_manifest(manifest: dict[str, Any]) -> None:
    require(manifest.get("schema_version") == 1, "manifest schema_version must be 1")
    require(isinstance(manifest.get("run_bundle_id"), str) and manifest["run_bundle_id"], "manifest run_bundle_id is required")
    source = manifest.get("source")
    require(isinstance(source, dict), "manifest source identity is required")
    require_sha(source.get("tree_sha256"), "manifest source.tree_sha256")
    require(source.get("commit") is None or (isinstance(source.get("commit"), str) and source["commit"]), "manifest source.commit must be null or non-empty")
    require(isinstance(source.get("dirty"), bool), "manifest source.dirty must be boolean")
    runtime = manifest.get("runtime")
    require(isinstance(runtime, dict), "manifest runtime identity is required")
    for field in ("implementation", "version", "platform"):
        require(isinstance(runtime.get(field), str) and runtime[field], f"manifest runtime.{field} is required")
    for field in ("configuration_sha256", "initial_state_sha256", "schedule_bundle_sha256"):
        require_sha(manifest.get(field), f"manifest {field}")
    seed = manifest.get("seed")
    require(isinstance(seed, int) and not isinstance(seed, bool), "manifest seed must be an integer")
    faults = manifest.get("supported_failure_model")
    require(isinstance(faults, list) and faults and all(isinstance(item, str) and item for item in faults), "manifest supported_failure_model is required")


def validate_identity(identity: object, manifest: dict[str, Any], scenario_id: str) -> None:
    require(isinstance(identity, dict), f"{scenario_id} identity is required")
    require(identity.get("run_bundle_id") == manifest["run_bundle_id"], f"{scenario_id} run_bundle identity differs")
    require(identity.get("source_tree_sha256") == manifest["source"]["tree_sha256"], f"{scenario_id} source identity differs")
    require(identity.get("configuration_sha256") == manifest["configuration_sha256"], f"{scenario_id} configuration identity differs")
    require(identity.get("initial_state_sha256") == manifest["initial_state_sha256"], f"{scenario_id} initial-state identity differs")
    require(identity.get("seed") == manifest["seed"], f"{scenario_id} seed identity differs")
    require_sha(identity.get("schedule_sha256"), f"{scenario_id} schedule identity")


def validate_run(workspace: Path, run: dict[str, Any], manifest: dict[str, Any]) -> tuple[str, str, str]:
    scenario_id = run.get("scenario_id")
    run_id = run.get("run_id")
    require(scenario_id in REQUIRED_SCENARIOS, f"unknown scenario_id: {scenario_id!r}")
    require(isinstance(run_id, str) and run_id, f"{scenario_id} run_id is required")
    validate_identity(run.get("identity"), manifest, scenario_id)
    trace_path = artifact_path(workspace, run.get("trace"), f"{scenario_id} trace")
    trace = load_json(trace_path, f"{scenario_id} trace")
    require(trace.get("run_id") == run_id, f"{scenario_id} trace/report run_id differs")
    require(trace.get("scenario_id") == scenario_id, f"{scenario_id} trace scenario identity differs")
    diagnostics = validate_trace(trace)
    require(not diagnostics, f"trace rejected for {scenario_id}: {diagnostics[0].id} {diagnostics[0].message}")
    evidence_diagnostics = check_scenario_evidence(trace, scenario_id)
    require(not evidence_diagnostics, f"scenario evidence rejected for {scenario_id}: {evidence_diagnostics[0].message}")
    actual_results = check_invariants(trace)
    actual_ids = {result.id for result in actual_results if result.ok}
    require(actual_ids >= SCENARIO_INVARIANTS[scenario_id], f"{scenario_id} trace does not exercise its required invariant predicates")
    digest = canonical_trace_digest(trace)
    require_sha(run.get("trace_digest"), f"{scenario_id} trace_digest")
    require(run["trace_digest"] == digest, f"{scenario_id} trace digest differs from artifact")
    replay = run.get("replay")
    require(isinstance(replay, dict), f"{scenario_id} replay evidence is required")
    command = replay.get("command")
    require(isinstance(command, list) and command and all(isinstance(item, str) and item for item in command), f"{scenario_id} replay command is required")
    require(replay.get("exit_code") == 0, f"{scenario_id} replay was not successful")
    require(replay.get("observed_trace_digest") == digest, f"{scenario_id} replay digest differs")
    invariants = run.get("invariant_evidence")
    require(isinstance(invariants, dict) and invariants.get("result") == "PASS", f"{scenario_id} invariant result must be PASS")
    checked_steps = invariants.get("checked_steps")
    event_count = len(trace["events"])
    require(checked_steps == [1, event_count], f"{scenario_id} invariant checked_steps must cover the complete trace")
    invariant_ids = invariants.get("invariant_ids")
    require(isinstance(invariant_ids, list) and set(invariant_ids) >= SCENARIO_INVARIANTS[scenario_id], f"{scenario_id} invariant evidence is incomplete")
    history = run.get("history_evidence")
    require(isinstance(history, dict), f"{scenario_id} history evidence is required")
    if scenario_id in HISTORY_SCENARIOS:
        require(history.get("result") == "PASS", f"{scenario_id} history result must be PASS")
        require(isinstance(history.get("witness"), list) and history["witness"], f"{scenario_id} history witness is required")
        require(history.get("pending_policy") in {"drop", "complete", "either"}, f"{scenario_id} pending policy is required")
    else:
        require(history.get("result") in {"PASS", "UNVERIFIED"}, f"{scenario_id} history result must be PASS or UNVERIFIED")
        if history.get("result") == "UNVERIFIED":
            require(isinstance(history.get("reason"), str) and history["reason"], f"{scenario_id} UNVERIFIED history needs a reason")
    return str(scenario_id), run_id, str(trace_path.relative_to(workspace))


def validate_counterexample(workspace: Path, value: object) -> None:
    require(isinstance(value, dict), "counterexample evidence is required")
    diagnostic_id = value.get("diagnostic_id")
    require(diagnostic_id in KNOWN_DIAGNOSTICS, f"counterexample diagnostic_id is not a required known-wrong diagnostic: {diagnostic_id!r}")
    trace_path = artifact_path(workspace, value.get("trace"), "counterexample trace")
    trace = load_json(trace_path, "counterexample trace")
    diagnostics = validate_trace(trace)
    ids = {item.id for item in diagnostics}
    require("TRACE_SCHEMA" not in ids, "counterexample trace has an invalid envelope")
    require(diagnostic_id in ids, f"counterexample did not reproduce {diagnostic_id}: got={sorted(ids)}")
    digest = canonical_trace_digest(trace)
    require_sha(value.get("trace_digest"), "counterexample trace_digest")
    require(value["trace_digest"] == digest, "counterexample digest differs from artifact")
    original = value.get("original_steps")
    minimized = value.get("minimized_steps")
    require(isinstance(original, int) and isinstance(minimized, int), "counterexample shrink step counts are required")
    require(1 <= minimized < original, "counterexample must show a non-empty strict shrink")
    require(minimized == len(trace.get("events", [])), "counterexample minimized_steps differs from trace")
    command = value.get("replay_command")
    require(isinstance(command, list) and command and all(isinstance(item, str) and item for item in command), "counterexample replay command is required")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace")
    args = parser.parse_args()
    workspace_input = Path(args.workspace).expanduser()
    if workspace_input.is_symlink():
        fail("workspace must not be a symlink")
    try:
        workspace = workspace_input.resolve(strict=True)
    except OSError as exc:
        fail(f"workspace does not exist: {exc}")
    if not workspace.is_dir():
        fail("workspace must be a real directory")
    if workspace == (ROOT / "capstone/starter").resolve():
        fail("copy the starter; canonical source is not learner work")
    for name in REQUIRED_DESIGN:
        path = artifact_path(workspace, f"design/{name}", f"design/{name}")
        text = path.read_text(encoding="utf-8")
        if "TODO" in text:
            fail(f"unfinished design evidence: design/{name}")
    raw_report_path = workspace / "evidence/run-report.json"
    if not raw_report_path.is_file():
        fail("evidence/run-report.json is required; see capstone/evidence/run-report.schema.json")
    report_path = artifact_path(workspace, "evidence/run-report.json", "run report")
    report = load_json(report_path, "run report")
    require(report.get("schema_version") == 1, "run report schema_version must be 1")
    manifest_path = artifact_path(workspace, report.get("manifest"), "run manifest")
    manifest = load_json(manifest_path, "run manifest")
    validate_manifest(manifest)
    runs = report.get("runs")
    require(isinstance(runs, list) and len(runs) == 7, "run report must contain exactly seven runs")
    identities = [validate_run(workspace, run, manifest) for run in runs if isinstance(run, dict)]
    require(len(identities) == 7, "every run must be an object")
    scenarios = [item[0] for item in identities]
    run_ids = [item[1] for item in identities]
    trace_paths = [item[2] for item in identities]
    trace_digests = [run["trace_digest"] for run in runs]
    require(set(scenarios) == REQUIRED_SCENARIOS and len(set(scenarios)) == 7, f"run scenarios must be exactly the required seven: got={scenarios}")
    require(len(set(run_ids)) == 7, "run_id values must be unique")
    require(len(set(trace_paths)) == 7, "each scenario must use a distinct trace artifact")
    require(len(set(trace_digests)) == 7, "each scenario must use a distinct trace digest")
    validate_counterexample(workspace, report.get("counterexample"))
    with tempfile.TemporaryDirectory(prefix="guide-ds-learner-cache-") as cache:
        environment = os.environ.copy()
        environment["CAPSTONE_ROOT"] = str(workspace)
        environment["PYTHONPYCACHEPREFIX"] = cache
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "capstone/tests", "-v"],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
    if completed.returncode != 0:
        sys.stdout.write(completed.stdout or "")
        fail("public behavior tests failed")
    print("CAPSTONE AUTOMATED CONTRACT OK")
    print("HUMAN REVIEW REQUIRED: safety/liveness reasoning, membership, sharding, and model gaps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
