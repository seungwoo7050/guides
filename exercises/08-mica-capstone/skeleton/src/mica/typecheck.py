from __future__ import annotations

from .syntax import Node
from .types import Type


def check_types(module: Node, resolutions: dict[int, str]) -> dict[int, Type]:
    """Return AST node id -> Type without mutating the parser tree."""
    del module, resolutions
    raise NotImplementedError("Exercise 03: implement Mica type rules")
