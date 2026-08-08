#!/usr/bin/env bash
set -Eeuo pipefail

GUIDE_ID="backend-spring-boot"
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
STATE_TOOL="$ROOT_DIR/scripts/guide_state.py"
RUNNER="$ROOT_DIR/scripts/run_in_session.py"
MARKER="$ROOT_DIR/.guide/$GUIDE_ID/prepared.json"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEFAULT_LOG="/tmp/guide-backend-spring-boot-verify-$TIMESTAMP-$$.log"
REQUESTED_LOG="${VERIFY_LOG:-$DEFAULT_LOG}"
FALLBACK_LOG="/tmp/guide-backend-spring-boot-preflight-$TIMESTAMP-$$.log"
VERIFY_LOG=""
WORK_ROOT=""
WORK_TREE=""
ACTIVE_PID=""
ACTIVE_PGID=""
SOURCE_BEFORE=""
INDEX_BEFORE=""
COPY_BEFORE=""
RUN_ID="backend-spring-boot-$TIMESTAMP-$$-${RANDOM:-0}"
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
FINISHED=0
STATE_CHECKED=0
DOCKER_BASELINE_READY=0
DOCKER_CLEANED=0

POSTGRES_IMAGE="postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
REDIS_IMAGE="redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005"
RYUK_IMAGE="testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0"
KAFKA_IMAGE="apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"

canonical_path() {
  python3 - "$1" <<'PY'
import sys
from pathlib import Path

try:
    print(Path(sys.argv[1]).resolve(strict=False))
except (OSError, RuntimeError) as error:
    raise SystemExit(str(error))
PY
}

emit_raw_summary() {
  local destination=$1 message=$2
  umask 077
  mkdir -p -- "$(dirname -- "$destination")" 2>/dev/null || true
  {
    printf '[FAIL] %s\n' "$message"
    printf 'SUMMARY: passed=0 failed=1 skipped=0\n'
    printf 'VERIFY LOG: %s\n' "$destination"
    printf 'RESULT: FAIL\n'
  } | tee "$destination" >&2
}

log_preflight_fail() {
  local message=$1 fallback
  fallback="$(canonical_path "$FALLBACK_LOG" 2>/dev/null || printf '%s' "$FALLBACK_LOG")"
  emit_raw_summary "$fallback" "$message"
  exit 2
}

