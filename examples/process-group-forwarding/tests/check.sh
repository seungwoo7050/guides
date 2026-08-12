#!/bin/sh
set -eu

temporary=$(mktemp -d "${TMPDIR:-/tmp}/guide-c-process-group.XXXXXX")
child=
cleanup()
{
    if [ -n "$child" ]; then
        kill -TERM "$child" 2>/dev/null || true
        wait "$child" 2>/dev/null || true
    fi
    rm -rf -- "$temporary"
}
trap cleanup EXIT HUP INT TERM

./process_group_forwarding sh -c \
    'trap "exit 42" TERM; printf "ready\n"; while :; do sleep 1; done' \
    >"$temporary/stdout" 2>"$temporary/stderr" &
child=$!

attempt=0
while ! grep -q '^ready$' "$temporary/stdout"; do
    attempt=$((attempt + 1))
    [ "$attempt" -lt 200 ] || { printf '%s\n' 'ready timeout' >&2; exit 1; }
    sleep 0.01
done

kill -TERM "$child"
set +e
wait "$child"
status=$?
set -e
child=
[ "$status" -eq 143 ]
# 전달 대상 명령과 그 자식이 쓰는 stderr는 그대로 통과하므로 비어 있음을 요구하지 않습니다.

set +e
./process_group_forwarding command-that-does-not-exist-guide-c \
    >"$temporary/missing.out" 2>"$temporary/missing.err"
status=$?
set -e
[ "$status" -eq 127 ]
[ ! -s "$temporary/missing.out" ]
[ -s "$temporary/missing.err" ]

printf '%s\n' 'process-group-forwarding 검사: 통과'
