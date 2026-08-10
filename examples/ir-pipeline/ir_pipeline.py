#!/usr/bin/env python3
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from typing import Any

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1
TERMINATORS = {"JUMP", "BRANCH", "RETURN"}


class IRVerificationError(ValueError):
    pass


class IRRuntimeError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


Program = dict[str, Any]


def _uses(instruction: dict[str, Any]) -> list[str]:
    op = instruction["op"]
    if op in {"ADD_CHECKED", "DIV_CHECKED"}:
        return [instruction["left"], instruction["right"]]
    if op == "BRANCH":
        return [instruction["condition"]]
    if op == "RETURN":
        return [instruction["value"]]
    return []


def _targets(instruction: dict[str, Any]) -> list[str]:
    if instruction["op"] == "JUMP":
        return [instruction["target"]]
    if instruction["op"] == "BRANCH":
        return [instruction["then"], instruction["else"]]
    return []


def verify(program: Program) -> None:
    blocks = program.get("blocks")
    entry = program.get("entry")
    if not isinstance(blocks, dict) or not blocks or entry not in blocks:
        raise IRVerificationError("invalid blocks or entry")
    definitions: set[str] = set()
    allowed = {"PARAM", "CONST", "ADD_CHECKED", "DIV_CHECKED", *TERMINATORS}
    for block_name, instructions in blocks.items():
        if not isinstance(instructions, list) or not instructions:
            raise IRVerificationError(f"empty block: {block_name}")
        terminal_positions = [index for index, item in enumerate(instructions) if item.get("op") in TERMINATORS]
        if terminal_positions != [len(instructions) - 1]:
            raise IRVerificationError(f"block must have one final terminator: {block_name}")
        for instruction in instructions:
            op = instruction.get("op")
            if op not in allowed:
                raise IRVerificationError(f"unknown op: {op}")
            result = instruction.get("result")
            if result is not None:
                if not isinstance(result, str) or not result.startswith("%") or result in definitions:
                    raise IRVerificationError(f"invalid or duplicate result: {result}")
                definitions.add(result)
            for target in _targets(instruction):
                if target not in blocks:
                    raise IRVerificationError(f"unknown target: {target}")
    for instructions in blocks.values():
        for instruction in instructions:
            for operand in _uses(instruction):
                if operand not in definitions:
                    raise IRVerificationError(f"undefined value: {operand}")


def reachability_trace(program: Program) -> list[list[str]]:
    verify(program)
    reached = {program["entry"]}
    trace = [sorted(reached)]
    while True:
        expanded = set(reached)
        for name in reached:
            expanded.update(_targets(program["blocks"][name][-1]))
        if expanded == reached:
            return trace
        reached = expanded
        trace.append(sorted(reached))


def reachable(program: Program) -> set[str]:
    return set(reachability_trace(program)[-1])


def _checked(value: int) -> int:
    if not I64_MIN <= value <= I64_MAX:
        raise IRRuntimeError("MICA4002")
    return value


def execute(program: Program, arguments: dict[str, int] | None = None, *, max_steps: int = 100) -> int:
    verify(program)
    arguments = arguments or {}
    values: dict[str, int | bool] = {}
    block = program["entry"]
    steps = 0
    while True:
        jumped = False
        for instruction in program["blocks"][block]:
            steps += 1
            if steps > max_steps:
                raise IRRuntimeError("MICA4004")
            op = instruction["op"]
            if op == "PARAM":
                values[instruction["result"]] = int(arguments[instruction["name"]])
            elif op == "CONST":
                values[instruction["result"]] = instruction["value"]
            elif op == "ADD_CHECKED":
                values[instruction["result"]] = _checked(int(values[instruction["left"]]) + int(values[instruction["right"]]))
            elif op == "DIV_CHECKED":
                left = int(values[instruction["left"]])
                right = int(values[instruction["right"]])
                if right == 0:
                    raise IRRuntimeError("MICA4001")
                if left == I64_MIN and right == -1:
                    raise IRRuntimeError("MICA4002")
                quotient = abs(left) // abs(right)
                values[instruction["result"]] = -quotient if (left < 0) != (right < 0) else quotient
            elif op == "JUMP":
                block = instruction["target"]
                jumped = True
                break
            elif op == "BRANCH":
                block = instruction["then"] if values[instruction["condition"]] else instruction["else"]
                jumped = True
                break
            elif op == "RETURN":
                return int(values[instruction["value"]])
        if not jumped:
            raise AssertionError("verified block did not transfer control")


