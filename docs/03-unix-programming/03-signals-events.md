# 시그널과 사건 전달: 비동기 문맥을 작게 유지하기

시그널은 프로세스에 비동기 사건을 알리는 메커니즘입니다. 바이트 스트림이나 일반적인 데이터 전송 수단이 아닙니다. 핵심은 handler에서 많은 일을 하는 것이 아니라, 사건이 발생했다는 사실을 안전하게 기록하고 정상 제어 흐름이 정책·출력·정리를 수행하게 만드는 데 있습니다.

## 생성, 보류, 전달과 처리

시그널의 흐름을 나누어 생각합니다.

```text
생성                보류·마스크 판단             전달과 처리
kill, Ctrl-C, timer  kernel pending 상태           기본 동작 / 무시 / handler
```

각 시그널에는 다음 처리 방식 중 하나가 적용됩니다.

- 기본 동작: 종료, 무시, 정지, 계속 등 시그널별 정책입니다.
- `SIG_IGN`: 명시적으로 무시합니다.
- 사용자 handler: 지정한 함수가 비동기적으로 실행됩니다.

시그널이 block되어 있으면 생성되어도 즉시 handler로 전달되지 않고 pending 상태가 됩니다. block은 일반적으로 삭제가 아니라 전달 지연입니다.

## `signal`보다 `sigaction`

```c
struct sigaction action;

memset(&action, 0, sizeof action);
action.sa_handler = handle_signal;
sigemptyset(&action.sa_mask);
action.sa_flags = 0;

if (sigaction(SIGINT, &action, NULL) < 0)
{
    /* 오류 */
}
```

`sigaction`은 handler, handler 실행 중 추가로 block할 mask와 동작 flag를 명시할 수 있습니다. 역사적 구현 차이가 있었던 `signal`보다 제어가 분명합니다.

대표 flag:

| flag | 의미 |
|---|---|
| `SA_SIGINFO` | 세 인자 handler와 `siginfo_t`를 사용합니다. |
| `SA_RESTART` | 일부 중단된 시스템 호출을 자동 재시작합니다. |
| `SA_NODEFER` | handler 중 같은 시그널의 자동 block을 해제합니다. |
| `SA_RESETHAND` | 한 번 처리한 뒤 기본 동작으로 되돌립니다. |

초기 설계에서는 재진입을 늘리는 `SA_NODEFER` 같은 선택을 피합니다. `SA_RESTART`도 항상 켜는 편의 옵션이 아니라 종료 요청과 `EINTR` 계약을 함께 고려해 결정합니다.

## `SA_SIGINFO`와 발생 원인

```c
static void handle_signal(
    int signal_number,
    siginfo_t *information,
    void *context
)
{
    (void)context;
    /* information->si_code, si_pid 등을 제한적으로 관찰 */
}
```

```c
struct sigaction action;

memset(&action, 0, sizeof action);
action.sa_sigaction = handle_signal;
sigemptyset(&action.sa_mask);
action.sa_flags = SA_SIGINFO;
```

`siginfo_t`의 유효한 필드는 시그널과 발생 원인에 따라 다릅니다. `kill` 또는 `sigqueue`로 전달된 시그널에서는 송신 PID나 값이 의미 있을 수 있지만, 모든 시그널에서 같은 필드를 신뢰하면 안 됩니다.

이 장의 연습은 단순 handler와 self-pipe에 집중하며 송신자 정보를 정책 판단에 사용하지 않습니다.

## 시그널 mask

`sigset_t`는 전용 함수로 초기화합니다.

```c
sigset_t set;
sigset_t previous;

sigemptyset(&set);
sigaddset(&set, SIGUSR1);

if (sigprocmask(SIG_BLOCK, &set, &previous) < 0)
{
    /* 오류 */
}
```

중요한 상태와 handler를 설치하거나 해제할 때 관련 시그널을 block하면 중간 상태를 handler가 관찰하는 경쟁 구간을 제거할 수 있습니다.

멀티스레드 프로그램에서는 `pthread_sigmask`를 사용해 스레드별 mask 정책을 명확히 합니다. 새 스레드는 생성한 스레드의 mask를 상속하므로 생성 순서도 설계 일부입니다.

`sigaction.sa_mask`는 해당 handler가 실행되는 동안 추가로 block할 시그널을 지정합니다. 같은 공유 상태를 만지는 여러 handler의 중첩을 제한할 수 있습니다.

