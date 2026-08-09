#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import importlib.util
import os
import random
import subprocess
import sys
from pathlib import Path

CODE = "GUIDE_SEMANTIC:partitioned-join"
CONTRACT = "GUIDE_CONTRACT:partitioned-join"


def load(path: Path):
    spec = importlib.util.spec_from_file_location("learner_solution", path / "solution.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load solution")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "partition_for", None)) or not callable(
        getattr(module, "join_and_report", None)
    ):
        raise TypeError("partition_for and join_and_report are required")
    return module


def partition_in_process(solution_file: Path, seed: str) -> int:
    code = (
        "import importlib.util,sys;"
        "s=importlib.util.spec_from_file_location('candidate',sys.argv[1]);"
        "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
        "print(m.partition_for('customer-1',97))"
    )
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = seed
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-B", "-c", code, str(solution_file)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
        timeout=3,
    )
    return int(result.stdout.strip())


def expected_partition(key: str, partition_count: int) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % partition_count


def expect_value_error(call, message: str) -> None:
    try:
        call()
    except ValueError:
        return
    raise AssertionError(message)


def check(solution, target: Path) -> None:
    process_values = {partition_in_process(target / "solution.py", seed) for seed in ("1", "2", "random")}
    assert len(process_values) == 1, "partition hash must be stable across Python processes"
    for key in ("customer-1", "A", "B", "C", "", "고객-1"):
        for partition_count in (1, 4, 97):
            assert solution.partition_for(key, partition_count) == expected_partition(key, partition_count), (
                "partition_for must use SHA-256 first 8 bytes as unsigned big-endian modulo partition_count"
            )

    left = [{"key": "A", "l": 2}, {"key": "A", "l": 1}, {"key": "B", "l": 3}]
    right = [{"key": "A", "r": 2}, {"key": "A", "r": 1}, {"key": "C", "r": 4}]
    original = copy.deepcopy((left, right))
    report = solution.join_and_report(left, right, 4, 3, 3)
    assert report["joined"] == [
        {"key": "A", "left": {"key": "A", "l": 1}, "right": {"key": "A", "r": 1}},
        {"key": "A", "left": {"key": "A", "l": 1}, "right": {"key": "A", "r": 2}},
        {"key": "A", "left": {"key": "A", "l": 2}, "right": {"key": "A", "r": 1}},
        {"key": "A", "left": {"key": "A", "l": 2}, "right": {"key": "A", "r": 2}},
    ], "joined must preserve the exact four encoded Cartesian rows"
    assert report["strategy"] == "broadcast-right", "broadcast threshold is inclusive"
    assert report["hot_keys"] == ["A"], "hot keys must use combined left/right load"
    expected_loads = [0, 0, 0, 0]
    for row in left + right:
        expected_loads[expected_partition(row["key"], 4)] += 1
    assert report["partition_loads"] == expected_loads, (
        "partition loads must place every left/right row in partition_for(key)"
    )
    assert (left, right) == original, "join must not mutate inputs"
    shuffled_left = list(left)
    shuffled_right = list(right)
    random.Random(3).shuffle(shuffled_left)
    random.Random(4).shuffle(shuffled_right)
    assert report == solution.join_and_report(shuffled_left, shuffled_right, 4, 3, 3), (
        "report must be input-order independent"
    )
    assert solution.join_and_report([], [{"key": "x"}], 2, 1, 0)["strategy"] == "shuffle-both"
    assert solution.join_and_report([], [], 2, 1, 0)["strategy"] == "broadcast-right"

    expect_value_error(lambda: solution.join_and_report([], [], 0, 1, 0), "invalid partition count must fail")
    expect_value_error(lambda: solution.join_and_report([], [], 2, 0, 0), "invalid hot threshold must fail")
    expect_value_error(lambda: solution.join_and_report([], [], 2, 1, -1), "invalid broadcast threshold must fail")
    expect_value_error(lambda: solution.partition_for("x", True), "boolean partition count must fail")
    expect_value_error(
        lambda: solution.join_and_report([{"key": 1}], [], 2, 1, 0), "non-string record key must fail"
    )


def main() -> int:
    try:
        target = Path(sys.argv[1]).resolve()
        solution = load(target)
        check(solution, target)
    except AssertionError as exc:
        print(f"{CODE}: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"{CONTRACT}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("OK partitioned-join")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
