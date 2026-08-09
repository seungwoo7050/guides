from __future__ import annotations

import sys
from pathlib import Path


Path(sys.argv[1]).write_text(sys.argv[2], encoding="utf-8")
