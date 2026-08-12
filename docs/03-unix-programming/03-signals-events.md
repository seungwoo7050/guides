# 시그널과 이벤트 전달: 비동기 문맥 최소화

시그널은 프로세스에 비동기적인 이벤트가 발생했음을 알리는 메커니즘입니다. 바이트 스트림처럼 데이터를 전달하는 수단도 아니고, 일반적인 메시지 큐를 대신하는 기능도 아닙니다.

시그널 처리에서 중요한 것은 handler 안에서 많은 일을 수행하는 것이 아닙니다. handler에서는 이벤트가 발생했다는 사실만 안전하게 기록하고, 출력·메모리 관리·자식 회수·종료와 같은 실제 정책은 일반 제어 흐름에서 처리하는 것이 기본 원칙입니다.

## 생성·보류·전달·처리

시그널이 처리되기까지의 과정을 나누어 생각할 수 있습니다.

```text
생성                  pending·mask 판단              전달과 처리
kill, Ctrl-C, timer   kernel의 pending 상태          기본 동작 / 무시 / handler
```

각 시그널에는 다음 중 하나의 처리 방식이 적용됩니다.

* 기본 동작: 종료, 무시, 정지, 계속 등 시그널마다 정해진 동작을 수행합니다.
* `SIG_IGN`: 해당 시그널을 명시적으로 무시합니다.
* 사용자 handler: 등록한 함수가 시그널 전달 시 실행됩니다.

시그널이 block되어 있다면 생성되더라도 즉시 handler가 실행되지 않고 pending 상태로 남습니다. 일반적인 시그널 block은 시그널을 없애는 것이 아니라 **전달 시점을 늦추는 것**입니다.

## `signal`보다 `sigaction`

POSIX 프로그램에서는 시그널 handler를 설치할 때 `signal`보다 `sigaction`을 사용하는 편이 좋습니다.

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

`sigaction`을 사용하면 handler뿐 아니라 handler가 실행되는 동안 추가로 block할 시그널과 세부 동작을 명시적으로 지정할 수 있습니다.

대표적인 flag는 다음과 같습니다.

| flag           | 의미                                      |
| -------------- | --------------------------------------- |
| `SA_SIGINFO`   | 세 인자 handler와 `siginfo_t`를 사용합니다.       |
| `SA_RESTART`   | 일부 중단된 시스템 호출을 자동으로 다시 시작합니다.           |
| `SA_NODEFER`   | handler 실행 중 같은 시그널을 자동으로 block하지 않습니다. |
| `SA_RESETHAND` | 한 번 처리한 뒤 해당 시그널의 동작을 기본값으로 되돌립니다.      |

초기 설계에서는 불필요한 재진입 가능성을 높이는 `SA_NODEFER` 같은 옵션을 피하는 편이 안전합니다.

`SA_RESTART` 역시 항상 켜 두는 편의 옵션으로 생각해서는 안 됩니다. 시스템 호출이 중단되었을 때 즉시 종료 요청을 확인해야 하는지, 아니면 자동으로 작업을 이어가야 하는지를 프로그램의 `EINTR` 정책과 함께 결정해야 합니다.

## `SA_SIGINFO`와 발생 정보

시그널의 발생 원인에 관한 추가 정보가 필요하다면 `SA_SIGINFO`를 사용할 수 있습니다.

```c
static void handle_signal(
    int signal_number,
    siginfo_t *information,
    void *context
)
{
    (void)context;

    /* information->si_code, si_pid 등을 필요한 범위에서 확인 */
}
```

```c
struct sigaction action;

memset(&action, 0, sizeof action);
action.sa_sigaction = handle_signal;
sigemptyset(&action.sa_mask);
action.sa_flags = SA_SIGINFO;
```

`siginfo_t`에서 어떤 필드가 의미 있는지는 시그널의 종류와 발생 원인에 따라 달라집니다.

예를 들어 `kill`이나 `sigqueue`를 통해 전달된 시그널에서는 송신 프로세스의 PID나 함께 전달한 값이 의미 있을 수 있지만, 모든 시그널에서 같은 필드를 유효하다고 가정해서는 안 됩니다.

이 장의 연습에서는 발생 주체에 따른 정책까지 다루지 않고, 단순한 handler와 self-pipe를 통한 이벤트 전달에 집중합니다.

