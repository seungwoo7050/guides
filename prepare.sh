#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

python3 - <<'PY2'
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12 이상이 필요합니다: {sys.version.split()[0]}")
for command in ("make", "git"):
    if shutil.which(command) is None:
        raise SystemExit(f"필수 command가 없습니다: {command}")

root = Path.cwd()
sys.path.insert(0, str(root / "scripts"))
from source_fingerprint import fingerprint

sha256, count = fingerprint(root)
git_head = None
git_status = None
if (root / ".git").exists():
    git_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.strip() or None
    git_status = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=normal"], cwd=root, text=True, stdout=subprocess.PIPE, check=True).stdout.splitlines()

marker = root / ".guide/language-implementation/prepared.json"
marker.parent.mkdir(parents=True, exist_ok=True)
marker.write_text(json.dumps({
    "guide": "language-implementation",
    "schema_version": 1,
    "python": platform.python_version(),
    "platform": platform.platform(),
    "source_sha256": sha256,
    "source_files": count,
    "git_head": git_head,
    "git_status": git_status,
}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(f"PREPARED files={count} sha256={sha256}")
print(f"MARKER {marker}")
PY2
