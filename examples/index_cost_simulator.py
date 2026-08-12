#!/usr/bin/env python3
"""선택도와 랜덤 I/O 비용이 인덱스 선택을 바꾸는 이유를 관찰한다."""

from __future__ import annotations

from dataclasses import dataclass


# [Implementation 1] 이 축소 model이 사용하는 page 수와 random/sequential 비용 가정을 한곳에 고정한다.
@dataclass(frozen=True)
class CostModel:
    table_pages: int
    index_height: int = 3
    random_page_cost: float = 4.0
    sequential_page_cost: float = 1.0

    # [Implementation 2] 같은 비용 단위로 sequential path와 index+heap path를 비교한다.
    def sequential_scan(self) -> float:
        return self.table_pages * self.sequential_page_cost

    def index_scan(self, matching_rows: int, rows_per_page: int, correlation: float = 0.0) -> float:
        heap_pages = max(1, matching_rows / rows_per_page)
        random_factor = self.random_page_cost - correlation * (self.random_page_cost - self.sequential_page_cost)
        return self.index_height + heap_pages * random_factor


# [Implementation 3] 선택적인 조건과 비선택적인 조건에서 접근 경로의 상대 비용이 뒤집히는지 본다.
model = CostModel(table_pages=10_000)
selective = model.index_scan(matching_rows=50, rows_per_page=100)
unselective = model.index_scan(matching_rows=400_000, rows_per_page=100)
assert selective < model.sequential_scan()
assert unselective > model.sequential_scan()
print("index cost example: PASS")
