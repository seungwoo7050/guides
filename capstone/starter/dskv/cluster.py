"""Deterministic cluster harness shared by learner tests."""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any

from .network import DeterministicNetwork
from .node import Node
from .storage import MemoryStorage
from .types import (
    ClientRequest,
    ClientResponse,
    Command,
    Message,
    Role,
    Snapshot,
    canonical_fingerprint,
)


class Cluster:
    def __init__(
        self,
        node_ids: list[str],
        election_timeouts: dict[str, int] | None = None,
        *,
        run_id: str = "learner-run",
    ) -> None:
        if len(node_ids) < 3:
            raise ValueError("capstone core requires at least three nodes")
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("node ids must be unique")
        if not run_id:
            raise ValueError("run_id must be non-empty")
        self.run_id = run_id
        self.node_ids = tuple(node_ids)
        self.storage = {node_id: MemoryStorage() for node_id in node_ids}
        election_timeouts = election_timeouts or {
            node_id: index + 3 for index, node_id in enumerate(node_ids)
        }
        if set(election_timeouts) != set(node_ids):
            raise ValueError("election timeouts must cover every node exactly")
        self._timeouts = dict(election_timeouts)
        self.nodes = {node_id: self._new_node(node_id) for node_id in node_ids}
        self.running = set(node_ids)
        self.network = DeterministicNetwork(node_ids)
        self.trace: list[dict[str, Any]] = []

    @property
    def now(self) -> int:
        return self.network.now

    def _new_node(self, node_id: str) -> Node:
        peers = [peer for peer in self.node_ids if peer != node_id]
        return Node(node_id, peers, self.storage[node_id], self._timeouts[node_id])

    def _state_hash(self) -> str:
        payload = json.dumps(
            self.state_snapshot(), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _record(
        self,
        kind: str,
        *,
        actor: str | None = None,
        target: str | None = None,
        message_id: str | None = None,
        delivery_id: str | None = None,
        state_before_hash: str | None = None,
        **details: Any,
    ) -> None:
        state_after_hash = self._state_hash()
        self.trace.append({
            "schema_version": 1,
            "run_id": self.run_id,
            "step": len(self.trace) + 1,
            "virtual_time": self.now,
            "event_id": f"e{len(self.trace) + 1}",
            "kind": kind,
            "actor": actor,
            "target": target,
            "message_id": message_id,
            "delivery_id": delivery_id,
            "state_before_hash": state_before_hash or state_after_hash,
            "state_after_hash": state_after_hash,
            "invariant_results": [],
            "details": details,
        })

    def _enqueue(self, messages: list[Message], delay: int = 0) -> list[str]:
        delivery_ids: list[str] = []
        for message in messages:
            before = self._state_hash()
            delivery_id = self.network.send(message, delay=delay)
            delivery_ids.append(delivery_id)
            logical_id = dict(self.network.pending())[delivery_id].message_id
            self._record(
                "send",
                actor=message.source,
                target=message.target,
                message_id=logical_id,
                delivery_id=delivery_id,
                state_before_hash=before,
                message_kind=message.kind.value,
                term=message.term,
            )
        return delivery_ids

    def tick(self, node_id: str) -> None:
        before = self._state_hash()
        self.network.advance(1)
        if node_id not in self.running:
            self._record("tick_ignored", actor=node_id, state_before_hash=before)
            return
        outgoing = self.nodes[node_id].tick(self.now)
        self._record("tick", actor=node_id, state_before_hash=before)
        self._enqueue(outgoing)

    def tick_all(self) -> None:
        for node_id in self.node_ids:
            self.tick(node_id)

    def deliver(self, delivery_id: str | None = None) -> bool:
        before = self._state_hash()
        item = self.network.pop(delivery_id)
        if item is None:
            return False
        disposition, actual_delivery_id, message = item
        if disposition != "DELIVER":
            self._record(
                disposition.lower(), actor=message.source, target=message.target,
                message_id=message.message_id, delivery_id=actual_delivery_id,
                state_before_hash=before,
            )
            return True
        if message.target not in self.running:
            self._record(
                "target_down", actor=message.source, target=message.target,
                message_id=message.message_id, delivery_id=actual_delivery_id,
                state_before_hash=before,
            )
            return True
        outgoing = self.nodes[message.target].receive(message, self.now)
        self._record(
            "deliver", actor=message.source, target=message.target,
            message_id=message.message_id, delivery_id=actual_delivery_id,
            state_before_hash=before, message_kind=message.kind.value, term=message.term,
        )
        self._enqueue(outgoing)
        return True

    def deliver_next(self) -> bool:
        return self.deliver()

    def deliver_all(self, limit: int = 10_000) -> None:
        delivered = 0
        while self.deliver():
            delivered += 1
            if delivered > limit:
                raise RuntimeError("delivery limit exceeded; possible message loop")

    def delay(self, delivery_id: str, extra_delay: int) -> None:
        before = self._state_hash()
        message = dict(self.network.pending())[delivery_id]
        self.network.delay(delivery_id, extra_delay)
        self._record(
            "delay", actor=message.source, target=message.target,
            message_id=message.message_id, delivery_id=delivery_id,
            state_before_hash=before, extra_delay=extra_delay,
        )

    def drop(self, delivery_id: str) -> None:
        before = self._state_hash()
        message = dict(self.network.pending())[delivery_id]
        self.network.drop(delivery_id)
        self._record(
            "drop", actor=message.source, target=message.target,
            message_id=message.message_id, delivery_id=delivery_id,
            state_before_hash=before,
        )

    def duplicate(self, delivery_id: str, extra_delay: int = 0) -> str:
        before = self._state_hash()
        original = dict(self.network.pending())[delivery_id]
        duplicate_id = self.network.duplicate(delivery_id, extra_delay)
        self._record(
            "duplicate", actor=original.source, target=original.target,
            message_id=original.message_id, delivery_id=duplicate_id,
            state_before_hash=before, source_delivery_id=delivery_id,
            extra_delay=extra_delay,
        )
        return duplicate_id

    def partition(self, source: str, target: str, bidirectional: bool = False) -> None:
        before = self._state_hash()
        self.network.partition(source, target, bidirectional)
        self._record(
            "partition", actor=source, target=target, state_before_hash=before,
            bidirectional=bidirectional, applied=True,
        )

    def heal(self, source: str | None = None, target: str | None = None) -> None:
        before = self._state_hash()
        self.network.heal(source, target)
        self._record(
            "heal", actor=source, target=target, state_before_hash=before,
            applied=True,
        )

    def crash(self, node_id: str) -> None:
        before = self._state_hash()
        if node_id not in self.running:
            raise ValueError(f"node not running: {node_id}")
        self.running.discard(node_id)
        self.nodes.pop(node_id, None)
        self._record("crash", actor=node_id, state_before_hash=before)

    def restart(self, node_id: str) -> None:
        before = self._state_hash()
        if node_id in self.running:
            raise ValueError(f"node already running: {node_id}")
        self.nodes[node_id] = self._new_node(node_id)
        self.running.add(node_id)
        self._record("restart", actor=node_id, state_before_hash=before)

    def submit(self, node_id: str, request: ClientRequest) -> ClientResponse | None:
        before = self._state_hash()
        if node_id not in self.running:
            raise ValueError(f"node not running: {node_id}")
        outgoing, response = self.nodes[node_id].submit(request, self.now)
        self._record(
            "client_submit", actor=request.client_id, target=node_id,
            state_before_hash=before, sequence=request.sequence,
            command=asdict(request.command),
            response=asdict(response) if response is not None else None,
        )
        self._enqueue(outgoing)
        return response

    def drain_responses(self) -> list[ClientResponse]:
        before = self._state_hash()
        responses: list[ClientResponse] = []
        for node in self.nodes.values():
            responses.extend(node.drain_responses())
        self._record(
            "drain_responses", state_before_hash=before,
            responses=[asdict(response) for response in responses],
        )
        return responses

    def create_snapshot(self, node_id: str, through_index: int) -> Snapshot:
        before = self._state_hash()
        if node_id not in self.running:
            raise ValueError(f"node not running: {node_id}")
        snapshot = self.nodes[node_id].create_snapshot(through_index)
        self._record(
            "create_snapshot", actor=node_id, state_before_hash=before,
            through_index=through_index, generation=snapshot.generation,
            checksum=snapshot.checksum,
        )
        return snapshot

    def leaders(self) -> list[str]:
        return [
            node_id for node_id, node in self.nodes.items()
            if node_id in self.running and node.role is Role.LEADER
        ]

    def state_snapshot(self) -> dict[str, Any]:
        return {
            "virtual_time": self.now,
            "running": sorted(self.running),
            "nodes": {
                node_id: self.nodes[node_id].state_summary()
                for node_id in sorted(self.nodes)
                if node_id in self.running
            },
            "durable": {
                node_id: asdict(self.storage[node_id].load())
                for node_id in sorted(self.storage)
            },
            "network": self.network.state_snapshot(),
        }

    def summaries(self) -> dict[str, dict[str, Any]]:
        return self.state_snapshot()["nodes"]

    def trace_document(self, scenario_id: str) -> dict[str, Any]:
        if not scenario_id:
            raise ValueError("scenario_id must be non-empty")
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "scenario_id": scenario_id,
            "events": list(self.trace),
        }

    def run_schedule(self, schedule: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for item in schedule:
            if not isinstance(item, dict):
                raise ValueError("every schedule action must be an object")
            kind = item.get("kind")
            if kind == "tick":
                for _ in range(int(item.get("repeat", 1))):
                    self.tick(item["node"])
            elif kind == "tick_all":
                for _ in range(int(item.get("repeat", 1))):
                    self.tick_all()
            elif kind == "deliver":
                self.deliver(item.get("delivery_id"))
            elif kind == "deliver_all":
                self.deliver_all(int(item.get("limit", 10_000)))
            elif kind == "crash":
                self.crash(item["node"])
            elif kind == "restart":
                self.restart(item["node"])
            elif kind == "drop":
                self.drop(item["delivery_id"])
            elif kind == "delay":
                self.delay(item["delivery_id"], int(item["ticks"]))
            elif kind == "duplicate":
                self.duplicate(item["delivery_id"], int(item.get("extra_delay", 0)))
            elif kind == "partition":
                self.partition(item["source"], item["target"], bool(item.get("bidirectional", False)))
            elif kind == "heal":
                self.heal(item.get("source"), item.get("target"))
            elif kind == "submit":
                command = Command(**item["command"])
                request = ClientRequest(
                    str(item["client_id"]), int(item["sequence"]),
                    str(item.get("fingerprint") or canonical_fingerprint(command)), command,
                )
                self.submit(item["node"], request)
            elif kind == "drain_responses":
                self.drain_responses()
            elif kind == "create_snapshot":
                self.create_snapshot(item["node"], int(item["through_index"]))
            else:
                raise ValueError(f"unsupported schedule action: {kind}")
        return list(self.trace)
