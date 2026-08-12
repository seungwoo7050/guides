#!/bin/sh
set -eu
export LC_ALL=C

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

"$SCRIPT_DIR/preflight.sh" nat
# [Implementation 5-1] NAT evidence 파일과 server process를 driver가 끝까지 소유합니다.
PEER_FILE=$(mktemp)
READY_FILE=$(mktemp)
rm -f "$READY_FILE"
SERVER_PID=
cleanup() {
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$PEER_FILE" "$READY_FILE"
    cleanup_topology
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
configure_nat_topology

# [Implementation 5-2] SNAT, server readiness, observed source와 응답 역변환을 순서대로 검증합니다.
ip netns exec "$ROUTER" iptables -t nat -A POSTROUTING \
    -s 10.202.1.0/24 -o r1 -j SNAT --to-source 198.18.0.1

ip netns exec "$SERVER" python3 "$SCRIPT_DIR/udp_probe.py" server \
    --bind 198.18.0.2 --port 9000 --output "$PEER_FILE" --ready "$READY_FILE" &
SERVER_PID=$!

attempt=0
while [ ! -s "$READY_FILE" ]; do
    if ! kill -0 "$SERVER_PID" 2>/dev/null; then
        wait "$SERVER_PID"
        printf '%s\n' "UDP server가 준비되기 전에 종료했습니다." >&2
        exit 1
    fi
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 100 ]; then
        printf '%s\n' "UDP server가 5초 안에 bind를 완료하지 못했습니다." >&2
        exit 1
    fi
    sleep 0.05
done
ip netns exec "$CLIENT" python3 "$SCRIPT_DIR/udp_probe.py" client \
    --target 198.18.0.2 --port 9000
wait "$SERVER_PID"
SERVER_PID=

printf '%s\n' "[nat] server가 관찰한 요청 출발지"
cat "$PEER_FILE"
case "$(cat "$PEER_FILE")" in
    198.18.0.1:*) ;;
    *)
        printf '%s\n' "SNAT된 출발지 주소를 관찰하지 못했습니다." >&2
        exit 1
        ;;
esac
printf '%s\n' "[nat] 내부 주소가 router 외부 주소로 변환되고 응답이 역변환되었습니다."
