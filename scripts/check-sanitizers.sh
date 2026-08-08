#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
CC=${CC:-cc}
TEMPORARY="$(mktemp -d "${TMPDIR:-/tmp}/guide-architecture-sanitize.XXXXXX")"
cleanup() { rm -rf -- "$TEMPORARY"; }
trap cleanup EXIT INT TERM HUP
for source in \
    examples/layout-benchmark/layout_benchmark.c \
    examples/branch-benchmark/branch_benchmark.c \
    examples/vectorization-report/vector_sum.c \
    examples/false-sharing/false_sharing.c
do
    name=$(basename "$source" .c)
    extra=()
    case "$source" in
        *false-sharing*) extra=(-pthread) ;;
        *vectorization*) extra=(-lm) ;;
    esac
    "$CC" -D_POSIX_C_SOURCE=200809L -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=address,undefined -fno-omit-frame-pointer "$ROOT/$source" "${extra[@]}" \
        -o "$TEMPORARY/$name"
    case "$name" in
        layout_benchmark) args=(128 96 2) ;;
        branch_benchmark) args=(200000) ;;
        false_sharing) args=(2 100000) ;;
        vector_sum) args=() ;;
    esac
    ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 "$TEMPORARY/$name" "${args[@]}" >/dev/null
    printf '[PASS] sanitizer: %s\n' "$source"
done
