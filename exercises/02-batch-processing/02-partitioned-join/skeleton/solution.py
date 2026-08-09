from __future__ import annotations


def partition_for(key: str, partition_count: int) -> int:
    return hash(key) % partition_count


def join_and_report(left, right, partition_count, hot_key_threshold, broadcast_threshold):
    return {
        "strategy": "broadcast-right",
        "partition_loads": [0] * partition_count,
        "hot_keys": [],
        "joined": [],
    }
