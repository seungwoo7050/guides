#!/usr/bin/env bash
set -euo pipefail

EXERCISE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$EXERCISE/../../.." && pwd)
SEED=${GUIDE_MAVEN_REPOSITORY:-}
WORK="$EXERCISE/.workspace"
REPOSITORY="$WORK/repository"

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

cleanup() {
  rm -rf "$WORK" "$EXERCISE/contract-library/target" "$EXERCISE/consumer-service/target"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

[[ "$SEED" == /* && -d "$SEED" ]] \
  || fail "GUIDE_MAVEN_REPOSITORY에 준비된 절대 캐시 경로가 필요합니다."
rm -rf "$WORK"
mkdir -p "$REPOSITORY"
cp -R "$SEED"/. "$REPOSITORY"/
rm -rf "$REPOSITORY/dev/guides/contract-library"

COMMON=(-B -ntp -o -Dmaven.repo.local="$REPOSITORY")

set +e
"$ROOT/mvnw" "${COMMON[@]}" -f "$EXERCISE/consumer-service/pom.xml" test \
  >"$WORK/before.log" 2>&1
before=$?
set -e
[[ $before -ne 0 ]] || fail "생산 모듈 설치 전에 소비 모듈이 성공했습니다."
grep -Eq 'Could not find artifact|Could not resolve dependencies|DependencyResolutionException' \
  "$WORK/before.log" \
  || { cat "$WORK/before.log" >&2; fail "소비 모듈이 예상한 의존성 누락이 아닌 이유로 실패했습니다."; }
printf '[PASS] 생산 모듈 설치 전 소비 모듈 실패\n'

"$ROOT/mvnw" "${COMMON[@]}" -f "$EXERCISE/contract-library/pom.xml" clean install
"$ROOT/mvnw" "${COMMON[@]}" -f "$EXERCISE/consumer-service/pom.xml" clean test
printf '[PASS] 생산 모듈 설치 후 소비 모듈 성공\n'
