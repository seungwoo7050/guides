from __future__ import annotations

import json
import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import (
    ClientRequest,
    Command,
    DeterministicNetwork,
    LogEntry,
    MemoryStorage,
    Message,
    MessageKind,
    Node,
    PersistentState,
    SessionRecord,
    build_snapshot,
    canonical_fingerprint,
)


class HarnessContractTest(unittest.TestCase):
    def test_duplicate_preserves_message_id_but_has_new_delivery_id(self) -> None:
        network = DeterministicNetwork(["A", "B", "C"])
        first = network.send(Message("A", "B", 1, MessageKind.REQUEST_VOTE))
        second = network.duplicate(first, extra_delay=2)
        pending = dict(network.pending())
        self.assertNotEqual(first, second)
        self.assertEqual(pending[first].message_id, pending[second].message_id)
        network.delay(first, 3)
        disposition, delivery_id, _message = network.pop(second)
        self.assertEqual(("DELIVER", second), (disposition, delivery_id))

    def test_partition_consumes_delivery(self) -> None:
        network = DeterministicNetwork(["A", "B", "C"])
        delivery = network.send(Message("A", "B", 1, MessageKind.APPEND_ENTRIES))
        network.partition("A", "B")
        disposition, actual, _message = network.pop(delivery)
        self.assertEqual(("PARTITION_DROPPED", delivery), (disposition, actual))
        self.assertEqual([], network.pending())

    def test_restart_restores_snapshot_state_sessions_and_configuration(self) -> None:
        command = Command("put", "x", 1)
        fingerprint = canonical_fingerprint(command)
        snapshot = build_snapshot(
            last_included_index=4,
            last_included_term=2,
            state_machine={"x": 1},
            client_sessions={"c": SessionRecord(1, fingerprint, "OK")},
            configuration=("A", "B", "C"),
            generation=1,
        )
        storage = MemoryStorage(PersistentState(current_term=2, snapshot=snapshot))
        node = Node("A", ["B", "C"], storage, election_timeout=3)
        self.assertEqual({"x": 1}, node.state_machine)
        self.assertEqual(1, node.client_sessions["c"].last_sequence)
        self.assertEqual(("A", "B", "C"), node.configuration)

    def test_snapshot_compacts_only_at_applied_boundary(self) -> None:
        command = Command("put", "x", 1)
        request = ClientRequest("c", 1, canonical_fingerprint(command), command)
        storage = MemoryStorage(PersistentState(
            current_term=1,
            log=[LogEntry(1, 1, request)],
        ))
        node = Node("A", ["B", "C"], storage, election_timeout=3)
        node.commit_index = node.last_applied = 1
        node.state_machine = {"x": 1}
        snapshot = node.create_snapshot(1)
        self.assertEqual(1, snapshot.last_included_index)
        self.assertEqual([], storage.load().log)

    def test_snapshot_refuses_uncommitted_applied_boundary(self) -> None:
        node = Node("A", ["B", "C"], MemoryStorage(), election_timeout=3)
        node.last_applied = 1
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            node.create_snapshot(1)

    def test_faults_and_reconfiguration_are_hash_chained_trace_events(self) -> None:
        from dskv import Cluster

        schedule = [
            {"kind": "partition", "source": "A", "target": "B"},
            {"kind": "heal", "source": "A", "target": "B"},
            {"kind": "crash", "node": "C"},
            {"kind": "restart", "node": "C"},
        ]
        first = Cluster(["A", "B", "C"])
        first.run_schedule(schedule)
        self.assertEqual(
            ["partition", "heal", "crash", "restart"],
            [event["kind"] for event in first.trace],
        )
        for left, right in zip(first.trace, first.trace[1:]):
            self.assertEqual(left["state_after_hash"], right["state_before_hash"])

        second = Cluster(["A", "B", "C"])
        second.run_schedule(schedule)
        canonical = lambda trace: json.dumps(trace, sort_keys=True, separators=(",", ":"))
        self.assertEqual(canonical(first.trace), canonical(second.trace))


if __name__ == "__main__":
    unittest.main()
