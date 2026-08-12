#!/bin/sh
set -eu

fail()
{
    printf 'new-workspace: %s\n' "$*" >&2
    exit 1
}

publish_no_replace()
{
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
    function.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint
    ]
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
raw=${1:-}
[ -n "$raw" ] || fail '사용법: scripts/new-workspace.sh exercises/<part>/<exercise>'

case "$raw" in
    exercises/*) ;;
    *) fail "exercises/ 아래의 상대 경로만 허용합니다: $raw" ;;
esac
case "/$raw/" in
    *'/../'*|*'/./'*) fail "경로 순회 표기를 허용하지 않습니다: $raw" ;;
esac

expected="$root/$raw"
[ -d "$expected" ] || fail "연습문제 디렉터리가 없습니다: $raw"
[ ! -L "$expected" ] || fail "연습문제 symlink를 허용하지 않습니다: $raw"
exercise=$(CDPATH= cd -- "$expected" && pwd -P)
[ "$exercise" = "$expected" ] || fail "symlink가 포함된 연습문제 경로를 허용하지 않습니다: $raw"

for required in README.md Makefile skeleton reference tests
do
    [ -e "$exercise/$required" ] || fail "연습문제 구성요소가 없습니다: $raw/$required"
done

source_dir="$exercise/skeleton"
target_dir="$exercise/workspace"
lock_dir="$exercise/.workspace.lock"
temporary=
lock_held=0

[ -d "$source_dir" ] && [ ! -L "$source_dir" ] || fail 'skeleton은 실제 디렉터리여야 합니다.'
[ -z "$(find "$source_dir" -type l -print -quit)" ] || fail 'skeleton 내부 symlink를 복사하지 않습니다.'
[ ! -e "$target_dir" ] && [ ! -L "$target_dir" ] || fail "기존 workspace를 덮어쓰지 않습니다: $target_dir"

cleanup()
{
    status=$?
    trap - EXIT HUP INT TERM
    if [ -n "$temporary" ] && [ -d "$temporary" ] && [ ! -L "$temporary" ]; then
        rm -rf -- "$temporary"
    fi
    if [ "$lock_held" -eq 1 ]; then
        rmdir -- "$lock_dir" 2>/dev/null || true
    fi
    exit "$status"
}
trap cleanup EXIT HUP INT TERM

mkdir -- "$lock_dir" 2>/dev/null || fail '다른 workspace 생성 작업이 진행 중이거나 stale lock이 있습니다.'
lock_held=1
[ ! -e "$target_dir" ] && [ ! -L "$target_dir" ] || fail "lock 획득 중 workspace가 생성되었습니다: $target_dir"

temporary=$(mktemp -d "$exercise/.workspace.tmp.XXXXXX") || fail '임시 workspace를 만들 수 없습니다.'
cp -R "$source_dir/." "$temporary/"
[ ! -e "$target_dir" ] && [ ! -L "$target_dir" ] || fail "publish 직전에 workspace가 생성되었습니다: $target_dir"
publish_no_replace "$temporary" "$target_dir"
temporary=
rmdir -- "$lock_dir"
lock_held=0
trap - EXIT HUP INT TERM

printf '작업 공간을 만들었습니다: %s\n' "$target_dir"
