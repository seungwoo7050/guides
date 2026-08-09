#!/usr/bin/env python3
import os
import runpy
from pathlib import Path

os.environ["MODERN_MODEL_BUG"] = "tokenizer-base-mismatch"
runpy.run_path(str(Path(__file__).resolve().parents[2] / "reference" / "candidate.py"), run_name="__main__")
