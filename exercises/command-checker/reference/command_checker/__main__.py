# [Implementation 1-1] module 실행도 하나의 cli.main에 위임해 종료 상태 계약을 공유합니다.
from .cli import main

raise SystemExit(main())
