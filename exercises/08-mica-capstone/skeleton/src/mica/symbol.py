from __future__ import annotations

from dataclasses import dataclass

from .source import Span


@dataclass(frozen=True, slots=True)
class Symbol:
    symbol_id: str
    name: str
    kind: str
    declaration: Span
