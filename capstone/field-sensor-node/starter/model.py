#!/usr/bin/env python3
"""Intentionally incomplete starter for the field-sensor-node host model.

Keep the public ``run_fixture`` contract and replace the TODO policies.  This
starter is executable so learners can inspect failures immediately; it is not a
reference implementation and is expected to fail ``check.py``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def run_fixture(fixture: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    event_capacity = int(fixture.get("event_capacity", 2))
    storage_capacity = int(fixture.get("storage_capacity", 2))
    state: dict[str, Any] = {
        "device_state": "BOOTING",
        "driver_ready": False,
        "sensor_identity": None,
        "power_state": "ACTIVE",
        "mmio_status": 0,
        "active_generation": None,
        "buffer_owners": {},
        "queue": [],
        "max_event_depth": 0,
        "event_dropped": 0,
        "stale_events": 0,
        "rejected_requests": 0,
        "dma_transfers": 0,
        "staging": None,
        "records": [],
        "committed_ids": [],
        "acked_ids": [],
        "reclaimed_ids": [],
        "storage_full": 0,
        "uploader_offline_attempts": 0,
        "upload_attempts": {},
        "upload_unknown": 0,
        "sleep_aborts": 0,
        "watchdog_feeds": 0,
        "reset_count": 0,
        "power_losses": 0,
        "crash_records": [],
        "firmware_mode": "CONFIRMED",
        "current_image": "v1",
        "confirmed_image": "v1",
        "previous_image": None,
        "trial_self_test": False,
        "trial_attempts": 0,
        "current_schema": 1,
        "rollback_reason": None,
        "covered_stages": set(),
        "evidence": [],
    }
    pending_irq: dict[str, Any] | None = None
    upload_current: str | None = None
    next_record = 1
    trace: list[dict[str, Any]] = []

    for step, event in enumerate(fixture.get("events", []), start=1):
        op = event["op"]
        if op == "BOOT":
            # TODO: probe identity and distinguish ready/degraded dependencies.
            state["sensor_identity"] = event.get("identity", "SENSOR-42")
            state["driver_ready"] = True
            state["device_state"] = "OPERATIONAL"
            state["covered_stages"].add("driver")
        elif op == "REQUEST_SAMPLE":
            generation = int(event.get("generation", 0))
            state["active_generation"] = generation
            state["buffer_owners"][str(generation)] = "DMA"
            state["covered_stages"].update({"driver", "dma"})
        elif op == "MMIO_RAISE":
            state["mmio_status"] |= int(event.get("status", 1))
            pending_irq = dict(event)
            state["covered_stages"].add("mmio")
        elif op == "ISR":
            # TODO: implement W1C, generation checks, and bounded handoff.
            state["mmio_status"] = 0
            if pending_irq:
                state["queue"].append(pending_irq)
                state["max_event_depth"] = max(state["max_event_depth"], len(state["queue"]))
                state["dma_transfers"] += 1
            pending_irq = None
            state["active_generation"] = None
            state["covered_stages"].update({"mmio", "queue"})
        elif op == "TIMEOUT":
            # TODO: invalidate the generation so late completions cannot commit.
            pass
        elif op == "WORK" and state["queue"]:
            descriptor = state["queue"].pop(0)
            state["staging"] = {
                "id": f"R{next_record}",
                "generation": descriptor.get("generation"),
                "integrity": False,
                "state": "STAGING",
            }
            next_record += 1
            state["buffer_owners"].pop(str(descriptor.get("generation")), None)
            state["covered_stages"].update({"queue", "persistence"})
        elif op == "COMMIT" and state["staging"]:
            # TODO: add capacity, commit marker, torn-write, and recovery rules.
            record = dict(state["staging"])
            record["integrity"] = True
            record["state"] = "PENDING_UPLOAD"
            state["records"].append(record)
            state["committed_ids"].append(record["id"])
            state["staging"] = None
            state["covered_stages"].add("persistence")
        elif op == "SET_UPLOADER":
            pass
        elif op == "UPLOAD_START" and state["records"]:
            upload_current = state["records"][0]["id"]
            state["upload_attempts"][upload_current] = state["upload_attempts"].get(upload_current, 0) + 1
            state["covered_stages"].add("upload")
        elif op == "UPLOAD_RESULT" and upload_current:
            # TODO: UNKNOWN must retain the stable record ID; ACK must be durable.
            state["records"] = [record for record in state["records"] if record["id"] != upload_current]
            if event.get("result") == "ACK":
                state["acked_ids"].append(upload_current)
            upload_current = None
            state["covered_stages"].add("upload")
        elif op == "RECLAIM":
            pass
        elif op == "POWER_LOSS":
            state["power_losses"] += 1
            state["reset_count"] += 1
            state["covered_stages"].add("power")
        elif op == "SLEEP_REQUEST":
            state["power_state"] = "PREPARE_SLEEP"
            state["covered_stages"].add("power")
        elif op == "WAKE_EVENT":
            # TODO: latch and arbitrate events arriving in the sleep window.
            pass
        elif op == "SLEEP_COMMIT":
            state["power_state"] = "SLEEP"
            state["covered_stages"].add("power")
        elif op == "WAKE":
            state["power_state"] = "ACTIVE"
            state["covered_stages"].add("power")
        elif op == "HANG":
            state["covered_stages"].add("watchdog")
        elif op == "WATCHDOG_TICK":
            # TODO: gate feed on every critical service and persist crash context.
            state["watchdog_feeds"] += 1
            state["covered_stages"].add("watchdog")
        elif op == "UPDATE_DOWNLOAD":
            state["current_image"] = event.get("version", "v2")
            state["firmware_mode"] = "CANDIDATE"
            state["covered_stages"].add("update")
        elif op == "UPDATE_TRIAL":
            state["firmware_mode"] = "TRIAL"
            state["trial_attempts"] += 1
            state["covered_stages"].add("update")
        elif op == "SELF_TEST_OK":
            state["trial_self_test"] = True
        elif op == "CONFIRM":
            # TODO: confirmation must be gated and power-fail safe.
            state["confirmed_image"] = state["current_image"]
            state["firmware_mode"] = "CONFIRMED"
        elif op == "SCHEMA_COMMIT":
            state["current_schema"] = int(event["schema"])
            state["covered_stages"].add("persistence")
        elif op == "TRIAL_CRASH":
            # TODO: revert or select recovery according to schema compatibility.
            state["covered_stages"].add("crash")

        trace.append(
            {
                "step": step,
                "op": op,
                "event_depth": len(state["queue"]),
                "record_ids": [record["id"] for record in state["records"]],
                "violations": [],
            }
        )

    records = state["records"]
    result = {
        "fixture_id": fixture["fixture_id"],
        "build_id": "starter-build",
        "device_state": state["device_state"],
        "driver_ready": state["driver_ready"],
        "sensor_identity": state["sensor_identity"],
        "power_state": state["power_state"],
        "mmio_status": state["mmio_status"],
        "w1c_writes": [],
        "active_generation": state["active_generation"],
        "buffer_owners": state["buffer_owners"],
        "event_depth": len(state["queue"]),
        "event_capacity": event_capacity,
        "max_event_depth": state["max_event_depth"],
        "event_dropped": state["event_dropped"],
        "stale_events": state["stale_events"],
        "rejected_requests": state["rejected_requests"],
        "dma_transfers": state["dma_transfers"],
        "staging": state["staging"],
        "records": records,
        "record_ids": [record["id"] for record in records],
        "record_states": [record["state"] for record in records],
        "records_integral": all(record["integrity"] for record in records),
        "committed_ids": state["committed_ids"],
        "acked_ids": state["acked_ids"],
        "reclaimed_ids": state["reclaimed_ids"],
        "storage_capacity": storage_capacity,
        "storage_full": state["storage_full"],
        "uploader_offline_attempts": state["uploader_offline_attempts"],
        "upload_attempts": state["upload_attempts"],
        "upload_unknown": state["upload_unknown"],
        "sleep_aborts": state["sleep_aborts"],
        "watchdog_feeds": state["watchdog_feeds"],
        "reset_count": state["reset_count"],
        "power_losses": state["power_losses"],
        "crash_records": state["crash_records"],
        "crash_reasons": [],
        "firmware_mode": state["firmware_mode"],
        "current_image": state["current_image"],
        "confirmed_image": state["confirmed_image"],
        "previous_image": state["previous_image"],
        "trial_self_test": state["trial_self_test"],
        "trial_attempts": state["trial_attempts"],
        "current_schema": state["current_schema"],
        "rollback_reason": state["rollback_reason"],
        "covered_stages": sorted(state["covered_stages"]),
        "evidence": ["starter:replace-each-TODO-with-observable-policy"],
        "violations": [],
    }
    return result, trace


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    result, trace = run_fixture(fixture)
    print(json.dumps({"result": result, "trace": trace}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
