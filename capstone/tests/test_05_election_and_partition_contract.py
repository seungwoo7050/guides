from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import Cluster, LogEntry, MemoryStorage, Message, MessageKind, Node, PersistentState, Role


class ElectionAndPartitionContractTest(unittest.TestCase):
    def test_staggered_timeout_elects_one_leader(self) -> None:
        cluster = Cluster(["A", "B", "C"], {"A": 2, "B": 4, "C": 6})
        cluster.tick("A")
        cluster.tick("A")
        cluster.deliver_all()
        self.assertEqual(1, len(cluster.leaders()))

    def test_stale_candidate_is_rejected(self) -> None:
        storage = MemoryStorage(PersistentState(
            current_term=2,
            log=[LogEntry(index=1, term=2, request=None)],
        ))
        node = Node("A", ["B", "C"], storage, election_timeout=5)
        response = node.receive(Message(
            "B", "A", 3, MessageKind.REQUEST_VOTE,
            {"last_log_index": 1, "last_log_term": 1},
        ), now=1)
        self.assertFalse(response[0].payload["vote_granted"])

    def test_higher_term_message_steps_leader_down(self) -> None:
        node = Node("A", ["B", "C"], MemoryStorage(), election_timeout=5)
        node.role = Role.LEADER
        node.receive(Message("B", "A", 9, MessageKind.APPEND_ENTRIES, {
            "prev_log_index": 0, "prev_log_term": 0, "entries": [], "leader_commit": 0,
        }), now=1)
        self.assertEqual(Role.FOLLOWER, node.role)

    def test_one_way_partition_replaces_old_leader_in_a_higher_term(self) -> None:
        cluster = Cluster(["A", "B", "C"], {"A": 2, "B": 4, "C": 8})
        cluster.tick("A")
        cluster.tick("A")
        cluster.deliver_all()
        self.assertEqual(["A"], cluster.leaders())
        old_term = cluster.nodes["A"].current_term
        cluster.partition("A", "B")
        cluster.partition("A", "C")
        for _ in range(4):
            cluster.tick("B")
        cluster.deliver_all()
        self.assertEqual(["B"], cluster.leaders())
        self.assertGreater(cluster.nodes["B"].current_term, old_term)


if __name__ == "__main__":
    unittest.main()
