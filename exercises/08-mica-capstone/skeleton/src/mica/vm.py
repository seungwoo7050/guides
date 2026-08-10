from __future__ import annotations

from .runtime import RuntimeValue


def execute(module: object, *, max_steps: int, max_call_depth: int) -> RuntimeValue:
    del module, max_steps, max_call_depth
    raise NotImplementedError("Exercise 06: implement verified bytecode execution")
