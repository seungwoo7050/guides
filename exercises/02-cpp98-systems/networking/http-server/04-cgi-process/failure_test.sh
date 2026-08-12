#!/usr/bin/env bash
set -euo pipefail

bin="${1:?}"
temporary="$(mktemp -d "${TMPDIR:-/tmp}/guide-cpp-cgi-failure.XXXXXX")"
trap 'rm -rf "$temporary"' EXIT HUP INT TERM
timeout_out="$temporary/timeout.out"
timeout_err="$temporary/timeout.err"
missing_out="$temporary/missing.out"
missing_err="$temporary/missing.err"
large_out="$temporary/large.out"
large_err="$temporary/large.err"

fail_case()
{
    name=$1
    code=$2
    error_file=$3
    printf 'CGI failure case failed: %s (exit=%s)\n' "$name" "$code" >&2
    if [[ -s $error_file ]]; then
        sed 's/^/stderr: /' "$error_file" >&2
    fi
    exit 1
}

set +e
"$bin" ./helpers/slow_cgi.py 100 x >"$timeout_out" 2>"$timeout_err"
timeout_code=$?
set -e
[[ $timeout_code -eq 124 ]] \
    || fail_case timeout "$timeout_code" "$timeout_err"
grep -F '제한 시간을 넘었습니다' "$timeout_err" >/dev/null \
    || fail_case timeout-message "$timeout_code" "$timeout_err"

set +e
"$bin" ./helpers/missing 100 x >"$missing_out" 2>"$missing_err"
missing_code=$?
set -e
[[ $missing_code -ne 0 ]] \
    || fail_case missing-executable "$missing_code" "$missing_err"

set +e
# This case measures the output cap, not scheduler speed. Keep its deadline
# comfortably above the 2-second timeout fixture so a loaded matrix cannot
# misclassify a valid output-limit result as a timing failure.
"$bin" ./helpers/large_cgi.py 10000 x >"$large_out" 2>"$large_err"
large_code=$?
set -e
[[ $large_code -ne 0 ]] \
    || fail_case output-limit "$large_code" "$large_err"
grep -F '출력 제한을 넘었습니다' "$large_err" >/dev/null \
    || fail_case output-limit-message "$large_code" "$large_err"

echo 'CGI 제한 시간·실행 실패·출력 제한 검사: 통과'
