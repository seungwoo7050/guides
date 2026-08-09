#!/usr/bin/env python3
"""Compatibility entry point for the interrupt event reference model."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REFERENCE = Path(__file__).resolve().parent / "reference" / "model.py"
SPEC = importlib.util.spec_from_file_location("interrupt_event_reference", REFERENCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load reference model: {REFERENCE}")
_reference = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = _reference
SPEC.loader.exec_module(_reference)

ModelError = _reference.ModelError
EventRecord = _reference.EventRecord
InterruptModel = _reference.InterruptModel
run_fixture = _reference.run_fixture
contains = _reference.contains
main = _reference.main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ModelError) as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
