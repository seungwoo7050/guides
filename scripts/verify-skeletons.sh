#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
WORK_ROOT="${GUIDE_VERIFY_WORK_DIR:-$ROOT/.guide/verify}/java-skeleton"

rm -rf -- "$WORK_ROOT"
mkdir -p -- "$WORK_ROOT/support"

map_test_class() {
  local source="$1"
  local relative_path="${source#*/src/test/java/}"
  relative_path="${relative_path%.java}"
  printf '%s\n' "${relative_path//\//.}"
}

compile_support() {
  local sources=()
  local source
  while IFS= read -r source; do
    sources+=("$source")
  done < <(
    find "$ROOT/exercises/test-support/src/main/java" \
      -type f -name '*.java' | sort
  )
  [[ ${#sources[@]} -gt 0 ]] || {
    printf 'test support has no Java sources\n' >&2
    return 1
  }
  javac --release 17 -encoding UTF-8 -Xlint:all \
    -d "$WORK_ROOT/support" \
    "${sources[@]}"
}

verify_expected_failure() {
  local module="$1"
  local name="${module#"$ROOT/"}"
  local safe_name="${name//\//_}"
  local output_dir="$WORK_ROOT/$safe_name"
  local test_file
  local test_class
  local log_file="$WORK_ROOT/$safe_name.log"
  local status
  local expected
  local sources=()
  local source

  mkdir -p -- "$output_dir"
  while IFS= read -r source; do
    sources+=("$source")
  done < <(
    {
      find "$module/src/main/java" -type f -name '*.java'
      find "$module/src/test/java" -type f -name '*.java'
    } | sort
  )

  [[ ${#sources[@]} -gt 0 ]] || {
    printf 'no Java sources in %s\n' "$name" >&2
    return 1
  }

  javac --release 17 -encoding UTF-8 -Xlint:all \
    -cp "$WORK_ROOT/support" \
    -d "$output_dir" \
    "${sources[@]}"

  test_file="$(find "$module/src/test/java" -type f -name '*Test.java' | sort | head -n 1)"
  [[ -n "$test_file" ]] || {
    printf 'no executable test class in %s\n' "$name" >&2
    return 1
  }
  test_class="$(map_test_class "$test_file")"

  set +e
  java -Dfile.encoding=UTF-8 \
    -cp "$WORK_ROOT/support:$output_dir" \
    "$test_class" >"$log_file" 2>&1
  status=$?
  set -e

  if [[ $status -eq 0 ]]; then
    printf 'skeleton unexpectedly passed: %s\n' "$name" >&2
    return 1
  fi
  if ! grep -q 'AssertionError' "$log_file"; then
    printf 'skeleton failed for an unintended reason: %s\n' "$name" >&2
    cat "$log_file" >&2
    return 1
  fi

  case "$name" in
    exercises/01-boundaries-and-failure/01-uncertain-outcome/skeleton) expected='응답 유실 뒤 저장된 결과를 조회해야 합니다' ;;
    exercises/01-boundaries-and-failure/02-service-boundary/skeleton) expected='공유 쓰기를 찾아야 합니다' ;;
    exercises/01-boundaries-and-failure/03-request-decision/skeleton) expected='거절된 요청은 수량을 바꾸면 안 됩니다' ;;
    exercises/02-delivery-and-consistency/01-duplicate-delivery/skeleton) expected='잔액 효과는 한 번이어야 합니다' ;;
    exercises/02-delivery-and-consistency/02-outbox-reconciliation/skeleton) expected='실패한 Outbox는 대기 상태로 남아야 합니다' ;;
    exercises/02-delivery-and-consistency/03-contracts-and-order/skeleton) expected='채널 drift를 조용히 허용하면 안 됩니다' ;;
    exercises/02-delivery-and-consistency/04-read-model-rebuild/skeleton) expected='적용되지 않은 이벤트를 건너뛰면 안 됩니다' ;;
    exercises/03-resilience-and-load/01-retry-budget/skeleton) expected='재시도는 같은 operation ID를 사용해야 합니다' ;;
    exercises/03-resilience-and-load/02-backpressure/skeleton) expected='대기열 상한을 넘은 요청은 즉시 거절해야 합니다' ;;
    exercises/04-release-and-evidence/02-observability-correlation/skeleton) expected='모든 hop이 같은 correlation ID를 유지해야 합니다' ;;
    exercises/04-release-and-evidence/03-chaos-evidence/skeleton) expected='장애 중 Outbox 대기 건을 보존해야 합니다' ;;
    exercises/04-release-and-evidence/04-performance-gate/skeleton) expected='필수 반복 수가 없으면 성능을 판정할 수 없습니다' ;;
    exercises/05-capstone/reservation-flow/skeleton) expected='같은 operation ID를 다른 입력에 재사용하면 거절해야 합니다' ;;
    *)
      printf 'missing expected failure contract for %s\n' "$name" >&2
      return 1
      ;;
  esac
  if ! grep -Fq "$expected" "$log_file"; then
    printf 'skeleton failed at the wrong contract: %s\n' "$name" >&2
    cat "$log_file" >&2
    return 1
  fi

  printf '[PASS] expected contract failure: %s\n' "$name"
}

compile_support

count=0
if [[ $# -gt 0 ]]; then
  for requested in "$@"; do
    if [[ "$requested" == /* ]]; then
      module="$requested"
    else
      module="$ROOT/$requested"
    fi
    [[ -d "$module/src/main/java" && -d "$module/src/test/java" ]] || {
      printf 'not a Java exercise module: %s\n' "$requested" >&2
      exit 2
    }
    verify_expected_failure "$module"
    count=$((count + 1))
  done
else
  while IFS= read -r module; do
    [[ -d "$module/src/main/java" ]] || continue
    verify_expected_failure "$module"
    count=$((count + 1))
  done < <(find "$ROOT/exercises" -type d -name skeleton | sort)
fi

[[ $count -gt 0 ]] || {
  printf 'no Java skeleton modules were found\n' >&2
  exit 1
}

printf '[PASS] %d Java skeleton failure checks\n' "$count"
