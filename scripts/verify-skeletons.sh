#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
WORK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/guide-java-skeletons.XXXXXX")

cleanup() {
  rm -rf "$WORK_ROOT"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

verify_contract() {
  local label=$1
  local pom=$2
  local selector=$3
  local message=$4
  local detail=$5
  local output="$WORK_ROOT/$label.log"
  local status

  set +e
  "$ROOT/scripts/mvn-guide.sh" -f "$ROOT/$pom" -Dtest="$selector" test \
    >"$output" 2>&1
  status=$?
  set -e

  if [[ $status -eq 0 ]] \
    || ! grep -Fq "${selector//#/.}" "$output" \
    || ! grep -Fq "$message" "$output" \
    || ! grep -Fq "$detail" "$output" \
    || ! grep -Eq 'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0' "$output" \
    || grep -Eq 'COMPILATION ERROR|NoClassDefFoundError|Could not resolve dependencies|Tests run: 1, Failures: 0, Errors: [1-9]' "$output"; then
    printf '[FAIL] %s skeleton이 지정된 학습 계약이 아닌 이유로 실패했습니다.\n' "$label" >&2
    cat "$output" >&2
    return 1
  fi
  printf '[PASS] %s skeleton 지정 학습 계약 실패: %s\n' "$label" "$selector"
}

run_requested() {
  local requested=${1:-all}
  local matched=0

  if [[ "$requested" == all || "$requested" == first-program ]]; then
    verify_contract first-program \
      exercises/01-language-and-domain/01-first-program/skeleton/pom.xml \
      dev.guides.java.firstprogram.NumberReportApplicationTest#rejectsMissingArgumentsWithoutWritingStandardOutput \
      'expected: 2' 'but was: 0'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == value-object-contract ]]; then
    verify_contract value-object-contract \
      exercises/01-language-and-domain/02-value-object-contract/skeleton/pom.xml \
      dev.guides.java.valueobject.MoneyTest#rejectsNegativeAmount \
      'Expecting code to raise a throwable.' 'MoneyTest.rejectsNegativeAmount'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == concurrent-state-update ]]; then
    verify_contract concurrent-state-update \
      exercises/02-runtime-and-concurrency/01-concurrent-state-update/skeleton/pom.xml \
      dev.guides.java.concurrentstate.CounterConcurrencyTest#lockPreservesConservationInvariant \
      'expected: 80L' 'but was: 160L'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == executor-lifecycle ]]; then
    verify_contract executor-lifecycle \
      exercises/02-runtime-and-concurrency/02-executor-lifecycle/skeleton/pom.xml \
      dev.guides.java.executor.BoundedTaskRunnerTest#rejectsWorkWhenWorkerAndQueueAreOccupied \
      'Expecting code to raise a throwable.' 'BoundedTaskRunnerTest.rejectsWorkWhenWorkerAndQueueAreOccupied'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == state-and-effect-testing ]]; then
    verify_contract state-and-effect-testing \
      exercises/03-build-test-and-evidence/02-state-and-effect-testing/skeleton/pom.xml \
      dev.guides.java.stateeffect.StrongEvidenceTest#provesOneStateChangeAndEffectForRepeatedKey \
      'Expected size: 1 but was: 20' 'StrongEvidenceTest.provesOneStateChangeAndEffectForRepeatedKey'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == concurrent-job-ledger ]]; then
    verify_contract concurrent-job-ledger \
      exercises/04-capstone/01-concurrent-job-ledger/skeleton/pom.xml \
      dev.guides.java.jobledger.ConcurrentJobLedgerTest#sameIdentifierAndCommandShareOneResultAndOneEffect \
      'to refer to the same object' 'ConcurrentJobLedgerTest.sameIdentifierAndCommandShareOneResultAndOneEffect'
    matched=1
  fi

  [[ $matched -eq 1 ]] || fail "알 수 없는 skeleton 계약입니다: $requested"
}

[[ $# -le 1 ]] || fail "사용법: scripts/verify-skeletons.sh [contract-name]"
run_requested "${1:-all}"
