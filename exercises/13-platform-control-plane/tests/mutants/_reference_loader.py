"""Load and export the reference implementation for one-defect mutants."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def export_reference(namespace: dict[str, Any]) -> Any:
    path = Path(__file__).resolve().parents[2] / "reference/platform_model.py"
    name = f"platform_reference_{Path(namespace.get('__file__', 'mutant')).stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load platform reference")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    for public in (
        "request_environment",
        "reconcile",
        "observe_drift",
        "request_migration",
        "retire_service",
        "snapshot",
    ):
        namespace[public] = getattr(module, public)
    return module
