#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

python3 scripts/check_docs.py

set -- $(python3 scripts/source_fingerprint.py)
FINGERPRINT=$1
FILE_COUNT=$2

mkdir -p .guide/agentic-systems
cat > .guide/agentic-systems/prepared.json <<JSON
{
  "guide": "agentic-systems",
  "profile": "documentation-and-design",
  "source_sha256": "$FINGERPRINT",
  "source_files": $FILE_COUNT
}
JSON

printf 'PREPARED source_files=%s sha256=%s\n' "$FILE_COUNT" "$FINGERPRINT"
