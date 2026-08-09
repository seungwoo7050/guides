from __future__ import annotations

from .runtime import RuntimeValue
from .syntax import Node


def execute(module: Node, *, max_steps: int, max_call_depth: int) -> RuntimeValue:
    """Execute a checked module with explicit budgets and no host traceback leakage."""
    del module, max_steps, max_call_depth
    raise NotImplementedError("Exercise 04: implement tree-walk execution")
