from __future__ import annotations

import unittest

from _load import CAPSTONE_ROOT  # noqa: F401
from dskv import ClientRequest, Command, MemoryStorage, Node, Role, canonical_fingerprint


class ClientContractTest(unittest.TestCase):
    def test_follower_does_not_accept_mutating_command(self) -> None:
        node = Node("A", ["B", "C"], MemoryStorage(), election_timeout=5)
        command = Command(kind="put", key="x", value=1)
        request = ClientRequest("client-1", 1, canonical_fingerprint(command), command)
        messages, response = node.submit(request, now=0)
        self.assertEqual(Role.FOLLOWER, node.role)
        self.assertEqual([], messages)
        self.assertIsNotNone(response)
        self.assertEqual("NOT_LEADER", response.status)
        self.assertEqual({}, node.state_machine)


if __name__ == "__main__":
    unittest.main()
