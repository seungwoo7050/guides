#!/usr/bin/env python3
"""Public fake hardware used by the sensor-driver exercise.

The fake is deliberately stateful.  A transfer can succeed while the device is
still resetting, STATUS is a W1C MMIO register, and a DMA receive buffer must be
handed back to the CPU before it can be read.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


REG_ID = 0x00
REG_CONFIG = 0x01
REG_COMMAND = 0x02
REG_STATUS = 0x03
REG_SAMPLE = 0x04
REG_THRESHOLD = 0x05

COMMAND_RESET = 0xA5
COMMAND_START = 0x01
STATUS_DATA_READY = 0x01
STATUS_DEVICE_FAULT = 0x02
EXPECTED_IDENTITY = 0x42


class TransportError(RuntimeError):
    """A controller/bus failure, distinct from a device semantic failure."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class DeviceBusy(RuntimeError):
    """The bus worked, but the device is not ready for the requested operation."""


class OwnershipError(RuntimeError):
    """CPU/DMA buffer ownership or cache visibility was violated."""


@dataclass
class DmaBuffer:
    """A tiny cache-coherency model for a device-to-CPU DMA buffer."""

    size: int = 2
    owner: str = "CPU"
    _device_payload: bytes = b""
    _cpu_payload: bytes = b""
    cpu_visible: bool = True
    pre_dma_invalidations: int = 0
    post_dma_invalidations: int = 0
    history: list[str] = field(default_factory=list)

    def prepare_for_device_write(self) -> None:
        if self.owner != "CPU":
            raise OwnershipError("DMA buffer is not owned by the CPU")
        self.pre_dma_invalidations += 1
        self.cpu_visible = False
        self.owner = "DMA"
        self.history.append("CPU_INVALIDATE_AND_RELEASE")

    def dma_write(self, payload: bytes) -> None:
        if self.owner != "DMA":
            raise OwnershipError("device wrote a buffer not owned by DMA")
        if len(payload) != self.size:
            raise OwnershipError("DMA payload has the wrong size")
        self._device_payload = bytes(payload)
        self.history.append("DMA_WRITE")

    def acquire_from_device(self) -> bytes:
        if self.owner != "DMA":
            raise OwnershipError("CPU acquired a buffer not owned by DMA")
        self._cpu_payload = self._device_payload
        self.post_dma_invalidations += 1
        self.cpu_visible = True
        self.owner = "CPU"
        self.history.append("CPU_INVALIDATE_AND_ACQUIRE")
        return self._cpu_payload

    def cpu_read(self) -> bytes:
        if self.owner != "CPU" or not self.cpu_visible:
            raise OwnershipError("CPU read before DMA ownership/cache handoff")
        return self._cpu_payload


class FakeSensorBus:
    """Stateful I2C/SPI sensor and controller model.

    ``faults`` maps operation keys such as ``read:0`` or ``write:5`` to a list
    of transport errors.  Each operation consumes at most one scripted error.
    """

    def __init__(
        self,
        *,
        transport: str,
        identity: int = EXPECTED_IDENTITY,
        reset_delay: int = 2,
        faults: dict[str, list[str]] | None = None,
    ) -> None:
        if transport not in {"i2c", "spi"}:
            raise ValueError("transport must be i2c or spi")
        self.transport = transport
        self.identity = identity
        self.reset_delay = reset_delay
        self.faults = {key: list(value) for key, value in (faults or {}).items()}
        self.log: list[dict[str, Any]] = []
        self.reset_ready_at = 0
        self.configured = False
        self.registers = {
            REG_CONFIG: 0,
            REG_THRESHOLD: 0,
            REG_STATUS: 0,
            REG_SAMPLE: 0,
        }
        self.ready_generation: int | None = None
        self.pending_dma: tuple[int, DmaBuffer, int] | None = None

    def _fault(self, operation: str, register: int) -> None:
        key = f"{operation}:{register}"
        scripted = self.faults.get(key, [])
        if scripted:
            code = scripted.pop(0)
            self.log.append(
                {"transport": self.transport, "operation": operation, "register": register, "result": code}
            )
            raise TransportError(code)

    def write(self, register: int, value: int, *, now: int) -> None:
        self._fault("write", register)
        entry: dict[str, Any] = {
            "transport": self.transport,
            "operation": "write",
            "register": register,
            "value": value,
            "result": "OK",
        }
        if register == REG_STATUS:
            # Write-one-to-clear.  Writing zero must not acknowledge an event.
            self.registers[REG_STATUS] &= ~value
            entry["semantic"] = "W1C"
        elif register == REG_COMMAND and value == COMMAND_RESET:
            self.reset_ready_at = now + self.reset_delay
            self.configured = False
            self.registers[REG_STATUS] = 0
            self.ready_generation = None
        elif register == REG_COMMAND and value == COMMAND_START:
            if now < self.reset_ready_at or not self.configured:
                raise DeviceBusy("device is not configured and ready")
        else:
            self.registers[register] = value
            if register == REG_THRESHOLD:
                self.configured = True
        self.log.append(entry)

    def read(self, register: int, *, now: int) -> int:
        self._fault("read", register)
        if register == REG_ID:
            if now < self.reset_ready_at:
                raise DeviceBusy("identity read while reset is in progress")
            value = self.identity
        else:
            value = self.registers.get(register, 0)
        self.log.append(
            {
                "transport": self.transport,
                "operation": "read",
                "register": register,
                "value": value,
                "result": "OK",
            }
        )
        return value

    def wait_until_ready(self, *, now: int, deadline: int) -> int:
        """Advance virtual time only as far as the reset-ready boundary."""

        if self.reset_ready_at > deadline:
            self.log.append({"operation": "wait_ready", "result": "TIMEOUT", "deadline": deadline})
            raise TimeoutError("reset readiness deadline exceeded")
        ready_at = max(now, self.reset_ready_at)
        self.log.append({"operation": "wait_ready", "result": "READY", "at": ready_at})
        return ready_at

    def raise_data_ready(self, *, generation: int, sample: int) -> None:
        self.ready_generation = generation
        self.registers[REG_SAMPLE] = sample & 0xFFFF
        self.registers[REG_STATUS] |= STATUS_DATA_READY
        self.log.append({"operation": "hardware_event", "generation": generation, "sample": sample & 0xFFFF})

    def begin_dma_read(self, *, generation: int, buffer: DmaBuffer, now: int) -> None:
        # The ISR may already have acknowledged the W1C interrupt bit.  The
        # device's sample latch remains valid for the matching operation.
        if self.ready_generation != generation:
            raise DeviceBusy("DMA requested without a matching ready sample")
        if buffer.owner != "DMA":
            raise OwnershipError("driver did not release DMA buffer")
        self.pending_dma = (generation, buffer, self.registers[REG_SAMPLE])
        self.log.append({"operation": "dma_begin", "generation": generation, "at": now})

    def complete_dma(self, *, generation: int, now: int) -> DmaBuffer:
        if self.pending_dma is None:
            raise DeviceBusy("no DMA transfer is pending")
        pending_generation, buffer, sample = self.pending_dma
        if pending_generation != generation:
            raise DeviceBusy("DMA completion generation does not match pending transfer")
        buffer.dma_write(sample.to_bytes(2, "little"))
        self.pending_dma = None
        self.log.append({"operation": "dma_complete", "generation": generation, "at": now})
        return buffer
