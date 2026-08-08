#!/bin/sh
set -eu

mode="${1:-reference}"
case "$mode" in skeleton|reference) ;; *) echo "사용법: $0 [skeleton|reference]" >&2; exit 2 ;; esac
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
work="$base_dir/$mode"
verify_run="${GUIDE_VERIFY_RUN_ID:-manual-$$}"
project="web-infra-${verify_run}-exercise03-${mode}"
port=
count_file=$(mktemp "${TMPDIR:-/tmp}/exercise03-count.XXXXXX")
export COMPOSE_PROJECT_NAME="$project"
export EXERCISE_PORT="${EXERCISE_PORT:-0}"

compose() { docker compose -f "$work/compose.yaml" "$@"; }
cleanup()
{
    compose down --rmi local -v --remove-orphans >/dev/null 2>&1 || true
    rm -f "$count_file"
}
on_signal()
{
    signal=$1
    trap - EXIT HUP INT TERM
    cleanup
    case "$signal" in
        HUP) exit 129 ;;
        INT) exit 130 ;;
        TERM) exit 143 ;;
    esac
}
trap cleanup EXIT
trap 'on_signal HUP' HUP
trap 'on_signal INT' INT
trap 'on_signal TERM' TERM

if ! compose config --quiet
then
    echo "실패: Compose app의 Compose 설정이 유효하지 않습니다." >&2
    exit 1
fi
if ! compose up -d --build app
then
    echo "실패: Compose 설정을 시작하지 못했습니다." >&2
    compose ps >&2 || true
    compose logs >&2 || true
    exit 1
fi

ready=0
attempt=0
while [ "$attempt" -lt 60 ]
do
    attempt=$((attempt + 1))
    binding=$(compose port app 8080 2>/dev/null || true)
    if [ -n "$binding" ]
    then
        port=${binding##*:}
        if curl -fsS --connect-timeout 1 --max-time 2 \
            "http://127.0.0.1:$port/healthz" >/dev/null 2>&1
        then
            ready=1
            break
        fi
    fi
    sleep 0.5
done
[ "$ready" -eq 1 ] || {
    echo "실패: Compose app이 제한 시간 안에 준비되지 않았습니다." >&2
    compose ps >&2
    compose logs >&2
    exit 1
}

compose run --rm client | grep -q '^ok$' || {
    echo "실패: 내부 service name을 사용한 client 요청이 성공하지 않았습니다." >&2
    exit 1
}

curl -fsS --connect-timeout 1 --max-time 5 -X POST \
    "http://127.0.0.1:$port/increment" | grep -q '"count": 1' || {
    echo "실패: 첫 번째 증가 결과가 1이 아닙니다." >&2
    exit 1
}
curl -fsS --connect-timeout 1 --max-time 5 -X POST \
    "http://127.0.0.1:$port/increment" | grep -q '"count": 2' || {
    echo "실패: 두 번째 증가 결과가 2가 아닙니다." >&2
    exit 1
}
before=$(curl -fsS --connect-timeout 1 --max-time 5 \
    "http://127.0.0.1:$port/count")
printf '%s' "$before" | grep -q '"count": 2' || {
    echo "실패: 재생성 전 count가 2가 아닙니다: $before" >&2
    exit 1
}

# volume은 보존한 채 container/network만 내렸다가 다시 올립니다.
compose down
compose up -d app
ready=0
attempt=0
while [ "$attempt" -lt 40 ]
do
    attempt=$((attempt + 1))
    binding=$(compose port app 8080 2>/dev/null || true)
    if [ -n "$binding" ]
    then
        port=${binding##*:}
        if curl -fsS --connect-timeout 1 --max-time 2 \
            "http://127.0.0.1:$port/count" >"$count_file" 2>/dev/null
        then
            ready=1
            break
        fi
    fi
    sleep 0.5
done
[ "$ready" -eq 1 ] || {
    echo "실패: Compose app 재생성 뒤 준비되지 않았습니다." >&2
    compose logs >&2
    exit 1
}
grep -q '"count": 2' "$count_file" || {
    echo "실패: 이름 있는 volume의 count가 보존되지 않았습니다." >&2
    cat "$count_file" >&2
    exit 1
}

echo "통과: Compose 상태 보존 검사 ($mode)"
