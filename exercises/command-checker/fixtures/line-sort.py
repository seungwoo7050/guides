#!/usr/bin/env python3
"""표준 입력의 정수를 오름차순으로 한 줄씩 출력하는 검사 대상입니다."""

from __future__ import annotations

import sys


def main() -> int:
    try:
        values = [int(token) for token in sys.stdin.read().split()]
    except ValueError as error:
        print(f"정수가 아닌 입력입니다: {error}", file=sys.stderr)
        return 2
    if values:
        sys.stdout.write("\n".join(str(value) for value in sorted(values)) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
