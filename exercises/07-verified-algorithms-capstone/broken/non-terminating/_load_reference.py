from __future__ import annotations

from pathlib import Path


def load_reference(namespace: dict[str, object]) -> None:
    source = Path(__file__).resolve().parents[2] / "reference" / "algorithms.py"
    exec(compile(source.read_text(encoding="utf-8"), str(source), "exec"), namespace)
