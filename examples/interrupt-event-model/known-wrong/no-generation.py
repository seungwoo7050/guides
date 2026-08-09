#!/usr/bin/env python3
"""Known wrong: accepts stale completion as a current event."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_path = Path(__file__).resolve().parents[1] / "reference" / "model.py"
_spec = importlib.util.spec_from_file_location("interrupt_wrong_generation_reference", _path)
assert _spec is not None and _spec.loader is not None
_reference = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _reference
_spec.loader.exec_module(_reference)


def run_fixture(data: dict[str, Any]):
    result, trace = _reference.run_fixture(data)
    if result.get("stale", 0):
        result["stale"] = 0
        result["handled_samples"] = [99]
    return result, trace
