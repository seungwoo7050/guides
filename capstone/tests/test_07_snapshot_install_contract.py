from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import (
    Command, MemoryStorage, Message, MessageKind, Node, SessionRecord,
    build_snapshot, canonical_fingerprint,
)


class SnapshotInstallContractTest(unittest.TestCase):
    def test_install_restores_sessions_and_rejects_stale_snapshot(self) -> None:
        node = Node("C", ["A", "B"], MemoryStorage(), election_timeout=7)
        command = Command("put", "x", 2)
        session = SessionRecord(3, canonical_fingerprint(command), "OK")
        snapshot = build_snapshot(
            last_included_index=8,
            last_included_term=3,
            state_machine={"x": 2},
            client_sessions={"client": session},
            configuration=("A", "B", "C"),
            generation=2,
        )
        node.receive(Message(
            "A", "C", 4, MessageKind.INSTALL_SNAPSHOT, {"snapshot": snapshot}
        ), now=10)
        self.assertEqual(8, node.last_applied)
        self.assertEqual({"x": 2}, node.state_machine)
        self.assertEqual(3, node.client_sessions["client"].last_sequence)
        self.assertEqual(("A", "B", "C"), node.configuration)

        stale = build_snapshot(
            last_included_index=7,
            last_included_term=2,
            state_machine={"x": 1},
            client_sessions={},
            configuration=("A", "B", "C"),
            generation=1,
        )
        node.receive(Message(
            "A", "C", 4, MessageKind.INSTALL_SNAPSHOT, {"snapshot": stale}
        ), now=11)
        self.assertEqual((8, {"x": 2}, 3), (
            node.last_applied, node.state_machine,
            node.client_sessions["client"].last_sequence,
        ))


if __name__ == "__main__":
    unittest.main()
