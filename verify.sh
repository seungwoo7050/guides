#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
MARKER=.guide/computer-graphics/prepared.json

if [ ! -f "$MARKER" ]; then
  echo '먼저 ./prepare.sh를 실행하십시오.' >&2
  exit 1
fi

python3 scripts/source_fingerprint.py --check-file "$MARKER"
BEFORE=$(python3 scripts/source_fingerprint.py)
TMP=$(mktemp -d "${TMPDIR:-/tmp}/guide-computer-graphics.XXXXXX")
cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT HUP INT TERM

python3 - "$ROOT" "$TMP/repository" <<'PY'
from pathlib import Path
import shutil
import sys
src = Path(sys.argv[1])
dst = Path(sys.argv[2])
shutil.copytree(src, dst, ignore=shutil.ignore_patterns('.git', '.guide', 'build', 'out', '__pycache__', '*.pyc', '*.log'))
PY

(
  cd "$TMP/repository"
  python3 scripts/verify_repository.py
)

AFTER=$(python3 scripts/source_fingerprint.py)
if [ "$BEFORE" != "$AFTER" ]; then
  echo "원본 source가 검증 중 변경됐습니다: before=$BEFORE after=$AFTER" >&2
  exit 1
fi

echo "VERIFY_OK source_sha256=$AFTER"
