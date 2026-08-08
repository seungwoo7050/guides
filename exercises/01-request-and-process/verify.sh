#!/bin/sh
set -eu

mode="${1:-reference}"
case "$mode" in
    skeleton|reference) ;;
    *) echo "사용법: $0 [skeleton|reference]" >&2; exit 2 ;;
esac

base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-python3}
requested_port="${EXERCISE_PORT:-0}"
port=
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/web-infra-exercise01.XXXXXX")
log_file="$run_dir/server.log"
body_file="$run_dir/response-body"
server_pid=

cleanup()
{
    if [ -n "$server_pid" ]
    then
        kill -TERM "$server_pid" 2>/dev/null || true
        wait "$server_pid" 2>/dev/null || true
        server_pid=
    fi
    rm -rf "$run_dir"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

APP_HOST=127.0.0.1 APP_PORT="$requested_port" \
    "$PYTHON" -B "$base_dir/$mode/server.py" >"$log_file" 2>&1 &
server_pid=$!

ready=0
attempt=0
while [ "$attempt" -lt 50 ]
do
    attempt=$((attempt + 1))
    if [ -z "$port" ]
    then
        port=$(sed -n 's/^수신 주소=127\.0\.0\.1:\([0-9][0-9]*\) .*/\1/p' \
            "$log_file" | tail -n 1)
    fi
    if [ -n "$port" ] && curl -fsS --connect-timeout 1 --max-time 2 \
        "http://127.0.0.1:$port/healthz" >/dev/null 2>&1
    then
        ready=1
        break
    fi
    sleep 0.1
done

if [ "$ready" -ne 1 ]
then
    echo "실패: 서버가 제한 시간 안에 준비되지 않았습니다." >&2
    cat "$log_file" >&2
    exit 1
fi

health=$(curl -fsS --connect-timeout 1 --max-time 5 \
    "http://127.0.0.1:$port/healthz")
[ "$health" = "ok" ] || {
    echo "실패: /healthz 본문이 ok가 아닙니다." >&2
    exit 1
}

root=$(curl -fsS --connect-timeout 1 --max-time 5 \
    "http://127.0.0.1:$port/")
printf '%s' "$root" | grep -q '"status": "running"' || {
    echo "실패: / 요청이 서버 상태 JSON을 반환하지 않았습니다." >&2
    exit 1
}

status=$(curl -sS --connect-timeout 1 --max-time 5 \
    -o "$body_file" -w '%{http_code}' \
    "http://127.0.0.1:$port/missing")
[ "$status" = "404" ] || {
    echo "실패: /missing 응답이 404여야 하지만 $status입니다." >&2
    exit 1
}
grep -q '찾을 수 없습니다' "$body_file" || {
    echo "실패: 404 응답 본문에 경로를 찾을 수 없다는 설명이 없습니다." >&2
    exit 1
}
rm -f "$body_file"

kill -TERM "$server_pid"
wait "$server_pid"
server_pid=

if curl -fsS --connect-timeout 1 --max-time 2 \
    "http://127.0.0.1:$port/healthz" >/dev/null 2>&1
then
    echo "실패: 서버 종료 뒤에도 요청이 성공했습니다." >&2
    exit 1
fi

grep -q 'path=/healthz' "$log_file" || {
    echo "실패: 요청 로그가 기록되지 않았습니다." >&2
    exit 1
}

echo "통과: 요청과 프로세스 검사 ($mode)"
