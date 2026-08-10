#!/usr/bin/env python3
"""Known-wrong example: UNKNOWN upload outcome deletes the durable record."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable


def _reference() -> Callable[..., Any]:
    path = Path(__file__).resolve().parents[1] / "reference" / "model.py"
    spec = importlib.util.spec_from_file_location("field_sensor_reference_unknown", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reference model at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_fixture


def run_fixture(fixture: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result, trace = _reference()(fixture)
    if fixture["fixture_id"] == "S07":
        result["records"] = []
        result["record_ids"] = []
        result["record_states"] = []
        result["acked_ids"] = []
        result["upload_attempts"] = {"R1": 1}
        result["evidence"].append("known-wrong:delete-after-unknown-result")
    return result, trace
