# int-vector 기준 구현

이 디렉터리는 workspace 구현과 검증을 끝낸 뒤 비교하는 기준 구현입니다. 번호는 Git 이력이 아니라 상태 불변식과 commit 경계를 만드는 **학습용 권장 구현 순서**입니다.

## 구현 순서

| 번호 | 책임 |
|---:|---|
| `1` | allocator와 빈 vector 상태의 소유자를 정합니다. |
| `2` | `length <= capacity`와 buffer shape를 검증합니다. |
| `3` | 크기 오버플로를 먼저 거부하고 resize 성공 뒤 원소를 commit합니다. |
| `4` | 범위를 검증한 뒤에만 조회 결과를 호출자에게 commit합니다. |
| `5` | buffer를 해제하고 객체를 반복 정리 가능한 빈 상태로 되돌립니다. |

별도 project/dependency bootstrap이 없어 `Implementation 0`은 없습니다.
