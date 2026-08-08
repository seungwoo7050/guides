#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then
    printf '%s\n' "tcpdump 캡처에는 권한이 필요합니다. sudo로 다시 실행하세요." >&2
    exit 1
fi
for command in python3 tcpdump; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf '%s\n' "필수 명령을 찾지 못했습니다: $command" >&2
        exit 1
    fi
done

PORT=${PORT:-18080}
OUTPUT=${OUTPUT:-capture.txt}
SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
SERVER_LOG=$(mktemp)
SERVER_PID=
CAPTURE_PID=

case "$(uname -s)" in
    Darwin) INTERFACE=${INTERFACE:-lo0} ;;
    Linux) INTERFACE=${INTERFACE:-lo} ;;
    *)
        printf '%s\n' "지원하지 않는 운영체제입니다." >&2
        exit 1
        ;;
esac

if [ -e "$OUTPUT" ]; then
    printf '%s\n' "기존 캡처 파일을 덮어쓰지 않습니다: $OUTPUT" >&2
    exit 1
fi

cleanup() {
    if [ -n "$CAPTURE_PID" ]; then
        kill -INT "$CAPTURE_PID" 2>/dev/null || true
        wait "$CAPTURE_PID" 2>/dev/null || true
    fi
    if [ -n "$SERVER_PID" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        wait "$SERVER_PID" 2>/dev/null || true
    fi
    rm -f "$SERVER_LOG"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

python3 -m http.server "$PORT" --bind 127.0.0.1 >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!
sleep 1
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    cat "$SERVER_LOG" >&2
    exit 1
fi

tcpdump -i "$INTERFACE" -nn -tt -l "tcp port $PORT" >"$OUTPUT" 2>/dev/null &
CAPTURE_PID=$!
sleep 1
python3 - "$PORT" <<'PYCLIENT'
import http.client
import sys

port = int(sys.argv[1])
connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
connection.request("GET", "/")
response = connection.getresponse()
response.read()
connection.close()
if response.status != 200:
    raise SystemExit(f"예상하지 않은 HTTP 상태: {response.status}")
PYCLIENT
sleep 0.5
kill -INT "$CAPTURE_PID"
wait "$CAPTURE_PID" || true
CAPTURE_PID=
python3 "$SCRIPT_DIR/analyze_tcpdump.py" "$OUTPUT"
