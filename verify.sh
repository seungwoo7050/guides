#!/usr/bin/env bash
set -Eeuo pipefail
export GIT_OPTIONAL_LOCKS=0

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
ACTIVE_PID=""

FINGERPRINT_INPUTS=(
  prepare.sh
  verify.sh
  mvnw
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

while IFS= read -r module_pom; do
  FINGERPRINT_INPUTS+=("${module_pom#"$ROOT/"}")
done < <(find "$ROOT/exercises" -type f -name pom.xml | sort)

default_log="/tmp/guide-distributed-services-verify-$(date -u +%Y%m%dT%H%M%SZ)-$$.log"
VERIFY_LOG="${VERIFY_LOG:-$default_log}"
VERIFY_LOG_READY=0

emit_preflight_failure() {
  local message="$1"
  if (( VERIFY_LOG_READY == 0 )); then
    VERIFY_LOG="$(python3 - "$default_log" <<'PY'
import os
import sys
print(os.path.realpath(sys.argv[1]))
PY
)"
    : >"$VERIFY_LOG" 2>/dev/null || true
    {
      printf '[verify] ERROR: %s\n' "$message"
      printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" 1 "$SKIPPED"
      printf 'VERIFY LOG: %s\n' "$VERIFY_LOG"
      printf 'RESULT: FAIL\n'
    } | tee -a "$VERIFY_LOG" >&2
  else
    printf '[verify] ERROR: %s\n' "$message" >&2
    printf 'passed=%d failed=%d skipped=%d\n' "$PASSED" 1 "$SKIPPED" >&2
    printf 'VERIFY LOG: %s\n' "$VERIFY_LOG" >&2
    printf 'RESULT: FAIL\n' >&2
  fi
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
  VERIFY_LOG_READY=1
}

validate_log_path
exec > >(tee -a "$VERIFY_LOG") 2>&1

