#!/bin/sh
set -eu

# [Implementation 12] End-to-end lifecycle verification
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
project="notes-stack-test-$$"
export COMPOSE_PROJECT_NAME="$project"
export TLS_PORT=0
compose() { docker compose -f "$base_dir/compose.yaml" "$@"; }
cleanup() { compose down --rmi local -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT HUP INT TERM

"$base_dir/prepare-secrets.sh"
compose config --quiet
compose up -d --build

wait_https() {
    attempt=0
    while [ "$attempt" -lt 180 ]; do
        attempt=$((attempt + 1))
        binding=$(compose port gateway 443 2>/dev/null || true)
        if [ -n "$binding" ]; then
            port=${binding##*:}
            if curl -kfsS --connect-timeout 1 --max-time 2 "https://127.0.0.1:$port/health" >/dev/null 2>&1; then
                return 0
            fi
        fi
        sleep 0.5
    done
    compose ps >&2 || true
    compose logs >&2 || true
    return 1
}
wait_https

compose exec -T app php -l /var/www/html/index.php >/dev/null
compose exec -T app php -l /opt/app/bootstrap.php >/dev/null
compose exec -T gateway nginx -t >/dev/null
password=$(cat "$base_dir/secrets/db_password.txt")
db() { compose exec -T db mariadb -uappuser -p"$password" appdb "$@"; }

permissions=$(compose exec -T app stat -c '%U:%G:%a' /run/app-secrets/db_password)
[ "$permissions" = root:www-data:440 ] || { echo "unexpected runtime secret permissions: $permissions" >&2; exit 1; }
if compose exec -T --user www-data app sh -c 'test -w "$DB_PASSWORD_FILE"'; then
    echo "PHP-FPM worker can modify its runtime secret" >&2
    exit 1
fi
seed_count=$(db --batch --skip-column-names -e "SELECT COUNT(*) FROM notes WHERE body='seed note';")
[ "$seed_count" = 1 ] || { echo "seed note count is $seed_count" >&2; exit 1; }
curl -kfsS "https://127.0.0.1:$port/static.txt" | grep -q 'served directly by nginx'
curl -kfsS "https://127.0.0.1:$port/api/notes" | grep -q 'seed note'

compose restart app >/dev/null
wait_https
seed_count=$(db --batch --skip-column-names -e "SELECT COUNT(*) FROM notes WHERE body='seed note';")
[ "$seed_count" = 1 ] || { echo "seed note duplicated after restart" >&2; exit 1; }
curl -kfsS -H 'Content-Type: application/json' -d '{"body":"persisted note"}' \
    "https://127.0.0.1:$port/api/notes" | grep -q 'persisted note'
compose up -d --force-recreate app gateway >/dev/null
wait_https
persisted=$(db --batch --skip-column-names -e "SELECT COUNT(*) FROM notes WHERE body='persisted note';")
[ "$persisted" = 1 ] || { echo "user data did not survive stateless container recreation" >&2; exit 1; }

backup_path=$("$base_dir/backup.sh")
db -e 'DROP TABLE notes;'
"$base_dir/restore.sh" "$backup_path"
restored=$(db --batch --skip-column-names -e "SELECT COUNT(*) FROM notes WHERE body='persisted note';")
[ "$restored" = 1 ] || { echo "logical restore failed" >&2; exit 1; }

db < "$base_dir/sql/index-demo.sql" >/tmp/notes-stack-index-demo.$$.log
rm -f /tmp/notes-stack-index-demo.$$.log

for service in app db; do
    id=$(compose ps -q "$service")
    ports=$(docker inspect "$id" --format '{{json .NetworkSettings.Ports}}')
    case "$ports" in
        *HostPort*) echo "$service exposes an internal port to the host" >&2; exit 1 ;;
    esac
done
