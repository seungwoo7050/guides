#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:quality-lineage"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(solution, rows):
    return solution.evaluate_and_emit(
        rows,
        run_id="run-42",
        job_name="daily-sales",
        input_dataset={"namespace": "source", "name": "orders", "snapshot": "lsn:120"},
        output_dataset={"namespace": "analytics", "name": "daily_sales", "snapshot": "snap:abc"},
        code_revision="git:deadbeef",
    )


def main() -> int:
    try:
        solution = load(Path(sys.argv[1]).resolve())
        good = run(solution, [
            {"id": "a", "event_time": "2026-08-09T00:00:00Z", "value": 1},
            {"id": "b", "event_time": "2026-08-09T00:01:00+00:00", "value": 2},
        ])
        assert good["quality"] == {
            "passed": True,
            "row_count": 2,
            "distinct_keys": 2,
            "duplicate_keys": [],
            "null_required": 0,
            "latest_event_time": "2026-08-09T00:01:00Z",
        }
        lineage = good["lineage"]
        assert lineage["event_type"] == "COMPLETE"
        assert lineage["run_id"] == "run-42"
        assert lineage["code_revision"] == "git:deadbeef"
        assert lineage["inputs"][0]["snapshot"] == "lsn:120"
        assert lineage["outputs"][0]["snapshot"] == "snap:abc"

        bad = run(solution, [
            {"id": "a", "event_time": "2026-08-09T00:00:00Z", "value": 1},
            {"id": "a", "event_time": "2026-08-09T00:01:00Z", "value": None},
        ])
        assert bad["quality"]["passed"] is False
        assert bad["quality"]["duplicate_keys"] == ["a"]
        assert bad["quality"]["null_required"] == 1
        assert bad["lineage"]["event_type"] == "FAIL"
        assert bad["lineage"]["outputs"] == []
        assert bad["lineage"]["attempted_output"]["snapshot"] == "snap:abc"
    except Exception as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    print("OK quality-lineage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
