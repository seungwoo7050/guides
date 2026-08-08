#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="unix-systems"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
STATE_TOOL="$ROOT/scripts/repository_state.py"
SUCCESS=0
TEMP_MARKER=''
TEMP_MARKER_ID=''
export GIT_OPTIONAL_LOCKS=0

die() { printf '[prepare] ERROR: %s\n' "$*" >&2; exit 1; }
require() { command -v "$1" >/dev/null 2>&1 || die "필수 명령이 없습니다: $1"; }
finish() {
    local status=$?
    trap - EXIT HUP INT TERM
    if [[ -n "$TEMP_MARKER" && ( -e "$TEMP_MARKER" || -L "$TEMP_MARKER" ) ]]; then
        if ! python3 - "$TEMP_MARKER" "$TEMP_MARKER_ID" <<'PY'
import os, stat, sys
path, expected = sys.argv[1:]
metadata = os.lstat(path)
actual = f"{metadata.st_dev}:{metadata.st_ino}"
if actual != expected or not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
    raise SystemExit(f"refusing to unlink replaced marker temp: {path}")
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
trap finish EXIT HUP INT TERM

for command_name in git bash python3 ps mktemp make; do require "$command_name"; done
[[ "$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null)" == "$ROOT" ]] || \
    die '독립 Git 저장소 루트가 아닙니다.'
bash -c '[[ -n ${BASH_VERSION:-} ]]' || die 'bash 기능 probe에 실패했습니다.'
MAKE_IDENTITY="$(make --version 2>&1)" || die 'make 기능 probe에 실패했습니다.'
[[ -n "$MAKE_IDENTITY" ]] || die 'make 기능 probe 결과가 비어 있습니다.'
MAKE_PROBE="$(printf 'probe:\n\t@printf "%%s\\n" GUIDE_MAKE_FUNCTIONAL\n' | \
    make -s -f - probe 2>&1)" || die 'make target 실행 probe에 실패했습니다.'
[[ "$MAKE_PROBE" == GUIDE_MAKE_FUNCTIONAL ]] || die 'make target 실행 probe 출력이 올바르지 않습니다.'
PS_PROBE="$(ps -p "$$" -o state= -o lstart= -o vsz= -o rss= -o command= 2>&1)" || \
    die "ps 기능 probe에 실패했습니다: $PS_PROBE"
[[ -n "$PS_PROBE" ]] || die 'ps 기능 probe 결과가 비어 있습니다.'
GUIDE_PS_PROBE="$PS_PROBE" python3 - <<'PY' || die 'ps 기능 probe 출력 형식이 요구사항과 다릅니다.'
import os
fields = os.environ["GUIDE_PS_PROBE"].strip().split(None, 8)
if len(fields) != 9 or not fields[6].isdigit() or not fields[7].isdigit() or not fields[8]:
    raise SystemExit(1)
PY
python3 - <<'PY' || die 'Python 3.12 이상이 필요합니다.'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

before_source="$(python3 "$STATE_TOOL" fingerprint --root "$ROOT")"
before_index="$(python3 "$STATE_TOOL" index --root "$ROOT")"
python3 "$ROOT/scripts/validate.py"
after_source="$(python3 "$STATE_TOOL" fingerprint --root "$ROOT")"
after_index="$(python3 "$STATE_TOOL" index --root "$ROOT")"
[[ "$before_source" == "$after_source" ]] || die 'prepare가 source tree를 변경했습니다.'
[[ "$before_index" == "$after_index" ]] || die 'prepare가 Git index를 변경했습니다.'

umask 077
[[ ! -L "$ROOT/.guide" ]] || die '.guide directory symlink를 허용하지 않습니다.'
[[ ! -e "$ROOT/.guide" || -d "$ROOT/.guide" ]] || die '.guide가 디렉터리가 아닙니다.'
mkdir -p -- "$ROOT/.guide"
[[ ! -L "$STATE_DIR" ]] || die '.guide/unix-systems directory symlink를 허용하지 않습니다.'
[[ ! -e "$STATE_DIR" || -d "$STATE_DIR" ]] || die '.guide/unix-systems가 디렉터리가 아닙니다.'
mkdir -p -- "$STATE_DIR"
[[ "$(cd -- "$STATE_DIR" && pwd -P)" == "$STATE_DIR" ]] || \
    die '준비 상태 디렉터리는 저장소 내부 실제 디렉터리여야 합니다.'
[[ ! -e "$MARKER" && ! -L "$MARKER" || ( -f "$MARKER" && ! -L "$MARKER" ) ]] || \
    die 'prepared marker는 일반 파일이거나 존재하지 않아야 합니다.'
created_marker="$(mktemp "$STATE_DIR/.prepared.XXXXXX")" || die 'marker 임시 파일을 만들지 못했습니다.'
created_parent="${created_marker%/*}"
created_name="${created_marker##*/}"
[[ "$created_parent" == "$STATE_DIR" && "$created_name" == .prepared.?????? ]] || \
    die 'marker 임시 파일이 sibling 경로가 아닙니다.'
[[ "$(cd -- "$created_parent" && pwd -P)" == "$STATE_DIR" ]] || \
    die 'marker 임시 파일의 실제 parent가 준비 상태 디렉터리가 아닙니다.'
[[ -f "$created_marker" && ! -L "$created_marker" ]] || die 'marker 임시 파일이 안전한 일반 파일이 아닙니다.'
created_marker_id="$(python3 - "$created_marker" <<'PY'
import os, stat, sys
metadata = os.lstat(sys.argv[1])
if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
    raise SystemExit(1)
print(f"{metadata.st_dev}:{metadata.st_ino}")
PY
)" || die 'marker 임시 파일 identity를 기록하지 못했습니다.'
TEMP_MARKER="$created_marker"
TEMP_MARKER_ID="$created_marker_id"

