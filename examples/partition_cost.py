#!/usr/bin/env python3
"""Observe key skew under deterministic hash partitioning."""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Iterable


def partition_for(key: str, partitions: int) -> int:
    if partitions <= 0:
        raise ValueError("partitions must be positive")
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % partitions


def distribution(keys: Iterable[str], partitions: int) -> dict[int, int]:
    counts = Counter(partition_for(key, partitions) for key in keys)
    return {partition: counts.get(partition, 0) for partition in range(partitions)}


def imbalance_ratio(counts: dict[int, int]) -> float:
    values = list(counts.values())
    average = sum(values) / len(values) if values else 0.0
    return max(values) / average if average else 0.0
