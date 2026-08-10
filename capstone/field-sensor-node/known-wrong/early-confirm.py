#!/usr/bin/env python3
"""Known-wrong example: a trial becomes confirmed before durable health proof."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable


def _reference() -> Callable[..., Any]:
    path = Path(__file__).resolve().parents[1] / "reference" / "model.py"
    spec = importlib.util.spec_from_file_location("field_sensor_reference_confirm", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reference model at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_fixture


def run_fixture(fixture: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result, trace = _reference()(fixture)
    fixture_id = fixture["fixture_id"]
    if fixture_id == "S10":
        result.update(
            {
                "firmware_mode": "CONFIRMED",
                "current_image": "v3",
                "confirmed_image": "v3",
                "previous_image": None,
                "rollback_reason": None,
            }
        )
        result["evidence"].append("known-wrong:trial-confirmed-before-survival")
    elif fixture_id == "S11":
        result.update(
            {
                "firmware_mode": "CONFIRMED",
                "current_image": "v2",
                "confirmed_image": "v2",
                "rollback_reason": None,
            }
        )
        result["evidence"].append("known-wrong:torn-confirm-treated-as-success")
    return result, trace
