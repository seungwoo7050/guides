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
    path = ROOT / "examples/semantic-model/semantic_model.py"
    spec = importlib.util.spec_from_file_location("guide_semantic_model", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    model = load_example()
    cases = json.loads((HERE / "fixtures/semantic-cases.json").read_text(encoding="utf-8"))
    for case in cases["type_rules"]:
        assert model.binary_type(case["operator"], case["left"], case["right"]) == case["expected"]
    for case in cases["invalid_type_rules"]:
        try:
            model.binary_type(case["operator"], case["left"], case["right"])
        except model.SemanticError:
            pass
        else:
            raise AssertionError(f"invalid type rule accepted: {case}")
    for case in cases["all_paths_return"]:
        assert model.all_paths_return(case["statement"]) is case["expected"]

    merge = cases["definite_assignment"]
    actual_merge = sorted(model.merge_definitely_assigned([set(items) for items in merge["predecessors"]]))
    assert actual_merge == merge["expected"]
    assert actual_merge != merge["known_bad_union"]

    summary = json.loads((HERE / "reference/semantic-summary.json").read_text(encoding="utf-8"))
    symbols = {symbol["id"]: symbol for symbol in summary["symbols"]}
    assert len(symbols) == len(summary["symbols"])
    for reference in summary["references"]:
        assert reference["symbol_id"] in symbols
        assert symbols[reference["symbol_id"]]["name"] == reference["name"]
    assert [reference["symbol_id"] for reference in summary["references"]] == ["s2", "s3", "s2"]
    assert symbols["s2"]["declaration"] != symbols["s3"]["declaration"]
    assert summary["flow"] == {"all_paths_return": True, "definitely_assigned_at_join": ["s2"]}
    assert summary["diagnostics"] == []

    trace = model.observed_trace()
    assert trace["references"] == ["s1", "s2", "s1"]
    print("PASS lab03 SymbolId shadowing scope-exit type-rules all-path-return merge known-bad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
