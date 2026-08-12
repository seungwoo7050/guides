# owned-string 기준 구현

이 디렉터리는 workspace 구현과 검증을 끝낸 뒤 비교하는 기준 구현입니다. 번호는 실제 과거 작성 이력이 아니라 소유권과 실패 보장을 세우는 **학습용 권장 구현 순서**입니다.

## 구현 순서

| 번호 | 책임 |
|---:|---|
| `1` | allocator와 명확한 빈 상태를 객체에 주입합니다. |
| `2` | 객체 shape와 오버플로 없는 capacity 선택 규칙을 정의합니다. |
| `3` | 입력 별칭을 offset으로 보존하고 변경 전에 크기·오버플로를 검증합니다. |
| `4` | resize가 성공한 뒤에만 새 buffer, 내용과 메타데이터를 commit합니다. |
| `5` | 소유 buffer를 해제하고 반복 정리 가능한 빈 상태로 되돌립니다. |

별도 project/dependency bootstrap이 없어 `Implementation 0`은 없습니다.
