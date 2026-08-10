#!/usr/bin/env python3
"""Deterministic two-slot firmware update lifecycle model.

This is an executable state contract, not a production bootloader.  Metadata
commits are atomic in the model; POWER_LOSS fixtures expose the before/after
commit cut points explicitly.
"""

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
    hardware: str = "board-v1"
    schema_min: int = 1
    schema_max: int = 1


@dataclass
class UpdateModel:
    max_trial_attempts: int = 2
    hardware_id: str = "board-v1"
    data_schema: int = 1
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
    boot_ok: bool = False
    self_test_pass: bool = False
    errors: list[str] = field(default_factory=list)
    last_reason: str = "initial"
    trace: list[dict[str, Any]] = field(default_factory=list)
    metadata_sequence: int = 0
    _durable: dict[str, Any] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.max_trial_attempts <= 0:
            raise ModelError("max_trial_attempts must be greater than zero")
        if not isinstance(self.data_schema, int) or self.data_schema <= 0:
            raise ModelError("data_schema must be a positive integer")
        self._persist(initial=True)

    @staticmethod
    def image_dict(image: Image | None) -> dict[str, Any] | None:
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
            "boot_ok": self.boot_ok,
            "self_test_pass": self.self_test_pass,
            "hardware_id": self.hardware_id,
            "data_schema": self.data_schema,
            "metadata_sequence": self.metadata_sequence,
            "metadata": {
                "committed": True,
                "mode": self._durable.get("mode"),
                "current": self._durable.get("current"),
                "sequence": self.metadata_sequence,
            },
            "slots": {name: self.image_dict(image) for name, image in self.slots.items()},
            "errors": list(self.errors),
            "last_reason": self.last_reason,
        }

    def _persistent_state(self) -> dict[str, Any]:
        return {
            "slots": copy.deepcopy(self.slots),
            "current": self.current,
            "candidate": self.candidate,
            "previous": self.previous,
            "pending": self.pending,
            "mode": self.mode,
            "trial_attempts": self.trial_attempts,
            "data_schema": self.data_schema,
            "last_reason": self.last_reason,
        }

    def _persist(self, *, initial: bool = False) -> None:
        if not initial:
            self.metadata_sequence += 1
        self._durable = self._persistent_state()

    def _restore_after_power_loss(self) -> None:
        for key, value in self._durable.items():
            setattr(self, key, copy.deepcopy(value))
        self.boot_ok = False
        self.self_test_pass = False

    def inactive_slot(self) -> str:
        return "B" if self.current == "A" else "A"

    def add_error(self, code: str) -> None:
        self.errors.append(code)
        self.last_reason = code

    def image_bootable(self, image: Image | None, *, require_confirmed: bool = False) -> bool:
        return bool(
            image is not None
            and image.valid
            and image.compatible
            and image.hardware == self.hardware_id
            and image.schema_min <= self.data_schema <= image.schema_max
            and (image.confirmed or not require_confirmed)
        )

    def select_recovery_if_needed(self) -> None:
        current_image = None if self.current is None else self.slots.get(self.current)
        if self.image_bootable(current_image, require_confirmed=self.mode != "TRIAL"):
            return
        for name, image in self.slots.items():
            if self.image_bootable(image, require_confirmed=True):
                self.current = name
                self.mode = "CONFIRMED"
                self.previous = None
                self.candidate = None
                self.pending = False
                self.trial_attempts = 0
                self.last_reason = "selected_other_confirmed"
                self._persist()
                return
        self.current = None
        self.mode = "RECOVERY"
        self.previous = None
        self.pending = False
        self.last_reason = "no_bootable_confirmed_image"
        self._persist()

    def _commit_revert(self, reason: str) -> None:
        previous = self.previous
        image = None if previous is None else self.slots.get(previous)
        if self.image_bootable(image, require_confirmed=True):
            self.current = previous
            self.mode = "CONFIRMED"
            self.candidate = None
            self.previous = None
            self.pending = False
            self.trial_attempts = 0
            self.boot_ok = False
            self.self_test_pass = False
            self.last_reason = reason
            self._persist()
            return
        self.current = None
        self.mode = "RECOVERY"
        self.candidate = None
        self.previous = None
        self.pending = False
        self.trial_attempts = 0
        self.boot_ok = False
        self.self_test_pass = False
        self.last_reason = f"{reason}_without_compatible_previous"
        self._persist()

    def _commit_confirm(self) -> None:
        if self.current is None:
            self.add_error("cannot_confirm_without_current")
            return
        image = self.slots.get(self.current)
        if not self.image_bootable(image):
            self.add_error("cannot_confirm_unbootable_image")
            return
        assert image is not None
        image.confirmed = True
        self.mode = "CONFIRMED"
        self.previous = None
        self.candidate = None
        self.pending = False
        self.trial_attempts = 0
        self.boot_ok = False
        self.self_test_pass = False
        self.last_reason = "trial_confirmed"
        self._persist()

    def apply(self, event: dict[str, Any]) -> None:
        op = event.get("op")
        if not isinstance(op, str):
            raise ModelError("each event needs a string 'op'")
        before = self.snapshot()

        if op == "DOWNLOAD":
            if self.mode in {"TRIAL", "REVERTING"}:
                self.add_error("download_blocked_during_trial")
            else:
                version = event.get("version")
                valid = event.get("valid", True)
                compatible = event.get("compatible", True)
                if not isinstance(version, str) or not version:
                    raise ModelError("DOWNLOAD needs non-empty string 'version'")
                if not isinstance(valid, bool) or not isinstance(compatible, bool):
                    raise ModelError("valid and compatible must be booleans")
                schema_min = event.get("schema_min", 1)
                schema_max = event.get("schema_max", schema_min)
                if not isinstance(schema_min, int) or not isinstance(schema_max, int) or schema_min > schema_max:
                    raise ModelError("DOWNLOAD schema_min/schema_max are invalid")
                hardware = event.get("hardware", self.hardware_id if compatible else "incompatible-hardware")
                if not isinstance(hardware, str) or not hardware:
                    raise ModelError("DOWNLOAD hardware must be a non-empty string")
                slot = self.inactive_slot()
                self.slots[slot] = Image(
                    version=version,
                    valid=valid,
                    compatible=compatible,
                    confirmed=False,
                    hardware=hardware,
                    schema_min=schema_min,
                    schema_max=schema_max,
                )
                self.candidate = slot
                self.pending = False
                self.last_reason = f"downloaded_{version}_to_{slot}"
                self._persist()

        elif op == "MARK_PENDING":
            if self.candidate is None:
                self.add_error("no_candidate")
            else:
                image = self.slots[self.candidate]
                if image is None or not image.valid:
                    self.add_error("candidate_invalid")
                elif not image.compatible or image.hardware != self.hardware_id:
                    self.add_error("candidate_incompatible")
                elif not (image.schema_min <= self.data_schema <= image.schema_max):
                    self.add_error("candidate_schema_incompatible")
                else:
                    self.pending = True
                    self.last_reason = "candidate_pending"
                    self._persist()

        elif op == "RESET":
            self.boot_ok = False
            self.self_test_pass = False
            if self.pending and self.candidate is not None:
                candidate_image = self.slots.get(self.candidate)
                if not self.image_bootable(candidate_image):
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
                    self._persist()
            elif self.mode == "TRIAL":
                current_image = None if self.current is None else self.slots.get(self.current)
                if not self.image_bootable(current_image):
                    self._commit_revert("trial_image_invalid")
                elif self.trial_attempts >= self.max_trial_attempts:
                    self._commit_revert("trial_attempt_limit")
                else:
                    self.trial_attempts += 1
                    self.last_reason = f"trial_boot_{self.trial_attempts}"
                    self._persist()
            else:
                self.last_reason = "normal_reset"
                self.select_recovery_if_needed()

        elif op == "BOOT_OK":
            if self.mode != "TRIAL":
                self.add_error("boot_ok_outside_trial")
            else:
                self.boot_ok = True
                self.last_reason = "trial_boot_ok_unconfirmed"

        elif op == "SELF_TEST_PASS":
            if self.mode != "TRIAL":
                self.add_error("self_test_pass_outside_trial")
            else:
                self.self_test_pass = True
                self.last_reason = "trial_self_test_pass_unconfirmed"

        elif op == "CONFIRM":
            if self.mode != "TRIAL" or self.current is None:
                self.add_error("confirm_outside_trial")
            elif not (self.boot_ok and self.self_test_pass):
                self.add_error("confirm_gates_incomplete")
            else:
                self._commit_confirm()

        elif op == "SELF_TEST_FAIL":
            if self.mode != "TRIAL":
                self.add_error("self_test_fail_outside_trial")
            else:
                self.mode = "REVERTING"
                self._commit_revert("self_test_failed")

        elif op == "BEGIN_REVERT":
            if self.mode != "TRIAL":
                self.add_error("revert_outside_trial")
            else:
                self.mode = "REVERTING"
                self.last_reason = event.get("reason", "manual_revert")

        elif op == "COMMIT_REVERT":
            if self.mode != "REVERTING":
                self.add_error("commit_revert_outside_reverting")
            else:
                self._commit_revert(str(event.get("reason", self.last_reason)))

        elif op == "WATCHDOG_RESET":
            self.boot_ok = False
            self.self_test_pass = False
            if self.mode == "TRIAL":
                if self.trial_attempts >= self.max_trial_attempts:
                    self._commit_revert("watchdog_trial_attempt_limit")
                else:
                    self.trial_attempts += 1
                    self.last_reason = f"watchdog_trial_boot_{self.trial_attempts}"
                    self._persist()
            else:
                self.last_reason = "watchdog_reset_confirmed"
                self.select_recovery_if_needed()

        elif op == "COMMIT_SCHEMA":
            schema = event.get("schema")
            if self.mode != "TRIAL" or not isinstance(schema, int) or schema <= 0:
                self.add_error("schema_commit_not_allowed")
            else:
                current_image = None if self.current is None else self.slots.get(self.current)
                if current_image is None or not (current_image.schema_min <= schema <= current_image.schema_max):
                    self.add_error("schema_not_supported_by_trial")
                else:
                    self.data_schema = schema
                    self.last_reason = f"schema_{schema}_committed"
                    self._persist()

        elif op == "POWER_LOSS":
            point = event.get("point")
            if point == "confirm_before_commit":
                if self.mode != "TRIAL" or not (self.boot_ok and self.self_test_pass):
                    self.add_error("confirm_power_loss_without_gates")
                self._restore_after_power_loss()
                self.last_reason = "power_loss_confirm_before_commit"
            elif point == "confirm_after_commit":
                if self.mode != "TRIAL" or not (self.boot_ok and self.self_test_pass):
                    self.add_error("confirm_power_loss_without_gates")
                else:
                    self._commit_confirm()
                self._restore_after_power_loss()
                self.last_reason = "power_loss_confirm_after_commit"
            elif point == "revert_before_commit":
                if self.mode not in {"TRIAL", "REVERTING"}:
                    self.add_error("revert_power_loss_outside_trial")
                self._restore_after_power_loss()
                self.last_reason = "power_loss_revert_before_commit"
            elif point == "revert_after_commit":
                if self.mode not in {"TRIAL", "REVERTING"}:
                    self.add_error("revert_power_loss_outside_trial")
                else:
                    self._commit_revert(str(event.get("reason", "power_loss_revert")))
                self._restore_after_power_loss()
                self.last_reason = "power_loss_revert_after_commit"
            else:
                raise ModelError("unsupported POWER_LOSS point")

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
                self._persist()

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
    model = UpdateModel(
        max_trial_attempts=max_attempts,
        hardware_id=data.get("hardware_id", "board-v1"),
        data_schema=data.get("data_schema", 1),
    )
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
