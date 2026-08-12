#!/bin/sh
set -eu

# [Implementation 1] 임시 경로 안에 stdout, stderr와 상태별 evidence를 분리해 원본 fixture를 바꾸지 않습니다.
tmp=$(mktemp -d "${TMPDIR:-/tmp}/guide-c-text-checks.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

set +e
./src/loggen.sh >"$tmp/usage.out" 2>"$tmp/usage.err"
status=$?
set -e
[ "$status" -eq 2 ]
[ ! -s "$tmp/usage.out" ]
printf '사용법: ./src/loggen.sh ok|bad-format|duplicate|error\n' >"$tmp/usage.expected"
cmp -s "$tmp/usage.expected" "$tmp/usage.err"

# [Implementation 2] exact cmp와 readable diff는 같은 예상 결과를 서로 다른 실패 표현으로 확인합니다.
./src/loggen.sh ok >"$tmp/ok"
cat >"$tmp/expected" <<'EOT'
100 1 start
105 2 start
120 1 work
130 1 done
140 2 work
150 2 done
EOT
diff -u "$tmp/expected" "$tmp/ok"

# [Implementation 3] grep은 한 줄 계약을, sed 뒤 grep은 비본질적 timestamp를 제거한 계약을 확인합니다.
grep -q '^100 1 start$' "$tmp/ok"
if grep -q 'error' "$tmp/ok"; then
    echo '정상 출력에 오류 문구가 포함되었습니다' >&2
    exit 1
fi

sed 's/^[0-9][0-9]* //' "$tmp/ok" >"$tmp/normalized"
grep -q '^1 done$' "$tmp/normalized"

# [Implementation 4] awk 상태는 id별 done 이후 사건 금지와 최종 완료 불변식을 전체 stream에 걸쳐 소유합니다.
validate()
{
    awk '
        !/^[0-9]+ [1-9][0-9]* (start|work|done)$/ {
            printf "%d번째 줄의 형식이 올바르지 않습니다: %s\n", NR, $0 > "/dev/stderr"
            bad = 1
            next
        }
        {
            id = $2
            state = $3
            if (finished[id]) {
                printf "%d번째 줄: id %s의 done 뒤에 이벤트가 이어졌습니다\n", NR, id > "/dev/stderr"
                bad = 1
            }
            if (state == "done") finished[id] = 1
            seen[id] = 1
        }
        END {
            if (NR == 0) bad = 1
            for (id in seen) if (!finished[id]) bad = 1
            exit bad
        }
    ' "$1"
}

validate "$tmp/ok"

# [Implementation 5] known-bad 입력과 명시적 error 경로로 검사가 실패 방향까지 판별함을 고정합니다.
./src/loggen.sh bad-format >"$tmp/bad-format"
if validate "$tmp/bad-format" 2>"$tmp/bad-format.err"; then
    echo '잘못된 형식이 검사에 통과했습니다' >&2
    exit 1
fi
grep -q '^2번째 줄의 형식이 올바르지 않습니다:' "$tmp/bad-format.err"

./src/loggen.sh duplicate >"$tmp/duplicate"
if validate "$tmp/duplicate" 2>"$tmp/duplicate.err"; then
    echo '종료 상태 뒤의 이벤트가 검사에 통과했습니다' >&2
    exit 1
fi
grep -q '^3번째 줄: id 1의 done 뒤에 이벤트가 이어졌습니다$' "$tmp/duplicate.err"

set +e
./src/loggen.sh error >"$tmp/error.out" 2>"$tmp/error.err"
status=$?
set -e
[ "$status" -eq 1 ]
[ ! -s "$tmp/error.out" ]
grep -q '^오류: 입력이 올바르지 않습니다$' "$tmp/error.err"

echo 'text-checks 검사: 통과'
