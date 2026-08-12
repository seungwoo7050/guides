#!/bin/sh
set -eu

temporary=$(mktemp -d "${TMPDIR:-/tmp}/guide-c-fd-redirection.XXXXXX")
trap 'rm -rf -- "$temporary"' EXIT HUP INT TERM
output="$temporary/output.txt"

./fd_redirection truncate "$output" sh -c 'printf first'
[ "$(cat "$output")" = first ]

./fd_redirection append "$output" sh -c 'printf second'
[ "$(cat "$output")" = firstsecond ]

set +e
./fd_redirection truncate "$output" command-that-does-not-exist-guide-c \
    >"$temporary/stdout" 2>"$temporary/stderr"
status=$?
set -e
[ "$status" -eq 127 ]
[ ! -s "$temporary/stdout" ]
[ -s "$temporary/stderr" ]

set +e
./fd_redirection invalid "$output" sh -c ':' >"$temporary/usage.out" 2>"$temporary/usage.err"
status=$?
set -e
[ "$status" -eq 2 ]
[ ! -s "$temporary/usage.out" ]
grep -q '^사용법:' "$temporary/usage.err"

printf '%s\n' 'fd-redirection 검사: 통과'
