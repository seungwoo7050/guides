#!/usr/bin/env python3
"""A minimal snapshot + ordered change-log merge model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, order=True)
class Position:
    value: int


@dataclass(frozen=True)
class SnapshotRow:
    key: str
    value: dict[str, Any]
    snapshot_position: Position


@dataclass(frozen=True)
class Change:
    key: str
    position: Position
    operation: str
    after: dict[str, Any] | None


def materialize(snapshot_rows: Iterable[SnapshotRow], changes: Iterable[Change]) -> dict[str, dict[str, Any]]:
    state: dict[str, tuple[Position, dict[str, Any]]] = {}
    for row in snapshot_rows:
        current = state.get(row.key)
        if current is None or row.snapshot_position >= current[0]:
            state[row.key] = (row.snapshot_position, dict(row.value))

    for change in sorted(changes, key=lambda item: item.position):
        current = state.get(change.key)
        if current is not None and change.position <= current[0]:
            continue
        if change.operation == "DELETE":
            state.pop(change.key, None)
        elif change.operation in {"INSERT", "UPDATE"} and change.after is not None:
            state[change.key] = (change.position, dict(change.after))
        else:
            raise ValueError(f"invalid change: {change}")

    return {key: value for key, (_, value) in sorted(state.items())}
