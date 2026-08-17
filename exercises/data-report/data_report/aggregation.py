"""Deterministic report aggregation."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from .model import CategoryTotal, Record, Report


# [Implementation 4]
# Aggregation normalizes category order independently of input ordering.
def aggregate(records: Iterable[Record]) -> Report:
    counts: dict[str, int] = defaultdict(int)
    totals: dict[str, Decimal] = defaultdict(Decimal)
    overall_count = 0
    overall_total = Decimal(0)

    for record in records:
        counts[record.category] += 1
        totals[record.category] += record.amount
        overall_count += 1
        overall_total += record.amount

    # 출력 순서를 입력 순서나 dict insertion history에 맡기지 않는다.
    # 동일한 dataset이면 source format과 record 배치가 달라도 같은 report 순서를 보장한다.
    rows = tuple(
        CategoryTotal(
            category=category,
            count=counts[category],
            total=totals[category],
        )
        for category in sorted(totals)
    )
    return Report(rows=rows, count=overall_count, total=overall_total)
