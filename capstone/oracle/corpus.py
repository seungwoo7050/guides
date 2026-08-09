"""Turn structured reference schedules into canonical evidence traces.

These traces are oracle fixtures, not claims that the intentionally incomplete
starter executed a Raft protocol. Every schedule action is shaped for
``Cluster.run_schedule``; protocol/client observations remain explicit reference
evidence until a learner implementation replays and records them.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def trace_from_case(case: dict[str, Any]) -> dict[str, Any]:
    scenario_id = str(case["id"])
    run_id = str(case.get("run_id", f"reference-{scenario_id}"))
    cluster = case.get("cluster")
    actions = case.get("actions")
    if not isinstance(actions, list) or not actions:
        actions = [{
            "kind": case.get("kind", "evidence"),
            "actor": case.get("actor"),
            "target": case.get("target"),
        }]
    before = _digest({"scenario_id": scenario_id, "cluster": cluster, "phase": "initial"})
    events: list[dict[str, Any]] = []
    for offset, action in enumerate(actions, 1):
        if not isinstance(action, dict):
            raise ValueError("reference schedule actions must be objects")
        after = _digest({
            "scenario_id": scenario_id,
            "previous_state_hash": before,
            "step": offset,
            "action": action,
        })
        details: dict[str, Any] = {"schedule_action": action}
        if offset == 1:
            details["cluster"] = cluster
        if offset == len(actions):
            evidence = case.get("details", {})
            if not isinstance(evidence, dict):
                raise ValueError("reference scenario details must be an object")
            details.update(evidence)
        events.append({
            "schema_version": 1,
            "run_id": run_id,
            "step": offset,
            "virtual_time": offset,
            "event_id": f"e{offset}",
            "kind": str(action.get("kind", "evidence")),
            "actor": action.get("node") or action.get("source") or action.get("actor"),
            "target": action.get("target"),
            "message_id": action.get("message_id"),
            "delivery_id": action.get("delivery_id"),
            "state_before_hash": before,
            "state_after_hash": after,
            "invariant_results": [],
            "details": details,
        })
        before = after
    return {
        "schema_version": 1,
        "run_id": run_id,
        "scenario_id": scenario_id,
        "events": events,
    }
