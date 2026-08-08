"""데드락 분석의 학습자 구현 골격입니다."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class DeadlockInputError(ValueError):
    pass


def find_wait_cycle(graph: Mapping[str, Sequence[str]]) -> list[str] | None:
    raise NotImplementedError("DFS 방문 상태로 한 순환을 찾으세요.")


def detect_deadlocked(
    available: Sequence[int],
    allocation: Mapping[str, Sequence[int]],
    outstanding: Mapping[str, Sequence[int]],
) -> set[str]:
    raise NotImplementedError("완료 가능한 작업의 자원을 반복해서 반환하세요.")


def safe_sequence(
    available: Sequence[int],
    allocation: Mapping[str, Sequence[int]],
    maximum: Mapping[str, Sequence[int]],
) -> list[str] | None:
    raise NotImplementedError("모든 작업을 끝낼 수 있는 안전 순서를 찾으세요.")
