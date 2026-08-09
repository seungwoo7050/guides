from __future__ import annotations

import json
from collections import Counter, defaultdict


def partition_for(key: str, partition_count: int) -> int:
    if partition_count <= 0:
        raise ValueError("partition_count must be positive")
    return hash(key) % partition_count


def join_and_report(left, right, partition_count, hot_key_threshold, broadcast_threshold):
    by_key = defaultdict(list)
    for row in right:
        by_key[row["key"]].append(dict(row))
    counts = Counter(row["key"] for row in left + right)
    loads = [0] * partition_count
    for key, count in counts.items():
        loads[partition_for(key, partition_count)] += count
    joined = [
        {"key": row["key"], "left": dict(row), "right": match}
        for row in left
        for match in by_key.get(row["key"], [])
    ]
    canonical = lambda value: json.dumps(value, sort_keys=True)
    joined.sort(key=lambda item: (item["key"], canonical(item["left"]), canonical(item["right"])))
    return {
        "strategy": "broadcast-right" if len(right) <= broadcast_threshold else "shuffle-both",
        "partition_loads": loads,
        "hot_keys": sorted(key for key, count in counts.items() if count >= hot_key_threshold),
        "joined": joined,
    }
