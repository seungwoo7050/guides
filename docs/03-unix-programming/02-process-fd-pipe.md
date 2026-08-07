# 프로세스·파일 디스크립터·파이프: 복제된 상태 정리하기

Unix에서 새 프로그램을 실행하는 과정은 “새 프로세스를 한 번에 만든다”기보다 **현재 프로세스를 복제하고 복제본의 실행 이미지를 교체하는 것**에 가깝습니다. 그 사이에 파일 디스크립터를 바꾸면 리다이렉션과 파이프라인을 구성할 수 있습니다.

난점은 `fork`, `dup2`, `exec` 각각의 문법이 아닙니다. 어느 프로세스가 어느 descriptor를 소유하고, 중간 실패 뒤 이미 만든 자식과 파이프를 누가 정리하는지 끝까지 추적하는 일입니다.

## 프로그램 이미지와 프로세스

디스크의 실행 파일은 프로그램 이미지이고, 프로세스는 그것을 실행하는 인스턴스입니다. 프로세스는 대략 다음 상태를 가집니다.

- 코드, 전역 데이터, 힙과 스택으로 이루어진 주소 공간
- 레지스터와 실행 문맥
- 파일 디스크립터 테이블
- PID와 부모 PID
- 작업 디렉터리와 환경
- 사용자·그룹 정보
- 시그널 처리 상태

같은 실행 파일을 여러 번 실행해도 서로 다른 PID와 주소 공간을 가진 프로세스가 생깁니다.

## `fork`: 한 번 호출하고 두 실행 흐름으로 돌아오기

```c
pid_t pid = fork();

if (pid < 0)
{
    /* 실패: 원래 프로세스만 존재 */
}
else if (pid == 0)
{
    /* 자식 */
}
else
{
    /* 부모, pid는 자식 PID */
}
```

성공하면 부모와 자식이 `fork` 다음 문장부터 각각 실행합니다. 일반 메모리는 논리적으로 복제되므로 이후 변수 변경은 서로에게 보이지 않습니다. 현대 시스템이 copy-on-write로 실제 복사를 지연해도 프로그래머가 의존할 모델은 독립된 주소 공간입니다.

반면 파일 디스크립터 테이블의 각 항목은 같은 커널의 열린 파일 설명(open file description)을 가리킬 수 있습니다. 이 공유가 파일 offset, 파이프 EOF와 상태 flag에 영향을 줍니다.

## FD 번호와 열린 파일 설명은 다릅니다

```text
부모 fd 3 ─┐
            ├─ 열린 파일 설명: offset, status flags, 파일
자식 fd 3 ─┘
```

FD는 프로세스별 정수 인덱스입니다. `fork`, `dup`, `dup2`로 생긴 여러 FD가 같은 열린 파일 설명을 가리킬 수 있습니다.

```c
int fd = open("out.txt", O_WRONLY | O_CREAT | O_TRUNC, 0644);
int copy = dup(fd);

write(fd, "A", 1);
write(copy, "B", 1); /* 보통 같은 offset을 공유해 AB */
```

FD 번호가 같은지보다 어떤 열린 설명을 공유하는지가 중요합니다.

## `exec`: 현재 실행 이미지를 교체하기

```c
char *arguments[] = {"printf", "%s\n", "child", NULL};
execvp(arguments[0], arguments);
```

성공하면 현재 프로세스의 코드와 데이터가 새 프로그램으로 교체되며 호출로 돌아오지 않습니다. 반환했다면 실패입니다.

```c
execvp(arguments[0], arguments);
{
    int error_number = errno;

    dprintf(STDERR_FILENO, "%s: %s\n",
            arguments[0], strerror(error_number));
    _exit(error_number == ENOENT ? 127 : 126);
}
```

실제 async-signal-safety가 필요한 문맥이 아니라면 `dprintf` 대신 더 단순한 진단을 사용할 수 있습니다. 중요한 점은 다음입니다.

- `exec` 실패 전의 `errno`를 다른 호출 전에 저장합니다.
- 자식 전용 실패 경로는 `_exit`로 끝냅니다.
- `argv`는 마지막 널 포인터를 포함해야 합니다.