def optimize(program: Program) -> Program:
    verify(program)
    result = deepcopy(program)
    for instructions in result["blocks"].values():
        constants: dict[str, int] = {}
        for index, instruction in enumerate(instructions):
            op = instruction["op"]
            if op == "CONST":
                constants[instruction["result"]] = instruction["value"]
            elif op in {"ADD_CHECKED", "DIV_CHECKED"}:
                left = constants.get(instruction["left"])
                right = constants.get(instruction["right"])
                if left is None or right is None:
                    continue
                if op == "ADD_CHECKED":
                    value = left + right
                    if not I64_MIN <= value <= I64_MAX:
                        continue
                else:
                    if right == 0 or (left == I64_MIN and right == -1):
                        continue
                    quotient = abs(left) // abs(right)
                    value = -quotient if (left < 0) != (right < 0) else quotient
                replacement = {"op": "CONST", "result": instruction["result"], "value": value}
                instructions[index] = replacement
                constants[instruction["result"]] = value
    keep = reachable(result)
    result["blocks"] = {name: body for name, body in result["blocks"].items() if name in keep}
    verify(result)
    return result


def constant_program() -> Program:
    return {
        "schema_version": 1,
        "entry": "entry",
        "blocks": {
            "entry": [
                {"op": "CONST", "result": "%a", "value": 40},
                {"op": "CONST", "result": "%b", "value": 2},
                {"op": "ADD_CHECKED", "result": "%sum", "left": "%a", "right": "%b"},
                {"op": "JUMP", "target": "exit"},
            ],
            "exit": [{"op": "RETURN", "value": "%sum"}],
            "dead": [
                {"op": "CONST", "result": "%zero", "value": 0},
                {"op": "DIV_CHECKED", "result": "%trap", "left": "%a", "right": "%zero"},
                {"op": "RETURN", "value": "%trap"},
            ],
        },
    }


def division_program() -> Program:
    return {
        "schema_version": 1,
        "entry": "entry",
        "blocks": {
            "entry": [
                {"op": "PARAM", "result": "%x", "name": "x"},
                {"op": "DIV_CHECKED", "result": "%q", "left": "%x", "right": "%x"},
                {"op": "RETURN", "value": "%q"},
            ]
        },
    }


def known_bad_x_div_x(program: Program) -> Program:
    result = deepcopy(program)
    for instructions in result["blocks"].values():
        for index, instruction in enumerate(instructions):
            if instruction["op"] == "DIV_CHECKED" and instruction["left"] == instruction["right"]:
                instructions[index] = {"op": "CONST", "result": instruction["result"], "value": 1}
    return result


def self_test() -> None:
    original = constant_program()
    optimized = optimize(original)
    assert reachability_trace(original) == [["entry"], ["entry", "exit"]]
    assert execute(original) == execute(optimized) == 42
    assert set(optimized["blocks"]) == {"entry", "exit"}
    assert optimized["blocks"]["entry"][2] == {"op": "CONST", "result": "%sum", "value": 42}
    division = division_program()
    assert execute(division, {"x": 2}) == execute(known_bad_x_div_x(division), {"x": 2}) == 1
    try:
        execute(division, {"x": 0})
    except IRRuntimeError as fault:
        assert fault.code == "MICA4001"
    else:
        raise AssertionError("division by zero did not trap")
    assert execute(known_bad_x_div_x(division), {"x": 0}) == 1
    invalid = constant_program()
    invalid["blocks"]["entry"].append({"op": "RETURN", "value": "%sum"})
    try:
        verify(invalid)
    except IRVerificationError:
        pass
    else:
        raise AssertionError("instruction after terminator was accepted")
    print("PASS IR pipeline verifier reachability checked-fold differential known-bad")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        original = constant_program()
        print(json.dumps({"before": original, "after": optimize(original)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
