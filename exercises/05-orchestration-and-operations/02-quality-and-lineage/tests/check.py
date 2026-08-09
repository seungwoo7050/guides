#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:quality-lineage"
CONTRACT = "GUIDE_CONTRACT:quality-lineage"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "evaluate_and_emit", None)):
        raise TypeError("evaluate_and_emit is required")
    return module


def run(solution, rows, **overrides):
    values = {
        "run_id": "run-42",
        "job_name": "daily-sales",
        "input_dataset": {"namespace": "source", "name": "orders", "snapshot": "lsn:120"},
        "output_dataset": {"namespace": "analytics", "name": "daily_sales", "snapshot": "snap:abc"},
        "code_revision": "git:deadbeef",
    }
    values.update(overrides)
    return solution.evaluate_and_emit(rows, **values)


def expect_value_error(call, message: str) -> None:
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def check(solution) -> None:
    rows = [
        {"id": "a", "event_time": "2026-08-09T00:00:00Z", "value": 1},
        {"id": "b", "event_time": "2026-08-09T09:01:00+09:00", "value": 2},
    ]
    original = copy.deepcopy(rows)
    good = run(solution, rows)
    assert rows == original, "quality evaluation must not mutate rows"
    assert good["quality"] == {
        "passed": True,
        "row_count": 2,
        "distinct_keys": 2,
        "duplicate_keys": [],
        "null_required": 0,
        "invalid_event_time": 0,
        "latest_event_time": "2026-08-09T00:01:00Z",
    }, "good quality report is wrong"
    lineage = good["lineage"]
    assert lineage["event_type"] == "COMPLETE"
    assert lineage["run_id"] == "run-42" and lineage["code_revision"] == "git:deadbeef"
    assert lineage["inputs"][0]["snapshot"] == "lsn:120"
    assert lineage["outputs"][0]["snapshot"] == "snap:abc"

    bad = run(solution, [
        {"id": "a", "event_time": "2026-08-09T00:00:00Z", "value": 1},
        {"id": "a", "event_time": "not-a-time", "value": None},
        {"id": "", "event_time": "2026-08-09T00:02:00Z", "value": 3},
    ])
    assert bad["quality"]["passed"] is False
    assert bad["quality"]["duplicate_keys"] == ["a"]
    assert bad["quality"]["null_required"] == 2, "null value and empty ID must be measured"
    assert bad["quality"]["invalid_event_time"] == 1, "invalid timestamp must be quality evidence"
    assert bad["lineage"]["event_type"] == "FAIL" and bad["lineage"]["outputs"] == []
    assert bad["lineage"]["attempted_output"]["snapshot"] == "snap:abc"

    expect_value_error(lambda: run(solution, [], run_id=""), "empty run ID must be rejected")
    expect_value_error(lambda: run(solution, [], job_name=None), "non-string job name must be rejected")
    expect_value_error(lambda: run(solution, [], code_revision=""), "empty code revision must be rejected")
    expect_value_error(
        lambda: run(
            solution,
            [],
            input_dataset={"namespace": "source", "name": "orders", "snapshot": ""},
        ),
        "dataset snapshot must be pinned",
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
    print("OK quality-lineage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
