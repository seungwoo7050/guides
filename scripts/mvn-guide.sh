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
else
  [[ -f "$MARKER" ]] || fail "먼저 저장소 루트에서 ./prepare.sh를 실행하십시오."
  fingerprint=$(python3 "$ROOT/scripts/guide_state.py" capture "$ROOT")
  MAVEN_REPOSITORY=$(
    python3 "$ROOT/scripts/guide_state.py" marker-field \
      "$MARKER" "$fingerprint" maven_repository
  )
fi

exec "$ROOT/mvnw" -B -ntp -o -Dmaven.repo.local="$MAVEN_REPOSITORY" "$@"