if [[ "${GUIDE_PREPARE_TEST_HOLD:-0}" == 1 ]]; then
    ready_file="${GUIDE_PREPARE_TEST_READY_FILE:-}"
    release_file="${GUIDE_PREPARE_TEST_RELEASE_FILE:-}"
    [[ "$ready_file" == /* && "$release_file" == /* ]] || \
        die 'prepare test hold 경로는 절대 경로여야 합니다.'
    [[ ! -e "$ready_file" && ! -L "$ready_file" ]] || die 'prepare test ready 파일이 이미 있습니다.'
    (set -C; printf '%s\n' "$$" > "$ready_file") || die 'prepare test ready 파일을 만들지 못했습니다.'
    while [[ ! -e "$release_file" ]]; do sleep 0.02; done
fi

GUIDE_ID="$GUIDE_ID" GUIDE_HEAD="$(git -C "$ROOT" rev-parse HEAD)" \
GUIDE_SOURCE="$after_source" GUIDE_INDEX="$after_index" \
GUIDE_GIT="$(git --version)" GUIDE_PYTHON="$(python3 --version 2>&1)" \
GUIDE_BASH="$BASH_VERSION" GUIDE_MAKE="$MAKE_IDENTITY" \
GUIDE_MKTEMP="$(command -v mktemp)" GUIDE_PS="$(command -v ps)" \
python3 - "$TEMP_MARKER" "$MARKER" <<'PY'
import json, os, platform, stat, sys
from pathlib import Path
payload = {
    "schema": 3,
    "guide_id": os.environ["GUIDE_ID"],
    "head": os.environ["GUIDE_HEAD"],
    "source_fingerprint": os.environ["GUIDE_SOURCE"],
    "index_fingerprint": os.environ["GUIDE_INDEX"],
    "platform": {
        "machine": platform.machine(),
        "platform": platform.platform(),
        "python_implementation": platform.python_implementation(),
        "system": platform.system(),
    },
    "tools": {
        "bash": os.environ["GUIDE_BASH"],
        "git": os.environ["GUIDE_GIT"],
        "make": os.environ["GUIDE_MAKE"],
        "mktemp": os.environ["GUIDE_MKTEMP"],
        "ps": os.environ["GUIDE_PS"],
        "python": os.environ["GUIDE_PYTHON"],
    },
}
temporary, marker = map(Path, sys.argv[1:])
nofollow = getattr(os, "O_NOFOLLOW", None)
if nofollow is None:
    raise SystemExit("O_NOFOLLOW를 지원하지 않는 플랫폼입니다.")
descriptor = os.open(temporary, os.O_WRONLY | nofollow)
try:
    path_state = os.lstat(temporary)
    descriptor_state = os.fstat(descriptor)
    if (not stat.S_ISREG(descriptor_state.st_mode) or descriptor_state.st_nlink != 1
            or (path_state.st_dev, path_state.st_ino) != (descriptor_state.st_dev, descriptor_state.st_ino)):
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
