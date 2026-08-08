#!/usr/bin/env bash
set -Eeuo pipefail
[[ $# -eq 3 ]] || { echo "usage: $0 CONTAINER DATABASE IMPLEMENTATION" >&2; exit 2; }
container="$1"; database="$2"; implementation="$3"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

psql_stdin() { docker exec -i "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database"; }
psql_cmd() { docker exec "$container" psql -v ON_ERROR_STOP=1 -U guide -d "$database" -Atq -c "$1"; }

psql_stdin < "$root/setup.sql"
psql_stdin < "$root/$implementation/functions.sql"

psql_cmd "SELECT reserve_inventory('book', 7);" >"$tmp/inventory-1" & p1=$!
psql_cmd "SELECT reserve_inventory('book', 7);" >"$tmp/inventory-2" & p2=$!
wait "$p1"
wait "$p2"
true_count="$(cat "$tmp/inventory-1" "$tmp/inventory-2" | grep -c '^t$' || true)"
available="$(psql_cmd "SELECT available FROM inventory WHERE sku='book';")"
[[ "$true_count" == 1 ]] || { echo "inventory: expected one success, got $true_count" >&2; exit 1; }
[[ "$available" == 3 ]] || { echo "inventory: expected 3, got $available" >&2; exit 1; }

psql_cmd "UPDATE doctors SET on_call=true;" >/dev/null
psql_cmd "SELECT take_off_call(1);" >"$tmp/oncall-1" & p1=$!
psql_cmd "SELECT take_off_call(2);" >"$tmp/oncall-2" & p2=$!
wait "$p1"
wait "$p2"
true_count="$(cat "$tmp/oncall-1" "$tmp/oncall-2" | grep -c '^t$' || true)"
remaining="$(psql_cmd "SELECT count(*) FROM doctors WHERE on_call;")"
[[ "$true_count" == 1 ]] || { echo "on-call: expected one success, got $true_count" >&2; exit 1; }
[[ "$remaining" == 1 ]] || { echo "on-call: expected one remaining doctor, got $remaining" >&2; exit 1; }
