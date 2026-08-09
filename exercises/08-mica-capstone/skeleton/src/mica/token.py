from __future__ import annotations

from dataclasses import dataclass

from .source import Span


@dataclass(frozen=True, slots=True)
class Token:
    kind: str
    lexeme: str
    span: Span
    channel: str = "syntax"
