# signal-loop

`signal-loop`은 POSIX signal을 self-pipe를 통해 일반 event-processing 흐름으로 전달하는 standalone utility다. Signal handler는 pending flag와 wake byte만 기록하고, 출력과 종료 정책은 main control flow에서 수행한다.

## Features

- startup 완료 뒤 `ready pid=<PID>` 출력
- `SIGUSR1`을 `event=SIGUSR1` event로 처리하고 계속 실행
- `SIGTERM`을 `event=SIGTERM` event로 처리한 뒤 상태 `0`으로 종료
- async-signal-safe handler operation만 사용
- non-blocking self-pipe write end와 close-on-exec 설정
- handler installation failure rollback과 이전 disposition 복원
- setup과 teardown 동안 관련 signal 차단
- standard signal coalescing을 명시적으로 허용

## Architecture

Handler는 `sig_atomic_t` pending bits를 설정하고 self-pipe에 wake byte를 시도한다. Pipe가 가득 차 write가 실패해도 이미 남은 wake bytes와 pending bits가 event 존재를 보존한다. Main loop는 wake byte를 소비한 뒤 관련 signals를 잠시 block하고 pending snapshot을 가져온다.

## Build

```sh
make
```

Executable은 `build/signal-loop`에 생성된다.

## Usage

```sh
./build/signal-loop
# ready pid=12345

kill -USR1 12345
# event=SIGUSR1

kill -TERM 12345
# event=SIGTERM
```

## Verification

```sh
make test
make sanitize
```

Python process test는 ready ordering, 순차 `SIGUSR1`, burst signal coalescing, `SIGTERM` shutdown, exit status, unexpected output, timeout을 확인한다.

## Design Decisions

- Handler에서 `printf`, allocation, locking을 수행하지 않는다. `sig_atomic_t` assignment, `write`, `errno` 보존만 사용한다.
- 정확한 signal 발생 횟수를 약속하지 않는다. Standard signal은 pending 상태에서 합쳐질 수 있다.
- Handler와 descriptors의 수명 전환 중에는 `SIGUSR1`과 `SIGTERM`을 block한다.
- 이전 handler dispositions를 저장하고 종료 시 복원한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Minimal async-signal-safe handler | `src/signal_loop.c` |
| 2 | Self-pipe descriptor policy | `src/signal_loop.c` |
| 3 | Handler installation and rollback | `src/signal_loop.c` |
| 4 | Wake consumption and pending snapshot | `src/signal_loop.c` |
| 5 | Signal-blocked initialization | `src/signal_loop.c` |
| 6 | Event policy and reverse-order teardown | `src/signal_loop.c` |

## Scope and Limitations

`SIGUSR1`과 `SIGTERM`만 처리한다. Realtime signal queueing, arbitrary payloads, multiple event sources, `poll`/`select` integration은 제공하지 않는다.
