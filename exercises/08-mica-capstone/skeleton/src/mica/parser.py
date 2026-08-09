from __future__ import annotations

from .diagnostic import Diagnostic
from .syntax import Node
from .token import Token


def parse(_tokens: list[Token]) -> tuple[Node, list[Diagnostic]]:
    """Learner boundary: produce a normalized Module or recovery nodes."""
    raise NotImplementedError("implement Mica parser and normalized AST")
