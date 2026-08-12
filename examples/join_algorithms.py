#!/usr/bin/env python3
"""중첩 loop와 hash join이 SQL의 중복·NULL 계약을 보존하는지 비교한다."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

Row = dict[str, Any]
Joined = list[tuple[Row, Row]]


# [Implementation 1] Nested loop를 NULL·중복을 포함한 bag 의미의 가장 직접적인 기준으로 둔다.
def nested_loop(left: list[Row], right: list[Row], left_key: str, right_key: str) -> Joined:
    result: Joined = []
    for left_row in left:
        key = left_row[left_key]
        if key is None:
            continue
        for right_row in right:
            if right_row[right_key] is not None and key == right_row[right_key]:
                result.append((left_row, right_row))
    return result


# [Implementation 2] Hash bucket은 같은 key의 모든 오른쪽 row를 보유해 중복 조합을 잃지 않는다.
def hash_join(left: list[Row], right: list[Row], left_key: str, right_key: str) -> Joined:
    buckets: dict[Any, list[Row]] = defaultdict(list)
    for row in right:
        key = row[right_key]
        if key is not None:
            buckets[key].append(row)
    return [(left_row, right_row) for left_row in left if left_row[left_key] is not None for right_row in buckets.get(left_row[left_key], [])]


# [Implementation 3] 같은 입력에서 두 알고리즘의 bag 결과와 NULL 배제를 함께 확인한다.
users = [{"id": 1}, {"id": 1}, {"id": 2}, {"id": None}]
orders = [
    {"id": 10, "user_id": 1},
    {"id": 11, "user_id": 1},
    {"id": 12, "user_id": 3},
    {"id": 13, "user_id": None},
]
expected = nested_loop(users, orders, "id", "user_id")
assert expected == hash_join(users, orders, "id", "user_id")
assert len(expected) == 4  # left 2개 × right 2개: bag 의미를 보존한다.
assert all(left["id"] is not None and right["user_id"] is not None for left, right in expected)
print("join algorithms example: PASS")
