#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
MARKER="$ROOT/.guide/java/prepared.json"

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

if [[ -n "${GUIDE_MAVEN_REPOSITORY:-}" ]]; then
  MAVEN_REPOSITORY=$GUIDE_MAVEN_REPOSITORY
  [[ "$MAVEN_REPOSITORY" == /* && -d "$MAVEN_REPOSITORY" ]] \
    || fail "GUIDE_MAVEN_REPOSITORY는 존재하는 절대 디렉터리여야 합니다."
  [[ "${MAVEN_USER_HOME:-}" == /* && -d "${MAVEN_USER_HOME:-}" ]] \
    || fail "격리 검증에는 준비된 절대 MAVEN_USER_HOME이 필요합니다."
else
  [[ -f "$MARKER" ]] || fail "먼저 저장소 루트에서 make prepare를 실행하십시오."
  fingerprint=$(python3 "$ROOT/scripts/guide_state.py" preparation-capture "$ROOT")
  MAVEN_REPOSITORY=$(
    python3 "$ROOT/scripts/guide_state.py" marker-field \
      "$MARKER" "$fingerprint" maven_repository
  )
  MAVEN_USER_HOME=$(
    python3 "$ROOT/scripts/guide_state.py" marker-field \
      "$MARKER" "$fingerprint" maven_user_home
  )
fi
export MAVEN_USER_HOME

exec "$ROOT/mvnw" -B -ntp -o -Dmaven.repo.local="$MAVEN_REPOSITORY" "$@"
