#!/bin/sh
set -eu
export LC_ALL=C

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
EXERCISE_DIR=$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)
ANALYZER="$EXERCISE_DIR/../packet-observation/scripts/analyze_tcpdump.py"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/common.sh"

"$SCRIPT_DIR/preflight.sh" loss
# [Implementation 6-1] qdisc, process와 temporary capture를 소유해 trap이 처리하는 종료 경로에서 정리합니다.
TRACE=$(mktemp)
REPORT=$(mktemp)
SERVER_PID=
CLIENT_PID=
CAPTURE_PID=
cleanup() {
    ip netns exec "$ROUTER" tc qdisc del dev r1 root 2>/dev/null || true
    for pid in "$CLIENT_PID" "$SERVER_PID" "$CAPTURE_PID"; do
        if [ -n "$pid" ]; then
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
        fi
    done
    rm -f "$TRACE" "$REPORT"
    cleanup_topology
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
configure_routed_topology

# [Implementation 6-2] capture 뒤 100% 손실을 걸고 반복 SYN을 본 후 제거해 연결 복구를 증명합니다.
ip netns exec "$SERVER" python3 "$SCRIPT_DIR/tcp_probe.py" server \
    --bind 10.201.2.2 --port 9000 &
SERVER_PID=$!
sleep 0.2

ip netns exec "$CLIENT" tcpdump -i c0 -nn -tt -l -c 2 \
    'tcp dst port 9000 and (tcp[tcpflags] & tcp-syn != 0)' \
    >"$TRACE" 2>/dev/null &
CAPTURE_PID=$!
sleep 0.2

ip netns exec "$ROUTER" tc qdisc add dev r1 root netem loss 100%
ip netns exec "$CLIENT" python3 "$SCRIPT_DIR/tcp_probe.py" client \
    --target 10.201.2.2 --port 9000 --timeout 10 &
CLIENT_PID=$!

count=0
attempt=0
while [ "$count" -lt 2 ] && [ "$attempt" -lt 60 ]; do
    sleep 0.1
    count=$(grep -c 'Flags \[S\]' "$TRACE" 2>/dev/null || true)
    attempt=$((attempt + 1))
done
if [ "$count" -lt 2 ]; then
    printf '%s\n' "제한 시간 안에 초기 SYN과 재전송 SYN을 관찰하지 못했습니다." >&2
    exit 1
fi
ip netns exec "$ROUTER" tc qdisc del dev r1 root

wait "$CLIENT_PID"
CLIENT_PID=
wait "$SERVER_PID"
SERVER_PID=
wait "$CAPTURE_PID"
CAPTURE_PID=

python3 "$ANALYZER" "$TRACE" >"$REPORT"
python3 - "$REPORT" <<'PYCHECK'
import json
from pathlib import Path
import sys

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if len(report["retransmission_candidates"]) < 1:
    raise SystemExit("반복 SYN을 재전송 후보로 찾지 못했습니다")
PYCHECK
printf '%s\n' "[loss] 캡처된 SYN"
cat "$TRACE"
printf '%s\n' "[loss] 100% 손실을 제거한 뒤 재전송된 SYN으로 연결이 복구되었습니다."