`exit`는 부모에서 복제된 stdio buffer를 flush하거나 `atexit` 함수를 다시 실행해 중복 효과를 만들 수 있습니다.

## `execvp`, `execve`와 환경

`execvp`는 명령 이름에 `/`가 없으면 현재 환경의 `PATH`를 검색하고 현재 환경을 새 프로그램에 전달합니다.

환경을 직접 통제하려면 `execve`를 사용할 수 있습니다.

```c
execve(path, arguments, environment);
```

`execve`는 PATH 검색을 자동으로 하지 않습니다. 환경은 `KEY=VALUE` 문자열로 이루어진 널 종료 포인터 배열입니다.

권한이 높은 프로그램은 사용자 제공 PATH와 환경을 그대로 신뢰해서는 안 됩니다. 대화형 셸에서는 사용자의 환경을 따르는 것이 기능일 수 있으므로 프로그램 목적에 맞는 경계를 정합니다.

## `waitpid`와 좀비

자식이 종료해도 부모가 상태를 회수하기 전까지 커널에 최소 정보가 남을 수 있습니다. 이를 좀비 상태라고 부릅니다.

```c
int status;
pid_t result;

do
{
    result = waitpid(pid, &status, 0);
}
while (result < 0 && errno == EINTR);
```

`status`는 일반 종료 코드 자체가 아닙니다. 매크로로 해석합니다.

```c
if (WIFEXITED(status))
{
    int code = WEXITSTATUS(status);
}
else if (WIFSIGNALED(status))
{
    int signal_number = WTERMSIG(status);
}
```

CLI 실행기는 시그널 종료를 `128 + signal_number` 형태로 변환할 수 있습니다. 이는 널리 쓰는 관례이지 `waitpid`가 직접 반환한 원시 상태가 아닙니다.

생성한 자식마다 누가 `waitpid`하는지 정해야 합니다. 실패한 자식도 회수 대상입니다.

## `dup2`와 리다이렉션

```c
int fd = open("out.txt", O_WRONLY | O_CREAT | O_TRUNC, 0644);
if (fd < 0)
{
    /* 오류 */
}
if (dup2(fd, STDOUT_FILENO) < 0)
{
    /* 오류 */
}
close(fd);
```

`dup2(oldfd, newfd)`는 `newfd`가 `oldfd`와 같은 열린 파일 설명을 가리키게 합니다. `newfd`가 열려 있었다면 원자적으로 교체합니다.

```text
> 파일   O_WRONLY | O_CREAT | O_TRUNC
>> 파일  O_WRONLY | O_CREAT | O_APPEND
< 파일   O_RDONLY, STDIN_FILENO에 dup2
```

외부 명령의 리다이렉션은 보통 자식에서 적용합니다. 부모에서 `dup2`하면 부모 프로그램 자체의 표준 입출력이 바뀝니다.

상태를 부모에서 바꿔야 하는 builtin에 리다이렉션을 적용한다면 원본 FD를 `dup`으로 저장하고 모든 경로에서 복구해야 합니다.

## `pipe`: 단방향 바이트 스트림

```c
int pipefd[2];
if (pipe(pipefd) < 0)
{
    /* 오류 */
}
```

```text
pipefd[1]에 write → 커널 버퍼 → pipefd[0]에서 read
```

파이프에는 애플리케이션 메시지 경계가 없습니다. 가장 중요한 EOF 규칙은 다음입니다.

> 읽기 쪽이 EOF를 받으려면 그 파이프를 가리키는 모든 쓰기 FD가 닫혀야 합니다.

실제 writer 자식이 종료했어도 부모나 다른 자식이 쓰기 끝 복제본을 열어 두면 reader는 EOF를 받지 못합니다.

## 두 명령 파이프라인

```text
왼쪽 명령 stdout → 파이프 → 오른쪽 명령 stdin
```

기본 안무:

