from __future__ import annotations


class PageFullError(RuntimeError):
    pass


class SlottedPage:
    def __init__(self, page_size: int = 256) -> None:
        # TODO: 페이지 헤더, slot directory, free-space 경계를 초기화한다.
        self.page_size = page_size

    def insert(self, payload: bytes) -> int:
        raise NotImplementedError

    def read(self, slot_id: int) -> bytes:
        raise NotImplementedError

    def delete(self, slot_id: int) -> None:
        raise NotImplementedError

    def update(self, slot_id: int, payload: bytes) -> None:
        raise NotImplementedError

    def compact(self) -> None:
        raise NotImplementedError

    @property
    def free_space(self) -> int:
        raise NotImplementedError

    def serialize(self) -> bytes:
        raise NotImplementedError

    @classmethod
    def from_bytes(cls, raw: bytes) -> "SlottedPage":
        raise NotImplementedError
