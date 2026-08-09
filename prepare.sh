#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

PYTHON=${PYTHON:-python3}
"$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit('Python 3.11 이상이 필요합니다.')
PY

GUIDE_DIR=.guide
MARKER_DIR=$GUIDE_DIR/main
MARKER=$MARKER_DIR/prepared.json

require_directory_or_absent() {
    path=$1
    if [ -L "$path" ]; then
        echo "$path 는 symbolic link일 수 없습니다." >&2
        exit 1
    fi
    if [ -e "$path" ] && [ ! -d "$path" ]; then
        echo "$path 는 directory여야 합니다." >&2
        exit 1
    fi
}

require_directory_or_absent "$GUIDE_DIR"
mkdir -p "$GUIDE_DIR"
require_directory_or_absent "$MARKER_DIR"
mkdir -p "$MARKER_DIR"

if [ -L "$MARKER" ] || { [ -e "$MARKER" ] && [ ! -f "$MARKER" ]; }; then
    echo "$MARKER 는 regular file이어야 합니다." >&2
    exit 1
fi

fingerprint=$("$PYTHON" scripts/source_fingerprint.py)
temporary_marker=$(mktemp "$MARKER_DIR/.prepared.json.XXXXXX")
cleanup_marker() {
    if [ -n "${temporary_marker:-}" ]; then
        rm -f "$temporary_marker"
    fi
}
trap cleanup_marker EXIT HUP INT TERM

"$PYTHON" - "$fingerprint" > "$temporary_marker" <<'PY'
import json
import platform
import sys
from datetime import datetime, timezone
fingerprint = sys.argv[1]
print(json.dumps({
    'guide': 'main',
    'schema_version': 1,
    'source_fingerprint': fingerprint,
    'python': platform.python_version(),
    'prepared_at': datetime.now(timezone.utc).isoformat(),
}, ensure_ascii=False, indent=2))
PY

mv "$temporary_marker" "$MARKER"
temporary_marker=
trap - EXIT HUP INT TERM

echo "PREPARED main $fingerprint"
