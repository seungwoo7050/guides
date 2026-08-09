from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REFERENCE_PATH = Path(__file__).resolve().parents[2] / "reference/cloud_model.py"
SPEC = importlib.util.spec_from_file_location("cloud_model_reference_for_mutants", REFERENCE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load reference model: {REFERENCE_PATH}")
REFERENCE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = REFERENCE
SPEC.loader.exec_module(REFERENCE)


def expose(namespace: dict[str, object]) -> None:
    for name in (
        "CloudModelError",
        "AccessDenied",
        "QuotaExceeded",
        "TenantInactive",
        "EventConflict",
        "Event",
    ):
        namespace[name] = getattr(REFERENCE, name)
