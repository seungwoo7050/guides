from __future__ import annotations

from collections import defaultdict
from typing import Any

Row = dict[str, Any]
Joined = tuple[Row, Row]


# [Implementation 1] Nested loop가 NULL 불일치와 중복 row 조합을 보존하는 bag semantic oracle이다.
def nested_loop_join(left: list[Row], right: list[Row], left_key: str, right_key: str) -> list[Joined]:
    result: list[Joined] = []
    for left_row in left:
        left_value = left_row.get(left_key)
        if left_value is None:
            continue
        for right_row in right:
            right_value = right_row.get(right_key)
            if right_value is not None and left_value == right_value:
                result.append((left_row, right_row))
    return result


# [Implementation 2] Hash join은 작은 입력을 build하되 외부 결과 tuple의 left/right 방향을 유지한다.
def hash_join(left: list[Row], right: list[Row], left_key: str, right_key: str) -> list[Joined]:
    # 더 작은 쪽을 build하면 hash table 메모리를 줄일 수 있다. 결과 tuple은 항상 (left, right)다.
    if len(left) <= len(right):
        buckets: dict[Any, list[Row]] = defaultdict(list)
        for row in left:
            value = row.get(left_key)
            if value is not None:
                buckets[value].append(row)
        return [
            (left_row, right_row)
            for right_row in right
            if (value := right_row.get(right_key)) is not None
            for left_row in buckets.get(value, [])
        ]

    buckets = defaultdict(list)
    for row in right:
        value = row.get(right_key)
        if value is not None:
            buckets[value].append(row)
    return [
        (left_row, right_row)
        for left_row in left
        if (value := left_row.get(left_key)) is not None
        for right_row in buckets.get(value, [])
    ]


# [Implementation 3] Merge join은 두 입력을 정렬한 뒤 같은 key의 양쪽 run 전체를 곱으로 결합한다.
def merge_join(left: list[Row], right: list[Row], left_key: str, right_key: str) -> list[Joined]:
    left_rows = sorted((row for row in left if row.get(left_key) is not None), key=lambda row: row[left_key])
    right_rows = sorted((row for row in right if row.get(right_key) is not None), key=lambda row: row[right_key])
    result: list[Joined] = []
    i = j = 0

    while i < len(left_rows) and j < len(right_rows):
        left_value = left_rows[i][left_key]
        right_value = right_rows[j][right_key]
        if left_value < right_value:
            i += 1
            continue
        if left_value > right_value:
            j += 1
            continue

        left_end = i
        while left_end < len(left_rows) and left_rows[left_end][left_key] == left_value:
            left_end += 1
        right_end = j
        while right_end < len(right_rows) and right_rows[right_end][right_key] == right_value:
            right_end += 1

        for left_row in left_rows[i:left_end]:
            for right_row in right_rows[j:right_end]:
                result.append((left_row, right_row))
        i, j = left_end, right_end

    return result