## 시그널 마스크

`sigset_t`는 전용 함수를 사용해 초기화하고 조작합니다.

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

handler가 참조하는 상태를 준비하거나 handler를 설치·해제하는 동안 관련 시그널을 block하면, 초기화가 끝나기 전에 handler가 실행되는 경쟁 구간을 막을 수 있습니다.

멀티스레드 프로그램에서는 `pthread_sigmask`를 사용해 각 스레드의 시그널 마스크 정책을 명확하게 관리합니다.

새로운 스레드는 자신을 만든 스레드의 시그널 마스크를 상속하므로, **언제 시그널을 block하고 언제 worker를 생성하는가** 역시 설계의 일부입니다.

`sigaction.sa_mask`는 특정 handler가 실행되는 동안 추가로 block할 시그널을 지정합니다. 같은 상태를 다루는 여러 handler가 서로 중첩되는 것을 제한할 때 사용할 수 있습니다.

## handler는 임의의 실행 지점에 끼어들 수 있습니다

시그널 handler는 일반 코드가 거의 어떤 작업을 수행하는 중에도 실행될 수 있습니다.

예를 들어 메인 코드가 다음과 같은 내부 상태를 변경하는 도중일 수 있습니다.

* 메모리 할당기의 내부 자료구조
* stdio 버퍼
* locale 관련 전역 상태
* 라이브러리 내부 lock

이때 handler가 같은 비재진입 함수를 호출하면 문제가 발생할 수 있습니다.

* 이미 잡혀 있는 내부 lock을 다시 기다리면서 교착 상태에 빠짐
* 아직 갱신이 끝나지 않은 전역 상태를 다시 수정함
* 출력 버퍼가 중복으로 처리되거나 출력이 섞임
* allocator의 내부 metadata가 손상됨

POSIX는 시그널 handler에서 안전하게 호출할 수 있는 async-signal-safe 함수들을 별도로 규정합니다.

`write`, `_exit`, `kill`과 일부 시그널 관련 함수가 대표적입니다.

반대로 다음과 같은 함수나 작업을 handler에서 안전하다고 가정해서는 안 됩니다.

```text
printf, fprintf
malloc, free
일반적인 문자열 포맷팅
pthread_mutex_lock
대부분의 사용자 정의 콜백
```

기본적인 설계는 다음과 같습니다.

```text
handler:
  작은 flag를 기록하거나
  self-pipe에 최소한의 데이터를 write
  즉시 반환

일반 이벤트 루프:
  이벤트 확인
  메시지 출력
  메모리 관리
  자식 회수
  종료와 자원 정리
```

handler의 역할은 **정책을 실행하는 것**이 아니라 **일반 제어 흐름을 깨우는 것**에 가깝습니다.

## `volatile sig_atomic_t`

handler와 일반 코드 사이에서 단순한 상태를 공유해야 한다면 `volatile sig_atomic_t`를 사용할 수 있습니다.

```c
static volatile sig_atomic_t stop_requested;

static void handle_sigterm(int signal_number)
{
    (void)signal_number;
    stop_requested = 1;
}
```

이 타입은 handler와 일반 제어 흐름 사이에서 단순한 정수 값을 읽고 쓰는 용도에 적합합니다.

그러나 다음 기능까지 제공하는 것은 아닙니다.

* `counter++` 같은 읽기-수정-쓰기 연산 전체의 원자성
* 여러 변수로 구성된 상태의 일관된 snapshot
* pthread 사이의 일반적인 메모리 동기화
* 동일한 이벤트가 몇 번 발생했는지 정확한 개수 보존

복잡한 정보를 handler와 직접 공유하기보다 self-pipe, `sigwait` 또는 별도의 이벤트 큐로 전달하는 편이 좋습니다.

## 표준 시그널은 발생 횟수를 보존하지 않습니다

전통적인 표준 시그널은 같은 번호의 시그널이 여러 번 발생했다고 해서 그 횟수가 그대로 보존된다고 기대할 수 없습니다.

예를 들어 해당 시그널을 block한 상태에서 같은 시그널이 여러 번 생성되면 다음과 같이 하나의 pending 상태로 합쳐질 수 있습니다.

```text
SIGUSR1을 block한 상태에서 10번 생성

→ "SIGUSR1이 pending 상태임"
```

