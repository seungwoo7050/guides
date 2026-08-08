#!/usr/bin/env bash
set -Eeuo pipefail

GUIDE_ID="backend-spring-boot"
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
STATE_TOOL="$ROOT_DIR/scripts/guide_state.py"
RUNNER="$ROOT_DIR/scripts/run_in_session.py"
CACHE_DIR="$ROOT_DIR/.guide/$GUIDE_ID"
MAVEN_HOME_DIR="$CACHE_DIR/maven-home"
MAVEN_REPOSITORY="$CACHE_DIR/m2"
MARKER="$CACHE_DIR/prepared.json"
WORK_ROOT=""
WORK_TREE=""
ACTIVE_PID=""
ACTIVE_PGID=""
SOURCE_BEFORE=""
INDEX_BEFORE=""
SUCCESS=0
FINISHED=0

POSTGRES_IMAGE="postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
REDIS_IMAGE="redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005"
RYUK_IMAGE="testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0"
KAFKA_IMAGE="apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"
IMAGES=("$POSTGRES_IMAGE" "$REDIS_IMAGE" "$RYUK_IMAGE" "$KAFKA_IMAGE")

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

pass() {
  printf '[PASS] %s\n' "$*"
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

run_managed() {
  local status=0 observed_pgid="" attempt
  python3 "$RUNNER" "$@" &
  ACTIVE_PID=$!
  ACTIVE_PGID=$ACTIVE_PID
  for attempt in {1..100}; do
    observed_pgid="$(ps -o pgid= -p "$ACTIVE_PID" 2>/dev/null | tr -d ' ' || true)"
    [[ "$observed_pgid" == "$ACTIVE_PID" ]] && break
    kill -0 "$ACTIVE_PID" >/dev/null 2>&1 || break
    sleep 0.01
  done
  wait "$ACTIVE_PID" || status=$?
  ACTIVE_PID=""
  ACTIVE_PGID=""
  return "$status"
}

finish() {
  local status=$? source_after="" index_after=""
  (( FINISHED == 0 )) || exit "$status"
  FINISHED=1
  trap - EXIT HUP INT TERM
  stop_active_group

  if [[ -n "$SOURCE_BEFORE" ]]; then
    source_after="$(python3 "$STATE_TOOL" capture "$ROOT_DIR" 2>/dev/null || true)"
    index_after="$(python3 "$STATE_TOOL" index-state "$ROOT_DIR" 2>/dev/null || true)"
    if [[ -z "$source_after" || -z "$index_after" \
          || "$SOURCE_BEFORE" != "$source_after" \
          || "$INDEX_BEFORE" != "$index_after" ]]; then
      printf '[FAIL] prepare가 원본 source 또는 Git index raw bytes·staged entries를 변경했습니다.\n' >&2
      status=1
    fi
  fi

  [[ -z "$WORK_ROOT" || ! -d "$WORK_ROOT" ]] || rm -rf -- "$WORK_ROOT"
  if (( status != 0 || SUCCESS != 1 )); then
    rm -f -- "$MARKER"
    printf 'PREPARE RESULT: FAIL\n' >&2
    (( status == 0 )) && status=1
    exit "$status"
  fi
  printf 'PREPARE RESULT: PASS\n'
  exit 0
}

handle_signal() {
  local code=$1
  trap - HUP INT TERM
  stop_active_group
  exit "$code"
}

trap finish EXIT
trap 'handle_signal 129' HUP
trap 'handle_signal 130' INT
trap 'handle_signal 143' TERM

need_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "필수 명령을 찾을 수 없습니다: $1"
}

run_maven() {
  run_managed env MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
    bash -c '
      work_tree=$1
      repository=$2
      shift 2
      cd -- "$work_tree"
      exec ./mvnw -B -ntp -Dmaven.repo.local="$repository" "$@"
    ' bash "$WORK_TREE" "$MAVEN_REPOSITORY" "$@"
}

