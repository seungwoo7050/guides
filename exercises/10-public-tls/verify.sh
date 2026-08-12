#!/bin/sh
set -eu

root=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
mode=${1:-workspace}
case "$mode" in
  skeleton|workspace|reference) ;;
  *) echo "사용법: $0 [skeleton|workspace|reference]" >&2; exit 2 ;;
esac
[ -d "$root/$mode" ] || { echo "구현 디렉터리가 없습니다: $root/$mode" >&2; exit 2; }
[ ! -L "$root/$mode" ] || { echo "구현 디렉터리 symlink를 허용하지 않습니다." >&2; exit 2; }
if find "$root/$mode" -type l -print -quit | grep -q .
then
    echo "구현 디렉터리 내부 symlink를 허용하지 않습니다." >&2
    exit 2
fi
script="$root/$mode/tls-lifecycle.sh"

file_mode() {
    if stat -c '%a' "$1" >/dev/null 2>&1; then
        stat -c '%a' "$1"
    else
        stat -f '%Lp' "$1"
    fi
}

for command in openssl stat mktemp; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "필요한 명령이 없습니다: $command" >&2
        exit 2
    fi
done

tmp=$(mktemp -d)
cleanup() { rm -rf "$tmp"; }
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

"$script" issue "$tmp/live" service.example.test 30
"$script" verify "$tmp/live" service.example.test 7
openssl verify -CAfile "$tmp/live/ca.crt" "$tmp/live/server.crt" >/dev/null
openssl x509 -in "$tmp/live/server.crt" -noout -checkhost service.example.test >/dev/null

if "$script" verify "$tmp/live" wrong.example.test 7 >/dev/null 2>&1; then
    echo "잘못된 hostname 검증이 성공했습니다." >&2
    exit 1
fi

serial_before=$(openssl x509 -in "$tmp/live/server.crt" -noout -serial)
"$script" renew "$tmp/live" service.example.test 45
"$script" verify "$tmp/live" service.example.test 30
serial_after=$(openssl x509 -in "$tmp/live/server.crt" -noout -serial)
if [ "$serial_before" = "$serial_after" ]; then
    echo "renewal 뒤 인증서 serial이 바뀌지 않았습니다." >&2
    exit 1
fi

"$script" issue "$tmp/short" short.example.test 1
if "$script" verify "$tmp/short" short.example.test 7 >/dev/null 2>&1; then
    echo "최소 유효기간보다 짧은 인증서를 허용했습니다." >&2
    exit 1
fi

for key in "$tmp/live/ca.key" "$tmp/live/server.key"; do
    mode_value=$(file_mode "$key")
    if [ "$mode_value" != "600" ]; then
        echo "개인키 권한이 600이 아닙니다: $key ($mode_value)" >&2
        exit 1
    fi
done

echo "통과: chain, SAN, expiry, key mode와 renewal ($mode)"
