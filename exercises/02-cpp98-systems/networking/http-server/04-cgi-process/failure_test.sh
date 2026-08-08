#!/usr/bin/env bash
set -euo pipefail

bin="${1:?}"
timeout_out="$(mktemp)"
timeout_err="$(mktemp)"
missing_out="$(mktemp)"
missing_err="$(mktemp)"
large_out="$(mktemp)"
large_err="$(mktemp)"
trap 'rm -f "$timeout_out" "$timeout_err" "$missing_out" "$missing_err" "$large_out" "$large_err"' EXIT

set +e
"$bin" ./helpers/slow_cgi.py 100 x >"$timeout_out" 2>"$timeout_err"
timeout_code=$?
set -e
[[ $timeout_code -eq 124 ]]
grep -F '제한 시간을 넘었습니다' "$timeout_err" >/dev/null

set +e
"$bin" ./helpers/missing 100 x >"$missing_out" 2>"$missing_err"
missing_code=$?
set -e
[[ $missing_code -ne 0 ]]

set +e
"$bin" ./helpers/large_cgi.py 1000 x >"$large_out" 2>"$large_err"
large_code=$?
set -e
[[ $large_code -ne 0 ]]
grep -F '출력 제한을 넘었습니다' "$large_err" >/dev/null

echo 'CGI 제한 시간·실행 실패·출력 제한 검사: 통과'
