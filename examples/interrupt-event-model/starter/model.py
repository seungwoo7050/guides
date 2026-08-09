#!/usr/bin/env python3
"""Intentionally incomplete interrupt model for exercise 2."""

from __future__ import annotations

import copy
from typing import Any


def run_fixture(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Implement W1C, bounds, generation, and reset policy here."""
    capacity = data.get("capacity", 2)
    hardware_capacity = data.get("hardware_capacity", 4)
    state: dict[str, Any] = {
        "enabled": False,
        "generation": 0,
        "status_register": 0,
        "pending": [],
        "queue": [],
        "handled_events": [],
        "handled_samples": [],
        "handled_sequences": [],
        "dropped": 0,
        "hardware_overrun": 0,
        "stale": 0,
        "spurious": 0,
        "raised_while_disabled": 0,
        "acknowledged": 0,
        "uncleared": 0,
        "idle_work": 0,
        "reset_count": 0,
        "max_queue_depth": 0,
        "max_pending_depth": 0,
        "w1c_writes": [],
    }
    trace: list[dict[str, Any]] = []
    sequence = 1
    for event in data.get("events", []):
        before = copy.deepcopy(state)
        op = event.get("op")
        if op == "ENABLE":
            state["enabled"] = True
            state["generation"] = 1
        elif op == "DISABLE":
            state["enabled"] = False
        elif op == "RAISE":
            if state["enabled"]:
                record = {
                    "generation": state["generation"],
                    "sequence": sequence,
                    "timestamp": event.get("timestamp", sequence - 1),
                    "raw_status": event.get("raw_status", 1),
                    "sample": event.get("sample"),
                }
                sequence += 1
                state["pending"].append(record)
                state["status_register"] |= record["raw_status"]
                state["max_pending_depth"] = max(state["max_pending_depth"], len(state["pending"]))
        elif op == "ISR":
            if state["pending"]:
                record = state["pending"].pop(0)
                state["acknowledged"] += 1
                # Deliberately incomplete: unbounded queue and no W1C behavior.
                state["queue"].append(record)
                state["max_queue_depth"] = max(state["max_queue_depth"], len(state["queue"]))
            else:
                state["spurious"] += 1
        elif op == "WORK":
            if state["queue"]:
                record = state["queue"].pop(0)
                state["handled_events"].append(record)
                state["handled_samples"].append(record["sample"])
                state["handled_sequences"].append(record["sequence"])
            else:
                state["idle_work"] += 1
        elif op == "RESET":
            state["enabled"] = False
            state["generation"] = 0
            state["pending"].clear()
            state["queue"].clear()
        trace.append({"event": copy.deepcopy(event), "before": before, "after": copy.deepcopy(state)})
    result = copy.deepcopy(state)
    result.update({
        "capacity": capacity,
        "hardware_capacity": hardware_capacity,
        "trace_length": len(trace),
    })
    return result, trace
