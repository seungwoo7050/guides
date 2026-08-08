"""검증용 기준 구현.

빠른 구현만을 목표로 하지 않고 각 공개 계약과 실패 조건을 명시적으로
지킨다. tests의 oracle은 이 파일과 다른 계산 방법을 사용한다.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import heapq
from typing import Iterable, Sequence


def prefix_sums(values: Sequence[int]) -> list[int]:
    prefix = [0]
    total = 0
    for value in values:
        total += value
        prefix.append(total)
    return prefix


def range_sum(prefix: Sequence[int], start: int, stop: int) -> int:
    if start < 0 or stop < start or stop >= len(prefix):
        raise ValueError("0 <= start <= stop < len(prefix)여야 합니다.")
    return prefix[stop] - prefix[start]


def lower_bound(values: Sequence[int], target: int) -> int:
    lo = 0
    hi = len(values)
    while lo < hi:
        middle = lo + (hi - lo) // 2
        if values[middle] < target:
            lo = middle + 1
        else:
            hi = middle
    return lo


def _validate_vertex(vertex_count: int, vertex: int) -> None:
    if not 0 <= vertex < vertex_count:
        raise ValueError(f"정점 {vertex}가 0..{vertex_count - 1} 범위를 벗어났습니다.")


def bfs_distances(graph: Sequence[Sequence[int]], start: int) -> list[int | None]:
    vertex_count = len(graph)
    _validate_vertex(vertex_count, start)
    for neighbors in graph:
        for target in neighbors:
            _validate_vertex(vertex_count, target)

    distance: list[int | None] = [None] * vertex_count
    distance[start] = 0
    queue: deque[int] = deque([start])
    while queue:
        vertex = queue.popleft()
        assert distance[vertex] is not None
        for target in graph[vertex]:
            if distance[target] is None:
                distance[target] = distance[vertex] + 1
                queue.append(target)
    return distance


def dijkstra(
    vertex_count: int,
    edges: Iterable[tuple[int, int, int]],
    start: int,
) -> list[int | None]:
    if vertex_count < 0:
        raise ValueError("vertex_count는 음수일 수 없습니다.")
    _validate_vertex(vertex_count, start)

    graph: list[list[tuple[int, int]]] = [[] for _ in range(vertex_count)]
    for source, target, weight in edges:
        _validate_vertex(vertex_count, source)
        _validate_vertex(vertex_count, target)
        if weight < 0:
            raise ValueError("Dijkstra는 음수 가중치를 허용하지 않습니다.")
        graph[source].append((target, weight))

    distance: list[int | None] = [None] * vertex_count
    distance[start] = 0
    queue: list[tuple[int, int]] = [(0, start)]
    while queue:
        current, vertex = heapq.heappop(queue)
        if distance[vertex] != current:
            continue
        for target, weight in graph[vertex]:
            candidate = current + weight
            if distance[target] is None or candidate < distance[target]:
                distance[target] = candidate
                heapq.heappush(queue, (candidate, target))
    return distance


def knapsack_01(items: Sequence[tuple[int, int]], capacity: int) -> int:
    if capacity < 0:
        raise ValueError("capacity는 음수일 수 없습니다.")
    for weight, _value in items:
        if weight <= 0:
            raise ValueError("물건 무게는 양수여야 합니다.")

    best = [0] * (capacity + 1)
    for weight, value in items:
        for current_capacity in range(capacity, weight - 1, -1):
            best[current_capacity] = max(
                best[current_capacity],
                best[current_capacity - weight] + value,
            )
    return best[capacity]


def select_intervals(intervals: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    normalized = list(intervals)
    if any(start >= stop for start, stop in normalized):
        raise ValueError("각 구간은 start < stop이어야 합니다.")

    selected: list[tuple[int, int]] = []
    last_stop: int | None = None
    for interval in sorted(normalized, key=lambda item: (item[1], item[0])):
        start, stop = interval
        if last_stop is None or start >= last_stop:
            selected.append(interval)
            last_stop = stop
    return selected


@dataclass
class RedBlackNode:
    key: int
    color: str
    left: "RedBlackNode | None" = None
    right: "RedBlackNode | None" = None


def red_black_height(root: RedBlackNode | None) -> int:
    if root is not None and root.color != "black":
        raise ValueError("root는 black이어야 합니다.")

    def visit(
        node: RedBlackNode | None,
        lower: int | None,
        upper: int | None,
    ) -> int:
        if node is None:
            return 1
        if node.color not in {"red", "black"}:
            raise ValueError("color는 red 또는 black이어야 합니다.")
        if lower is not None and node.key <= lower:
            raise ValueError("BST lower bound를 위반했습니다.")
        if upper is not None and node.key >= upper:
            raise ValueError("BST upper bound를 위반했습니다.")
        if node.color == "red":
            if node.left is not None and node.left.color == "red":
                raise ValueError("red node의 left child가 red입니다.")
            if node.right is not None and node.right.color == "red":
                raise ValueError("red node의 right child가 red입니다.")

        left_height = visit(node.left, lower, node.key)
        right_height = visit(node.right, node.key, upper)
        if left_height != right_height:
            raise ValueError("root-to-leaf black height가 다릅니다.")
        return left_height + (1 if node.color == "black" else 0)

    return visit(root, None, None)


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.component_size = [1] * size

    def find(self, vertex: int) -> int:
        root = vertex
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[vertex] != vertex:
            parent = self.parent[vertex]
            self.parent[vertex] = root
            vertex = parent
        return root

    def union(self, left: int, right: int) -> bool:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return False
        if self.component_size[left_root] < self.component_size[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.component_size[left_root] += self.component_size[right_root]
        return True


def kruskal_mst(
    vertex_count: int,
    edges: Iterable[tuple[int, int, int]],
) -> tuple[int, list[tuple[int, int, int]]]:
    if vertex_count < 0:
        raise ValueError("vertex_count는 음수일 수 없습니다.")
    if vertex_count == 0:
        return 0, []

    normalized: list[tuple[int, int, int]] = []
    for source, target, weight in edges:
        _validate_vertex(vertex_count, source)
        _validate_vertex(vertex_count, target)
        normalized.append((source, target, weight))

    groups = _DisjointSet(vertex_count)
    chosen: list[tuple[int, int, int]] = []
    total = 0
    for source, target, weight in sorted(
        normalized,
        key=lambda edge: (edge[2], edge[0], edge[1]),
    ):
        if groups.union(source, target):
            chosen.append((source, target, weight))
            total += weight
            if len(chosen) == vertex_count - 1:
                break

    if len(chosen) != vertex_count - 1:
        raise ValueError("그래프가 연결되어 있지 않습니다.")
    return total, chosen


def bellman_ford(
    vertex_count: int,
    edges: Sequence[tuple[int, int, int]],
    start: int,
) -> list[int | None]:
    if vertex_count < 0:
        raise ValueError("vertex_count는 음수일 수 없습니다.")
    _validate_vertex(vertex_count, start)

    normalized = list(edges)
    for source, target, _weight in normalized:
        _validate_vertex(vertex_count, source)
        _validate_vertex(vertex_count, target)

    distance: list[int | None] = [None] * vertex_count
    distance[start] = 0
    for _ in range(max(0, vertex_count - 1)):
        changed = False
        for source, target, weight in normalized:
            if distance[source] is None:
                continue
            candidate = distance[source] + weight
            if distance[target] is None or candidate < distance[target]:
                distance[target] = candidate
                changed = True
        if not changed:
            break

    for source, target, weight in normalized:
        if distance[source] is None:
            continue
        candidate = distance[source] + weight
        if distance[target] is None or candidate < distance[target]:
            raise ValueError("시작점에서 도달 가능한 음수 사이클이 있습니다.")
    return distance


def kmp_find(text: str, pattern: str) -> int:
    if pattern == "":
        return 0

    prefix = [0] * len(pattern)
    matched = 0
    for index in range(1, len(pattern)):
        while matched > 0 and pattern[index] != pattern[matched]:
            matched = prefix[matched - 1]
        if pattern[index] == pattern[matched]:
            matched += 1
        prefix[index] = matched

    matched = 0
    for index, character in enumerate(text):
        while matched > 0 and character != pattern[matched]:
            matched = prefix[matched - 1]
        if character == pattern[matched]:
            matched += 1
        if matched == len(pattern):
            return index - len(pattern) + 1
    return -1


def max_flow(
    capacity: Sequence[Sequence[int]],
    source: int,
    sink: int,
) -> tuple[int, list[list[int]]]:
    size = len(capacity)
    if any(len(row) != size for row in capacity):
        raise ValueError("capacity matrix는 정사각형이어야 합니다.")
    if any(value < 0 for row in capacity for value in row):
        raise ValueError("capacity는 음수일 수 없습니다.")
    _validate_vertex(size, source)
    _validate_vertex(size, sink)
    flow = [[0] * size for _ in range(size)]
    if source == sink:
        return 0, flow

    total = 0
    while True:
        parent: list[int | None] = [None] * size
        parent[source] = source
        queue: deque[int] = deque([source])
        while queue and parent[sink] is None:
            vertex = queue.popleft()
            for target in range(size):
                remaining = (
                    capacity[vertex][target]
                    - flow[vertex][target]
                    + flow[target][vertex]
                )
                if remaining > 0 and parent[target] is None:
                    parent[target] = vertex
                    queue.append(target)
                    if target == sink:
                        break
        if parent[sink] is None:
            return total, flow

        amount: int | None = None
        vertex = sink
        while vertex != source:
            previous = parent[vertex]
            assert previous is not None
            edge_capacity = (
                capacity[previous][vertex]
                - flow[previous][vertex]
                + flow[vertex][previous]
            )
            amount = edge_capacity if amount is None else min(amount, edge_capacity)
            vertex = previous
        assert amount is not None

        vertex = sink
        while vertex != source:
            previous = parent[vertex]
            assert previous is not None
            cancelled = min(amount, flow[vertex][previous])
            flow[vertex][previous] -= cancelled
            flow[previous][vertex] += amount - cancelled
            vertex = previous
        total += amount


def lcs_length(left: str, right: str) -> int:
    if len(right) > len(left):
        left, right = right, left
    previous = [0] * (len(right) + 1)
    for left_character in left:
        current = [0]
        for index, right_character in enumerate(right, start=1):
            if left_character == right_character:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[-1]))
        previous = current
    return previous[-1]
