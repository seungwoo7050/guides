#!/usr/bin/env bash

# Keep running independent checks so one failure does not hide later evidence.
set -uo pipefail
export GIT_OPTIONAL_LOCKS=0

ROOT=""
if ! ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" || [[ -z "$ROOT" ]]; then
  printf 'repository root cannot be resolved safely\n' >&2
  exit 2
fi
MARKER="$ROOT/.guide/computer-graphics/prepared.json"
GPU_MODE="${VERIFY_GPU:-auto}"
STRICT_MODE="${VERIFY_STRICT:-0}"
FAILED=0
CHECK_COUNT=0
TEMP_ROOT=""
TEMP_PARENT=""

case "$GPU_MODE" in auto|required|off) ;; *) printf 'VERIFY_GPU must be auto|required|off\n' >&2; exit 2 ;; esac
case "$STRICT_MODE" in 0|1) ;; *) printf 'VERIFY_STRICT must be 0 or 1\n' >&2; exit 2 ;; esac
if [[ "$STRICT_MODE" == 1 && "$GPU_MODE" == auto ]]; then
  printf 'VERIFY_STRICT=1 requires an explicit VERIFY_GPU=required or off decision.\n' >&2
  exit 2
fi

if ! TIMESTAMP="$(date +%Y%m%d-%H%M%S)" || [[ -z "$TIMESTAMP" ]]; then
  printf 'verification timestamp could not be created\n' >&2
  exit 2
