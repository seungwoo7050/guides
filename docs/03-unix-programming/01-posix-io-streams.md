# POSIX I/O와 스트림 상태: 부분 읽기·EOF·레코드

파일 디스크립터 기반 I/O는 한 번의 호출이 요청한 양을 모두 처리한다고 약속하지 않습니다. 커널은 현재 처리할 수 있는 바이트 수를 반환하지만, 애플리케이션은 한 줄·한 프레임·한 레코드 같은 논리적 단위를 원할 수 있습니다. 두 경계가 다르면 호출 사이에 상태를 보존해야 합니다.

이 장에서는 `read`와 `write`의 부분 성공, `EINTR`, EOF, 내부 버퍼, 출력 소유권과 실패 뒤 상태를 하나의 레코드 reader로 연결합니다.

## ISO C와 POSIX의 경계

ISO C 표준 라이브러리는 `FILE *`, `fopen`, `fread`, `fprintf` 같은 스트림 인터페이스를 제공합니다. 파일 디스크립터와 다음 함수는 POSIX 인터페이스입니다.

```c
#define _POSIX_C_SOURCE 200809L

#include <fcntl.h>
#include <sys/types.h>
#include <unistd.h>
```

```text
open, read, write, close
pipe, dup, fork, exec, poll ...
```

기능 테스트 매크로는 관련 시스템 헤더보다 먼저 정의하거나 빌드 옵션으로 번역 단위 전체에 적용합니다.

```sh
cc -D_POSIX_C_SOURCE=200809L ...
```

Windows 네이티브 API는 같은 계약을 제공하지 않습니다. 이 장의 코드는 POSIX.1-2008 계열 환경을 대상으로 합니다.

## 파일 디스크립터 모델

파일 디스크립터(FD)는 프로세스 안의 작은 정수 인덱스입니다.

```text
0  표준 입력
1  표준 출력
2  표준 오류
```

FD는 파일의 영구 식별자가 아닙니다. 프로세스의 descriptor table 항목이며 파일, 파이프, 소켓, 터미널 같은 커널 객체를 가리킵니다.

```c
int fd = open("input.txt", O_RDONLY);
```

성공하면 0 이상의 FD, 실패하면 `-1`을 반환합니다. `0`, `1`, `2`도 닫혀 있었다면 새 `open` 결과로 재사용될 수 있으므로 “성공한 FD는 항상 3 이상”이라고 가정하지 않습니다.

## `open`과 `close`의 소유권

```c
int fd = open(path, O_RDONLY);
if (fd < 0)
{
    /* 실패 직후 errno 확인 */
}
```

파일을 생성하는 플래그를 사용하면 모드 인자가 필요합니다.

```c
int fd = open(
    path,
    O_WRONLY | O_CREAT | O_TRUNC,
    0644
);
```

`close(fd)`는 현재 프로세스의 descriptor table 항목을 닫습니다. 함수가 전달받은 FD를 닫을지는 타입이 아니라 계약이 결정합니다.

```text
소유한 FD    함수가 정상·오류 경로에서 닫을 책임이 있음
빌린 FD      함수가 사용하는 동안만 유효하며 임의로 닫지 않음
이전한 FD    성공 뒤 새 소유자가 닫을 책임을 가짐
```

닫힌 번호는 곧 다른 자원에 재사용될 수 있습니다. `close`를 시도한 뒤 같은 숫자를 무조건 다시 닫는 복구는 다른 자원을 닫을 위험이 있으므로 소유 상태를 명확히 끝냅니다.

## `read`의 세 결과

```c
ssize_t count = read(fd, buffer, capacity);
```

| 결과 | 의미 |
|---|---|
| `count > 0` | `buffer[0..count)`에 실제 바이트가 있습니다. |
| `count == 0` | 양수 크기의 읽기에서 EOF를 관찰했습니다. |
| `count == -1` | 오류입니다. 직후 `errno`를 확인합니다. |

요청한 `capacity`보다 적은 양을 읽어도 오류가 아닙니다. 파이프, 터미널, 소켓은 물론 일반 파일에서도 짧은 읽기를 허용해야 합니다.

```c
ssize_t count = read(fd, buffer, sizeof buffer);
if (count > 0)
{
    consume(buffer, (size_t)count);
}
```

유효한 데이터 길이는 반환값으로만 판단합니다.

