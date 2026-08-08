#!/usr/bin/env bash
set -Eeuo pipefail

GUIDE_ID="backend-spring-boot"
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
CACHE_DIR="$ROOT_DIR/.guide/$GUIDE_ID"
MAVEN_HOME_DIR="$CACHE_DIR/maven-home"
MAVEN_REPOSITORY="$CACHE_DIR/m2"
MARKER="$CACHE_DIR/prepared.json"
RESULT_PRINTED=0

POSTGRES_IMAGE="postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
REDIS_IMAGE="redis:8.8.0-alpine@sha256:9d317178eceac8454a2284a9e6df2466b93c745529947f0cd42a0fa9609d7005"
RYUK_IMAGE="testcontainers/ryuk:0.14.0@sha256:7c1a8a9a47c780ed0f983770a662f80deb115d95cce3e2daa3d12115b8cd28f0"
KAFKA_IMAGE="apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"
IMAGES=("$POSTGRES_IMAGE" "$REDIS_IMAGE" "$RYUK_IMAGE" "$KAFKA_IMAGE")

fail() {
  printf '[FAIL] %s\n' "$*" >&2
  exit 1
}

pass() {
  printf '[PASS] %s\n' "$*"
}

cleanup_targets() {
  find "$ROOT_DIR" \
    -path "$ROOT_DIR/.git" -prune -o \
    -path "$ROOT_DIR/.guide" -prune -o \
    -type d -name target -prune -exec rm -rf -- {} +
}

