#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
RYUK_IMAGE="testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0"

[[ $# -eq 1 ]] || {
  printf '사용법: ./scripts/check-workspace.sh EXERCISE_SLUG\n' >&2
  exit 2
}
[[ "$(pwd -P)" == "$ROOT_DIR" ]] || {
  printf '저장소 루트에서 실행해야 합니다.\n' >&2
  exit 2
}

workspace="$(python3 "$ROOT_DIR/scripts/workspace.py" validate "$1")"
common_environment=(
  TESTCONTAINERS_PULL_POLICY=dev.guides.spring.testinfra.NeverPullPolicy
  TESTCONTAINERS_RYUK_CONTAINER_IMAGE="$RYUK_IMAGE"
  TESTCONTAINERS_CHECKS_DISABLE=true
)

if [[ -n "${MAVEN_USER_HOME:-}" && -n "${GUIDE_MAVEN_REPOSITORY:-}" ]]; then
  exec env "${common_environment[@]}" MAVEN_USER_HOME="$MAVEN_USER_HOME" \
    "$ROOT_DIR/mvnw" -B -ntp -o \
    -Dmaven.repo.local="$GUIDE_MAVEN_REPOSITORY" -f "$workspace/pom.xml" test
fi

exec env "${common_environment[@]}" \
  "$ROOT_DIR/scripts/mvn-guide.sh" -f "$workspace/pom.xml" test
