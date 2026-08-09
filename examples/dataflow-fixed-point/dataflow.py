#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    name: str
    uses: frozenset[str]
    defs: frozenset[str]
    successors: tuple[str, ...]


BLOCKS = {
    "entry": Block("entry", frozenset(), frozenset({"x", "y"}), ("test",)),
    "test": Block("test", frozenset({"x"}), frozenset(), ("body", "exit")),
    "body": Block("body", frozenset({"x", "y"}), frozenset({"y"}), ("test",)),
    "exit": Block("exit", frozenset({"y"}), frozenset(), ()),
}


def liveness(blocks: dict[str, Block], initial_order: list[str] | None = None) -> dict[str, dict[str, list[str]]]:
    names = list(blocks)
    predecessors = {name: set() for name in names}
    for name, block in blocks.items():
        for successor in block.successors:
            if successor not in blocks:
                raise ValueError(f"unknown successor {successor!r}")
            predecessors[successor].add(name)
    live_in = {name: set() for name in names}
    live_out = {name: set() for name in names}
    order = initial_order or list(reversed(names))
    work = deque(order)
    queued = set(order)
    while work:
        name = work.popleft()
        queued.discard(name)
        block = blocks[name]
        new_out = set().union(*(live_in[s] for s in block.successors)) if block.successors else set()
        new_in = set(block.uses) | (new_out - set(block.defs))
        if new_in != live_in[name] or new_out != live_out[name]:
            live_in[name] = new_in
            live_out[name] = new_out
            for pred in sorted(predecessors[name]):
                if pred not in queued:
                    work.append(pred)
                    queued.add(pred)
    return {
        name: {"in": sorted(live_in[name]), "out": sorted(live_out[name])}
        for name in sorted(names)
    }


def self_test() -> None:
    expected = {
        "body": {"in": ["x", "y"], "out": ["x", "y"]},
        "entry": {"in": [], "out": ["x", "y"]},
        "exit": {"in": ["y"], "out": []},
        "test": {"in": ["x", "y"], "out": ["x", "y"]},
    }
    assert liveness(BLOCKS) == expected
    assert liveness(BLOCKS, ["entry", "test", "body", "exit"]) == expected
    broken = dict(BLOCKS)
    broken["body"] = Block("body", frozenset({"x", "y"}), frozenset({"y"}), ())
    assert liveness(broken) != expected
    print("PASS data-flow fixed point")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        print(json.dumps(liveness(BLOCKS), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