따라서 표준 시그널을 정확한 이벤트 카운터로 사용해서는 안 됩니다.

다음과 같은 의미로 사용하는 편이 적절합니다.

```text
"이 상태를 다시 확인해야 한다."
"종료 요청이 들어왔다."
"자식 상태가 변했을 가능성이 있다."
```

실시간 시그널은 queue와 값 전달을 지원하지만 대기열의 용량과 플랫폼 범위를 고려해야 합니다.

일반적인 데이터 전달에는 파이프, 소켓이나 메시지 큐처럼 데이터 전송을 목적으로 설계된 IPC를 사용하는 편이 적절합니다.

## handler에서는 `errno`를 보존합니다

handler가 `write` 같은 함수를 호출하면 `errno` 값이 바뀔 수 있습니다.

handler가 실행되기 직전의 일반 코드가 기존 `errno`를 해석해야 할 수도 있으므로 handler에서는 값을 저장했다가 복원합니다.

```c
static void handle_signal(int signal_number)
{
    int saved_errno = errno;

    /* async-signal-safe 작업 */

    errno = saved_errno;
}
```

handler 내부에서 호출한 함수가 설정한 `errno`가 중단된 일반 코드의 실패 원인인 것처럼 노출되어서는 안 됩니다.

## `EINTR`와 `SA_RESTART`

블로킹 시스템 호출 도중 시그널 handler가 실행되면 시스템 호출이 중단되어 다음과 같이 반환할 수 있습니다.

```text
-1
errno == EINTR
```

따라서 호출 목적에 따라 재시도 정책을 정해야 합니다.

```c
ssize_t count;

do
{
    count = read(fd, buffer, sizeof buffer);
}
while (count < 0 && errno == EINTR && !stop_requested);
```

`SA_RESTART`를 사용하면 일부 시스템 호출은 자동으로 다시 시작될 수 있습니다.

하지만 모든 시스템 호출에 적용되는 것은 아니며, 호출 조건에 따라 동작도 달라질 수 있습니다.

특히 시그널을 통해 종료 요청을 전달하는 프로그램에서는 시스템 호출을 자동으로 다시 시작하는 것이 오히려 원하는 동작을 늦출 수 있습니다.

따라서 시스템 호출마다 다음 중 어떤 정책을 사용할지 정합니다.

* 프로그램 상태에 변화가 없으므로 그대로 다시 시도합니다.
* 종료 flag를 확인한 뒤 계속할지 중단할지 결정합니다.
* deadline까지 남은 시간을 다시 계산한 뒤 기다립니다.
* `EINTR`를 상위 호출자에게 그대로 전달합니다.

## `pause`와 깨우기 유실

다음 코드는 겉보기에는 자연스럽지만 경쟁 조건이 있습니다.

```c
while (!event_received)
{
    pause();
}
```

실행 순서를 다음과 같이 생각해 봅니다.

```text
event_received 확인 → false

시그널 발생
→ handler 실행
→ event_received = 1

handler 반환

pause 호출
→ 다음 시그널을 기다림
```

시그널이 조건 검사와 `pause` 사이에 도착하면 이미 필요한 이벤트를 처리했는데도 이후 `pause`가 새로운 시그널을 기다릴 수 있습니다.

문제는 다음 두 작업이 원자적으로 이루어지지 않는다는 점입니다.

```text
조건 확인
시그널을 받을 수 있는 상태로 잠들기
```

## `sigsuspend`를 이용한 원자적 대기

이 문제를 피하려면 기다릴 시그널을 먼저 block한 뒤 `sigsuspend`를 사용할 수 있습니다.

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

먼저 `SIGUSR1`을 block하기 때문에 조건을 검사하는 동안 해당 시그널의 handler가 실행되지 않습니다.

`sigsuspend`는 시그널 마스크를 임시 값으로 교체하는 것과 대기 상태로 들어가는 것을 하나의 원자적인 동작으로 수행합니다.

시그널을 처리하고 깨어나면 기존 마스크가 다시 적용됩니다.

원하는 이벤트가 아닌 다른 시그널 때문에도 대기가 끝날 수 있으므로 조건은 `if`가 아니라 `while`로 다시 확인해야 합니다.

## self-pipe 패턴

self-pipe는 시그널 handler에서 발생한 이벤트를 `poll`, `select` 같은 일반적인 FD 기반 이벤트 루프로 전달하는 실용적인 방법입니다.

