#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATE_TOOL="$ROOT_DIR/scripts/guide_state.py"
MARKER="$ROOT_DIR/.guide/backend-spring-boot/prepared.json"

[[ -f "$MARKER" ]] || {
  printf '[FAIL] prepare marker가 없습니다. 먼저 ./prepare.sh를 실행하세요.\n' >&2
  exit 1
}

fingerprint="$(python3 "$STATE_TOOL" capture "$ROOT_DIR")"
values="$(python3 "$STATE_TOOL" validate-marker "$MARKER" "$ROOT_DIR" "$fingerprint")" \
  || {
    printf '[FAIL] prepare marker가 손상·만료되었습니다. ./prepare.sh를 다시 실행하세요.\n' >&2
    exit 1
  }
IFS=$'\t' read -r maven_home maven_repository <<<"$values"

exec env MAVEN_USER_HOME="$maven_home" \
  "$ROOT_DIR/mvnw" -B -ntp -o \
  -Dmaven.repo.local="$maven_repository" "$@"
