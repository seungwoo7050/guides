from __future__ import annotations


class WALViolation(RuntimeError):
    pass


class DuplicateKeyError(RuntimeError):
    pass


class DiskManager:
    def __init__(self, page_size: int = 256) -> None:
        # TODO: persisted pages와 page allocator를 구현한다.
        self.page_size = page_size


class LogManager:
    def __init__(self) -> None:
        # TODO: append-only log, LSN, durable boundary를 구현한다.
        pass


class BufferPool:
    def __init__(self, disk: DiskManager, log: LogManager, capacity: int = 2) -> None:
        raise NotImplementedError


class MiniStorageEngine:
    def __init__(self, disk: DiskManager | None = None, log: LogManager | None = None, *, buffer_capacity: int = 2) -> None:
        raise NotImplementedError("GUIDE_SEMANTIC:mini-storage-engine")

    def insert(self, key: int, value: bytes) -> None:
        raise NotImplementedError

    def get(self, key: int) -> bytes:
        raise NotImplementedError

    def range(self, start: int, end: int) -> list[tuple[int, bytes]]:
        raise NotImplementedError

    def checkpoint(self) -> None:
        raise NotImplementedError

    @classmethod
    def recover(cls, disk: DiskManager, durable_records: list[object], *, buffer_capacity: int = 2) -> "MiniStorageEngine":
        raise NotImplementedError
