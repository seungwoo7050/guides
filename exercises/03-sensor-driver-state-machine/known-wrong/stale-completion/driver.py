#!/usr/bin/env python3
"""Known wrong: an old interrupt is attributed to the current request."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REFERENCE = Path(__file__).resolve().parents[2] / "reference" / "driver.py"
SPEC = importlib.util.spec_from_file_location("exercise3_reference_for_wrong", REFERENCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load reference driver")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SensorDriver(MODULE.SensorDriver):
    def on_data_ready(self, generation, *, now):
        # BUG: the callback token is discarded, so a cancelled generation can
        # complete whatever request happens to be active now.
        current = self.active_generation if self.active_generation is not None else generation
        return super().on_data_ready(current, now=now)
