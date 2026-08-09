#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$root"

python3 - <<'PY'
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path.cwd()
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 이상이 필요합니다.")

command = [sys.executable, "scripts/repo-state.py", "--root", str(root)]
before = json.loads(subprocess.check_output(command, text=True))
marker = root / ".guide/machine-learning/prepared.json"
for candidate in (marker.parent, marker):
    if candidate.is_symlink():
        raise SystemExit(f"준비 marker 경로의 symlink를 허용하지 않습니다: {candidate}")
marker.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "guide": "machine-learning",
    "python": ".".join(map(str, sys.version_info[:3])),
    "state": before,
}
with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=marker.parent, delete=False) as handle:
    os.chmod(handle.name, 0o600)
    json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
    temporary = Path(handle.name)
temporary.replace(marker)
after = json.loads(subprocess.check_output(command, text=True))
if before != after:
    raise SystemExit("prepare 과정에서 source·index·workspace 상태가 바뀌었습니다.")
print(
    f"PREPARED {marker.relative_to(root)} "
    f"head={before['head']} source={before['source_sha256']} index={before['index_sha256']}"
)
PY
