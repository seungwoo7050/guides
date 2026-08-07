#!/bin/sh
set -eu

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

./textstat 'hello world' l >"$tmp/out" 2>"$tmp/err"
printf 'length: 11\ncount: 3\n' >"$tmp/expected"
cmp -s "$tmp/expected" "$tmp/out"
[ ! -s "$tmp/err" ]

if ./textstat >"$tmp/bad.out" 2>"$tmp/bad.err"
then
    echo '잘못된 호출이 성공으로 끝났습니다' >&2
    exit 1
fi
[ ! -s "$tmp/bad.out" ]
grep -q '^사용법:' "$tmp/bad.err"

echo 'textkit 기본 검사: 통과'
