from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

path = Path(__file__).resolve().parents[2] / "reference" / "algorithms.py"
spec = importlib.util.spec_from_file_location("_capstone_reference", path)
assert spec is not None and spec.loader is not None
reference = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reference
spec.loader.exec_module(reference)

for name in dir(reference):
    if not name.startswith("_"):
        globals()[name] = getattr(reference, name)
