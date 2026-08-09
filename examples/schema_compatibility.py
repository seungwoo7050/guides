#!/usr/bin/env python3
"""A deliberately small reader/writer schema compatibility model.

This is not an Avro/Protobuf/JSON Schema implementation.  It makes the
questions visible: which reader reads which writer, and what defaults or type
promotions are required?  Real systems must use the selected format's official
compatibility implementation as well.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PROMOTIONS = {
    ("int", "long"),
    ("int", "double"),
    ("long", "double"),
    ("float", "double"),
}


@dataclass(frozen=True)
class Field:
    name: str
    type: str
    required: bool = True
    default: Any = None
    has_default: bool = False


@dataclass(frozen=True)
class Compatibility:
    backward: bool
    forward: bool
    backward_reasons: tuple[str, ...]
    forward_reasons: tuple[str, ...]

    @property
    def full(self) -> bool:
        return self.backward and self.forward


def _reader_accepts(writer: dict[str, Field], reader: dict[str, Field]) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    for name, reader_field in reader.items():
        writer_field = writer.get(name)
        if writer_field is None:
            if reader_field.required and not reader_field.has_default:
                reasons.append(f"reader requires missing field: {name}")
            continue
        if writer_field.type == reader_field.type:
            continue
        if (writer_field.type, reader_field.type) not in PROMOTIONS:
            reasons.append(
                f"reader type {reader_field.type} cannot read writer type "
                f"{writer_field.type} for {name}"
            )
    return not reasons, tuple(reasons)


def compare(old: list[Field], new: list[Field]) -> Compatibility:
    old_by_name = {field.name: field for field in old}
    new_by_name = {field.name: field for field in new}

    # New reader reads old data.
    backward, backward_reasons = _reader_accepts(old_by_name, new_by_name)
    # Old reader reads new data.
    forward, forward_reasons = _reader_accepts(new_by_name, old_by_name)
    return Compatibility(backward, forward, backward_reasons, forward_reasons)


def demo() -> None:
    old = [Field("order_id", "string"), Field("amount", "int")]
    new = [
        Field("order_id", "string"),
        Field("amount", "long"),
        Field("channel", "string", required=False, default=None, has_default=True),
    ]
    result = compare(old, new)
    print({"backward": result.backward, "forward": result.forward, "full": result.full})


if __name__ == "__main__":
    demo()
