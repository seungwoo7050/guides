#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_OPTIONAL_LOCKS=0
IFS=$'\n\t'

GUIDE_ID="computer-architecture"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
STATE_ROOT="$ROOT/.guide"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
STATE_FILE="$STATE_DIR/prepared.json"
PROBE_DIR=""
STATE_TEMP=""
STATE_CANDIDATE=""
SUCCESS=0
FINISHED=0

log() { printf '[prepare] %s\n' "$*"; }
die() { printf '[prepare] ERROR: %s\n' "$*" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || die "$1 명령이 필요합니다."; }

cleanup() {
    [[ -z "$PROBE_DIR" ]] || rm -rf -- "$PROBE_DIR"
    cleanup_state_candidate
    [[ -z "$STATE_TEMP" ]] || rm -f -- "$STATE_TEMP"
}

finish() {
    local status=$?
    (( FINISHED == 0 )) || exit "$status"
    FINISHED=1
    trap - EXIT HUP INT TERM
    cleanup
    if (( status != 0 || SUCCESS != 1 )); then
        printf 'PREPARE RESULT: FAIL\n' >&2
        (( status == 0 )) && status=1
        exit "$status"
    fi
    printf 'PREPARE RESULT: PASS\n'
}

ensure_state_directory() {
    [[ ! -L "$STATE_ROOT" ]] || die '.guide 상태 루트에 symbolic link를 사용할 수 없습니다.'
    if [[ ! -e "$STATE_ROOT" ]]; then
        mkdir -- "$STATE_ROOT" || die '.guide 상태 루트를 만들 수 없습니다.'
    fi
    [[ -d "$STATE_ROOT" && ! -L "$STATE_ROOT" ]] || die '.guide 상태 루트는 실제 directory여야 합니다.'
    [[ ! -L "$STATE_DIR" ]] || die '가이드 상태 경로에 symbolic link를 사용할 수 없습니다.'
    if [[ ! -e "$STATE_DIR" ]]; then
        mkdir -- "$STATE_DIR" || die '가이드 상태 directory를 만들 수 없습니다.'
    fi
    [[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]] || die '가이드 상태 경로는 실제 directory여야 합니다.'
}

cleanup_state_candidate() {
    [[ -n "$STATE_CANDIDATE" ]] || return 0
    python3 - "$ROOT" "$GUIDE_ID" "$STATE_CANDIDATE" <<'PY' >/dev/null 2>&1 || true
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
guide_id = sys.argv[2]
candidate = Path(sys.argv[3])
if candidate.parent != root / ".guide" / guide_id or candidate.name in {"", ".", "..", "prepared.json"}:
    raise SystemExit(0)
flags = os.O_RDONLY
if hasattr(os, "O_DIRECTORY"):
    flags |= os.O_DIRECTORY
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
descriptors = []
try:
    root_fd = os.open(root, flags)
    descriptors.append(root_fd)
    state_fd = os.open(".guide", flags, dir_fd=root_fd)
    descriptors.append(state_fd)
    guide_fd = os.open(guide_id, flags, dir_fd=state_fd)
    descriptors.append(guide_fd)
    metadata = os.stat(candidate.name, dir_fd=guide_fd, follow_symlinks=False)
    if (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_nlink == 1
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
    ):
        os.unlink(candidate.name, dir_fd=guide_fd)
        os.fsync(guide_fd)
except OSError:
    pass
finally:
    for descriptor in reversed(descriptors):
        os.close(descriptor)
PY
}

trap finish EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

