#!/usr/bin/env python3
"""Exhaustive linearizability checker for a small read/write register."""
from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Operation:
    id: str
    process: str
    op: str
    value: Any
    invoke: int
    complete: int | None
    result: Any
    pending: bool = False


def parse_operations(history: dict[str, Any]) -> tuple[list[Operation], list[Operation]]:
    completed: list[Operation] = []
    pending: list[Operation] = []
    for raw in history["operations"]:
        operation = Operation(
            id=raw["id"],
            process=raw["process"],
            op=raw["op"],
            value=raw.get("value"),
            invoke=int(raw["invoke"]),
            complete=None if raw.get("complete") is None else int(raw["complete"]),
            result=raw.get("result"),
            pending=raw.get("complete") is None,
        )
        (pending if operation.pending else completed).append(operation)
    return completed, pending


def apply_register(state: Any, operation: Operation) -> tuple[bool, Any]:
    if operation.op == "write":
        if operation.result not in ("OK", None):
            return False, state
        return True, operation.value
    if operation.op == "read":
        return operation.result == state, state
    raise ValueError(f"unsupported operation: {operation.op}")


def build_predecessors(operations: list[Operation]) -> dict[str, set[str]]:
    predecessors = {operation.id: set() for operation in operations}
    for left in operations:
        for right in operations:
            if left.id == right.id:
                continue
            if left.complete is not None and left.complete < right.invoke:
                predecessors[right.id].add(left.id)
            if (
                left.process == right.process
                and left.complete is not None
                and right.complete is not None
                and left.invoke < right.invoke
            ):
                predecessors[right.id].add(left.id)
    return predecessors


def search(operations: list[Operation], initial: Any) -> tuple[list[str] | None, int]:
    predecessors = build_predecessors(operations)
    by_id = {operation.id: operation for operation in operations}
    explored = 0
    memo: set[tuple[frozenset[str], str]] = set()

    def walk(done: frozenset[str], state: Any, order: list[str]) -> list[str] | None:
        nonlocal explored
        explored += 1
        memo_key = (done, json.dumps(state, sort_keys=True))
        if memo_key in memo:
            return None
        memo.add(memo_key)
        if len(done) == len(operations):
            return list(order)

        ready = [
            operation
            for operation in operations
            if operation.id not in done and predecessors[operation.id].issubset(done)
        ]
        ready.sort(key=lambda op: (op.invoke, op.id))
        for operation in ready:
            valid, next_state = apply_register(state, operation)
            if not valid:
                continue
            witness = walk(done | {operation.id}, next_state, order + [operation.id])
            if witness is not None:
                return witness
        return None

    return walk(frozenset(), initial, []), explored


def check_history(history: dict[str, Any], initial: Any = 0) -> dict[str, Any]:
    completed, pending = parse_operations(history)
    # A pending read has no observed result and can only be dropped in this small checker.
    pending_writes = [
        Operation(
            id=op.id,
            process=op.process,
            op=op.op,
            value=op.value,
            invoke=op.invoke,
            complete=None,
            result="OK",
            pending=True,
        )
        for op in pending
        if op.op == "write"
    ]

    total_explored = 0
    for count in range(len(pending_writes) + 1):
        for included in itertools.combinations(pending_writes, count):
            witness, explored = search(completed + list(included), initial)
            total_explored += explored
            if witness is not None:
                return {
                    "id": history["id"],
                    "linearizable": True,
                    "witness": witness,
                    "included_pending": [op.id for op in included],
                    "explored_states": total_explored,
                }
    return {
        "id": history["id"],
        "linearizable": False,
        "witness": None,
        "included_pending": [],
        "explored_states": total_explored,
    }


def check_file(data: dict[str, Any]) -> list[dict[str, Any]]:
    initial = data.get("object", {}).get("initial", 0)
    return [check_history(history, initial) for history in data["histories"]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("histories", type=Path)
    args = parser.parse_args()
    data = json.loads(args.histories.read_text(encoding="utf-8"))
    print(json.dumps(check_file(data), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
