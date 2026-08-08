from __future__ import annotations

from typing import Generic, TypeVar

V = TypeVar("V")


class BPlusTree(Generic[V]):
    def __init__(self, order: int = 4) -> None:
        # TODO: root node와 최대 key 수를 초기화한다.
        self.order = order

    def insert(self, key: int, value: V) -> None:
        raise NotImplementedError

    def get(self, key: int) -> V:
        raise NotImplementedError

    def range(self, start: int, end: int) -> list[tuple[int, V]]:
        raise NotImplementedError

    def validate(self) -> None:
        raise NotImplementedError
