from __future__ import annotations


def apply_setting(store: dict[str, str], name: str, value: str) -> str:
    store[name] = value
    return f"applied {name}={value}"
