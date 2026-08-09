"""Explicit deterministic message scheduling for the capstone."""
from __future__ import annotations

import copy
import heapq
from dataclasses import asdict, dataclass, field, replace

from .types import Message


@dataclass(order=True)
class Envelope:
    deliver_at: int
    sequence: int
    delivery_id: str = field(compare=False)
    message: Message = field(compare=False)
    dropped: bool = field(default=False, compare=False)


class DeterministicNetwork:
    """A single-clock network where every queued delivery is addressable."""

    def __init__(self, nodes: list[str]) -> None:
        self.nodes = set(nodes)
        self.now = 0
        self._sequence = 0
        self._message_sequence = 0
        self._delivery_sequence = 0
        self._queue: list[Envelope] = []
        self._by_delivery: dict[str, Envelope] = {}
        self._blocked: set[tuple[str, str]] = set()

    def advance(self, ticks: int = 1) -> int:
        if ticks < 0:
            raise ValueError("ticks must be non-negative")
        self.now += ticks
        return self.now

    def send(self, message: Message, delay: int = 0) -> str:
        if message.source not in self.nodes or message.target not in self.nodes:
            raise ValueError("message endpoints must be cluster nodes")
        if delay < 0:
            raise ValueError("delay must be non-negative")
        self._sequence += 1
        self._delivery_sequence += 1
        logical_id = message.message_id
        if logical_id is None:
            self._message_sequence += 1
            logical_id = f"m{self._message_sequence}"
        delivery_id = f"d{self._delivery_sequence}"
        stored = replace(
            message,
            message_id=logical_id,
            payload=copy.deepcopy(message.payload),
        )
        envelope = Envelope(self.now + delay, self._sequence, delivery_id, stored)
        heapq.heappush(self._queue, envelope)
        self._by_delivery[delivery_id] = envelope
        return delivery_id

    def drop(self, delivery_id: str) -> None:
        self._require_pending(delivery_id).dropped = True

    def delay(self, delivery_id: str, extra_delay: int) -> None:
        if extra_delay < 0:
            raise ValueError("extra_delay must be non-negative")
        envelope = self._require_pending(delivery_id)
        envelope.deliver_at += extra_delay
        heapq.heapify(self._queue)

    def duplicate(self, delivery_id: str, extra_delay: int = 0) -> str:
        original = self._require_pending(delivery_id)
        remaining = max(0, original.deliver_at - self.now)
        return self.send(original.message, remaining + extra_delay)

    def partition(self, source: str, target: str, bidirectional: bool = False) -> None:
        self._blocked.add((source, target))
        if bidirectional:
            self._blocked.add((target, source))

    def heal(self, source: str | None = None, target: str | None = None) -> None:
        if source is None and target is None:
            self._blocked.clear()
            return
        if source is None or target is None:
            raise ValueError("heal requires both source and target, or neither")
        self._blocked.discard((source, target))

    def pop(self, delivery_id: str | None = None) -> tuple[str, str, Message] | None:
        envelope = self._take(delivery_id)
        if envelope is None:
            return None
        self.now = max(self.now, envelope.deliver_at)
        message = envelope.message
        if envelope.dropped:
            return "DROPPED", envelope.delivery_id, copy.deepcopy(message)
        if (message.source, message.target) in self._blocked:
            # A delivery attempted during a partition is consumed. To model an old
            # packet arriving after heal, delay a distinct delivery beforehand.
            return "PARTITION_DROPPED", envelope.delivery_id, copy.deepcopy(message)
        return "DELIVER", envelope.delivery_id, copy.deepcopy(message)

    def pop_next(self) -> tuple[str, Message] | None:
        """Compatibility wrapper for the original starter API."""
        item = self.pop()
        if item is None:
            return None
        disposition, _delivery_id, message = item
        return disposition, message

    def pending(self) -> list[tuple[str, Message]]:
        return [
            (envelope.delivery_id, copy.deepcopy(envelope.message))
            for envelope in sorted(self._queue)
        ]

    def state_snapshot(self) -> dict[str, object]:
        """Return every scheduler field that can change a future execution."""
        return {
            "virtual_time": self.now,
            "blocked_links": [list(link) for link in sorted(self._blocked)],
            "pending": [
                {
                    "deliver_at": envelope.deliver_at,
                    "enqueue_sequence": envelope.sequence,
                    "delivery_id": envelope.delivery_id,
                    "dropped": envelope.dropped,
                    "message": asdict(envelope.message),
                }
                for envelope in sorted(self._queue)
            ],
            "next_message_sequence": self._message_sequence + 1,
            "next_delivery_sequence": self._delivery_sequence + 1,
        }

    def _require_pending(self, delivery_id: str) -> Envelope:
        try:
            return self._by_delivery[delivery_id]
        except KeyError as exc:
            raise KeyError(f"unknown or consumed delivery: {delivery_id}") from exc

    def _take(self, delivery_id: str | None) -> Envelope | None:
        if not self._queue:
            return None
        if delivery_id is None:
            envelope = heapq.heappop(self._queue)
        else:
            envelope = self._require_pending(delivery_id)
            self._queue.remove(envelope)
            heapq.heapify(self._queue)
        self._by_delivery.pop(envelope.delivery_id, None)
        return envelope
