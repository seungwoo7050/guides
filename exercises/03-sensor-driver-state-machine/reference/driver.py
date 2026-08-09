#!/usr/bin/env python3
"""Reference implementation for the sensor-driver state-machine exercise."""

from __future__ import annotations

from typing import Any

from lab_support import (
    COMMAND_RESET,
    COMMAND_START,
    EXPECTED_IDENTITY,
    REG_COMMAND,
    REG_CONFIG,
    REG_ID,
    REG_SAMPLE,
    REG_STATUS,
    REG_THRESHOLD,
    STATUS_DATA_READY,
    DeviceBusy,
    DmaBuffer,
    FakeSensorBus,
    TransportError,
)


class SensorDriver:
    """Own one operation generation and preserve terminal results."""

    def __init__(self, bus: FakeSensorBus, *, use_dma: bool = False) -> None:
        self.bus = bus
        self.use_dma = use_dma
        self.state = "UNBOUND"
        self.generation = 0
        self.active_generation: int | None = None
        self.deadline: int | None = None
        self.results: dict[int, dict[str, Any]] = {}
        self.evidence: list[dict[str, Any]] = []
        self._dma_buffers: dict[int, DmaBuffer] = {}

    def initialize(self, config: dict[str, int], *, now: int = 0) -> dict[str, Any]:
        if self.state not in {"UNBOUND", "FAULT"}:
            return {"status": "REJECTED", "reason": "invalid_state", "state": self.state}
        self.state = "RESETTING"
        try:
            self.bus.write(REG_COMMAND, COMMAND_RESET, now=now)
            ready_at = self.bus.wait_until_ready(now=now, deadline=now + int(config["reset_timeout"]))
            self.state = "PROBING"
            identity = self.bus.read(REG_ID, now=ready_at)
            if identity != EXPECTED_IDENTITY:
                self.state = "FAULT"
                return {"status": "ERROR", "class": "identity", "raw": identity}
            self.state = "CONFIGURING"
            self.bus.write(REG_CONFIG, int(config["mode"]), now=ready_at)
            self.bus.write(REG_THRESHOLD, int(config["threshold"]), now=ready_at)
        except TimeoutError:
            self.state = "FAULT"
            return {"status": "ERROR", "class": "operation", "raw": "RESET_TIMEOUT"}
        except TransportError as error:
            # A partially programmed device has unknown configuration.  Do not
            # pretend that the previous configuration was restored.
            self.state = "FAULT"
            return {"status": "ERROR", "class": "transport", "raw": error.code, "configuration": "UNKNOWN"}
        except (DeviceBusy, KeyError, ValueError) as error:
            self.state = "FAULT"
            return {"status": "ERROR", "class": "configuration", "raw": str(error)}
        self.state = "IDLE"
        return {"status": "READY", "identity": identity, "at": ready_at}

    def start_sample(self, *, now: int, deadline: int) -> int:
        if self.state != "IDLE":
            raise RuntimeError(f"start_sample is not allowed in {self.state}")
        if deadline < now:
            raise ValueError("deadline is before request acceptance")
        self.generation += 1
        self.active_generation = self.generation
        self.deadline = deadline
        self.bus.write(REG_COMMAND, COMMAND_START, now=now)
        self.state = "CONVERTING"
        self.evidence.append({"event": "START", "generation": self.generation, "at": now, "deadline": deadline})
        return self.generation

    def poll(self, *, now: int) -> str:
        if self.active_generation is None or self.state not in {"CONVERTING", "DMA_PENDING"}:
            return "IDLE"
        # Completion exactly at the deadline is accepted; expiry begins after it.
        if self.deadline is not None and now > self.deadline:
            generation = self.active_generation
            self.results[generation] = {"status": "TIMEOUT", "at": now}
            self.evidence.append({"event": "TIMEOUT", "generation": generation, "at": now})
            self.active_generation = None
            self.deadline = None
            self.state = "IDLE"
            return "TIMEOUT"
        return self.state

    def on_data_ready(self, generation: int, *, now: int) -> str:
        status = self.bus.read(REG_STATUS, now=now)
        if status & STATUS_DATA_READY:
            # STATUS is W1C.  A read-modify-write or write-zero acknowledge is a
            # different public behavior and leaves a duplicate interrupt pending.
            self.bus.write(REG_STATUS, STATUS_DATA_READY, now=now)
        else:
            self.evidence.append({"event": "SPURIOUS", "generation": generation, "at": now})
            return "SPURIOUS"

        if generation != self.active_generation or self.state != "CONVERTING":
            self.evidence.append({"event": "STALE", "generation": generation, "at": now})
            return "STALE"
        if self.deadline is not None and now > self.deadline:
            self.poll(now=now)
            return "STALE"

        if self.use_dma:
            buffer = DmaBuffer()
            buffer.prepare_for_device_write()
            self._dma_buffers[generation] = buffer
            self.bus.begin_dma_read(generation=generation, buffer=buffer, now=now)
            self.state = "DMA_PENDING"
            return "DMA_PENDING"

        sample = self.bus.read(REG_SAMPLE, now=now)
        self._complete(generation, sample=sample, now=now)
        return "COMPLETE"

    def on_dma_complete(self, generation: int, *, now: int) -> str:
        buffer = self._dma_buffers.get(generation)
        if buffer is None:
            return "SPURIOUS"
        completed = self.bus.complete_dma(generation=generation, now=now)
        payload = completed.acquire_from_device()
        # Reclaim ownership even for a timed-out/cancelled operation, but never
        # let that late payload complete a newer generation.
        if generation != self.active_generation or self.state != "DMA_PENDING":
            self.evidence.append({"event": "STALE_DMA", "generation": generation, "at": now})
            return "STALE"
        if self.deadline is not None and now > self.deadline:
            self.poll(now=now)
            return "STALE"
        self._complete(generation, sample=int.from_bytes(payload, "little"), now=now)
        return "COMPLETE"

    def _complete(self, generation: int, *, sample: int, now: int) -> None:
        self.results[generation] = {
            "status": "OK",
            "generation": generation,
            "sample": sample,
            "unit": "raw16",
            "timestamp": now,
            "valid": True,
        }
        self.evidence.append({"event": "COMPLETE", "generation": generation, "at": now})
        self.active_generation = None
        self.deadline = None
        self.state = "IDLE"

    def cancel(self, generation: int, *, now: int) -> str:
        if generation != self.active_generation:
            return "STALE"
        self.results[generation] = {"status": "CANCELLED", "at": now}
        self.evidence.append({"event": "CANCEL", "generation": generation, "at": now})
        self.active_generation = None
        self.deadline = None
        self.state = "IDLE"
        return "CANCELLED"

    def suspend(self, *, now: int) -> str:
        if self.active_generation is not None:
            self.cancel(self.active_generation, now=now)
        self.state = "SUSPENDED"
        return "SUSPENDED"

    def resume(self) -> str:
        if self.state != "SUSPENDED":
            return "REJECTED"
        # Register retention is not assumed.  Reinitialization is mandatory.
        self.state = "UNBOUND"
        return "REINITIALIZE"

    def result(self, generation: int) -> dict[str, Any] | None:
        return self.results.get(generation)

    def dma_buffer(self, generation: int) -> DmaBuffer | None:
        return self._dma_buffers.get(generation)

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "generation": self.generation,
            "active_generation": self.active_generation,
            "deadline": self.deadline,
            "results": self.results,
            "evidence": self.evidence,
        }
