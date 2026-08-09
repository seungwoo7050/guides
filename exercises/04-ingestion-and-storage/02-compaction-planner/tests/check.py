#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import random
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:compaction-planner"
CONTRACT = "GUIDE_CONTRACT:compaction-planner"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "plan_compaction", None)):
        raise TypeError("plan_compaction is required")
    return module


def file(path: str, size: int, *, partition: str = "d1", schema: int = 1, spec: int = 1, rows: int = 1, active: bool = True) -> dict:
    return {
        "path": path,
        "partition": partition,
        "schema_id": schema,
        "spec_id": spec,
        "bytes": size,
        "rows": rows,
        "active": active,
    }


def expect_value_error(call, message: str) -> None:
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def check(solution) -> None:
    files = [
        file("b", 30, rows=3),
        file("a", 20, rows=2),
        file("c", 10, schema=2),
        file("d", 80, partition="d2"),
        file("e", 5, active=False),
    ]
    original = copy.deepcopy(files)
    plans = solution.plan_compaction(files, 80, 4)
    assert plans == [{
        "partition": "d1",
        "schema_id": 1,
        "spec_id": 1,
        "inputs": ["a", "b"],
        "input_bytes": 50,
        "input_rows": 5,
    }], "inactive/exact-target/singleton boundary handling is wrong"
    assert files == original, "planner must not mutate input"
    shuffled = list(files)
    random.Random(4).shuffle(shuffled)
    assert solution.plan_compaction(shuffled, 80, 4) == plans, "plan must be input-order independent"

    pairable = [file("a60", 60), file("b60", 60), file("c20", 20), file("d20", 20)]
    paired = solution.plan_compaction(pairable, 80, 3)
    assert len(paired) == 2 and sorted(plan["input_bytes"] for plan in paired) == [80, 80], (
        "first-fit decreasing must not strand pairable files"
    )
    assert sorted(len(plan["inputs"]) for plan in paired) == [2, 2]

    limited = [file(str(index), 10) for index in range(6)]
    assert [len(plan["inputs"]) for plan in solution.plan_compaction(limited, 100, 3)] == [3, 3]
    separate = [file("p1", 10), file("p2", 10, partition="d2"), file("s1", 10, schema=2)]
    assert solution.plan_compaction(separate, 100, 3) == [], "boundary singletons must not be mixed"

    expect_value_error(lambda: solution.plan_compaction([], 0, 2), "invalid target must fail on empty input")
    expect_value_error(lambda: solution.plan_compaction([], 10, 1), "invalid max files must fail on empty input")
    expect_value_error(lambda: solution.plan_compaction([], True, 2), "boolean target must fail")
    expect_value_error(
        lambda: solution.plan_compaction([file("same", 1), file("same", 2)], 10, 2),
        "duplicate file paths must fail",
    )
    bad_bool = file("bool", 1)
    bad_bool["bytes"] = False
    expect_value_error(lambda: solution.plan_compaction([bad_bool], 10, 2), "boolean bytes must fail")
    bad_rows = file("rows", 1)
    bad_rows["rows"] = -1
    expect_value_error(lambda: solution.plan_compaction([bad_rows], 10, 2), "negative rows must fail")


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
    print("OK compaction-planner")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
