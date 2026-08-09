#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "usage: $0 <exercise-or-capstone-directory> [destination]" >&2
  exit 2
fi

SOURCE=$1
case "$SOURCE" in
  /*) SOURCE_ABS=$SOURCE ;;
  *) SOURCE_ABS=$ROOT/$SOURCE ;;
esac
SOURCE_ABS=$(CDPATH= cd -- "$SOURCE_ABS" 2>/dev/null && pwd) || {
  echo "ERROR: source directory does not exist: $SOURCE" >&2
  exit 1
}

case "$SOURCE_ABS" in
  "$ROOT"/exercises/*|"$ROOT"/capstone/*) ;;
  *)
    echo "ERROR: source must be under exercises/ or capstone/" >&2
    exit 1
    ;;
esac

if [ ! -f "$SOURCE_ABS/README.md" ]; then
  echo "ERROR: source has no README.md: $SOURCE_ABS" >&2
  exit 1
fi

if [ "$#" -eq 2 ]; then
  DEST=$2
else
  DEST=$SOURCE_ABS/workspace
fi
case "$DEST" in
  /*) DEST_ABS=$DEST ;;
  *) DEST_ABS=$ROOT/$DEST ;;
esac

if [ -e "$DEST_ABS" ] || [ -L "$DEST_ABS" ]; then
  echo "ERROR: destination already exists: $DEST_ABS" >&2
  exit 1
fi

mkdir -p "$DEST_ABS/evidence" "$DEST_ABS/fixtures" "$DEST_ABS/implementation"
SOURCE_REL=${SOURCE_ABS#"$ROOT"/}
cat > "$DEST_ABS/README.md" <<EOF
# 작업 공간

원본 과제: \`$SOURCE_REL\`

## 선택한 profile

- target/model:
- toolchain/version:
- source revision:

## 구현 범위

## 의도적 비범위

## 실행과 검증

## 확인하지 못한 항목
EOF
cat > "$DEST_ABS/design.md" <<'EOF'
# 설계

## 상태와 소유자

## 입력 사건

## 불변식

## timeout, reset와 recovery

## 검증 계획
EOF
cat > "$DEST_ABS/report.md" <<'EOF'
# 결과

## 실행한 검사

## raw evidence

## 결과와 반증

## 검증의 한계

## 다음 단계
EOF

echo "CREATED $DEST_ABS"
