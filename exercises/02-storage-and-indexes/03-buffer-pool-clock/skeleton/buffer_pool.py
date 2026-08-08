from __future__ import annotations


class BufferPoolFull(RuntimeError):
    pass


class DiskManager:
    def __init__(self, page_size: int = 64) -> None:
        self.page_size = page_size
        # TODO: persistent page map과 I/O counters를 초기화한다.

    def allocate(self, initial: bytes = b"") -> int:
        raise NotImplementedError

    def read(self, page_id: int) -> bytes:
        raise NotImplementedError

    def write(self, page_id: int, data: bytes) -> None:
        raise NotImplementedError


class BufferPool:
    def __init__(self, disk: DiskManager, capacity: int) -> None:
        raise NotImplementedError

    def fetch(self, page_id: int) -> bytearray:
        raise NotImplementedError

    def unpin(self, page_id: int, *, dirty: bool = False) -> None:
        raise NotImplementedError

    def flush(self, page_id: int) -> None:
        raise NotImplementedError

    def flush_all(self) -> None:
        raise NotImplementedError
