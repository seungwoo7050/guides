#!/usr/bin/env python3
"""reference package의 명령행 진입점입니다."""

# [Implementation 9-3] 이 얇은 entrypoint는 import 부작용 없이 package main의 정수 상태를 process exit status로 전달합니다.
from kernel_model.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
