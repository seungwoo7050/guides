# record-stream 기준 구현

이 디렉터리는 workspace 구현과 검증을 끝낸 뒤 비교하는 기준 구현입니다. 번호는 파일 배치나 실행 순서가 아니라 pending buffer와 FD 수명을 세우는 **학습용 권장 구현 순서**입니다.

## 구현 순서

| 번호 | 책임 |
|---:|---|
| `1` | borrowed FD, allocator와 빈 pending 상태를 초기화합니다. |
| `2` | 오버플로와 할당 실패 뒤 기존 상태를 보존하며 pending bytes를 늘립니다. |
| `3` | 아직 소비하지 않고 record delimiter 위치만 찾습니다. |
| `4` | 결과 buffer 할당이 성공한 뒤에만 pending record를 소비합니다. |
| `5` | `EINTR`, partial read, EOF와 terminal state를 하나의 next loop로 조합합니다. |
| `6` | owned pending buffer만 해제하고 borrowed FD는 닫지 않습니다. |

별도 project/dependency bootstrap이 없어 `Implementation 0`은 없습니다.
