#!/bin/sh
set -eu

usage()
{
    printf '%s\n' '사용법: ./scripts/new-workspace.sh exercises/<exercise>' >&2
    exit 2
}

[ "$#" -eq 1 ] || usage
exercise_relative=$1
case "$exercise_relative" in
    exercises/*) ;;
    *) usage ;;
esac
case "/$exercise_relative/" in
    *'/../'*|*'/./'*|*'//'*) usage ;;
esac

script_dir=$(CDPATH= cd "$(dirname "$0")" && pwd -P)
root=$(CDPATH= cd "$script_dir/.." && pwd -P)
publisher="$script_dir/atomic_directory_publish.py"
registry="$script_dir/exercises.txt"
files_manifest="$script_dir/workspace-files.txt"
grep -Fqx "$exercise_relative" "$registry" || {
    printf '등록되지 않은 실습입니다: %s\n' "$exercise_relative" >&2
    exit 2
}

exercise="$root/$exercise_relative"
[ -d "$exercise" ] && [ ! -L "$exercise" ] || {
    printf '실습 디렉터리가 없거나 symlink입니다: %s\n' "$exercise_relative" >&2
    exit 2
}
exercise_canonical=$(CDPATH= cd "$exercise" && pwd -P)
[ "$exercise_canonical" = "$exercise" ] || {
    printf '실습 경로가 저장소 밖으로 해석됩니다: %s\n' "$exercise_relative" >&2
    exit 2
}

skeleton="$exercise/skeleton"
workspace="$exercise/workspace"
lock="$exercise/.workspace-create.lock"
staging=
lock_held=0
actual=
expected=

[ -d "$skeleton" ] && [ ! -L "$skeleton" ] || {
    printf 'skeleton이 없거나 symlink입니다: %s\n' "$exercise_relative" >&2
    exit 2
}
[ -x "$publisher" ] || {
    printf '원자적 workspace 게시 도구가 없습니다.\n' >&2
    exit 2
}
if find "$skeleton" -type l -print -quit | grep -q .; then
    printf 'skeleton 안의 symlink는 복사하지 않습니다: %s\n' "$exercise_relative" >&2
    exit 2
fi
[ ! -e "$workspace" ] && [ ! -L "$workspace" ] || {
    printf '기존 workspace를 덮어쓰지 않습니다: %s\n' "$workspace" >&2
    exit 2
}

cleanup()
{
    [ -z "${actual:-}" ] || rm -f -- "$actual"
    [ -z "${expected:-}" ] || rm -f -- "$expected"
    [ -z "${staging:-}" ] || rm -rf -- "$staging"
    [ "$lock_held" -eq 0 ] || rmdir -- "$lock" 2>/dev/null || true
}
trap cleanup EXIT HUP INT TERM

actual=$(mktemp "${TMPDIR:-/tmp}/guide-cn-workspace-actual.XXXXXX")
expected=$(mktemp "${TMPDIR:-/tmp}/guide-cn-workspace-expected.XXXXXX")
find "$skeleton" -type f -print | while IFS= read -r path; do
    printf '%s\n' "${path#"$root/"}"
done | sort >"$actual"
prefix="$exercise_relative/skeleton/"
grep "^$prefix" "$files_manifest" | sort >"$expected" || true
cmp -s "$actual" "$expected" || {
    printf 'skeleton 파일 구성이 고정 manifest와 다릅니다: %s\n' "$exercise_relative" >&2
    exit 1
}

mkdir -- "$lock" 2>/dev/null || {
    printf '다른 workspace 생성이 진행 중입니다: %s\n' "$exercise_relative" >&2
    exit 2
}
lock_held=1
staging=$(mktemp -d "$exercise/.workspace-copy.XXXXXX")
copied=0
while IFS= read -r source_relative; do
    relative=${source_relative#"$prefix"}
    source="$root/$source_relative"
    destination="$staging/$relative"
    [ -f "$source" ] && [ ! -L "$source" ] || exit 1
    mkdir -p -- "$(dirname "$destination")"
    cp -p -- "$source" "$destination"
    copied=$((copied + 1))
    if [ "${GUIDE_WORKSPACE_TEST_INTERRUPT:-0}" = 1 ] && [ "$copied" -eq 1 ]; then
        printf '%s\n' '시험용 중단을 재현했습니다.' >&2
        exit 97
    fi
done <"$expected"
[ "$copied" -gt 0 ] || {
    printf '복사할 skeleton 파일이 없습니다: %s\n' "$exercise_relative" >&2
    exit 1
}
[ ! -e "$workspace" ] && [ ! -L "$workspace" ] || exit 2
if [ -n "${GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH:-}" ]; then
    sleep "$GUIDE_WORKSPACE_TEST_BEFORE_PUBLISH"
fi
python3 "$publisher" "$staging" "$workspace" || {
    printf 'workspace를 배타적으로 게시하지 못했습니다: %s\n' "$workspace" >&2
    exit 2
}
staging=
rmdir -- "$lock"
lock_held=0
rm -f -- "$actual" "$expected"
actual=
expected=
trap - EXIT HUP INT TERM
printf '작업 공간을 만들었습니다: %s\n' "$workspace"
