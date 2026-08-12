#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_OPTIONAL_LOCKS=0

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="distributed-services"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
MAVEN_HOME_DIR="$STATE_DIR/maven-home"
MAVEN_REPOSITORY="$STATE_DIR/m2"
MARKER="$STATE_DIR/prepared.json"
MARKER_TMP=""
KAFKA_IMAGE="apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"
STATE_TOOL="$ROOT/scripts/repository_state.py"
SOURCE_BEFORE=""
SOURCE_AFTER=""
WORK_DIR=""
COPY_ROOT=""
SUCCESS=0
ACTIVE_PID=""

FINGERPRINT_INPUTS=(
  prepare.sh
  verify.sh
  mvnw
  pom.xml
  .mvn/jvm.config
  .mvn/wrapper/maven-wrapper.properties
  scripts/repository_state.py
  scripts/new-workspace.sh
  scripts/validate.py
  scripts/test-validator.py
  scripts/verify-java.sh
  scripts/verify-skeletons.sh
  scripts/verify-nonjava.sh
  exercises/90-optional-labs/single-broker-kraft/verify.sh
  exercises/90-optional-labs/single-broker-kraft/skeleton/compose.yaml
  exercises/90-optional-labs/single-broker-kraft/reference/compose.yaml
)

while IFS= read -r module_pom; do
  FINGERPRINT_INPUTS+=("${module_pom#"$ROOT/"}")
done < <(find "$ROOT/exercises" -type f -name pom.xml | sort)

log() {
  printf '[prepare] %s\n' "$*"
}

