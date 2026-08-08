#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -eq 1 ]] || { printf '사용법: %s exercises/<경로>\n' "$0" >&2; exit 2; }

requested="$1"
case "$requested" in
    exercises/*) ;;
    *) printf 'exercise 경로만 허용합니다: %s\n' "$requested" >&2; exit 2 ;;
esac

base="$ROOT/$requested"
[[ -d "$base/skeleton" ]] || { printf 'skeleton이 없습니다: %s\n' "$requested" >&2; exit 1; }
[[ ! -e "$base/workspace" ]] || { printf 'workspace가 이미 있습니다: %s/workspace\n' "$requested" >&2; exit 1; }

cp -R "$base/skeleton" "$base/workspace"
printf '생성됨: %s/workspace\n' "$requested"
