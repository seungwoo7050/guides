#!/usr/bin/env bash
set -euo pipefail
bin="${1:?}"; a="$(mktemp)"; e="$(mktemp)"; trap 'rm -f "$a" "$e"' EXIT
cat >"$e" <<'OUT'
OK
VALUE 1
COUNT 1
DELETED
BYE
OUT
printf 'PUT a 1\nGET a\nCOUNT\nDELETE a\nQUIT\n' | "$bin" >"$a"
diff -u "$e" "$a"
echo '04단계 검사: 통과'
