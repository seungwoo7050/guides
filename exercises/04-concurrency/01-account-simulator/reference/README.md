# account-simulator 기준 구현

이 디렉터리는 workspace 구현과 검증을 끝낸 뒤 비교하는 기준 구현입니다. 번호는 thread scheduling 순서가 아니라 mutex와 계좌 불변식을 세우는 **학습용 권장 구현 순서**입니다.

## 구현 순서

| 번호 | 책임 |
|---:|---|
| `1` | account 값과 mutex의 공동 lifecycle을 초기화합니다. |
| `2` | 두 account를 ID 기준으로 한 번씩 잠그는 canonical lock order를 정합니다. |
| `3` | 잔액·오버플로 조건을 lock 안에서 검사하고 두 잔액을 함께 commit합니다. |
| `4` | 단일·두 계좌 snapshot을 같은 잠금 정책으로 읽고 성공 뒤 결과를 commit합니다. |
| `5` | 모든 thread join 뒤 mutex lifecycle을 끝냅니다. |

별도 project/dependency bootstrap이 없어 `Implementation 0`은 없습니다. ThreadSanitizer는 검증 도구이며 구현 단계가 아닙니다.
