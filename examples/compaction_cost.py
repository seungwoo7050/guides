#!/usr/bin/env python3
"""Compare small-file metadata savings with deterministic rewrite cost."""

from __future__ import annotations

import json


def _nonnegative_int(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def estimate(file_sizes: list[int], target_bytes: int) -> dict:
    """Estimate one deterministic ascending-pack compaction pass.

    Groups with at least two files are rewritten into one output. A singleton or
    a file at/above the target is left in place. The model exposes a cost
    comparison; it does not model a table-format commit or concurrent writers.
    """

    if not isinstance(file_sizes, list):
        raise ValueError("file_sizes must be a list")
    target = _nonnegative_int(target_bytes, "target_bytes")
    if target == 0:
        raise ValueError("target_bytes must be positive")
    sizes = sorted(_nonnegative_int(size, "file size") for size in file_sizes)

    candidate_groups: list[list[int]] = []
    current: list[int] = []
    current_bytes = 0
    for size in sizes:
        if size >= target:
            if current:
                candidate_groups.append(current)
                current = []
                current_bytes = 0
            candidate_groups.append([size])
            continue
        if current and current_bytes + size > target:
            candidate_groups.append(current)
            current = []
            current_bytes = 0
        current.append(size)
        current_bytes += size
    if current:
        candidate_groups.append(current)

    rewrite_groups = [group for group in candidate_groups if len(group) >= 2]
    unchanged_files = [group[0] for group in candidate_groups if len(group) == 1]
    output_files = len(rewrite_groups) + len(unchanged_files)
    return {
        "input_files": len(sizes),
        "input_bytes": sum(sizes),
        "output_files": output_files,
        "metadata_requests_saved": len(sizes) - output_files,
        "rewrite_bytes": sum(sum(group) for group in rewrite_groups),
        "rewrite_groups": [
            {"inputs": group, "input_bytes": sum(group), "output_files": 1}
            for group in rewrite_groups
        ],
        "unchanged_files": unchanged_files,
    }


def demo() -> None:
    print(json.dumps(estimate([10, 10, 10, 90], 100), indent=2))


if __name__ == "__main__":
    demo()
