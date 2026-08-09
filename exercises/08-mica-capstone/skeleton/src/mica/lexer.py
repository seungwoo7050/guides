from __future__ import annotations

from .diagnostic import Diagnostic
from .source import SourceText
from .token import Token


def lex(_source: SourceText) -> tuple[list[Token], list[Diagnostic]]:
    """Learner boundary: always advance, diagnose, or emit EOF."""
    raise NotImplementedError("implement Mica lexical contract")
