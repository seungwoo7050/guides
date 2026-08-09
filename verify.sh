#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
MARKER=.guide/main/prepared.json

if [ -L .guide ] || [ -L .guide/main ] || [ -L "$MARKER" ]; then
    echo "prepare 경로와 marker는 symbolic link일 수 없습니다." >&2
    exit 1
fi

if [ ! -f "$MARKER" ]; then
    echo "prepare marker가 없습니다. ./prepare.sh를 먼저 실행하세요." >&2
    exit 1
fi

expected=$("$PYTHON" - "$MARKER" <<'PY'
import json
import sys
with open(sys.argv[1], encoding='utf-8') as handle:
    marker = json.load(handle)
if marker.get('schema_version') != 1:
    raise SystemExit('prepare marker schema_version이 올바르지 않습니다.')
if marker.get('guide') != 'main':
    raise SystemExit('prepare marker가 main용이 아닙니다.')
fingerprint = marker.get('source_fingerprint')
if not isinstance(fingerprint, str) or not fingerprint:
    raise SystemExit('prepare marker에 source_fingerprint가 없습니다.')
print(fingerprint)
PY
)
actual=$("$PYTHON" scripts/source_fingerprint.py)
if [ "$expected" != "$actual" ]; then
    echo "prepare 이후 source가 변경되었습니다. ./prepare.sh를 다시 실행하세요." >&2
    echo "expected=$expected" >&2
    echo "actual=$actual" >&2
    exit 1
fi

"$PYTHON" scripts/check_catalog.py
"$PYTHON" scripts/render_catalog.py --check
"$PYTHON" scripts/check_links.py

echo "VERIFY OK"
