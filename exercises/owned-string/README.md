# owned-string

## 개요

`owned-string`은 자체 buffer를 소유하며 append에 따라 성장하는 C string container입니다. allocator를 주입할 수 있어 할당 실패를 결정적으로 시험할 수 있고, 현재 문자열 전체나 내부 suffix를 다시 append하는 alias 입력도 지원합니다.

## 불변식

```text
empty state:
  data == NULL
  length == 0
  capacity == 0

allocated state:
  data != NULL
  length < capacity
  data[length] == '\0'
```

## 주요 기능

- 기본 `realloc`/`free` allocator와 사용자 allocator 지원
- doubling 기반 capacity 성장과 `SIZE_MAX` overflow 검사
- self-append 및 내부 suffix append
- 성장 실패 시 pointer, 내용, length, capacity 보존
- 반복 호출 가능한 `owned_string_destroy`

## 빌드와 사용

```sh
make
```

생성되는 static library는 `build/libowned_string.a`입니다. 공개 API는 `include/owned_string.h`에 있습니다.

```c
struct owned_string value;

owned_string_init(&value, NULL);
if (owned_string_append(&value, "hello") == 0 &&
    owned_string_append(&value, " world") == 0)
{
    puts(value.data);
}
owned_string_destroy(&value);
```

## 검증

```sh
make test
make sanitize
```

테스트는 기본 allocator, 빈 append, 여러 번의 성장, 전체 self-append, 내부 suffix alias, 잘못된 object shape, allocator 실패와 반복 destroy를 확인합니다.

## 설계 결정

alias source가 현재 buffer 안에 있으면 원래 pointer 대신 offset을 기억합니다. `resize`가 buffer를 옮긴 뒤 새 base address에 offset을 적용하므로 dangling pointer를 사용하지 않습니다. 공개 상태는 할당이 성공한 뒤에만 갱신됩니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Ownership and allocator contract | `include/owned_string.h` |
| 2 | Empty-state initialization and shape invariant | `src/owned_string.c` |
| 3 | Alias-safe capacity planning | `src/owned_string.c` |
| 4 | Failure-atomic append commit | `src/owned_string.c` |
| 5 | Repeatable destruction | `src/owned_string.c` |

## 범위와 제한

container는 NUL 종료 byte string만 저장합니다. 임의 binary payload, insert/erase, shrink-to-fit, thread safety는 제공하지 않습니다. 초기화된 object를 다시 초기화하려면 먼저 destroy해야 합니다.
