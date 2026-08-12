# 프로세스 그룹 시그널 전달 관찰

고정된 argv를 새 프로세스 그룹에서 실행하고 부모가 받은 `SIGINT`·`SIGTERM`을 그 그룹 전체에 전달합니다. 셸 문법, token 자료구조와 리다이렉션은 포함하지 않으므로 `command-runner` 연습의 답안이 아닙니다.

## 빌드와 검사

```sh
make
make check
```

## 구현 순서

아래 번호는 실제 Git 작성 이력이 아니라, 시그널 소유권 경쟁을 줄이는 권장 구현 순서입니다.

| 순서 | 위치 | 먼저 고정하는 책임 |
|---:|---|---|
| `1` | `forward_signal` | handler가 공개된 process-group ID만 읽고 그룹 전달만 수행합니다. |
| `2` | `wait_child`, `public_status` | `EINTR` 재시도와 종료 상태 변환을 분리합니다. |
| `3` | `child_exec` | 자식이 기본 disposition과 원래 mask를 복구한 뒤 실행합니다. |
| `4` | `main`의 setup | 관련 시그널을 block한 구간에서 fork, `setpgid`, group 공개를 끝냅니다. |
| `5` | `main`의 cleanup | wait 뒤 group 공개를 해제하고 이전 handler와 mask를 역순 복구합니다. |

이 scope에는 application bootstrap이나 중간 생성 CLI가 없으므로 Implementation 0은 없습니다.
