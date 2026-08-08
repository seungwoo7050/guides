from __future__ import annotations

import copy
import unittest

from recovery import Disk, LogManager, Page, RecoveryManager, WALViolation


class WALRecoveryTests(unittest.TestCase):
    def test_wal_must_be_flushed_before_page(self) -> None:
        log = LogManager()
        disk = Disk()
        lsn = log.update(1, 0, 0, 10)
        with self.assertRaises(WALViolation):
            disk.write(0, Page(10, lsn), log)
        log.flush(lsn)
        disk.write(0, Page(10, lsn), log)
        self.assertEqual(disk.pages[0], Page(10, lsn))

    def test_redoes_committed_and_undoes_loser(self) -> None:
        log = LogManager()
        committed_lsn = log.update(1, 0, 0, 10)
        log.commit(1)
        log.update(2, 0, 10, 99)
        disk = Disk()
        disk.pages[0] = Page(0, 0)
        RecoveryManager().recover(disk, log.records)
        self.assertEqual(disk.pages[0].value, 10)
        self.assertGreaterEqual(disk.pages[0].page_lsn, committed_lsn)

    def test_multiple_updates_are_undone_in_reverse_order(self) -> None:
        log = LogManager()
        log.update(7, 3, 5, 6)
        log.update(7, 3, 6, 8)
        disk = Disk()
        RecoveryManager().recover(disk, log.records)
        self.assertEqual(disk.pages[3].value, 5)

    def test_page_lsn_skips_old_redo(self) -> None:
        log = LogManager()
        first = log.update(1, 0, 0, 10)
        log.commit(1)
        disk = Disk()
        disk.pages[0] = Page(777, first)
        RecoveryManager().recover(disk, log.records)
        self.assertEqual(disk.pages[0], Page(777, first))

    def test_recovery_is_idempotent(self) -> None:
        log = LogManager()
        log.update(1, 0, 0, 10)
        log.commit(1)
        log.update(2, 1, 0, 20)
        disk = Disk()
        manager = RecoveryManager()
        manager.recover(disk, log.records)
        once = copy.deepcopy(disk.pages)
        manager.recover(disk, log.records)
        self.assertEqual(disk.pages, once)


if __name__ == "__main__":
    unittest.main()
