#!/usr/bin/env python3
"""관계 대수의 선택·사영·조인을 작은 불변 데이터로 관찰한다."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

Row = dict[str, Any]
Relation = list[Row]


# [Implementation 1] 선택은 입력 row를 그대로 노출하지 않고 복사해 관찰 결과의 소유권을 분리한다.
def select(rows: Iterable[Row], predicate: Callable[[Row], bool]) -> Relation:
    return [dict(row) for row in rows if predicate(row)]


# [Implementation 2] 사영이 열 순서와 distinct key를 함께 소유해야 중복 제거 기준이 흔들리지 않는다.
def project(rows: Iterable[Row], *columns: str, distinct: bool = True) -> Relation:
    result: Relation = []
    seen: set[tuple[Any, ...]] = set()
    for row in rows:
        key = tuple(row[column] for column in columns)
        if distinct and key in seen:
            continue
        seen.add(key)
        result.append(dict(zip(columns, key, strict=True)))
    return result


# [Implementation 3] 오른쪽 lookup을 만든 뒤 양쪽 열을 namespace로 분리해 이름 충돌을 피한다.
def inner_join(left: Iterable[Row], right: Iterable[Row], left_key: str, right_key: str) -> Relation:
    index: dict[Any, list[Row]] = {}
    for row in right:
        index.setdefault(row[right_key], []).append(row)
    result: Relation = []
    for left_row in left:
        for right_row in index.get(left_row[left_key], []):
            merged = {f"left.{key}": value for key, value in left_row.items()}
            merged.update({f"right.{key}": value for key, value in right_row.items()})
            result.append(merged)
    return result


# [Implementation 4] 마지막에 작은 relation을 연결해 선택→조인→사영의 결과 계약을 관찰한다.
users = [
    {"id": 1, "email": "a@example.test"},
    {"id": 2, "email": "b@example.test"},
]
orders = [
    {"id": 10, "user_id": 1, "total": 5000},
    {"id": 11, "user_id": 1, "total": 0},
    {"id": 12, "user_id": 3, "total": 9000},
]

paid = select(orders, lambda row: row["total"] > 0)
joined = inner_join(users, paid, "id", "user_id")
emails = project(joined, "left.email")
assert emails == [{"left.email": "a@example.test"}]
print("relational algebra example: PASS")
