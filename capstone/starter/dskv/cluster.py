"""Deterministic cluster harness shared by learner tests."""
from __future__ import annotations

from typing import Any

from .network import DeterministicNetwork
from .node import Node
from .storage import MemoryStorage
from .types import ClientRequest, ClientResponse, Message, Role


class Cluster:
    def __init__(self, node_ids: list[str], election_timeouts: dict[str, int] | None = None) -> None:
        if len(node_ids) < 3:
            raise ValueError("capstone core requires at least three nodes")
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("node ids must be unique")
        self.node_ids = tuple(node_ids)
        self.storage = {node_id: MemoryStorage() for node_id in node_ids}
        election_timeouts = election_timeouts or {
            node_id: index + 3 for index, node_id in enumerate(node_ids)
        }
        self._timeouts = dict(election_timeouts)
        self.nodes = {
            node_id: self._new_node(node_id)
            for node_id in node_ids
        }
        self.running = set(node_ids)
        self.network = DeterministicNetwork(node_ids)
        self.now = 0
        self.trace: list[dict[str, Any]] = []

    def _new_node(self, node_id: str) -> Node:
        peers = [peer for peer in self.node_ids if peer != node_id]
        return Node(node_id, peers, self.storage[node_id], self._timeouts[node_id])

    def _record(self, kind: str, **data: Any) -> None:
        self.trace.append({"step": len(self.trace) + 1, "time": self.now, "kind": kind, **data})

    def _enqueue(self, messages: list[Message]) -> list[str]:
        ids = []
        for message in messages:
            message_id = self.network.send(message)
            ids.append(message_id)
            self._record("send", message_id=message_id, source=message.source, target=message.target, message_kind=message.kind.value, term=message.term)
        return ids

    def tick(self, node_id: str) -> None:
        self.now += 1
        if node_id not in self.running:
            self._record("tick_ignored", node=node_id)
            return
        outgoing = self.nodes[node_id].tick(self.now)
        self._record("tick", node=node_id)
        self._enqueue(outgoing)

    def tick_all(self) -> None:
        for node_id in self.node_ids:
            self.tick(node_id)

    def deliver_next(self) -> bool:
        item = self.network.pop_next()
        if item is None:
            return False
        disposition, message = item
        self.now = max(self.now, self.network.now)
        if disposition != "DELIVER":
            self._record(disposition.lower(), message_id=message.message_id, source=message.source, target=message.target)
            return True
        if message.target not in self.running:
            self._record("target_down", message_id=message.message_id, target=message.target)
            return True
        outgoing = self.nodes[message.target].receive(message, self.now)
        self._record("deliver", message_id=message.message_id, source=message.source, target=message.target, message_kind=message.kind.value, term=message.term)
        self._enqueue(outgoing)
        return True

    def deliver_all(self, limit: int = 10_000) -> None:
        delivered = 0
        while self.deliver_next():
            delivered += 1
            if delivered > limit:
                raise RuntimeError("delivery limit exceeded; possible message loop")

    def crash(self, node_id: str) -> None:
        self.running.discard(node_id)
        self.nodes.pop(node_id, None)
        self._record("crash", node=node_id)

    def restart(self, node_id: str) -> None:
        if node_id in self.running:
            raise ValueError(f"node already running: {node_id}")
        self.nodes[node_id] = self._new_node(node_id)
        self.running.add(node_id)
        self._record("restart", node=node_id)

    def submit(self, node_id: str, request: ClientRequest) -> ClientResponse | None:
        if node_id not in self.running:
            raise ValueError(f"node not running: {node_id}")
        outgoing, response = self.nodes[node_id].submit(request, self.now)
        self._record("client_submit", node=node_id, client_id=request.client_id, sequence=request.sequence)
        self._enqueue(outgoing)
        return response

    def leaders(self) -> list[str]:
        return [
            node_id
            for node_id, node in self.nodes.items()
            if node_id in self.running and node.role is Role.LEADER
        ]

    def summaries(self) -> dict[str, dict[str, Any]]:
        return {
            node_id: node.state_summary()
            for node_id, node in self.nodes.items()
            if node_id in self.running
        }
