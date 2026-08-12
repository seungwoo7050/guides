#!/bin/sh
set -eu

base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${PYTHON:-python3}
mode=${1:-workspace}

case "$mode" in
    scenarios)
        ;;
    template)
        "$PYTHON" -B "$base_dir/check-evidence.py" --template "$base_dir/template/evidence.md"
        "$PYTHON" -B "$base_dir/check-evidence.py" --self-test
        echo "통과: evidence template과 checker 방향성"
        exit 0
        ;;
    workspace)
        [ ! -L "$base_dir/workspace" ] || { echo "workspace symlink를 허용하지 않습니다." >&2; exit 2; }
        if find "$base_dir/workspace" -type l -print -quit | grep -q .
        then
            echo "workspace 내부 symlink를 허용하지 않습니다." >&2
            exit 2
        fi
        [ -f "$base_dir/workspace/evidence.md" ] || {
            echo "증거 문서가 없습니다. 먼저 scripts/new-workspace.py exercises/07-troubleshooting를 실행하세요." >&2
            exit 2
        }
        [ ! -L "$base_dir/workspace/evidence.md" ] || { echo "evidence symlink를 허용하지 않습니다." >&2; exit 2; }
        exec "$PYTHON" -B "$base_dir/check-evidence.py" "$base_dir/workspace/evidence.md"
        ;;
    *)
        echo "사용법: $0 [workspace|template|scenarios]" >&2
        exit 2
        ;;
esac

for scenario in \
    wrong-db-host \
    wrong-db-password \
    missing-secret \
    wrong-fcgi-port \
    broken-healthcheck \
    data-loss
do
    "$base_dir/run-scenario.sh" "$scenario"
done
echo "통과: 문제 해결 시나리오 6개"
