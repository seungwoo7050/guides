#!/bin/sh
set -eu

program=${1:?program path required}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

fail()
{
    printf 'number-report 검사 실패: %s\n' "$1" >&2
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
        || fail "종료 상태 기대=$expected 실제=$actual 인자=$*"
}

expect_success()
{
    expected_file=$1
    shift
    run_status 0 "$@"
    diff -u "$expected_file" "$tmp/out" || fail "정상 출력 불일치: $*"
    [ ! -s "$tmp/err" ] || fail "정상 입력이 stderr에 출력을 생성함: $*"
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

cat >"$tmp/expected-cancel" <<'EXPECTED'
count=3
minimum=-10
maximum=10
sum=0
average=0.00
even=3
odd=0
EXPECTED
expect_success "$tmp/expected-cancel" 10 -10 0

for bad in 12x '' ' 12' '12 ' + - 0x10 1.0 '1_000'; do
    run_status 2 "$bad"
    [ ! -s "$tmp/out" ] || fail "잘못된 입력이 stdout에 출력을 생성함: <$bad>"
    grep -F '오류:' "$tmp/err" >/dev/null || fail "진단 누락: <$bad>"
done

run_status 2
[ ! -s "$tmp/out" ] || fail '인자 없음이 stdout에 출력을 생성함'
grep -F '사용법:' "$tmp/err" >/dev/null || fail '사용법 누락'

run_status 2 999999999999999999999999999999999999
[ ! -s "$tmp/out" ] || fail '범위 밖 입력이 stdout에 출력을 생성함'
grep -F '오류:' "$tmp/err" >/dev/null || fail '범위 밖 입력 진단 누락'

long_max=$(python3 - <<'PY_INNER'
import ctypes
bits = ctypes.sizeof(ctypes.c_long) * 8
print((1 << (bits - 1)) - 1)
PY_INNER
)
long_min=$(python3 - <<'PY_INNER'
import ctypes
bits = ctypes.sizeof(ctypes.c_long) * 8
print(-(1 << (bits - 1)))
PY_INNER
)

run_status 0 "$long_max"
[ ! -s "$tmp/err" ] || fail 'LONG_MAX 단일 입력이 stderr에 출력을 생성함'
grep -Fx "minimum=$long_max" "$tmp/out" >/dev/null \
    || fail 'LONG_MAX minimum 출력 불일치'
grep -Fx "sum=$long_max" "$tmp/out" >/dev/null \
    || fail 'LONG_MAX sum 출력 불일치'

run_status 0 "$long_min"
[ ! -s "$tmp/err" ] || fail 'LONG_MIN 단일 입력이 stderr에 출력을 생성함'
grep -Fx "minimum=$long_min" "$tmp/out" >/dev/null \
    || fail 'LONG_MIN minimum 출력 불일치'
grep -Fx "sum=$long_min" "$tmp/out" >/dev/null \
    || fail 'LONG_MIN sum 출력 불일치'

run_status 0 "$long_max" "$long_min"
[ ! -s "$tmp/err" ] || fail '경계 상쇄 입력이 stderr에 출력을 생성함'
grep -Fx 'sum=-1' "$tmp/out" >/dev/null \
    || fail 'LONG_MAX + LONG_MIN 합 불일치'

run_status 3 "$long_max" 1
[ ! -s "$tmp/out" ] || fail '양수 합 overflow가 stdout에 출력을 생성함'
grep -F '범위를 넘습니다' "$tmp/err" >/dev/null \
    || fail '양수 합 overflow 진단 누락'

run_status 3 "$long_min" -1
[ ! -s "$tmp/out" ] || fail '음수 합 overflow가 stdout에 출력을 생성함'
grep -F '범위를 넘습니다' "$tmp/err" >/dev/null \
    || fail '음수 합 overflow 진단 누락'

printf 'number-report 검사 통과\n'
