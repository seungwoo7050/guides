from __future__ import annotations

from collections import defaultdict


def plan_compaction(files: list[dict], target_bytes: int, max_group_files: int) -> list[dict]:
    if target_bytes <= 0 or max_group_files < 2:
        raise ValueError("invalid limits")
    buckets = defaultdict(list)
    for file in files:
        if file["active"] and file["bytes"] < target_bytes:
            buckets[(file["partition"], file["schema_id"], file["spec_id"])].append(file)
    plans = []
    for identity in sorted(buckets):
        current = []
        current_bytes = 0
        for file in sorted(buckets[identity], key=lambda value: value["path"]):
            if current and (len(current) >= max_group_files or current_bytes + file["bytes"] > target_bytes):
                if len(current) >= 2:
                    plans.append((identity, current))
                current = []
                current_bytes = 0
            current.append(file)
            current_bytes += file["bytes"]
        if len(current) >= 2:
            plans.append((identity, current))
    return [
        {
            "partition": identity[0],
            "schema_id": identity[1],
            "spec_id": identity[2],
            "inputs": [file["path"] for file in group],
            "input_bytes": sum(file["bytes"] for file in group),
            "input_rows": sum(file["rows"] for file in group),
        }
        for identity, group in plans
    ]
