#!/bin/sh
set -eu

MODE=${1:-routing}
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

# [Implementation 2] privilege와 실험 mode별 필수 command를 topology 생성 전에 검증합니다.
require_root
for command in ip ping sysctl python3 grep; do
    require_command "$command"
done
case "$MODE" in
    routing) ;;
    nat) require_command iptables ;;
    loss)
        require_command tc
        require_command tcpdump
        ;;
    all)
        require_command iptables
        require_command tc
        require_command tcpdump
        ;;
    *)
        printf '%s\n' "사용법: $0 [routing|nat|loss|all]" >&2
        exit 2
        ;;
esac

# [Implementation 2-1] 실제 namespace 생성·실행을 확인하고 소유한 probe를 종료 시 정리합니다.
assert_names_available
probe="cn-probe-$RUN_SUFFIX"
probe_owned=0
cleanup_probe() {
    [ "$probe_owned" -eq 0 ] || ip netns del "$probe" 2>/dev/null || true
}
trap cleanup_probe EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
ip netns add "$probe"
probe_owned=1
ip netns exec "$probe" true
printf '%s\n' "Linux network namespace 실습 환경을 확인했습니다: $MODE"