## handler는 임의의 지점에 끼어듭니다

handler는 메인 코드가 거의 어떤 함수를 실행하는 중에도 끼어들 수 있습니다. 메인이 allocator 내부 목록, stdio buffer 또는 locale 상태를 갱신하는 중일 수 있습니다.

handler에서 같은 비재진입 함수를 호출하면 다음 문제가 생길 수 있습니다.

- 내부 lock을 다시 기다리는 교착
- 반쯤 갱신된 전역 상태 손상
- 중복 flush나 출력 섞임
- allocator metadata 손상

POSIX는 async-signal-safe 함수 목록을 규정합니다. `write`, `_exit`, `kill`과 일부 시그널 함수가 대표적입니다. 다음은 안전하다고 가정하지 않습니다.

```text
printf, fprintf, malloc, free
일반 문자열 포맷팅
pthread_mutex_lock
대부분의 사용자 콜백
```

안전한 기본 전략:

```text
handler:
  작은 flag 기록 또는 self-pipe에 한 바이트 write
  즉시 반환

일반 event loop:
  사건을 읽음
  메시지 출력
  메모리 관리
  자식 회수
  종료와 정리
```

## `volatile sig_atomic_t`

handler와 일반 코드가 공유하는 단순 flag에는 다음 타입을 사용할 수 있습니다.

```c
static volatile sig_atomic_t stop_requested;

static void handle_sigterm(int signal_number)
{
    (void)signal_number;
    stop_requested = 1;
}
```

이는 시그널 문맥에서 원자적으로 읽고 쓸 수 있는 제한된 정수 상태를 제공합니다. 다음을 제공하지는 않습니다.

- `counter++` 같은 읽기-수정-쓰기의 복합 원자성
- 여러 필드의 일관된 snapshot
- pthread 사이의 일반 메모리 동기화
- 여러 사건의 정확한 개수 보존

복잡한 데이터는 handler에서 직접 공유하지 말고 self-pipe, `sigwait` 또는 별도 event queue로 전달합니다.

## 표준 시그널은 개수를 보존하지 않을 수 있습니다

전통적인 표준 시그널은 block된 동안 같은 번호가 여러 번 생성되어도 하나의 pending 상태로 합쳐질 수 있습니다.

```text
SIGUSR1을 block한 동안 10번 생성
→ pending 상태는 보통 "SIGUSR1이 있음" 하나
```

따라서 표준 시그널을 정확한 이벤트 카운터로 사용하지 않습니다. “상태를 다시 확인하라”는 통지로 사용하는 편이 맞습니다.

실시간 시그널은 queue와 값 전달을 지원하지만 플랫폼 범위와 용량 한계가 있습니다. 일반 데이터 전송에는 파이프, 소켓 또는 메시지 queue가 더 적합합니다.

## `errno`를 보존합니다

handler가 `write` 같은 함수를 호출하면 `errno`가 바뀔 수 있습니다. 중단된 일반 코드가 기존 오류를 해석해야 하므로 저장하고 복원합니다.

```c
static void handle_signal(int signal_number)
{
    int saved_errno = errno;

    /* async-signal-safe operation */

    errno = saved_errno;
}
```

handler가 `errno`를 설정한 사실을 일반 코드의 함수 실패 원인처럼 노출하지 않습니다.

## `EINTR`와 `SA_RESTART`

블로킹 시스템 호출 중 handler가 실행되면 호출이 `-1`, `errno == EINTR`로 돌아올 수 있습니다.

```c
ssize_t count;

do
{
    count = read(fd, buffer, sizeof buffer);
}
while (count < 0 && errno == EINTR && !stop_requested);
```

`SA_RESTART`는 일부 함수와 조건에서 호출을 자동 재시작하지만 모든 POSIX 함수에 적용되지 않습니다. 종료 요청을 즉시 관찰해야 하는 프로그램에서는 자동 재시작이 원하는 정책이 아닐 수도 있습니다.

호출별로 다음 중 하나를 정합니다.

- 상태 변화가 없으므로 그대로 재시도합니다.
- 종료 flag를 확인한 뒤 재시도 또는 종료합니다.
- deadline의 남은 시간을 다시 계산해 기다립니다.
- 오류로 상위에 전달합니다.

## `pause`와 깨우기 유실

다음 코드는 경쟁이 있습니다.