main() {
  local command_name java_major python_version python_major python_minor
  local copied_source pom image
  [[ $# -eq 0 ]] || fail "사용법: ./prepare.sh"
  [[ "$(pwd -P)" == "$ROOT_DIR" ]] || fail "저장소 루트에서 ./prepare.sh를 실행해야 합니다."

  for command_name in git bash java javac python3 docker shasum awk ps tr; do
    need_command "$command_name"
  done
  [[ -x "$STATE_TOOL" && -x "$RUNNER" ]] \
    || fail "상태 또는 process-group helper가 실행 가능하지 않습니다."
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || fail "Git 작업 트리에서 실행해야 합니다."
  [[ "$(cd -- "$(git rev-parse --show-toplevel)" && pwd -P)" == "$ROOT_DIR" ]] \
    || fail "저장소 루트의 prepare.sh를 실행해야 합니다."
  for executable in mvnw prepare.sh verify.sh scripts/mvn-guide.sh \
      scripts/check-skeleton-report.py scripts/guide_state.py \
      scripts/check-workspace.sh scripts/new-workspace.sh \
      scripts/check-effective-pom.py \
      scripts/run_in_session.py scripts/verify-skeletons.sh \
      scripts/verify-workspaces.sh scripts/workspace.py; do
    [[ -x "$executable" ]] || fail "실행 권한이 없습니다: $executable"
  done
  pass "필수 명령과 일반 clone/linked worktree 저장소 루트 확인"

  grep -Fq 'wrapperVersion=3.3.4' .mvn/wrapper/maven-wrapper.properties \
    || fail "Maven Wrapper 3.3.4 설정이 아닙니다."
  grep -Fq 'apache-maven/3.9.16/apache-maven-3.9.16-bin.zip' \
    .mvn/wrapper/maven-wrapper.properties \
    || fail "Apache Maven 3.9.16 배포 URL이 아닙니다."
  grep -Fq 'distributionSha256Sum=5af3b743dd8b876b5c45da33b676251e5f1687712644abb4ee519ca56e1d89ce' \
    .mvn/wrapper/maven-wrapper.properties \
    || fail "Apache Maven 3.9.16 SHA-256이 다릅니다."

  java_major="$(java -version 2>&1 | sed -n '1s/.*version "\([0-9][0-9]*\).*/\1/p')"
  [[ "$java_major" == 21 ]] || fail "JDK 21이 필요합니다. 현재=$java_major"
  python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  python_major="${python_version%%.*}"
  python_minor="${python_version#*.}"
  (( python_major > 3 || (python_major == 3 && python_minor >= 10) )) \
    || fail "Python 3.10 이상이 필요합니다. 현재=$python_version"
  docker info >/dev/null 2>&1 || fail "Docker daemon에 연결할 수 없습니다."
  pass "JDK 21, Python $python_version, Maven Wrapper와 Docker daemon 확인"

  SOURCE_BEFORE="$(python3 "$STATE_TOOL" capture "$ROOT_DIR")"
  INDEX_BEFORE="$(python3 "$STATE_TOOL" index-state "$ROOT_DIR")"
  mkdir -p -- "$MAVEN_HOME_DIR" "$MAVEN_REPOSITORY"
  [[ ! -L "$MAVEN_HOME_DIR" && ! -L "$MAVEN_REPOSITORY" ]] \
    || fail "Maven cache 경로는 symlink일 수 없습니다."
  rm -f -- "$MARKER"

  WORK_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/guide-spring-prepare.XXXXXX")"
  WORK_TREE="$WORK_ROOT/repository"
  mkdir -p -- "$WORK_TREE"
  run_managed python3 "$STATE_TOOL" copy "$ROOT_DIR" "$WORK_TREE" \
    || fail "준비용 외부 복사본을 만들지 못했습니다."
  copied_source="$(python3 "$WORK_TREE/scripts/guide_state.py" capture "$WORK_TREE")"
  [[ "$copied_source" == "$SOURCE_BEFORE" ]] \
    || fail "준비용 외부 복사본이 현재 working tree와 다릅니다."
  pass "현재 working tree를 source bytes·mode·symlink 그대로 외부에 복사"

  run_maven --version >/dev/null
  run_maven dependency:get \
    -Dartifact=org.apache.maven.surefire:surefire-junit-platform:3.5.6 \
    -Dtransitive=true
  run_maven -DskipTests dependency:go-offline
  run_maven org.apache.maven.plugins:maven-help-plugin:3.5.1:effective-pom \
    -Doutput="$WORK_ROOT/effective-pom.xml"
  run_managed python3 "$WORK_TREE/scripts/check-effective-pom.py" \
    "$WORK_ROOT/effective-pom.xml"
  run_maven -DskipTests verify
  for pom in "$WORK_TREE"/exercises/*/skeleton/pom.xml; do
    run_maven -f "$pom" -DskipTests dependency:go-offline
    run_maven -f "$pom" -DskipTests verify
  done
  run_maven -o -DskipTests verify
  pass "외부 격리 복사본에서 Maven Wrapper·plugin·전체 offline cache 준비"

  for image in "${IMAGES[@]}"; do
    printf '[INFO] Docker image 준비: %s\n' "$image"
    run_managed docker pull "$image" >/dev/null
    run_managed docker image inspect "$image" >/dev/null
  done
  pass "immutable Docker image reference와 image ID 준비"

  [[ "$SOURCE_BEFORE" == "$(python3 "$STATE_TOOL" capture "$ROOT_DIR")" ]] \
    || fail "prepare가 source bytes, mode 또는 symlink를 변경했습니다."
  [[ "$INDEX_BEFORE" == "$(python3 "$STATE_TOOL" index-state "$ROOT_DIR")" ]] \
    || fail "prepare가 Git index raw bytes 또는 staged entries를 변경했습니다."
  pass "prepare 전후 원본 source와 Git index raw bytes·staged entries 불변"

  run_managed python3 "$STATE_TOOL" write-marker "$MARKER" "$ROOT_DIR" "$SOURCE_BEFORE"
  run_managed python3 "$STATE_TOOL" validate-marker "$MARKER" "$ROOT_DIR" "$SOURCE_BEFORE" \
    >/dev/null
  pass "정확한 schema·tool·cache·image ID 준비 marker 기록"
  SUCCESS=1
}

main "$@"
