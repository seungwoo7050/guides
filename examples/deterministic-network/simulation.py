#!/usr/bin/env python3
"""A small deterministic message scheduler for protocol exercises."""
from __future__ import annotations

import argparse
import copy
import hashlib
import heapq
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(order=True)
class ScheduledMessage:
    deliver_at: int
    sequence: int
    message_id: str = field(compare=False)
    source: str = field(compare=False)
    target: str = field(compare=False)
    payload: dict[str, Any] = field(compare=False)
    dropped: bool = field(default=False, compare=False)


class DeterministicNetwork:
    def __init__(self, nodes: list[str]) -> None:
        self.now = 0
        self.nodes = {node: {"running": True, "inbox": []} for node in nodes}
        self._queue: list[ScheduledMessage] = []
        self._by_id: dict[str, ScheduledMessage] = {}
        self._sequence = 0
        self._message_sequence = 0
        self.trace: list[dict[str, Any]] = []

    def _record(self, kind: str, **details: Any) -> None:
        self.trace.append({"step": len(self.trace) + 1, "time": self.now, "kind": kind, **details})

    def send(self, source: str, target: str, payload: dict[str, Any], delay: int = 0) -> str:
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("source and target must be registered nodes")
        if delay < 0:
            raise ValueError("delay must be non-negative")
        self._sequence += 1
        self._message_sequence += 1
        message_id = f"m{self._message_sequence}"
        message = ScheduledMessage(
            deliver_at=self.now + delay,
            sequence=self._sequence,
            message_id=message_id,
            source=source,
            target=target,
            payload=copy.deepcopy(payload),
        )
        heapq.heappush(self._queue, message)
        self._by_id[message_id] = message
        self._record("send", message_id=message_id, source=source, target=target, deliver_at=message.deliver_at, payload=payload)
        return message_id

    def drop(self, message_id: str) -> None:
        message = self._by_id.get(message_id)
        if message is None:
            raise ValueError(f"unknown message: {message_id}")
        message.dropped = True
        self._record("drop", message_id=message_id)

    def duplicate(self, message_id: str, extra_delay: int = 0) -> str:
        original = self._by_id.get(message_id)
        if original is None:
            raise ValueError(f"unknown message: {message_id}")
        delay = max(0, original.deliver_at - self.now) + extra_delay
        duplicate_id = self.send(original.source, original.target, original.payload, delay)
        self._record("duplicate", original=message_id, duplicate=duplicate_id)
        return duplicate_id

    def crash(self, node: str) -> None:
        self.nodes[node]["running"] = False
        self._record("crash", node=node)

    def restart(self, node: str) -> None:
        self.nodes[node]["running"] = True
        self._record("restart", node=node)

    def deliver_next(self) -> bool:
        if not self._queue:
            return False
        message = heapq.heappop(self._queue)
        self.now = max(self.now, message.deliver_at)
        if message.dropped:
            self._record("discard_dropped", message_id=message.message_id)
            return True
        if not self.nodes[message.target]["running"]:
            self._record("discard_target_down", message_id=message.message_id, target=message.target)
            return True
        envelope = {
            "message_id": message.message_id,
            "source": message.source,
            "payload": copy.deepcopy(message.payload),
            "delivered_at": self.now,
        }
        self.nodes[message.target]["inbox"].append(envelope)
        self._record("deliver", message_id=message.message_id, source=message.source, target=message.target, payload=message.payload)
        return True

    def deliver_all(self) -> None:
        while self.deliver_next():
            pass

    def result(self) -> dict[str, Any]:
        state = {
            "time": self.now,
            "nodes": self.nodes,
            "trace": self.trace,
            "pending": [
                {
                    "message_id": m.message_id,
                    "deliver_at": m.deliver_at,
                    "source": m.source,
                    "target": m.target,
                    "payload": m.payload,
                    "dropped": m.dropped,
                }
                for m in sorted(self._queue)
            ],
        }
        canonical = json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        state["digest"] = hashlib.sha256(canonical).hexdigest()
        return state


def run_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
    network = DeterministicNetwork(list(schedule["nodes"]))
    aliases: dict[str, str] = {}
    for action in schedule["actions"]:
        kind = action["kind"]
        if kind == "send":
            message_id = network.send(action["from"], action["to"], action["payload"], int(action.get("delay", 0)))
            aliases[f"m{len(aliases) + 1}"] = message_id
        elif kind == "drop":
            network.drop(aliases.get(action["message_id"], action["message_id"]))
        elif kind == "duplicate":
            network.duplicate(aliases.get(action["message_id"], action["message_id"]), int(action.get("extra_delay", 0)))
        elif kind == "crash":
            network.crash(action["node"])
        elif kind == "restart":
            network.restart(action["node"])
        elif kind == "deliver_next":
            network.deliver_next()
        elif kind == "deliver_all":
            network.deliver_all()
        else:
            raise ValueError(f"unknown action: {kind}")
    return network.result()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("schedule", nargs="?", type=Path, default=Path(__file__).with_name("schedule.json"))
    args = parser.parse_args()
    schedule = json.loads(args.schedule.read_text(encoding="utf-8"))
    print(json.dumps(run_schedule(schedule), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
