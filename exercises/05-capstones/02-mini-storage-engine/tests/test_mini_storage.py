from __future__ import annotations

import copy
import unittest

from mini_storage import (
    BufferPool,
    DiskManager,
    DuplicateKeyError,
    LogManager,
    MiniStorageEngine,
    WALViolation,
)


class MiniStorageEngineTests(unittest.TestCase):
    def test_insert_get_range_and_duplicate_contract(self) -> None:
        engine = MiniStorageEngine(DiskManager(160), buffer_capacity=2)
        for key in (30, 10, 20, 40):
            engine.insert(key, f"value-{key}".encode())
        self.assertEqual(engine.get(20), b"value-20")
        self.assertEqual(engine.range(15, 35), [(20, b"value-20"), (30, b"value-30")])
        with self.assertRaises(DuplicateKeyError):
            engine.insert(20, b"duplicate")

    def test_grows_to_multiple_pages(self) -> None:
        disk = DiskManager(128)
        engine = MiniStorageEngine(disk, buffer_capacity=1)
        for key in range(12):
            engine.insert(key, b"x" * 20)
        engine.checkpoint()
        self.assertGreater(len(disk.page_ids), 1)
        self.assertEqual(engine.get(11), b"x" * 20)

    def test_buffer_pool_enforces_wal_before_data(self) -> None:
        disk = DiskManager(128)
        page_id = disk.allocate()
        log = LogManager()
        pool = BufferPool(disk, log, capacity=1)
        lsn = log.insert(1, page_id, 7, b"seven")
        page = pool.fetch(page_id)
        page.insert(7, b"seven")
        page.page_lsn = lsn
        pool.unpin(page_id, dirty=True)
        with self.assertRaises(WALViolation):
            pool.flush(page_id)
        log.flush(lsn)
        pool.flush(page_id)

    def test_recovers_committed_log_without_data_page_flush(self) -> None:
        disk = DiskManager(160)
        engine = MiniStorageEngine(disk)
        engine.insert(1, b"durable-log")
        # checkpoint를 하지 않았으므로 data page는 insert 전 상태일 수 있다.
        recovered = MiniStorageEngine.recover(disk, engine.log.durable_records())
        self.assertEqual(recovered.get(1), b"durable-log")

    def test_ignores_uncommitted_insert(self) -> None:
        disk = DiskManager(160)
        page_id = disk.allocate()
        log = LogManager()
        lsn = log.insert(99, page_id, 9, b"not-committed")
        log.flush(lsn)
        recovered = MiniStorageEngine.recover(disk, log.durable_records())
        with self.assertRaises(KeyError):
            recovered.get(9)

    def test_recovery_is_idempotent(self) -> None:
        disk = DiskManager(160)
        engine = MiniStorageEngine(disk)
        engine.insert(1, b"one")
        durable = engine.log.durable_records()
        first = MiniStorageEngine.recover(disk, durable)
        snapshot = copy.deepcopy(disk.pages)
        second = MiniStorageEngine.recover(disk, durable)
        self.assertEqual(disk.pages, snapshot)
        self.assertEqual(first.get(1), second.get(1))


if __name__ == "__main__":
    unittest.main()
