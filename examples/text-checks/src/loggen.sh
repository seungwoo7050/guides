#!/bin/sh
set -eu

case ${1-} in
    ok)
        cat <<'EOT'
100 1 start
105 2 start
120 1 work
130 1 done
140 2 work
150 2 done
EOT
        ;;
    bad-format)
        cat <<'EOT'
100 1 start
bad line
130 1 done
EOT
        ;;
    duplicate)
        cat <<'EOT'
100 1 start
120 1 done
130 1 work
EOT
        ;;
    error)
        printf '오류: 입력이 올바르지 않습니다\n' >&2
        exit 1
        ;;
    *)
        printf '사용법: %s ok|bad-format|duplicate|error\n' "$0" >&2
        exit 2
        ;;
esac
