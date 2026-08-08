#!/bin/sh
set -eu
export LC_ALL=C

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

"$SCRIPT_DIR/preflight.sh" routing
trap cleanup_topology EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
configure_routed_topology

printf '%s\n' "[routing] client route table"
ip -n "$CLIENT" route show
printf '%s\n' "[routing] router route table"
ip -n "$ROUTER" route show

ip netns exec "$CLIENT" ping -c 2 -W 2 10.201.2.2 >/dev/null
printf '%s\n' "[routing] 두 subnet 사이 전달에 성공했습니다."

if ip netns exec "$CLIENT" ping -c 1 -W 2 -t 1 10.201.2.2 >/dev/null 2>&1; then
    printf '%s\n' "TTL 1 패킷이 예상과 달리 목적지에 도착했습니다." >&2
    exit 1
fi
ip netns exec "$CLIENT" ping -c 1 -W 2 -t 2 10.201.2.2 >/dev/null
printf '%s\n' "[routing] TTL 1은 router에서 만료되고 TTL 2는 목적지에 도착했습니다."

ip -n "$CLIENT" route del default
if ip netns exec "$CLIENT" ping -c 1 -W 1 10.201.2.2 >/dev/null 2>&1; then
    printf '%s\n' "기본 경로를 지운 뒤에도 외부 subnet에 도달했습니다." >&2
    exit 1
fi
ip -n "$CLIENT" route add default via 10.201.1.1
ip netns exec "$CLIENT" ping -c 1 -W 2 10.201.2.2 >/dev/null
printf '%s\n' "[routing] 경로 제거 실패와 복구를 확인했습니다."
