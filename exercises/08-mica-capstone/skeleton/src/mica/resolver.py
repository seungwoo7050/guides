from __future__ import annotations

from .syntax import Node


def resolve(module: Node) -> dict[int, str]:
    """Return AST node id -> stable SymbolId after implementing scope rules."""
    del module
    raise NotImplementedError("Exercise 03: implement lexical scope resolution")