```c
while (!event_received)
{
    pause();
}
```

조건 확인 직후 `pause` 전에 시그널이 오면 handler가 flag를 세우고 돌아옵니다. 그 뒤 메인 코드가 `pause`에 들어가 다음 시그널을 영원히 기다릴 수 있습니다.

이 문제는 “조건 확인”과 “시그널을 받을 수 있는 상태로 잠들기” 사이의 빈 구간에서 생깁니다.

## `sigsuspend`로 원자적 대기

기다릴 시그널을 먼저 block하고, 임시 mask 적용과 잠들기를 하나의 연산으로 수행합니다.

```c
sigset_t blocked;
sigset_t previous;

sigemptyset(&blocked);
sigaddset(&blocked, SIGUSR1);
sigprocmask(SIG_BLOCK, &blocked, &previous);

while (!event_received)
{
    sigsuspend(&previous);
}

sigprocmask(SIG_SETMASK, &previous, NULL);
```

`sigsuspend`는 임시 mask로 교체하고 잠든 뒤 handler가 실행되어 깨어나면 원래 mask를 복구합니다. 다른 시그널이나 spurious 조건으로도 돌아올 수 있으므로 flag는 `while`로 다시 검사합니다.

## self-pipe 패턴

handler의 사건을 `poll`, `select` 또는 블로킹 event loop로 넘기는 실용적인 방법입니다.

```text
시그널 handler
  write(self_pipe[1], 사건 바이트)

일반 제어 흐름
  self_pipe[0]에서 read
  정상 함수로 정책 처리
```

```c
static volatile sig_atomic_t event_write_fd = -1;

static void handle_signal(int signal_number)
{
    int saved_errno = errno;
    int fd = (int)event_write_fd;
    unsigned char event;

    event = signal_number == SIGUSR1 ? (unsigned char)'U'
                                      : (unsigned char)'T';
    if (fd >= 0)
    {
        ssize_t ignored = write(fd, &event, 1);
        (void)ignored;
    }
    errno = saved_errno;
}
```

파이프는 프로그램 시작 시 만들고 handler는 쓰기 끝만 사용합니다. 일반 루프는 읽기 끝에서 사건을 받아 `puts`, 메모리 해제와 종료 정리를 수행할 수 있습니다.

## nonblocking 쓰기와 사건 손실

self-pipe 쓰기 끝은 `O_NONBLOCK`으로 설정해 pipe가 가득 찼을 때 handler가 멈추지 않게 합니다.

```c
int flags = fcntl(fd, F_GETFL);
fcntl(fd, F_SETFL, flags | O_NONBLOCK);
```

이때 `write`가 `EAGAIN`으로 실패할 수 있습니다. 선택지는 다음과 같습니다.

- 사건별 정확한 개수를 포기하고 “무언가 발생함” flag를 함께 둡니다.
- 고정 크기 queue와 overflow flag를 설계합니다.
- 표준 시그널 자체가 합쳐질 수 있음을 공개 계약에 반영합니다.

handler 안에서 재시도하며 기다리면 nonblocking의 목적을 잃습니다. self-pipe는 무한한 신뢰성 queue가 아닙니다.

## close-on-exec

self-pipe가 자식 `exec` 뒤 필요하지 않다면 `FD_CLOEXEC`를 설정합니다.

```c
int flags = fcntl(fd, F_GETFD);
fcntl(fd, F_SETFD, flags | FD_CLOEXEC);
```

의도하지 않은 descriptor 상속은 자원 누수뿐 아니라 파이프 EOF 지연으로 이어질 수 있습니다. 프로그램이 `exec`하지 않더라도 생성 함수가 소유권과 상속 정책을 함께 정하는 습관이 좋습니다.

## 설치와 정리의 경쟁 구간

전역 쓰기 FD를 설정하기 전에 시그널이 오거나, FD를 닫은 뒤 handler가 실행되면 잘못된 descriptor에 쓸 수 있습니다.

안전한 설치 순서:

```text
관련 시그널 block
→ pipe 생성과 flag 설정
→ 전역 write FD 설정
→ handler 설치
→ mask 복원
→ ready 상태 공개
```

안전한 정리 순서:

```text
관련 시그널 block
→ handler를 기본 또는 이전 동작으로 복원
→ 전역 write FD 무효화
→ pipe FD close
→ 이전 mask 복원
```

