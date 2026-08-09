#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
MARKER=.guide/cloud-computing/prepared.json

"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit('Python 3.10 이상이 필요합니다.')
print('python:', sys.version.split()[0])
PY
command -v sh >/dev/null 2>&1 || { echo "POSIX shell이 필요합니다." >&2; exit 1; }
command -v tar >/dev/null 2>&1 || { echo "tar가 필요합니다." >&2; exit 1; }

if [ -L .guide ] || [ -L .guide/cloud-computing ] || [ -L "$MARKER" ]; then
    echo ".guide 경로는 symbolic link일 수 없습니다." >&2
    exit 1
fi
mkdir -p .guide/cloud-computing
fingerprint=$("$PYTHON" scripts/source_fingerprint.py)
tmp="$MARKER.tmp.$$"
"$PYTHON" - "$fingerprint" "$tmp" <<'PY'
import json
import os
import platform
import sys
fingerprint, target = sys.argv[1:]
value = {
    'schema_version': 1,
    'guide': 'cloud-computing',
    'source_fingerprint': fingerprint,
    'python': platform.python_version(),
    'required_external_services': [],
}
with open(target, 'w', encoding='utf-8') as handle:
    json.dump(value, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
os.replace(target, target.rsplit('.tmp.', 1)[0])
PY
printf 'PREPARED: %s\n' "$fingerprint"
