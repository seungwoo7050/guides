#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:run-ledger-backfill"
CONTRACT = "GUIDE_CONTRACT:run-ledger-backfill"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "plan_backfill", None)) or not callable(getattr(module, "transition", None)):
        raise TypeError("plan_backfill and transition are required")
    return module


def expect_value_error(call, message: str) -> None:
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def check(solution) -> None:
    existing = [
        {"logical_date": "2026-08-01", "attempt": 1, "status": "PUBLISHED"},
        {"logical_date": "2026-08-02", "attempt": 1, "status": "FAILED"},
    ]
    original = copy.deepcopy(existing)
    out = solution.plan_backfill(existing, "2026-08-01", "2026-08-03", "failed", 10)
    assert [(row["logical_date"], row["attempt"]) for row in out] == [
        ("2026-08-02", 2), ("2026-08-03", 1)
    ], "failed policy or inclusive missing-date planning is wrong"
    assert existing == original, "planning must not mutate ledger"
    assert solution.plan_backfill([], "2026-08-01", "2026-08-01", "none", 1)[0]["attempt"] == 1

    active = [{"logical_date": "2026-08-01", "attempt": 1, "status": "VALIDATING"}]
    assert [row["logical_date"] for row in solution.plan_backfill(active, "2026-08-01", "2026-08-03", "completed", 2)] == [
        "2026-08-02", "2026-08-03"
    ], "VALIDATING must block its date and capacity must bound new plans"
    superseded = [{"logical_date": "2026-08-01", "attempt": 2, "status": "SUPERSEDED"}]
    assert solution.plan_backfill(superseded, "2026-08-01", "2026-08-01", "completed", 1)[0]["attempt"] == 3
    assert solution.plan_backfill(superseded, "2026-08-01", "2026-08-01", "none", 1) == []

    expect_value_error(
        lambda: solution.plan_backfill([], "bad", "2026-08-01", "none", 0),
        "zero capacity must not bypass date validation",
    )
    expect_value_error(
        lambda: solution.plan_backfill([], "2026-08-02", "2026-08-01", "none", 0),
        "zero capacity must not bypass range validation",
    )
    expect_value_error(
        lambda: solution.plan_backfill(
            [{"logical_date": "bad", "attempt": 1, "status": "FAILED"}],
            "2026-08-01", "2026-08-01", "none", 0,
        ),
        "zero capacity must not bypass ledger validation",
    )
    duplicate = [
        {"logical_date": "2026-08-01", "attempt": 1, "status": "FAILED"},
        {"logical_date": "2026-08-01", "attempt": 1, "status": "PUBLISHED"},
    ]
    expect_value_error(
        lambda: solution.plan_backfill(duplicate, "2026-08-01", "2026-08-01", "failed", 1),
        "duplicate run identity must fail",
    )
    expect_value_error(
        lambda: solution.plan_backfill(
            [{"logical_date": "2026-08-01", "attempt": True, "status": "FAILED"}],
            "2026-08-01", "2026-08-01", "failed", 1,
        ),
        "boolean attempt must fail",
    )
    expect_value_error(
        lambda: solution.plan_backfill(
            [{"logical_date": "2026-08-01", "attempt": 1, "status": "UNKNOWN"}],
            "2026-08-01", "2026-08-01", "failed", 1,
        ),
        "unknown status must fail",
    )

    run = {"logical_date": "2026-08-01", "attempt": 1, "status": "PLANNED"}
    run_original = copy.deepcopy(run)
    running = solution.transition(run, "RUNNING")
    validating = solution.transition(running, "VALIDATING")
    published = solution.transition(validating, "PUBLISHED")
    assert solution.transition(published, "SUPERSEDED")["status"] == "SUPERSEDED"
    assert run == run_original, "transition must not mutate input"
    expect_value_error(lambda: solution.transition(published, "RUNNING"), "invalid transition must fail")


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
    print("OK run-ledger-backfill")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