handler 둘을 설치하다 둘째가 실패할 수도 있습니다. 이미 바꾼 첫 handler를 원래 상태로 되돌리고 pipe를 닫는 rollback 경로가 필요합니다.

## 사건과 정책을 분리합니다

handler는 `SIGTERM`이 왔다는 사실만 전달합니다. 일반 흐름이 다음 정책을 결정합니다.

- 현재 입력을 취소하고 계속할지
- 정상 종료 요청으로 전환할지
- 자식 process group에 전달할지
- 종료 전에 pending 작업을 비울지
- 어떤 메시지와 종료 상태를 남길지

이 분리는 handler를 작게 만들고 정책 함수를 일반 단위 테스트 대상으로 바꿉니다.

## `SIGCHLD`와 자식 회수

자식이 종료하면 부모는 `SIGCHLD`를 받을 수 있습니다. handler에서 복잡한 자료구조를 갱신하기보다 사건을 기록하고 일반 흐름에서 종료한 자식을 모두 회수합니다.

```c
while ((pid = waitpid(-1, &status, WNOHANG)) > 0)
{
    record_child_exit(pid, status);
}
```

여러 자식 사건이 한 번의 시그널 전달로 합쳐질 수 있으므로 한 번 깨어났을 때 `waitpid(..., WNOHANG)`를 반복합니다.

## 대화형 프로그램의 정책

대화형 부모와 실행한 포그라운드 자식은 같은 시그널을 다르게 처리할 수 있습니다.

```text
부모: SIGINT를 받아 현재 입력 취소, 셸 자체는 계속
자식: exec 전에 SIGINT를 SIG_DFL로 복원, Ctrl-C로 종료
```

완전한 job control은 process group, controlling terminal과 `tcsetpgrp`까지 포함합니다. 이 가이드는 단일 포그라운드 실행의 기본 경계까지만 다룹니다.

## timeout과 시계

`alarm`은 초 단위 timeout을 간단히 만들지만 프로세스당 하나의 alarm이라는 제약이 있습니다.

```c
alarm(3);
/* 사건 대기 */
alarm(0);
```

정밀하거나 여러 deadline이 필요하면 `timer_create`, `setitimer`, `poll` timeout 또는 event loop timer를 고려합니다. `nanosleep`이 `EINTR`로 중단되면 남은 시간을 이용해 재시도합니다.

테스트 timeout은 프로그램의 시간 정확성을 증명하는 기능이 아니라 멈춘 테스트를 끝내는 안전장치입니다.

## 멀티스레드 프로그램의 시그널

멀티스레드 프로세스에서는 process-directed signal이 어느 스레드에 전달될지 정책이 복잡합니다. 흔한 설계는 다음과 같습니다.

1. 시작 스레드에서 관련 시그널을 block합니다.
2. 이후 생성되는 worker가 mask를 상속합니다.
3. 전용 스레드가 `sigwait` 또는 `sigwaitinfo`로 동기적으로 받습니다.
4. 일반 pthread 코드로 사건을 처리합니다.

이 방식은 비동기 handler의 제한을 크게 줄입니다. 단, `sigwait` 대상 시그널을 모든 일반 worker에서 block해야 한다는 전제가 있습니다.

## 실습

[signal-loop](../../exercises/03-unix-programming/03-signal-loop/README.md)에서 다음을 구현합니다.

- `sigaction`을 이용한 `SIGUSR1`, `SIGTERM` handler
- 설치·정리 중 관련 시그널 block
- self-pipe와 nonblocking 쓰기 끝
- descriptor의 close-on-exec 설정
- handler의 `errno` 저장·복원
- 일반 흐름의 출력과 종료 정책
- `SIGUSR1` 뒤 계속 실행
- `SIGTERM` 뒤 handler·descriptor 정리와 상태 0 종료
- 실제 별도 프로세스에 시그널을 보내는 자동 검사
- ready 메시지 뒤에만 테스트가 시그널을 보내는 동기화

검사는 메시지뿐 아니라 정해진 시간 안에 종료하는지, 예상하지 않은 stderr가 없는지, 시그널 기본 동작으로 비정상 종료하지 않는지도 확인합니다.

## 다음 단계

명령 입력을 실행하는 프로그램에서는 lexer·parser·executor와 시그널 정책을 같은 함수에 섞지 않아야 합니다. [셸 파서와 실행기](04-shell-parser-executor.md)에서 처리 계층을 분리합니다.
