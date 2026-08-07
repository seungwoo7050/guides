#!/bin/sh
set -eu

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

./command_pipeline spawn >"$tmp/spawn.out" 2>"$tmp/spawn.err"
printf 'child-ok\n' >"$tmp/expected"
cmp -s "$tmp/expected" "$tmp/spawn.out"
[ ! -s "$tmp/spawn.err" ]

set +e
./command_pipeline missing >"$tmp/missing.out" 2>"$tmp/missing.err"
status=$?
set -e
[ "$status" -eq 127 ]
[ ! -s "$tmp/missing.out" ]
grep -q 'command-that-does-not-exist' "$tmp/missing.err"

./command_pipeline redirect "$tmp/file"
printf 'alpha\n' >"$tmp/alpha"
cmp -s "$tmp/alpha" "$tmp/file"
./command_pipeline append "$tmp/file"
printf 'alpha\nalpha\n' >"$tmp/two"
cmp -s "$tmp/two" "$tmp/file"

./command_pipeline pipeline >"$tmp/pipeline.out"
printf 'alpha\nbeta\n' >"$tmp/pipeline.expected"
cmp -s "$tmp/pipeline.expected" "$tmp/pipeline.out"

set +e
./command_pipeline pipeline-status
status=$?
set -e
[ "$status" -eq 7 ]

./command_pipeline repeat

echo 'command-pipeline 검사: 통과'
