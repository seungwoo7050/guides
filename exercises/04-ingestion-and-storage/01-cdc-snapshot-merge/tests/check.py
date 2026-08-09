#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:cdc-snapshot-merge"
CONTRACT = "GUIDE_CONTRACT:cdc-snapshot-merge"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "materialize", None)):
        raise TypeError("materialize is required")
    return module


def expect_value_error(call, message: str) -> None:
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def check(solution) -> None:
    snapshot = [
        {"key": "o1", "position": 10, "value": {"status": "NEW"}},
        {"key": "o2", "position": 20, "value": {"status": "PAID"}},
    ]
    changes = [
        {"key": "o1", "position": 12, "operation": "UPDATE", "after": {"status": "PAID"}},
        {"key": "o1", "position": 11, "operation": "UPDATE", "after": {"status": "CANCELLED"}},
        {"key": "o2", "position": 21, "operation": "DELETE", "after": None},
        {"key": "o2", "position": 19, "operation": "UPDATE", "after": {"status": "NEW"}},
        {"key": "o3", "position": 30, "operation": "DELETE", "after": None},
        {"key": "o3", "position": 29, "operation": "INSERT", "after": {"status": "STALE"}},
        {"key": "o3", "position": 31, "operation": "INSERT", "after": {"status": "NEW"}},
        {"key": "o3", "position": 31, "operation": "INSERT", "after": {"status": "NEW"}},
    ]
    original_snapshot = copy.deepcopy(snapshot)
    original_changes = copy.deepcopy(changes)
    expected = {"o1": {"status": "PAID"}, "o3": {"status": "NEW"}}
    assert solution.materialize(snapshot, changes) == expected, "snapshot/change materialization is wrong"
    assert solution.materialize(snapshot, list(reversed(changes))) == expected, "arrival order changed state"
    assert snapshot == original_snapshot and changes == original_changes, "materialize must not mutate inputs"

    delete_only = [
        {"key": "o1", "position": 11, "operation": "DELETE", "after": None},
        {"key": "o1", "position": 9, "operation": "UPDATE", "after": {"status": "STALE"}},
    ]
    assert solution.materialize(snapshot[:1], delete_only) == {}, "tombstone must block stale resurrection"

    conflict = [
        {"key": "o1", "position": 12, "operation": "UPDATE", "after": {"status": "A"}},
        {"key": "o1", "position": 12, "operation": "UPDATE", "after": {"status": "B"}},
    ]
    expect_value_error(lambda: solution.materialize([], conflict), "same-position change conflict must fail")
    expect_value_error(
        lambda: solution.materialize([], list(reversed(conflict))),
        "same-position conflict must fail in either arrival order",
    )
    snapshot_conflict = [
        {"key": "o1", "position": 10, "value": {"status": "A"}},
        {"key": "o1", "position": 10, "value": {"status": "B"}},
    ]
    expect_value_error(
        lambda: solution.materialize(snapshot_conflict, []), "same-position snapshot conflict must fail"
    )
    expect_value_error(
        lambda: solution.materialize(
            [], [{"key": "o1", "position": 1, "operation": "DELETE", "after": {"status": "X"}}]
        ),
        "DELETE payload must be null",
    )
    expect_value_error(
        lambda: solution.materialize(
            [{"key": "o1", "position": 10, "value": {"status": "A"}}],
            [{"key": "o1", "position": 9, "operation": "MYSTERY", "after": None}],
        ),
        "invalid stale changes must not bypass input validation",
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
    print("OK cdc-snapshot-merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
