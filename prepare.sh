#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ROOT"

command -v python3 >/dev/null 2>&1 || {
  echo "ERROR: Python 3 is required." >&2
  exit 1
}
command -v git >/dev/null 2>&1 || {
  echo "ERROR: Git is required." >&2
  exit 1
}

PYTHONDONTWRITEBYTECODE=1 python3 -B -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else "Python 3.12 or newer is required")'

# A marker is useful only for a repository whose static contracts already hold.
make check

PYTHONDONTWRITEBYTECODE=1 python3 -B - "$ROOT" <<'PY'
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import platform
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


root = Path(sys.argv[1]).resolve(strict=True)
module_path = root / "scripts" / "source_fingerprint.py"
spec = importlib.util.spec_from_file_location("source_fingerprint", module_path)
if spec is None or spec.loader is None:
    raise SystemExit("ERROR: cannot load source fingerprint module")
fingerprints = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fingerprints)

marker_parent = root / ".guide" / "agentic-systems"
marker = marker_parent / "prepared.json"

current = root
for component in (root / ".guide", marker_parent):
    if os.path.lexists(component):
        metadata = component.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise SystemExit(f"ERROR: unsafe preparation directory: {component}")
    else:
        component.mkdir(mode=0o700)
    current = component
if os.path.lexists(marker):
    metadata = marker.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise SystemExit(f"ERROR: unsafe preparation marker: {marker}")

source = fingerprints.fingerprint_report(root)
git = fingerprints.git_state(root)

schema_versions: dict[str, str] = {}
for path in sorted((root / "contracts").glob("*.schema.json")):
    value = json.loads(path.read_text(encoding="utf-8"))
    identifier = value.get("$id", "")
    suffix = identifier.rsplit("-", 1)[-1].removesuffix(".schema.json") if isinstance(identifier, str) else ""
    schema_versions[path.name] = suffix

git_version = subprocess.run(
    ["git", "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
).stdout.strip()
body = {
    "marker_schema_version": "2",
    "guide": {"id": "agentic-systems", "version": "1.0"},
    "profile": {"id": "local-coding-agent", "version": "1.0"},
    "contracts": {"action": "1.0", "model_event": "1.0", "schemas": schema_versions},
    "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    "source": source,
    "git": git,
    "tools": {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": str(Path(sys.executable).resolve()),
        },
        "git": {"version": git_version},
    },
    "platform": {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python_platform": platform.platform(),
    },
}

marker_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
descriptor, temporary_raw = tempfile.mkstemp(prefix=".prepared.", suffix=".json", dir=marker_parent)
temporary = Path(temporary_raw)
try:
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(body, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, marker)
    directory_fd = os.open(marker_parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
finally:
    if temporary.exists():
        temporary.unlink()

print(
    f"PREPARED {marker.relative_to(root)} source={source['sha256']} "
    f"entries={source['count']} bytes={source['bytes']} index_tree={git['index_tree']}"
)
PY
