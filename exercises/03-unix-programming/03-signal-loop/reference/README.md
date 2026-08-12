# signal-loop 기준 구현

이 디렉터리는 workspace 구현과 검증을 끝낸 뒤 비교하는 기준 구현입니다. 번호는 signal 도착 순서가 아니라 handler와 일반 제어 흐름의 책임을 나누는 **학습용 권장 구현 순서**입니다.

## 구현 순서

| 번호 | 책임 |
|---:|---|
| `1` | handler가 pending bit와 wake byte만 남기도록 최소화합니다. |
| `2` | self-pipe 양 끝에 close-on-exec와 nonblocking 정책을 적용합니다. |
| `3` | handler 설치 실패 rollback과 이전 disposition 복원을 묶습니다. |
| `4` | wake를 기다리고 blocked signal 상태에서 pending snapshot을 소비합니다. |
| `5` | 대상 signal을 block한 채 pipe, handler와 공개 event FD를 준비합니다. |
| `6` | 일반 흐름이 event 정책을 실행하고 모든 자원을 역순으로 정리합니다. |

별도 project/dependency bootstrap이 없어 `Implementation 0`은 없습니다.
