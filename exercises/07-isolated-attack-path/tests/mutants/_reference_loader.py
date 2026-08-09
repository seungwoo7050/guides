from __future__ import annotations

import importlib.util
from pathlib import Path


def load_reference():
    path = Path(__file__).resolve().parents[2] / "reference/ledgerlab_policy.py"
    spec = importlib.util.spec_from_file_location("mutant_reference_policy", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("reference implementation을 불러올 수 없습니다")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
