from __future__ import annotations

import unittest

from buffer_pool import BufferPool, BufferPoolFull, DiskManager


class BufferPoolTests(unittest.TestCase):
    def test_cache_hit_avoids_second_disk_read(self) -> None:
        disk = DiskManager(16)
        page = disk.allocate(b"alpha")
        pool = BufferPool(disk, 2)
        first = pool.fetch(page)
        pool.unpin(page)
        second = pool.fetch(page)
        self.assertIs(first, second)
        self.assertEqual(disk.read_count, 1)

    def test_dirty_eviction_writes_before_reuse(self) -> None:
        disk = DiskManager(16)
        first = disk.allocate(b"first")
        second = disk.allocate(b"second")
        pool = BufferPool(disk, 1)
        data = pool.fetch(first)
        data[:7] = b"changed"
        pool.unpin(first, dirty=True)
        pool.fetch(second)
        self.assertEqual(disk.pages[first][:7], b"changed")
        self.assertEqual(disk.write_count, 1)

    def test_pinned_page_is_not_evicted(self) -> None:
        disk = DiskManager(8)
        first = disk.allocate(b"one")
        second = disk.allocate(b"two")
        pool = BufferPool(disk, 1)
        pool.fetch(first)
        with self.assertRaises(BufferPoolFull):
            pool.fetch(second)

    def test_dirty_flag_survives_multiple_pins(self) -> None:
        disk = DiskManager(8)
        page = disk.allocate(b"old")
        pool = BufferPool(disk, 1)
        data = pool.fetch(page)
        pool.fetch(page)
        data[:3] = b"new"
        pool.unpin(page, dirty=True)
        pool.unpin(page)
        pool.flush(page)
        self.assertEqual(disk.pages[page][:3], b"new")

    def test_rejects_double_unpin(self) -> None:
        disk = DiskManager(8)
        page = disk.allocate()
        pool = BufferPool(disk, 1)
        pool.fetch(page)
        pool.unpin(page)
        with self.assertRaises(RuntimeError):
            pool.unpin(page)


if __name__ == "__main__":
    unittest.main()
