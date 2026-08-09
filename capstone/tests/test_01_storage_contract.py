from __future__ import annotations

from dataclasses import replace
import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import (
    ClientRequest,
    Command,
    LogEntry,
    MemoryStorage,
    PersistentState,
    SessionRecord,
    SimulatedCrash,
    build_snapshot,
    canonical_fingerprint,
)


def request(kind: str, key: str, value: object = None) -> ClientRequest:
    command = Command(kind=kind, key=key, value=value)
    return ClientRequest("client", 1, canonical_fingerprint(command), command)


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
            storage.save(PersistentState(current_term=1, log=[
                LogEntry(index=2, term=1, request=request("put", "x", 1))
            ]))

    def test_atomic_save_crash_boundary_is_observable(self) -> None:
        storage = MemoryStorage()
        next_state = PersistentState(current_term=1, voted_for="B")
        storage.fail_next_save("before")
        with self.assertRaises(SimulatedCrash):
            storage.save(next_state)
        self.assertEqual(0, storage.load().current_term)
        storage.fail_next_save("after")
        with self.assertRaises(SimulatedCrash):
            storage.save(next_state)
        self.assertEqual("B", storage.load().voted_for)

    def test_log_terms_must_not_move_backwards(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-decreasing"):
            MemoryStorage(PersistentState(current_term=3, log=[
                LogEntry(1, 3, request("put", "x", 1)),
                LogEntry(2, 2, request("put", "x", 2)),
            ]))

    def test_snapshot_checksum_and_rollback_are_rejected(self) -> None:
        command = Command("put", "x", 1)
        session = SessionRecord(1, canonical_fingerprint(command), "OK")
        current = build_snapshot(
            last_included_index=2, last_included_term=2,
            state_machine={"x": 1}, client_sessions={"c": session},
            configuration=("A", "B", "C"), generation=2,
        )
        storage = MemoryStorage(PersistentState(current_term=2, snapshot=current))
        stale = build_snapshot(
            last_included_index=1, last_included_term=1,
            state_machine={}, client_sessions={},
            configuration=("A", "B", "C"), generation=1,
        )
        with self.assertRaisesRegex(ValueError, "backwards"):
            storage.save(PersistentState(current_term=2, snapshot=stale))
        with self.assertRaisesRegex(ValueError, "checksum"):
            storage.save(PersistentState(
                current_term=2, snapshot=replace(current, checksum="0" * 64),
            ))


if __name__ == "__main__":
    unittest.main()
