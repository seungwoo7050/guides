#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="data-engineering"
STATE_TOOL="$ROOT/scripts/repository_state.py"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
TEMP_MARKER=''
TEMP_MARKER_ID=''
SUCCESS=0
export GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1

die() { printf '[prepare] ERROR: %s\n' "$*" >&2; exit 1; }
require() { command -v "$1" >/dev/null 2>&1 || die "필수 명령이 없습니다: $1"; }

finish() {
    local status=$?
    trap - EXIT HUP INT TERM
    if [[ -n "$TEMP_MARKER" && ( -e "$TEMP_MARKER" || -L "$TEMP_MARKER" ) ]]; then
        if ! python3 - "$TEMP_MARKER" "$TEMP_MARKER_ID" <<'PY'
import os
import stat
import sys

path, expected = sys.argv[1:]
metadata = os.lstat(path)
actual = f"{metadata.st_dev}:{metadata.st_ino}"
if actual != expected or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
    raise SystemExit(f"refusing to unlink replaced marker temporary: {path}")
os.unlink(path)
PY
        then
            status=1
        fi
    fi
    if (( status != 0 || SUCCESS != 1 )); then
        printf 'PREPARE RESULT: FAIL\n' >&2
        (( status != 0 )) || status=1
    fi
    exit "$status"
}
trap finish EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

for command_name in bash git make mktemp python3; do
    require "$command_name"
done
[[ "$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null)" == "$ROOT" ]] || \
    die '독립 Git 저장소 루트에서 실행해야 합니다.'
python3 - <<'PY' || die 'Python 3.11 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
MAKE_VERSION="$(make --version 2>&1 | sed -n '1p')"
[[ -n "$MAKE_VERSION" ]] || die 'make 기능 probe 결과가 비어 있습니다.'
MAKE_PROBE="$(printf 'probe:\n\t@printf "%%s\\n" GUIDE_MAKE_FUNCTIONAL\n' | make -s -f - probe 2>&1)" || \
    die 'make target 실행 probe에 실패했습니다.'
[[ "$MAKE_PROBE" == GUIDE_MAKE_FUNCTIONAL ]] || die 'make target 실행 probe가 올바르지 않습니다.'

cd "$ROOT"
before_source="$(python3 -B "$STATE_TOOL" source --root "$ROOT")"
before_workspace="$(python3 -B "$STATE_TOOL" workspace --root "$ROOT")"
before_index="$(python3 -B "$STATE_TOOL" index --root "$ROOT")"
before_head="$(git -C "$ROOT" rev-parse --verify HEAD)"
python3 -B "$ROOT/scripts/validate.py"
after_source="$(python3 -B "$STATE_TOOL" source --root "$ROOT")"
after_workspace="$(python3 -B "$STATE_TOOL" workspace --root "$ROOT")"
after_index="$(python3 -B "$STATE_TOOL" index --root "$ROOT")"
after_head="$(git -C "$ROOT" rev-parse --verify HEAD)"
[[ "$before_source" == "$after_source" ]] || die 'prepare가 source tree를 변경했습니다.'
[[ "$before_workspace" == "$after_workspace" ]] || die 'prepare가 학습자 workspace를 변경했습니다.'
[[ "$before_index" == "$after_index" ]] || die 'prepare가 Git index를 변경했습니다.'
[[ "$before_head" == "$after_head" ]] || die 'prepare 중 HEAD가 변경됐습니다.'

umask 077
[[ ! -L "$ROOT/.guide" ]] || die '.guide symlink는 허용하지 않습니다.'
[[ ! -e "$ROOT/.guide" || -d "$ROOT/.guide" ]] || die '.guide가 디렉터리가 아닙니다.'
mkdir -p -- "$ROOT/.guide"
[[ ! -L "$STATE_DIR" ]] || die '.guide/data-engineering symlink는 허용하지 않습니다.'
[[ ! -e "$STATE_DIR" || -d "$STATE_DIR" ]] || die '.guide/data-engineering이 디렉터리가 아닙니다.'
mkdir -p -- "$STATE_DIR"
[[ "$(cd -- "$STATE_DIR" && pwd -P)" == "$STATE_DIR" ]] || \
    die '준비 상태 디렉터리는 저장소 내부 실제 디렉터리여야 합니다.'
if [[ -e "$MARKER" || -L "$MARKER" ]]; then
    [[ -f "$MARKER" && ! -L "$MARKER" ]] || \
        die 'prepared marker는 일반 파일이어야 합니다.'
fi

