# 파일 디스크립터 리다이렉션 관찰

하나의 외부 명령 stdout을 파일로 연결하면서 `O_TRUNC`와 `O_APPEND`, `fork`, `dup2`, `close`, `execvp`, `waitpid`의 책임 경계를 관찰합니다. 파이프라인 구현이나 셸 파서는 포함하지 않습니다.

## 빌드와 검사

```sh
make
make check
```

직접 실행할 때는 모드, 출력 파일과 명령을 차례로 전달합니다.

```sh
./fd_redirection truncate result.txt sh -c 'printf first'
./fd_redirection append result.txt sh -c 'printf second'
```

## 구현 순서

아래 번호는 실제 Git 작성 이력이 아니라, 같은 관찰 프로그램을 다시 만들 때 권장하는 구현 순서입니다.

| 순서 | 위치 | 먼저 고정하는 책임 |
|---:|---|---|
| `1` | `output_flags` | truncate와 append 모드를 서로 다른 `open` 플래그로 변환합니다. |
| `2` | `public_status`, `wait_child` | 자식 회수와 공개 종료 상태 변환을 분리합니다. |
| `3` | `child_redirect_and_exec` | 자식만 stdout 소유권을 바꾸고 실행 실패 상태를 결정합니다. |
| `4` | `main` | 부모가 파일 FD와 자식 수명을 닫고 회수하는 전체 순서를 조립합니다. |

이 scope에는 application bootstrap이나 중간 생성 CLI가 없으므로 Implementation 0은 없습니다.
