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
project="web-infra-${verify_run}-exercise05-${mode}"
export COMPOSE_PROJECT_NAME="$project"
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
    echo "실패: database 스택의 Compose 설정이 유효하지 않습니다." >&2
    exit 1
fi
if ! compose up -d --build
then
    echo "실패: database 스택을 시작하지 못했습니다." >&2
    compose ps >&2 || true
    compose logs >&2 || true
    exit 1
fi

db_id=$(compose ps -q db)
ready=0
attempt=0
while [ "$attempt" -lt 100 ]
do
    attempt=$((attempt + 1))
    health=$(docker inspect "$db_id" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' 2>/dev/null || true)
    [ "$health" = healthy ] && { ready=1; break; }
    [ "$(docker inspect "$db_id" --format '{{.State.Status}}' 2>/dev/null || true)" = exited ] && break
    sleep 0.5
done
[ "$ready" -eq 1 ] || {
    echo "실패: 데이터베이스가 제한 시간 안에 healthy가 되지 않았습니다." >&2
    compose ps >&2
    compose logs db >&2
    exit 1
}

ports=$(docker inspect "$db_id" --format '{{json .NetworkSettings.Ports}}')
case "$ports" in
    *HostPort*) echo "실패: 데이터베이스 포트를 호스트에 공개하면 안 됩니다: $ports" >&2; exit 1 ;;
esac

password=$(cat "$work/secrets/db_password.txt")
db() { compose exec -T db mariadb -uappuser -p"$password" appdb "$@"; }

db -e 'CREATE TABLE IF NOT EXISTS verify_marker (id INT PRIMARY KEY, value VARCHAR(50) NOT NULL); INSERT INTO verify_marker VALUES (1,"persistent") ON DUPLICATE KEY UPDATE value=VALUES(value);'
[ "$(db --batch --skip-column-names -e 'SELECT value FROM verify_marker WHERE id=1;')" = persistent ] || {
    echo "실패: 검증 marker를 저장하거나 읽지 못했습니다." >&2
    exit 1
}

# 이름 있는 volume은 보존하고 컨테이너만 다시 만듭니다.
compose up -d --force-recreate db >/dev/null
db_id=$(compose ps -q db)
ready=0
attempt=0
while [ "$attempt" -lt 80 ]
do
    attempt=$((attempt + 1))
    if [ "$(docker inspect "$db_id" --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' 2>/dev/null || true)" = healthy ]
    then
        ready=1
        break
    fi
    sleep 0.5
done
[ "$ready" -eq 1 ] || {
    echo "실패: 데이터베이스 재생성 뒤 healthy가 되지 않았습니다." >&2
    compose logs db >&2
    exit 1
}
[ "$(db --batch --skip-column-names -e 'SELECT value FROM verify_marker WHERE id=1;')" = persistent ] || {
    echo "실패: 컨테이너 재생성 뒤 volume 데이터가 사라졌습니다." >&2
    exit 1
}

# 표시 테이블을 논리 backup하고 빈 상태에 복원합니다.
mkdir -p "$work/backups"
db -e 'DROP TABLE IF EXISTS restore_probe; CREATE TABLE restore_probe (id INT PRIMARY KEY, value VARCHAR(50)); INSERT INTO restore_probe VALUES (7,"from-backup");'
compose exec -T db mariadb-dump -uappuser -p"$password" appdb restore_probe > "$work/backups/restore-probe.sql"
db -e 'DROP TABLE restore_probe;'
compose exec -T db mariadb -uappuser -p"$password" appdb < "$work/backups/restore-probe.sql"
[ "$(db --batch --skip-column-names -e 'SELECT value FROM restore_probe WHERE id=7;')" = from-backup ] || {
    echo "실패: 논리 backup을 복원하지 못했습니다." >&2
    exit 1
}

# EXPLAIN 열 위치를 가정하지 않고 header에서 key 열을 찾습니다.
explain_key()
{
    db --batch -e "EXPLAIN SELECT * FROM index_demo WHERE email='user0400@users.local.test';" |
        awk -F '\t' '
            NR == 1 {
                for (column = 1; column <= NF; column += 1) {
                    if ($column == "key") key_column = column
                }
                next
            }
            NR == 2 && key_column > 0 { print $key_column }
        '
}

compose exec -T db mariadb -uappuser -p"$password" appdb < "$work/sql/index-demo.sql"
before=$(explain_key)
db -e 'CREATE INDEX idx_index_demo_email ON index_demo(email);'
after=$(explain_key)
[ "$after" = idx_index_demo_email ] || {
    echo "실패: 인덱스 키가 선택되지 않았습니다. 적용 전=$before 적용 후=$after" >&2
    exit 1
}

echo "통과: 데이터베이스 보존·복원·인덱스 검사 ($mode, 적용 전=$before, 적용 후=$after)"