## `read`는 문자열을 만들지 않습니다

커널은 NUL 종료 문자를 붙이지 않습니다.

```c
char buffer[1024];
ssize_t count = read(fd, buffer, sizeof buffer);
```

`count > 0`이어도 `buffer`가 C 문자열이라는 보장은 없습니다. 문자열 함수가 필요하면 한 바이트 여유를 두고 직접 종료해야 합니다.

```c
char buffer[1025];
ssize_t count = read(fd, buffer, 1024);

if (count > 0)
{
    buffer[count] = '\0';
}
```

입력 바이트 안에 NUL이 포함될 수 있다면 `strlen`을 데이터 길이로 사용하면 안 됩니다. 바이트 배열과 길이를 함께 전달합니다.

## 부분 읽기와 바이트 스트림

짧은 양수 읽기는 다음 이유로 발생할 수 있습니다.

- 파이프나 터미널에 현재 일부 데이터만 도착했습니다.
- 시그널 전까지 일부 바이트가 처리됐습니다.
- 장치나 파일 시스템이 요청보다 적게 반환했습니다.
- 소켓 상대가 데이터를 여러 번 나누어 보냈습니다.

“요청보다 적으므로 EOF”라고 판단하면 데이터를 조기에 끊습니다. EOF는 양수 크기로 호출한 `read`가 `0`을 반환했을 때 관찰합니다.

바이트 스트림에는 애플리케이션 메시지 경계가 없습니다.

```text
쓰기 호출: "abc", "def"
읽기 결과: "ab", "cdef"가 될 수도 있음
```

쓰기 호출 횟수와 읽기 호출 횟수를 대응시키지 않습니다.

## `write`와 부분 쓰기

`write`도 양수이지만 요청보다 작은 값을 반환할 수 있습니다. 전체를 보내야 하면 반복합니다.

```c
int write_all(int fd, const void *data, size_t length)
{
    const unsigned char *cursor = data;

    while (length > 0)
    {
        size_t request = length;
        ssize_t count;

        if (request > (size_t)SSIZE_MAX)
        {
            request = (size_t)SSIZE_MAX;
        }
        count = write(fd, cursor, request);
        if (count > 0)
        {
            cursor += (size_t)count;
            length -= (size_t)count;
        }
        else if (count < 0 && errno == EINTR)
        {
            continue;
        }
        else
        {
            return -1;
        }
    }
    return 0;
}
```

한 번의 호출이 표현할 수 있는 양을 넘지 않도록 큰 길이는 청크로 나눕니다. `write`가 `0`을 반환하는 예상 밖의 상황도 무한 반복하지 않습니다.

파이프나 소켓에서 읽는 쪽이 사라지면 `SIGPIPE` 또는 `EPIPE`가 발생할 수 있습니다. 시그널 정책과 오류 반환 중 어느 경로로 다룰지 프로그램 전체에서 정합니다.

## `errno`와 `EINTR`

`errno`는 함수가 실패를 반환한 직후에만 해석합니다. 성공한 함수는 이전 오류 값을 0으로 지워 줄 의무가 없습니다.

```c
ssize_t count;

do
{
    count = read(fd, buffer, capacity);
}
while (count < 0 && errno == EINTR);
```

시그널 때문에 데이터 전송 전에 중단되면 `EINTR`이 올 수 있습니다. 단순 블로킹 reader는 보통 재시도합니다. 그러나 종료 요청을 즉시 관찰해야 하거나 deadline이 있는 호출은 무조건 같은 인자로 재시도하면 안 됩니다. 남은 시간과 프로그램 상태를 다시 계산해야 합니다.

## 청크 경계와 레코드 경계

입력이 다음과 같다고 가정합니다.

```text
alpha\nbeta\ngamma
```

실제 `read` 결과는 다음처럼 나뉠 수 있습니다.

```text
[alp] [ha\nbeta\n] [gam] [ma]
```

한 레코드는 여러 읽기에 걸칠 수 있고 한 읽기 안에 여러 레코드가 들어올 수 있습니다. 따라서 “`read` 한 번 결과를 레코드 하나로 반환”하는 구현은 계약을 지키지 못합니다.

## EOF는 레코드 구분자와 다릅니다

newline을 결과에서 제거하는 reader라면 다음을 구분해야 합니다.

