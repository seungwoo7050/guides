"""단일·다중 인스턴스 자원의 대기 관계를 분석합니다."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence


class DeadlockInputError(ValueError):
    """자원 벡터나 그래프 입력이 유효하지 않을 때 발생합니다."""


def find_wait_cycle(graph: Mapping[str, Sequence[str]]) -> list[str] | None:
    """단일 인스턴스 대기 그래프에서 한 순환을 반환합니다."""

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    positions: dict[str, int] = {}

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            start = positions[node]
            return stack[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        positions[node] = len(stack)
        stack.append(node)
        for neighbor in graph.get(node, ()):
            cycle = visit(str(neighbor))
            if cycle is not None:
                return cycle
        stack.pop()
        positions.pop(node, None)
        visiting.remove(node)
        visited.add(node)
        return None

    nodes = set(graph)
    for neighbors in graph.values():
        nodes.update(str(item) for item in neighbors)
    for node in sorted(nodes):
        cycle = visit(node)
        if cycle is not None:
            return cycle
    return None


def detect_deadlocked(
    available: Sequence[int],
    allocation: Mapping[str, Sequence[int]],
    outstanding: Mapping[str, Sequence[int]],
) -> set[str]:
    """현재 할당과 미처리 요청으로 완료할 수 없는 작업 집합을 찾습니다."""

    resource_count = _validate_vectors(available, allocation, outstanding)
    work = list(available)
    finish = {tid: all(value == 0 for value in allocation[tid]) for tid in allocation}

    changed = True
    while changed:
        changed = False
        for tid in sorted(allocation):
            if finish[tid]:
                continue
            request = outstanding[tid]
            if all(request[index] <= work[index] for index in range(resource_count)):
                for index in range(resource_count):
                    work[index] += allocation[tid][index]
                finish[tid] = True
                changed = True

    return {tid for tid, completed in finish.items() if not completed}


def safe_sequence(
    available: Sequence[int],
    allocation: Mapping[str, Sequence[int]],
    maximum: Mapping[str, Sequence[int]],
) -> list[str] | None:
    """최대 요구량을 만족하면서 모든 작업을 끝낼 안전 순서를 찾습니다."""

    if set(allocation) != set(maximum):
        raise DeadlockInputError("allocation과 maximum의 작업 집합이 다릅니다.")
    resource_count = _validate_vectors(available, allocation, maximum)
    need: dict[str, list[int]] = {}
    for tid in allocation:
        current = allocation[tid]
        limit = maximum[tid]
        if any(current[index] > limit[index] for index in range(resource_count)):
            raise DeadlockInputError(f"현재 할당이 최대 요구량보다 큽니다: {tid}")
        need[tid] = [limit[index] - current[index] for index in range(resource_count)]

    work = list(available)
    remaining = set(allocation)
    order: list[str] = []
    while remaining:
        candidate = next(
            (
                tid
                for tid in sorted(remaining)
                if all(need[tid][index] <= work[index] for index in range(resource_count))
            ),
            None,
        )
        if candidate is None:
            return None
        order.append(candidate)
        remaining.remove(candidate)
        for index in range(resource_count):
            work[index] += allocation[candidate][index]
    return order


def _validate_vectors(
    available: Sequence[int],
    left: Mapping[str, Sequence[int]],
    right: Mapping[str, Sequence[int]],
) -> int:
    if set(left) != set(right):
        raise DeadlockInputError("두 작업 집합이 다릅니다.")
    if not available:
        raise DeadlockInputError("자원 종류가 하나 이상 필요합니다.")
    resource_count = len(available)
    if any(value < 0 for value in available):
        raise DeadlockInputError("가용 자원 수는 음수일 수 없습니다.")
    for name, vectors in (("left", left), ("right", right)):
        for tid, vector in vectors.items():
            if len(vector) != resource_count:
                raise DeadlockInputError(f"{name} 벡터 길이가 다릅니다: {tid}")
            if any(value < 0 for value in vector):
                raise DeadlockInputError(f"{name} 벡터에 음수가 있습니다: {tid}")
    return resource_count
