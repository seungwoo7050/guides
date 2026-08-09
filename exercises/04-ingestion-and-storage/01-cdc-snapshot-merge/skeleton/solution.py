from __future__ import annotations


def materialize(snapshot_rows: list[dict], changes: list[dict]) -> dict[str, dict]:
    # TODO: preserve positions and tombstones instead of applying arrival order.
    state = {str(row["key"]): dict(row["value"]) for row in snapshot_rows}
    for change in changes:
        key = str(change["key"])
        if change["operation"] == "DELETE":
            state.pop(key, None)
        else:
            state[key] = dict(change["after"])
    return state
