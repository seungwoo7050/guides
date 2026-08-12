# command-pipeline 기준 구현

이 디렉터리는 workspace 구현과 검증을 끝낸 뒤 비교하는 기준 구현입니다. 번호는 runtime event 순서가 아니라 FD와 자식 process의 실패 경계를 구축하는 **학습용 권장 구현 순서**입니다.

## 구현 순서

| 번호 | 책임 |
|---:|---|
| `1` | `waitpid` 재시도와 public 종료 상태 변환을 분리합니다. |
| `2` | FD 0·1 alias까지 포함해 duplicate와 close 소유권 규칙을 정합니다. |
| `3` | 자식이 FD를 정리한 뒤 `exec`하고 실패를 126·127로 종료합니다. |
| `4` | pipe를 만들고 두 자식을 모두 생성한 뒤 부모가 불필요한 끝을 닫습니다. |
| `5` | 부분 fork 실패를 회수하고 두 자식을 기다린 뒤 오른쪽 상태만 commit합니다. |

별도 project/dependency bootstrap이 없어 `Implementation 0`은 없습니다.