finish() {
  local status=$?
  cleanup_targets >/dev/null 2>&1 || true
  if (( RESULT_PRINTED == 0 )); then
    if (( status == 0 )); then
      printf 'PREPARE RESULT: PASS\n'
    else
      printf 'PREPARE RESULT: FAIL\n' >&2
    fi
  fi
  exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

need_command() {
  command -v "$1" >/dev/null 2>&1 \
    || fail "필수 명령을 찾을 수 없습니다: $1"
}

source_fingerprint() {
  python3 "$ROOT_DIR/scripts/source_fingerprint.py" "$ROOT_DIR"
}

index_fingerprint() {
  git -C "$ROOT_DIR" ls-files -s -z | shasum -a 256 | awk '{print $1}'
}

run_maven() {
  MAVEN_USER_HOME="$MAVEN_HOME_DIR" \
    "$ROOT_DIR/mvnw" -B -ntp \
    -Dmaven.repo.local="$MAVEN_REPOSITORY" "$@"
}

cd "$ROOT_DIR"
for command_name in git bash java curl python3 docker shasum awk; do
  need_command "$command_name"
done
pass "필수 명령 확인"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || fail "Git 작업 트리에서 실행해야 합니다."
[[ "$(git rev-parse --show-toplevel)" == "$ROOT_DIR" ]] \
  || fail "저장소 루트의 prepare.sh를 실행해야 합니다."
pass "일반 clone/linked worktree 저장소 루트 확인"

for executable in mvnw prepare.sh verify.sh; do
  [[ -x "$executable" ]] || fail "실행 권한이 없습니다: $executable"
done

grep -Fq 'wrapperVersion=3.3.4' .mvn/wrapper/maven-wrapper.properties \
  || fail "Maven Wrapper 3.3.4 설정이 아닙니다."
grep -Fq 'apache-maven/3.9.16/apache-maven-3.9.16-bin.zip' \
  .mvn/wrapper/maven-wrapper.properties \
  || fail "Apache Maven 3.9.16 배포 URL이 아닙니다."
grep -Fq 'distributionSha256Sum=5af3b743dd8b876b5c45da33b676251e5f1687712644abb4ee519ca56e1d89ce' \
  .mvn/wrapper/maven-wrapper.properties \
  || fail "Apache Maven 3.9.16 SHA-256이 다릅니다."
pass "Maven Wrapper 판본과 checksum 확인"

java_major="$(java -version 2>&1 | sed -n '1s/.*version "\([0-9][0-9]*\).*/\1/p')"
[[ "$java_major" =~ ^[0-9]+$ ]] || fail "JDK 주 버전을 읽을 수 없습니다."
(( java_major >= 21 )) || fail "JDK 21 이상이 필요합니다. 현재=$java_major"
pass "JDK $java_major"

python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
python_major="${python_version%%.*}"
python_minor="${python_version#*.}"
(( python_major > 3 || (python_major == 3 && python_minor >= 10) )) \
  || fail "Python 3.10 이상이 필요합니다. 현재=$python_version"
pass "Python $python_version"

docker info >/dev/null 2>&1 || fail "Docker daemon에 연결할 수 없습니다."
pass "Docker daemon"

before_source="$(source_fingerprint)"
before_index="$(index_fingerprint)"
mkdir -p -- "$MAVEN_HOME_DIR" "$MAVEN_REPOSITORY"

run_maven --version >/dev/null
run_maven dependency:get \
  -Dartifact=org.apache.maven.surefire:surefire-junit-platform:3.5.6 \
  -Dtransitive=true
run_maven -DskipTests dependency:go-offline
run_maven -DskipTests verify
pass "reference reactor와 plugin offline cache 준비"

for pom in exercises/*/skeleton/pom.xml; do
  run_maven -f "$pom" -DskipTests dependency:go-offline
  run_maven -f "$pom" -DskipTests verify
done
pass "모든 skeleton의 compile/plugin offline cache 준비"

image_ids=()
for image in "${IMAGES[@]}"; do
  printf '[INFO] Docker image 준비: %s\n' "$image"
  docker pull "$image" >/dev/null
  image_ids+=("$(docker image inspect --format '{{.Id}}' "$image")")
done
pass "immutable Docker image 준비"

cleanup_targets
after_source="$(source_fingerprint)"
after_index="$(index_fingerprint)"
[[ "$before_source" == "$after_source" ]] \
  || fail "prepare.sh가 source bytes, mode 또는 symlink를 변경했습니다."
[[ "$before_index" == "$after_index" ]] \
  || fail "prepare.sh가 Git index를 변경했습니다."
pass "source와 Git index 불변"

java_version="$(java -version 2>&1 | sed -n '1p')"
maven_version="$(run_maven --version | sed -n '1p')"
docker_version="$(docker version --format '{{.Server.Version}}')"
export GUIDE_ID before_source java_version maven_version docker_version
export MAVEN_HOME_DIR MAVEN_REPOSITORY POSTGRES_IMAGE REDIS_IMAGE RYUK_IMAGE KAFKA_IMAGE
export POSTGRES_IMAGE_ID="${image_ids[0]}"
export REDIS_IMAGE_ID="${image_ids[1]}"
export RYUK_IMAGE_ID="${image_ids[2]}"
export KAFKA_IMAGE_ID="${image_ids[3]}"
python3 - "$MARKER" <<'PY'
import json
import os
import sys
from pathlib import Path

marker = Path(sys.argv[1])
payload = {
    "schema": 1,
    "guide_id": os.environ["GUIDE_ID"],
    "input_fingerprint": os.environ["before_source"],
    "java": os.environ["java_version"],
    "maven": os.environ["maven_version"],
    "docker": os.environ["docker_version"],
    "maven_home": os.environ["MAVEN_HOME_DIR"],
    "maven_repository": os.environ["MAVEN_REPOSITORY"],
    "images": {
        os.environ["POSTGRES_IMAGE"]: os.environ["POSTGRES_IMAGE_ID"],
        os.environ["REDIS_IMAGE"]: os.environ["REDIS_IMAGE_ID"],
        os.environ["RYUK_IMAGE"]: os.environ["RYUK_IMAGE_ID"],
        os.environ["KAFKA_IMAGE"]: os.environ["KAFKA_IMAGE_ID"],
    },
}
temporary = marker.with_suffix(".json.tmp")
temporary.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
temporary.replace(marker)
PY
pass "namespaced 준비 marker: .guide/$GUIDE_ID/prepared.json"

RESULT_PRINTED=1
printf 'PREPARE RESULT: PASS\n'
