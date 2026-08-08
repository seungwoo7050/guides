#!/usr/bin/env bash
set -euo pipefail
bin="${1:?binary required}"; actual="$(mktemp)"; expected="$(mktemp)"
trap 'rm -f "$actual" "$expected"' EXIT
cat >"$expected" <<'OUT'
OK
OK
FULL
VALUE 1
COUNT 2
DELETED
COUNT 1
BYE
OUT
printf 'PUT a 1\nPUT b 2\nPUT c 3\nGET a\nCOUNT\nDELETE a\nCOUNT\nQUIT\n' | "$bin" >"$actual"
diff -u "$expected" "$actual"
echo '03단계 검사: 통과'
