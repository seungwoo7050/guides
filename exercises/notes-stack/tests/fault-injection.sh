#!/bin/sh
set -eu

# [Implementation 12-1] Fault-injection verification
scenario=${1:-all}
case "$scenario" in
    all|wrong-db-host|wrong-db-password|missing-secret|wrong-fcgi-port|broken-healthcheck|data-loss) ;;
    *) echo "usage: $0 [all|wrong-db-host|wrong-db-password|missing-secret|wrong-fcgi-port|broken-healthcheck|data-loss]" >&2; exit 2 ;;
esac
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)

run_one() {
    name=$1
    work=$(mktemp -d "${TMPDIR:-/tmp}/notes-stack-fault.XXXXXX")
    cp -R "$base_dir/." "$work"
    project="notes-stack-fault-${name}-$$"
    export COMPOSE_PROJECT_NAME="$project"
    export TLS_PORT=0
    if [ "$name" = data-loss ]; then
        compose() { docker compose -f "$work/compose.yaml" "$@"; }
    else
        compose() { docker compose -f "$work/compose.yaml" -f "$work/tests/scenarios/$name.yaml" "$@"; }
    fi
    cleanup() { compose down --rmi local -v --remove-orphans >/dev/null 2>&1 || true; rm -rf "$work"; }
    trap cleanup EXIT HUP INT TERM
    "$work/prepare-secrets.sh"
    printf '%s\n' intentionally-wrong-password > "$work/secrets/wrong_db_password.txt"
    chmod 0600 "$work/secrets/wrong_db_password.txt"

    case "$name" in
        wrong-db-host|wrong-db-password|missing-secret)
            compose up -d --build >/dev/null 2>&1 || true
            attempt=0
            while [ "$attempt" -lt 80 ]; do
                attempt=$((attempt + 1))
                app_id=$(compose ps -a -q app 2>/dev/null || true)
                [ -n "$app_id" ] || { sleep 0.25; continue; }
                state=$(docker inspect "$app_id" --format '{{.State.Status}}' 2>/dev/null || true)
                [ "$state" = exited ] && break
                sleep 0.25
            done
            [ "${state:-}" = exited ] || { compose logs app >&2; exit 1; }
            logs=$(compose logs --no-color app 2>&1 || true)
            case "$name" in
                wrong-db-host) printf '%s' "$logs" | grep -Eq 'did not become ready|Name or service not known|getaddrinfo' ;;
                wrong-db-password) printf '%s' "$logs" | grep -Eq 'Access denied|did not become ready' ;;
                missing-secret) printf '%s' "$logs" | grep -q 'DB_PASSWORD_FILE is not readable' ;;
            esac
            ;;
        wrong-fcgi-port)
            compose up -d --build >/dev/null
            attempt=0
            while [ "$attempt" -lt 160 ]; do
                attempt=$((attempt + 1))
                binding=$(compose port gateway 443 2>/dev/null || true)
                if [ -n "$binding" ]; then
                    port=${binding##*:}
                    code=$(curl -ksS -o /dev/null -w '%{http_code}' "https://127.0.0.1:$port/health" || true)
                    [ "$code" = 502 ] && break
                fi
                sleep 0.25
            done
            [ "${code:-}" = 502 ] || { compose logs >&2; exit 1; }
            ;;
        broken-healthcheck)
            compose up -d --build >/dev/null || true
            attempt=0
            while [ "$attempt" -lt 160 ]; do
                attempt=$((attempt + 1))
                binding=$(compose port gateway 443 2>/dev/null || true)
                gateway_id=$(compose ps -q gateway 2>/dev/null || true)
                if [ -n "$binding" ] && [ -n "$gateway_id" ]; then
                    port=${binding##*:}
                    code=$(curl -ksS -o /dev/null -w '%{http_code}' "https://127.0.0.1:$port/health" || true)
                    health=$(docker inspect "$gateway_id" --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' 2>/dev/null || true)
                    [ "$code" = 200 ] && [ "$health" = unhealthy ] && break
                fi
                sleep 0.25
            done
            [ "${code:-}" = 200 ] && [ "${health:-}" = unhealthy ]
            ;;
        data-loss)
            compose up -d --build >/dev/null
            attempt=0
            while [ "$attempt" -lt 160 ]; do
                attempt=$((attempt + 1))
                binding=$(compose port gateway 443 2>/dev/null || true)
                if [ -n "$binding" ]; then
                    port=${binding##*:}
                    curl -kfsS "https://127.0.0.1:$port/health" >/dev/null 2>&1 && break
                fi
                sleep 0.25
            done
            curl -kfsS -H 'Content-Type: application/json' -d '{"body":"deleted with volume"}' \
                "https://127.0.0.1:$port/api/notes" >/dev/null
            compose down -v --remove-orphans >/dev/null
            compose up -d >/dev/null
            attempt=0
            while [ "$attempt" -lt 160 ]; do
                attempt=$((attempt + 1))
                binding=$(compose port gateway 443 2>/dev/null || true)
                if [ -n "$binding" ]; then
                    port=${binding##*:}
                    notes=$(curl -kfsS "https://127.0.0.1:$port/api/notes" 2>/dev/null || true)
                    printf '%s' "$notes" | grep -q 'seed note' && break
                fi
                sleep 0.25
            done
            if printf '%s' "${notes:-}" | grep -q 'deleted with volume'; then
                echo "data remained after named volume deletion" >&2
                exit 1
            fi
            ;;
    esac
    trap - EXIT HUP INT TERM
    cleanup
    echo "passed: $name"
}

if [ "$scenario" = all ]; then
    for item in wrong-db-host wrong-db-password missing-secret wrong-fcgi-port broken-healthcheck data-loss; do
        run_one "$item"
    done
else
    run_one "$scenario"
fi