fi
LOG="${VERIFY_LOG:-${TMPDIR:-/tmp}/guide-computer-graphics-verify-${TIMESTAMP}-$$.log}"
case "$LOG" in /*) ;; *) printf 'VERIFY_LOG must be an absolute path outside the repository\n' >&2; exit 2 ;; esac
if ! LOG="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve(strict=False))' "$LOG")"; then
  printf 'VERIFY_LOG could not be resolved safely\n' >&2
  exit 2
fi
case "$LOG" in "$ROOT"|"$ROOT"/*) printf 'VERIFY_LOG may not be inside the repository\n' >&2; exit 2 ;; esac
mkdir -p -- "$(dirname -- "$LOG")" || exit 2
if [[ -e "$LOG" || -L "$LOG" ]]; then
  printf 'VERIFY_LOG must name a new non-symlink file: %s\n' "$LOG" >&2
  exit 2
fi
(set -o noclobber; : > "$LOG") || exit 2

log() {
  printf '%s\n' "$*" | tee -a "$LOG"
}

run_check() {
  local name=$1
  local seconds=$2
  shift 2
  CHECK_COUNT=$((CHECK_COUNT + 1))
  log "[CHECK] $name"
  if python3 "$ROOT/scripts/run_with_timeout.py" "$seconds" -- "$@" >> "$LOG" 2>&1; then
    log "[PASS] $name"
  else
    local status=$?
    log "[FAIL] $name exit=$status"
    FAILED=1
  fi
}

cleanup() {
  if [[ -n "$TEMP_ROOT" && -n "$TEMP_PARENT" &&
        "$TEMP_ROOT" == "$TEMP_PARENT"/guide-computer-graphics-verify.* &&
        -d "$TEMP_ROOT" && ! -L "$TEMP_ROOT" ]]; then
    rm -rf -- "$TEMP_ROOT"
  fi
}
trap cleanup EXIT HUP INT TERM

cd "$ROOT" || { printf 'repository root is unavailable: %s\n' "$ROOT" >&2; exit 2; }
[[ -f "$MARKER" ]] || { log '[FAIL] 먼저 ./prepare.sh를 실행하십시오.'; exit 1; }
run_check source-marker 30 python3 scripts/source_fingerprint.py --check-file "$MARKER"
run_check shell-syntax 30 bash -n prepare.sh verify.sh scripts/new-workspace.sh
run_check git-whitespace 30 git diff --check
run_check git-index-whitespace 30 git diff --cached --check

if ! TEMP_PARENT="$(cd -- "${TMPDIR:-/tmp}" && pwd -P)"; then
  log '[FAIL] temporary directory parent cannot be resolved'
  exit 2
fi
case "$TEMP_PARENT" in
  /|"$ROOT"|"$ROOT"/*)
    log "[FAIL] unsafe temporary directory parent: $TEMP_PARENT"
    exit 2
    ;;
esac
if ! TEMP_ROOT="$(mktemp -d "$TEMP_PARENT/guide-computer-graphics-verify.XXXXXX")"; then
  log '[FAIL] temporary verification root could not be created'
  exit 2
fi
if [[ ! -d "$TEMP_ROOT" || -L "$TEMP_ROOT" ||
      "$TEMP_ROOT" != "$TEMP_PARENT"/guide-computer-graphics-verify.* ]]; then
  log "[FAIL] unsafe temporary verification root: $TEMP_ROOT"
  exit 2
fi
SOURCE_BEFORE="$TEMP_ROOT/original-source-before.json"
SOURCE_AFTER="$TEMP_ROOT/original-source-after.json"
TRACKED_BEFORE="$TEMP_ROOT/original-tracked-before.txt"
TRACKED_AFTER="$TEMP_ROOT/original-tracked-after.txt"
WORK="$TEMP_ROOT/repository"
if ! python3 scripts/repository_state.py --root "$ROOT" --output "$SOURCE_BEFORE" --reject-symlinks; then
  log '[FAIL] original source snapshot or symlink check failed'
  exit 1
fi
if ! git status --porcelain=v1 --untracked-files=no > "$TRACKED_BEFORE"; then
  log '[FAIL] original tracked Git status could not be recorded'
  exit 1
fi

if ! python3 - "$ROOT" "$WORK" <<'PY'
from pathlib import Path
import shutil
import sys

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
ignored = shutil.ignore_patterns(
    ".git", ".guide", "build", "build-*", "out", "workspace", ".workspace.*",
    "__pycache__", "*.pyc", "*.log", "*.spv", "*.dxil", "*.metallib",
)
shutil.copytree(source, destination, symlinks=True, ignore=ignored)
PY
then
  log '[FAIL] isolated repository copy failed'
  exit 1
fi
if [[ ! -d "$WORK" || -L "$WORK" ]] ||
   ! python3 "$ROOT/scripts/repository_state.py" --root "$WORK" --reject-symlinks >/dev/null; then
  log '[FAIL] isolated repository copy is missing, linked, or contains source symlinks'
  exit 1
fi
if [[ "$(cd -- "$WORK" && pwd -P)" != "$TEMP_ROOT/repository" ]]; then
  log '[FAIL] isolated repository escaped its temporary root'
  exit 1
fi

cd "$WORK" || { log '[FAIL] cannot enter isolated repository copy'; exit 1; }
run_check python-syntax 60 python3 -m compileall -q scripts exercises tools
run_check repository-contract 120 python3 scripts/verify_repository.py
run_check repository-negative-controls 300 python3 scripts/test_repository_verifier.py
run_check ppm-oracle 30 python3 tools/ppm_diff.py --self-test
run_check starter-negative-control 300 python3 exercises/check.py --impl starter --stage all --expect not-implemented --gpu off
run_check reference-contract 900 python3 exercises/check.py --impl reference --stage all --expect pass --gpu "$GPU_MODE"
run_check debug-ctest 300 ctest --test-dir "build/check-reference-$GPU_MODE" --output-on-failure

if [[ -f scripts/test_mutations.py ]]; then
  run_check known-bad-mutations 1200 python3 scripts/test_mutations.py --gpu "$GPU_MODE"
else
  log '[FAIL] scripts/test_mutations.py is missing'
  FAILED=1
fi
if [[ -f scripts/test_workspace_tools.py ]]; then
  run_check workspace-safety 180 python3 scripts/test_workspace_tools.py \
    --reference "build/check-reference-$GPU_MODE/cg-render" \
    --starter "build/check-starter-off/cg-render"
else
  log '[FAIL] scripts/test_workspace_tools.py is missing'
  FAILED=1
fi

run_check release-configure 180 cmake -S exercises/08-renderer-capstone/project -B build/release \
  -DCG_IMPLEMENTATION=reference -DCG_GPU="$GPU_MODE" -DCMAKE_BUILD_TYPE=Release
run_check release-build 600 cmake --build build/release --parallel 4
run_check release-ctest 300 ctest --test-dir build/release --output-on-failure

if c++ -x c++ -std=c++20 -fsanitize=address,undefined -fno-omit-frame-pointer \
     -o "$TEMP_ROOT/sanitizer-probe" - >/dev/null 2>&1 <<'CPP'
#include <vector>
int main() { std::vector<int> values{1, 2, 3}; return values.at(1) == 2 ? 0 : 1; }
CPP
then
  if "$TEMP_ROOT/sanitizer-probe" >> "$LOG" 2>&1; then
    run_check sanitizer-configure 180 cmake -S exercises/08-renderer-capstone/project -B build/sanitize \
      -DCG_IMPLEMENTATION=reference -DCG_GPU=off -DCMAKE_BUILD_TYPE=Debug \
      '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer'
    run_check sanitizer-build 600 cmake --build build/sanitize --parallel 4
    run_check sanitizer-ctest 300 ctest --test-dir build/sanitize --output-on-failure
  else
    log '[FAIL] sanitizer runtime probe failed'
    [[ "$STRICT_MODE" == 1 ]] && FAILED=1
  fi
else
  log '[INFO] sanitizer compiler probe unavailable'
  [[ "$STRICT_MODE" == 1 ]] && FAILED=1
fi

cd "$ROOT" || { log '[FAIL] cannot return to original repository root'; exit 1; }
if ! python3 scripts/repository_state.py --root "$ROOT" --output "$SOURCE_AFTER" --reject-symlinks; then
  log '[FAIL] final original source snapshot or symlink check failed'
  FAILED=1
fi
if ! git status --porcelain=v1 --untracked-files=no > "$TRACKED_AFTER"; then
  log '[FAIL] final original tracked Git status could not be recorded'
  FAILED=1
fi
if cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
  log '[PASS] original source snapshot unchanged'
else
  log '[FAIL] verification changed original source'
  FAILED=1
fi
if cmp -s "$TRACKED_BEFORE" "$TRACKED_AFTER"; then
  log '[PASS] original tracked Git status unchanged'
else
  log '[FAIL] verification changed tracked Git status'
  FAILED=1
fi

cleanup
TEMP_ROOT=""
trap - EXIT HUP INT TERM

if [[ "$FAILED" == 0 ]]; then
  log "VERIFY_OK checks=$CHECK_COUNT gpu=$GPU_MODE log=$LOG"
  exit 0
fi
log "VERIFY_FAILED checks=$CHECK_COUNT gpu=$GPU_MODE log=$LOG"
exit 1
