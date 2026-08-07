#!/bin/sh
set -eu

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

./account_simulator 8 8 5000 >"$tmp/out" 2>"$tmp/err"
[ ! -s "$tmp/err" ]
awk '
    /^initial=[0-9]+ final=[0-9]+ completed=[0-9]+ elapsed_ms=[0-9]+$/ {
        split($1, a, "=")
        split($2, b, "=")
        if (a[2] == b[2]) ok = 1
    }
    END { exit !ok }
' "$tmp/out"

set +e
BANK_FAIL_AFTER=2 ./account_simulator 4 4 100 >"$tmp/fail.out" 2>"$tmp/fail.err"
status=$?
set -e
[ "$status" -ne 0 ]
grep -q '^2번 작업자 스레드를 만들지 못했습니다:' "$tmp/fail.err"

echo 'account-simulator 검사: 통과'