resolve_log() {
  local canonical_root canonical_log parent after_parent
  [[ "$REQUESTED_LOG" == /* ]] \
    || log_preflight_fail "VERIFY_LOG는 저장소 밖의 절대 경로여야 합니다: $REQUESTED_LOG"
  canonical_root="$(canonical_path "$ROOT_DIR")" \
    || log_preflight_fail "저장소 경로를 해석하지 못했습니다."
  canonical_log="$(canonical_path "$REQUESTED_LOG")" \
    || log_preflight_fail "VERIFY_LOG 경로를 해석하지 못했습니다: $REQUESTED_LOG"
  case "$canonical_log" in
    "$canonical_root"|"$canonical_root"/*)
      log_preflight_fail "VERIFY_LOG는 저장소 밖이어야 합니다: $canonical_log"
      ;;
  esac
  parent="$(dirname -- "$canonical_log")"
  mkdir -p -- "$parent" \
    || log_preflight_fail "VERIFY_LOG parent를 만들 수 없습니다: $parent"
  after_parent="$(canonical_path "$parent")" \
    || log_preflight_fail "VERIFY_LOG parent를 다시 확인하지 못했습니다: $parent"
  case "$after_parent/$(basename -- "$canonical_log")" in
    "$canonical_root"|"$canonical_root"/*)
      log_preflight_fail "VERIFY_LOG parent가 저장소 안으로 바뀌었습니다."
      ;;
  esac
  VERIFY_LOG="$canonical_log"
  umask 077
  : >"$VERIFY_LOG" || log_preflight_fail "VERIFY_LOG를 쓸 수 없습니다: $VERIFY_LOG"
}

resolve_log

emit_line() {
  printf '%s\n' "$*"
  printf '%s\n' "$*" >>"$VERIFY_LOG"
}

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  emit_line "[PASS] $*"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  emit_line "[FAIL] $*"
  return 1
}

preflight_fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  emit_line "[FAIL] $*"
  exit 2
}

fatal() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  emit_line "[FAIL] $*"
  exit 1
}

process_group_exists() {
  [[ -n "${ACTIVE_PGID:-}" ]] \
    && kill -0 -- "-$ACTIVE_PGID" >/dev/null 2>&1
}

stop_active_group() {
  local attempt
  [[ -n "${ACTIVE_PID:-}" ]] || return 0
  kill -TERM -- "-$ACTIVE_PGID" >/dev/null 2>&1 || true
  for attempt in {1..50}; do
    process_group_exists || break
    sleep 0.1
  done
  process_group_exists \
    && kill -KILL -- "-$ACTIVE_PGID" >/dev/null 2>&1 || true
  wait "$ACTIVE_PID" >/dev/null 2>&1 || true
  ACTIVE_PID=""
  ACTIVE_PGID=""
}

start_managed() {
  local output=$1 observed_pgid="" attempt
  shift
  python3 "$RUNNER" "$@" >>"$output" 2>&1 &
  ACTIVE_PID=$!
  ACTIVE_PGID=$ACTIVE_PID
  for attempt in {1..100}; do
    observed_pgid="$(ps -o pgid= -p "$ACTIVE_PID" 2>/dev/null | tr -d ' ' || true)"
    [[ "$observed_pgid" == "$ACTIVE_PID" ]] && break
    kill -0 "$ACTIVE_PID" >/dev/null 2>&1 || break
    sleep 0.01
  done
}

run_managed_to() {
  local output=$1 status=0
  shift
  start_managed "$output" "$@"
  wait "$ACTIVE_PID" || status=$?
  ACTIVE_PID=""
  ACTIVE_PGID=""
  return "$status"
}

run_managed() {
  run_managed_to "$VERIFY_LOG" "$@"
}

capture_managed() {
  local variable=$1 output value
  shift
  output="$(mktemp "/tmp/guide-spring-capture.XXXXXX")" \
    || return 1
  if ! run_managed_to "$output" "$@"; then
    cat "$output" >>"$VERIFY_LOG"
    rm -f -- "$output"
    return 1
  fi
  value="$(cat "$output")"
  rm -f -- "$output"
  printf -v "$variable" '%s' "$value"
}

run_check() {
  local label=$1
  shift
  {
    printf '\nCHECK: %s\n' "$label"
    printf 'COMMAND:'
    printf ' %q' "$@"
    printf '\n'
  } >>"$VERIFY_LOG"
  if run_managed "$@"; then
    pass "$label"
  else
    local status=$?
    fatal "$label (exit=$status)"
  fi
}

snapshot_docker_direct() {
  local prefix=$1
  {
    docker ps -aq --filter label=org.testcontainers=true 2>/dev/null || true
    docker ps -aq --filter "label=dev.guides.verify-run=$RUN_ID" 2>/dev/null || true
  } | sort -u >"$WORK_ROOT/$prefix.containers"
  {
    docker network ls -q --filter label=org.testcontainers=true 2>/dev/null || true
    docker network ls -q --filter "label=dev.guides.verify-run=$RUN_ID" 2>/dev/null || true
  } | sort -u >"$WORK_ROOT/$prefix.networks"
  {
    docker volume ls -q --filter label=org.testcontainers=true 2>/dev/null || true
    docker volume ls -q --filter "label=dev.guides.verify-run=$RUN_ID" 2>/dev/null || true
  } | sort -u >"$WORK_ROOT/$prefix.volumes"
}

snapshot_docker_managed() {
  local prefix=$1 kind command
  for kind in containers networks volumes; do
    case "$kind" in
      containers) command='docker ps -aq --filter label=org.testcontainers=true; docker ps -aq --filter "label=dev.guides.verify-run=$GUIDE_VERIFY_RUN_ID"' ;;
      networks) command='docker network ls -q --filter label=org.testcontainers=true; docker network ls -q --filter "label=dev.guides.verify-run=$GUIDE_VERIFY_RUN_ID"' ;;
      volumes) command='docker volume ls -q --filter label=org.testcontainers=true; docker volume ls -q --filter "label=dev.guides.verify-run=$GUIDE_VERIFY_RUN_ID"' ;;
    esac
    run_managed_to "$WORK_ROOT/$prefix.$kind.raw" \
      env GUIDE_VERIFY_RUN_ID="$RUN_ID" bash -c "$command" \
      || return 1
    sort -u "$WORK_ROOT/$prefix.$kind.raw" >"$WORK_ROOT/$prefix.$kind"
  done
  DOCKER_BASELINE_READY=1
}

remove_new_docker_resources() {
  local attempt kind identifier remaining=0
  (( DOCKER_BASELINE_READY == 1 )) || return 0
  for attempt in {1..30}; do
    snapshot_docker_direct current
    while IFS= read -r identifier; do
      [[ -n "$identifier" ]] || continue
      docker rm -f "$identifier" >/dev/null 2>&1 || true
    done < <(comm -13 "$WORK_ROOT/before.containers" "$WORK_ROOT/current.containers")
    while IFS= read -r identifier; do
      [[ -n "$identifier" ]] || continue
      docker network rm "$identifier" >/dev/null 2>&1 || true
    done < <(comm -13 "$WORK_ROOT/before.networks" "$WORK_ROOT/current.networks")
    while IFS= read -r identifier; do
      [[ -n "$identifier" ]] || continue
      docker volume rm -f "$identifier" >/dev/null 2>&1 || true
    done < <(comm -13 "$WORK_ROOT/before.volumes" "$WORK_ROOT/current.volumes")
    snapshot_docker_direct after
    remaining=0
    for kind in containers networks volumes; do
      [[ -z "$(comm -13 "$WORK_ROOT/before.$kind" "$WORK_ROOT/after.$kind")" ]] \
        || remaining=1
    done
    (( remaining == 0 )) && return 0
    sleep 0.2
  done
  return 1
}

check_original_state() {
  local source_after="" index_after=""
  (( STATE_CHECKED == 0 )) || return 0
  STATE_CHECKED=1
  [[ -n "$SOURCE_BEFORE" && -n "$INDEX_BEFORE" ]] || return 0
  source_after="$(python3 "$STATE_TOOL" capture "$ROOT_DIR" 2>>"$VERIFY_LOG" || true)"
  index_after="$(python3 "$STATE_TOOL" index-state "$ROOT_DIR" 2>>"$VERIFY_LOG" || true)"
  if [[ -n "$source_after" && -n "$index_after" \
        && "$SOURCE_BEFORE" == "$source_after" \
        && "$INDEX_BEFORE" == "$index_after" ]]; then
    pass "원본 source bytes·mode·symlink와 Git index raw bytes·staged entries 불변"
    return 0
  fi
  fail "검증이 원본 source 또는 Git index raw bytes·staged entries를 변경했습니다."
}

print_summary() {
  local result=$1
  emit_line "SUMMARY: passed=$PASS_COUNT failed=$FAIL_COUNT skipped=$SKIP_COUNT"
  emit_line "VERIFY LOG: $VERIFY_LOG"
  emit_line "RESULT: $result"
}

finish() {
  local status=$? result=PASS
  (( FINISHED == 0 )) || exit "$status"
  FINISHED=1
  trap - EXIT HUP INT TERM
  stop_active_group
  if (( DOCKER_CLEANED == 0 && DOCKER_BASELINE_READY == 1 )); then
    if ! remove_new_docker_resources; then
      fail "검증 실행이 만든 Testcontainers container/network/volume을 정리하지 못했습니다."
    fi
    DOCKER_CLEANED=1
  fi
  check_original_state || true
  [[ -z "$WORK_ROOT" || ! -d "$WORK_ROOT" ]] || rm -rf -- "$WORK_ROOT"
  if (( status != 0 || FAIL_COUNT != 0 || SKIP_COUNT != 0 )); then
    result=FAIL
    (( status != 0 )) || status=1
  fi
  print_summary "$result"
  exit "$status"
}

handle_signal() {
  local code=$1 name=$2
  trap - HUP INT TERM
  stop_active_group
  FAIL_COUNT=$((FAIL_COUNT + 1))
  emit_line "[FAIL] $name 신호로 검증이 중단되었습니다."
  exit "$code"
}

trap finish EXIT
trap 'handle_signal 129 HUP' HUP
trap 'handle_signal 130 INT' INT
trap 'handle_signal 143 TERM' TERM

main() {
  local command_name marker_values copied_state copy_after
  [[ $# -eq 0 ]] || preflight_fail "사용법: ./verify.sh"
  [[ "$(pwd -P)" == "$ROOT_DIR" ]] || preflight_fail "저장소 루트에서 ./verify.sh를 실행해야 합니다."
  for command_name in git bash java javac python3 docker sort comm ps tr; do
    command -v "$command_name" >/dev/null 2>&1 \
      || preflight_fail "필수 명령을 찾을 수 없습니다: $command_name"
  done
  [[ -x "$STATE_TOOL" && -x "$RUNNER" ]] \
    || preflight_fail "상태 또는 process-group helper가 실행 가능하지 않습니다."
  pass "필수 명령 확인"

  [[ "$(cd -- "$(git rev-parse --show-toplevel 2>/dev/null)" && pwd -P)" == "$ROOT_DIR" ]] \
    || preflight_fail "저장소 루트의 verify.sh를 실행해야 합니다."
  run_managed_to /dev/null docker info \
    || preflight_fail "Docker daemon에 연결할 수 없습니다."
  pass "저장소와 Docker daemon 확인"

  [[ -f "$MARKER" ]] || preflight_fail "prepare marker가 없습니다. 먼저 ./prepare.sh를 실행하세요."
  capture_managed SOURCE_BEFORE python3 "$STATE_TOOL" capture "$ROOT_DIR" \
    || preflight_fail "검증 전 source fingerprint를 기록하지 못했습니다."
  capture_managed INDEX_BEFORE python3 "$STATE_TOOL" index-state "$ROOT_DIR" \
    || preflight_fail "검증 전 Git index raw bytes와 staged entries를 기록하지 못했습니다."
  if ! capture_managed marker_values \
      python3 "$STATE_TOOL" validate-marker "$MARKER" "$ROOT_DIR" "$SOURCE_BEFORE"; then
    preflight_fail "prepare marker가 손상·만료되었거나 현재 tool/cache/image와 다릅니다."
  fi
  IFS=$'\t' read -r MAVEN_HOME_DIR MAVEN_REPOSITORY <<<"$marker_values"
  export MAVEN_HOME_DIR MAVEN_REPOSITORY
  pass "정확한 preparation fingerprint·tool·cache·immutable image marker 확인"

  WORK_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/guide-spring-verify.XXXXXX")" \
    || fatal "검증용 외부 임시 디렉터리를 만들지 못했습니다."
  WORK_TREE="$WORK_ROOT/repository"
  mkdir -p -- "$WORK_TREE"
  snapshot_docker_managed before \
    || fatal "검증 전 Testcontainers resource baseline을 기록하지 못했습니다."
  run_managed python3 "$STATE_TOOL" copy "$ROOT_DIR" "$WORK_TREE" \
    || fatal "현재 working tree를 격리 디렉터리로 복사하지 못했습니다."
  copied_state="$(python3 "$WORK_TREE/scripts/guide_state.py" capture "$WORK_TREE")"
  [[ "$copied_state" == "$SOURCE_BEFORE" ]] \
    || fatal "격리 복사본이 원본 source bytes·mode·symlink와 다릅니다."
  COPY_BEFORE="$copied_state"
  pass "현재 working tree를 외부 임시 디렉터리에 정확히 격리 복사"

  export GUIDE_VERIFY_RUN_ID="$RUN_ID"
  export GUIDE_MAVEN_REPOSITORY="$MAVEN_REPOSITORY"
  export MAVEN_USER_HOME="$MAVEN_HOME_DIR"
  export TESTCONTAINERS_PULL_POLICY="dev.guides.spring.testinfra.NeverPullPolicy"
  export TESTCONTAINERS_RYUK_CONTAINER_IMAGE="$RYUK_IMAGE"
  export TESTCONTAINERS_CHECKS_DISABLE="true"
  export SPRING_GUIDE_MARKER="$MARKER"
  cd "$WORK_TREE" || fatal "격리 복사본으로 이동하지 못했습니다."

  run_managed python3 scripts/validate.py \
    || fatal "repository exact-tree·문서·실습 validator"
  run_managed python3 scripts/validator_self_test.py \
    || fatal "validator와 검증 계약 mutant suite"
  run_managed ./scripts/verify-workspaces.sh \
    || fatal "7개 학습 workspace 수정본과 canonical 공개 tests"
  run_managed env MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
    ./mvnw -B -ntp -o -Dmaven.repo.local="$MAVEN_REPOSITORY" \
    org.apache.maven.plugins:maven-help-plugin:3.5.1:effective-pom \
    -Doutput="$WORK_ROOT/effective-pom.xml" \
    || fatal "Maven effective POM 생성"
  run_managed python3 scripts/check-effective-pom.py \
    "$WORK_ROOT/effective-pom.xml" --self-test \
    || fatal "effective XML 판본·plugin·dependency pin"
  run_managed bash -c \
    'while IFS= read -r -d "" script; do bash -n "$script" || exit 1; done < <(find . -type f -name "*.sh" -not -path "*/target/*" -print0)' \
    || fatal "전체 shell 문법 검사"
  pass "validator·mutant suite·7개 workspace·shell 문법"

  run_check "reference 전체 offline compile" env MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
    ./mvnw -B -ntp -o -Dmaven.repo.local="$MAVEN_REPOSITORY" -DskipTests compile
  run_check "reference와 integration test 전체 offline 검증" env MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
    ./mvnw -B -ntp -o -Dmaven.repo.local="$MAVEN_REPOSITORY" verify

  for exercise in application-boundaries security-boundaries transaction-locking \
      idempotency-outbox kafka-avro-contract resilient-http-client single-service-capstone; do
    run_check "$exercise skeleton 지정 실패" ./scripts/verify-skeletons.sh "$exercise"
  done

  run_managed make clean || fatal "격리 복사본의 지정 생성물 정리"
  run_managed python3 scripts/validate.py || fatal "정리 뒤 exact-tree 재검사"
  copy_after="$(python3 scripts/guide_state.py capture "$WORK_TREE")"
  [[ "$copy_after" == "$COPY_BEFORE" ]] \
    || fatal "검증이 격리 복사본의 source bytes·mode·symlink를 변경했습니다."

  cd "$ROOT_DIR"
  remove_new_docker_resources \
    || fatal "검증 실행의 Testcontainers container/network/volume 정리"
  DOCKER_CLEANED=1
  pass "실행 범위 Docker 자원 즉시 정리와 baseline sentinel 보존"
}

main "$@"
