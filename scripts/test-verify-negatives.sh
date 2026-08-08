#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
markers=(.guide/*/prepared.json)
[[ ${#markers[@]} -eq 1 && -f "${markers[0]}" ]] || {
    printf 'negative-check: 먼저 ./prepare.sh를 실행하십시오.\n' >&2
    exit 1
}
MARKER="$ROOT/${markers[0]}"
TEMPORARY="$(mktemp -d "${TMPDIR:-/tmp}/guide-verify-negatives.XXXXXX")"
BACKUP="$TEMPORARY/prepared.valid.json"
FIXTURE="$ROOT/.verify-stale-fixture"
MARKER_MOVED=0
VERIFY_PID=''
OWNED_PID=''

cleanup() {
    status=$?
    trap - EXIT HUP INT TERM
    [[ -z "$VERIFY_PID" ]] || kill -TERM "$VERIFY_PID" 2>/dev/null || true
    [[ -z "$VERIFY_PID" ]] || wait "$VERIFY_PID" 2>/dev/null || true
    [[ -z "$OWNED_PID" ]] || kill -KILL "$OWNED_PID" 2>/dev/null || true
    rm -f -- "$FIXTURE"
    if (( MARKER_MOVED == 1 )); then
        rm -f -- "$MARKER"
        mv -- "$BACKUP" "$MARKER"
    fi
    rm -rf -- "$TEMPORARY"
    exit "$status"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

expect_failure() {
    local label=$1
    local expected=$2
    shift 2
    if "$@" >"$TEMPORARY/$label.console" 2>&1; then
        printf 'negative-check: %s가 성공했습니다.\n' "$label" >&2
        exit 1
    fi
    grep -R -Fq -- "$expected" "$TEMPORARY"
    grep -Fq 'failed=1 skipped=0' "$TEMPORARY/$label.console"
    grep -Fq 'RESULT: FAIL' "$TEMPORARY/$label.console"
}

expect_failure relative-log '절대 경로' ./verify.sh relative-negative.log
[[ ! -e "$ROOT/relative-negative.log" ]]
expect_failure in-repository-log '저장소 밖' ./verify.sh "$ROOT/.negative-inside.log"
[[ ! -e "$ROOT/.negative-inside.log" ]]
printf 'sentinel\n' > "$TEMPORARY/log-target"
ln -s -- "$TEMPORARY/log-target" "$TEMPORARY/log-link"
expect_failure leaf-symlink-log 'symlink' ./verify.sh "$TEMPORARY/log-link"
[[ "$(cat "$TEMPORARY/log-target")" == sentinel ]]

mv -- "$MARKER" "$BACKUP"
MARKER_MOVED=1
expect_failure missing-marker 'prepared marker가 없습니다' env VERIFY_LOG="$TEMPORARY/missing.log" ./verify.sh
mv -- "$BACKUP" "$MARKER"
MARKER_MOVED=0

mv -- "$MARKER" "$BACKUP"
MARKER_MOVED=1
printf '{not-json\n' > "$MARKER"
expect_failure corrupt-marker 'invalid prepared marker' env VERIFY_LOG="$TEMPORARY/corrupt.log" ./verify.sh
rm -f -- "$MARKER"
mv -- "$BACKUP" "$MARKER"
MARKER_MOVED=0

mv -- "$MARKER" "$BACKUP"
MARKER_MOVED=1
python3 - "$BACKUP" "$MARKER" <<'PY'
import json, sys
from pathlib import Path
source, target = map(Path, sys.argv[1:])
data = json.loads(source.read_text(encoding="utf-8"))
data["tools"]["git"] = "git version stale-fixture"
target.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
expect_failure stale-tools 'stale prepared marker field: tools' \
    env VERIFY_LOG="$TEMPORARY/stale-tools.log" ./verify.sh
rm -f -- "$MARKER"
mv -- "$BACKUP" "$MARKER"
MARKER_MOVED=0

mv -- "$MARKER" "$BACKUP"
MARKER_MOVED=1
python3 - "$BACKUP" "$MARKER" <<'PY'
import json, sys
from pathlib import Path
source, target = map(Path, sys.argv[1:])
data = json.loads(source.read_text(encoding="utf-8"))
data["platform"]["system"] = "stale-fixture"
target.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
expect_failure stale-platform 'stale prepared marker field: platform' \
    env VERIFY_LOG="$TEMPORARY/stale-platform.log" ./verify.sh
rm -f -- "$MARKER"
mv -- "$BACKUP" "$MARKER"
MARKER_MOVED=0

touch "$FIXTURE"
expect_failure stale-marker 'stale prepared marker field: source_fingerprint' \
    env VERIFY_LOG="$TEMPORARY/stale.log" ./verify.sh
rm -f -- "$FIXTURE"

signal_pid_file="$TEMPORARY/owned.pid"
signal_log="$TEMPORARY/signal.log"
env GUIDE_VERIFY_TEST_HOLD=1 GUIDE_VERIFY_TEST_PID_FILE="$signal_pid_file" \
    VERIFY_LOG="$signal_log" ./verify.sh >"$TEMPORARY/signal.console" 2>&1 &
verify_pid=$!
VERIFY_PID=$verify_pid
for _ in {1..200}; do
    [[ -s "$signal_pid_file" ]] && break
    kill -0 "$verify_pid" 2>/dev/null || break
    sleep 0.02
done
if [[ ! -s "$signal_pid_file" ]]; then
    kill -TERM "$verify_pid" 2>/dev/null || true
    wait "$verify_pid" 2>/dev/null || true
    printf 'negative-check: signal cleanup fixture가 시작되지 않았습니다.\n' >&2
    exit 1
fi
owned_pid="$(cat "$signal_pid_file")"
OWNED_PID=$owned_pid
kill -TERM "$verify_pid"
if wait "$verify_pid" 2>/dev/null; then
    printf 'negative-check: signal을 받은 verify가 성공했습니다.\n' >&2
    exit 1
fi
for _ in {1..100}; do
    kill -0 "$owned_pid" 2>/dev/null || break
    sleep 0.02
done
if kill -0 "$owned_pid" 2>/dev/null; then
    kill -KILL "$owned_pid" 2>/dev/null || true
    printf 'negative-check: verify 소유 process가 signal 뒤 남았습니다: %s\n' "$owned_pid" >&2
    exit 1
fi
VERIFY_PID=''
OWNED_PID=''
grep -Fq 'failed=1 skipped=0' "$TEMPORARY/signal.console"
grep -Fq 'RESULT: FAIL' "$TEMPORARY/signal.console"

printf 'VERIFY NEGATIVES: PASS (relative/in-repo/leaf-symlink log, missing/corrupt/source-tools-platform-stale marker, signal-owned-process cleanup)\n'
