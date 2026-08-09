#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any


class VerificationError(ValueError):
    pass


@dataclass(frozen=True)
class Value:
    type: str
    value: int


Program = list[tuple[Any, ...]]


def verify(program: Program, constants: list[Value], return_type: str = "Int") -> None:
    stack: list[str] = []
    saw_return = False
    for ip, instruction in enumerate(program):
        if not instruction:
            raise VerificationError(f"{ip}: empty instruction")
        op = instruction[0]
        if op == "CONST":
            if len(instruction) != 2 or not isinstance(instruction[1], int):
                raise VerificationError(f"{ip}: malformed CONST")
            index = instruction[1]
            if not 0 <= index < len(constants):
                raise VerificationError(f"{ip}: constant index out of range")
            stack.append(constants[index].type)
        elif op in ("ADD", "MUL"):
            if len(stack) < 2:
                raise VerificationError(f"{ip}: stack underflow")
            right, left = stack.pop(), stack.pop()
            if left != "Int" or right != "Int":
                raise VerificationError(f"{ip}: {op} requires Int, Int")
            stack.append("Int")
        elif op == "RETURN":
            if ip != len(program) - 1:
                raise VerificationError(f"{ip}: this linear example requires final RETURN")
            if stack != [return_type]:
                raise VerificationError(f"{ip}: return stack is {stack}, expected [{return_type}]")
            saw_return = True
        else:
            raise VerificationError(f"{ip}: unknown opcode {op!r}")
    if not saw_return:
        raise VerificationError("program has no RETURN")


def execute(program: Program, constants: list[Value]) -> Value:
    verify(program, constants)
    stack: list[Value] = []
    for instruction in program:
        op = instruction[0]
        if op == "CONST":
            stack.append(constants[instruction[1]])
        elif op in ("ADD", "MUL"):
            right, left = stack.pop(), stack.pop()
            result = left.value + right.value if op == "ADD" else left.value * right.value
            stack.append(Value("Int", result))
        elif op == "RETURN":
            return stack.pop()
    raise AssertionError("verified program did not return")


def self_test() -> None:
    constants = [Value("Int", 2), Value("Int", 3), Value("Int", 4)]
    program: Program = [("CONST", 0), ("CONST", 1), ("CONST", 2), ("MUL",), ("ADD",), ("RETURN",)]
    assert execute(program, constants) == Value("Int", 14)
    bad_programs: list[Program] = [
        [("ADD",), ("RETURN",)],
        [("CONST", 99), ("RETURN",)],
        [("CONST", 0)],
    ]
    for bad in bad_programs:
        try:
            verify(bad, constants)
        except VerificationError:
            pass
        else:
            raise AssertionError(f"invalid program accepted: {bad}")
    print("PASS bytecode verifier and VM")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        constants = [Value("Int", 2), Value("Int", 3), Value("Int", 4)]
        program: Program = [("CONST", 0), ("CONST", 1), ("CONST", 2), ("MUL",), ("ADD",), ("RETURN",)]
        result = execute(program, constants)
        print(json.dumps({"type": result.type, "value": result.value}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
