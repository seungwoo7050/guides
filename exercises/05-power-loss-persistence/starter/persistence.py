#!/usr/bin/env python3
"""Starter for the two-slot NOR persistence exercise."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


FLASH_SIZE = 256
SLOT_SIZE = 128
ERASED = 0xFF
COMMIT_PATTERN = bytes((0x7F, 0x3F, 0x1F, 0x0F))


class FlashViolation(ValueError):
    pass


class PowerLoss(RuntimeError):
    pass


class NorFlash:
    """The physical byte rules are provided; implement record recovery below."""

    def __init__(self, image: bytes | bytearray | None = None) -> None:
        raw = bytes((ERASED,)) * FLASH_SIZE if image is None else bytes(image)
        if len(raw) != FLASH_SIZE:
            raise FlashViolation("wrong flash size")
        self._bytes = bytearray(raw)

    def snapshot(self) -> bytes:
        return bytes(self._bytes)

    def erase_slot(self, slot: str, cut_after: int | None = None) -> None:
        if slot not in ("A", "B"):
            raise FlashViolation("slot must be A or B")
        if cut_after is not None and not 0 <= cut_after <= SLOT_SIZE:
            raise FlashViolation("invalid cut")
        start = 0 if slot == "A" else SLOT_SIZE
        for index in range(SLOT_SIZE):
            if cut_after == index:
                raise PowerLoss("erase cut")
            self._bytes[start + index] = ERASED
        if cut_after == SLOT_SIZE:
            raise PowerLoss("erase cut after completion")

    def program(self, offset: int, data: bytes, cut_after: int | None = None) -> None:
        raw = bytes(data)
        if offset < 0 or offset + len(raw) > FLASH_SIZE:
            raise FlashViolation("program outside flash")
        if cut_after is not None and not 0 <= cut_after <= len(raw):
            raise FlashViolation("invalid cut")
        for index, value in enumerate(raw):
            previous = self._bytes[offset + index]
            if (previous | value) != previous:
                raise FlashViolation("NOR programming only clears bits")
        for index, value in enumerate(raw):
            if cut_after == index:
                raise PowerLoss("program cut")
            self._bytes[offset + index] &= value
        if cut_after == len(raw):
            raise PowerLoss("program cut after completion")


def recover(image: bytes, supported_schemas: Iterable[int] = (1,)) -> dict[str, Any]:
    """TODO: classify slots and select a committed record."""

    raise NotImplementedError("TODO: recover committed slots")


def seed_image(
    payload: bytes,
    sequence: int,
    schema: int = 1,
    *,
    active_slot: str = "A",
    stale_inactive: bool = True,
) -> bytes:
    """TODO: construct a valid starting image without bypassing NOR rules."""

    raise NotImplementedError("TODO: seed a committed record")


def operation_lengths(payload: bytes, sequence: int, schema: int = 1) -> dict[str, int]:
    raise NotImplementedError("TODO: expose physical operation lengths")


def cut_points(payload: bytes, sequence: int, schema: int = 1) -> list[dict[str, int | str]]:
    raise NotImplementedError("TODO: enumerate every byte boundary")


def apply_update(
    image: bytes,
    payload: bytes,
    sequence: int,
    schema: int = 1,
    *,
    cut: dict[str, Any] | None = None,
    supported_schemas: Iterable[int] = (1,),
) -> bytes:
    raise NotImplementedError("TODO: erase, write, verify, commit, obsolete")
