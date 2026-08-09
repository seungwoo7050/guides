from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import (
    ClientRequest, Command, LogEntry, MemoryStorage, Message, MessageKind,
    Node, PersistentState, canonical_fingerprint,
)


def entry(index: int, term: int, key: str, value: object) -> LogEntry:
    command = Command("put", key, value)
    request = ClientRequest("fixture", index, canonical_fingerprint(command), command)
    return LogEntry(index, term, request)


class AppendContractTest(unittest.TestCase):
    def test_conflicting_suffix_is_replaced_after_matching_prefix(self) -> None:
        storage = MemoryStorage(PersistentState(
            current_term=5,
            log=[
                entry(1, 1, "a", 1),
                entry(2, 2, "b", 1),
                entry(3, 4, "c", 9),
                entry(4, 4, "d", 9),
            ],
        ))
        node = Node("F", ["L", "X"], storage, election_timeout=5)
        message = Message(
            source="L",
            target="F",
            term=6,
            kind=MessageKind.APPEND_ENTRIES,
            payload={
                "prev_log_index": 2,
                "prev_log_term": 2,
                "entries": [
                    entry(3, 3, "c", 1),
                    entry(4, 6, "e", 1),
                ],
                "leader_commit": 2,
            },
        )
        responses = node.receive(message, now=1)
        persisted = storage.load()
        self.assertEqual([1, 2, 3, 6], [entry.term for entry in persisted.log])
        self.assertTrue(responses[0].payload["success"])
        self.assertEqual(4, responses[0].payload["match_index"])


if __name__ == "__main__":
    unittest.main()
