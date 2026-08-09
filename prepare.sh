#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
GUIDE_ID=language-implementation
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
STATE_TOOL="$ROOT/scripts/repository_state.py"
CONTROL=$(mktemp -d "${TMPDIR:-/tmp}/guide-language-implementation-prepare.XXXXXX")
CANDIDATE=
cleanup() {
  [ -z "$CANDIDATE" ] || rm -f -- "$CANDIDATE"
  rm -rf -- "$CONTROL"
}
trap cleanup EXIT HUP INT TERM

for command_name in git python3 make sh mktemp; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "필수 command가 없습니다: $command_name" >&2
    exit 1
  }
done
python3 - <<'PY' || exit 1
import sys
if sys.version_info < (3, 12):
    raise SystemExit(f"Python 3.12 이상이 필요합니다: {sys.version.split()[0]}")
PY

git_root=$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null || true)
[ "$git_root" = "$ROOT" ] || {
  echo "독립 language-implementation Git 저장소 루트에서 실행하십시오." >&2
  exit 1
}
[ -x "$STATE_TOOL" ] || {
  echo "repository state 도구를 실행할 수 없습니다: $STATE_TOOL" >&2
  exit 1
}

BEFORE="$CONTROL/before.json"
AFTER="$CONTROL/after.json"
python3 "$STATE_TOOL" snapshot --root "$ROOT" --output "$BEFORE"
mkdir -p -- "$STATE_DIR"
CANDIDATE=$(mktemp "$STATE_DIR/prepared.XXXXXX")
python3 - "$BEFORE" "$CANDIDATE" "$GUIDE_ID" <<'PY'
from __future__ import annotations
import json
import platform
import subprocess
import sys
from pathlib import Path

snapshot = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
snapshot.update({
    "guide_id": sys.argv[3],
    "schema_version": 2,
    "python_version": platform.python_version(),
    "platform": platform.platform(),
    "git_version": subprocess.check_output(["git", "--version"], text=True).strip(),
    "make_version": subprocess.check_output(["make", "--version"], text=True).splitlines()[0],
})
Path(sys.argv[2]).write_text(
    json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
python3 "$STATE_TOOL" snapshot --root "$ROOT" --output "$AFTER"
cmp -s "$BEFORE" "$AFTER" || {
  echo "prepare가 source 또는 Git index 상태를 변경했습니다." >&2
  exit 1
}
mv -f -- "$CANDIDATE" "$MARKER"
CANDIDATE=
trap - EXIT HUP INT TERM
rm -rf -- "$CONTROL"

python3 - "$MARKER" <<'PY'
import json
import sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(f"PREPARED files={value['source_files']} sha256={value['source_fingerprint']}")
print(f"HEAD {value['head_commit']}")
print(f"MARKER {sys.argv[1]}")
PY
