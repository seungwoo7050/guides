#!/bin/sh

# [Implementation 1] 실행별 resource 이름과 소유권 flag를 먼저 고정합니다.
RUN_SEED=${GUIDE_NETWORK_RUN_ID:-$$}
RUN_SUFFIX=$(printf '%s' "$RUN_SEED" | cksum | awk '{print $1}')
CLIENT="cn-client-$RUN_SUFFIX"
ROUTER="cn-router-$RUN_SUFFIX"
SERVER="cn-server-$RUN_SUFFIX"
CLIENT_LINK="c${RUN_SUFFIX}a"
ROUTER_LEFT_LINK="r${RUN_SUFFIX}a"
ROUTER_RIGHT_LINK="r${RUN_SUFFIX}b"
SERVER_LINK="s${RUN_SUFFIX}a"
OWN_CLIENT=0
OWN_ROUTER=0
OWN_SERVER=0
OWN_LEFT_LINK=0
OWN_RIGHT_LINK=0

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        printf '%s\n' "이 실습은 격리된 network namespace를 만들기 위해 root 권한이 필요합니다." >&2
        exit 1
    fi
}

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        printf '%s\n' "필수 명령을 찾지 못했습니다: $1" >&2
        exit 1
    fi
}

namespace_exists() {
    ip netns list | grep -Eq "^$1([[:space:]]|$)"
}

# [Implementation 1-1] 기존 namespace와 interface를 발견하면 덮어쓰기 전에 중단합니다.
assert_names_available() {
    for namespace in "$CLIENT" "$ROUTER" "$SERVER"; do
        if namespace_exists "$namespace"; then
            printf '%s\n' \
                "이미 존재하는 namespace를 덮어쓰지 않습니다: $namespace" \
                "이전 실습의 잔여물인지 확인한 뒤 직접 정리하세요." >&2
            exit 1
        fi
    done

    for interface in "$CLIENT_LINK" "$ROUTER_LEFT_LINK" "$ROUTER_RIGHT_LINK" "$SERVER_LINK"; do
        if ip link show "$interface" >/dev/null 2>&1; then
            printf '%s\n' \
                "이미 존재하는 interface를 덮어쓰지 않습니다: $interface" \
                "이전 실습의 잔여물인지 확인한 뒤 직접 정리하세요." >&2
            exit 1
        fi
    done
}

# [Implementation 1-2] ownership을 획득한 resource만 정리합니다.
cleanup_topology() {
    [ "$OWN_CLIENT" -eq 0 ] || ip netns del "$CLIENT" 2>/dev/null || true
    [ "$OWN_ROUTER" -eq 0 ] || ip netns del "$ROUTER" 2>/dev/null || true
    [ "$OWN_SERVER" -eq 0 ] || ip netns del "$SERVER" 2>/dev/null || true
    [ "$OWN_LEFT_LINK" -eq 0 ] || ip link del "$CLIENT_LINK" 2>/dev/null || true
    [ "$OWN_RIGHT_LINK" -eq 0 ] || ip link del "$ROUTER_RIGHT_LINK" 2>/dev/null || true
}

# [Implementation 3] namespace와 veth를 만들고 각 resource의 ownership 이전을 기록합니다.
create_links() {
    assert_names_available
    ip netns add "$CLIENT"
    OWN_CLIENT=1
    ip netns add "$ROUTER"
    OWN_ROUTER=1
    ip netns add "$SERVER"
    OWN_SERVER=1

    ip link add "$CLIENT_LINK" type veth peer name "$ROUTER_LEFT_LINK"
    OWN_LEFT_LINK=1
    ip link add "$ROUTER_RIGHT_LINK" type veth peer name "$SERVER_LINK"
    OWN_RIGHT_LINK=1

    ip link set "$CLIENT_LINK" netns "$CLIENT"
    OWN_LEFT_LINK=0
    ip link set "$ROUTER_LEFT_LINK" netns "$ROUTER"
    ip link set "$ROUTER_RIGHT_LINK" netns "$ROUTER"
    OWN_RIGHT_LINK=0
    ip link set "$SERVER_LINK" netns "$SERVER"

    ip -n "$CLIENT" link set "$CLIENT_LINK" name c0
    ip -n "$ROUTER" link set "$ROUTER_LEFT_LINK" name r0
    ip -n "$ROUTER" link set "$ROUTER_RIGHT_LINK" name r1
    ip -n "$SERVER" link set "$SERVER_LINK" name s0

    for namespace in "$CLIENT" "$ROUTER" "$SERVER"; do
        ip -n "$namespace" link set lo up
    done
    ip -n "$CLIENT" link set c0 up
    ip -n "$ROUTER" link set r0 up
    ip -n "$ROUTER" link set r1 up
    ip -n "$SERVER" link set s0 up
}

# [Implementation 3-1] 두 subnet의 주소·route와 router forwarding을 함께 구성합니다.
configure_routed_topology() {
    create_links
    ip -n "$CLIENT" address add 10.201.1.2/24 dev c0
    ip -n "$ROUTER" address add 10.201.1.1/24 dev r0
    ip -n "$ROUTER" address add 10.201.2.1/24 dev r1
    ip -n "$SERVER" address add 10.201.2.2/24 dev s0
    ip -n "$CLIENT" route add default via 10.201.1.1
    ip -n "$SERVER" route add default via 10.201.2.1
    ip netns exec "$ROUTER" sysctl -q -w net.ipv4.ip_forward=1 >/dev/null
}

# [Implementation 3-2] 사설·시험 대역을 분리해 주소 변환 전 topology를 고정합니다.
configure_nat_topology() {
    create_links
    ip -n "$CLIENT" address add 10.202.1.2/24 dev c0
    ip -n "$ROUTER" address add 10.202.1.1/24 dev r0
    ip -n "$ROUTER" address add 198.18.0.1/24 dev r1
    ip -n "$SERVER" address add 198.18.0.2/24 dev s0
    ip -n "$CLIENT" route add default via 10.202.1.1
    ip netns exec "$ROUTER" sysctl -q -w net.ipv4.ip_forward=1 >/dev/null
}
