from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import Command, LogEntry, MemoryStorage, PersistentState


class StorageContractTest(unittest.TestCase):
    def test_load_returns_copy_and_save_is_explicit(self) -> None:
        storage = MemoryStorage(PersistentState(current_term=2, voted_for="A"))
        loaded = storage.load()
        loaded.current_term = 9
        self.assertEqual(2, storage.load().current_term)
        storage.save(loaded)
        self.assertEqual(9, storage.load().current_term)

    def test_log_must_be_contiguous(self) -> None:
        storage = MemoryStorage()
        with self.assertRaises(ValueError):
            storage.save(PersistentState(log=[
                LogEntry(index=2, term=1, command=Command(kind="put", key="x", value=1))
            ]))


if __name__ == "__main__":
    unittest.main()
