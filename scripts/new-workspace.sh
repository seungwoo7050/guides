#!/bin/sh
set -eu

fail() {
    printf 'new-workspace: %s\n' "$*" >&2
    exit 1
}

publish_no_replace() {
    python3 - "$1" "$2" <<'PY'
import ctypes
import os
import sys

source, destination = map(os.fsencode, sys.argv[1:])
libc = ctypes.CDLL(None, use_errno=True)
if sys.platform == "darwin":
    function = libc.renamex_np
    function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    status = function(source, destination, 0x00000004)
elif sys.platform.startswith("linux"):
    function = libc.renameat2
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    status = function(-100, source, -100, destination, 0x00000001)
else:
    raise SystemExit(f"exclusive atomic publish를 지원하지 않는 플랫폼입니다: {sys.platform}")
if status:
    error = ctypes.get_errno()
    raise OSError(error, os.strerror(error), os.fsdecode(destination))
PY
}

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
exercise="$root/exercises/model-lifecycle"
source_dir="$exercise/skeleton"
target_dir="$exercise/workspace"
lock_dir="$exercise/.workspace.lock"
temporary=''
lock_held=0

[ -d "$source_dir" ] || fail "skeleton/이 없습니다: $source_dir"
[ ! -L "$root/exercises" ] && [ ! -L "$exercise" ] && [ ! -L "$source_dir" ] || \
    fail '실습 경로의 symlink component를 허용하지 않습니다.'
[ -z "$(find "$source_dir" -type l -print -quit)" ] || \
    fail 'skeleton 내부 symlink를 복사하지 않습니다.'
[ ! -e "$target_dir" ] && [ ! -L "$target_dir" ] || \
    fail "기존 workspace 또는 symlink를 덮어쓰지 않습니다: $target_dir"

cleanup() {
    status=$?
    trap - EXIT HUP INT TERM
    if [ -n "$temporary" ] && [ -d "$temporary" ]; then
        rm -rf -- "$temporary"
    fi
    if [ "$lock_held" -eq 1 ]; then
        rmdir -- "$lock_dir" 2>/dev/null || true
    fi
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

mkdir -- "$lock_dir" 2>/dev/null || fail '다른 workspace 생성 작업이 진행 중이거나 stale lock이 있습니다.'
lock_held=1
[ ! -e "$target_dir" ] && [ ! -L "$target_dir" ] || \
    fail "lock 획득 중 생성된 workspace를 덮어쓰지 않습니다: $target_dir"

temporary=$(mktemp -d "$exercise/.workspace.tmp.XXXXXX") || fail '임시 작업 공간을 만들 수 없습니다.'
cp -R "$source_dir/." "$temporary/"

[ ! -e "$target_dir" ] && [ ! -L "$target_dir" ] || \
    fail "완성 직전에 발견한 workspace를 덮어쓰지 않습니다: $target_dir"
publish_no_replace "$temporary" "$target_dir"
temporary=''
rmdir -- "$lock_dir"
lock_held=0
trap - EXIT HUP INT TERM

printf '작업 공간을 만들었습니다: %s\n' "$target_dir"