index_fingerprint() {
    local index_path
    index_path="$(git -C "$ROOT" rev-parse --git-path index)"
    [[ "$index_path" == /* ]] || index_path="$ROOT/$index_path"
    python3 - "$index_path" <<'PY'
import hashlib
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing")
PY
}

cd "$ROOT"
for command in git python3 make cc bash rsync sed; do require_command "$command"; done
python3 - <<'PY' || die "Python 3.12 이상이 필요합니다."
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY

top_level="$(git rev-parse --show-toplevel 2>/dev/null)" || die "Git 저장소에서 실행해야 합니다."
[[ "$(cd "$top_level" && pwd -P)" == "$ROOT" ]] || die "저장소 루트에서 실행해야 합니다."
[[ -f docs/00-roadmap.md && -f exercises/processor-model/spec/tiny-risc-isa.md ]] \
    || die "최종 가이드 구조가 불완전합니다."
ensure_state_directory

before_source="$(python3 scripts/tree-fingerprint.py "$ROOT")"
before_index="$(index_fingerprint)"
PROBE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-architecture-prepare.XXXXXX")" \
    || die "compiler probe 디렉터리를 만들지 못했습니다."
cat > "$PROBE_DIR/probe.c" <<'C'
#define _POSIX_C_SOURCE 200809L
#include <pthread.h>
#include <time.h>
static void *worker(void *value) { return value; }
int main(void) {
    pthread_t thread;
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) return 2;
    if (pthread_create(&thread, 0, worker, 0) != 0) return 3;
    return pthread_join(thread, 0);
}
C
cc -std=c11 -Wall -Wextra -Werror -pedantic "$PROBE_DIR/probe.c" -pthread -o "$PROBE_DIR/probe" \
    || die "C11·POSIX thread compiler probe가 실패했습니다."
"$PROBE_DIR/probe" || die "C11·POSIX thread 실행 probe가 실패했습니다."
cc -std=c11 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined \
    -fno-omit-frame-pointer "$PROBE_DIR/probe.c" -pthread -o "$PROBE_DIR/probe-sanitize" \
    || die "AddressSanitizer·UndefinedBehaviorSanitizer가 필요합니다."
ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 "$PROBE_DIR/probe-sanitize" \
    || die "sanitizer 실행 probe가 실패했습니다."
mkdir -p "$PROBE_DIR/rsync-source" "$PROBE_DIR/rsync-destination"
printf 'rsync functional probe\n' > "$PROBE_DIR/rsync-source/value.txt"
chmod 640 "$PROBE_DIR/rsync-source/value.txt"
ln -s value.txt "$PROBE_DIR/rsync-source/value-link"
rsync -a "$PROBE_DIR/rsync-source/" "$PROBE_DIR/rsync-destination/" \
    || die "rsync 실행 probe가 실패했습니다."
python3 - "$PROBE_DIR/rsync-destination" <<'PY' || die "rsync bytes·mode·symlink probe가 실패했습니다."
import os
from pathlib import Path
import stat
import sys
root = Path(sys.argv[1])
value = root / "value.txt"
link = root / "value-link"
raise SystemExit(
    0 if value.read_bytes() == b"rsync functional probe\n"
    and stat.S_IMODE(value.stat().st_mode) == 0o640
    and link.is_symlink() and os.readlink(link) == "value.txt" else 1
)
PY
printf 'probe:\n\t@:\n' | make -s -f - probe || die "make 실행 probe가 실패했습니다."

after_source="$(python3 scripts/tree-fingerprint.py "$ROOT")"
after_index="$(index_fingerprint)"
[[ "$before_source" == "$after_source" ]] || die "prepare가 source tree를 변경했습니다."
[[ "$before_index" == "$after_index" ]] || die "prepare가 Git index를 변경했습니다."

umask 077
STATE_CANDIDATE="$(mktemp "$STATE_DIR/.prepared.XXXXXX")" \
    || die "준비 상태 임시 파일을 만들지 못했습니다."
python3 - "$STATE_DIR" "$STATE_CANDIDATE" <<'PY' \
    || die "mktemp가 안전한 marker sibling을 만들지 못했습니다."
import os
from pathlib import Path
import stat
import sys

expected_parent = Path(sys.argv[1])
candidate = Path(sys.argv[2])
if candidate.parent != expected_parent or candidate.name in {"", ".", "..", "prepared.json"}:
    raise SystemExit("marker candidate가 expected state directory의 sibling이 아닙니다")
metadata = candidate.lstat()
if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
    raise SystemExit("marker candidate는 link가 없는 regular file이어야 합니다")
if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
    raise SystemExit("marker candidate의 owner 또는 mode가 안전하지 않습니다")
PY
STATE_TEMP="$STATE_CANDIDATE"
STATE_CANDIDATE=""
GUIDE_ID="$GUIDE_ID" SOURCE_FINGERPRINT="$after_source" INDEX_FINGERPRINT="$after_index" \
HEAD_COMMIT="$(git rev-parse HEAD)" PYTHON_VERSION="$(python3 -c 'import platform; print(platform.python_version())')" \
GIT_VERSION="$(git --version)" MAKE_VERSION="$(make --version | sed -n '1p')" \
CC_VERSION="$(cc --version 2>/dev/null | sed -n '1p')" \
RSYNC_VERSION="$(rsync --version | sed -n '1p')" \
python3 - "$STATE_TEMP" <<'PY'
import json
import os
import stat
import sys
payload = {
    "schema_version": 1,
    "guide_id": os.environ["GUIDE_ID"],
    "head_commit": os.environ["HEAD_COMMIT"],
    "source_fingerprint": os.environ["SOURCE_FINGERPRINT"],
    "index_fingerprint": os.environ["INDEX_FINGERPRINT"],
    "python_version": os.environ["PYTHON_VERSION"],
    "git_version": os.environ["GIT_VERSION"],
    "make_version": os.environ["MAKE_VERSION"],
    "compiler_version": os.environ["CC_VERSION"],
    "rsync_version": os.environ["RSYNC_VERSION"],
    "c11_posix_threads": True,
    "asan_ubsan": True,
}
data = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
flags = os.O_WRONLY | os.O_TRUNC
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
descriptor = os.open(sys.argv[1], flags)
try:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise RuntimeError("marker 임시 파일은 link가 없는 regular file이어야 합니다")
    os.fchmod(descriptor, 0o600)
    view = memoryview(data)
    while view:
        view = view[os.write(descriptor, view):]
    os.fsync(descriptor)
finally:
    os.close(descriptor)
PY
python3 - "$ROOT" "$GUIDE_ID" "$STATE_TEMP" <<'PY'
import os
from pathlib import Path
import stat
import sys

root = Path(sys.argv[1])
guide_id = sys.argv[2]
temporary = Path(sys.argv[3])
if temporary.parent != root / ".guide" / guide_id or temporary.name == "prepared.json":
    raise SystemExit("marker 임시 경로가 안전한 sibling이 아닙니다")
flags = os.O_RDONLY
if hasattr(os, "O_DIRECTORY"):
    flags |= os.O_DIRECTORY
if hasattr(os, "O_NOFOLLOW"):
    flags |= os.O_NOFOLLOW
root_fd = os.open(root, flags)
state_fd = guide_fd = None
try:
    state_fd = os.open(".guide", flags, dir_fd=root_fd)
    guide_fd = os.open(guide_id, flags, dir_fd=state_fd)
    metadata = os.stat(temporary.name, dir_fd=guide_fd, follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise RuntimeError("marker 임시 파일은 link가 없는 regular file이어야 합니다")
    if stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_uid != os.geteuid():
        raise RuntimeError("marker 임시 파일의 mode 또는 owner가 안전하지 않습니다")
    os.replace(temporary.name, "prepared.json", src_dir_fd=guide_fd, dst_dir_fd=guide_fd)
    os.fsync(guide_fd)
finally:
    if guide_fd is not None:
        os.close(guide_fd)
    if state_fd is not None:
        os.close(state_fd)
    os.close(root_fd)
PY
STATE_TEMP=""
SUCCESS=1
log "준비 상태: $STATE_FILE"
