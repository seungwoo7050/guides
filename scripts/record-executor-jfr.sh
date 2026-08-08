#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
RECORDING_DIR=$(mktemp -d "${TMPDIR:-/tmp}/guide-java-jfr.XXXXXX")

cleanup() {
  rm -rf "$RECORDING_DIR"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

"$ROOT/scripts/mvn-guide.sh" \
  -pl :executor-lifecycle-reference -am -DskipTests package

java_command=java
jfr_command=jfr
if [[ -n "${JAVA_HOME:-}" ]]; then
  java_command="$JAVA_HOME/bin/java"
  jfr_command="$JAVA_HOME/bin/jfr"
fi

"$java_command" \
  -XX:StartFlightRecording="filename=$RECORDING_DIR/executor.jfr,settings=profile,dumponexit=true" \
  -cp "$ROOT/exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference/target/classes" \
  dev.guides.java.executor.ExecutorProbe

"$jfr_command" summary "$RECORDING_DIR/executor.jfr" >"$RECORDING_DIR/summary.txt"
grep -Eq 'jdk\.(ThreadStart|ThreadEnd|ExecutionSample)' "$RECORDING_DIR/summary.txt"
printf '[PASS] JFR 실행기 기록과 요약 확인\n'
