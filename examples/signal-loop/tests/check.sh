#!/bin/sh
set -eu

tmp=$(mktemp -d)
pid=''
cleanup()
{
    if [ -n "$pid" ]; then
        kill -TERM "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    fi
    rm -rf "$tmp"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

./signal_loop >"$tmp/out" 2>"$tmp/err" &
pid=$!

i=0
while ! grep -q '^pid=' "$tmp/out" 2>/dev/null; do
    i=$((i + 1))
    [ "$i" -lt 50 ] || { echo 'PID 출력을 기다리다 제한 시간을 넘었습니다' >&2; exit 1; }
    sleep 0.02
done

kill -USR1 "$pid"
i=0
while ! grep -q '^event=usr1 ' "$tmp/out" 2>/dev/null; do
    i=$((i + 1))
    [ "$i" -lt 50 ] || { echo 'USR1 이벤트를 기다리다 제한 시간을 넘었습니다' >&2; exit 1; }
    sleep 0.02
done

kill -TERM "$pid"
wait "$pid"
pid=''

grep -q '^shutdown observed=1$' "$tmp/out"
[ ! -s "$tmp/err" ]

echo 'signal-loop 검사: 통과'
