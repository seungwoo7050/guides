#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from typing import Any, Callable

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1


class RuntimeFault(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def checked(value: int) -> int:
    if not I64_MIN <= value <= I64_MAX:
        raise RuntimeFault("MICA4002", "integer overflow")
    return value


def checked_add(left: int, right: int) -> int:
    return checked(left + right)


def checked_neg(value: int) -> int:
    if value == I64_MIN:
        raise RuntimeFault("MICA4002", "integer overflow")
    return -value


def checked_div(left: int, right: int) -> int:
    if right == 0:
        raise RuntimeFault("MICA4001", "division by zero")
    if left == I64_MIN and right == -1:
        raise RuntimeFault("MICA4002", "integer overflow")
    quotient = abs(left) // abs(right)
    return -quotient if (left < 0) != (right < 0) else quotient


def short_circuit_and(left: bool, right: Callable[[], bool]) -> bool:
    return right() if left else False


@dataclass(slots=True)
class Budget:
    max_steps: int
    max_depth: int
    steps: int = 0
    depth: int = 0

    def tick(self) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise RuntimeFault("MICA4005", "execution limit exceeded")

    def enter(self) -> None:
        self.depth += 1
        if self.depth > self.max_depth:
            self.depth -= 1
            raise RuntimeFault("MICA4004", "call depth exceeded")

    def leave(self) -> None:
        if self.depth <= 0:
            raise AssertionError("unbalanced frame leave")
        self.depth -= 1


def execute_case(case: dict[str, Any]) -> dict[str, Any]:
    stdout = ""
    rhs_calls = 0
    try:
        operation = case["operation"]
        args = case.get("args", [])
        if operation == "add":
            value: object = checked_add(*args)
        elif operation == "div":
            value = checked_div(*args)
        elif operation == "neg":
            value = checked_neg(*args)
        elif operation == "and":
            def right() -> bool:
                nonlocal rhs_calls
                rhs_calls += 1
                if case.get("right_fault"):
                    raise RuntimeFault("MICA4999", "right operand evaluated")
                return bool(case["right"])

            value = short_circuit_and(bool(case["left"]), right)
        elif operation == "steps":
            budget = Budget(int(case["max_steps"]), 100)
            for _ in range(int(case["ticks"])):
                budget.tick()
            value = budget.steps
        elif operation == "depth":
            budget = Budget(100, int(case["max_depth"]))
            entered = 0
            try:
                for _ in range(int(case["enters"])):
                    budget.enter()
                    entered += 1
            finally:
                for _ in range(entered):
                    budget.leave()
            value = entered
        else:
            raise AssertionError(f"unknown operation: {operation}")
        return {"diagnostic": None, "return_value": value, "rhs_calls": rhs_calls, "stdout": stdout}
    except RuntimeFault as fault:
        return {"diagnostic": fault.code, "return_value": None, "rhs_calls": rhs_calls, "stdout": stdout}


def self_test() -> None:
    assert execute_case({"operation": "add", "args": [40, 2]})["return_value"] == 42
    lazy = execute_case({"operation": "and", "left": False, "right": True, "right_fault": True})
    assert lazy == {"diagnostic": None, "return_value": False, "rhs_calls": 0, "stdout": ""}
    assert execute_case({"operation": "div", "args": [1, 0]})["diagnostic"] == "MICA4001"
    assert execute_case({"operation": "add", "args": [I64_MAX, 1]})["diagnostic"] == "MICA4002"
    assert execute_case({"operation": "div", "args": [I64_MIN, -1]})["diagnostic"] == "MICA4002"
    assert execute_case({"operation": "neg", "args": [I64_MIN]})["diagnostic"] == "MICA4002"
    assert execute_case({"operation": "steps", "max_steps": 3, "ticks": 4})["diagnostic"] == "MICA4005"
    assert execute_case({"operation": "depth", "max_depth": 2, "enters": 3})["diagnostic"] == "MICA4004"
    print("PASS runtime semantics checked-i64 short-circuit step-budget call-depth")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        cases = [
            {"operation": "add", "args": [40, 2]},
            {"operation": "and", "left": False, "right": True, "right_fault": True},
        ]
        print(json.dumps([execute_case(case) for case in cases], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
