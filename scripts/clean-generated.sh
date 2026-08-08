#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
rm -rf -- "$ROOT/.verify"
for base in "$ROOT/examples" "$ROOT/exercises" "$ROOT/scripts"; do
    [[ -d "$base" ]] || continue
    find "$base" -type d -name __pycache__ -prune -exec rm -rf -- {} +
    find "$base" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
done
printf '[clean] generated Python cache와 legacy .verify만 제거했습니다.\n'
