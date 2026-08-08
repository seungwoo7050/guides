#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
GUIDE_ID="distributed-services"
STATE_DIR="$ROOT/.guide/$GUIDE_ID"
MARKER="$STATE_DIR/prepared.json"
STATE_TOOL="$ROOT/scripts/repository_state.py"
KAFKA_IMAGE="apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"
RUN_ID="guide-distributed-$(date -u +%Y%m%dT%H%M%SZ)-$$-${RANDOM:-0}"
DOCKER_PREFIX="$(printf '%s' "$RUN_ID" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9_-]/-/g')"
WORK_DIR=""
COPY_ROOT=""
SOURCE_BEFORE=""
SOURCE_AFTER=""
COPY_BEFORE=""
COPY_AFTER=""
PASSED=0
FAILED=0
SKIPPED=0
FINISHED=0

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

default_log="${TMPDIR:-/tmp}/guide-distributed-services-verify-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
VERIFY_LOG="${VERIFY_LOG:-$default_log}"

emit_preflight_failure() {
  printf '[verify] ERROR: %s\n' "$1" >&2
  printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" 1 "$SKIPPED" >&2
  printf 'VERIFY LOG: %s\n' "$VERIFY_LOG" >&2
  printf 'RESULT: FAIL\n' >&2
  exit 2
}