```text
빈 스트림   → 즉시 EOF
"\n"        → 빈 레코드 하나, 그 다음 EOF
"\n\n"      → 빈 레코드 두 개, 그 다음 EOF
"last"     → "last" 한 개, 그 다음 EOF
"last\n"   → "last" 한 개, 가짜 빈 레코드 없이 EOF
```

EOF를 빈 문자열로 표현하면 실제 빈 레코드와 구분할 수 없습니다. 반환 상태를 별도로 둡니다.

```text
1   레코드 반환
0   EOF이며 남은 레코드 없음
-1  잘못된 인자, I/O 또는 메모리 오류
```

## 호출 사이의 상태

첫 호출이 `alpha`만 반환했더라도 이미 읽은 `beta` 일부를 버리면 안 됩니다. 함수 지역 배열은 반환과 함께 수명이 끝나므로 상태 객체가 필요합니다.

```c
struct record_reader
{
    int fd;
    char *pending;
    size_t length;
    size_t capacity;
    int eof;
    int failed;
    struct record_reader_allocator allocator;
};
```

핵심 불변식:

```text
length <= capacity
pending[0..length)는 아직 반환하지 않은 바이트
eof이면 더 이상 read를 호출하지 않음
failed이면 이후 next도 -1
reader는 fd를 빌리며 destroy에서 닫지 않음
destroy 뒤 다시 사용하려면 init으로 새 수명을 시작함
```

명시적인 reader 객체를 사용하면 여러 FD의 상태를 독립적으로 유지하고, 조기 중단 때 내부 버퍼를 확실히 해제할 수 있습니다.

## 내부 탐색 위치와 반복 비용

더 큰 구현에서는 다음 위치를 별도로 추적할 수 있습니다.

```text
0        begin        scan          end       capacity
| 소비됨 | 반환 후보 | 이미 검색함 | 미검색 데이터 | 빈 공간 |
```

불변식:

```text
begin <= scan <= end <= capacity
```

- `begin`: 다음 레코드 후보의 시작입니다.
- `scan`: newline이 없음을 이미 확인한 끝입니다.
- `end`: 저장된 실제 바이트의 끝입니다.
- `capacity`: 할당 전체 크기입니다.

매 호출마다 처음부터 newline을 다시 찾으면 긴 레코드에서 같은 바이트를 반복 검사할 수 있습니다. 작은 연습은 `begin == 0`을 유지하며 소비 뒤 `memmove`하지만, 규모가 커지면 시작·검색 위치를 분리할 수 있습니다.

## 버퍼 압축과 성장

앞부분을 소비했고 뒤쪽 공간이 부족하면 남은 데이터를 앞으로 옮깁니다.

```c
memmove(buffer, buffer + consumed, remaining);
```

범위가 겹치므로 `memcpy`가 아니라 `memmove`를 사용합니다.

그래도 부족하면 용량을 기하급수적으로 늘립니다.

```text
필요 길이 덧셈 overflow 검사
→ 새 용량 계산
→ realloc 결과를 임시 포인터에 받음
→ 성공한 뒤 data와 capacity 교체
```

성장 실패 시 기존 포인터와 이미 읽은 데이터가 유효해야 합니다. `realloc` 결과를 원래 포인터에 직접 대입하지 않습니다.

## 공개 결과와 소유권

이번 연습의 API는 레코드마다 새 NUL 종료 배열을 할당해 호출자에게 넘깁니다.

```c
int record_reader_next(
    struct record_reader *reader,
    char **out_record,
    size_t *out_length
);
```

```text
반환 1   *out_record와 *out_length를 새 결과로 commit
반환 0   출력 매개변수 변경 없음
반환 -1  출력 매개변수 변경 없음
```

성공한 호출 뒤 호출자가 `free(*out_record)`합니다. 문자열 끝의 NUL은 편의를 위한 추가 바이트이고, 실제 데이터 길이는 `*out_length`입니다. 입력에 포함된 NUL도 길이와 `memcmp`를 사용하면 보존할 수 있습니다.

## 결과를 만든 뒤 소비합니다

newline 위치를 찾았다고 pending 데이터를 먼저 제거하면 결과 배열 할당 실패 때 레코드를 잃습니다. 안전한 순서는 다음과 같습니다.

```text
경계 찾기
→ 결과 길이 overflow 검사
→ 결과 배열 할당
→ 데이터 복사와 NUL 종료
→ pending에서 소비 범위 제거
→ 출력 매개변수 commit
```

