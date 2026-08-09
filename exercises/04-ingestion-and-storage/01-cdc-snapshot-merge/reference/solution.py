from __future__ import annotations


def materialize(snapshot_rows: list[dict], changes: list[dict]) -> dict[str, dict]:
    values: dict[str, dict] = {}
    positions: dict[str, int] = {}

    for row in snapshot_rows:
        key = str(row["key"])
        position = int(row["position"])
        if position >= positions.get(key, -1):
            positions[key] = position
            values[key] = dict(row["value"])

    for change in sorted(changes, key=lambda item: (int(item["position"]), str(item["key"]))):
        key = str(change["key"])
        position = int(change["position"])
        if position <= positions.get(key, -1):
            continue
        operation = str(change["operation"])
        if operation == "DELETE":
            values.pop(key, None)
        elif operation in {"INSERT", "UPDATE"}:
            after = change.get("after")
            if not isinstance(after, dict):
                raise ValueError("INSERT/UPDATE requires after object")
            values[key] = dict(after)
        else:
            raise ValueError(f"unsupported operation: {operation}")
        positions[key] = position

    return {key: values[key] for key in sorted(values)}
