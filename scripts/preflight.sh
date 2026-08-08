#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
WORK=

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

pass() {
  printf '[PASS] %s\n' "$*"
}

cleanup() {
  [[ -z "${WORK:-}" ]] || rm -rf "$WORK"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

case "$(uname -s)" in
  Darwin) pass "macOS 환경" ;;
  Linux) pass "Linux 환경" ;;
  *) fail "Linux와 macOS에서만 지원합니다." ;;
esac

for required_command in git java javac jfr curl python3 make; do
  command -v "$required_command" >/dev/null 2>&1 \
    || fail "$required_command 명령이 필요합니다."
  pass "$required_command 명령"
done

java_specification=$(
  java -XshowSettings:properties -version 2>&1 \
    | sed -n 's/^[[:space:]]*java.specification.version = //p' \
    | head -n 1
)
javac_version=$(javac -version 2>&1)
[[ "$java_specification" == 21 ]] \
  || fail "실행 중인 Java가 21이 아닙니다: $(java -version 2>&1 | head -n 1)"
[[ "$javac_version" =~ ^javac[[:space:]]21([.]|$) ]] \
  || fail "실행 중인 javac가 21이 아닙니다: $javac_version"
pass "$(java -version 2>&1 | head -n 1)"
pass "$javac_version"

properties="$ROOT/.mvn/wrapper/maven-wrapper.properties"
[[ -f "$properties" ]] || fail "Maven Wrapper 설정이 없습니다."
grep -Fxq 'wrapperVersion=3.3.4' "$properties" \
  || fail "Maven Wrapper 버전이 3.3.4가 아닙니다."
grep -Fxq \
  'distributionUrl=https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.16/apache-maven-3.9.16-bin.zip' \
  "$properties" || fail "Maven 배포 버전이 3.9.16이 아닙니다."
grep -Fxq \
  'distributionSha256Sum=5af3b743dd8b876b5c45da33b676251e5f1687712644abb4ee519ca56e1d89ce' \
  "$properties" || fail "Maven 3.9.16 SHA-256이 올바르지 않습니다."
pass "Maven Wrapper 3.3.4와 Maven 3.9.16 설정"

maven_version=$("$ROOT/mvnw" -version 2>&1) \
  || fail "Maven Wrapper를 실행하지 못했습니다."
grep -Fq 'Apache Maven 3.9.16' <<<"$maven_version" \
  || fail "Maven Wrapper가 Apache Maven 3.9.16을 실행하지 않았습니다."
grep -Eq 'Java version:[[:space:]]*21([.,]|$)' <<<"$maven_version" \
  || fail "Maven이 JDK 21로 실행되지 않았습니다."
pass "Maven 3.9.16과 JDK 21 실행 환경"

WORK=$(mktemp -d "${TMPDIR:-/tmp}/guide-java-release.XXXXXX")
printf '%s\n' 'public final class ReleaseProbe {}' >"$WORK/ReleaseProbe.java"
javac --release 17 -d "$WORK" "$WORK/ReleaseProbe.java" \
  || fail "JDK 21에서 --release 17 컴파일을 실행할 수 없습니다."
pass "JDK 21의 javac --release 17 호환성"
