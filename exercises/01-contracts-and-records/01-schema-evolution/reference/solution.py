from __future__ import annotations

from typing import Any

Schema = dict[str, dict[str, Any]]
PROMOTIONS = {("int", "long"), ("int", "double"), ("long", "double"), ("float", "double")}
SUPPORTED_TYPES = {"boolean", "int", "long", "float", "double", "string"}


def _validate(schema: Schema) -> None:
    if not isinstance(schema, dict):
        raise ValueError("schema must be an object")
    for name, field in schema.items():
        if not isinstance(name, str) or not name or not isinstance(field, dict):
            raise ValueError("schema fields require a non-empty name and object definition")
        if field.get("type") not in SUPPORTED_TYPES:
            raise ValueError(f"unsupported field type: {field.get('type')!r}")
        if "required" in field and not isinstance(field["required"], bool):
            raise ValueError("required must be boolean")


def reader_accepts(writer: Schema, reader: Schema) -> bool:
    _validate(writer)
    _validate(reader)
    for name, reader_field in reader.items():
        writer_field = writer.get(name)
        reader_required = reader_field.get("required", True)
        reader_has_default = "default" in reader_field
        if writer_field is None:
            if reader_required and not reader_has_default:
                return False
            continue
        if not writer_field.get("required", True) and reader_required and not reader_has_default:
            return False
        writer_type = writer_field["type"]
        reader_type = reader_field["type"]
        if writer_type != reader_type and (writer_type, reader_type) not in PROMOTIONS:
            return False
    return True