```text
시그널 handler
  ↓
self-pipe write end에 작은 값 기록
  ↓
커널 파이프
  ↓
일반 이벤트 루프가 read
  ↓
정상적인 코드에서 정책 처리
```

예를 들어 다음처럼 handler가 이벤트 종류를 한 바이트로 기록할 수 있습니다.

```c
static volatile sig_atomic_t event_write_fd = -1;

static void handle_signal(int signal_number)
{
    int saved_errno = errno;
    int fd = (int)event_write_fd;
    unsigned char event;

    event = signal_number == SIGUSR1
        ? (unsigned char)'U'
        : (unsigned char)'T';

    if (fd >= 0)
    {
        ssize_t ignored = write(fd, &event, 1);
        (void)ignored;
    }

    errno = saved_errno;
}
```

파이프는 프로그램 초기화 단계에서 만들어 둡니다.

handler에서는 쓰기 끝에 최소한의 정보만 기록하고, 읽기 끝은 일반 이벤트 루프에서 처리합니다.

따라서 다음과 같은 작업은 handler 밖에서 정상적인 코드로 수행할 수 있습니다.

```text
puts나 fprintf를 이용한 출력
메모리 할당과 해제
복잡한 상태 변경
자식 프로세스 회수
종료 절차
```

self-pipe의 핵심 목적은 시그널 handler를 일반적인 FD 기반 제어 흐름과 연결하는 것입니다.

## nonblocking 쓰기와 이벤트 손실

self-pipe의 쓰기 끝은 `O_NONBLOCK`으로 설정하는 편이 안전합니다.

```c
int flags = fcntl(fd, F_GETFL);

if (flags >= 0)
{
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}
```

파이프가 가득 찬 상태에서 handler의 `write`가 blocking된다면 handler 자체가 멈출 수 있기 때문입니다.

nonblocking 모드에서는 파이프가 가득 찼을 때 `write`가 다음과 같이 실패할 수 있습니다.

```text
-1
errno == EAGAIN
```

따라서 self-pipe를 설계할 때는 이벤트 손실에 대한 정책도 필요합니다.

대표적인 선택은 다음과 같습니다.

* 정확한 발생 횟수는 포기하고 별도의 "이벤트가 있음" flag를 둡니다.
* 고정 크기 큐와 overflow 상태를 따로 관리합니다.
* 표준 시그널 자체가 발생 횟수를 보존하지 않는다는 점을 공개 계약에 반영합니다.

handler 내부에서 파이프에 공간이 생길 때까지 반복해서 기다리면 nonblocking으로 만든 목적이 사라집니다.

self-pipe는 무제한으로 이벤트를 보존하는 신뢰성 있는 메시지 큐가 아닙니다.

## close-on-exec

self-pipe가 자식의 `exec` 이후 필요하지 않다면 해당 파일 디스크립터에 `FD_CLOEXEC`를 설정합니다.

```c
int flags = fcntl(fd, F_GETFD);

if (flags >= 0)
{
    fcntl(fd, F_SETFD, flags | FD_CLOEXEC);
}
```

이 설정이 적용된 FD는 성공한 `exec` 과정에서 닫힙니다.

필요하지 않은 파일 디스크립터가 의도치 않게 새 프로그램으로 상속되면 단순한 자원 누수뿐 아니라 파이프의 EOF가 늦어지는 문제도 발생할 수 있습니다.

프로그램에서 실제로 `exec`를 사용하지 않더라도 FD를 생성하는 시점에 다음 두 가지를 함께 정하는 습관이 좋습니다.

```text
누가 이 FD를 닫는가?
exec 뒤에도 이 FD가 살아 있어야 하는가?
```

## 설치와 정리 사이의 경쟁 구간

self-pipe의 전역 쓰기 FD를 설정하기 전에 시그널이 전달되거나, FD를 닫은 뒤 handler가 다시 실행되면 handler가 유효하지 않은 상태를 볼 수 있습니다.

따라서 초기화와 정리 과정에서도 관련 시그널을 block해야 합니다.

안전한 설치 순서는 다음과 같이 구성할 수 있습니다.

```text
관련 시그널 block
→ pipe 생성
→ FD flag 설정
→ handler가 사용할 상태 준비
→ handler 설치
→ 이전 시그널 mask 복원
→ 초기화 완료 상태 공개
```

