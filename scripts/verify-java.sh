#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
WORK_ROOT="${GUIDE_VERIFY_WORK_DIR:-$ROOT/.guide/verify}/java-reference"

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

verify_module() {
  local module="$1"
  local name="${module#"$ROOT/"}"
  local safe_name="${name//\//_}"
  local output_dir="$WORK_ROOT/$safe_name"
  local test_file
  local test_class
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
  if [[ "$(find "$module/src/test/java" -type f -name '*Test.java' | wc -l | tr -d ' ')" != "1" ]]; then
    printf 'each exercise must expose exactly one *Test.java main: %s\n' "$name" >&2
    return 1
  fi
  test_class="$(map_test_class "$test_file")"

  java -Dfile.encoding=UTF-8 \
    -cp "$WORK_ROOT/support:$output_dir" \
    "$test_class"

  printf '[PASS] %s\n' "$name"
}

command -v java >/dev/null 2>&1 || {
  printf 'java is required\n' >&2
  exit 1
}
command -v javac >/dev/null 2>&1 || {
  printf 'javac is required\n' >&2
  exit 1
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
    verify_module "$module"
    count=$((count + 1))
  done
else
  while IFS= read -r module; do
    [[ -d "$module/src/main/java" ]] || continue
    verify_module "$module"
    count=$((count + 1))
  done < <(find "$ROOT/exercises" -type d -name reference | sort)
fi

[[ $count -gt 0 ]] || {
  printf 'no Java reference modules were found\n' >&2
  exit 1
}

printf '[PASS] %d Java reference exercises\n' "$count"
