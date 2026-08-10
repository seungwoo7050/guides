#!/usr/bin/env python3
"""Runnable starter. Replace the TODO state with durable lifecycle logic."""


def run_fixture(data):
    events = data.get("events", [])
    result = {
        "mode": "CONFIRMED",
        "current": "A",
        "candidate": None,
        "previous": None,
        "pending": False,
        "trial_attempts": 0,
        "boot_ok": False,
        "self_test_pass": False,
        "data_schema": data.get("data_schema", 1),
        "metadata": {"committed": True, "mode": "CONFIRMED", "current": "A", "sequence": 0},
        "slots": {"A": {"version": "v1", "valid": True, "compatible": True, "confirmed": True}},
        "errors": ["TODO"],
        "last_reason": "starter_not_implemented",
        "trace_length": len(events),
    }
    trace = [{"event": event, "before": {}, "after": dict(result)} for event in events]
    return result, trace
