#!/usr/bin/env python3
"""Reference submission: reuse the documented executable example model."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PATH = Path(__file__).resolve().parents[3] / "examples" / "update-state-model" / "model.py"
SPEC = importlib.util.spec_from_file_location("exercise6_reference_model", PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load update-state reference")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

ModelError = MODULE.ModelError
Image = MODULE.Image
UpdateModel = MODULE.UpdateModel
run_fixture = MODULE.run_fixture
