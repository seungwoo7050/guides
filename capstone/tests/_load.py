from __future__ import annotations

import os
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "starter"
CAPSTONE_ROOT = Path(os.environ.get("CAPSTONE_ROOT", DEFAULT_ROOT)).resolve()
if not (CAPSTONE_ROOT / "dskv").is_dir():
    raise RuntimeError(f"CAPSTONE_ROOT has no dskv package: {CAPSTONE_ROOT}")
sys.path.insert(0, str(CAPSTONE_ROOT))
