#!/bin/sh
set -eu

scenario="${1:-}"
case "$scenario" in
    wrong-db-host|wrong-db-password|missing-secret|wrong-fcgi-port|broken-healthcheck|data-loss) ;;
    *)
        echo "사용법: $0 {wrong-db-host|wrong-db-password|missing-secret|wrong-fcgi-port|broken-healthcheck|data-loss}" >&2
        exit 2
        ;;
esac

base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/web-infra-troubleshooting.XXXXXX")
cp -R "$base_dir/../06-app-bootstrap/reference/." "$work"
verify_run="${GUIDE_VERIFY_RUN_ID:-manual-$$}"
project="web-infra-${verify_run}-exercise07-${scenario}"
export COMPOSE_PROJECT_NAME="$project"
export TLS_PORT="${TLS_PORT:-0}"
port=

compose()
{
    if [ "$scenario" = data-loss ]
    then
        docker compose -f "$work/compose.yaml" "$@"
    else
        docker compose \
            -f "$work/compose.yaml" \
            -f "$base_dir/scenarios/$scenario.yaml" \
            "$@"
    fi
}
cleanup_stack() { compose down --rmi local -v --remove-orphans >/dev/null 2>&1 || true; }
cleanup()
{
    cleanup_stack
    rm -rf "$work"
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

"$work/prepare-secrets.sh"
printf '%s\n' 'intentionally-wrong-password' > "$work/secrets/wrong_db_password.txt"
chmod 0600 "$work/secrets/wrong_db_password.txt"

wait_db()
{
    attempt=0
    while [ "$attempt" -lt 120 ]
    do
        attempt=$((attempt + 1))
        id=$(compose ps -q db 2>/dev/null || true)
        if [ -z "$id" ]
        then
            sleep 0.25
            continue
        fi
        health=$(docker inspect "$id" --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' 2>/dev/null || true)
        [ "$health" = healthy ] && return 0
        sleep 0.25
    done
    return 1
}

wait_https()
{
    path="${1:-/health}"
    attempt=0
    while [ "$attempt" -lt 120 ]
    do
        attempt=$((attempt + 1))
        binding=$(compose port gateway 443 2>/dev/null || true)
        if [ -n "$binding" ]
        then
            port=${binding##*:}
            if curl -kfsS --connect-timeout 1 --max-time 2 \
                "https://127.0.0.1:$port$path" >/dev/null 2>&1
            then
                return 0
            fi
        fi
        sleep 0.25
    done
    return 1
}

case "$scenario" in
    wrong-db-host|wrong-db-password|missing-secret)
        set +e
        compose up -d --build >/dev/null 2>&1
        up_status=$?
        set -e
        wait_db || {
            echo "실패: database가 준비되지 않아 애플리케이션 실패 계층을 검사할 수 없습니다." >&2
            compose logs db >&2
            exit 1
        }

        app_id=""
        attempt=0
        while [ "$attempt" -lt 80 ]
        do
            attempt=$((attempt + 1))
            app_id=$(compose ps -a -q app 2>/dev/null || true)
            if [ -n "$app_id" ]
            then
                state=$(docker inspect "$app_id" --format '{{.State.Status}}' 2>/dev/null || true)
                [ "$state" = exited ] && break
            fi
            sleep 0.25
        done
        [ -n "$app_id" ] || {
            echo "실패: app 컨테이너가 만들어지지 않았습니다." >&2
            exit 1
        }
        state=$(docker inspect "$app_id" --format '{{.State.Status}}')
        [ "$state" = exited ] || {
            compose ps >&2
            compose logs app >&2
            echo "실패: app 컨테이너가 종료되어야 합니다." >&2
            exit 1
        }
        logs=$(compose logs --no-color app 2>&1 || true)
        case "$scenario" in
            wrong-db-host)
                printf '%s' "$logs" | grep -Eq '준비되지 않았습니다|Name or service not known|getaddrinfo' || {
                    printf '%s\n' "$logs" >&2
                    echo "실패: DNS 또는 연결 진단 메시지가 없습니다." >&2
                    exit 1
                }
                ;;
            wrong-db-password)
                printf '%s' "$logs" | grep -Eq 'Access denied|준비되지 않았습니다' || {
                    printf '%s\n' "$logs" >&2
                    echo "실패: 인증 진단 메시지가 없습니다." >&2
                    exit 1
                }
                ;;
            missing-secret)
                printf '%s' "$logs" | grep -q 'DB_PASSWORD_FILE을 읽을 수 없습니다' || {
                    printf '%s\n' "$logs" >&2
                    echo "실패: 비밀값 파일 진단 메시지가 없습니다." >&2
                    exit 1
                }
                ;;
        esac
        echo "통과: $scenario (Compose 시작 종료 코드=$up_status, app 상태=$state)"
        ;;

    wrong-fcgi-port)
        compose up -d --build
        wait_db || {
            echo "실패: database가 준비되지 않았습니다." >&2
            compose logs db >&2
            exit 1
        }
        gateway_id=$(compose ps -q gateway)
        health=""
        attempt=0
        while [ "$attempt" -lt 120 ]
        do
            attempt=$((attempt + 1))
            health=$(docker inspect "$gateway_id" --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' 2>/dev/null || true)
            [ "$health" = healthy ] && break
            sleep 0.25
        done
        [ "$health" = healthy ] || {
            echo "실패: gateway 자체 상태 검사가 healthy가 되지 않았습니다." >&2
            compose logs gateway >&2
            exit 1
        }
        binding=$(compose port gateway 443)
        port=${binding##*:}
        code=$(curl -ksS --connect-timeout 1 --max-time 5 \
            -o /dev/null -w '%{http_code}' "https://127.0.0.1:$port/health")
        [ "$code" = 502 ] || {
            compose logs gateway >&2
            echo "실패: 동적 요청 응답이 502여야 하지만 $code입니다." >&2
            exit 1
        }
        echo "통과: $scenario (gateway 상태=$health, 동적 요청=$code)"
        ;;

    broken-healthcheck)
        compose up -d --build
        wait_https /health || {
            echo "실패: 외부 사용자 요청이 준비되지 않았습니다." >&2
            compose logs >&2
            exit 1
        }
        gateway_id=$(compose ps -q gateway)
        health=""
        attempt=0
        while [ "$attempt" -lt 80 ]
        do
            attempt=$((attempt + 1))
            health=$(docker inspect "$gateway_id" --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' 2>/dev/null || true)
            [ "$health" = unhealthy ] && break
            sleep 0.25
        done
        [ "$health" = unhealthy ] || {
            echo "실패: 의도적으로 고장 낸 healthcheck가 unhealthy가 되지 않았습니다." >&2
            docker inspect "$gateway_id" >&2
            exit 1
        }
        code=$(curl -ksS --connect-timeout 1 --max-time 5 \
            -o /dev/null -w '%{http_code}' "https://127.0.0.1:$port/health")
        [ "$code" = 200 ] || {
            echo "실패: 상태 검사가 실패해도 서비스 요청은 동작해야 합니다." >&2
            exit 1
        }
        echo "통과: $scenario (외부 응답=$code, 상태 검사=$health)"
        ;;

    data-loss)
        compose up -d --build
        wait_https /health || {
            echo "실패: 데이터 손실 시나리오의 정상 스택이 준비되지 않았습니다." >&2
            compose logs >&2
            exit 1
        }
        curl -kfsS --connect-timeout 1 --max-time 5 \
            -H 'Content-Type: application/json' \
            -d '{"body":"will be deleted with the volume"}' \
            "https://127.0.0.1:$port/api/notes" >/dev/null
        curl -kfsS --connect-timeout 1 --max-time 5 \
            "https://127.0.0.1:$port/api/notes" | grep -q 'will be deleted with the volume' || {
            echo "실패: volume 삭제 전 사용자 데이터가 기록되지 않았습니다." >&2
            exit 1
        }

        compose down -v --remove-orphans >/dev/null
        compose up -d
        wait_https /health || {
            echo "실패: volume 삭제 뒤 새 스택이 준비되지 않았습니다." >&2
            compose logs >&2
            exit 1
        }
        notes=$(curl -kfsS --connect-timeout 1 --max-time 5 \
            "https://127.0.0.1:$port/api/notes")
        printf '%s' "$notes" | grep -q 'seed note' || {
            echo "실패: 새 volume의 초기 상태가 만들어지지 않았습니다." >&2
            exit 1
        }
        if printf '%s' "$notes" | grep -q 'will be deleted with the volume'
        then
            echo "실패: volume을 삭제했는데 사용자 데이터가 남아 있습니다." >&2
            exit 1
        fi
        echo "통과: $scenario (volume 삭제 뒤 사용자 데이터가 사라졌습니다.)"
        ;;
esac
