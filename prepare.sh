#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd -P)
GUIDE_ROOT="$ROOT/.guide/java"
MAVEN_USER_HOME="$GUIDE_ROOT/maven-home"
MAVEN_REPOSITORY="$GUIDE_ROOT/maven-repository"
MARKER="$GUIDE_ROOT/prepared.json"
WORK_ROOT=
WORK_TREE=
export MAVEN_USER_HOME

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

pass() {
  printf '[PASS] %s\n' "$*"
}

cleanup() {
  [[ -z "${WORK_ROOT:-}" || ! -d "$WORK_ROOT" ]] || rm -rf "$WORK_ROOT"
}

trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

assert_repository_root() {
  [[ "$PWD" == "$ROOT" ]] || fail "저장소 루트에서 ./prepare.sh를 실행해야 합니다."
  local git_root
  git_root=$(git -C "$ROOT" rev-parse --show-toplevel 2>/dev/null) \
    || fail "Git 저장소를 찾지 못했습니다."
  git_root=$(cd "$git_root" && pwd -P)
  [[ "$git_root" == "$ROOT" ]] || fail "저장소 루트의 prepare.sh를 실행해야 합니다: $git_root"
  for required in \
    README.md pom.xml mvnw verify.sh scripts/guide_state.py scripts/mvn-guide.sh \
    scripts/preflight.sh scripts/validate.py scripts/workspaces.txt \
    scripts/new-workspace.sh scripts/check-workspace.sh docs/00-roadmap.md exercises; do
    [[ -e "$ROOT/$required" ]] || fail "필수 경로가 없습니다: $required"
  done
  for executable in \
    prepare.sh verify.sh mvnw scripts/mvn-guide.sh scripts/preflight.sh \
    scripts/smoke-javac.sh scripts/record-executor-jfr.sh \
    scripts/new-workspace.sh scripts/check-workspace.sh \
    exercises/03-build-test-and-evidence/01-multi-repository-maven/verify.sh; do
    [[ -x "$ROOT/$executable" ]] || fail "실행 권한이 필요합니다: $executable"
  done
  pass "일반 clone과 linked worktree를 지원하는 저장소 루트 확인"
}

prepare_maven_cache() {
  mkdir -p "$MAVEN_USER_HOME" "$MAVEN_REPOSITORY"
  WORK_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/guide-java-prepare.XXXXXX") \
    || fail "준비용 임시 디렉터리를 만들지 못했습니다."
  WORK_TREE="$WORK_ROOT/repository"
  mkdir -p "$WORK_TREE"
  python3 "$ROOT/scripts/guide_state.py" copy "$ROOT" "$WORK_TREE" \
    || fail "준비용 source 복사본을 만들지 못했습니다."
  local copied_state
  copied_state=$(python3 "$WORK_TREE/scripts/guide_state.py" capture "$WORK_TREE") \
    || fail "준비용 source 복사본의 상태를 기록하지 못했습니다."
  [[ "$copied_state" == "$1" ]] \
    || fail "준비용 source 복사본이 현재 working tree와 일치하지 않습니다."

  "$WORK_TREE/scripts/preflight.sh"

  local online=(-B -ntp -Dmaven.repo.local="$MAVEN_REPOSITORY")
  "$WORK_TREE/mvnw" "${online[@]}" -f "$WORK_TREE/pom.xml" \
    -DskipTests dependency:go-offline
  local coordinate
  for coordinate in \
    org.apache.maven.surefire:surefire-junit-platform:3.5.2 \
    org.junit.platform:junit-platform-engine:1.9.3 \
    org.junit.platform:junit-platform-launcher:1.9.3 \
    org.junit.platform:junit-platform-commons:1.9.3 \
    org.junit.platform:junit-platform-launcher:6.1.0; do
    "$WORK_TREE/mvnw" "${online[@]}" -f "$WORK_TREE/pom.xml" \
      dependency:get -Dartifact="$coordinate"
  done
  "$WORK_TREE/mvnw" "${online[@]}" -f "$WORK_TREE/pom.xml" \
    -DskipTests verify

  local pom
  for pom in \
    exercises/01-language-and-domain/01-first-program/skeleton/pom.xml \
    exercises/01-language-and-domain/02-value-object-contract/skeleton/pom.xml \
    exercises/02-runtime-and-concurrency/01-concurrent-state-update/skeleton/pom.xml \
    exercises/02-runtime-and-concurrency/02-executor-lifecycle/skeleton/pom.xml \
    exercises/03-build-test-and-evidence/02-state-and-effect-testing/skeleton/pom.xml \
    exercises/04-capstone/01-concurrent-job-ledger/skeleton/pom.xml; do
    "$WORK_TREE/mvnw" "${online[@]}" -DskipTests \
      -f "$WORK_TREE/$pom" dependency:go-offline
    "$WORK_TREE/mvnw" "${online[@]}" -DskipTests \
      -f "$WORK_TREE/$pom" test
  done

  local multi="$WORK_TREE/exercises/03-build-test-and-evidence/01-multi-repository-maven"
  "$WORK_TREE/mvnw" "${online[@]}" -DskipTests \
    -f "$multi/contract-library/pom.xml" clean install
  "$WORK_TREE/mvnw" "${online[@]}" -DskipTests \
    -f "$multi/consumer-service/pom.xml" dependency:go-offline
  "$WORK_TREE/mvnw" "${online[@]}" -DskipTests \
    -f "$multi/consumer-service/pom.xml" test

  "$WORK_TREE/mvnw" -B -ntp -o -Dmaven.repo.local="$MAVEN_REPOSITORY" \
    -f "$WORK_TREE/pom.xml" -DskipTests verify
  cleanup
  WORK_ROOT=
  WORK_TREE=
  pass "격리 복사본에서 Maven 3.9.16 배포본과 전체 오프라인 의존성 준비"
}

