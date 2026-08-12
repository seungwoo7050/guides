# Readline 입력 어댑터 관찰

같은 REPL 정책을 plain `getline` 입력과 선택적인 GNU Readline 입력에 연결합니다. TTY일 때만 prompt·history·completion을 활성화하고, 파이프 입력에서는 결정적인 plain 경로를 유지하는 어댑터 경계를 관찰합니다.

## 빌드와 검사

Readline 없이도 기본 검사를 실행할 수 있습니다.

```sh
make check
```

개발 파일이 준비된 환경에서는 다음을 추가로 실행합니다.

```sh
make readline-check
make run-readline
```

자동 검사는 비대화형 입력 경계를 확인합니다. TTY completion과 history 탐색은 `make run-readline`로 직접 관찰해야 합니다.

## 구현 순서

아래 번호는 실제 Git 작성 이력이 아니라, 입력 소유권과 선택 기능을 분리하는 권장 구현 순서입니다.

| 순서 | 위치 | 먼저 고정하는 책임 |
|---:|---|---|
| `1` | `plain_read_line` | plain 경로의 할당·EOF·newline 제거 계약을 정합니다. |
| `2` | Readline completion/history helpers | Readline이 소유하는 후보와 history 범위를 어댑터 안에 가둡니다. |
| `3` | `read_command_line` | TTY 여부에 따라 두 입력 backend 중 하나를 선택합니다. |
| `4` | `handle_line` | 입력 backend와 독립적인 명령 정책을 구현합니다. |
| `5` | `main` | 한 줄의 소유권을 처리 뒤 항상 해제하는 REPL 수명을 조립합니다. |

이 scope에는 application bootstrap이나 중간 생성 CLI가 없으므로 Implementation 0은 없습니다.
