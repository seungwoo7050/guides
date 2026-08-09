#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from typing import Any


class SemanticError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Symbol:
    symbol_id: str
    name: str
    kind: str
    type: str
    declaration: str


class ScopeStack:
    def __init__(self) -> None:
        self._scopes: list[dict[str, Symbol]] = [{}]
        self._next_id = 1

    def enter(self) -> None:
        self._scopes.append({})

    def exit(self) -> None:
        if len(self._scopes) == 1:
            raise SemanticError("cannot exit the root scope")
        self._scopes.pop()

    def declare(self, name: str, kind: str, type_name: str, declaration: str) -> Symbol:
        current = self._scopes[-1]
        if name in current:
            raise SemanticError(f"duplicate declaration: {name}")
        symbol = Symbol(f"s{self._next_id}", name, kind, type_name, declaration)
        self._next_id += 1
        current[name] = symbol
        return symbol

    def resolve(self, name: str) -> Symbol:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise SemanticError(f"unknown name: {name}")


def binary_type(operator: str, left: str, right: str) -> str:
    rules = {
        ("+", "Int", "Int"): "Int",
        ("<", "Int", "Int"): "Bool",
        ("==", "Int", "Int"): "Bool",
        ("==", "Bool", "Bool"): "Bool",
        ("&&", "Bool", "Bool"): "Bool",
    }
    try:
        return rules[(operator, left, right)]
    except KeyError as exc:
        raise SemanticError(f"invalid operands: {left} {operator} {right}") from exc


def all_paths_return(statement: dict[str, Any]) -> bool:
    kind = statement["kind"]
    if kind == "Return":
        return True
    if kind == "Block":
        reachable = True
        for child in statement["statements"]:
            if reachable and all_paths_return(child):
                reachable = False
        return not reachable
    if kind == "If":
        alternate = statement.get("else")
        return alternate is not None and all_paths_return(statement["then"]) and all_paths_return(alternate)
    return False


def merge_definitely_assigned(predecessors: list[set[str]]) -> set[str]:
    if not predecessors:
        return set()
    return set.intersection(*(set(facts) for facts in predecessors))


def observed_trace() -> dict[str, Any]:
    scopes = ScopeStack()
    outer = scopes.declare("x", "local", "Int", "10:11")
    before = scopes.resolve("x")
    scopes.enter()
    inner = scopes.declare("x", "local", "Bool", "30:31")
    inside = scopes.resolve("x")
    scopes.exit()
    after = scopes.resolve("x")
    return {
        "symbols": [asdict(outer), asdict(inner)],
        "references": [before.symbol_id, inside.symbol_id, after.symbol_id],
        "types": [binary_type("+", "Int", "Int"), binary_type("<", "Int", "Int")],
        "definitely_assigned": sorted(merge_definitely_assigned([{"a", "b"}, {"a", "c"}])),
    }


def self_test() -> None:
    trace = observed_trace()
    assert trace["references"] == ["s1", "s2", "s1"]
    assert trace["types"] == ["Int", "Bool"]
    assert trace["definitely_assigned"] == ["a"]
    scope = ScopeStack()
    scope.declare("x", "local", "Int", "0:1")
    try:
        scope.declare("x", "local", "Int", "2:3")
    except SemanticError:
        pass
    else:
        raise AssertionError("same-scope duplicate was accepted")
    try:
        binary_type("+", "Bool", "Int")
    except SemanticError:
        pass
    else:
        raise AssertionError("invalid type combination was accepted")
    returning = {"kind": "If", "then": {"kind": "Return"}, "else": {"kind": "Return"}}
    assert all_paths_return(returning)
    assert not all_paths_return({"kind": "If", "then": {"kind": "Return"}})
    print("PASS semantic model shadowing duplicate types all-path-return intersection")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(observed_trace(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
