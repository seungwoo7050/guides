"""Capstone에서 사용하는 공개 함수와 자료형."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


def _missing(name: str):
    raise NotImplementedError(f"TODO: {name}을(를) 구현하세요.")


def prefix_sums(values: Sequence[int]) -> list[int]:
    return _missing("prefix_sums")


def range_sum(prefix: Sequence[int], start: int, stop: int) -> int:
    return _missing("range_sum")


def lower_bound(values: Sequence[int], target: int) -> int:
    return _missing("lower_bound")


def bfs_distances(graph: Sequence[Sequence[int]], start: int) -> list[int | None]:
    return _missing("bfs_distances")


def dijkstra(
    vertex_count: int,
    edges: Iterable[tuple[int, int, int]],
    start: int,
) -> list[int | None]:
    return _missing("dijkstra")


def knapsack_01(items: Sequence[tuple[int, int]], capacity: int) -> int:
    return _missing("knapsack_01")


def select_intervals(intervals: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    return _missing("select_intervals")


@dataclass
class RedBlackNode:
    key: int
    color: str
    left: "RedBlackNode | None" = None
    right: "RedBlackNode | None" = None


def red_black_height(root: RedBlackNode | None) -> int:
    return _missing("red_black_height")


def kruskal_mst(
    vertex_count: int,
    edges: Iterable[tuple[int, int, int]],
) -> tuple[int, list[tuple[int, int, int]]]:
    return _missing("kruskal_mst")


def bellman_ford(
    vertex_count: int,
    edges: Sequence[tuple[int, int, int]],
    start: int,
) -> list[int | None]:
    return _missing("bellman_ford")


def kmp_find(text: str, pattern: str) -> int:
    return _missing("kmp_find")


def max_flow(capacity: Sequence[Sequence[int]], source: int, sink: int) -> int:
    return _missing("max_flow")


def lcs_length(left: str, right: str) -> int:
    return _missing("lcs_length")
