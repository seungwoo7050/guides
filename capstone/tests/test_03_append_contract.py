from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import Command, LogEntry, MemoryStorage, Message, MessageKind, Node, PersistentState


class AppendContractTest(unittest.TestCase):
    def test_conflicting_suffix_is_replaced_after_matching_prefix(self) -> None:
        storage = MemoryStorage(PersistentState(
            current_term=5,
            log=[
                LogEntry(1, 1, Command("put", "a", 1)),
                LogEntry(2, 2, Command("put", "b", 1)),
                LogEntry(3, 4, Command("put", "c", 9)),
                LogEntry(4, 4, Command("put", "d", 9)),
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
                    LogEntry(3, 3, Command("put", "c", 1)),
                    LogEntry(4, 6, Command("put", "e", 1)),
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