```text
pipe 생성

왼쪽 자식:
  dup2(pipe write, STDOUT_FILENO)
  pipe read/write 원본 모두 close
  exec

오른쪽 자식:
  dup2(pipe read, STDIN_FILENO)
  pipe read/write 원본 모두 close
  exec

부모:
  pipe read/write 모두 close
  왼쪽 wait
  오른쪽 wait
```

각 프로세스의 소유권을 표로 먼저 작성하면 누락을 줄일 수 있습니다.

| 프로세스 | read end | write end |
|---|---|---|
| 왼쪽 자식 | 닫음 | stdout으로 복제한 뒤 원본 닫음 |
| 오른쪽 자식 | stdin으로 복제한 뒤 원본 닫음 | 닫음 |
| 부모 | 닫음 | 닫음 |

`dup2` 뒤 원래 파이프 FD를 닫아도 표준 입력·출력의 복제본은 유지됩니다.

## 두 자식을 모두 시작한 뒤 기다립니다

잘못된 순서:

```text
왼쪽 생성
왼쪽 종료까지 wait
오른쪽 생성
```

왼쪽 출력이 파이프 용량을 넘으면 오른쪽 reader가 아직 없어서 writer가 막힙니다. 부모는 writer가 끝나기를 기다리므로 교착합니다.

올바른 기본 순서:

```text
파이프 생성
왼쪽 생성
오른쪽 생성
부모의 파이프 끝 닫기
두 자식 wait
```

작은 출력은 커널 버퍼에 전부 들어가 잘못된 순서도 통과할 수 있습니다. 파이프 용량보다 큰 데이터로 테스트해야 합니다.

## N단 파이프라인으로 확장하기

`N`개 명령에는 일반적으로 `N - 1`개의 연결이 필요합니다. 모든 파이프를 먼저 만들 수도 있고 이전 read end만 유지하며 한 단계씩 만들 수도 있습니다.

순차 생성 방식의 핵심 상태:

```text
previous_read  이전 명령의 출력이 들어오는 FD, 첫 명령에는 없음
current_pipe   마지막 명령이 아니라면 새로 생성
```

각 명령 자식은 다음 순서로 준비합니다.

1. `previous_read`가 있으면 stdin으로 연결합니다.
2. 마지막 명령이 아니면 현재 pipe write end를 stdout으로 연결합니다.
3. 명시적 리다이렉션을 문법이 정한 순서로 적용합니다.
4. 상속받은 불필요한 FD를 모두 닫습니다.
5. `exec`합니다.

부모는 다음 단계에 필요 없는 FD를 즉시 닫아 EOF 문제와 열린 FD 수를 줄입니다.

## 파이프와 리다이렉션의 우선순위

```text
producer > out.txt | consumer
```

명시적 리다이렉션이 파이프보다 우선하는 문법이라면 자식에서 먼저 파이프 stdout을 연결하고 뒤에 파일 리다이렉션을 적용합니다. 마지막 `dup2`가 최종 목적지를 결정합니다.

이 규칙은 파서가 리다이렉션을 `argv` 문자열이 아니라 별도 실행 계획으로 전달해야 하는 이유입니다.

## 자식의 실패는 부모 메모리에 기록되지 않습니다

자식이 부모의 일반 변수에 오류를 써도 `fork` 뒤 주소 공간은 분리되어 있어 부모에게 전달되지 않습니다.

단순 실행기는 다음 채널을 사용합니다.

- 자식 `stderr`: 사람이 읽는 진단
- 자식 종료 상태: 성공·실패 분류
- 필요하면 별도 pipe: `exec` 전 상세 오류 번호 전달

복잡한 오류 객체가 필요하면 명시적인 IPC를 설계해야 합니다.

## 생성 중간 실패

두 번째 `fork`가 실패하면 첫 번째 자식은 이미 실행 중일 수 있습니다. “함수 실패”가 “아무 외부 효과도 없음”을 뜻하지 않습니다.

부모의 정리 순서 예:

```text
새 자식 생성을 중단
→ 부모가 가진 모든 pipe 끝 close
→ 이미 만든 자식에 필요한 종료 정책 적용
→ 생성된 자식 모두 wait
→ 임시 배열과 계획 객체 해제
→ 출력 매개변수를 변경하지 않고 오류 반환
```

