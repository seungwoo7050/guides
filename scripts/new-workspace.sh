#!/bin/sh
set -eu

fail() {
    printf 'workspace 생성 실패: %s\n' "$*" >&2
    exit 2
}

[ "$#" -eq 1 ] || fail '사용법: scripts/new-workspace.sh <exercise-directory>'

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
root=$(CDPATH='' cd -- "$script_dir/.." && pwd -P)
publisher=$script_dir/atomic_directory_publish.py
requested=$1
[ -d "$requested" ] || fail "실습 디렉터리가 없습니다: $requested"
exercise=$(CDPATH='' cd -- "$requested" && pwd -P)
case "$exercise" in
    "$root"/exercises/*) ;;
    *) fail "저장소 exercises 밖의 경로입니다: $requested" ;;
esac

skeleton=$exercise/skeleton
workspace=$exercise/workspace
lock=$exercise/.workspace-create.lock
staging=
lock_held=0
lock_acquiring=0
pending_signal=0

[ -d "$skeleton" ] && [ ! -L "$skeleton" ] || fail '일반 skeleton 디렉터리가 필요합니다'
[ -x "$publisher" ] || fail '원자적 workspace 게시 도구가 없습니다'
[ ! -e "$workspace" ] && [ ! -L "$workspace" ] || fail "기존 workspace를 덮어쓰지 않습니다: $workspace"

if find "$skeleton" -type l -print -quit | grep -q .; then
    fail 'skeleton 안의 심볼릭 링크는 복사하지 않습니다'
fi
if ! find "$skeleton" -type f -print -quit | grep -q .; then
    fail 'skeleton에 복사할 일반 파일이 없습니다'
fi

cleanup() {
    [ -z "${staging:-}" ] || rm -rf -- "$staging"
    [ "$lock_held" -eq 0 ] || rmdir -- "$lock" 2>/dev/null || true
}
stop_on_signal() {
    code=$1
    if [ "$lock_acquiring" -eq 1 ]; then
        pending_signal=$code
        return 0
    fi
    trap - EXIT HUP INT TERM
    cleanup
    exit "$code"
}
trap cleanup EXIT
trap 'stop_on_signal 129' HUP
trap 'stop_on_signal 130' INT
trap 'stop_on_signal 143' TERM

lock_acquiring=1
if sh -c 'trap "" HUP INT TERM; exec mkdir -- "$1"' _ "$lock" 2>/dev/null; then
    if [ -n "${GUIDE_WORKSPACE_TEST_AFTER_LOCK_MKDIR:-}" ]; then
        sleep "$GUIDE_WORKSPACE_TEST_AFTER_LOCK_MKDIR" || :
    fi
    lock_held=1
    lock_acquired=1
else
    lock_acquired=0
fi
lock_acquiring=0
if [ "$pending_signal" -ne 0 ]; then
    stop_on_signal "$pending_signal"
fi
[ "$lock_acquired" -eq 1 ] || fail '다른 workspace 생성 작업이 진행 중입니다'
if [ -n "${GUIDE_WORKSPACE_TEST_PAUSE:-}" ]; then
    sleep "$GUIDE_WORKSPACE_TEST_PAUSE"
fi
staging=$(mktemp -d "$exercise/.workspace-copy.XXXXXX")

(cd "$skeleton" && find . -type d -print | sort) | while IFS= read -r directory; do
    mkdir -p -- "$staging/$directory"
done
(cd "$skeleton" && find . -type f -print | sort) | while IFS= read -r source; do
    cp -p -- "$skeleton/$source" "$staging/$source"
done

[ ! -e "$workspace" ] && [ ! -L "$workspace" ] || fail "기존 workspace를 덮어쓰지 않습니다: $workspace"
if [ -n "${GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH:-}" ]; then
    sleep "$GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH"
fi
python3 "$publisher" "$staging" "$workspace" || fail 'workspace를 배타적으로 게시하지 못했습니다'
staging=
rmdir -- "$lock"
lock_held=0
trap - EXIT HUP INT TERM
printf 'workspace를 만들었습니다: %s\n' "$workspace"
