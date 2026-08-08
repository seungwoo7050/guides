#!/usr/bin/env bash
set -euo pipefail
bin="${1:?binary required}"
actual="$(mktemp)"
expected="$(mktemp)"
trap 'rm -f "$actual" "$expected"' EXIT
cat >"$expected" <<'OUT'
OK
VALUE alice
COUNT 1
DELETED
NOT_FOUND
BYE
OUT
printf 'PUT name alice\nGET name\nCOUNT\nDELETE name\nGET name\nQUIT\n' | "$bin" >"$actual"
diff -u "$expected" "$actual"
printf '01단계 검사: 통과\n'
