#!/bin/sh
set -eu

program=${1:?program path required}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

fail()
{
    printf 'textstat 검사 실패: %s\n' "$1" >&2
    exit 1
}

"$program" 'one two' >"$tmp/out" 2>"$tmp/err"
printf 'length=7\nwords=2\n' >"$tmp/expected"
diff -u "$tmp/expected" "$tmp/out" || fail '일반 입력 출력 불일치'
[ ! -s "$tmp/err" ] || fail '일반 입력이 stderr에 출력을 생성함'

"$program" '' >"$tmp/out" 2>"$tmp/err"
printf 'length=0\nwords=0\n' >"$tmp/expected"
diff -u "$tmp/expected" "$tmp/out" || fail '빈 문자열 출력 불일치'
[ ! -s "$tmp/err" ] || fail '빈 문자열이 stderr에 출력을 생성함'

set +e
"$program" >"$tmp/out" 2>"$tmp/err"
status=$?
set -e
[ "$status" -eq 2 ] || fail "사용법 상태 기대=2 실제=$status"
[ ! -s "$tmp/out" ] || fail '사용법 오류가 stdout에 출력을 생성함'
grep -F '사용법:' "$tmp/err" >/dev/null || fail '사용법 진단 누락'

printf 'textstat 검사 통과\n'
