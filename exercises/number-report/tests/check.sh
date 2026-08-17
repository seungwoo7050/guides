#!/bin/sh
set -eu

program=${1:?program path required}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

fail()
{
    printf 'number-report test failed: %s\n' "$1" >&2
    exit 1
}

run_status()
{
    expected=$1
    shift
    set +e
    "$program" "$@" >"$tmp/out" 2>"$tmp/err"
    actual=$?
    set -e
    [ "$actual" -eq "$expected" ] \
        || fail "expected status=$expected actual=$actual arguments=$*"
}

expect_success()
{
    expected_file=$1
    shift
    run_status 0 "$@"
    diff -u "$expected_file" "$tmp/out" || fail "output mismatch: $*"
    [ ! -s "$tmp/err" ] || fail "successful input wrote to stderr: $*"
}

cat >"$tmp/expected-main" <<'EXPECTED'
count=5
minimum=-3
maximum=42
sum=65
average=13.00
even=4
odd=1
EXPECTED
expect_success "$tmp/expected-main" 10 -3 8 8 42

cat >"$tmp/expected-single" <<'EXPECTED'
count=1
minimum=7
maximum=7
sum=7
average=7.00
even=0
odd=1
EXPECTED
expect_success "$tmp/expected-single" 7

cat >"$tmp/expected-syntax-valid" <<'EXPECTED'
count=4
minimum=-1
maximum=3
sum=4
average=1.00
even=2
odd=2
EXPECTED
expect_success "$tmp/expected-syntax-valid" 0 -1 +2 0003

for bad in 12x '' ' 12' '12 ' + - 0x10 1.0 '1_000'; do
    run_status 2 "$bad"
    [ ! -s "$tmp/out" ] || fail "invalid input wrote to stdout: <$bad>"
    grep -F 'Error:' "$tmp/err" >/dev/null || fail "missing diagnostic: <$bad>"
done

run_status 2
[ ! -s "$tmp/out" ] || fail 'missing arguments wrote to stdout'
grep -F 'Usage:' "$tmp/err" >/dev/null || fail 'missing usage diagnostic'

run_status 2 999999999999999999999999999999999999
[ ! -s "$tmp/out" ] || fail 'out-of-range input wrote to stdout'
grep -F 'Error:' "$tmp/err" >/dev/null || fail 'missing out-of-range diagnostic'

long_max=$(python3 - <<'PY'
import ctypes
bits = ctypes.sizeof(ctypes.c_long) * 8
print((1 << (bits - 1)) - 1)
PY
)
long_min=$(python3 - <<'PY'
import ctypes
bits = ctypes.sizeof(ctypes.c_long) * 8
print(-(1 << (bits - 1)))
PY
)

run_status 0 "$long_max"
grep -Fx "sum=$long_max" "$tmp/out" >/dev/null || fail 'LONG_MAX sum mismatch'
run_status 0 "$long_min"
grep -Fx "sum=$long_min" "$tmp/out" >/dev/null || fail 'LONG_MIN sum mismatch'
run_status 0 "$long_max" "$long_min"
grep -Fx 'sum=-1' "$tmp/out" >/dev/null || fail 'boundary cancellation mismatch'

run_status 3 "$long_max" 1
[ ! -s "$tmp/out" ] || fail 'positive overflow wrote to stdout'
grep -F 'exceeds the range' "$tmp/err" >/dev/null || fail 'missing positive overflow diagnostic'
run_status 3 "$long_min" -1
[ ! -s "$tmp/out" ] || fail 'negative overflow wrote to stdout'
grep -F 'exceeds the range' "$tmp/err" >/dev/null || fail 'missing negative overflow diagnostic'

printf 'number-report tests passed\n'
