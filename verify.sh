#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
default_log="/tmp/guide-distributed-systems-verify-$$.log"
LOG=${VERIFY_LOG:-$default_log}

case "$LOG" in
  /*) ;;
  *) echo 'VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다.' >&2; exit 2 ;;
esac
LOG=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$LOG")
case "$LOG" in
  "$ROOT"|"$ROOT"/*) echo 'VERIFY_LOG는 저장소 내부일 수 없습니다.' >&2; exit 2 ;;
esac
mkdir -p "$(dirname -- "$LOG")"

WORK=$(mktemp -d /tmp/guide-distributed-systems-verify.XXXXXX)
SOURCE_BEFORE="$WORK/source-before.json"
SOURCE_AFTER="$WORK/source-after.json"
INDEX_BEFORE="$WORK/index-before.json"
INDEX_AFTER="$WORK/index-after.json"
WORKSPACE_BEFORE="$WORK/workspace-before.json"
WORKSPACE_AFTER="$WORK/workspace-after.json"
COPY_ROOT="$WORK/repository"
COPY_BEFORE="$WORK/copy-before.json"
COPY_AFTER="$WORK/copy-after.json"

cleanup() {
  rm -rf -- "$WORK"
}
trap cleanup EXIT HUP INT TERM

run_all() {
  printf '[verify] original source/index preflight\n'
  PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$WORK/preflight-cache" \
    python3 "$ROOT/scripts/repository_state.py" manifest --root "$ROOT" --output "$SOURCE_BEFORE"
  PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$WORK/preflight-cache" \
    python3 "$ROOT/scripts/repository_state.py" git-index --root "$ROOT" --output "$INDEX_BEFORE"
  PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$WORK/preflight-cache" \
    python3 "$ROOT/scripts/repository_state.py" workspace --root "$ROOT" --output "$WORKSPACE_BEFORE"
  PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$WORK/prepared-cache" \
    python3 "$ROOT/scripts/verify.py" --prepared-only
  PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$WORK/preflight-cache" \
    python3 "$ROOT/scripts/verify.py" --policy-only
  git -C "$ROOT" diff --check
  git -C "$ROOT" diff --cached --check

  printf '[verify] isolated source copy\n'
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/copy_source.py" "$ROOT" "$COPY_ROOT"
  PYTHONDONTWRITEBYTECODE=1 python3 "$COPY_ROOT/scripts/repository_state.py" \
    manifest --root "$COPY_ROOT" --output "$COPY_BEFORE"

  printf '[verify] curriculum, exercise, oracle, model, and starter contracts\n'
  (
    cd "$COPY_ROOT"
    PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$WORK/copy-cache" \
      python3 scripts/verify.py --quick
  )

  PYTHONDONTWRITEBYTECODE=1 python3 "$COPY_ROOT/scripts/repository_state.py" \
    manifest --root "$COPY_ROOT" --output "$COPY_AFTER"
  cmp -s "$COPY_BEFORE" "$COPY_AFTER" || {
    echo '[verify] isolated checks changed source bytes, modes, or symlinks' >&2
    return 1
  }

  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/repository_state.py" \
    manifest --root "$ROOT" --output "$SOURCE_AFTER"
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/repository_state.py" \
    git-index --root "$ROOT" --output "$INDEX_AFTER"
  PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/scripts/repository_state.py" \
    workspace --root "$ROOT" --output "$WORKSPACE_AFTER"
  cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER" || {
    echo '[verify] verification changed original source bytes, modes, or symlinks' >&2
    return 1
  }
  cmp -s "$INDEX_BEFORE" "$INDEX_AFTER" || {
    echo '[verify] verification changed the Git index entries, modes, or flags' >&2
    return 1
  }
  cmp -s "$WORKSPACE_BEFORE" "$WORKSPACE_AFTER" || {
    echo '[verify] verification changed .workspace bytes, modes, or symlinks' >&2
    return 1
  }
  printf 'passed=6 failed=0 skipped=0\n'
  printf 'RESULT: PASS\n'
}

if run_all >"$LOG" 2>&1; then
  cat "$LOG"
  printf 'VERIFY LOG: %s\n' "$LOG"
else
  status=$?
  cat "$LOG" >&2
  printf 'VERIFY LOG: %s\n' "$LOG" >&2
  printf 'RESULT: FAIL\n' >&2
  exit "$status"
fi
