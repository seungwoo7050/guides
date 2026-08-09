#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
PYTHON=${PYTHON:-python3}
MARKER=.guide/cloud-computing/prepared.json

[ -f "$MARKER" ] || { echo "prepare marker가 없습니다. ./prepare.sh를 먼저 실행하세요." >&2; exit 1; }
expected=$("$PYTHON" - "$MARKER" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as handle:
    marker=json.load(handle)
if marker.get('schema_version') != 1 or marker.get('guide') != 'cloud-computing':
    raise SystemExit('잘못된 prepare marker입니다.')
print(marker['source_fingerprint'])
PY
)
actual=$("$PYTHON" scripts/source_fingerprint.py)
[ "$expected" = "$actual" ] || {
    echo "prepare 이후 source가 변경되었습니다. ./prepare.sh를 다시 실행하세요." >&2
    echo "expected=$expected" >&2
    echo "actual=$actual" >&2
    exit 1
}

TMP=$(mktemp -d "${TMPDIR:-/tmp}/guide-cloud-computing.XXXXXX")
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT HUP INT TERM

tar --exclude=.git --exclude=.guide --exclude=.workspace --exclude='__pycache__' -cf - . | tar -xf - -C "$TMP"
cd "$TMP"
"$PYTHON" scripts/check_structure.py
"$PYTHON" scripts/check_links.py
"$PYTHON" scripts/check_profiles.py
"$PYTHON" -m compileall -q scripts exercises/07-local-cloud-model

echo "VERIFY OK"
