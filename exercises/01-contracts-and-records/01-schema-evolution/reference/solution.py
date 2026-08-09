from __future__ import annotations

from typing import Any

Schema = dict[str, dict[str, Any]]
PROMOTIONS = {("int", "long"), ("int", "double"), ("long", "double"), ("float", "double")}


def reader_accepts(writer: Schema, reader: Schema) -> bool:
    for name, reader_field in reader.items():
        writer_field = writer.get(name)
        if writer_field is None:
            has_default = "default" in reader_field
            if reader_field.get("required", True) and not has_default:
                return False
            continue
        writer_type = writer_field["type"]
        reader_type = reader_field["type"]
        if writer_type != reader_type and (writer_type, reader_type) not in PROMOTIONS:
            return False
    return True
