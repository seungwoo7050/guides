#!/usr/bin/env python3
"""Reference interrupt-to-worker model with W1C and bounded ownership."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Deque


class ModelError(ValueError):
    """Raised for malformed fixture input."""


def nonnegative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ModelError(f"{label} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class EventRecord:
    generation: int
    sequence: int
    timestamp: int
    raw_status: int
    sample: int


@dataclass
class InterruptModel:
    capacity: int
    hardware_capacity: int = 4
    enabled: bool = False
    generation: int = 0
    next_sequence: int = 1
    status_register: int = 0
    pending: Deque[EventRecord] = field(default_factory=deque)
    queue: Deque[EventRecord] = field(default_factory=deque)
    handled_events: list[dict[str, int]] = field(default_factory=list)
    handled_samples: list[int] = field(default_factory=list)
    handled_sequences: list[int] = field(default_factory=list)
    dropped: int = 0
    hardware_overrun: int = 0
    stale: int = 0
    spurious: int = 0
    raised_while_disabled: int = 0
    acknowledged: int = 0
    uncleared: int = 0
    idle_work: int = 0
    reset_count: int = 0
    max_queue_depth: int = 0
    max_pending_depth: int = 0
    w1c_writes: list[int] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.capacity, bool) or not isinstance(self.capacity, int) or self.capacity <= 0:
            raise ModelError("capacity must be greater than zero")
        if (
            isinstance(self.hardware_capacity, bool)
            or not isinstance(self.hardware_capacity, int)
            or self.hardware_capacity <= 0
        ):
            raise ModelError("hardware_capacity must be greater than zero")

    def snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "generation": self.generation,
            "status_register": self.status_register,
            "pending": [asdict(item) for item in self.pending],
            "queue": [asdict(item) for item in self.queue],
            "handled_events": list(self.handled_events),
            "handled_samples": list(self.handled_samples),
            "handled_sequences": list(self.handled_sequences),
            "dropped": self.dropped,
            "hardware_overrun": self.hardware_overrun,
            "stale": self.stale,
            "spurious": self.spurious,
            "raised_while_disabled": self.raised_while_disabled,
            "acknowledged": self.acknowledged,
            "uncleared": self.uncleared,
            "idle_work": self.idle_work,
            "reset_count": self.reset_count,
            "max_queue_depth": self.max_queue_depth,
            "max_pending_depth": self.max_pending_depth,
            "w1c_writes": list(self.w1c_writes),
        }

    def write_w1c(self, mask: int) -> None:
        self.w1c_writes.append(mask)
        self.status_register &= ~mask

    def relatch_pending_status(self) -> None:
        for record in self.pending:
            self.status_register |= record.raw_status

    def apply(self, event: dict[str, Any]) -> None:
        op = event.get("op")
        if not isinstance(op, str):
            raise ModelError("each event needs a string 'op'")

        before = self.snapshot()
        if op == "ENABLE":
            if not self.enabled:
                self.generation += 1
                self.enabled = True
        elif op == "DISABLE":
            self.enabled = False
        elif op == "RAISE":
            sample = event.get("sample")
            if isinstance(sample, bool) or not isinstance(sample, int):
                raise ModelError("RAISE needs integer 'sample'")
            timestamp = nonnegative_integer(event.get("timestamp", self.next_sequence - 1), "RAISE timestamp")
            raw_status = nonnegative_integer(event.get("raw_status", 1), "RAISE raw_status")
            if raw_status == 0:
                raise ModelError("RAISE raw_status must contain at least one bit")
            if not self.enabled:
                self.raised_while_disabled += 1
            elif len(self.pending) >= self.hardware_capacity:
                self.hardware_overrun += 1
            else:
                record = EventRecord(
                    generation=self.generation,
                    sequence=self.next_sequence,
                    timestamp=timestamp,
                    raw_status=raw_status,
                    sample=sample,
                )
                self.next_sequence += 1
                self.pending.append(record)
                self.status_register |= raw_status
                self.max_pending_depth = max(self.max_pending_depth, len(self.pending))
        elif op == "ISR":
            snapshot = self.status_register
            clear_mask = nonnegative_integer(event.get("clear_mask", snapshot), "ISR clear_mask")
            if snapshot == 0:
                self.spurious += 1
            elif not self.pending:
                # A latched status can remain after the associated data was lost.
                self.spurious += 1
                self.write_w1c(clear_mask)
            else:
                record = self.pending.popleft()
                self.acknowledged += 1
                self.write_w1c(clear_mask)
                if record.raw_status & ~clear_mask:
                    self.uncleared += 1
                self.relatch_pending_status()
                if len(self.queue) >= self.capacity:
                    self.dropped += 1
                else:
                    self.queue.append(record)
                    self.max_queue_depth = max(self.max_queue_depth, len(self.queue))
        elif op == "WORK":
            if not self.queue:
                self.idle_work += 1
            else:
                record = self.queue.popleft()
                if not self.enabled or record.generation != self.generation:
                    self.stale += 1
                else:
                    serialized = asdict(record)
                    self.handled_events.append(serialized)
                    self.handled_samples.append(record.sample)
                    self.handled_sequences.append(record.sequence)
        elif op == "RESET":
            # Queues and status are volatile. Diagnostic counters and the monotonic
            # session generation remain observable in this teaching model.
            self.enabled = False
            self.status_register = 0
            self.pending.clear()
            self.queue.clear()
            self.reset_count += 1
        else:
            raise ModelError(f"unsupported op: {op}")

        self.trace.append({"event": dict(event), "before": before, "after": self.snapshot()})

    def result(self) -> dict[str, Any]:
        final = self.snapshot()
        final["capacity"] = self.capacity
        final["hardware_capacity"] = self.hardware_capacity
        final["trace_length"] = len(self.trace)
        return final


def run_fixture(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    capacity = data.get("capacity", 2)
    hardware_capacity = data.get("hardware_capacity", 4)
    if isinstance(capacity, bool) or not isinstance(capacity, int):
        raise ModelError("capacity must be an integer")
    if isinstance(hardware_capacity, bool) or not isinstance(hardware_capacity, int):
        raise ModelError("hardware_capacity must be an integer")
    events = data.get("events")
    if not isinstance(events, list):
        raise ModelError("fixture needs an 'events' array")

    model = InterruptModel(capacity=capacity, hardware_capacity=hardware_capacity)
    for event in events:
        if not isinstance(event, dict):
            raise ModelError("event must be an object")
        model.apply(event)
    return model.result(), model.trace


def contains(actual: Any, expected: Any, path: str = "result") -> list[str]:
    errors: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object, got {type(actual).__name__}"]
        for key, value in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: missing")
            else:
                errors.extend(contains(actual[key], value, f"{path}.{key}"))
    elif actual != expected:
        errors.append(f"{path}: expected {expected!r}, got {actual!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    data = json.loads(args.fixture.read_text(encoding="utf-8"))
    result, trace = run_fixture(data)
    output: dict[str, Any] = {"result": result}
    if args.trace:
        output["trace"] = trace
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))

    if args.check:
        expected = data.get("expected")
        if not isinstance(expected, dict):
            raise ModelError("--check requires an 'expected' object")
        errors = contains(result, expected)
        if errors:
            for error in errors:
                print(f"CHECK FAILED: {error}")
            return 1
        print("CHECK OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ModelError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
