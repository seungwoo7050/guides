"""Bellman–Ford의 마지막 음수 cycle 검사를 생략한 결함."""

from _load_reference import *  # noqa: F401,F403


def bellman_ford(vertex_count, edges, start):
    if vertex_count < 0 or not 0 <= start < vertex_count:
        raise ValueError("invalid graph")
    normalized = list(edges)
    distance = [None] * vertex_count
    distance[start] = 0
    for _ in range(max(0, vertex_count - 1)):
        for source, target, weight in normalized:
            if not (0 <= source < vertex_count and 0 <= target < vertex_count):
                raise ValueError("invalid vertex")
            if distance[source] is None:
                continue
            candidate = distance[source] + weight
            if distance[target] is None or candidate < distance[target]:
                distance[target] = candidate
    return distance
