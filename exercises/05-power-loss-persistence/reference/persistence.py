#!/usr/bin/env python3
"""Reference two-slot NOR-flash persistence model.

The model is intentionally small: erase and program progress one byte at a
time, while a record uses an exact multi-byte commit pattern written last.
It models power-cut recovery contracts, not a particular flash controller.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Iterable
from typing import Any


FLASH_SIZE = 256
SLOT_SIZE = FLASH_SIZE // 2
SLOT_NAMES = ("A", "B")
ERASED = 0xFF
FORMAT_VERSION = 1
MAGIC = b"CFG1"
HEADER = struct.Struct("<4sBBBH")
CHECKSUM = struct.Struct("<I")
MARKER_SIZE = 4
COMMIT_PATTERN = bytes((0x7F, 0x3F, 0x1F, 0x0F))
OBSOLETE_PATTERN = b"\x00" * MARKER_SIZE
COMMIT_OFFSET = SLOT_SIZE - (2 * MARKER_SIZE)
OBSOLETE_OFFSET = SLOT_SIZE - MARKER_SIZE
MAX_PAYLOAD = COMMIT_OFFSET - HEADER.size - CHECKSUM.size


class FlashViolation(ValueError):
    """Raised when a request violates the NOR geometry or 1-to-0 rule."""


class PowerLoss(RuntimeError):
    """Internal signal used to stop an operation at a byte boundary."""


class NorFlash:
    """Byte-array NOR flash with slot erase and 1-to-0 programming."""

    def __init__(self, image: bytes | bytearray | None = None) -> None:
        raw = bytes((ERASED,)) * FLASH_SIZE if image is None else bytes(image)
        if len(raw) != FLASH_SIZE:
            raise FlashViolation(f"flash image must be {FLASH_SIZE} bytes")
        self._bytes = bytearray(raw)

    def snapshot(self) -> bytes:
        return bytes(self._bytes)

    @staticmethod
    def _cut_limit(cut_after: int | None, length: int) -> int | None:
        if cut_after is None:
            return None
        if isinstance(cut_after, bool) or not isinstance(cut_after, int):
            raise FlashViolation("cut_after must be an integer byte count")
        if cut_after < 0 or cut_after > length:
            raise FlashViolation("cut_after is outside the operation")
        return cut_after

    @staticmethod
    def _range(offset: int, length: int) -> None:
        if (
            isinstance(offset, bool)
            or isinstance(length, bool)
            or not isinstance(offset, int)
            or not isinstance(length, int)
            or offset < 0
            or length < 0
            or offset + length > FLASH_SIZE
        ):
            raise FlashViolation("flash access is outside the device")

    def erase_slot(self, slot: str, cut_after: int | None = None) -> None:
        if slot not in SLOT_NAMES:
            raise FlashViolation("slot must be A or B")
        cut_after = self._cut_limit(cut_after, SLOT_SIZE)
        start = 0 if slot == "A" else SLOT_SIZE
        for index in range(SLOT_SIZE):
            if cut_after == index:
                raise PowerLoss(f"erase {slot} cut after {index} bytes")
            self._bytes[start + index] = ERASED
        if cut_after == SLOT_SIZE:
            raise PowerLoss(f"erase {slot} cut after completion")

    def program(self, offset: int, data: bytes, cut_after: int | None = None) -> None:
        payload = bytes(data)
        self._range(offset, len(payload))
        cut_after = self._cut_limit(cut_after, len(payload))

        # Validate the complete request before changing the array. A controller
        # rejects an impossible 0-to-1 request; this is not a power-cut case.
        for index, value in enumerate(payload):
            previous = self._bytes[offset + index]
            if (previous | value) != previous:
                raise FlashViolation(
                    f"program requires 0-to-1 transition at offset {offset + index}"
                )

        for index, value in enumerate(payload):
            if cut_after == index:
                raise PowerLoss(f"program cut after {index} bytes")
            self._bytes[offset + index] &= value
        if cut_after == len(payload):
            raise PowerLoss("program cut after completion")


def _slot_start(slot: str) -> int:
    if slot not in SLOT_NAMES:
        raise ValueError("slot must be A or B")
    return 0 if slot == "A" else SLOT_SIZE


def _validate_record_input(payload: bytes, sequence: int, schema: int) -> bytes:
    value = bytes(payload)
    if len(value) > MAX_PAYLOAD:
        raise ValueError(f"payload exceeds {MAX_PAYLOAD} bytes")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or not 0 <= sequence <= 0xFF:
        raise ValueError("sequence must be an unsigned 8-bit integer")
    if isinstance(schema, bool) or not isinstance(schema, int) or not 0 <= schema <= 0xFF:
        raise ValueError("schema must be an unsigned 8-bit integer")
    return value


def _record_body(payload: bytes, sequence: int, schema: int) -> bytes:
    value = _validate_record_input(payload, sequence, schema)
    header = HEADER.pack(MAGIC, FORMAT_VERSION, schema, sequence, len(value))
    checksum = CHECKSUM.pack(zlib.crc32(header + value) & 0xFFFFFFFF)
    return header + value + checksum


def _classify_slot(
    image: bytes,
    slot: str,
    supported_schemas: Iterable[int],
) -> dict[str, Any]:
    start = _slot_start(slot)
    raw = image[start : start + SLOT_SIZE]
    if raw == bytes((ERASED,)) * SLOT_SIZE:
        return {"status": "erased"}

    commit = raw[COMMIT_OFFSET : COMMIT_OFFSET + MARKER_SIZE]
    obsolete = raw[OBSOLETE_OFFSET : OBSOLETE_OFFSET + MARKER_SIZE]
    if commit != COMMIT_PATTERN:
        return {"status": "incomplete"}
    if obsolete != bytes((ERASED,)) * MARKER_SIZE:
        return {"status": "obsolete"}

    try:
        magic, format_version, schema, sequence, length = HEADER.unpack_from(raw)
    except struct.error:
        return {"status": "structurally-invalid"}
    if magic != MAGIC or format_version != FORMAT_VERSION or length > MAX_PAYLOAD:
        return {"status": "structurally-invalid"}

    payload_end = HEADER.size + length
    checksum_end = payload_end + CHECKSUM.size
    if checksum_end > COMMIT_OFFSET:
        return {"status": "structurally-invalid"}
    payload = raw[HEADER.size:payload_end]
    try:
        (stored_checksum,) = CHECKSUM.unpack(raw[payload_end:checksum_end])
    except struct.error:
        return {"status": "structurally-invalid"}
    calculated = zlib.crc32(raw[:HEADER.size] + payload) & 0xFFFFFFFF
    if stored_checksum != calculated:
        return {"status": "checksum-invalid"}
    if schema not in set(supported_schemas):
        return {
            "status": "unsupported-schema",
            "schema": schema,
            "sequence": sequence,
        }
    return {
        "status": "valid",
        "schema": schema,
        "sequence": sequence,
        "payload": bytes(payload),
    }


def _newer(left: int, right: int) -> bool:
    """Return whether left follows right in the unambiguous half range."""

    distance = (left - right) & 0xFF
    return 0 < distance < 0x80


def recover(image: bytes, supported_schemas: Iterable[int] = (1,)) -> dict[str, Any]:
    raw = bytes(image)
    if len(raw) != FLASH_SIZE:
        raise ValueError(f"flash image must be {FLASH_SIZE} bytes")
    schemas = tuple(supported_schemas)
    if not schemas or any(
        isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFF
        for value in schemas
    ):
        raise ValueError("supported_schemas must contain unsigned byte values")

    slots = {
        slot: _classify_slot(raw, slot, schemas)
        for slot in SLOT_NAMES
    }
    valid = [slot for slot in SLOT_NAMES if slots[slot]["status"] == "valid"]
    if not valid:
        return {
            "status": "recovery",
            "selected_slot": None,
            "payload": None,
            "sequence": None,
            "schema": None,
            "slots": slots,
        }

    selected = valid[0]
    if len(valid) == 2:
        left, right = valid
        left_sequence = slots[left]["sequence"]
        right_sequence = slots[right]["sequence"]
        if _newer(right_sequence, left_sequence):
            selected = right
        elif _newer(left_sequence, right_sequence):
            selected = left
        else:
            # Equal or exactly half-range-apart values are ambiguous. Slot A is
            # the documented deterministic tie breaker.
            selected = "A"
    record = slots[selected]
    return {
        "status": "ok",
        "selected_slot": selected,
        "payload": record["payload"],
        "sequence": record["sequence"],
        "schema": record["schema"],
        "slots": slots,
    }


def seed_image(
    payload: bytes,
    sequence: int,
    schema: int = 1,
    *,
    active_slot: str = "A",
    stale_inactive: bool = True,
) -> bytes:
    """Create one committed record and optionally dirty the inactive slot."""

    body = _record_body(payload, sequence, schema)
    fill = 0x00 if stale_inactive else ERASED
    image = bytearray(bytes((fill,)) * FLASH_SIZE)
    flash = NorFlash(image)
    flash.erase_slot(active_slot)
    start = _slot_start(active_slot)
    flash.program(start, body)
    flash.program(start + COMMIT_OFFSET, COMMIT_PATTERN)
    return flash.snapshot()


def operation_lengths(payload: bytes, sequence: int, schema: int = 1) -> dict[str, int]:
    body = _record_body(payload, sequence, schema)
    return {
        "erase-inactive": SLOT_SIZE,
        "program-body": len(body),
        "program-commit": MARKER_SIZE,
        "obsolete-old": MARKER_SIZE,
    }


def cut_points(payload: bytes, sequence: int, schema: int = 1) -> list[dict[str, int | str]]:
    """List every byte boundary, including before and after each operation."""

    return [
        {"operation": operation, "after": after}
        for operation, length in operation_lengths(payload, sequence, schema).items()
        for after in range(length + 1)
    ]


def apply_update(
    image: bytes,
    payload: bytes,
    sequence: int,
    schema: int = 1,
    *,
    cut: dict[str, Any] | None = None,
    supported_schemas: Iterable[int] = (1,),
) -> bytes:
    """Update the inactive slot and return bytes present after an optional cut."""

    schemas = tuple(supported_schemas)
    if schema not in schemas:
        raise ValueError("writer cannot commit an unsupported schema")
    body = _record_body(payload, sequence, schema)
    recovered = recover(image, schemas)
    if recovered["status"] != "ok":
        raise ValueError("an active committed record is required")
    active = recovered["selected_slot"]
    inactive = "B" if active == "A" else "A"

    cut_operation: str | None = None
    cut_after: int | None = None
    if cut is not None:
        if not isinstance(cut, dict):
            raise ValueError("cut must be an object")
        cut_operation = cut.get("operation")
        cut_after = cut.get("after")
        lengths = operation_lengths(payload, sequence, schema)
        if cut_operation not in lengths:
            raise ValueError("unknown cut operation")
        if (
            isinstance(cut_after, bool)
            or not isinstance(cut_after, int)
            or not 0 <= cut_after <= lengths[cut_operation]
        ):
            raise ValueError("cut byte boundary is outside the operation")

    flash = NorFlash(image)

    def requested(name: str) -> int | None:
        return cut_after if cut_operation == name else None

    try:
        flash.erase_slot(inactive, requested("erase-inactive"))
        inactive_start = _slot_start(inactive)
        flash.program(inactive_start, body, requested("program-body"))
        if flash.snapshot()[inactive_start : inactive_start + len(body)] != body:
            raise FlashViolation("read-back verification failed")
        flash.program(
            inactive_start + COMMIT_OFFSET,
            COMMIT_PATTERN,
            requested("program-commit"),
        )
        flash.program(
            _slot_start(active) + OBSOLETE_OFFSET,
            OBSOLETE_PATTERN,
            requested("obsolete-old"),
        )
    except PowerLoss:
        pass
    return flash.snapshot()
