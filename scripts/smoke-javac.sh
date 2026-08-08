#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d)
cleanup() {
  rm -rf "$WORK"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

compile_module() {
  local module=$1
  local source="$ROOT/$module/src/main/java"
  [[ -d "$source" ]] || return 0
  local list="$WORK/${module//\//_}.txt"
  find "$source" -type f -name '*.java' | LC_ALL=C sort >"$list"
  [[ -s "$list" ]] || return 0
  local out="$WORK/out/${module//\//_}"
  mkdir -p "$out"
  javac --release 17 -Xlint:all -d "$out" @"$list"
  printf '[PASS] javac --release 17: %s\n' "$module"
}

compile_module examples/runtime-model
compile_module exercises/01-language-and-domain/01-first-program/reference
compile_module exercises/01-language-and-domain/02-value-object-contract/reference
compile_module exercises/02-runtime-and-concurrency/01-concurrent-state-update/reference
compile_module exercises/02-runtime-and-concurrency/02-executor-lifecycle/reference
compile_module exercises/03-build-test-and-evidence/02-state-and-effect-testing/reference
compile_module exercises/04-capstone/01-concurrent-job-ledger/reference
