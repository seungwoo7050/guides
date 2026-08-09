from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import (
    ClientRequest, Command, MemoryStorage, Node, Role, SessionRecord,
    canonical_fingerprint,
)


def request(sequence: int, command: Command, fingerprint: str | None = None) -> ClientRequest:
    return ClientRequest("client", sequence, fingerprint or canonical_fingerprint(command), command)


class ClientSequenceContractTest(unittest.TestCase):
    def test_leader_does_not_reply_before_commit_and_apply(self) -> None:
        node = Node("A", ["B", "C"], MemoryStorage(), election_timeout=5)
        node.role = Role.LEADER
        _messages, response = node.submit(request(1, Command("put", "x", 1)), now=0)
        self.assertIsNone(response)

    def node_with_completed_request(self) -> tuple[Node, Command]:
        prior = Command("put", "x", 1)
        node = Node("A", ["B", "C"], MemoryStorage(), election_timeout=5)
        node.role = Role.LEADER
        node.state_machine = {"x": 1}
        node.client_sessions["client"] = SessionRecord(
            2, canonical_fingerprint(prior), "cached-result",
        )
        return node, prior

    def test_exact_duplicate_reuses_the_cached_result(self) -> None:
        node, prior = self.node_with_completed_request()
        messages, response = node.submit(request(2, prior), now=0)
        self.assertEqual([], messages)
        self.assertEqual(("OK", "cached-result"), (response.status, response.result) if response else None)

    def test_same_sequence_with_another_fingerprint_is_conflict(self) -> None:
        node, _prior = self.node_with_completed_request()
        messages, response = node.submit(request(2, Command("put", "x", 9)), now=0)
        self.assertEqual([], messages)
        self.assertEqual("CONFLICT", response.status if response else None)
        self.assertEqual({"x": 1}, node.state_machine)

    def test_stale_sequence_is_rejected_without_effect(self) -> None:
        node, _prior = self.node_with_completed_request()
        messages, response = node.submit(request(1, Command("get", "x")), now=0)
        self.assertEqual([], messages)
        self.assertEqual("STALE_SEQUENCE", response.status if response else None)
        self.assertEqual({"x": 1}, node.state_machine)

    def test_sequence_gap_is_distinct_from_stale_and_conflict(self) -> None:
        node, _prior = self.node_with_completed_request()
        messages, response = node.submit(request(4, Command("put", "x", 2)), now=0)
        self.assertEqual([], messages)
        self.assertEqual("SEQUENCE_GAP", response.status if response else None)
        self.assertEqual({"x": 1}, node.state_machine)


if __name__ == "__main__":
    unittest.main()
