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
    path = ROOT / "examples/ir-pipeline/ir_pipeline.py"
    spec = importlib.util.spec_from_file_location("guide_ir_pipeline", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def rejected(model: Any, program: dict[str, Any]) -> None:
    try:
        model.verify(program)
    except model.IRVerificationError:
        return
    raise AssertionError(f"invalid IR accepted: {program}")


def main() -> int:
    model = load_example()
    cases = json.loads((HERE / "fixtures/ir-cases.json").read_text(encoding="utf-8"))
    reference = json.loads((HERE / "reference/ir-pipeline.json").read_text(encoding="utf-8"))
    original = model.constant_program()
    optimized = model.optimize(original)
    assert model.reachability_trace(original) == reference["analysis"]["iterations"]
    assert sorted(original["blocks"]) == reference["pass"]["before_blocks"]
    assert sorted(optimized["blocks"]) == reference["pass"]["after_blocks"]
    assert optimized["blocks"]["entry"][2] == reference["pass"]["folded"]
    for case in cases["normal"]:
        assert model.execute(original, case["arguments"]) == case["expected"]
        assert model.execute(optimized, case["arguments"]) == case["expected"]

    invalid = model.constant_program()
    invalid["blocks"]["entry"].append({"op": "RETURN", "value": "%sum"})
    rejected(model, invalid)
    invalid = model.constant_program()
    invalid["blocks"]["entry"][-1]["target"] = "missing"
    rejected(model, invalid)
    invalid = model.constant_program()
    invalid["blocks"]["exit"][0]["value"] = "%missing"
    rejected(model, invalid)

    division = model.division_program()
    bad = model.known_bad_x_div_x(division)
    assert model.execute(division, {"x": 2}) == model.execute(bad, {"x": 2}) == 1
    try:
        model.execute(division, {"x": 0})
    except model.IRRuntimeError as fault:
        assert fault.code == "MICA4001"
    else:
        raise AssertionError("trap-preserving case did not trap")
    assert model.execute(bad, {"x": 0}) == 1
    print("PASS lab05 CFG verifier fixed-point checked pass differential trap-preservation known-bad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
