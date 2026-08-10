#!/usr/bin/env python3
"""Deterministic host model for the field sensor node capstone.

This model deliberately represents only public state transitions.  It does not
pretend to model instruction timing, electrical behaviour, or a particular MCU.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BUILD_ID = "field-node-model-v1"


class NodeModel:
    def __init__(self, fixture: dict[str, Any]) -> None:
        self.event_capacity = int(fixture.get("event_capacity", 2))
        self.storage_capacity = int(fixture.get("storage_capacity", 2))
        if self.event_capacity < 1 or self.storage_capacity < 1:
            raise ValueError("capacities must be positive")

        self.device_state = "BOOTING"
        self.driver_ready = False
        self.sensor_identity: str | None = None
        self.power_state = "ACTIVE"
        self.mmio_status = 0
        self.pending_irq: dict[str, Any] | None = None
        self.w1c_writes: list[int] = []
        self.active_generation: int | None = None
        self.deadline: int | None = None
        self.generation = 0
        self.buffer_owners: dict[str, str] = {}
        self.event_queue: list[dict[str, Any]] = []
        self.max_event_depth = 0
        self.event_dropped = 0
        self.stale_events = 0
        self.rejected_requests = 0
        self.dma_transfers = 0

        self.staging: dict[str, Any] | None = None
        self.records: list[dict[str, Any]] = []
        self.next_record = 1
        self.committed_ids: list[str] = []
        self.acked_ids: list[str] = []
        self.reclaimed_ids: list[str] = []
        self.storage_full = 0
        self.uploader_online = True
        self.uploader_offline_attempts = 0
        self.upload_current: str | None = None
        self.upload_attempts: dict[str, int] = {}
        self.upload_unknown = 0

        self.sleep_aborts = 0
        self.wake_pending = False
        self.hung_services: set[str] = set()
        self.watchdog_feeds = 0
        self.reset_count = 0
        self.power_losses = 0
        self.crash_records: list[dict[str, Any]] = []

        self.firmware_mode = "CONFIRMED"
        self.current_image: str | None = "v1"
        self.confirmed_image = "v1"
        self.previous_image: str | None = None
        self.candidate: dict[str, Any] | None = None
        self.trial_self_test = False
        self.trial_attempts = 0
        self.current_schema = 1
        self.image_schema_support: dict[str, list[int]] = {"v1": [1]}
        self.rollback_reason: str | None = None

        self.covered_stages: set[str] = set()
        self.evidence: list[str] = []
        self.violations: list[str] = []
        self.trace: list[dict[str, Any]] = []

    def _record(self, op: str) -> None:
        if len(self.event_queue) > self.event_capacity:
            self.violations.append("event queue exceeded its declared capacity")
        if len(self.records) > self.storage_capacity:
            self.violations.append("persistent store exceeded its declared capacity")
        if any(not record.get("integrity") for record in self.records):
            self.violations.append("a non-integral record became durable")
        if any(owner not in {"DMA", "QUEUE", "CPU"} for owner in self.buffer_owners.values()):
            self.violations.append("invalid DMA buffer owner")
        self.trace.append(
            {
                "step": len(self.trace) + 1,
                "op": op,
                "device_state": self.device_state,
                "power_state": self.power_state,
                "driver_ready": self.driver_ready,
                "mmio_status": self.mmio_status,
                "active_generation": self.active_generation,
                "buffer_owners": dict(sorted(self.buffer_owners.items())),
                "event_depth": len(self.event_queue),
                "record_ids": [record["id"] for record in self.records],
                "record_states": [record["state"] for record in self.records],
                "firmware_mode": self.firmware_mode,
                "current_image": self.current_image,
                "violations": list(self.violations),
            }
        )

    def _volatile_reset(self) -> None:
        self.driver_ready = False
        self.device_state = "BOOTING"
        self.mmio_status = 0
        self.pending_irq = None
        self.active_generation = None
        self.deadline = None
        self.buffer_owners.clear()
        self.event_queue.clear()
        self.staging = None
        self.upload_current = None
        self.power_state = "ACTIVE"
        self.wake_pending = False

    def _find_record(self, record_id: str | None) -> dict[str, Any] | None:
        if record_id is None:
            return None
        return next((record for record in self.records if record["id"] == record_id), None)

    def apply(self, event: dict[str, Any]) -> None:
        op = str(event.get("op", ""))
        if not op:
            raise ValueError("every event needs an op")

        if op == "BOOT":
            identity = str(event.get("identity", "SENSOR-42"))
            self.sensor_identity = identity
            self.power_state = "ACTIVE"
            self.covered_stages.add("driver")
            if identity == "SENSOR-42":
                self.driver_ready = True
                self.device_state = "OPERATIONAL"
                self.evidence.append("driver:identity-accepted")
            else:
                self.driver_ready = False
                self.device_state = "DEGRADED"
                self.evidence.append("driver:identity-rejected")

        elif op == "REQUEST_SAMPLE":
            if not self.driver_ready or self.power_state != "ACTIVE":
                self.rejected_requests += 1
                self.evidence.append("driver:request-rejected")
            else:
                generation = int(event.get("generation", self.generation + 1))
                self.generation = max(self.generation, generation)
                self.active_generation = generation
                self.deadline = int(event.get("deadline", 0))
                self.buffer_owners[str(generation)] = "DMA"
                self.covered_stages.update({"driver", "dma"})
                self.evidence.append(f"dma:{generation}:CPU->DMA")

        elif op == "MMIO_RAISE":
            status = int(event.get("status", 1))
            self.mmio_status |= status
            self.pending_irq = {
                "generation": int(event.get("generation", -1)),
                "timestamp": int(event.get("timestamp", 0)),
                "sample": event.get("sample"),
                "status": status,
            }
            self.covered_stages.add("mmio")

        elif op == "ISR":
            snapshot = self.mmio_status
            clear_mask = int(event.get("clear_mask", snapshot))
            self.w1c_writes.append(clear_mask)
            self.mmio_status &= ~clear_mask
            self.covered_stages.update({"mmio", "queue"})
            pending = self.pending_irq
            if not pending:
                self.evidence.append("interrupt:spurious")
            else:
                generation = int(pending["generation"])
                key = str(generation)
                if generation != self.active_generation:
                    self.stale_events += 1
                    self.buffer_owners.pop(key, None)
                    self.evidence.append(f"interrupt:{generation}:stale-discard")
                elif len(self.event_queue) >= self.event_capacity:
                    self.event_dropped += 1
                    self.buffer_owners.pop(key, None)
                    self.evidence.append(f"queue:{generation}:overflow-drop")
                else:
                    descriptor = dict(pending)
                    descriptor["raw_status"] = snapshot
                    self.event_queue.append(descriptor)
                    self.max_event_depth = max(self.max_event_depth, len(self.event_queue))
                    self.buffer_owners[key] = "QUEUE"
                    self.dma_transfers += 1
                    self.evidence.append(f"dma:{generation}:DMA->QUEUE")
                self.active_generation = None
                self.deadline = None
            self.pending_irq = None

        elif op == "TIMEOUT":
            now = int(event.get("now", 0))
            if self.active_generation is not None and self.deadline is not None and now >= self.deadline:
                generation = self.active_generation
                self.active_generation = None
                self.deadline = None
                self.buffer_owners.pop(str(generation), None)
                self.evidence.append(f"driver:{generation}:timeout")

        elif op == "WORK":
            if self.event_queue:
                descriptor = self.event_queue.pop(0)
                generation = int(descriptor["generation"])
                key = str(generation)
                self.buffer_owners[key] = "CPU"
                record_id = f"R{self.next_record}"
                self.next_record += 1
                self.staging = {
                    "id": record_id,
                    "generation": generation,
                    "timestamp": descriptor["timestamp"],
                    "sample": descriptor.get("sample"),
                    "quality": "VALID",
                    "integrity": False,
                    "state": "STAGING",
                    "schema": self.current_schema,
                }
                self.buffer_owners.pop(key, None)
                self.covered_stages.update({"dma", "queue", "persistence"})
                self.evidence.append(f"dma:{generation}:QUEUE->CPU->FREE")

        elif op == "COMMIT":
            self.covered_stages.add("persistence")
            if self.staging is None:
                self.evidence.append("persistence:no-staging-record")
            elif len(self.records) >= self.storage_capacity:
                self.storage_full += 1
                self.evidence.append(f"persistence:{self.staging['id']}:storage-full")
                self.staging = None
            else:
                record = dict(self.staging)
                record["integrity"] = True
                record["state"] = "PENDING_UPLOAD"
                self.records.append(record)
                self.committed_ids.append(record["id"])
                self.staging = None
                self.evidence.append(f"persistence:{record['id']}:commit-marker")

        elif op == "SET_UPLOADER":
            self.uploader_online = bool(event.get("online", True))

        elif op == "UPLOAD_START":
            self.covered_stages.add("upload")
            pending = next(
                (record for record in self.records if record["state"] == "PENDING_UPLOAD"),
                None,
            )
            if pending is None:
                self.evidence.append("upload:no-pending-record")
            elif not self.uploader_online:
                self.uploader_offline_attempts += 1
                self.evidence.append(f"upload:{pending['id']}:offline-retain")
            else:
                record_id = str(pending["id"])
                pending["state"] = "IN_FLIGHT"
                self.upload_current = record_id
                self.upload_attempts[record_id] = self.upload_attempts.get(record_id, 0) + 1
                self.evidence.append(f"upload:{record_id}:attempt-{self.upload_attempts[record_id]}")

        elif op == "UPLOAD_RESULT":
            self.covered_stages.add("upload")
            record = self._find_record(self.upload_current)
            result = str(event.get("result", "UNKNOWN"))
            if record is not None and result == "ACK":
                record["state"] = "ACKNOWLEDGED"
                if record["id"] not in self.acked_ids:
                    self.acked_ids.append(record["id"])
                self.evidence.append(f"upload:{record['id']}:durable-ack")
            elif record is not None:
                record["state"] = "PENDING_UPLOAD"
                if result == "UNKNOWN":
                    self.upload_unknown += 1
                self.evidence.append(f"upload:{record['id']}:{result.lower()}-retain")
            self.upload_current = None

        elif op == "RECLAIM":
            retained: list[dict[str, Any]] = []
            for record in self.records:
                if record["state"] == "ACKNOWLEDGED":
                    self.reclaimed_ids.append(record["id"])
                else:
                    retained.append(record)
            self.records = retained

        elif op == "POWER_LOSS":
            point = str(event.get("point", "runtime"))
            self.power_losses += 1
            self.covered_stages.add("power")
            if point == "confirm" and self.firmware_mode == "TRIAL" and self.previous_image:
                self.current_image = self.previous_image
                self.confirmed_image = self.previous_image
                self.previous_image = None
                self.candidate = None
                self.firmware_mode = "CONFIRMED"
                self.trial_self_test = False
                self.rollback_reason = "confirm_power_loss_revert"
                self.evidence.append("update:confirm-power-loss-revert")
            self.reset_count += 1
            self._volatile_reset()
            self.evidence.append(f"power-loss:{point}:volatile-discard")

        elif op == "SLEEP_REQUEST":
            self.covered_stages.add("power")
            if self.pending_irq or self.event_queue or self.active_generation is not None:
                self.sleep_aborts += 1
                self.power_state = "ACTIVE"
                self.evidence.append("power:sleep-abort-work-pending")
            else:
                self.power_state = "PREPARE_SLEEP"
                self.evidence.append("power:sleep-check-complete")

        elif op == "WAKE_EVENT":
            self.covered_stages.add("power")
            self.wake_pending = True
            if self.power_state in {"PREPARE_SLEEP", "SLEEP"}:
                if self.power_state == "PREPARE_SLEEP":
                    self.sleep_aborts += 1
                self.power_state = "ACTIVE"
                self.driver_ready = self.sensor_identity == "SENSOR-42"
                self.evidence.append("power:wake-latched-and-restored")

        elif op == "SLEEP_COMMIT":
            self.covered_stages.add("power")
            if self.wake_pending or self.pending_irq or self.event_queue:
                self.sleep_aborts += int(self.power_state == "PREPARE_SLEEP")
                self.power_state = "ACTIVE"
                self.wake_pending = False
                self.evidence.append("power:sleep-commit-aborted")
            elif self.power_state == "PREPARE_SLEEP":
                self.power_state = "SLEEP"
                self.driver_ready = False
                self.evidence.append("power:sleep-entered")

        elif op == "WAKE":
            self.covered_stages.add("power")
            self.power_state = "ACTIVE"
            self.wake_pending = False
            self.driver_ready = self.sensor_identity == "SENSOR-42"
            self.evidence.append("power:wake-restored-driver")

        elif op == "HANG":
            service = str(event.get("service", "sensor"))
            self.hung_services.add(service)
            self.covered_stages.add("watchdog")

        elif op == "WATCHDOG_TICK":
            self.covered_stages.add("watchdog")
            if self.hung_services:
                reason = "watchdog:" + ",".join(sorted(self.hung_services))
                crash = {
                    "build_id": BUILD_ID,
                    "reason": reason,
                    "last_progress": str(event.get("last_progress", "unknown")),
                    "integrity": True,
                }
                self.crash_records.append(crash)
                self.covered_stages.add("crash")
                self.evidence.append(f"crash:{reason}:committed-before-reset")
                self.reset_count += 1
                self.hung_services.clear()
                self._volatile_reset()
            else:
                self.watchdog_feeds += 1

        elif op == "UPDATE_DOWNLOAD":
            self.covered_stages.add("update")
            valid = bool(event.get("valid", True))
            version = str(event.get("version", "v2"))
            schema = int(event.get("schema", 1))
            support = [int(value) for value in event.get("supports", [1])]
            if valid:
                self.candidate = {"version": version, "schema": schema, "supports": support}
                self.image_schema_support[version] = support
                self.firmware_mode = "CANDIDATE"
                self.evidence.append(f"update:{version}:candidate-validated")
            else:
                self.candidate = None
                self.evidence.append(f"update:{version}:candidate-rejected")

        elif op == "UPDATE_TRIAL":
            self.covered_stages.add("update")
            if self.candidate:
                self.previous_image = self.current_image
                self.current_image = str(self.candidate["version"])
                self.firmware_mode = "TRIAL"
                self.trial_self_test = False
                self.trial_attempts += 1
                self.evidence.append(f"update:{self.current_image}:trial-start")

        elif op == "SELF_TEST_OK":
            self.covered_stages.add("update")
            if self.firmware_mode == "TRIAL":
                self.trial_self_test = True
                self.evidence.append(f"update:{self.current_image}:self-test-ok")

        elif op == "CONFIRM":
            self.covered_stages.add("update")
            if self.firmware_mode == "TRIAL" and self.trial_self_test and self.current_image:
                self.confirmed_image = self.current_image
                self.previous_image = None
                self.candidate = None
                self.firmware_mode = "CONFIRMED"
                self.evidence.append(f"update:{self.current_image}:confirmed")
            else:
                self.evidence.append("update:confirm-rejected")

        elif op == "SCHEMA_COMMIT":
            self.covered_stages.update({"persistence", "update"})
            self.current_schema = int(event["schema"])
            self.evidence.append(f"persistence:schema-{self.current_schema}:committed")

        elif op == "TRIAL_CRASH":
            self.covered_stages.update({"update", "crash"})
            previous = self.previous_image
            if self.firmware_mode == "TRIAL" and previous:
                if self.current_schema not in self.image_schema_support.get(previous, []):
                    self.current_image = None
                    self.firmware_mode = "RECOVERY"
                    self.rollback_reason = "schema_incompatible"
                    self.evidence.append("update:rollback-blocked-schema-incompatible")
                else:
                    self.current_image = previous
                    self.confirmed_image = previous
                    self.firmware_mode = "CONFIRMED"
                    self.rollback_reason = "trial_crash_revert"
                    self.evidence.append(f"update:{previous}:trial-crash-revert")
                self.previous_image = None
                self.candidate = None
                self.trial_self_test = False

        else:
            raise ValueError(f"unsupported op: {op}")

        self._record(op)

    def result(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {
            "fixture_id": fixture["fixture_id"],
            "build_id": BUILD_ID,
            "device_state": self.device_state,
            "driver_ready": self.driver_ready,
            "sensor_identity": self.sensor_identity,
            "power_state": self.power_state,
            "mmio_status": self.mmio_status,
            "w1c_writes": list(self.w1c_writes),
            "active_generation": self.active_generation,
            "buffer_owners": dict(sorted(self.buffer_owners.items())),
            "event_depth": len(self.event_queue),
            "event_capacity": self.event_capacity,
            "max_event_depth": self.max_event_depth,
            "event_dropped": self.event_dropped,
            "stale_events": self.stale_events,
            "rejected_requests": self.rejected_requests,
            "dma_transfers": self.dma_transfers,
            "staging": self.staging,
            "records": self.records,
            "record_ids": [record["id"] for record in self.records],
            "record_states": [record["state"] for record in self.records],
            "records_integral": all(record["integrity"] for record in self.records),
            "committed_ids": self.committed_ids,
            "acked_ids": self.acked_ids,
            "reclaimed_ids": self.reclaimed_ids,
            "storage_capacity": self.storage_capacity,
            "storage_full": self.storage_full,
            "uploader_offline_attempts": self.uploader_offline_attempts,
            "upload_attempts": dict(sorted(self.upload_attempts.items())),
            "upload_unknown": self.upload_unknown,
            "sleep_aborts": self.sleep_aborts,
            "watchdog_feeds": self.watchdog_feeds,
            "reset_count": self.reset_count,
            "power_losses": self.power_losses,
            "crash_records": self.crash_records,
            "crash_reasons": [record["reason"] for record in self.crash_records],
            "firmware_mode": self.firmware_mode,
            "current_image": self.current_image,
            "confirmed_image": self.confirmed_image,
            "previous_image": self.previous_image,
            "trial_self_test": self.trial_self_test,
            "trial_attempts": self.trial_attempts,
            "current_schema": self.current_schema,
            "rollback_reason": self.rollback_reason,
            "covered_stages": sorted(self.covered_stages),
            "evidence": self.evidence,
            "violations": self.violations,
        }


def run_fixture(fixture: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    model = NodeModel(fixture)
    events = fixture.get("events")
    if not isinstance(events, list):
        raise ValueError("fixture events must be a list")
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("fixture events must be objects")
        model.apply(event)
    return model.result(fixture), model.trace


def _matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _matches(actual[key], value) for key, value in expected.items()
        )
    return actual == expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--check", action="store_true", help="check the fixture's expected subset")
    parser.add_argument("--trace", action="store_true", help="include the per-event trace")
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    result, trace = run_fixture(fixture)
    payload: dict[str, Any] = {"result": result}
    if args.trace:
        payload["trace"] = trace
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.check and not _matches(result, fixture.get("expected", {})):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