TEMP_MARKER="$(mktemp "$STATE_DIR/.prepared.XXXXXX")" || die 'marker 임시 파일을 만들지 못했습니다.'
temp_parent="${TEMP_MARKER%/*}"
temp_name="${TEMP_MARKER##*/}"
[[ "$temp_parent" == "$STATE_DIR" && "$temp_name" == .prepared.?????? ]] || \
    die 'marker 임시 파일이 안전한 sibling 경로가 아닙니다.'
[[ "$(cd -- "$temp_parent" && pwd -P)" == "$STATE_DIR" ]] || \
    die 'marker 임시 파일의 실제 parent가 준비 상태 디렉터리가 아닙니다.'
[[ -f "$TEMP_MARKER" && ! -L "$TEMP_MARKER" ]] || die 'marker 임시 파일이 일반 파일이 아닙니다.'
TEMP_MARKER_ID="$(python3 - "$TEMP_MARKER" <<'PY'
import os
import stat
import sys

metadata = os.lstat(sys.argv[1])
if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
    raise SystemExit(1)
print(f"{metadata.st_dev}:{metadata.st_ino}")
PY
)" || die 'marker 임시 파일 identity를 기록하지 못했습니다.'

if [[ "${GUIDE_PREPARE_TEST_HOLD:-0}" == 1 ]]; then
    ready_file="${GUIDE_PREPARE_TEST_READY_FILE:-}"
    release_file="${GUIDE_PREPARE_TEST_RELEASE_FILE:-}"
    [[ "$ready_file" == /* && "$release_file" == /* ]] || \
        die 'prepare test hold 경로는 절대 경로여야 합니다.'
    [[ ! -e "$ready_file" && ! -L "$ready_file" ]] || die 'prepare test ready 파일이 이미 있습니다.'
    (set -C; printf '%s\n' "$$" > "$ready_file") || die 'prepare test ready 파일을 만들지 못했습니다.'
    while [[ ! -e "$release_file" ]]; do sleep 0.02; done
fi

PYTHON_ID="$(python3 - <<'PY'
import platform
import sys
print(f"{platform.python_implementation()} {platform.python_version()} ({sys.executable})")
PY
)"
GIT_VERSION="$(git --version)"
MKTEMP_PATH="$(command -v mktemp)"
GUIDE_ID="$GUIDE_ID" GUIDE_HEAD="$after_head" GUIDE_SOURCE="$after_source" \
GUIDE_INDEX="$after_index" GUIDE_PYTHON="$PYTHON_ID" GUIDE_GIT="$GIT_VERSION" \
GUIDE_MAKE="$MAKE_VERSION" GUIDE_MKTEMP="$MKTEMP_PATH" GUIDE_BASH="$BASH_VERSION" \
python3 - "$TEMP_MARKER" "$MARKER" <<'PY'
import json
import os
import stat
import sys
from pathlib import Path

temporary, marker = map(Path, sys.argv[1:])
payload = {
    "schema_version": 2,
    "guide_id": os.environ["GUIDE_ID"],
    "head_commit": os.environ["GUIDE_HEAD"],
    "source_fingerprint": os.environ["GUIDE_SOURCE"],
    "index_fingerprint": os.environ["GUIDE_INDEX"],
    "tools": {
        "bash": os.environ["GUIDE_BASH"],
        "git": os.environ["GUIDE_GIT"],
        "make": os.environ["GUIDE_MAKE"],
        "mktemp": os.environ["GUIDE_MKTEMP"],
        "python": os.environ["GUIDE_PYTHON"],
    },
}
nofollow = getattr(os, "O_NOFOLLOW", None)
if nofollow is None:
    raise SystemExit("O_NOFOLLOW를 지원하지 않는 플랫폼입니다.")
descriptor = os.open(temporary, os.O_WRONLY | nofollow)
try:
    path_state = os.lstat(temporary)
    descriptor_state = os.fstat(descriptor)
    if (
        not stat.S_ISREG(descriptor_state.st_mode)
        or descriptor_state.st_nlink != 1
        or (path_state.st_dev, path_state.st_ino)
        != (descriptor_state.st_dev, descriptor_state.st_ino)
    ):
        raise SystemExit("marker 임시 파일 identity가 바뀌었습니다.")
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    os.fchmod(descriptor, 0o600)
    os.ftruncate(descriptor, 0)
    view = memoryview(encoded)
    while view:
        view = view[os.write(descriptor, view):]
    os.fsync(descriptor)
finally:
    os.close(descriptor)
os.replace(temporary, marker)
directory = os.open(marker.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
try:
    os.fsync(directory)
finally:
    os.close(directory)
PY
TEMP_MARKER=''
TEMP_MARKER_ID=''
SUCCESS=1
printf '[prepare] marker: %s\n' "$MARKER"
printf 'PREPARE RESULT: PASS\n'
