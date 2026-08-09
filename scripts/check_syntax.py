#!/usr/bin/env python3
from __future__ import annotations

import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    failures: list[str] = []
    shell_count = 0
    for path in sorted(ROOT.rglob("*.sh")):
        if any(part in {".git", ".guide", ".workspaces"} for part in path.parts):
            continue
        first = path.read_text(encoding="utf-8").splitlines()[0] if path.stat().st_size else ""
        shell = "bash" if "bash" in first else "sh"
        result = subprocess.run([shell, "-n", str(path)], text=True, capture_output=True, check=False)
        shell_count += 1
        if result.returncode:
            failures.append(f"{path.relative_to(ROOT)}: {result.stderr.strip()}")
    python_count = 0
    with tempfile.TemporaryDirectory(prefix="language-implementation-pycache-") as cache:
        old = os.environ.get("PYTHONPYCACHEPREFIX")
        os.environ["PYTHONPYCACHEPREFIX"] = cache
        try:
            for path in sorted(ROOT.rglob("*.py")):
                if any(part in {".git", ".guide", ".workspaces", "__pycache__"} for part in path.parts):
                    continue
                python_count += 1
                try:
                    py_compile.compile(str(path), doraise=True)
                except py_compile.PyCompileError as exc:
                    failures.append(f"{path.relative_to(ROOT)}: {exc.msg}")
        finally:
            if old is None:
                os.environ.pop("PYTHONPYCACHEPREFIX", None)
            else:
                os.environ["PYTHONPYCACHEPREFIX"] = old
    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print(f"PASS syntax shell={shell_count} python={python_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
