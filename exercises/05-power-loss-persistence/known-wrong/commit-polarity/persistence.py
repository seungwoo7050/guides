#!/usr/bin/env python3
"""Intentional mutant: erased commit bytes are interpreted as committed."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REFERENCE = Path(__file__).resolve().parents[2] / "reference" / "persistence.py"
spec = importlib.util.spec_from_file_location("persistence_wrong_polarity_base", REFERENCE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load reference model")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

# With this polarity, a fully written body becomes visible before the commit
# operation clears any bit. The checker must reject that early visibility.
base.COMMIT_PATTERN = b"\xff" * base.MARKER_SIZE

FlashViolation = base.FlashViolation
PowerLoss = base.PowerLoss
NorFlash = base.NorFlash
recover = base.recover
seed_image = base.seed_image
operation_lengths = base.operation_lengths
cut_points = base.cut_points
apply_update = base.apply_update
