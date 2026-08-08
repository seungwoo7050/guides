from __future__ import annotations

import unittest

from slotted_page import PageFullError, SlottedPage


class SlottedPageTests(unittest.TestCase):
    def test_insert_read_delete_and_slot_reuse(self) -> None:
        page = SlottedPage(128)
        first = page.insert(b"first")
        second = page.insert(b"second-record")
        self.assertEqual(page.read(first), b"first")
        page.delete(first)
        with self.assertRaises(KeyError):
            page.read(first)
        reused = page.insert(b"replacement")
        self.assertEqual(reused, first)
        self.assertEqual(page.read(second), b"second-record")

    def test_compaction_keeps_record_identifiers_stable(self) -> None:
        page = SlottedPage(128)
        ids = [page.insert(value) for value in (b"a" * 10, b"b" * 20, b"c" * 10)]
        page.delete(ids[1])
        before = page.free_space
        page.compact()
        self.assertGreaterEqual(page.free_space, before)
        self.assertEqual(page.read(ids[0]), b"a" * 10)
        self.assertEqual(page.read(ids[2]), b"c" * 10)

    def test_failed_update_is_atomic(self) -> None:
        page = SlottedPage(96)
        target = page.insert(b"stable")
        page.insert(b"x" * 40)
        snapshot = page.serialize()
        with self.assertRaises(PageFullError):
            page.update(target, b"y" * 70)
        self.assertEqual(page.serialize(), snapshot)
        self.assertEqual(page.read(target), b"stable")

    def test_failed_insert_is_atomic_even_when_page_is_fragmented(self) -> None:
        page = SlottedPage(96)
        first = page.insert(b"a" * 20)
        second = page.insert(b"b" * 20)
        page.delete(first)
        snapshot = page.serialize()
        with self.assertRaises(PageFullError):
            page.insert(b"c" * 70)
        self.assertEqual(page.serialize(), snapshot)
        self.assertEqual(page.read(second), b"b" * 20)

    def test_round_trip(self) -> None:
        page = SlottedPage(192)
        live = page.insert(b"persisted")
        dead = page.insert(b"deleted")
        page.delete(dead)
        restored = SlottedPage.from_bytes(page.serialize())
        self.assertEqual(restored.read(live), b"persisted")
        with self.assertRaises(KeyError):
            restored.read(dead)

    def test_rejects_empty_record(self) -> None:
        with self.assertRaises(ValueError):
            SlottedPage().insert(b"")


if __name__ == "__main__":
    unittest.main()
