#!/bin/sh
set -eu

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

printf 'echo hello\nhelp\nquit\n' | ./repl >"$tmp/out" 2>"$tmp/err"
printf 'hello\n명령: echo 문자열, help, history, quit\n' >"$tmp/expected"
cmp -s "$tmp/expected" "$tmp/out"
[ ! -s "$tmp/err" ]

printf 'bad\nquit\n' | ./repl >"$tmp/bad.out" 2>"$tmp/bad.err"
[ ! -s "$tmp/bad.out" ]
grep -q '^알 수 없는 명령입니다: bad$' "$tmp/bad.err"

echo 'readline-repl 기본 입력 검사: 통과'
