#!/bin/sh
set -eu

# [Implementation 12-2] Static configuration verification
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
for script in \
    "$base_dir/prepare-secrets.sh" \
    "$base_dir/backup.sh" \
    "$base_dir/restore.sh" \
    "$base_dir/db/docker-entrypoint.sh" \
    "$base_dir/app/docker-entrypoint.sh" \
    "$base_dir/gateway/docker-entrypoint.sh" \
    "$base_dir/tests/integration.sh" \
    "$base_dir/tests/fault-injection.sh"; do
    sh -n "$script"
done
php -l "$base_dir/app/bin/bootstrap.php" >/dev/null
php -l "$base_dir/app/public/index.php" >/dev/null
python - "$base_dir/compose.yaml" "$base_dir/tests/scenarios" <<'PY'
import sys
from pathlib import Path
import yaml
for path in [Path(sys.argv[1]), *sorted(Path(sys.argv[2]).glob('*.yaml'))]:
    value = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise SystemExit(f'invalid YAML document: {path}')
PY
