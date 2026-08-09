#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"
MARKER="$ROOT/.guide/data-engineering/prepared.json"

if [ ! -f "$MARKER" ]; then
  echo '먼저 make prepare를 실행하십시오.' >&2
  exit 1
fi

BEFORE=$(python3 -B scripts/fingerprint.py "$ROOT")
PREPARED=$(python3 - "$MARKER" <<'PY'
import json
import sys
print(json.load(open(sys.argv[1], encoding='utf-8'))['source_fingerprint'])
PY
)
if [ "$BEFORE" != "$PREPARED" ]; then
  echo 'prepare 이후 source가 변경됐습니다. make prepare를 다시 실행하십시오.' >&2
  exit 1
fi

if [ -n "${VERIFY_LOG:-}" ]; then
  LOG=$VERIFY_LOG
  CREATE_LOG=1
else
  LOG=$(mktemp "${TMPDIR:-/tmp}/guide-data-engineering-verify.XXXXXX")
  CREATE_LOG=0
fi

python3 - "$ROOT" "$LOG" "$CREATE_LOG" <<'PY'
import os
import sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
log = Path(sys.argv[2])
create_log = sys.argv[3] == '1'
if not log.is_absolute():
    raise SystemExit('VERIFY_LOG는 절대 경로여야 합니다.')
resolved = log.resolve(strict=False)
try:
    resolved.relative_to(root)
except ValueError:
    pass
else:
    raise SystemExit('VERIFY_LOG는 저장소 밖 경로여야 합니다.')
if not resolved.parent.is_dir():
    raise SystemExit('VERIFY_LOG 상위 디렉터리가 존재해야 합니다.')
if create_log:
    try:
        descriptor = os.open(resolved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit('VERIFY_LOG 기존 파일을 덮어쓰지 않습니다.')
    else:
        os.close(descriptor)
PY

TMP=$(mktemp -d /tmp/guide-data-engineering-work-XXXXXX)
cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT INT TERM
COPY="$TMP/data-engineering"

python3 - "$ROOT" "$COPY" <<'PY'
import shutil
import sys
from pathlib import Path
source = Path(sys.argv[1])
target = Path(sys.argv[2])
ignore = shutil.ignore_patterns('.git', '.guide', 'workspace', '__pycache__', '*.pyc', '*.pyo', '*.log', '.pytest_cache', '.coverage')
shutil.copytree(source, target, symlinks=True, ignore=ignore)
PY

set +e
(
  set -eu
  cd "$COPY"
  printf '%s\n' '== structure and links =='
  PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/validate.py
  printf '%s\n' '== example unit tests =='
  PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tests -p 'test_*.py' -v
  printf '%s\n' '== skeleton/reference contracts =='
  PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/exercise_tool.py verify-all
  printf '%s\n' '== example smoke =='
  PYTHONDONTWRITEBYTECODE=1 python3 -B examples/schema_compatibility.py
  printf '%s\n' 'VERIFY OK'
) >"$LOG" 2>&1
STATUS=$?
set -e
cat "$LOG"
if [ "$STATUS" -ne 0 ]; then
  exit "$STATUS"
fi

AFTER=$(python3 -B scripts/fingerprint.py "$ROOT")
if [ "$BEFORE" != "$AFTER" ]; then
  echo 'verify가 source를 변경했습니다.' >&2
  exit 1
fi
printf 'SOURCE UNCHANGED %s\n' "$AFTER"
printf 'LOG %s\n' "$LOG"
