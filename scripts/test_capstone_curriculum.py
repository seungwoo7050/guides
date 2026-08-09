#!/usr/bin/env python3
"""Meta-test capstone oracles, reference evidence, and starter rejection."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from capstone.model.election_model import explore  # noqa: E402
from capstone.oracle import (  # noqa: E402
    canonical_trace_digest,
    check_expected,
    check_history,
    check_scenario_evidence,
    shrink_failure,
    validate_trace,
)
from capstone.oracle.checks import REQUIRED_SCENARIO_EVIDENCE  # noqa: E402
from capstone.oracle.corpus import trace_from_case  # noqa: E402


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


ACTION_FIELDS = {
    "tick": ({"kind", "node"}, {"kind", "node", "repeat"}),
    "tick_all": ({"kind"}, {"kind", "repeat"}),
    "deliver": ({"kind"}, {"kind", "delivery_id"}),
    "deliver_all": ({"kind"}, {"kind", "limit"}),
    "crash": ({"kind", "node"}, {"kind", "node"}),
    "restart": ({"kind", "node"}, {"kind", "node"}),
    "drop": ({"kind", "delivery_id"}, {"kind", "delivery_id"}),
    "delay": ({"kind", "delivery_id", "ticks"}, {"kind", "delivery_id", "ticks"}),
    "duplicate": ({"kind", "delivery_id"}, {"kind", "delivery_id", "extra_delay"}),
    "partition": ({"kind", "source", "target"}, {"kind", "source", "target", "bidirectional"}),
    "heal": ({"kind"}, {"kind", "source", "target"}),
    "submit": (
        {"kind", "node", "client_id", "sequence", "command"},
        {"kind", "node", "client_id", "sequence", "command", "fingerprint"},
    ),
    "drain_responses": ({"kind"}, {"kind"}),
    "create_snapshot": ({"kind", "node", "through_index"}, {"kind", "node", "through_index"}),
}


def validate_schedule_action(action: object, scenario_id: str, position: int) -> None:
    require(isinstance(action, dict), f"{scenario_id} action {position} is not an object")
    kind = action.get("kind")
    require(kind in ACTION_FIELDS, f"{scenario_id} action {position} unsupported kind={kind!r}")
    required, allowed = ACTION_FIELDS[kind]
    require(required <= set(action) <= allowed, f"{scenario_id} action {position} fields differ: {action}")
    for field in set(action) & {"node", "source", "target", "delivery_id", "client_id", "fingerprint"}:
        require(isinstance(action[field], str) and action[field], f"{scenario_id} action {position} invalid {field}")
    for field in set(action) & {"ticks", "extra_delay", "through_index"}:
        require(isinstance(action[field], int) and not isinstance(action[field], bool) and action[field] >= 0, f"{scenario_id} {field} must be non-negative")
    for field in set(action) & {"repeat", "limit", "sequence"}:
        require(isinstance(action[field], int) and not isinstance(action[field], bool) and action[field] >= 1, f"{scenario_id} {field} must be positive")
    if "bidirectional" in action:
        require(isinstance(action["bidirectional"], bool), f"{scenario_id} bidirectional must be boolean")
    if kind == "heal":
        require(set(action) in ({"kind"}, {"kind", "source", "target"}), f"{scenario_id} heal requires both endpoints or neither")
    if kind == "submit":
        command = action["command"]
        require(isinstance(command, dict), f"{scenario_id} submit command must be an object")
        require({"kind", "key"} <= set(command) <= {"kind", "key", "value", "expected"}, f"{scenario_id} submit command fields differ")
        require(command["kind"] in {"put", "get", "compare_and_set"}, f"{scenario_id} command kind is unsupported")
        require(isinstance(command["key"], str) and command["key"], f"{scenario_id} command key is required")


def validate_cluster_identity(value: object, scenario_id: str) -> None:
    require(isinstance(value, dict) and set(value) == {"node_ids", "election_timeouts"}, f"{scenario_id} cluster identity fields differ")
    nodes = value["node_ids"]
    timeouts = value["election_timeouts"]
    require(isinstance(nodes, list) and len(nodes) == 3 and len(set(nodes)) == 3, f"{scenario_id} cluster needs three unique nodes")
    require(all(isinstance(node, str) and node for node in nodes), f"{scenario_id} node ids must be non-empty strings")
    require(isinstance(timeouts, dict) and set(timeouts) == set(nodes), f"{scenario_id} election timeouts must cover every node")
    require(all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in timeouts.values()), f"{scenario_id} election timeouts must be positive integers")


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _event(step: int, before: str, after: str, details: dict, run_id: str = "mutant-run") -> dict:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "step": step,
        "virtual_time": step,
        "event_id": f"e{step}",
        "kind": "model_step",
        "actor": "model",
        "target": None,
        "message_id": None,
        "delivery_id": None,
        "state_before_hash": before,
        "state_after_hash": after,
        "invariant_results": [],
        "details": details,
    }


def check_oracle_mutants() -> None:
    require("TRACE_SCHEMA" in {d.id for d in validate_trace({"schema_version": 1, "run_id": "empty", "events": []})}, "empty trace accepted")
    first_after = _hash("after-1")
    dual = {
        "schema_version": 1,
        "run_id": "mutant-run",
        "scenario_id": "split-vote",
        "events": [
            _event(1, _hash("before"), first_after, {"leaders_by_term": {"1": ["A"]}}),
            _event(2, first_after, _hash("after-2"), {"leaders_by_term": {"1": ["B"]}}),
        ],
    }
    require("ELECTION_SAFETY" in {d.id for d in validate_trace(dual)}, "cross-event dual leader accepted")
    identity = copy.deepcopy(dual)
    identity["events"][1]["run_id"] = "another-run"
    require("TRACE_RUN_ID" in {d.id for d in validate_trace(identity)}, "event/top run identity mismatch accepted")
    broken_chain = copy.deepcopy(dual)
    broken_chain["events"][1]["state_before_hash"] = _hash("unrelated")
    require("TRACE_HASH_CHAIN" in {d.id for d in validate_trace(broken_chain)}, "broken state hash chain accepted")
    malformed = {
        "schema_version": 1,
        "run_id": "malformed",
        "events": [_event(1, _hash("m0"), _hash("m1"), {"durable_votes": [{}]}, "malformed")],
    }
    malformed_ids = {d.id for d in validate_trace(malformed)}
    require("TRACE_SCHEMA" in malformed_ids, f"malformed invariant evidence did not become TRACE_SCHEMA: {malformed_ids}")


def check_corpus() -> tuple[int, int]:
    schedules_document = load("capstone/scenarios/schedules.json")
    schedules = schedules_document["scenarios"]
    wrong = load("capstone/known-wrong/traces.json")["cases"]
    expected = load("capstone/expected/outcomes.json")
    require(schedules_document.get("schema_version") == 1, "schedule schema_version differs")
    require(
        [case["id"] for case in schedules] == expected["required_scenarios"],
        "required scenario order or identity differs",
    )
    require(expected["required_scenario_evidence"] == {
        scenario: list(fields) for scenario, fields in REQUIRED_SCENARIO_EVIDENCE.items()
    }, "scenario evidence contract differs between oracle and expected outcomes")
    seen_runs: set[str] = set()
    seen_digests: set[str] = set()
    for case in schedules:
        scenario_id = case["id"]
        require(case.get("run_id") not in seen_runs, f"duplicate reference run_id: {case.get('run_id')}")
        seen_runs.add(case["run_id"])
        validate_cluster_identity(case.get("cluster"), scenario_id)
        actions = case.get("actions")
        require(isinstance(actions, list) and actions, f"{scenario_id} has no executable schedule actions")
        for position, action in enumerate(actions, 1):
            validate_schedule_action(action, scenario_id, position)
        require(case.get("required_evidence") == list(REQUIRED_SCENARIO_EVIDENCE[scenario_id]), f"{scenario_id} required evidence differs")
        trace = trace_from_case(case)
        diagnostics = validate_trace(trace)
        require(not diagnostics, f"valid reference trace rejected: {scenario_id}: {diagnostics}")
        evidence_diagnostics = check_scenario_evidence(trace, scenario_id)
        require(not evidence_diagnostics, f"scenario evidence rejected: {scenario_id}: {evidence_diagnostics}")
        digest = canonical_trace_digest(trace)
        require(digest == expected["reference_trace_digests"][scenario_id], f"reference digest differs: {scenario_id}")
        require(not check_expected(trace, {"diagnostic_ids": [], "digest": digest}), f"check_expected rejected {scenario_id}")
        require(digest not in seen_digests, f"two scenarios reuse the same reference trace: {scenario_id}")
        seen_digests.add(digest)
        require(digest == canonical_trace_digest(trace_from_case(case)), f"nondeterministic reference trace: {scenario_id}")
    expected_wrong = expected["required_known_wrong"]
    require({case["id"]: case["diagnostic_id"] for case in wrong} == expected_wrong, "known-wrong catalog differs")
    for case in wrong:
        diagnostics = validate_trace(trace_from_case(case))
        ids = {item.id for item in diagnostics}
        require("TRACE_SCHEMA" not in ids, f"known-wrong fixture has invalid schema: {case['id']} {diagnostics}")
        require(case["diagnostic_id"] in ids, f"known-wrong case not rejected for intended reason: {case['id']} got={sorted(ids)}")
    check_oracle_mutants()
    return len(schedules), len(wrong)


def check_model_and_history() -> None:
    safe = explore()
    unsafe = explore(unsafe_send_before_persist=True)
    require(safe["explored_states"] > 0 and safe["stale_requests_considered"] > 0, "safe model did not explore bounded state/log freshness")
    require(safe["double_vote"] is False and safe["dual_majority"] is False, "persist-before-send model violated election safety")
    require(unsafe["double_vote"] is True and unsafe["dual_majority"] is True, "unsafe model did not expose double vote and dual majority")
    require(unsafe["minimal_counterexample_length"] == 3, f"unsafe counterexample is not minimal: {unsafe['counterexample']}")
    require(all(len(voters) == 2 for voters in unsafe["majorities"].values()), "unsafe witness does not contain two real majorities")
    history = {
        "pending_policy": "drop",
        "initial": {"x": 1},
        "operations": [
            {"id": "cas", "client": "c1", "kind": "compare_and_set", "key": "x", "expected": 1, "value": 2, "status": "OK", "invoke": 1, "complete": 3},
            {"id": "read", "client": "c2", "kind": "get", "key": "x", "status": "OK", "result": 2, "invoke": 4, "complete": 5},
        ],
    }
    require(check_history(history).linearizable, "valid KV/CAS history rejected")
    pending = {
        "initial": {"x": 0},
        "operations": [
            {"id": "pending-write", "client": "c1", "kind": "put", "key": "x", "value": 1, "status": "OK", "invoke": 1, "complete": None},
            {"id": "read", "client": "c2", "kind": "get", "key": "x", "status": "OK", "result": 1, "invoke": 2, "complete": 3},
        ],
    }
    require(not check_history(pending, pending_policy="drop").linearizable, "drop policy incorrectly completed a pending write")
    require(check_history(pending, pending_policy="complete").linearizable, "complete policy rejected a legal pending completion")
    require(check_history(pending, pending_policy="either").linearizable, "either policy failed to explore pending completion")
    malformed_time = {"initial": {}, "operations": [{"id": "x", "client": "c", "kind": "put", "key": "x", "value": 1, "status": "OK", "invoke": 4, "complete": 2}]}
    require(not check_history(malformed_time).linearizable, "history with completion before invocation accepted")
    schedule = [{"id": value} for value in ["noise-a", "vote-b", "noise-c", "vote-c"]]
    shrunk = shrink_failure(schedule, lambda items: {item["id"] for item in items} >= {"vote-b", "vote-c"})
    require([item["id"] for item in shrunk] == ["vote-b", "vote-c"], "failure shrink did not find the minimal witness")


EXPECTED_STARTER_ERRORS = {
    "test_crash_hooks_expose_the_persist_before_response_barrier",
    "test_granted_vote_is_durable_before_response",
    "test_same_term_second_candidate_is_rejected",
    "test_conflicting_suffix_is_replaced_after_matching_prefix",
    "test_follower_does_not_accept_mutating_command",
    "test_higher_term_message_steps_leader_down",
    "test_one_way_partition_replaces_old_leader_in_a_higher_term",
    "test_staggered_timeout_elects_one_leader",
    "test_stale_candidate_is_rejected",
    "test_exact_duplicate_reuses_the_cached_result",
    "test_leader_does_not_reply_before_commit_and_apply",
    "test_same_sequence_with_another_fingerprint_is_conflict",
    "test_sequence_gap_is_distinct_from_stale_and_conflict",
    "test_stale_sequence_is_rejected_without_effect",
    "test_install_restores_sessions_and_rejects_stale_snapshot",
    "test_put_logged_get_and_cas_apply_after_commit",
    "test_response_loss_leader_replacement_and_retry_have_one_effect",
    "test_snapshot_restart_preserves_kv_session_and_configuration",
}


def check_starter_rejection() -> tuple[int, int]:
    with tempfile.TemporaryDirectory(prefix="guide-ds-capstone-cache-") as cache:
        environment = os.environ.copy()
        environment["CAPSTONE_ROOT"] = str(ROOT / "capstone/starter")
        environment["PYTHONPYCACHEPREFIX"] = cache
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "capstone/tests", "-v"],
            cwd=ROOT,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
    total = 29
    require(completed.returncode != 0, "canonical starter unexpectedly passed the full capstone contract")
    require(f"Ran {total} tests" in completed.stdout, f"unexpected public test count\n{completed.stdout}")
    require(f"FAILED (errors={len(EXPECTED_STARTER_ERRORS)})" in completed.stdout, f"starter failure shape changed\n{completed.stdout}")
    require("FAILED (failures=" not in completed.stdout, "starter has assertion failures rather than intentional incomplete transitions")
    errors = set(re.findall(r"^ERROR: (test_[a-z0-9_]+) ", completed.stdout, flags=re.MULTILINE))
    require(errors == EXPECTED_STARTER_ERRORS, f"starter errors differ: expected={sorted(EXPECTED_STARTER_ERRORS)} got={sorted(errors)}")
    require(completed.stdout.count("NotImplementedError:") == len(EXPECTED_STARTER_ERRORS), "starter failures are not all intentional transition gaps")
    return total - len(errors), len(errors)


def main() -> int:
    valid, wrong = check_corpus()
    check_model_and_history()
    starter_pass, starter_expected_fail = check_starter_rejection()
    print(
        "CAPSTONE CURRICULUM OK "
        f"valid_scenarios={valid} known_wrong={wrong} "
        f"starter_pass={starter_pass} starter_expected_fail={starter_expected_fail}"
    )
    print("NOTE: reference traces are oracle evidence; the incomplete starter did not execute them.")
    print("NOTE: curriculum evidence does not certify a learner implementation or human reasoning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