이 순서는 결과 생성 실패 전에 내부 레코드를 보존합니다. 다만 실제 `read`로 커널에서 가져온 바이트까지 호출 전 위치로 되돌릴 수 있는 것은 아닙니다.

## 오류와 되돌리기의 한계

한 호출에서 여러 번 `read`한 뒤 내부 버퍼 성장에 실패할 수 있습니다. 이미 성공한 `read`는 파일 오프셋을 전진시켰고, 파이프나 터미널은 일반적으로 되감을 수 없습니다.

따라서 다음과 같은 강한 보장을 약속하면 안 됩니다.

```text
실패하면 커널 스트림과 reader가 모두 호출 전 상태로 돌아감  ← 일반적으로 불가능
```

이번 연습은 내부 성장 또는 I/O 오류 뒤 reader를 terminal failed 상태로 만듭니다.

```text
내부 메모리 누수 없음
출력 매개변수 보존
다른 reader에는 영향 없음
이 reader의 이후 next는 계속 -1
호출자가 빌려준 fd는 닫지 않음
```

실패 뒤 재사용을 지원하려면 읽은 바이트와 오류 원인을 보존하는 더 복잡한 상태 머신이 필요합니다.

## 여러 reader와 FD 번호 재사용

FD마다 reader 객체를 하나씩 만들면 상태 격리가 명확합니다.

```c
struct record_reader left;
struct record_reader right;

record_reader_init(&left, left_fd, NULL);
record_reader_init(&right, right_fd, NULL);
```

호출을 번갈아 해도 각 pending 데이터가 섞이지 않아야 합니다.

FD 정수만 key로 쓰는 전역 레지스트리는 다음 문제를 가집니다.

- close 뒤 같은 번호가 다른 자원에 재사용됩니다.
- 호출자가 중간에 읽기를 포기할 때 정리 진입점이 부족합니다.
- 전역 상태의 스레드 안전성이 필요합니다.
- `dup`된 FD가 같은 열린 파일 설명을 공유한다는 관계를 알기 어렵습니다.

명시적인 reader가 가능한 API에서는 전역 정적 상태보다 수명과 테스트가 단순합니다.

## 비보장 범위

이번 단순 블로킹 reader는 다음을 지원하지 않습니다.

- 같은 FD를 reader 밖에서 동시에 `read`
- 활성 reader가 있는 동안 외부 `lseek`
- `dup`된 FD 두 개를 독립 reader로 섞어 사용
- FD close 후 번호 재사용 자동 감지
- `O_NONBLOCK`의 `EAGAIN`을 나중에 계속할 상태로 처리
- 같은 reader에 대한 여러 스레드의 동시 호출

지원하지 않는 조건을 정상 테스트에 몰래 포함하지 않고 문서에서 경계를 고정합니다.

## 파이프로 부분 읽기를 검증합니다

일반 파일은 환경에 따라 큰 덩어리로 읽혀 결함을 가릴 수 있습니다. 파이프를 사용하면 조각난 입력과 EOF 시점을 제어할 수 있습니다.

```text
쓰기: "ab"
쓰기: "c\nxy"
쓰기 끝 close
읽기: 여러 read를 거쳐 "abc", "xy" 반환
```

모든 파이프 쓰기 끝이 닫혀야 reader가 EOF를 받습니다. 이 규칙은 다음 장의 프로세스·파이프 설계에서 더 중요해집니다.

## 실습

[record-stream](../../exercises/03-unix-programming/01-record-stream/README.md)에서 다음을 구현하고 검증합니다.

- 한 read보다 긴 레코드
- 한 read에 여러 레코드
- 연속 newline의 빈 레코드
- newline 없는 마지막 레코드
- newline으로 끝나는 입력의 가짜 빈 레코드 방지
- 반복 EOF 호출과 출력값 보존
- 내부 버퍼 성장과 할당 실패 주입
- 오류 뒤 terminal failed 상태
- 두 reader의 교차 호출과 상태 격리
- 포함된 NUL과 명시적 길이
- destroy와 FD 소유권 분리

## 다음 단계

`fork`로 descriptor table이 복제되면 쓰지 않는 파이프 끝도 EOF에 영향을 줍니다. [프로세스·파일 디스크립터·파이프](02-process-fd-pipe.md)에서 이어집니다.
