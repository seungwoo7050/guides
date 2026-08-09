from __future__ import annotations


def reader_accepts(writer: dict, reader: dict) -> bool:
    promotions = {("int", "long"), ("int", "double"), ("long", "double"), ("float", "double")}
    for name, reader_field in reader.items():
        writer_field = writer.get(name)
        if writer_field is None:
            if reader_field.get("required", True) and "default" not in reader_field:
                return False
            continue
        if writer_field["type"] != reader_field["type"] and (
            writer_field["type"], reader_field["type"]
        ) not in promotions:
            return False
    return True