write_marker() {
  local fingerprint=$1
  local java_version javac_version maven_version
  java_version=$(java -version 2>&1 | head -n 1)
  javac_version=$(javac -version 2>&1)
  maven_version=$("$ROOT/mvnw" -version 2>&1 | head -n 1)
  GUIDE_MARKER="$MARKER" \
  GUIDE_FINGERPRINT="$fingerprint" \
  GUIDE_JAVA_VERSION="$java_version" \
  GUIDE_JAVAC_VERSION="$javac_version" \
  GUIDE_MAVEN_VERSION_TEXT="$maven_version" \
  GUIDE_MAVEN_USER_HOME="$MAVEN_USER_HOME" \
  GUIDE_MAVEN_REPOSITORY="$MAVEN_REPOSITORY" \
    python3 - <<'PY'
import json
import os
from pathlib import Path

marker = Path(os.environ["GUIDE_MARKER"])
temporary = marker.with_name(f".{marker.name}.tmp-{os.getpid()}")
payload = {
    "schema": 1,
    "guide_id": "java",
    "input_fingerprint": os.environ["GUIDE_FINGERPRINT"],
    "java_version": os.environ["GUIDE_JAVA_VERSION"],
    "javac_version": os.environ["GUIDE_JAVAC_VERSION"],
    "maven_version": "3.9.16",
    "maven_version_text": os.environ["GUIDE_MAVEN_VERSION_TEXT"],
    "maven_user_home": os.environ["GUIDE_MAVEN_USER_HOME"],
    "maven_repository": os.environ["GUIDE_MAVEN_REPOSITORY"],
    "docker_image_id": None,
}
temporary.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
os.replace(temporary, marker)
PY
}

main() {
  assert_repository_root
  local source_before preparation_before index_before source_after preparation_after index_after
  source_before=$(python3 "$ROOT/scripts/guide_state.py" capture "$ROOT")
  preparation_before=$(python3 "$ROOT/scripts/guide_state.py" preparation-capture "$ROOT")
  index_before=$(python3 "$ROOT/scripts/guide_state.py" index-state "$ROOT")

  prepare_maven_cache "$source_before"

  source_after=$(python3 "$ROOT/scripts/guide_state.py" capture "$ROOT")
  preparation_after=$(python3 "$ROOT/scripts/guide_state.py" preparation-capture "$ROOT")
  index_after=$(python3 "$ROOT/scripts/guide_state.py" index-state "$ROOT")
  [[ "$source_before" == "$source_after" ]] \
    || fail "prepare가 source bytes, mode 또는 symlink를 변경했습니다."
  [[ "$index_before" == "$index_after" ]] \
    || fail "prepare가 Git index raw bytes 또는 staged entries를 변경했습니다."
  [[ "$preparation_before" == "$preparation_after" ]] \
    || fail "prepare가 준비 fingerprint 입력을 변경했습니다."
  pass "prepare 전후 source와 Git index raw bytes·staged entries 불변"

  write_marker "$preparation_after"
  python3 "$ROOT/scripts/guide_state.py" validate-marker "$MARKER" "$preparation_after"
  pass "원자적 준비 상태 기록: .guide/java/prepared.json"
  printf '\nPREPARE RESULT: PASS\n'
  printf '다음 명령: VERIFY_LOG=/tmp/guide-java-verify.log make verify\n'
}

main "$@"
