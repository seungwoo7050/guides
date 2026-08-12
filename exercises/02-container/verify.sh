#!/bin/sh
set -eu

mode="${1:-workspace}"
case "$mode" in skeleton|workspace|reference) ;; *) echo "사용법: $0 [skeleton|workspace|reference]" >&2; exit 2 ;; esac

base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
[ -d "$base_dir/$mode" ] || { echo "구현 디렉터리가 없습니다: $base_dir/$mode" >&2; exit 2; }
[ ! -L "$base_dir/$mode" ] || { echo "구현 디렉터리 symlink를 허용하지 않습니다." >&2; exit 2; }
if find "$base_dir/$mode" -type l -print -quit | grep -q .
then
    echo "구현 디렉터리 내부 symlink를 허용하지 않습니다." >&2
    exit 2
fi
verify_run="${GUIDE_VERIFY_RUN_ID:-manual-$$}"
image="web-infra-${verify_run}-exercise02-${mode}:verify"
container="web-infra-${verify_run}-exercise02-${mode}"
requested_port="${EXERCISE_PORT:-0}"
port=

cleanup()
{
    docker rm -f "$container" >/dev/null 2>&1 || true
    docker image rm -f "$image" >/dev/null 2>&1 || true
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

start_container()
{
    docker run -d --name "$container" \
        --label "guide.web-infrastructure.verify-run=$verify_run" \
        -p "127.0.0.1:$requested_port:8080" \
        "$image" >/dev/null
    port=$(
        docker inspect "$container" \
            --format '{{(index (index .NetworkSettings.Ports "8080/tcp") 0).HostPort}}'
    )
    [ -n "$port" ] || {
        echo "실패: 게시된 호스트 포트를 찾지 못했습니다." >&2
        exit 1
    }
}

if [ -n "${BUILDX_BUILDER:-}" ]
then
    docker buildx build \
        --builder "$BUILDX_BUILDER" \
        --load \
        --label "guide.web-infrastructure.verify-run=$verify_run" \
        -t "$image" \
        "$base_dir/$mode"
else
    docker build \
        --label "guide.web-infrastructure.verify-run=$verify_run" \
        -t "$image" \
        "$base_dir/$mode"
fi

entrypoint=$(docker image inspect "$image" --format '{{json .Config.Entrypoint}}')
[ "$entrypoint" = '["python","/app/server.py"]' ] || {
    echo "실패: entrypoint는 exec 형식의 python /app/server.py여야 합니다: $entrypoint" >&2
    exit 1
}

user=$(docker image inspect "$image" --format '{{.Config.User}}')
[ "$user" = '65532:65532' ] || {
    echo "실패: 이미지 사용자는 65532:65532여야 합니다: '$user'" >&2
    exit 1
}

start_container

ready=0
attempt=0
while [ "$attempt" -lt 60 ]
do
    attempt=$((attempt + 1))
    if curl -fsS --connect-timeout 1 --max-time 2 \
        "http://127.0.0.1:$port/healthz" >/dev/null 2>&1
    then
        ready=1
        break
    fi
    sleep 0.2
done
[ "$ready" -eq 1 ] || {
    echo "실패: 컨테이너가 제한 시간 안에 준비되지 않았습니다." >&2
    docker logs "$container" >&2 || true
    exit 1
}

curl -fsS --connect-timeout 1 --max-time 5 \
    "http://127.0.0.1:$port/" | grep -q '"status": "running"' || {
    echo "실패: 컨테이너 사용자 경로가 예상 상태를 반환하지 않았습니다." >&2
    exit 1
}

pid1=$(docker exec "$container" sh -c 'tr "\000" " " </proc/1/cmdline')
case "$pid1" in
    *python*server.py*) ;;
    *) echo "실패: PID 1이 예상한 프로세스가 아닙니다: $pid1" >&2; exit 1 ;;
esac

docker exec -u 0 "$container" sh -c 'echo runtime >/tmp/runtime-value'
docker exec "$container" cat /tmp/runtime-value | grep -q runtime

docker rm -f "$container" >/dev/null
start_container

ready=0
attempt=0
while [ "$attempt" -lt 60 ]
do
    attempt=$((attempt + 1))
    if curl -fsS --connect-timeout 1 --max-time 2 \
        "http://127.0.0.1:$port/healthz" >/dev/null 2>&1
    then
        ready=1
        break
    fi
    sleep 0.2
done
[ "$ready" -eq 1 ] || {
    echo "실패: 다시 만든 컨테이너가 제한 시간 안에 준비되지 않았습니다." >&2
    docker logs "$container" >&2 || true
    exit 1
}

if docker exec "$container" test -e /tmp/runtime-value
then
    echo "실패: 쓰기 계층의 파일이 컨테이너를 다시 만든 뒤에도 남아 있습니다." >&2
    exit 1
fi

docker stop -t 5 "$container" >/dev/null
status=$(docker inspect "$container" --format '{{.State.ExitCode}}')
[ "$status" = '0' ] || {
    echo "실패: 정상 종료 코드는 0이어야 하지만 $status입니다." >&2
    docker logs "$container" >&2 || true
    exit 1
}

echo "통과: 컨테이너 수명 주기 검사 ($mode)"
