#!/usr/bin/env python3
"""Deterministic two-slot firmware update lifecycle model."""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


class ModelError(ValueError):
    """Raised for malformed fixture input."""


@dataclass
class Image:
    version: str
    valid: bool
    compatible: bool
    confirmed: bool


@dataclass
class UpdateModel:
    max_trial_attempts: int = 2
    slots: dict[str, Image | None] = field(
        default_factory=lambda: {
            "A": Image(version="v1", valid=True, compatible=True, confirmed=True),
            "B": None,
        }
    )
    current: str | None = "A"
    candidate: str | None = None
    previous: str | None = None
    pending: bool = False
    mode: str = "CONFIRMED"
    trial_attempts: int = 0
    errors: list[str] = field(default_factory=list)
    last_reason: str = "initial"
    trace: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.max_trial_attempts <= 0:
            raise ModelError("max_trial_attempts must be greater than zero")

    def image_dict(self, image: Image | None) -> dict[str, Any] | None:
        return None if image is None else asdict(image)

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "current": self.current,
            "candidate": self.candidate,
            "previous": self.previous,
            "pending": self.pending,
            "trial_attempts": self.trial_attempts,
            "max_trial_attempts": self.max_trial_attempts,
            "slots": {name: self.image_dict(image) for name, image in self.slots.items()},
            "errors": list(self.errors),
            "last_reason": self.last_reason,
        }

    def inactive_slot(self) -> str:
        return "B" if self.current == "A" else "A"

    def add_error(self, code: str) -> None:
        self.errors.append(code)
        self.last_reason = code

    def select_recovery_if_needed(self) -> None:
        if self.current is not None:
            image = self.slots.get(self.current)
            if image is not None and image.valid and image.compatible:
                return
        for name, image in self.slots.items():
            if image is not None and image.valid and image.compatible and image.confirmed:
                self.current = name
                self.mode = "CONFIRMED"
                self.previous = None
                self.candidate = None
                self.pending = False
                self.trial_attempts = 0
                self.last_reason = "selected_other_confirmed"
                return
        self.current = None
        self.mode = "RECOVERY"
        self.previous = None
        self.pending = False
        self.last_reason = "no_bootable_confirmed_image"

    def revert(self, reason: str) -> None:
        previous = self.previous
        if previous is not None:
            image = self.slots.get(previous)
            if image is not None and image.valid and image.compatible and image.confirmed:
                self.current = previous
                self.mode = "CONFIRMED"
                self.candidate = None
                self.previous = None
                self.pending = False
                self.trial_attempts = 0
                self.last_reason = reason
                return
        self.current = None
        self.mode = "RECOVERY"
        self.candidate = None
        self.previous = None
        self.pending = False
        self.trial_attempts = 0
        self.last_reason = f"{reason}_without_previous"

    def apply(self, event: dict[str, Any]) -> None:
        op = event.get("op")
        if not isinstance(op, str):
            raise ModelError("each event needs a string 'op'")
        before = self.snapshot()

        if op == "DOWNLOAD":
            version = event.get("version")
            valid = event.get("valid", True)
            compatible = event.get("compatible", True)
            if not isinstance(version, str) or not version:
                raise ModelError("DOWNLOAD needs non-empty string 'version'")
            if not isinstance(valid, bool) or not isinstance(compatible, bool):
                raise ModelError("valid and compatible must be booleans")
            slot = self.inactive_slot()
            self.slots[slot] = Image(
                version=version,
                valid=valid,
                compatible=compatible,
                confirmed=False,
            )
            self.candidate = slot
            self.pending = False
            self.last_reason = f"downloaded_{version}_to_{slot}"

        elif op == "MARK_PENDING":
            if self.candidate is None:
                self.add_error("no_candidate")
            else:
                image = self.slots[self.candidate]
                if image is None or not image.valid:
                    self.add_error("candidate_invalid")
                elif not image.compatible:
                    self.add_error("candidate_incompatible")
                else:
                    self.pending = True
                    self.last_reason = "candidate_pending"

        elif op == "RESET":
            if self.pending and self.candidate is not None:
                candidate_image = self.slots.get(self.candidate)
                if candidate_image is None or not candidate_image.valid or not candidate_image.compatible:
                    self.pending = False
                    self.add_error("pending_candidate_not_bootable")
                    self.select_recovery_if_needed()
                else:
                    self.previous = self.current
                    self.current = self.candidate
                    self.mode = "TRIAL"
                    self.pending = False
                    self.trial_attempts = 1
                    self.last_reason = "trial_boot_1"
            elif self.mode == "TRIAL":
                current_image = None if self.current is None else self.slots.get(self.current)
                if current_image is None or not current_image.valid or not current_image.compatible:
                    self.revert("trial_image_invalid")
                elif self.trial_attempts >= self.max_trial_attempts:
                    self.revert("trial_attempt_limit")
                else:
                    self.trial_attempts += 1
                    self.last_reason = f"trial_boot_{self.trial_attempts}"
            else:
                self.last_reason = "normal_reset"
                self.select_recovery_if_needed()

        elif op == "BOOT_OK":
            if self.mode != "TRIAL":
                self.add_error("boot_ok_outside_trial")
            else:
                self.last_reason = "trial_boot_ok_unconfirmed"

        elif op == "CONFIRM":
            if self.mode != "TRIAL" or self.current is None:
                self.add_error("confirm_outside_trial")
            else:
                image = self.slots.get(self.current)
                if image is None or not image.valid or not image.compatible:
                    self.add_error("cannot_confirm_unbootable_image")
                else:
                    image.confirmed = True
                    self.mode = "CONFIRMED"
                    self.previous = None
                    self.candidate = None
                    self.pending = False
                    self.trial_attempts = 0
                    self.last_reason = "trial_confirmed"

        elif op == "SELF_TEST_FAIL":
            if self.mode != "TRIAL":
                self.add_error("self_test_fail_outside_trial")
            else:
                self.revert("self_test_failed")

        elif op == "WATCHDOG_RESET":
            if self.mode == "TRIAL":
                if self.trial_attempts >= self.max_trial_attempts:
                    self.revert("watchdog_trial_attempt_limit")
                else:
                    self.trial_attempts += 1
                    self.last_reason = f"watchdog_trial_boot_{self.trial_attempts}"
            else:
                self.last_reason = "watchdog_reset_confirmed"
                self.select_recovery_if_needed()

        elif op == "CORRUPT":
            slot = event.get("slot")
            if slot not in self.slots:
                raise ModelError("CORRUPT slot must be A or B")
            image = self.slots[slot]
            if image is None:
                self.add_error(f"corrupt_empty_{slot}")
            else:
                image.valid = False
                self.last_reason = f"corrupted_{slot}"

        elif op == "RECOVER":
            self.select_recovery_if_needed()

        else:
            raise ModelError(f"unsupported op: {op}")

        self.trace.append({"event": copy.deepcopy(event), "before": before, "after": self.snapshot()})

    def result(self) -> dict[str, Any]:
        result = self.snapshot()
        result["trace_length"] = len(self.trace)
        return result


def run_fixture(data: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    max_attempts = data.get("max_trial_attempts", 2)
    if not isinstance(max_attempts, int):
        raise ModelError("max_trial_attempts must be an integer")
    events = data.get("events")
    if not isinstance(events, list):
        raise ModelError("fixture needs an 'events' array")

    model = UpdateModel(max_trial_attempts=max_attempts)
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