정리할 때는 반대 방향으로 수명을 끝냅니다.

```text
관련 시그널 block
→ handler를 이전 동작으로 복원
→ handler가 참조하는 FD를 무효화
→ pipe FD close
→ 이전 mask 복원
```

여러 handler를 설치하는 과정도 부분적으로 실패할 수 있습니다.

예를 들어 첫 번째 handler는 설치했지만 두 번째 handler 설치에 실패했다면 이미 변경한 첫 번째 handler를 원래 상태로 되돌리고 생성한 파이프도 닫아야 합니다.

초기화 함수도 정상 경로뿐 아니라 **부분 초기화 뒤 rollback 경로**를 가져야 합니다.

## 이벤트 전달과 정책을 분리합니다

handler가 `SIGTERM`을 받았다고 해서 handler 내부에서 프로그램 종료 절차 전체를 수행할 필요는 없습니다.

handler는 다음 사실만 전달할 수 있습니다.

```text
SIGTERM이 도착했다.
```

그 뒤 일반 제어 흐름이 프로그램의 정책을 결정합니다.

* 현재 입력 작업을 취소할 것인가?
* 정상적인 종료 요청으로 전환할 것인가?
* 실행 중인 자식 process group에도 시그널을 전달할 것인가?
* 종료하기 전에 남아 있는 작업을 처리할 것인가?
* 어떤 메시지를 출력하고 어떤 종료 상태를 사용할 것인가?

이렇게 이벤트의 **발생 통지**와 **정책 실행**을 분리하면 handler를 작게 유지할 수 있습니다.

동시에 정책 함수는 일반 함수가 되므로 handler 문맥 없이 단위 테스트하기도 쉬워집니다.

## `SIGCHLD`와 자식 회수

자식 프로세스의 상태가 바뀌면 부모는 `SIGCHLD`를 받을 수 있습니다.

handler에서 자식 관리 자료구조를 직접 복잡하게 수정하기보다, 자식 상태가 변했다는 사실만 기록하고 일반 제어 흐름에서 실제 회수를 수행하는 편이 좋습니다.

```c
while ((pid = waitpid(-1, &status, WNOHANG)) > 0)
{
    record_child_exit(pid, status);
}
```

여러 자식의 상태 변화가 하나의 시그널 전달로 합쳐질 수 있으므로 `SIGCHLD`를 한 번 받았다고 `waitpid`를 한 번만 호출해서는 안 됩니다.

한 번 깨어났다면 `waitpid(..., WNOHANG)`가 더 이상 회수할 자식을 찾지 못할 때까지 반복합니다.

즉 `SIGCHLD`는 다음 의미에 가깝습니다.

```text
"적어도 하나의 자식 상태가 바뀌었을 수 있으니 다시 확인하라."
```

## 대화형 프로그램의 시그널 정책

대화형 부모 프로그램과 그 프로그램이 실행한 포그라운드 자식은 같은 시그널을 서로 다르게 처리해야 할 수 있습니다.

예를 들어 간단한 셸에서는 다음과 같은 정책을 사용할 수 있습니다.

```text
부모:
  SIGINT를 받으면 현재 입력이나 작업을 취소
  셸 프로세스 자체는 계속 실행

포그라운드 자식:
  exec 전에 SIGINT를 SIG_DFL로 복원
  사용자가 Ctrl-C를 누르면 기본 동작에 따라 종료
```

부모의 handler를 그대로 자식에게 물려주면 외부 명령까지 셸과 동일한 시그널 정책으로 실행될 수 있습니다.

따라서 자식은 `exec` 전에 외부 프로그램이 기대하는 기본 시그널 동작을 복원해야 할 수 있습니다.

완전한 job control은 여기서 더 나아가 다음 개념까지 포함합니다.

```text
process group
session
controlling terminal
tcsetpgrp
```

이 가이드에서는 하나의 포그라운드 작업을 실행하는 데 필요한 기본적인 시그널 경계까지만 다룹니다.

## timeout과 시간 관리

`alarm`을 사용하면 간단한 초 단위 timeout을 만들 수 있습니다.

```c
alarm(3);

/* 이벤트 대기 */

alarm(0);
```

다만 `alarm`은 프로세스당 하나의 alarm만 관리할 수 있다는 제약이 있습니다.

