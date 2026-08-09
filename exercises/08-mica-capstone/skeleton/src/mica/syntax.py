from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .source import Span


@dataclass(frozen=True, slots=True)
class Node:
    kind: str
    node_id: int
    span: Span
    fields: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        span = {
            "source_id": self.span.source_id,
            "start": self.span.start,
            "end": self.span.end,
        }
        return {"kind": self.kind, "id": self.node_id, "span": span, **self.fields}
