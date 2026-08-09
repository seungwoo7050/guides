#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10 이상이 필요합니다.')
print('Python', '.'.join(map(str, sys.version_info[:3])))
PY

python3 scripts/verify_repository.py --quick

python3 - <<'PY'
from __future__ import annotations

import json
import os
import platform
from pathlib import Path
import stat
import sys
import tempfile

sys.path.insert(0, str(Path('scripts').resolve()))
from source_fingerprint import fingerprint

value, count = fingerprint(Path.cwd())
guide_dir = Path('.guide')
marker_dir = guide_dir / 'platform-engineering'
marker = marker_dir / 'prepared.json'

for directory in (guide_dir, marker_dir):
    if directory.exists() or directory.is_symlink():
        mode = directory.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise SystemExit(f'unsafe preparation path: {directory}')
    else:
        directory.mkdir(mode=0o755)

if marker.is_symlink():
    raise SystemExit(f'unsafe preparation marker: {marker}')

payload = json.dumps({
    'schemaVersion': 1,
    'guide': 'platform-engineering',
    'python': platform.python_version(),
    'sourceSha256': value,
    'sourceFiles': count,
    'preparation': 'source fingerprint only; no system packages or platform tools installed'
}, ensure_ascii=False, indent=2) + '\n'

descriptor, temporary_name = tempfile.mkstemp(
    dir=marker_dir,
    prefix='.prepared.',
    suffix='.tmp',
)
temporary = Path(temporary_name)
try:
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o644)
    os.replace(temporary, marker)
    directory_descriptor = os.open(marker_dir, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)
finally:
    if temporary.exists():
        temporary.unlink()

print('PREPARED', marker)
print('SOURCE SHA256', value)
PY
