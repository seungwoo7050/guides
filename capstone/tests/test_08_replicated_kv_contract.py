from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import ClientRequest, Cluster, Command, canonical_fingerprint


def request(sequence: int, command: Command) -> ClientRequest:
    return ClientRequest("client", sequence, canonical_fingerprint(command), command)


def elect_a(cluster: Cluster) -> None:
    cluster.tick("A")
    cluster.tick("A")
    cluster.deliver_all()
    if cluster.leaders() != ["A"]:
        raise AssertionError(f"expected A leader, got {cluster.leaders()}")


def commit(cluster: Cluster, sequence: int, command: Command):
    immediate = cluster.submit("A", request(sequence, command))
    if immediate is not None:
        raise AssertionError(f"leader replied before commit/apply: {immediate}")
    cluster.deliver_all()
    responses = [item for item in cluster.drain_responses() if item.sequence == sequence]
    if len(responses) != 1:
        raise AssertionError(f"expected one response for sequence {sequence}: {responses}")
    return responses[0]


class ReplicatedKVContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cluster = Cluster(["A", "B", "C"], {"A": 2, "B": 4, "C": 8})
        elect_a(self.cluster)

    def test_put_logged_get_and_cas_apply_after_commit(self) -> None:
        put = commit(self.cluster, 1, Command("put", "x", 1))
        self.assertEqual("OK", put.status)
        read = commit(self.cluster, 2, Command("get", "x"))
        self.assertEqual(("OK", 1), (read.status, read.result))
        mismatch = commit(
            self.cluster, 3, Command("compare_and_set", "x", 2, expected=9)
        )
        self.assertEqual("MISMATCH", mismatch.status)
        self.assertEqual(1, self.cluster.nodes["A"].state_machine["x"])
        changed = commit(
            self.cluster, 4, Command("compare_and_set", "x", 2, expected=1)
        )
        self.assertEqual("OK", changed.status)
        self.assertEqual(2, self.cluster.nodes["A"].state_machine["x"])

    def test_response_loss_leader_replacement_and_retry_have_one_effect(self) -> None:
        command = Command("put", "x", 1)
        self.assertIsNone(self.cluster.submit("A", request(1, command)))
        self.cluster.deliver_all()
        # Propagate the advanced commit frontier, then lose A's queued response.
        self.cluster.tick("A")
        self.cluster.deliver_all()
        self.cluster.crash("A")
        for _ in range(4):
            self.cluster.tick("B")
        self.cluster.deliver_all()
        self.assertEqual(["B"], self.cluster.leaders())
        replay = self.cluster.submit("B", request(1, command))
        self.assertIsNotNone(replay)
        self.assertEqual("OK", replay.status)
        self.assertEqual(1, self.cluster.nodes["B"].state_machine["x"])

    def test_snapshot_restart_preserves_kv_session_and_configuration(self) -> None:
        command = Command("put", "x", 1)
        response = commit(self.cluster, 1, command)
        self.assertEqual("OK", response.status)
        node = self.cluster.nodes["A"]
        self.cluster.create_snapshot("A", node.last_applied)
        self.cluster.crash("A")
        self.cluster.restart("A")
        restored = self.cluster.nodes["A"]
        self.assertEqual({"x": 1}, restored.state_machine)
        self.assertEqual(1, restored.client_sessions["client"].last_sequence)
        self.assertEqual(("A", "B", "C"), restored.configuration)


if __name__ == "__main__":
    unittest.main()
