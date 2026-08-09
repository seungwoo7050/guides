#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

python3 - <<'PY'
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

root = Path.cwd()
if sys.version_info < (3, 10):
    raise SystemExit(f"Python 3.10 이상이 필요합니다. 현재: {sys.version.split()[0]}")

required = [
    root / "README.md",
    root / "docs/00-roadmap.md",
    root / "scripts/verify.py",
    root / "scripts/check_submission.py",
    root / "examples/fixed-step-replay/sim.py",
    root / "projects/relay-arena-vertical-slice/tests/check_contract.py",
]
for path in required:
    if not path.is_file():
        raise SystemExit(f"필수 파일이 없습니다: {path.relative_to(root)}")

ignored_parts = {".git", ".guide", "__pycache__"}
ignored_suffixes = {".pyc", ".pyo", ".log"}
digest = hashlib.sha256()
for path in sorted(root.rglob("*"), key=lambda p: p.as_posix()):
    if not path.is_file():
        continue
    relative = path.relative_to(root)
    if any(part in ignored_parts for part in relative.parts) or path.suffix in ignored_suffixes:
        continue
    digest.update(relative.as_posix().encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
    digest.update(b"\0")

marker = root / ".guide/game-development/prepared.json"
marker.parent.mkdir(parents=True, exist_ok=True)
head = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=root,
    text=True,
    capture_output=True,
    check=False,
)
marker.write_text(
    json.dumps(
        {
            "guide": "game-development",
            "python": ".".join(map(str, sys.version_info[:3])),
            "git_head": head.stdout.strip() if head.returncode == 0 else None,
            "source_sha256": digest.hexdigest(),
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(f"PREPARED {marker.relative_to(root)}")
PY
