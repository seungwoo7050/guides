# command-pipeline

`command-pipeline`은 두 external command를 POSIX pipe로 연결하는 C library다. 두 child를 모두 시작한 뒤 기다리고, parent와 child가 사용하지 않는 pipe ends를 닫아 큰 stream에서도 deadlock 없이 동작한다.

## Features

- `argv` 배열 두 개를 직접 받아 `left | right` 실행
- 마지막 command의 exit status를 pipeline status로 반환
- command-not-found `127`, exec failure `126`, signal termination `128 + signal`
- `EINTR`에 안전한 `dup2`와 `waitpid`
- 부분 `fork` 실패 시 이미 생성한 child 회수
- 닫힌 standard descriptor가 pipe FD `0` 또는 `1`로 재사용되는 경우 처리
- 반복 실행 시 descriptor leak 방지

## Architecture

`run_pipeline`은 pipe를 만든 뒤 left child와 right child를 순서대로 생성한다. 각 child는 필요한 standard stream을 연결하고 불필요한 descriptors를 닫은 뒤 `execvp`를 호출한다. Parent는 두 pipe ends를 즉시 닫고 두 child를 모두 회수한다.

## Build

```sh
make
```

정적 library는 `build/libcommand_pipeline.a`에 생성된다.

## Usage

```c
char *left[] = {"printf", "alpha\\nbeta\\n", NULL};
char *right[] = {"wc", "-l", NULL};
int status;

if (run_pipeline(left, right, &status) != 0)
{
    /* process setup or collection failed */
}
```

Library call 자체가 성공하면 `0`을 반환하고 right command의 normalized status를 `*out_status`에 기록한다. 준비, `fork`, `waitpid` 실패는 `-1`이며 output status를 변경하지 않는다.

## Verification

```sh
make test
make sanitize
```

검사는 4 MiB stream 전달, standard FD 재사용, left/right exit status, signal termination, missing/non-executable commands, 반복 실행 후 FD count, invalid inputs를 확인한다.

## Design Decisions

- 공개 pipeline status는 shell과 같이 마지막 command에서 결정한다.
- 두 child를 생성하기 전에 left child를 기다리지 않는다. 그렇지 않으면 pipe capacity를 넘는 output에서 deadlock이 발생할 수 있다.
- `dup2(source, destination)`에서 두 FD가 같으면 duplicate하지 않으며, 최종 standard stream으로 사용 중인 pipe end를 정리 단계에서 닫지 않는다.
- `execvp` 실패는 child 내부의 exit status로 전달하고 library setup failure와 구분한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Public pipeline contract | `include/command_pipeline.h` |
| 2 | Wait and status normalization | `src/command_pipeline.c` |
| 3 | Descriptor duplication and close rules | `src/command_pipeline.c` |
| 4 | Child exec boundary | `src/command_pipeline.c` |
| 5 | Two-process composition | `src/command_pipeline.c` |
| 6 | Partial-fork recovery and result commit | `src/command_pipeline.c` |

## Scope and Limitations

정확히 두 command만 지원한다. shell parsing, redirection, environment assignment, job control, arbitrary-length pipelines는 제공하지 않는다.