파이프 FD 배열을 `-1`로 초기화하면 부분 생성 정리가 단순해집니다.

```c
if (pipefd[0] >= 0)
{
    close(pipefd[0]);
    pipefd[0] = -1;
}
```

자식에서는 부모용 정리 함수로 돌아가지 않고, 상속된 불필요한 FD를 닫은 뒤 `_exit`하는 짧은 오류 경로가 필요합니다.

## `waitpid` 실패와 여러 자식 회수

한 자식의 wait가 실패했다고 나머지 자식을 버리면 안 됩니다. `EINTR`은 재시도하고, 회수 가능한 자식은 계속 회수해 좀비를 남기지 않습니다.

공개 함수가 마지막 명령 상태를 결과로 사용하더라도 왼쪽 자식도 반드시 기다립니다.

```text
함수 반환값  파이프라인을 준비·회수하는 API 자체의 성공/실패
out_status    마지막 명령의 shell-style 상태
```

이 두 채널을 분리하면 “명령이 상태 1로 정상 종료”와 “부모가 fork/wait에 실패”를 구분할 수 있습니다.

## FD 누수와 멈춤 진단

파이프라인이 멈추면 다음을 순서대로 확인합니다.

1. 누가 쓰기 끝을 아직 들고 있습니까?
2. 부모와 두 자식이 불필요한 끝을 모두 닫았습니까?
3. reader가 어떤 입력 종료를 기다리고 있습니까?
4. 부모가 자식을 기다리기 전에 데이터를 읽거나 써야 합니까?
5. writer가 파이프 용량 때문에 막혔는데 reader가 아직 시작되지 않았습니까?

FD 누수는 짧은 프로그램이 종료할 때 가려질 수 있습니다. 같은 부모 프로세스에서 파이프라인을 반복하고 열린 descriptor 수가 계속 증가하지 않는지 검사합니다.

Linux에서는 `/proc/self/fd`, macOS에서는 `fcntl` 기반 탐색이나 `lsof` 같은 도구를 보조로 사용할 수 있습니다. 플랫폼 전용 검사는 조건부로 둡니다.

## 큰 입력과 timeout으로 교착을 검출합니다

연습 테스트는 4 MiB를 생성하고 소비하는 두 helper를 연결합니다.

```text
emit-bytes 4194304 | expect-bytes 4194304
```

검사는 다음을 동시에 확인합니다.

- 두 자식을 wait 전에 모두 생성했습니다.
- 부모가 파이프 쓰기 끝을 닫았습니다.
- 부분 읽기·쓰기를 반복합니다.
- 일정 시간 안에 종료합니다.

timeout은 올바른 결과의 증명이 아니라 “영원히 기다리지 않게 하는 실패 경계”입니다. 느린 환경에서도 정상 작업이 끝날 여유를 둡니다.

## 실습

[command-pipeline](../../exercises/03-unix-programming/02-command-pipeline/README.md)에서 다음을 구현합니다.

- 입력 포인터와 `argv[0]` 검증
- 파이프 생성과 두 자식 생성
- 자식의 stdin/stdout 연결
- 부모와 자식의 모든 미사용 FD 닫기
- exec 실패의 126·127 상태
- `EINTR`를 고려한 `waitpid`
- signal 종료를 `128 + signal`로 변환
- 마지막 명령 상태만 `out_status`에 commit
- 중간 실패 뒤 이미 만든 자식 회수
- 4 MiB 데이터로 순차 wait 교착 검출
- 반복 실행과 FD 정리

완료 뒤 부모의 쓰기 끝 close 또는 “두 번째 자식을 만들기 전 wait”를 일부러 넣어 테스트가 timeout으로 결함을 드러내는지 확인합니다.

## 다음 단계

프로세스는 `SIGCHLD`, `SIGINT`, `SIGTERM` 같은 비동기 사건도 받습니다. handler와 일반 제어 흐름을 분리하는 방법은 [시그널과 사건 전달](03-signals-events.md)에서 다룹니다.
