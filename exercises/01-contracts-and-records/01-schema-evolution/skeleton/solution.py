"""Implement reader_accepts without using a schema-registry library."""

from __future__ import annotations

from typing import Any

Schema = dict[str, dict[str, Any]]


def reader_accepts(writer: Schema, reader: Schema) -> bool:
    # TODO: compare missing required fields and supported type promotions.
    return True
