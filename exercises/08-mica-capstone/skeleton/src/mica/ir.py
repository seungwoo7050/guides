from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Instruction:
    opcode: str
    operands: tuple[object, ...]
    result: str | None = None


def lower(typed_module: object) -> object:
    del typed_module
    raise NotImplementedError("Exercise 05: implement typed AST to explicit CFG lowering")
