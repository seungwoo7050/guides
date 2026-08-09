#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
MARKER=.guide/cloud-computing/prepared.json
export PYTHONDONTWRITEBYTECODE=1
umask 077

printf '[prepare] checking required local tools\n'
"$PYTHON" - <<'PY'
import sys

if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10 이상이 필요합니다.')
print('python:', sys.version.split()[0])
PY
command -v sh >/dev/null 2>&1 || { echo 'POSIX shell이 필요합니다.' >&2; exit 1; }
command -v tar >/dev/null 2>&1 || { echo 'tar가 필요합니다.' >&2; exit 1; }

printf '[prepare] fingerprinting source without network or external services\n'
fingerprint=$("$PYTHON" scripts/source_fingerprint.py)

printf '[prepare] writing an atomic, non-symlink marker\n'
"$PYTHON" - "$ROOT" "$MARKER" "$fingerprint" <<'PY'
from __future__ import annotations

import json
import os
import platform
import stat
import sys
from pathlib import Path


root = Path(sys.argv[1]).absolute()
relative = Path(sys.argv[2])
fingerprint = sys.argv[3]
if relative.is_absolute() or '..' in relative.parts:
    raise SystemExit(f'unsafe prepare marker path: {relative}')

target = root / relative
current = root
for component in relative.parent.parts:
    current = current / component
    try:
        metadata = current.lstat()
    except FileNotFoundError:
        os.mkdir(current, 0o700)
        metadata = current.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise SystemExit(f'prepare marker parent must be a non-symlink directory: {current}')

if target.exists() or target.is_symlink():
    metadata = target.lstat()
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise SystemExit(f'prepare marker must be a non-symlink regular file: {target}')

value = {
    'schema_version': 2,
    'fingerprint_version': 2,
    'guide': 'cloud-computing',
    'source_fingerprint': fingerprint,
    'python': platform.python_version(),
    'network_required': False,
    'required_external_services': [],
}
temporary = target.parent / f'.{target.name}.tmp.{os.getpid()}'
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
if hasattr(os, 'O_NOFOLLOW'):
    flags |= os.O_NOFOLLOW
descriptor = -1
try:
    descriptor = os.open(temporary, flags, 0o600)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode('utf-8')
    with os.fdopen(descriptor, 'wb') as stream:
        descriptor = -1
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    if target.exists() or target.is_symlink():
        metadata = target.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise SystemExit(f'prepare marker changed to an unsafe type: {target}')
    os.replace(temporary, target)
    os.chmod(target, 0o600)
finally:
    if descriptor >= 0:
        os.close(descriptor)
    try:
        temporary.unlink()
    except FileNotFoundError:
        pass
PY

after=$("$PYTHON" scripts/source_fingerprint.py)
if [ "$fingerprint" != "$after" ]; then
    echo 'prepare가 source를 변경했습니다.' >&2
    printf 'before=%s\nafter=%s\n' "$fingerprint" "$after" >&2
    exit 1
fi

"$PYTHON" scripts/source_fingerprint.py --check-marker "$MARKER"
printf 'PREPARE SUMMARY: PASS source=%s network=none external-services=none\n' "$fingerprint"
