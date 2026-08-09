from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .source import Span


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: str
    phase: str
    message: str
    primary: Span
    secondary: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)