여러 deadline을 동시에 관리하거나 더 정밀한 시간이 필요하다면 다음 수단을 고려할 수 있습니다.

* `timer_create`
* `setitimer`
* `poll`이나 유사한 이벤트 대기 함수의 timeout
* 별도의 이벤트 루프 timer

`sleep`이나 `nanosleep` 같은 대기 함수 역시 시그널에 의해 중단될 수 있습니다.

`nanosleep`이 `EINTR`로 끝났다면 남은 시간을 이용해 다시 기다릴지, 현재 상태를 확인하고 중단할지 정책을 정해야 합니다.

테스트의 timeout은 프로그램이 시간을 정확히 처리한다는 사실을 증명하기 위한 기능이 아닙니다.

교착 상태나 무한 대기에 빠진 테스트가 전체 테스트 실행을 멈추지 않도록 만드는 **실패 경계**입니다.

## 멀티스레드 프로그램의 시그널 처리

멀티스레드 프로세스에서는 프로세스 대상으로 전달된 시그널을 어느 스레드가 처리하는지까지 고려해야 하므로 비동기 handler 기반 설계가 더 복잡해집니다.

흔히 사용하는 방법 중 하나는 시그널을 전용 스레드에서 동기적으로 처리하는 것입니다.

```text
1. 시작 스레드에서 관련 시그널을 block
2. worker thread 생성
3. worker들은 block된 mask를 상속
4. 전용 signal thread가 sigwait 또는 sigwaitinfo로 대기
5. 일반 pthread 코드에서 이벤트 처리
```

이 방식에서는 시그널을 처리하는 스레드가 일반적인 동기 제어 흐름 안에서 실행되므로 비동기 handler에 적용되는 제약을 크게 줄일 수 있습니다.

단, `sigwait` 계열 함수로 받을 시그널은 이를 처리하지 않는 일반 worker에서도 block되어 있어야 합니다.

따라서 worker를 생성한 뒤 뒤늦게 mask를 변경하기보다 **스레드를 만들기 전에 시그널 정책을 먼저 확정하는 것**이 중요합니다.

## 실습

[signal-loop](../../exercises/03-unix-programming/03-signal-loop/README.md)에서 다음 항목을 구현하고 검증합니다.

* `sigaction`을 이용한 `SIGUSR1`, `SIGTERM` handler 설치
* 설치와 정리 과정에서 관련 시그널 block
* self-pipe 구성과 쓰기 끝의 nonblocking 설정
* 파일 디스크립터의 close-on-exec 설정
* handler에서 `errno` 저장과 복원
* 일반 제어 흐름에서 출력과 종료 정책 처리
* `SIGUSR1`을 받은 뒤 계속 실행
* `SIGTERM`을 받은 뒤 handler와 FD를 정리하고 상태 0으로 종료
* 별도 프로세스에 실제 시그널을 전달하는 자동 테스트
* 프로그램이 준비되었다는 신호를 확인한 뒤에만 테스트가 시그널을 보내도록 동기화

테스트에서는 출력 메시지만 확인하지 않습니다.

다음 조건도 함께 검증합니다.

* 정해진 시간 안에 프로그램이 종료되는가?
* 예상하지 않은 stderr 출력이 없는가?
* handler가 아닌 시그널 기본 동작 때문에 비정상 종료하지 않는가?
* 종료 과정에서 파일 디스크립터가 정상적으로 정리되는가?

이 실습의 핵심은 시그널 handler 안에서 프로그램을 직접 제어하는 것이 아닙니다.

**비동기 문맥에서는 최소한의 사실만 안전하게 전달하고, 실제 정책과 자원 관리는 다시 일반적인 동기 제어 흐름으로 가져오는 것**이 목표입니다.

## 다음 단계

명령을 읽고 실행하는 프로그램에서는 lexer, parser, executor와 시그널 정책을 하나의 함수에 섞어서는 안 됩니다.

입력 문자열을 구조화하는 단계, 실행 계획을 만드는 단계, 프로세스를 실제로 생성하는 단계와 비동기 이벤트를 처리하는 단계가 분리되어야 각 계층의 계약과 실패 조건을 명확하게 유지할 수 있습니다.

[셸 파서와 실행기](04-shell-parser-executor.md)에서 이 처리 계층을 이어서 분리합니다.
