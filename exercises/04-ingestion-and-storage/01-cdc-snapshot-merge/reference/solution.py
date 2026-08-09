from __future__ import annotations

import json


def _position(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("position must be a non-negative integer")
    return value


def _key(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("key must be a non-empty string")
    return value


def _snapshot(row: object) -> tuple[str, int, dict]:
    if not isinstance(row, dict):
        raise ValueError("snapshot row must be an object")
    value = row.get("value")
    if not isinstance(value, dict):
        raise ValueError("snapshot value must be an object")
    return _key(row.get("key")), _position(row.get("position")), json.loads(json.dumps(value, allow_nan=False))


def _change(change: object) -> tuple[str, int, str, dict | None]:
    if not isinstance(change, dict):
        raise ValueError("change must be an object")
    key = _key(change.get("key"))
    position = _position(change.get("position"))
    operation = change.get("operation")
    after = change.get("after")
    if operation == "DELETE":
        if after is not None:
            raise ValueError("DELETE after must be null")
        return key, position, operation, None
    if operation not in {"INSERT", "UPDATE"}:
        raise ValueError(f"unsupported operation: {operation}")
    if not isinstance(after, dict):
        raise ValueError("INSERT/UPDATE requires after object")
    return key, position, operation, json.loads(json.dumps(after, allow_nan=False))


def _payload(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def materialize(snapshot_rows: list[dict], changes: list[dict]) -> dict[str, dict]:
    values: dict[str, dict] = {}
    positions: dict[str, int] = {}
    snapshot_seen: dict[tuple[str, int], str] = {}

    for raw in snapshot_rows:
        key, position, value = _snapshot(raw)
        identity = (key, position)
        canonical = _payload(value)
        previous_payload = snapshot_seen.get(identity)
        if previous_payload is not None and previous_payload != canonical:
            raise ValueError(f"conflicting snapshot rows at {key}@{position}")
        snapshot_seen[identity] = canonical
        if position > positions.get(key, -1):
            positions[key] = position
            values[key] = value

    unique_changes: dict[tuple[str, int], tuple[str, dict | None]] = {}
    for raw in changes:
        key, position, operation, after = _change(raw)
        identity = (key, position)
        payload = (operation, after)
        previous = unique_changes.get(identity)
        if previous is not None and _payload(previous) != _payload(payload):
            raise ValueError(f"conflicting changes at {key}@{position}")
        unique_changes[identity] = payload

    for (key, position), (operation, after) in sorted(
        unique_changes.items(), key=lambda item: (item[0][1], item[0][0])
    ):
        if position <= positions.get(key, -1):
            continue
        if operation == "DELETE":
            values.pop(key, None)
        else:
            assert after is not None
            values[key] = after
        positions[key] = position

    return {key: values[key] for key in sorted(values)}
