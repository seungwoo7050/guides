#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load_pratt() -> Any:
    path = ROOT / "examples/pratt-parser/pratt.py"
    spec = importlib.util.spec_from_file_location("guide_pratt", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def project(node: dict[str, Any]) -> object:
    if node["kind"] == "Int":
        return node["value"]
    if node["kind"] == "Neg":
        return ["neg", project(node["value"])]
    if node["kind"] == "Binary":
        return [node["op"], project(node["left"]), project(node["right"])]
    raise AssertionError(f"unknown node: {node}")


def main() -> int:
    pratt = load_pratt()
    cases = json.loads((HERE / "fixtures/expressions.json").read_text(encoding="utf-8"))
    for case in cases["expressions"]:
        assert project(pratt.parse(case["source"])) == case["projection"]
    for source in cases["invalid"]:
        try:
            pratt.parse(source)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid expression accepted: {source}")

    token_trace = json.loads((HERE / "reference/token-trace.json").read_text(encoding="utf-8"))
    source = token_trace["source"].encode("utf-8")
    starts: list[int] = []
    for token in token_trace["tokens"]:
        span = token["span"]
        assert span["source_id"] == token_trace["source_id"]
        assert 0 <= span["start"] <= span["end"] <= len(source)
        if token["kind"] != "EOF":
            assert source[span["start"] : span["end"]].decode("utf-8") == token["lexeme"]
        starts.append(span["start"])
    assert starts == sorted(starts)
    assert token_trace["tokens"][-1]["kind"] == "EOF"

    ast = json.loads((HERE / "reference/ast-projection.json").read_text(encoding="utf-8"))
    assert ast["projection"] == pratt.parse("1 + 2 * 3")
    known_bad = ["*", ["+", 1, 2], 3]
    assert known_bad != cases["expressions"][0]["projection"]
    print("PASS lab02 token slices Pratt precedence associativity recovery AST projection known-bad")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
