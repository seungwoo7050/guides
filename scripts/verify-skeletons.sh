#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
WORK_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/guide-spring-skeletons.XXXXXX")"

cleanup() {
  rm -rf -- "$WORK_ROOT"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

run_maven() {
  if [[ -n "${MAVEN_USER_HOME:-}" && -n "${GUIDE_MAVEN_REPOSITORY:-}" ]]; then
    "$ROOT_DIR/mvnw" -B -ntp -o \
      -Dmaven.repo.local="$GUIDE_MAVEN_REPOSITORY" "$@"
  else
    "$ROOT_DIR/scripts/mvn-guide.sh" "$@"
  fi
}

verify_contract() {
  local label=$1 pom=$2 selector=$3 summary=$4
  shift 4
  local output="$WORK_ROOT/$label.log" status=0 detail method
  method="${selector##*#}"

  run_maven -f "$ROOT_DIR/$pom" -Dtest="$selector" test \
    >"$output" 2>&1 || status=$?
  if (( status == 0 )) \
      || ! grep -Fq "$method" "$output" \
      || ! grep -Fq "$summary" "$output"; then
    printf '[FAIL] %s skeleton이 지정된 test/result mapping으로 실패하지 않았습니다.\n' "$label" >&2
    cat "$output" >&2
    return 1
  fi
  for detail in "$@"; do
    if ! grep -Fq "$detail" "$output"; then
      printf '[FAIL] %s skeleton 지정 실패 메시지가 없습니다: %s\n' "$label" "$detail" >&2
      cat "$output" >&2
      return 1
    fi
  done
  if grep -Eqi \
      'COMPILATION ERROR|Could not resolve dependencies|Non-resolvable parent|No tests were executed|Failed to load ApplicationContext|Could not bind properties|Could not find a valid Docker environment|ContainerLaunchException|Failed to start container|Plugin .* could not be resolved|Unknown lifecycle phase' \
      "$output"; then
    printf '[FAIL] %s skeleton이 학습 계약이 아닌 준비·compile·context·Docker 오류로 실패했습니다.\n' "$label" >&2
    cat "$output" >&2
    return 1
  fi
  python3 "$ROOT_DIR/scripts/check-skeleton-report.py" "$label" "$ROOT_DIR" \
    || return 1
  printf '[PASS] %s skeleton 지정 실패: %s\n' "$label" "$selector"
}

run_requested() {
  local requested=${1:-all} matched=0
  if [[ "$requested" == all || "$requested" == application-boundaries ]]; then
    verify_contract application-boundaries \
      exercises/application-boundaries/skeleton/pom.xml \
      dev.guides.spring.boundaries.PreviewControllerTest#rejectsBusinessPolicyAsConflict \
      'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0' \
      'Status expected:<409> but was:<200>'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == security-boundaries ]]; then
    verify_contract security-boundaries \
      exercises/security-boundaries/skeleton/pom.xml \
      dev.guides.spring.security.SecurityBoundaryTest#authenticationIsRequired \
      'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0' \
      'Status expected:<401> but was:<200>'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == transaction-locking ]]; then
    verify_contract transaction-locking \
      exercises/transaction-locking/skeleton/pom.xml \
      dev.guides.spring.locking.InventoryConcurrencyIntegrationTest#exactlyTenOfTwentyConcurrentDebitsSucceed \
      'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0' \
      'expected: 10' 'but was: 20'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == idempotency-outbox ]]; then
    verify_contract idempotency-outbox \
      exercises/idempotency-outbox/skeleton/pom.xml \
      dev.guides.spring.idempotency.IdempotencyIntegrationTest#concurrentSameKeyCreatesOneOperationWhenRedisFails \
      'Tests run: 1, Failures: 0, Errors: 1, Skipped: 0' \
      'java.util.concurrent.ExecutionException' \
      'duplicate key value violates unique constraint "operation_record_pkey"'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == kafka-avro-contract ]]; then
    verify_contract kafka-avro-contract \
      exercises/kafka-avro-contract/skeleton/pom.xml \
      dev.guides.spring.kafkaavro.KafkaAvroContractIntegrationTest#preservesPartitionKeyAndAvroFields \
      'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0' \
      'Expecting actual not to be null'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == resilient-http-client ]]; then
    verify_contract resilient-http-client \
      exercises/resilient-http-client/skeleton/pom.xml \
      dev.guides.spring.failclosed.DecisionClientIntegrationTest#retryBudgetReusesTheSameRequestIdentifier \
      'Tests run: 1, Failures: 0, Errors: 1, Skipped: 0' \
      'dev.guides.spring.failclosed.DependencyUnavailableException' \
      '외부 시스템을 사용할 수 없습니다.'
    matched=1
  fi
  if [[ "$requested" == all || "$requested" == single-service-capstone ]]; then
    verify_contract single-service-capstone \
      exercises/single-service-capstone/skeleton/pom.xml \
      dev.guides.spring.capstone.PublicationServiceIntegrationTest#creationWritesPublicationOutboxCacheAndMetric \
      'Tests run: 1, Failures: 1, Errors: 0, Skipped: 0' \
      'expected: 1L' 'but was: 0L'
    matched=1
  fi
  (( matched == 1 )) || fail "알 수 없는 skeleton 계약입니다: $requested"
}

[[ $# -le 1 ]] || fail "사용법: scripts/verify-skeletons.sh [contract-name]"
run_requested "${1:-all}"