validate_log_path() {
  [[ "$VERIFY_LOG" == /* ]] || emit_preflight_failure "VERIFY_LOG must be an absolute path"
  local canonical_root canonical_log parent
  canonical_root="$(cd -- "$ROOT" && pwd -P)"
  canonical_log="$(python3 - "$VERIFY_LOG" <<'PY'
import os
import sys
print(os.path.realpath(sys.argv[1]))
PY
)" || emit_preflight_failure "cannot canonicalize VERIFY_LOG"
  case "$canonical_log" in
    "$canonical_root"|"$canonical_root"/*)
      emit_preflight_failure "VERIFY_LOG must be outside the repository"
      ;;
  esac
  parent="$(dirname -- "$canonical_log")"
  mkdir -p -- "$parent" || emit_preflight_failure "cannot create VERIFY_LOG parent"
  VERIFY_LOG="$canonical_log"
  : >"$VERIFY_LOG" || emit_preflight_failure "cannot write VERIFY_LOG"
}

validate_log_path
exec > >(tee -a "$VERIFY_LOG") 2>&1

log() {
  printf '[verify] %s\n' "$*"
}

pass() {
  PASSED=$((PASSED + 1))
  log "[PASS] $*"
}

fail() {
  FAILED=$((FAILED + 1))
  log "[FAIL] $*"
  return 1
}

preflight_fail() {
  FAILED=$((FAILED + 1))
  log "ERROR: $*"
  exit 2
}

marker_field() {
  local key="$1"
  python3 - "$MARKER" "$key" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
key = sys.argv[2]
try:
    value = json.loads(path.read_text(encoding="utf-8"))[key]
except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
    raise SystemExit(f"invalid prepare marker field {key}: {error}")
if not isinstance(value, (str, int)):
    raise SystemExit(f"prepare marker field {key} must be scalar")
print(value)
PY
}

cleanup() {
  local kraft=""
  if [[ -n "$COPY_ROOT" ]]; then
    kraft="$COPY_ROOT/exercises/90-optional-labs/single-broker-kraft/verify.sh"
  fi
  if [[ -x "$kraft" ]] && command -v docker >/dev/null 2>&1; then
    GUIDE_DOCKER_PROJECT_PREFIX="$DOCKER_PREFIX" "$kraft" --cleanup >/dev/null 2>&1 || true
  fi
  if [[ -n "$WORK_DIR" && -d "$WORK_DIR" ]]; then
    rm -rf -- "$WORK_DIR"
  fi
}

finish() {
  local status=$?
  (( FINISHED == 0 )) || exit "$status"
  FINISHED=1
  trap - EXIT HUP INT TERM

  if [[ -n "$SOURCE_AFTER" && -x "$STATE_TOOL" ]]; then
    "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_AFTER" >/dev/null 2>&1 || status=1
    if [[ -n "$SOURCE_BEFORE" ]] && ! cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
      log "[FAIL] verification changed original source files, modes, or symlinks"
      FAILED=$((FAILED + 1))
      status=1
    fi
  fi
  cleanup
  if (( status != 0 || FAILED != 0 || SKIPPED != 0 )); then
    (( status == 0 )) && status=1
    printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" "$FAILED" "$SKIPPED"
    printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
    printf 'RESULT: FAIL\n'
    exit "$status"
  fi
  printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" "$FAILED" "$SKIPPED"
  printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
  printf 'RESULT: PASS\n'
}

signal_exit() {
  exit "$1"
}

check_prepared_state() {
  [[ -f "$MARKER" ]] || preflight_fail "run ./prepare.sh first"
  local guide_id expected actual maven_home maven_repository marker_image marker_image_id current_image_id
  guide_id="$(marker_field guide_id)" || preflight_fail "prepare marker is invalid"
  [[ "$guide_id" == "$GUIDE_ID" ]] || preflight_fail "prepare marker belongs to another guide"
  expected="$(marker_field preparation_fingerprint)" || preflight_fail "prepare marker is invalid"
  actual="$("$STATE_TOOL" fingerprint --root "$ROOT" "${FINGERPRINT_INPUTS[@]}")" \
    || preflight_fail "cannot compute preparation fingerprint"
  [[ "$expected" == "$actual" ]] || preflight_fail "preparation inputs changed; rerun ./prepare.sh"

  maven_home="$(marker_field maven_home)" || preflight_fail "prepare marker is invalid"
  maven_repository="$(marker_field maven_repository)" || preflight_fail "prepare marker is invalid"
  [[ "$maven_home" == "$STATE_DIR"/* && -d "$maven_home" ]] \
    || preflight_fail "prepared Maven home is missing or outside the guide cache"
  [[ "$maven_repository" == "$STATE_DIR"/* && -d "$maven_repository" ]] \
    || preflight_fail "prepared Maven repository is missing or outside the guide cache"
  PREPARED_MAVEN_HOME="$maven_home"
  PREPARED_M2="$maven_repository"

  marker_image="$(marker_field kafka_image)" || preflight_fail "prepare marker is invalid"
  marker_image_id="$(marker_field kafka_image_id)" || preflight_fail "prepare marker is invalid"
  [[ "$marker_image" == "$KAFKA_IMAGE" ]] || preflight_fail "prepared Kafka image is stale"
  current_image_id="$(docker image inspect --format '{{.Id}}' "$KAFKA_IMAGE" 2>/dev/null)" \
    || preflight_fail "prepared Kafka image is missing"
  [[ "$marker_image_id" == "$current_image_id" ]] \
    || preflight_fail "prepared Kafka image identity changed; rerun ./prepare.sh"
}

copy_working_tree() {
  WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/guide-distributed-verify.XXXXXX")"
  COPY_ROOT="$WORK_DIR/repository"
  SOURCE_BEFORE="$WORK_DIR/source-before.json"
  SOURCE_AFTER="$WORK_DIR/source-after.json"
  COPY_BEFORE="$WORK_DIR/copy-before.json"
  COPY_AFTER="$WORK_DIR/copy-after.json"
  mkdir -p -- "$COPY_ROOT"
  "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_BEFORE"
  rsync -a \
    --exclude=.git \
    --exclude=.guide \
    --exclude=target \
    --exclude=__pycache__ \
    --exclude='*.pyc' \
    "$ROOT/" "$COPY_ROOT/"
  "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_BEFORE"
}

check_shell_syntax() {
  while IFS= read -r script; do
    bash -n "$script"
  done < <(find "$COPY_ROOT" -type f -name '*.sh' -not -path '*/target/*' | sort)
}

check_python_syntax() {
  while IFS= read -r source; do
    python3 -m py_compile "$source"
  done < <(find "$COPY_ROOT/scripts" "$COPY_ROOT/exercises" -type f -name '*.py' | sort)
}

main() {
  [[ $# -eq 0 ]] || preflight_fail "usage: ./verify.sh"
  trap finish EXIT
  trap 'signal_exit 129' HUP
  trap 'signal_exit 130' INT
  trap 'signal_exit 143' TERM

  command -v python3 >/dev/null 2>&1 || preflight_fail "python3 is required"
  command -v java >/dev/null 2>&1 || preflight_fail "java is required"
  command -v javac >/dev/null 2>&1 || preflight_fail "javac is required"
  command -v docker >/dev/null 2>&1 || preflight_fail "docker is required"
  command -v rsync >/dev/null 2>&1 || preflight_fail "rsync is required"
  docker compose version >/dev/null 2>&1 || preflight_fail "Docker Compose v2 is required"
  docker info >/dev/null 2>&1 || preflight_fail "Docker daemon is not available"
  [[ -x "$STATE_TOOL" ]] || preflight_fail "repository state helper is missing"

  check_prepared_state
  pass "prepared environment fingerprint"
  git -C "$ROOT" diff --check
  git -C "$ROOT" diff --cached --check
  pass "working and staged diff hygiene"

  copy_working_tree
  python3 "$COPY_ROOT/scripts/validate.py"
  python3 "$COPY_ROOT/scripts/test-validator.py"
  pass "repository structure, pedagogy, and validator mutants"

  check_shell_syntax
  check_python_syntax
  pass "shell and Python syntax"

  (
    cd "$COPY_ROOT"
    MAVEN_USER_HOME="$PREPARED_MAVEN_HOME" \
      ./mvnw -o -B -ntp \
      -Dmaven.repo.local="$PREPARED_M2" \
      -DskipTests package
  )
  pass "offline Maven reactor"

  GUIDE_VERIFY_WORK_DIR="$WORK_DIR/results" "$COPY_ROOT/scripts/verify-java.sh"
  pass "all Java reference contracts"
  GUIDE_VERIFY_WORK_DIR="$WORK_DIR/results" "$COPY_ROOT/scripts/verify-skeletons.sh"
  pass "all Java skeleton rejection contracts"
  GUIDE_DOCKER_READY=1 \
    GUIDE_DOCKER_PROJECT_PREFIX="$DOCKER_PREFIX" \
    GUIDE_VERIFY_WORK_DIR="$WORK_DIR/results" \
    "$COPY_ROOT/scripts/verify-nonjava.sh"
  pass "release manifest and KRaft integration"

  "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_AFTER"
  cmp -s "$COPY_BEFORE" "$COPY_AFTER" || fail "verification changed isolated source inputs"
  pass "isolated and original source stability"
}

main "$@"
