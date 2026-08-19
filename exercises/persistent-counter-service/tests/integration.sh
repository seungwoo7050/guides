#!/bin/sh
set -eu

# [Implementation 7-1] Container lifecycle verification
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
project="persistent-counter-test-$$"
export COMPOSE_PROJECT_NAME="$project"
export COUNTER_PORT=0
compose() { docker compose -f "$base_dir/compose.yaml" "$@"; }
cleanup() { compose down --rmi local -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT HUP INT TERM

compose config --quiet
compose up -d --build app
attempt=0
port=""
while [ "$attempt" -lt 80 ]; do
    attempt=$((attempt + 1))
    binding=$(compose port app 8080 2>/dev/null || true)
    if [ -n "$binding" ]; then
        port=${binding##*:}
        if curl -fsS --connect-timeout 1 --max-time 2 "http://127.0.0.1:$port/healthz" >/dev/null 2>&1; then
            break
        fi
    fi
    sleep 0.25
done
[ -n "$port" ] || { echo "app did not publish a port" >&2; exit 1; }
compose run --rm client | grep -q '^ok$'
curl -fsS -X POST "http://127.0.0.1:$port/increment" | grep -q '"count":1'
curl -fsS -X POST "http://127.0.0.1:$port/increment" | grep -q '"count":2'
compose down
compose up -d app
attempt=0
while [ "$attempt" -lt 80 ]; do
    attempt=$((attempt + 1))
    binding=$(compose port app 8080 2>/dev/null || true)
    if [ -n "$binding" ]; then
        port=${binding##*:}
        if curl -fsS "http://127.0.0.1:$port/count" | grep -q '"count":2'; then
            exit 0
        fi
    fi
    sleep 0.25
done
echo "counter was not preserved after container recreation" >&2
exit 1
