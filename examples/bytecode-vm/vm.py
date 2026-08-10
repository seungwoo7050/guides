#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any


class VerificationError(ValueError):
    pass


class ExecutionError(ValueError):
    pass


I64_MIN = -(2**63)
I64_MAX = 2**63 - 1


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
            if not I64_MIN <= result <= I64_MAX:
                raise ExecutionError("MICA4002")
            stack.append(Value("Int", result))
        elif op == "RETURN":
            return stack.pop()
    raise AssertionError("verified program did not return")


def compile_expression(expression: object) -> tuple[Program, list[Value]]:
    program: Program = []
    constants: list[Value] = []

    def emit(node: object) -> None:
        if isinstance(node, int) and not isinstance(node, bool):
            constants.append(Value("Int", node))
            program.append(("CONST", len(constants) - 1))
            return
        if isinstance(node, list) and len(node) == 3 and node[0] in {"+", "*"}:
            emit(node[1])
            emit(node[2])
            program.append(("ADD",) if node[0] == "+" else ("MUL",))
            return
        raise ValueError(f"unsupported expression: {node!r}")

    emit(expression)
    program.append(("RETURN",))
    verify(program, constants)
    return program, constants


def evaluate_expression(expression: object) -> Value:
    if isinstance(expression, int) and not isinstance(expression, bool):
        return Value("Int", expression)
    if isinstance(expression, list) and len(expression) == 3 and expression[0] in {"+", "*"}:
        left = evaluate_expression(expression[1])
        right = evaluate_expression(expression[2])
        result = left.value + right.value if expression[0] == "+" else left.value * right.value
        if not I64_MIN <= result <= I64_MAX:
            raise ExecutionError("MICA4002")
        return Value("Int", result)
    raise ValueError(f"unsupported expression: {expression!r}")


def disassemble(program: Program, constants: list[Value]) -> str:
    verify(program, constants)
    lines: list[str] = []
    for index, instruction in enumerate(program):
        op = instruction[0]
        operand = f" {instruction[1]}" if len(instruction) == 2 else ""
        annotation = ""
        if op == "CONST":
            value = constants[instruction[1]]
            annotation = f" ; {value.type}({value.value})"
        lines.append(f"{index:04d} {op}{operand}{annotation}")
    return "\n".join(lines) + "\n"


def self_test() -> None:
    expression: object = ["+", 2, ["*", 3, 4]]
    program, constants = compile_expression(expression)
    assert execute(program, constants) == Value("Int", 14)
    assert evaluate_expression(expression) == execute(program, constants)
    assert disassemble(program, constants).startswith("0000 CONST 0 ; Int(2)\n")
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
    overflow_program, overflow_constants = compile_expression(["+", I64_MAX, 1])
    try:
        execute(overflow_program, overflow_constants)
    except ExecutionError as fault:
        assert str(fault) == "MICA4002"
    else:
        raise AssertionError("unchecked VM overflow")
    print("PASS bytecode verifier compiler disassembly VM differential checked-i64")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    else:
        program, constants = compile_expression(["+", 2, ["*", 3, 4]])
        result = execute(program, constants)
        print(json.dumps({"disassembly": disassemble(program, constants), "type": result.type, "value": result.value}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
