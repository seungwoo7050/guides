"""검증용 기준 구현.

빠른 구현만을 목표로 하지 않고 각 공개 계약과 실패 조건을 명시적으로
지킨다. tests의 oracle은 이 파일과 다른 계산 방법을 사용한다.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import heapq
from typing import Iterable, Sequence


# [Implementation 1] 누적 배열이 구간 질의의 상태를 소유하게 한다.
# 첫 0 sentinel을 두면 모든 반열린 구간을 두 누적값의 차이라는 한 계약으로 처리할 수 있다.
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


# [Implementation 2] 정렬은 호출자 전조건으로 두고 후보 구간의 경계만 소유한다.
# [lo, hi) 안에 첫 삽입 위치가 있다는 불변식이 종료 시 하나의 위치로 수렴한다.
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


# [Implementation 7] 그래프 함수가 공유할 정점 경계와 미방문 상태를 먼저 고정한다.
# BFS에서는 None이 아직 발견되지 않은 거리이며 queue에 넣는 순간 최초 거리가 확정된다.
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


# [Implementation 8] 일회성 edge 입력을 adjacency가 소유한 뒤 nonnegative 최단 경로를 확장한다.
# heap의 값이 현재 distance와 다르면 이미 더 나은 경로가 소유권을 넘겨받은 stale entry다.
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


# [Implementation 4] best[c]는 지금까지 처리한 물건으로 capacity c에서 얻는 최적값이다.
# capacity를 역순으로 방문해야 현재 물건의 값이 같은 iteration에서 다시 사용되지 않는다.
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


# [Implementation 5] 가장 일찍 끝나는 구간이 이후 선택을 위한 frontier를 소유한다.
# 종료·시작 순 tie-break는 같은 최적 개수에서도 결과를 결정적으로 유지한다.
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


# [Implementation 3] node 구조와 subtree 검증 결과를 같은 red-black 계약으로 묶는다.
# 재귀 호출은 key bound를 인자로 전달하고 black height를 반환하며 색·BST·red-red 위반은 즉시 실패시킨다.
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


# [Implementation 9] DSU가 component 대표와 size를 소유하고 Kruskal은 선택 edge를 소유한다.
# union 성공만 certificate에 넣어 cycle을 막고 V-1개에 못 미치면 disconnected 상태로 실패한다.
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


# [Implementation 10] edge를 반복 가능한 상태로 고정해 경로 edge 수별 relaxation을 수행한다.
# 마지막 추가 개선은 시작점에서 도달 가능한 음수 cycle이라는 별도 실패 상태다.
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


# [Implementation 12] prefix table이 pattern의 proper-prefix 상태와 fallback 경로를 소유한다.
# 빈 pattern 계약을 먼저 끝내고 mismatch 때 이미 확인한 text를 다시 읽지 않는다.
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


# [Implementation 11] flow matrix 자체를 원본 directed edge의 검증 가능한 certificate로 유지한다.
# residual path는 기존 역방향 flow를 먼저 취소한 뒤 새 flow를 보내 capacity와 conservation을 보존한다.
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


# [Implementation 6] previous와 current row가 두 문자열 prefix의 LCS 상태를 번갈아 소유한다.
# 짧은 문자열을 열 축으로 두어 recurrence는 유지하면서 추가 공간을 제한한다.
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
