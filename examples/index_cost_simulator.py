#!/usr/bin/env python3
"""선택도와 랜덤 I/O 비용이 인덱스 선택을 바꾸는 이유를 관찰한다."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    table_pages: int
    index_height: int = 3
    random_page_cost: float = 4.0
    sequential_page_cost: float = 1.0

    def sequential_scan(self) -> float:
        return self.table_pages * self.sequential_page_cost

    def index_scan(self, matching_rows: int, rows_per_page: int, correlation: float = 0.0) -> float:
        heap_pages = max(1, matching_rows / rows_per_page)
        random_factor = self.random_page_cost - correlation * (self.random_page_cost - self.sequential_page_cost)
        return self.index_height + heap_pages * random_factor


model = CostModel(table_pages=10_000)
selective = model.index_scan(matching_rows=50, rows_per_page=100)
unselective = model.index_scan(matching_rows=400_000, rows_per_page=100)
assert selective < model.sequential_scan()
assert unselective > model.sequential_scan()
print("index cost example: PASS")