log() {
  printf '[verify] %s\n' "$*"
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

validate_marker_schema() {
  python3 - "$MARKER" <<'PY'
import json
import sys
from pathlib import Path

try:
    marker = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as error:
    raise SystemExit(f"invalid prepare marker: {error}")
required = {
    "schema", "guide_id", "preparation_fingerprint", "maven_home",
    "maven_repository", "java_version", "javac_version", "maven_version",
    "docker_version", "docker_compose_version", "python_version", "git_version",
    "rsync_version", "kafka_image", "kafka_image_id", "kafka_repo_digests",
}
if set(marker) != required or marker.get("schema") != 1:
    raise SystemExit("prepare marker schema or keys differ")
for key in required - {"schema", "kafka_repo_digests"}:
    if not isinstance(marker.get(key), str) or not marker[key]:
        raise SystemExit(f"prepare marker field must be a non-empty string: {key}")
digests = marker.get("kafka_repo_digests")
if not isinstance(digests, list) or not digests or not all(
    isinstance(item, str) and item for item in digests
):
    raise SystemExit("prepare marker Kafka repo digests are invalid")
PY
}

cleanup() {
  terminate_active_child
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
    "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_AFTER" >/dev/null 2>&1 \
      || { (( status == 0 )) && status=1; }
    if [[ -n "$SOURCE_BEFORE" ]] && ! cmp -s "$SOURCE_BEFORE" "$SOURCE_AFTER"; then
      log "[FAIL] verification changed original source files, modes, or symlinks"
      FAILED=$((FAILED + 1))
      (( status == 0 )) && status=1
    fi
  fi
  cleanup
  [[ -n "$SOURCE_BEFORE" ]] && rm -f -- "$SOURCE_BEFORE"
  [[ -n "$SOURCE_AFTER" ]] && rm -f -- "$SOURCE_AFTER"
  if (( status != 0 && FAILED == 0 )); then
    FAILED=1
  fi
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
  local code="$1"
  trap - HUP INT TERM
  terminate_active_child
  exit "$code"
}

check_prepared_state() {
  [[ -f "$MARKER" ]] || preflight_fail "run ./prepare.sh first"
  validate_marker_schema || preflight_fail "prepare marker is invalid"
  local guide_id expected actual maven_home maven_repository marker_image marker_image_id current_image_id
  local current_java current_javac current_maven current_docker current_compose
  local current_python current_git current_rsync current_repo_digests marker_repo_digests
  guide_id="$(marker_field guide_id)" || preflight_fail "prepare marker is invalid"
  [[ "$guide_id" == "$GUIDE_ID" ]] || preflight_fail "prepare marker belongs to another guide"
  expected="$(marker_field preparation_fingerprint)" || preflight_fail "prepare marker is invalid"
  actual="$("$STATE_TOOL" fingerprint --root "$ROOT" "${FINGERPRINT_INPUTS[@]}")" \
    || preflight_fail "cannot compute preparation fingerprint"
  [[ "$expected" == "$actual" ]] || preflight_fail "preparation inputs changed; rerun ./prepare.sh"

  maven_home="$(marker_field maven_home)" || preflight_fail "prepare marker is invalid"
  maven_repository="$(marker_field maven_repository)" || preflight_fail "prepare marker is invalid"
  [[ "$maven_home" == "$STATE_DIR/maven-home" && -d "$maven_home" ]] \
    || preflight_fail "prepared Maven home path is invalid"
  [[ "$maven_repository" == "$STATE_DIR/m2" && -d "$maven_repository" ]] \
    || preflight_fail "prepared Maven repository path is invalid"
  python3 - "$STATE_DIR" "$maven_home" "$maven_repository" <<'PY' \
    || preflight_fail "prepared Maven cache escapes the guide cache"
import sys
from pathlib import Path

state = Path(sys.argv[1]).resolve(strict=True)
for raw in sys.argv[2:]:
    resolved = Path(raw).resolve(strict=True)
    try:
        resolved.relative_to(state)
    except ValueError as error:
        raise SystemExit(f"cache path escapes state directory: {raw}") from error
PY
  PREPARED_MAVEN_HOME="$maven_home"
  PREPARED_M2="$maven_repository"

  marker_image="$(marker_field kafka_image)" || preflight_fail "prepare marker is invalid"
  marker_image_id="$(marker_field kafka_image_id)" || preflight_fail "prepare marker is invalid"
  [[ "$marker_image" == "$KAFKA_IMAGE" ]] || preflight_fail "prepared Kafka image is stale"
  current_image_id="$(docker image inspect --format '{{.Id}}' "$KAFKA_IMAGE" 2>/dev/null)" \
    || preflight_fail "prepared Kafka image is missing"
  [[ "$marker_image_id" == "$current_image_id" ]] \
    || preflight_fail "prepared Kafka image identity changed; rerun ./prepare.sh"

  current_java="$(java -version 2>&1)"
  current_javac="$(javac -version 2>&1)"
  current_maven="$(MAVEN_USER_HOME="$maven_home" "$ROOT/mvnw" -o -B -ntp \
    -Dmaven.repo.local="$maven_repository" -version 2>&1)"
  current_docker="$(docker version --format '{{.Server.Version}}')"
  current_compose="$(docker compose version)"
  current_python="$(python3 --version 2>&1)"
  current_git="$(git --version)"
  current_rsync="$(rsync --version | sed -n '1p')"
  [[ "$(marker_field java_version)" == "$current_java" ]] \
    || preflight_fail "Java runtime changed; rerun ./prepare.sh"
  [[ "$(marker_field javac_version)" == "$current_javac" ]] \
    || preflight_fail "javac changed; rerun ./prepare.sh"
  [[ "$(marker_field maven_version)" == "$current_maven" ]] \
    || preflight_fail "Maven runtime changed; rerun ./prepare.sh"
  [[ "$(marker_field docker_version)" == "$current_docker" ]] \
    || preflight_fail "Docker daemon version changed; rerun ./prepare.sh"
  [[ "$(marker_field docker_compose_version)" == "$current_compose" ]] \
    || preflight_fail "Docker Compose changed; rerun ./prepare.sh"
  [[ "$(marker_field python_version)" == "$current_python" ]] \
    || preflight_fail "Python changed; rerun ./prepare.sh"
  [[ "$(marker_field git_version)" == "$current_git" ]] \
    || preflight_fail "Git changed; rerun ./prepare.sh"
  [[ "$(marker_field rsync_version)" == "$current_rsync" ]] \
    || preflight_fail "rsync changed; rerun ./prepare.sh"
  current_repo_digests="$(docker image inspect --format '{{json .RepoDigests}}' "$KAFKA_IMAGE")"
  marker_repo_digests="$(python3 - "$MARKER" <<'PY'
import json
import sys
print(json.dumps(json.load(open(sys.argv[1], encoding="utf-8"))["kafka_repo_digests"], separators=(",", ":")))
PY
)"
  [[ "$marker_repo_digests" == "$current_repo_digests" ]] \
    || preflight_fail "prepared Kafka repo digests changed; rerun ./prepare.sh"
}

