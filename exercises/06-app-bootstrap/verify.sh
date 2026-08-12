#!/bin/sh
set -eu

mode="${1:-workspace}"
case "$mode" in skeleton|workspace|reference) ;; *) echo "사용법: $0 [skeleton|workspace|reference]" >&2; exit 2 ;; esac
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
work="$base_dir/$mode"
[ -d "$work" ] || { echo "구현 디렉터리가 없습니다: $work" >&2; exit 2; }
[ ! -L "$work" ] || { echo "구현 디렉터리 symlink를 허용하지 않습니다." >&2; exit 2; }
if find "$work" -type l -print -quit | grep -q .
then
    echo "구현 디렉터리 내부 symlink를 허용하지 않습니다." >&2
    exit 2
fi
verify_run="${GUIDE_VERIFY_RUN_ID:-manual-$$}"
project="web-infra-${verify_run}-exercise06-${mode}"
export COMPOSE_PROJECT_NAME="$project"
export TLS_PORT="${TLS_PORT:-0}"
port=
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

"$work/prepare-secrets.sh"
if ! compose config --quiet
then
    echo "실패: 애플리케이션 스택의 Compose 설정이 유효하지 않습니다." >&2
    exit 1
fi
if ! compose up -d --build
then
    echo "실패: 애플리케이션 스택을 시작하지 못했습니다." >&2
    compose ps >&2 || true
    compose logs >&2 || true
    exit 1
fi

wait_https()
{
    attempt=0
    while [ "$attempt" -lt 160 ]
    do
        attempt=$((attempt + 1))
        binding=$(compose port gateway 443 2>/dev/null || true)
        if [ -n "$binding" ]
        then
            port=${binding##*:}
            if curl -kfsS --connect-timeout 1 --max-time 2 \
                "https://127.0.0.1:$port/health" >/dev/null 2>&1
            then
                return 0
            fi
        fi
        sleep 0.5
    done
    echo "실패: 애플리케이션 스택이 제한 시간 안에 준비되지 않았습니다." >&2
    compose ps >&2
    compose logs >&2
    return 1
}

wait_https
compose exec -T app php -l /var/www/html/index.php >/dev/null
compose exec -T app php -l /opt/app/bootstrap.php >/dev/null
compose exec -T gateway nginx -t >/dev/null

password=$(cat "$work/secrets/db_password.txt")
db() { compose exec -T db mariadb -uappuser -p"$password" appdb "$@"; }

runtime_password_file=/run/app-secrets/db_password
runtime_permissions=$(compose exec -T app stat -c '%U:%G:%a' "$runtime_password_file")
[ "$runtime_permissions" = root:www-data:440 ] || {
    echo "실패: 런타임 비밀값 권한이 예상과 다릅니다: $runtime_permissions" >&2
    exit 1
}
runtime_password=$(compose exec -T --user www-data app cat "$runtime_password_file")
[ "$runtime_password" = "$password" ] || {
    echo "실패: PHP-FPM 작업자가 동일한 비밀값을 읽지 못했습니다." >&2
    exit 1
}
if compose exec -T --user www-data app sh -c 'test -w "$DB_PASSWORD_FILE"'
then
    echo "실패: PHP-FPM 작업자가 런타임 비밀값을 수정할 수 있습니다." >&2
    exit 1
fi

seed_count=$(db --batch --skip-column-names -e "SELECT COUNT(*) FROM notes WHERE body='seed note';")
[ "$seed_count" = 1 ] || {
    echo "실패: 초기 메모가 한 건이어야 하지만 $seed_count건입니다." >&2
    exit 1
}

curl -kfsS --connect-timeout 1 --max-time 5 \
    "https://127.0.0.1:$port/api/notes" | grep -q 'seed note' || {
    echo "실패: 사용자 API에서 seed note를 읽지 못했습니다." >&2
    exit 1
}
curl -kfsS --connect-timeout 1 --max-time 5 \
    "https://127.0.0.1:$port/static.txt" | grep -q 'served directly by nginx' || {
    echo "실패: 정적 파일이 gateway에서 제공되지 않았습니다." >&2
    exit 1
}

# 재시작하면 시작 스크립트가 다시 실행되지만 초기 데이터는 중복되지 않아야 합니다.
compose restart app >/dev/null
wait_https
seed_count=$(db --batch --skip-column-names -e "SELECT COUNT(*) FROM notes WHERE body='seed note';")
[ "$seed_count" = 1 ] || {
    echo "실패: 재시작 뒤 초기 메모가 중복되었습니다." >&2
    exit 1
}

created=$(curl -kfsS --connect-timeout 1 --max-time 5 \
    -H 'Content-Type: application/json' \
    -d '{"body":"persisted note"}' \
    "https://127.0.0.1:$port/api/notes")
printf '%s' "$created" | grep -q 'persisted note' || {
    echo "실패: 사용자 데이터 쓰기가 성공하지 않았습니다." >&2
    exit 1
}

# 데이터베이스 volume은 보존하고 무상태 container를 다시 만듭니다.
compose up -d --force-recreate app gateway >/dev/null
wait_https
persisted=$(db --batch --skip-column-names -e "SELECT COUNT(*) FROM notes WHERE body='persisted note';")
[ "$persisted" = 1 ] || {
    echo "실패: app 컨테이너를 다시 만든 뒤 애플리케이션 데이터가 사라졌습니다." >&2
    exit 1
}
seed_count=$(db --batch --skip-column-names -e "SELECT COUNT(*) FROM notes WHERE body='seed note';")
[ "$seed_count" = 1 ] || {
    echo "실패: 컨테이너를 다시 만든 뒤 초기 메모가 중복되었습니다." >&2
    exit 1
}

app_id=$(compose ps -q app)
db_id=$(compose ps -q db)
for id in "$app_id" "$db_id"
do
    ports=$(docker inspect "$id" --format '{{json .NetworkSettings.Ports}}')
    case "$ports" in
        *HostPort*) echo "실패: 내부 서비스 포트가 호스트에 공개되었습니다: $ports" >&2; exit 1 ;;
    esac
done

echo "통과: 애플리케이션 초기화 검사 ($mode, 초기 메모=$seed_count, 보존된 메모=$persisted)"
