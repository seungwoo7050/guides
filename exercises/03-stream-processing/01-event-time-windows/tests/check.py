#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:event-time-windows"
CONTRACT = "GUIDE_CONTRACT:event-time-windows"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "window_totals", None)) or not callable(
        getattr(module, "lateness_class", None)
    ):
        raise TypeError("window_totals and lateness_class are required")
    return module


def expect_value_error(call, message: str) -> None:
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def check(solution) -> None:
    events = [
        {"event_id": "e2", "key": "store", "occurred_at": "2026-08-09T00:05:00Z", "amount": 11},
        {"event_id": "e1", "key": "store", "occurred_at": "2026-08-09T00:04:59Z", "amount": 7},
        {"event_id": "e1", "key": "store", "occurred_at": "2026-08-09T00:04:59+00:00", "amount": 7},
        {"event_id": "e3", "key": "other", "occurred_at": "2026-08-09T09:01:00+09:00", "amount": 3},
    ]
    original = copy.deepcopy(events)
    expected = [
        {"key": "other", "window_start": "2026-08-09T00:00:00Z", "window_end": "2026-08-09T00:05:00Z", "total": 3},
        {"key": "store", "window_start": "2026-08-09T00:00:00Z", "window_end": "2026-08-09T00:05:00Z", "total": 7},
        {"key": "store", "window_start": "2026-08-09T00:05:00Z", "window_end": "2026-08-09T00:10:00Z", "total": 11},
    ]
    assert solution.window_totals(events, 5) == expected, "event-time window totals are wrong"
    assert solution.window_totals(list(reversed(events)), 5) == expected, "arrival order must not change windows"
    assert events == original, "windowing must not mutate input"
    assert solution.window_totals([], 5) == [], "empty input must produce no windows"
    expect_value_error(lambda: solution.window_totals([], 0), "invalid window must fail even for empty input")
    expect_value_error(lambda: solution.window_totals([], True), "boolean window size must be rejected")

    conflict = [events[1], {**events[1], "amount": 8}]
    expect_value_error(lambda: solution.window_totals(conflict, 5), "conflicting event ID must fail")
    expect_value_error(
        lambda: solution.window_totals(list(reversed(conflict)), 5),
        "conflicting event ID must fail in either arrival order",
    )
    expect_value_error(
        lambda: solution.window_totals(
            [{"event_id": "bad", "key": "s", "occurred_at": "2026-08-09T00:00:00", "amount": 1}], 5
        ),
        "naive event timestamp must be rejected",
    )
    expect_value_error(
        lambda: solution.window_totals(
            [{"event_id": "bad", "key": "s", "occurred_at": "2026-08-09T00:00:00Z", "amount": True}], 5
        ),
        "boolean amount must be rejected",
    )

    assert solution.lateness_class("2026-08-09T00:10:00Z", "2026-08-09T00:10:00Z", 5) == "ON_TIME"
    assert solution.lateness_class("2026-08-09T00:10:00Z", "2026-08-09T00:15:00Z", 5) == "CORRECTABLE"
    assert solution.lateness_class("2026-08-09T00:10:00Z", "2026-08-09T00:15:00.001Z", 5) == "DROPPED"
    expect_value_error(
        lambda: solution.lateness_class("2026-08-09T00:10:00", "2026-08-09T00:12:00Z", 5),
        "naive event time must be rejected",
    )
    expect_value_error(
        lambda: solution.lateness_class("2026-08-09T00:10:00Z", "2026-08-09T00:12:00", 5),
        "naive watermark must be rejected",
    )
    expect_value_error(
        lambda: solution.lateness_class("2026-08-09T00:10:00Z", "2026-08-09T00:12:00Z", -1),
        "negative lateness must be rejected",
    )


def main() -> int:
    try:
        solution = load(Path(sys.argv[1]).resolve())
        check(solution)
    except AssertionError as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"{CONTRACT}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("OK event-time-windows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
