#!/usr/bin/env bash
set -Eeuo pipefail

GUIDE_ID="backend-spring-boot"
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
MARKER="$ROOT_DIR/.guide/$GUIDE_ID/prepared.json"
POSTGRES_IMAGE="postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
REDIS_IMAGE="redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005"
RYUK_IMAGE="testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0"
KAFKA_IMAGE="apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"
TEMP_DIR=""
WORK_DIR=""
RUN_ID="backend-spring-boot-$$-$(date +%s)"
PASS_COUNT=0
FAIL_COUNT=0
RESULT_PRINTED=0
ACTIVE_PID=""

preflight_fail() {
  printf '[FAIL] %s\nRESULT: FAIL\n' "$*" >&2
  exit 1
}

[[ -n "${VERIFY_LOG:-}" ]] \
  || preflight_fail "저장소 밖의 절대 로그 경로를 VERIFY_LOG로 지정해야 합니다."
[[ "$VERIFY_LOG" == /* ]] \
  || preflight_fail "VERIFY_LOG는 절대 경로여야 합니다: $VERIFY_LOG"
python3 - "$ROOT_DIR" "$VERIFY_LOG" <<'PY' \
  || preflight_fail "VERIFY_LOG는 저장소 밖에 있어야 합니다: $VERIFY_LOG"
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
log = Path(sys.argv[2]).resolve()
try:
    log.relative_to(root)
except ValueError:
    raise SystemExit(0)
raise SystemExit(1)
PY
[[ -d "$(dirname -- "$VERIFY_LOG")" ]] \
  || preflight_fail "VERIFY_LOG 상위 디렉터리가 없습니다: $(dirname -- "$VERIFY_LOG")"
: >"$VERIFY_LOG" || preflight_fail "VERIFY_LOG에 쓸 수 없습니다: $VERIFY_LOG"
exec > >(tee -a "$VERIFY_LOG") 2>&1

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  printf '[PASS] %s\n' "$*"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

source_fingerprint() {
  python3 "$ROOT_DIR/scripts/source_fingerprint.py" "$ROOT_DIR"
}

index_fingerprint() {
  git -C "$ROOT_DIR" ls-files -s -z | shasum -a 256 | awk '{print $1}'
}

cleanup_run_containers() {
  command -v docker >/dev/null 2>&1 || return 0
  while IFS= read -r container_id; do
    [[ -n "$container_id" ]] || continue
    docker rm -f "$container_id" >/dev/null 2>&1 || true
  done < <(docker ps -aq --filter "label=dev.guides.verify-run=$RUN_ID" 2>/dev/null || true)
}

terminate_process_tree() {
  local process_id="$1"
  local child_id
  while IFS= read -r child_id; do
    [[ -n "$child_id" ]] || continue
    terminate_process_tree "$child_id"
  done < <(pgrep -P "$process_id" 2>/dev/null || true)
  kill -TERM "$process_id" >/dev/null 2>&1 || true
}

terminate_active_child() {
  local attempt
  [[ -n "$ACTIVE_PID" ]] || return 0
  terminate_process_tree "$ACTIVE_PID"
  for attempt in {1..20}; do
    kill -0 "$ACTIVE_PID" >/dev/null 2>&1 || break
    sleep 0.1
  done
  kill -KILL "$ACTIVE_PID" >/dev/null 2>&1 || true
  wait "$ACTIVE_PID" >/dev/null 2>&1 || true
  ACTIVE_PID=""
}

finish() {
  local status=$?
  terminate_active_child
  cleanup_run_containers
  [[ -z "$TEMP_DIR" ]] || rm -rf -- "$TEMP_DIR"
  if (( RESULT_PRINTED == 0 )); then
    if (( status == 0 )); then
      printf 'RESULT: PASS\n'
    else
      (( FAIL_COUNT > 0 )) || FAIL_COUNT=1
      printf 'SUMMARY: passed=%d failed=%d skipped=0\n' "$PASS_COUNT" "$FAIL_COUNT"
      printf 'LOG: %s\n' "$VERIFY_LOG"
      printf 'RESULT: FAIL\n'
    fi
  fi
  exit "$status"
}
trap finish EXIT
trap 'terminate_active_child; exit 130' INT
trap 'terminate_active_child; exit 143' TERM
trap 'terminate_active_child; exit 129' HUP

need_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "필수 명령을 찾을 수 없습니다: $1"
}

snapshot_testcontainers() {
  local prefix="$1"
  docker ps -aq --filter label=org.testcontainers=true | sort \
    >"$TEMP_DIR/$prefix.containers"
  docker network ls -q --filter label=org.testcontainers=true | sort \
    >"$TEMP_DIR/$prefix.networks"
  docker volume ls -q --filter label=org.testcontainers=true | sort \
    >"$TEMP_DIR/$prefix.volumes"
}

run_maven() {
  local status=0
  (
    cd "$WORK_DIR"
    export MAVEN_USER_HOME="$MAVEN_HOME_DIR"
    exec ./mvnw -B -ntp -o \
      -Dmaven.repo.local="$MAVEN_REPOSITORY" "$@"
  ) &
  ACTIVE_PID=$!
  wait "$ACTIVE_PID" || status=$?
  ACTIVE_PID=""
  return "$status"
}

expect_test_failure() {
  local exercise="$1"
  local log="$TEMP_DIR/skeleton-$exercise.log"
  local pom="$WORK_DIR/exercises/$exercise/skeleton/pom.xml"

  printf '[INFO] skeleton 실패 계약: %s\n' "$exercise"
  if run_maven -f "$pom" test >"$log" 2>&1; then
    cat "$log"
    fail "$exercise skeleton이 예상과 달리 통과했습니다."
  fi
  if grep -Eqi \
    'COMPILATION ERROR|Could not resolve|Non-resolvable parent|No tests were executed|Could not find a valid Docker environment|ContainerLaunchException|Failed to start container|Plugin .* could not be resolved|Unknown lifecycle phase' \
    "$log"; then
    cat "$log"
    fail "$exercise skeleton이 학습 결함이 아닌 준비·컴파일·Docker 오류로 실패했습니다."
  fi
  if ! grep -Eq \
    'Tests run: [0-9]+, Failures: [1-9][0-9]*|Tests run: [0-9]+, Failures: [0-9]+, Errors: [1-9][0-9]*' \
    "$log"; then
    cat "$log"
    fail "$exercise skeleton에서 Surefire test failure를 확인하지 못했습니다."
  fi
  pass "skeleton의 의도한 test failure: $exercise"
}

cd "$ROOT_DIR"
for command_name in git bash java python3 docker shasum awk tee pgrep; do
  need_command "$command_name"
done
pass "필수 명령 확인"

[[ "$(git rev-parse --show-toplevel 2>/dev/null || true)" == "$ROOT_DIR" ]] \
  || fail "저장소 루트의 verify.sh를 실행해야 합니다."
[[ -f "$MARKER" ]] || fail "prepare marker가 없습니다. 먼저 ./prepare.sh를 실행하세요."
docker info >/dev/null 2>&1 || fail "Docker daemon에 연결할 수 없습니다."
pass "저장소와 Docker daemon 확인"

before_source="$(source_fingerprint)"
before_index="$(index_fingerprint)"
python3 - "$MARKER" "$GUIDE_ID" "$before_source" <<'PY' \
  || fail "prepare marker가 손상되었거나 현재 source와 맞지 않습니다. ./prepare.sh를 다시 실행하세요."
import json
import sys
from pathlib import Path

marker = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
required = {
    "schema", "guide_id", "input_fingerprint", "java", "maven", "docker",
    "maven_home", "maven_repository", "images",
}
if set(marker) != required:
    raise SystemExit(1)
if marker["schema"] != 1 or marker["guide_id"] != sys.argv[2]:
    raise SystemExit(1)
if marker["input_fingerprint"] != sys.argv[3]:
    raise SystemExit(1)
if not Path(marker["maven_home"]).is_dir() or not Path(marker["maven_repository"]).is_dir():
    raise SystemExit(1)
PY
MAVEN_HOME_DIR="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["maven_home"])' "$MARKER")"
MAVEN_REPOSITORY="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["maven_repository"])' "$MARKER")"
for image in "$POSTGRES_IMAGE" "$REDIS_IMAGE" "$RYUK_IMAGE" "$KAFKA_IMAGE"; do
  docker image inspect "$image" >/dev/null 2>&1 \
    || fail "준비된 Docker image가 없습니다: $image"
done
pass "fingerprint·cache·immutable image marker 확인"

TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-spring-verify.XXXXXX")"
WORK_DIR="$TEMP_DIR/work"
snapshot_testcontainers before
python3 - "$ROOT_DIR" "$WORK_DIR" <<'PY'
import shutil
import sys
from pathlib import Path

source = Path(sys.argv[1])
destination = Path(sys.argv[2])

def ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in {".git", ".guide", "target", "__pycache__"}}
    ignored.update(name for name in names if name.endswith(".pyc"))
    return ignored

shutil.copytree(source, destination, symlinks=True, copy_function=shutil.copy2, ignore=ignore)
PY
pass "현재 working tree를 외부 임시 디렉터리에 격리 복사"

export GUIDE_VERIFY_RUN_ID="$RUN_ID"
export TESTCONTAINERS_PULL_POLICY="dev.guides.spring.testinfra.NeverPullPolicy"
export TESTCONTAINERS_RYUK_CONTAINER_IMAGE="$RYUK_IMAGE"
export TESTCONTAINERS_CHECKS_DISABLE="true"

(
  cd "$WORK_DIR"
  python3 scripts/validate.py
  python3 scripts/validator_self_test.py
  bash -n prepare.sh verify.sh scripts/mvn-guide.sh
)
pass "validator·mutant suite·shell 문법"

run_maven -DskipTests compile
pass "reference 전체 offline compile"
run_maven verify
pass "reference와 integration test 전체 offline 검증"

skeletons=(
  "application-boundaries"
  "security-boundaries"
  "transaction-locking"
  "idempotency-outbox"
  "kafka-avro-contract"
  "resilient-http-client"
  "single-service-capstone"
)
for exercise in "${skeletons[@]}"; do
  expect_test_failure "$exercise"
done

for attempt in {1..30}; do
  if [[ -z "$(docker ps -aq --filter "label=dev.guides.verify-run=$RUN_ID")" ]]; then
    break
  fi
  sleep 1
done
cleanup_run_containers
[[ -z "$(docker ps -aq --filter "label=dev.guides.verify-run=$RUN_ID")" ]] \
  || fail "이 실행의 Testcontainers container가 남았습니다."

for attempt in {1..30}; do
  snapshot_testcontainers after
  new_testcontainers_resource=0
  for kind in containers networks volumes; do
    if [[ -n "$(comm -13 "$TEMP_DIR/before.$kind" "$TEMP_DIR/after.$kind" || true)" ]]; then
      new_testcontainers_resource=1
      break
    fi
  done
  (( new_testcontainers_resource == 0 )) && break
  sleep 1
done
snapshot_testcontainers after
for kind in containers networks volumes; do
  remaining="$(comm -13 "$TEMP_DIR/before.$kind" "$TEMP_DIR/after.$kind" || true)"
  [[ -z "$remaining" ]] || fail "검증 뒤 새 Testcontainers $kind 자원이 남았습니다: $remaining"
done
pass "실행 범위 Docker 자원 정리와 기존 자원 보존"

after_source="$(source_fingerprint)"
after_index="$(index_fingerprint)"
[[ "$before_source" == "$after_source" ]] \
  || fail "verify.sh가 원본 source bytes, mode 또는 symlink를 변경했습니다."
[[ "$before_index" == "$after_index" ]] \
  || fail "verify.sh가 원본 Git index를 변경했습니다."
pass "원본 source와 Git index 전후 동일"

RESULT_PRINTED=1
printf 'SUMMARY: passed=%d failed=0 skipped=0\n' "$PASS_COUNT"
printf 'LOG: %s\n' "$VERIFY_LOG"
printf 'RESULT: PASS\n'
