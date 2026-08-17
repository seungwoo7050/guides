#!/bin/sh
set -eu

program=${1:?program path required}
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

fail()
{
    printf 'textstat test failed: %s\n' "$1" >&2
    exit 1
}

"$program" 'one two' >"$tmp/out" 2>"$tmp/err"
printf 'length=7\nwords=2\n' >"$tmp/expected"
diff -u "$tmp/expected" "$tmp/out" || fail 'regular output mismatch'
[ ! -s "$tmp/err" ] || fail 'regular input wrote to stderr'

"$program" '' >"$tmp/out" 2>"$tmp/err"
printf 'length=0\nwords=0\n' >"$tmp/expected"
diff -u "$tmp/expected" "$tmp/out" || fail 'empty-string output mismatch'
[ ! -s "$tmp/err" ] || fail 'empty string wrote to stderr'

set +e
"$program" >"$tmp/out" 2>"$tmp/err"
status=$?
set -e
[ "$status" -eq 2 ] || fail "expected usage status=2 actual=$status"
[ ! -s "$tmp/out" ] || fail 'usage error wrote to stdout'
grep -F 'Usage:' "$tmp/err" >/dev/null || fail 'missing usage diagnostic'

printf 'textstat tests passed\n'
