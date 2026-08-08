#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="distributed-services"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
MAVEN_HOME_DIR="$STATE_DIR/maven-home"
MAVEN_REPOSITORY="$STATE_DIR/m2"
MARKER="$STATE_DIR/prepared.json"
KAFKA_IMAGE="apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"
STATE_TOOL="$ROOT/scripts/repository_state.py"
SOURCE_BEFORE="$(mktemp "${TMPDIR:-/tmp}/guide-distributed-prepare-before.XXXXXX")"
SOURCE_AFTER="$(mktemp "${TMPDIR:-/tmp}/guide-distributed-prepare-after.XXXXXX")"
SUCCESS=0

FINGERPRINT_INPUTS=(
  prepare.sh
  verify.sh
  pom.xml
  .mvn/jvm.config
  .mvn/wrapper/maven-wrapper.properties
  scripts/repository_state.py
  scripts/validate.py
  scripts/test-validator.py
  scripts/verify-java.sh
  scripts/verify-skeletons.sh
  scripts/verify-nonjava.sh
  exercises/90-optional-labs/single-broker-kraft/verify.sh
  exercises/90-optional-labs/single-broker-kraft/skeleton/compose.yaml
  exercises/90-optional-labs/single-broker-kraft/reference/compose.yaml
)

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

cleanup_generated() {
  find "$ROOT/exercises" -type d -name target -prune -exec rm -rf -- {} + 2>/dev/null || true
  find "$ROOT" -type d -name __pycache__ -not -path "$ROOT/.guide/*" -prune -exec rm -rf -- {} + 2>/dev/null || true
  find "$ROOT" -type f -name '*.pyc' -not -path "$ROOT/.guide/*" -delete 2>/dev/null || true
}

finish() {
  local status=$?
  trap - EXIT HUP INT TERM
  cleanup_generated
  if [[ -x "$STATE_TOOL" ]]; then
    "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_AFTER" >/dev/null 2>&1 || status=1
    if ! cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
      printf '[prepare] ERROR: preparation changed source files, modes, or symlinks\n' >&2
      status=1
    fi
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
  exit "$1"
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

prepare_maven() {
  mkdir -p -- "$MAVEN_HOME_DIR" "$MAVEN_REPOSITORY"
  log "resolving Maven Wrapper, plugins, and dependencies"
  (
    cd "$ROOT"
    MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
      ./mvnw -B -ntp \
      -Dmaven.repo.local="$MAVEN_REPOSITORY" \
      -DskipTests clean package
    MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
      ./mvnw -o -B -ntp \
      -Dmaven.repo.local="$MAVEN_REPOSITORY" \
      -DskipTests clean package
  )
  cleanup_generated
}

prepare_docker() {
  log "pulling $KAFKA_IMAGE"
  docker pull "$KAFKA_IMAGE"
  docker image inspect "$KAFKA_IMAGE" >/dev/null
}

write_marker() {
  local fingerprint java_version javac_version maven_version image_id repo_digests temporary
  fingerprint="$("$STATE_TOOL" fingerprint --root "$ROOT" "${FINGERPRINT_INPUTS[@]}")"
  java_version="$(java -version 2>&1 | head -n 1)"
  javac_version="$(javac -version 2>&1)"
  maven_version="$(MAVEN_USER_HOME="$MAVEN_HOME_DIR" "$ROOT/mvnw" -o -B -ntp -Dmaven.repo.local="$MAVEN_REPOSITORY" -version | head -n 1)"
  image_id="$(docker image inspect --format '{{.Id}}' "$KAFKA_IMAGE")"
  repo_digests="$(docker image inspect --format '{{json .RepoDigests}}' "$KAFKA_IMAGE")"
  temporary="$MARKER.tmp.$$"
  mkdir -p -- "$STATE_DIR"
  umask 077
  GUIDE_MARKER="$temporary" \
  GUIDE_ID_VALUE="$GUIDE_ID" \
  GUIDE_FINGERPRINT="$fingerprint" \
  GUIDE_MAVEN_HOME="$MAVEN_HOME_DIR" \
  GUIDE_M2="$MAVEN_REPOSITORY" \
  GUIDE_JAVA_VERSION="$java_version" \
  GUIDE_JAVAC_VERSION="$javac_version" \
  GUIDE_MAVEN_VERSION="$maven_version" \
  GUIDE_KAFKA_IMAGE="$KAFKA_IMAGE" \
  GUIDE_KAFKA_IMAGE_ID="$image_id" \
  GUIDE_KAFKA_REPO_DIGESTS="$repo_digests" \
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
    "kafka_image": os.environ["GUIDE_KAFKA_IMAGE"],
    "kafka_image_id": os.environ["GUIDE_KAFKA_IMAGE_ID"],
    "kafka_repo_digests": json.loads(os.environ["GUIDE_KAFKA_REPO_DIGESTS"]),
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
marker.chmod(0o600)
PY
  mv -f -- "$temporary" "$MARKER"
}

main() {
  [[ $# -eq 0 ]] || die "usage: ./prepare.sh"
  trap finish EXIT
  trap 'signal_exit 129' HUP
  trap 'signal_exit 130' INT
  trap 'signal_exit 143' TERM

  assert_checkout
  assert_runtime
  "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_BEFORE"
  rm -f -- "$MARKER"
  prepare_maven
  prepare_docker
  write_marker
  SUCCESS=1
  log "repository is ready for ./verify.sh"
}

main "$@"
