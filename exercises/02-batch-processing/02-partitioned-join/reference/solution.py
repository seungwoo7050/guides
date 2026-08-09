from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict


def _positive_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def partition_for(key: str, partition_count: int) -> int:
    count = _positive_int(partition_count, "partition_count")
    if not isinstance(key, str):
        raise ValueError("key must be a string")
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % count


def _rows(value: object, label: str) -> list[dict]:
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"{label} must be a list of objects")
    for row in value:
        if not isinstance(row.get("key"), str):
            raise ValueError(f"{label} row key must be a string")
        json.dumps(row, ensure_ascii=False, allow_nan=False)
    return value


def _canonical(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def join_and_report(
    left: list[dict],
    right: list[dict],
    partition_count: int,
    hot_key_threshold: int,
    broadcast_threshold: int,
) -> dict:
    count = _positive_int(partition_count, "partition_count")
    hot = _positive_int(hot_key_threshold, "hot_key_threshold")
    broadcast = _nonnegative_int(broadcast_threshold, "broadcast_threshold")
    left_rows = _rows(left, "left")
    right_rows = _rows(right, "right")

    right_by_key: dict[str, list[dict]] = defaultdict(list)
    for row in right_rows:
        right_by_key[row["key"]].append(dict(row))
    counts = Counter(row["key"] for row in left_rows)
    counts.update(row["key"] for row in right_rows)
    loads = [0] * count
    for key, load in counts.items():
        loads[partition_for(key, count)] += load

    joined: list[dict] = []
    for left_row in left_rows:
        key = left_row["key"]
        for right_row in right_by_key.get(key, []):
            joined.append({"key": key, "left": dict(left_row), "right": dict(right_row)})
    joined.sort(key=lambda item: (item["key"], _canonical(item["left"]), _canonical(item["right"])))
    return {
        "strategy": "broadcast-right" if len(right_rows) <= broadcast else "shuffle-both",
        "partition_loads": loads,
        "hot_keys": sorted(key for key, load in counts.items() if load >= hot),
        "joined": joined,
    }
