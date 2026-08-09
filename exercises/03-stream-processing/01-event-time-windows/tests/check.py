#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:event-time-windows"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        solution = load(Path(sys.argv[1]).resolve())
        events = [
            {"event_id": "e2", "key": "store", "occurred_at": "2026-08-09T00:05:00Z", "amount": 11},
            {"event_id": "e1", "key": "store", "occurred_at": "2026-08-09T00:04:59Z", "amount": 7},
            {"event_id": "e1", "key": "store", "occurred_at": "2026-08-09T00:04:59Z", "amount": 7},
            {"event_id": "e3", "key": "other", "occurred_at": "2026-08-09T00:01:00+00:00", "amount": 3},
        ]
        expected = [
            {"key": "other", "window_start": "2026-08-09T00:00:00Z", "window_end": "2026-08-09T00:05:00Z", "total": 3},
            {"key": "store", "window_start": "2026-08-09T00:00:00Z", "window_end": "2026-08-09T00:05:00Z", "total": 7},
            {"key": "store", "window_start": "2026-08-09T00:05:00Z", "window_end": "2026-08-09T00:10:00Z", "total": 11},
        ]
        assert solution.window_totals(events, 5) == expected
        assert solution.window_totals(list(reversed(events)), 5) == expected
        assert solution.lateness_class("2026-08-09T00:10:00Z", "2026-08-09T00:09:00Z", 5) == "ON_TIME"
        assert solution.lateness_class("2026-08-09T00:10:00Z", "2026-08-09T00:12:00Z", 5) == "CORRECTABLE"
        assert solution.lateness_class("2026-08-09T00:10:00Z", "2026-08-09T00:16:00Z", 5) == "DROPPED"
        try:
            solution.window_totals([
                {"event_id": "bad", "key": "s", "occurred_at": "2026-08-09T00:00:00", "amount": 1}
            ], 5)
        except ValueError:
            pass
        else:
            raise AssertionError("naive timestamp must be rejected")
    except Exception as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    print("OK event-time-windows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
