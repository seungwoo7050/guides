#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load_example() -> Any:
    path = ROOT / "examples/runtime-semantics/runtime.py"
    spec = importlib.util.spec_from_file_location("guide_runtime_semantics", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    runtime = load_example()
    fixtures = json.loads((HERE / "fixtures/runtime-cases.json").read_text(encoding="utf-8"))["cases"]
    expected = json.loads((HERE / "reference/runtime-trace.json").read_text(encoding="utf-8"))["outcomes"]
    actual = []
    for case in fixtures:
        outcome = runtime.execute_case(case)
        actual.append({"name": case["name"], **outcome})
    assert actual == expected
    assert runtime.checked_div(-7, 2) == -3
    assert runtime.checked_div(7, -2) == -3
    assert runtime.checked_div(-7, -2) == 3

    by_name = {item["name"]: item for item in actual}
    assert by_name["short-circuit"]["rhs_calls"] == 0
    eager_known_bad = {**by_name["short-circuit"], "diagnostic": "MICA4999", "rhs_calls": 1}
    unchecked_known_bad = {**by_name["addition-overflow"], "diagnostic": None, "return_value": 2**63}
    assert eager_known_bad != by_name["short-circuit"]
    assert unchecked_known_bad != by_name["addition-overflow"]

    assert [runtime.execute_case(case) for case in fixtures] == [runtime.execute_case(case) for case in fixtures]
    print("PASS lab04 deterministic runtime short-circuit checked-i64 budgets diagnostics known-bad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
