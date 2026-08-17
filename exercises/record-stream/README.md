# record-stream

`record-stream`은 file descriptor에서 newline으로 구분된 record를 한 개씩 반환하는 stateful C library다. 한 번의 `read`와 논리 record 경계가 일치하지 않는 상황을 내부 pending buffer로 처리하며, 포함된 NUL byte도 길이 기반 데이터로 보존한다.

## Features

- fragmented input과 여러 청크에 걸친 긴 record 처리
- 연속 newline을 길이 0인 record로 반환
- newline 없이 끝난 마지막 비어 있지 않은 record 반환
- embedded NUL을 포함한 binary-safe output
- 반복 가능한 EOF 상태와 terminal failure 상태 구분
- allocator injection을 통한 buffer 성장 실패 검증
- reader가 file descriptor를 닫지 않는 borrowed-FD ownership

## Architecture

`struct record_reader`가 pending bytes, EOF 여부, terminal failure 여부를 소유한다. `record_reader_next`는 먼저 buffered delimiter를 찾고, 없으면 blocking `read`를 반복한다. record output allocation이 성공한 뒤에만 pending bytes를 소비하므로 output 생성 실패가 reader state를 부분적으로 변경하지 않는다.

## Build

```sh
make
```

정적 library는 `build/librecord_stream.a`에 생성된다.

## Usage

```c
struct record_reader reader;
char *record;
size_t length;

record_reader_init(&reader, fd, NULL);
while (record_reader_next(&reader, &record, &length) == 1)
{
    consume(record, length);
    free(record);
}
record_reader_destroy(&reader);
```

반환값은 record를 반환한 경우 `1`, EOF이며 남은 record가 없는 경우 `0`, 잘못된 인자·I/O·memory failure인 경우 `-1`이다. `0` 또는 `-1`에서는 output parameters를 변경하지 않는다.

## Verification

```sh
make test
make sanitize
```

검사는 fragmented records, 빈 record, trailing newline, newline 없는 마지막 record, embedded NUL, 두 reader의 독립성, 반복 EOF, allocator failure, invalid arguments, borrowed FD lifetime을 확인한다.

## Design Decisions

- `fd`는 caller가 소유한다. `record_reader_destroy`는 내부 buffer만 해제한다.
- internal allocation failure 뒤 reader는 terminal failure 상태가 된다. 불완전한 buffered input을 재시도 가능한 상태처럼 노출하지 않는다.
- 반환 record는 항상 별도 allocation이며 caller가 `free`한다.
- delimiter는 byte `\n` 하나로 고정한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Reader ownership contract | `include/record_stream.h` |
| 2 | Failure-atomic pending-buffer growth | `src/record_stream.c` |
| 3 | Delimiter discovery | `src/record_stream.c` |
| 4 | Record extraction and state commit | `src/record_stream.c` |
| 5 | Read/EOF/error state machine | `src/record_stream.c` |
| 6 | Borrowed-FD teardown | `src/record_stream.c` |

## Scope and Limitations

이 library는 blocking file descriptor와 newline delimiter만 지원한다. non-blocking retry policy, configurable delimiters, encoding interpretation, automatic FD closure는 범위에 포함하지 않는다.
