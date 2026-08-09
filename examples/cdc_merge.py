#!/usr/bin/env python3
"""A minimal snapshot + ordered change-log merge model."""

from __future__ import annotations

import json
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


def _key(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("key must be a non-empty string")
    return value


def _position(value: object) -> Position:
    if not isinstance(value, Position):
        raise ValueError("position must be a Position")
    if not isinstance(value.value, int) or isinstance(value.value, bool) or value.value < 0:
        raise ValueError("position must be a non-negative integer")
    return value


def _object(value: object, *, label: str) -> tuple[dict[str, Any], str]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    try:
        canonical = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        copied = json.loads(canonical)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must contain JSON values") from exc
    return copied, canonical


def materialize(snapshot_rows: Iterable[SnapshotRow], changes: Iterable[Change]) -> dict[str, dict[str, Any]]:
    positions: dict[str, Position] = {}
    values: dict[str, dict[str, Any]] = {}
    snapshot_seen: dict[tuple[str, int], str] = {}
    for row in snapshot_rows:
        if not isinstance(row, SnapshotRow):
            raise ValueError("snapshot row must be a SnapshotRow")
        key = _key(row.key)
        position = _position(row.snapshot_position)
        value, canonical = _object(row.value, label="snapshot value")
        identity = (key, position.value)
        previous = snapshot_seen.get(identity)
        if previous is not None and previous != canonical:
            raise ValueError(f"conflicting snapshot rows at {key}@{position.value}")
        snapshot_seen[identity] = canonical
        current = positions.get(key)
        if current is None or position > current:
            positions[key] = position
            values[key] = value

    unique_changes: dict[tuple[str, int], tuple[str, dict[str, Any] | None, str]] = {}
    for change in changes:
        if not isinstance(change, Change):
            raise ValueError("change must be a Change")
        key = _key(change.key)
        position = _position(change.position)
        if not isinstance(change.operation, str):
            raise ValueError("operation must be a string")
        if change.operation == "DELETE":
            if change.after is not None:
                raise ValueError("DELETE after must be null")
            after = None
            canonical = "DELETE:null"
        elif change.operation in {"INSERT", "UPDATE"}:
            after, payload = _object(change.after, label="INSERT/UPDATE after")
            canonical = f"{change.operation}:{payload}"
        else:
            raise ValueError(f"unsupported operation: {change.operation}")
        identity = (key, position.value)
        previous = unique_changes.get(identity)
        if previous is not None and previous[2] != canonical:
            raise ValueError(f"conflicting changes at {key}@{position.value}")
        unique_changes[identity] = (change.operation, after, canonical)

    for (key, raw_position), (operation, after, _) in sorted(
        unique_changes.items(), key=lambda item: (item[0][1], item[0][0])
    ):
        position = Position(raw_position)
        current = positions.get(key)
        if current is not None and position <= current:
            continue
        positions[key] = position
        if operation == "DELETE":
            values.pop(key, None)
        else:
            assert after is not None
            values[key] = after

    return {key: values[key] for key in sorted(values)}
