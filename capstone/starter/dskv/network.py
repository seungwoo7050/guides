"""Explicit deterministic message scheduling for the capstone."""
from __future__ import annotations

import copy
import heapq
from dataclasses import dataclass, field, replace

from .types import Message


@dataclass(order=True)
class Envelope:
    deliver_at: int
    sequence: int
    message: Message = field(compare=False)
    dropped: bool = field(default=False, compare=False)


class DeterministicNetwork:
    def __init__(self, nodes: list[str]) -> None:
        self.nodes = set(nodes)
        self.now = 0
        self._sequence = 0
        self._message_sequence = 0
        self._queue: list[Envelope] = []
        self._by_id: dict[str, Envelope] = {}
        self._blocked: set[tuple[str, str]] = set()

    def send(self, message: Message, delay: int = 0) -> str:
        if message.source not in self.nodes or message.target not in self.nodes:
            raise ValueError("message endpoints must be cluster nodes")
        if delay < 0:
            raise ValueError("delay must be non-negative")
        self._sequence += 1
        self._message_sequence += 1
        message_id = message.message_id or f"m{self._message_sequence}"
        if message_id in self._by_id:
            raise ValueError(f"duplicate message id: {message_id}")
        stored = replace(message, message_id=message_id, payload=copy.deepcopy(message.payload))
        envelope = Envelope(self.now + delay, self._sequence, stored)
        heapq.heappush(self._queue, envelope)
        self._by_id[message_id] = envelope
        return message_id

    def drop(self, message_id: str) -> None:
        self._by_id[message_id].dropped = True

    def duplicate(self, message_id: str, extra_delay: int = 0) -> str:
        original = self._by_id[message_id]
        delay = max(0, original.deliver_at - self.now) + extra_delay
        return self.send(replace(original.message, message_id=None), delay)

    def partition(self, source: str, target: str, bidirectional: bool = False) -> None:
        self._blocked.add((source, target))
        if bidirectional:
            self._blocked.add((target, source))

    def heal(self, source: str | None = None, target: str | None = None) -> None:
        if source is None and target is None:
            self._blocked.clear()
            return
        self._blocked.discard((source, target))

    def pop_next(self) -> tuple[str, Message] | None:
        while self._queue:
            envelope = heapq.heappop(self._queue)
            self.now = max(self.now, envelope.deliver_at)
            message = envelope.message
            if envelope.dropped:
                return "DROPPED", message
            if (message.source, message.target) in self._blocked:
                return "BLOCKED", message
            return "DELIVER", copy.deepcopy(message)
        return None

    def pending(self) -> list[Message]:
        return [copy.deepcopy(envelope.message) for envelope in sorted(self._queue)]
