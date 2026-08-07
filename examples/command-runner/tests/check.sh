#!/bin/sh
set -eu

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

./command_runner --dump "cat < input.txt | wc -c >> output.txt" >"$tmp/dump"
cat >"$tmp/dump.expected" <<'EOT'
파이프라인 길이=2
명령 0
  argv[0]=<cat>
  표준 입력=<input.txt>
  표준 출력=<->
명령 1
  argv[0]=<wc>
  argv[1]=<-c>
  표준 입력=<->
  표준 출력=<output.txt> 모드=추가
EOT
cmp -s "$tmp/dump.expected" "$tmp/dump"

./command_runner "printf 'a b\n' | wc -c" >"$tmp/count"
awk '$1 == 4 { ok = 1 } END { exit !ok }' "$tmp/count"

printf 'hello\n' >"$tmp/input"
./command_runner "cat < $tmp/input > $tmp/output"
cmp -s "$tmp/input" "$tmp/output"
./command_runner "printf world >> $tmp/output"
printf 'hello\nworld' >"$tmp/combined"
cmp -s "$tmp/combined" "$tmp/output"

dd if=/dev/zero of="$tmp/large.bin" bs=1048576 count=4 2>/dev/null
./command_runner "cat $tmp/large.bin | wc -c" >"$tmp/large-count"
awk '$1 == 4194304 { ok = 1 } END { exit !ok }' "$tmp/large-count"

set +e
./command_runner "| cat" >"$tmp/bad.out" 2>"$tmp/bad.err"
status=$?
set -e
[ "$status" -eq 2 ]
[ ! -s "$tmp/bad.out" ]
grep -q '^문법 오류:' "$tmp/bad.err"

set +e
./command_runner "command-that-does-not-exist-c-guide" >"$tmp/missing.out" 2>"$tmp/missing.err"
status=$?
set -e
[ "$status" -eq 127 ]
grep -q 'command-that-does-not-exist' "$tmp/missing.err"

./command_runner \
    "sh -c 'echo \$\$ > $tmp/child.pid; sleep 30'" \
    >"$tmp/signal.out" 2>"$tmp/signal.err" &
runner_pid=$!
attempts=0
while [ ! -s "$tmp/child.pid" ] && [ "$attempts" -lt 100 ]; do
    sleep 0.02
    attempts=$((attempts + 1))
done
[ -s "$tmp/child.pid" ]
child_pid=$(cat "$tmp/child.pid")
kill -TERM "$runner_pid"
set +e
wait "$runner_pid"
status=$?
set -e
[ "$status" -eq 143 ]
if kill -0 "$child_pid" 2>/dev/null; then
    echo 'SIGTERM 전달 뒤에도 파이프라인 자식 프로세스가 남았습니다' >&2
    exit 1
fi

echo 'command-runner 검사: 통과'