die() {
  printf '[prepare] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

finish() {
  local status=$?
  trap - EXIT HUP INT TERM
  terminate_active_child
  if [[ -n "$SOURCE_BEFORE" && -n "$SOURCE_AFTER" && -x "$STATE_TOOL" ]]; then
    "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_AFTER" >/dev/null 2>&1 \
      || { (( status == 0 )) && status=1; }
    if ! cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
      printf '[prepare] ERROR: preparation changed source files, modes, or symlinks\n' >&2
      (( status == 0 )) && status=1
    fi
  fi
  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
    rm -rf -- "$WORK_DIR"
  fi
  if [[ -n "$MARKER_TMP" ]]; then
    rm -f -- "$MARKER_TMP"
  fi
  rm -f -- "$SOURCE_BEFORE" "$SOURCE_AFTER"
  if (( status != 0 || SUCCESS != 1 )); then
    (( status == 0 )) && status=1
    rm -f -- "$MARKER"
    printf 'PREPARE RESULT: FAIL\n' >&2
    exit "$status"
  fi
  printf 'PREPARE RESULT: PASS\n'
}

signal_exit() {
  local code="$1"
  trap - HUP INT TERM
  terminate_active_child
  exit "$code"
}

terminate_process_tree() {
  local root_pid="$1"
  python3 - "$root_pid" <<'PY'
import os
import signal
import subprocess
import sys
import time

root = int(sys.argv[1])
children: dict[int, list[int]] = {}
for line in subprocess.run(
    ["ps", "-axo", "pid=,ppid="], check=True, capture_output=True, text=True
).stdout.splitlines():
    pid_text, parent_text = line.split()
    children.setdefault(int(parent_text), []).append(int(pid_text))
targets: list[int] = []
stack = [root]
while stack:
    pid = stack.pop()
    targets.append(pid)
    stack.extend(children.get(pid, ()))
for pid in reversed(targets):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
deadline = time.monotonic() + 2.0
alive = targets
while alive and time.monotonic() < deadline:
    remaining = []
    for pid in alive:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        remaining.append(pid)
    alive = remaining
    if alive:
        time.sleep(0.05)
for pid in reversed(alive):
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
PY
}

terminate_active_child() {
  [[ -n "$ACTIVE_PID" ]] || return 0
  terminate_process_tree "$ACTIVE_PID" || true
  wait "$ACTIVE_PID" >/dev/null 2>&1 || true
  ACTIVE_PID=""
}

run_managed() {
  local status=0
  "$@" &
  ACTIVE_PID=$!
  wait "$ACTIVE_PID" || status=$?
  ACTIVE_PID=""
  return "$status"
}

assert_checkout() {
  git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
    || die "run this script from a Git checkout"
  local top
  top="$(git -C "$ROOT" rev-parse --show-toplevel)"
  [[ "$(cd -- "$top" && pwd -P)" == "$ROOT" ]] \
    || die "script root does not match the Git checkout root"
}

assert_runtime() {
  require_command git
  require_command python3
  require_command java
  require_command javac
  require_command docker
  require_command rsync
  [[ -x "$ROOT/mvnw" ]] || die "Maven Wrapper is missing or not executable"
  [[ -x "$STATE_TOOL" ]] || die "repository state helper is missing or not executable"

  python3 - <<'PY' || die "Python 3.10 or newer is required"
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY

  local javac_version major
  javac_version="$(javac -version 2>&1 | awk '{print $2}')"
  major="${javac_version%%.*}"
  [[ "$major" =~ ^[0-9]+$ ]] || die "cannot parse javac version: $javac_version"
  (( major >= 17 && major <= 25 )) \
    || die "JDK 17 through 25 is required: $javac_version"

  docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required"
  docker info >/dev/null 2>&1 || die "Docker daemon is not available"
  [[ "${GUIDE_SKIP_MAVEN:-0}" != "1" && "${GUIDE_SKIP_DOCKER:-0}" != "1" ]] \
    || die "skip flags cannot produce a complete preparation marker"
}

prepare_maven_copy() {
  mkdir -p -- "$MAVEN_HOME_DIR" "$MAVEN_REPOSITORY"
  WORK_DIR="$(mktemp -d "/tmp/guide-distributed-prepare-work.XXXXXX")"
  COPY_ROOT="$WORK_DIR/repository"
  mkdir -p -- "$COPY_ROOT"
  rsync -a \
    --exclude='/.git' \
    --exclude='/.guide/' \
    --exclude='/.workspace/' \
    --exclude='/target/' \
    --exclude='/exercises/**/target/' \
    --exclude='/scripts/**/__pycache__/' \
    --exclude='/exercises/**/__pycache__/' \
    --exclude='/scripts/**/*.pyc' \
    --exclude='/exercises/**/*.pyc' \
    "$ROOT/" "$COPY_ROOT/"
}

prepare_maven_build() {
  log "resolving Maven Wrapper, plugins, and dependencies"
  (
    cd "$COPY_ROOT"
    MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
      ./mvnw -B -ntp \
      -Dmaven.repo.local="$MAVEN_REPOSITORY" \
      -DskipTests clean package
    MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
      ./mvnw -o -B -ntp \
      -Dmaven.repo.local="$MAVEN_REPOSITORY" \
      -DskipTests clean package
  )
}

prepare_docker() {
  log "pulling $KAFKA_IMAGE"
  run_managed docker pull "$KAFKA_IMAGE"
  docker image inspect "$KAFKA_IMAGE" >/dev/null
}

write_marker_file() {
  python3 - <<'PY'
import json
import os
from pathlib import Path

marker = Path(os.environ["GUIDE_MARKER"])
marker.write_text(json.dumps({
    "schema": 1,
    "guide_id": os.environ["GUIDE_ID_VALUE"],
    "preparation_fingerprint": os.environ["GUIDE_FINGERPRINT"],
    "maven_home": os.environ["GUIDE_MAVEN_HOME"],
    "maven_repository": os.environ["GUIDE_M2"],
    "java_version": os.environ["GUIDE_JAVA_VERSION"],
    "javac_version": os.environ["GUIDE_JAVAC_VERSION"],
    "maven_version": os.environ["GUIDE_MAVEN_VERSION"],
    "docker_version": os.environ["GUIDE_DOCKER_VERSION"],
    "docker_compose_version": os.environ["GUIDE_COMPOSE_VERSION"],
    "python_version": os.environ["GUIDE_PYTHON_VERSION"],
    "git_version": os.environ["GUIDE_GIT_VERSION"],
    "rsync_version": os.environ["GUIDE_RSYNC_VERSION"],
    "kafka_image": os.environ["GUIDE_KAFKA_IMAGE"],
    "kafka_image_id": os.environ["GUIDE_KAFKA_IMAGE_ID"],
    "kafka_repo_digests": json.loads(os.environ["GUIDE_KAFKA_REPO_DIGESTS"]),
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
marker.chmod(0o600)
PY
}

write_marker() {
  local fingerprint java_version javac_version maven_version docker_version compose_version
  local python_version git_version rsync_version image_id repo_digests
  fingerprint="$("$STATE_TOOL" fingerprint --root "$ROOT" "${FINGERPRINT_INPUTS[@]}")"
  java_version="$(java -version 2>&1)"
  javac_version="$(javac -version 2>&1)"
  maven_version="$(MAVEN_USER_HOME="$MAVEN_HOME_DIR" "$COPY_ROOT/mvnw" -o -B -ntp -Dmaven.repo.local="$MAVEN_REPOSITORY" -version 2>&1)"
  docker_version="$(docker version --format '{{.Server.Version}}')"
  compose_version="$(docker compose version)"
  python_version="$(python3 --version 2>&1)"
  git_version="$(git --version)"
  rsync_version="$(rsync --version | sed -n '1p')"
  image_id="$(docker image inspect --format '{{.Id}}' "$KAFKA_IMAGE")"
  repo_digests="$(docker image inspect --format '{{json .RepoDigests}}' "$KAFKA_IMAGE")"
  MARKER_TMP="$MARKER.tmp.$$"
  mkdir -p -- "$STATE_DIR"
  rm -f -- "$MARKER_TMP"
  umask 077
  export GUIDE_MARKER="$MARKER_TMP"
  export GUIDE_ID_VALUE="$GUIDE_ID"
  export GUIDE_FINGERPRINT="$fingerprint"
  export GUIDE_MAVEN_HOME="$MAVEN_HOME_DIR"
  export GUIDE_M2="$MAVEN_REPOSITORY"
  export GUIDE_JAVA_VERSION="$java_version"
  export GUIDE_JAVAC_VERSION="$javac_version"
  export GUIDE_MAVEN_VERSION="$maven_version"
  export GUIDE_DOCKER_VERSION="$docker_version"
  export GUIDE_COMPOSE_VERSION="$compose_version"
  export GUIDE_PYTHON_VERSION="$python_version"
  export GUIDE_GIT_VERSION="$git_version"
  export GUIDE_RSYNC_VERSION="$rsync_version"
  export GUIDE_KAFKA_IMAGE="$KAFKA_IMAGE"
  export GUIDE_KAFKA_IMAGE_ID="$image_id"
  export GUIDE_KAFKA_REPO_DIGESTS="$repo_digests"
  run_managed write_marker_file
  mv -f -- "$MARKER_TMP" "$MARKER"
  MARKER_TMP=""
}

main() {
  [[ $# -eq 0 ]] || die "usage: ./prepare.sh"
  trap finish EXIT
  trap 'signal_exit 129' HUP
  trap 'signal_exit 130' INT
  trap 'signal_exit 143' TERM

  require_command git
  require_command python3
  [[ -x "$STATE_TOOL" ]] || die "repository state helper is missing or not executable"
  SOURCE_BEFORE="$(mktemp "/tmp/guide-distributed-prepare-before.XXXXXX")"
  SOURCE_AFTER="$(mktemp "/tmp/guide-distributed-prepare-after.XXXXXX")"
  "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_BEFORE"
  assert_checkout
  assert_runtime
  rm -f -- "$MARKER"
  prepare_maven_copy
  run_managed prepare_maven_build
  prepare_docker
  write_marker
  SUCCESS=1
  log "repository is ready for ./verify.sh"
}

main "$@"
