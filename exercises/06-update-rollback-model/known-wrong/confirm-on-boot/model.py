#!/usr/bin/env python3
"""Known wrong: CONFIRM silently manufactures both health gates."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PATH = Path(__file__).resolve().parents[4] / "examples" / "update-state-model" / "model.py"
SPEC = importlib.util.spec_from_file_location("exercise6_wrong_base", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load update-state reference")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def run_fixture(data):
    model = MODULE.UpdateModel(
        max_trial_attempts=data.get("max_trial_attempts", 2),
        hardware_id=data.get("hardware_id", "board-v1"),
        data_schema=data.get("data_schema", 1),
    )
    for event in data.get("events", []):
        if event.get("op") == "CONFIRM":
            # BUG: reaching application code is mistaken for completed boot and
            # product self-test evidence.
            model.boot_ok = True
            model.self_test_pass = True
        model.apply(event)
    return model.result(), model.trace