copy_working_tree() {
  WORK_DIR="$(mktemp -d "/tmp/guide-distributed-verify.XXXXXX")"
  COPY_ROOT="$WORK_DIR/repository"
  COPY_BEFORE="$WORK_DIR/copy-before.json"
  COPY_AFTER="$WORK_DIR/copy-after.json"
  mkdir -p -- "$COPY_ROOT"
  rsync -a \
    --exclude='/.git' \
    --exclude='/.guide/' \
    --exclude='/target/' \
    --exclude='/exercises/**/target/' \
    --exclude='/scripts/**/__pycache__/' \
    --exclude='/exercises/**/__pycache__/' \
    --exclude='/scripts/**/*.pyc' \
    --exclude='/exercises/**/*.pyc' \
    "$ROOT/" "$COPY_ROOT/"
  "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_BEFORE"
}

check_shell_syntax() {
  while IFS= read -r script; do
    bash -n "$script"
  done < <(find "$COPY_ROOT" -type f -name '*.sh' -not -path "$COPY_ROOT/.workspace/*" -not -path '*/target/*' | sort)
}

check_python_syntax() {
  while IFS= read -r source; do
    python3 -m py_compile "$source"
  done < <(find "$COPY_ROOT/scripts" "$COPY_ROOT/exercises" -type f -name '*.py' | sort)
}

offline_maven() {
  (
    cd "$COPY_ROOT"
    MAVEN_USER_HOME="$PREPARED_MAVEN_HOME" \
      ./mvnw -o -B -ntp \
      -Dmaven.repo.local="$PREPARED_M2" \
      -DskipTests package
  )
}

main() {
  [[ $# -eq 0 ]] || preflight_fail "usage: ./verify.sh"
  trap finish EXIT
  trap 'signal_exit 129' HUP
  trap 'signal_exit 130' INT
  trap 'signal_exit 143' TERM

  command -v python3 >/dev/null 2>&1 || preflight_fail "python3 is required"
  command -v git >/dev/null 2>&1 || preflight_fail "git is required"
  [[ -x "$STATE_TOOL" ]] || preflight_fail "repository state helper is missing"
  SOURCE_BEFORE="$(mktemp "/tmp/guide-distributed-verify-before.XXXXXX")"
  SOURCE_AFTER="$(mktemp "/tmp/guide-distributed-verify-after.XXXXXX")"
  "$STATE_TOOL" manifest --root "$ROOT" --output "$SOURCE_BEFORE" \
    || preflight_fail "cannot capture initial repository state"
  command -v java >/dev/null 2>&1 || preflight_fail "java is required"
  command -v javac >/dev/null 2>&1 || preflight_fail "javac is required"
  command -v docker >/dev/null 2>&1 || preflight_fail "docker is required"
  command -v rsync >/dev/null 2>&1 || preflight_fail "rsync is required"
  docker compose version >/dev/null 2>&1 || preflight_fail "Docker Compose v2 is required"
  docker info >/dev/null 2>&1 || preflight_fail "Docker daemon is not available"

  check_prepared_state
  pass "prepared environment fingerprint"
  git -C "$ROOT" diff --check
  git -C "$ROOT" diff --cached --check
  pass "working and staged diff hygiene"

  copy_working_tree
  run_managed python3 "$COPY_ROOT/scripts/validate.py"
  run_managed python3 "$COPY_ROOT/scripts/test-validator.py"
  pass "repository structure, pedagogy, and validator mutants"

  run_managed check_shell_syntax
  run_managed check_python_syntax
  pass "shell and Python syntax"

  run_managed offline_maven
  pass "offline Maven reactor"

  run_managed env GUIDE_VERIFY_WORK_DIR="$WORK_DIR/results" \
    "$COPY_ROOT/scripts/verify-java.sh"
  pass "all Java reference contracts"
  run_managed env GUIDE_VERIFY_WORK_DIR="$WORK_DIR/results" \
    "$COPY_ROOT/scripts/verify-skeletons.sh"
  pass "all Java skeleton rejection contracts"
  run_managed env GUIDE_DOCKER_READY=1 \
    GUIDE_DOCKER_PROJECT_PREFIX="$DOCKER_PREFIX" \
    GUIDE_VERIFY_WORK_DIR="$WORK_DIR/results" \
    "$COPY_ROOT/scripts/verify-nonjava.sh"
  pass "release manifest and KRaft integration"

  "$COPY_ROOT/scripts/repository_state.py" manifest --root "$COPY_ROOT" --output "$COPY_AFTER"
  cmp -s "$COPY_BEFORE" "$COPY_AFTER" || fail "verification changed isolated source inputs"
  pass "isolated and original source stability"
}

main "$@"
