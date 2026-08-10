#!/usr/bin/env python3
"""Known-wrong example: the ISR lets a burst exceed the queue bound."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable


def _reference() -> Callable[..., Any]:
    path = Path(__file__).resolve().parents[1] / "reference" / "model.py"
    spec = importlib.util.spec_from_file_location("field_sensor_reference_unbounded", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reference model at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_fixture


def run_fixture(fixture: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result, trace = _reference()(fixture)
    if fixture["fixture_id"] == "S03":
        result["event_depth"] = result["event_capacity"] + 1
        result["max_event_depth"] = result["event_capacity"] + 1
        result["event_dropped"] = 0
        trace[-1]["event_depth"] = result["event_depth"]
        result["evidence"].append("known-wrong:unbounded-ISR-queue")
    return result, trace
