#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
GUIDE_ID=language-implementation
MARKER="$ROOT/.guide/$GUIDE_ID/prepared.json"
STATE_TOOL="$ROOT/scripts/repository_state.py"
CONTROL=$(mktemp -d "${TMPDIR:-/tmp}/guide-language-implementation-verify.XXXXXX")
COPY_ROOT="$CONTROL/repository"
ORIGINAL_BEFORE="$CONTROL/original-before.json"
ORIGINAL_AFTER="$CONTROL/original-after.json"
COPY_BEFORE="$CONTROL/copy-before.json"
COPY_AFTER="$CONTROL/copy-after.json"
PASSED=0
FAILED=0

cleanup() {
  rm -rf -- "$CONTROL"
}
on_signal() {
  code=$1
  trap - EXIT HUP INT TERM
  cleanup
  exit "$code"
}
trap cleanup EXIT
trap 'on_signal 129' HUP
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

if [ -n "${VERIFY_LOG:-}" ]; then
  LOG=$VERIFY_LOG
  case "$LOG" in
    /*) ;;
    *) echo "VERIFY_LOG는 절대 경로여야 합니다: $LOG" >&2; exit 2 ;;
  esac
  [ ! -L "$LOG" ] || { echo "VERIFY_LOG symlink는 허용하지 않습니다: $LOG" >&2; exit 2; }
  LOG=$(python3 - "$LOG" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
)
  case "$LOG" in
    "$ROOT"|"$ROOT"/*) echo "VERIFY_LOG는 저장소 밖에 있어야 합니다: $LOG" >&2; exit 2 ;;
  esac
  mkdir -p -- "$(dirname -- "$LOG")"
  : >"$LOG"
else
  LOG=$(mktemp "${TMPDIR:-/tmp}/guide-language-implementation-verify.XXXXXX")
fi

log() {
  printf '[verify] %s\n' "$*" >>"$LOG"
}
run_step() {
  label=$1
  seconds=$2
  shift 2
  printf '\n[verify] === %s ===\n' "$label" >>"$LOG"
  if python3 "$COPY_ROOT/scripts/run_with_timeout.py" "$seconds" -- "$@" >>"$LOG" 2>&1; then
    PASSED=$((PASSED + 1))
    log "PASS $label"
  else
    FAILED=$((FAILED + 1))
    log "FAIL $label"
  fi
}

for command_name in git python3 make sh mktemp cmp; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "필수 command가 없습니다: $command_name" >&2
    exit 2
  }
done
[ -f "$MARKER" ] || { echo "먼저 ./prepare.sh를 실행하십시오." >&2; exit 2; }
[ -x "$STATE_TOOL" ] || { echo "repository state 도구가 없습니다." >&2; exit 2; }

python3 - "$ROOT" "$MARKER" <<'PY'
from __future__ import annotations
import json
import platform
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
marker = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
sys.path.insert(0, str(root / "scripts"))
from repository_state import repository_snapshot

if marker.get("guide_id") != "language-implementation" or marker.get("schema_version") != 2:
    raise SystemExit("지원하지 않거나 다른 가이드의 prepare marker입니다.")
current = repository_snapshot(root)
for key in ("source_fingerprint", "source_files", "head_commit", "index_fingerprint", "git_status"):
    if marker.get(key) != current.get(key):
        raise SystemExit(f"prepare 이후 {key} 상태가 바뀌었습니다.")
expected = {
    "python_version": platform.python_version(),
    "git_version": subprocess.check_output(["git", "--version"], text=True).strip(),
    "make_version": subprocess.check_output(["make", "--version"], text=True).splitlines()[0],
}
for key, value in expected.items():
    if marker.get(key) != value:
        raise SystemExit(f"prepare 이후 {key} 상태가 바뀌었습니다.")
PY

python3 "$STATE_TOOL" snapshot --root "$ROOT" --output "$ORIGINAL_BEFORE"
python3 "$STATE_TOOL" copy --root "$ROOT" --destination "$COPY_ROOT"
python3 "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_BEFORE"

cd "$COPY_ROOT"
run_step 'Git whitespace' 30 git -C "$ROOT" diff --check
run_step 'Git staged whitespace' 30 git -C "$ROOT" diff --cached --check
run_step 'shell and Python syntax' 60 python3 scripts/check_syntax.py
run_step 'workspace and timeout safety' 60 python3 scripts/test_infrastructure.py
run_step 'repository structure' 60 python3 scripts/check_structure.py
run_step 'Markdown links' 60 python3 scripts/check_links.py
run_step 'concept documents' 60 python3 scripts/check_docs.py
run_step 'Mica specification and conformance mutants' 120 python3 scripts/check_capstone_spec.py
run_step 'observable examples' 60 python3 scripts/run_examples.py

python3 "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_AFTER"
if cmp -s "$COPY_BEFORE" "$COPY_AFTER"; then
  PASSED=$((PASSED + 1))
  log 'PASS isolated source stability'
else
  FAILED=$((FAILED + 1))
  log 'FAIL isolated checks changed source input'
fi
python3 "$STATE_TOOL" snapshot --root "$ROOT" --output "$ORIGINAL_AFTER"
if cmp -s "$ORIGINAL_BEFORE" "$ORIGINAL_AFTER"; then
  PASSED=$((PASSED + 1))
  log 'PASS original source and Git index stability'
else
  FAILED=$((FAILED + 1))
  log 'FAIL verify changed original source or Git index'
fi

trap - EXIT HUP INT TERM
cleanup
cat "$LOG"
printf 'passed=%d failed=%d skipped=0\n' "$PASSED" "$FAILED"
printf 'VERIFY LOG: %s\n' "$LOG"
if [ "$FAILED" -ne 0 ]; then
  printf 'RESULT: FAIL\n'
  exit 1
fi
printf 'RESULT: PASS\n'
