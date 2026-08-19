#!/bin/sh
set -eu

# [Implementation 8] Lifecycle regression suite
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/tls-lifecycle.XXXXXX")
cleanup() { rm -rf "$work"; }
trap cleanup EXIT HUP INT TERM

"$base_dir/tls-lifecycle.sh" issue "$work" api.local.test 2 >/dev/null
"$base_dir/tls-lifecycle.sh" verify "$work" api.local.test 0
serial_one=$(openssl x509 -in "$work/server.crt" -noout -serial)
[ "$(stat -L -c '%a' "$work/server.key" 2>/dev/null || stat -L -f '%Lp' "$work/server.key")" = 600 ]
[ -L "$work/current" ] && [ -L "$work/server.key" ] && [ -L "$work/server.crt" ]

if "$base_dir/tls-lifecycle.sh" verify "$work" wrong.local.test 0 >/dev/null 2>&1; then
    echo "hostname mismatch was accepted" >&2
    exit 1
fi
if "$base_dir/tls-lifecycle.sh" verify "$work" api.local.test 3 >/dev/null 2>&1; then
    echo "minimum remaining lifetime was not enforced" >&2
    exit 1
fi

"$base_dir/tls-lifecycle.sh" renew "$work" api.local.test 30 >/dev/null
"$base_dir/tls-lifecycle.sh" verify "$work" api.local.test 10
serial_two=$(openssl x509 -in "$work/server.crt" -noout -serial)
[ "$serial_one" != "$serial_two" ] || { echo "renewal did not change serial" >&2; exit 1; }
version_count=$(find "$work/versions" -mindepth 1 -maxdepth 1 -type d ! -name '.candidate.*' | wc -l | tr -d ' ')
[ "$version_count" -eq 2 ] || { echo "expected two retained certificate versions" >&2; exit 1; }
