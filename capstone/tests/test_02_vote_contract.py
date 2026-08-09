from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import MemoryStorage, Message, MessageKind, Node


class VoteContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = MemoryStorage()
        self.node = Node("A", ["B", "C"], self.storage, election_timeout=5)

    def request_vote(self, candidate: str, term: int) -> Message:
        return Message(
            source=candidate,
            target="A",
            term=term,
            kind=MessageKind.REQUEST_VOTE,
            payload={"last_log_index": 0, "last_log_term": 0},
        )

    def test_granted_vote_is_durable_before_response(self) -> None:
        responses = self.node.receive(self.request_vote("B", 1), now=1)
        self.assertEqual("B", self.storage.load().voted_for)
        self.assertEqual(1, self.storage.load().current_term)
        self.assertEqual(1, len(responses))
        self.assertTrue(responses[0].payload["vote_granted"])

    def test_same_term_second_candidate_is_rejected(self) -> None:
        self.node.receive(self.request_vote("B", 1), now=1)
        responses = self.node.receive(self.request_vote("C", 1), now=2)
        self.assertEqual("B", self.storage.load().voted_for)
        self.assertFalse(responses[0].payload["vote_granted"])


if __name__ == "__main__":
    unittest.main()
