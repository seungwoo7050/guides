#!/bin/sh
set -eu

mode="${1:-reference}"
case "$mode" in skeleton|reference) ;; *) echo "사용법: $0 [skeleton|reference]" >&2; exit 2 ;; esac
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
work="$base_dir/$mode"
verify_run="${GUIDE_VERIFY_RUN_ID:-manual-$$}"
project="web-infra-${verify_run}-exercise04-${mode}"
port=
export COMPOSE_PROJECT_NAME="$project"
export TLS_PORT="${TLS_PORT:-0}"
compose() { docker compose -f "$work/compose.yaml" "$@"; }
cleanup() { compose down --rmi local -v --remove-orphans >/dev/null 2>&1 || true; }
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
    echo "실패: gateway 스택의 Compose 설정이 유효하지 않습니다." >&2
    exit 1
fi
if ! compose up -d --build
then
    echo "실패: gateway 스택을 시작하지 못했습니다." >&2
    compose ps >&2 || true
    compose logs >&2 || true
    exit 1
fi

ready=0
attempt=0
while [ "$attempt" -lt 80 ]
do
    attempt=$((attempt + 1))
    binding=$(compose port gateway 443 2>/dev/null || true)
    if [ -n "$binding" ]
    then
        port=${binding##*:}
        if curl -kfsS --connect-timeout 1 --max-time 2 \
            "https://127.0.0.1:$port/healthz" >/dev/null 2>&1
        then
            ready=1
            break
        fi
    fi
    sleep 0.5
done
[ "$ready" -eq 1 ] || {
    echo "실패: HTTPS gateway가 제한 시간 안에 준비되지 않았습니다." >&2
    compose ps >&2
    compose logs >&2
    exit 1
}

[ "$(curl -kfsS --connect-timeout 1 --max-time 5 \
    "https://127.0.0.1:$port/healthz")" = "ok" ] || {
    echo "실패: gateway healthz 응답이 ok가 아닙니다." >&2
    exit 1
}
[ "$(curl -kfsS --connect-timeout 1 --max-time 5 \
    "https://127.0.0.1:$port/static.txt")" = "served directly by nginx" ] || {
    echo "실패: 정적 파일이 Nginx에서 직접 제공되지 않았습니다." >&2
    exit 1
}

body=$(curl -kfsS --connect-timeout 1 --max-time 5 \
    "https://127.0.0.1:$port/")
printf '%s' "$body" | grep -q '"runtime": "php-fpm"' || {
    echo "실패: 동적 요청이 PHP-FPM runtime에 도달하지 않았습니다." >&2
    exit 1
}
printf '%s' "$body" | grep -q '"https": "on"' || {
    echo "실패: FastCGI 요청에 HTTPS 상태가 전달되지 않았습니다." >&2
    exit 1
}
printf '%s' "$body" | grep -q '/var/www/html/index.php' || {
    echo "실패: SCRIPT_FILENAME 경계가 올바르지 않습니다." >&2
    exit 1
}

compose exec -T app sh -c '
  REQUEST_METHOD=GET SCRIPT_NAME=/ping SCRIPT_FILENAME=/ping \
  cgi-fcgi -bind -connect 127.0.0.1:9000
' | grep -q pong || {
    echo "실패: PHP-FPM FastCGI 직접 검사에 실패했습니다." >&2
    exit 1
}

app_id=$(compose ps -q app)
ports=$(docker inspect "$app_id" --format '{{json .NetworkSettings.Ports}}')
case "$ports" in
    *HostPort*) echo "실패: app의 FastCGI 포트를 호스트에 공개하면 안 됩니다: $ports" >&2; exit 1 ;;
    *) ;;
esac

compose exec -T app php -l /var/www/html/index.php >/dev/null
compose exec -T gateway nginx -t >/dev/null

echo "통과: 게이트웨이와 FastCGI 검사 ($mode)"
