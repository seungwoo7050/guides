#!/usr/bin/env python3
"""Deterministic interrupt-to-worker state model used by the guide."""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Deque


class ModelError(ValueError):
    """Raised for malformed fixture input."""


@dataclass(frozen=True)
class EventRecord:
    generation: int
    sequence: int
    sample: int


@dataclass
class InterruptModel:
    capacity: int
    enabled: bool = False
    generation: int = 0
    next_sequence: int = 1
    pending: Deque[EventRecord] = field(default_factory=deque)
    queue: Deque[EventRecord] = field(default_factory=deque)
    handled_samples: list[int] = field(default_factory=list)
    handled_sequences: list[int] = field(default_factory=list)
    dropped: int = 0
    stale: int = 0
    spurious: int = 0
    raised_while_disabled: int = 0
    acknowledged: int = 0
    idle_work: int = 0
    trace: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ModelError("capacity must be greater than zero")

    def snapshot(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "generation": self.generation,
            "pending": [asdict(item) for item in self.pending],
            "queue": [asdict(item) for item in self.queue],
            "handled_samples": list(self.handled_samples),
            "handled_sequences": list(self.handled_sequences),
            "dropped": self.dropped,
            "stale": self.stale,
            "spurious": self.spurious,
            "raised_while_disabled": self.raised_while_disabled,
            "acknowledged": self.acknowledged,
            "idle_work": self.idle_work,
        }

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
            if not isinstance(sample, int):
                raise ModelError("RAISE needs integer 'sample'")
            if not self.enabled:
                self.raised_while_disabled += 1
            else:
                self.pending.append(
                    EventRecord(
                        generation=self.generation,
                        sequence=self.next_sequence,
                        sample=sample,
                    )
                )
                self.next_sequence += 1
        elif op == "ISR":
            if not self.pending:
                self.spurious += 1
            else:
                record = self.pending.popleft()
                self.acknowledged += 1
                if len(self.queue) >= self.capacity:
                    self.dropped += 1
                else:
                    self.queue.append(record)
        elif op == "WORK":
            if not self.queue:
                self.idle_work += 1
            else:
                record = self.queue.popleft()
                if not self.enabled or record.generation != self.generation:
                    self.stale += 1
                else:
                    self.handled_samples.append(record.sample)
                    self.handled_sequences.append(record.sequence)
        elif op == "RESET":
            self.enabled = False
            self.generation = 0
            self.next_sequence = 1
            self.pending.clear()
            self.queue.clear()
        else:
            raise ModelError(f"unsupported op: {op}")

        self.trace.append({"event": event, "before": before, "after": self.snapshot()})

    def result(self) -> dict[str, Any]:
        final = self.snapshot()
        final["capacity"] = self.capacity
        final["trace_length"] = len(self.trace)
        return final


def run_fixture(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    capacity = data.get("capacity", 2)
    if not isinstance(capacity, int):
        raise ModelError("capacity must be an integer")
    events = data.get("events")
    if not isinstance(events, list):
        raise ModelError("fixture needs an 'events' array")

    model = InterruptModel(capacity=capacity)
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
