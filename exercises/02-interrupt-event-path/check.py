#!/usr/bin/env python3
"""Check an interrupt event model against the public exercise contract."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


EXERCISE_ROOT = Path(__file__).resolve().parent
FIXTURE_ROOT = EXERCISE_ROOT / "fixtures"
REQUIRED_FIXTURES = (
    "normal.json",
    "two-before-isr.json",
    "queue-overflow.json",
    "burst-overflow.json",
    "spurious.json",
    "disabled-raise.json",
    "stale-generation.json",
    "reset-policy.json",
    "w1c-status.json",
    "w1c-partial-clear.json",
    "hardware-overrun.json",
)
EVENT_FIELDS = {"generation", "sequence", "timestamp", "raw_status", "sample"}


class CheckError(RuntimeError):
    pass


def load_submission(path: Path):
    model_path = path / "model.py" if path.is_dir() else path
    if not model_path.is_file():
        raise CheckError(f"submission model does not exist: {model_path}")
    spec = importlib.util.spec_from_file_location(
        f"interrupt_submission_{abs(hash(model_path.resolve()))}", model_path.resolve()
    )
    if spec is None or spec.loader is None:
        raise CheckError(f"cannot load submission: {model_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise CheckError(f"submission import failed: {exc}") from exc
    if not callable(getattr(module, "run_fixture", None)):
        raise CheckError("submission must expose run_fixture(data)")
    return module, model_path


def contains(actual: Any, expected: Any, path: str = "result") -> list[str]:
    errors: list[str] = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{path}: expected object"]
        for key, value in expected.items():
            if key not in actual:
                errors.append(f"{path}.{key}: missing")
            else:
                errors.extend(contains(actual[key], value, f"{path}.{key}"))
    elif actual != expected:
        errors.append(f"{path}: expected {expected!r}, got {actual!r}")
    return errors


def load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURE_ROOT / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckError(f"cannot read required fixture {name}: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("expected"), dict):
        raise CheckError(f"required fixture has no expected object: {name}")
    return value


def run_checks(module: Any) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def record(check_id: str, passed: bool, message: str, actual: Any = None) -> None:
        checks.append({"id": check_id, "passed": passed, "message": message, "actual": actual})

    for name in REQUIRED_FIXTURES:
        data = load_fixture(name)
        try:
            first = module.run_fixture(data)
            second = module.run_fixture(data)
        except Exception as exc:
            record(f"fixture.{name}", False, "fixture execution raised", repr(exc))
            continue
        if (
            not isinstance(first, tuple)
            or len(first) != 2
            or not isinstance(first[0], dict)
            or not isinstance(first[1], list)
        ):
            record(f"fixture.{name}", False, "run_fixture must return (result dict, trace list)", repr(first))
            continue
        result, trace = first
        expectation_errors = contains(result, data["expected"])
        record(
            f"fixture.{name}",
            not expectation_errors,
            "final public behavior matches the fixture",
            expectation_errors,
        )
        record(
            f"deterministic.{name}",
            first == second,
            "same event input produces the same result and trace",
            None if first == second else "runs differ",
        )
        capacity = result.get("capacity")
        hardware_capacity = result.get("hardware_capacity")
        bounded = isinstance(capacity, int) and isinstance(hardware_capacity, int)
        if bounded:
            bounded = result.get("max_queue_depth", capacity + 1) <= capacity
            bounded = bounded and result.get("max_pending_depth", hardware_capacity + 1) <= hardware_capacity
            for transition in trace:
                after = transition.get("after") if isinstance(transition, dict) else None
                if not isinstance(after, dict):
                    bounded = False
                    break
                if len(after.get("queue", [])) > capacity or len(after.get("pending", [])) > hardware_capacity:
                    bounded = False
                    break
        record(f"bounded.{name}", bounded, "hardware pending and worker queue never exceed capacity")
        handled = result.get("handled_events", [])
        event_shape = isinstance(handled, list) and all(
            isinstance(item, dict) and EVENT_FIELDS <= set(item) for item in handled
        )
        record(f"event-shape.{name}", event_shape, "handled events preserve generation, sequence, timestamp, status, and sample")
    return checks


def emit(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return
    if result["status"] == "error":
        print(f"ERROR: {result['error']}", file=sys.stderr)
        return
    for check in result["checks"]:
        if not check["passed"]:
            print(f"FAIL {check['id']}: {check['message']}")
            if check.get("actual"):
                print(f"  {check['actual']!r}")
    summary = result["summary"]
    print(f"{result['status'].upper()} {result['exercise']} passed={summary['passed']} failed={summary['failed']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        module, model_path = load_submission(args.submission)
        checks = run_checks(module)
    except CheckError as exc:
        result = {"exercise": "02-interrupt-event-path", "status": "error", "error": str(exc)}
        emit(result, args.json)
        return 2
    failed = sum(not item["passed"] for item in checks)
    result = {
        "exercise": "02-interrupt-event-path",
        "submission": str(model_path),
        "status": "pass" if failed == 0 else "fail",
        "checks": checks,
        "summary": {"passed": len(checks) - failed, "failed": failed},
    }
    emit(result, args.json)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
