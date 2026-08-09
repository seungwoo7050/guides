#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$root"

python3 - <<'PY'
import json
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path.cwd()
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11 이상이 필요합니다.")

command = [sys.executable, "scripts/source-fingerprint.py", "--root", str(root), "--json"]
before = json.loads(subprocess.check_output(command, text=True))
marker = root / ".guide/machine-learning/prepared.json"
marker.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "guide": "machine-learning",
    "python": ".".join(map(str, sys.version_info[:3])),
    "source_sha256": before["source_sha256"],
    "entries": before["entries"],
}
with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=marker.parent, delete=False) as handle:
    json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
    handle.write("\n")
    temporary = Path(handle.name)
temporary.replace(marker)
after = json.loads(subprocess.check_output(command, text=True))
if before != after:
    raise SystemExit("prepare 과정에서 source fingerprint가 바뀌었습니다.")
print(f"PREPARED {marker.relative_to(root)} source={before['source_sha256']}")
PY
