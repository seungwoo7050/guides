# int-vector

## 개요

`int-vector`는 삽입 순서를 보존하며 자동으로 성장하는 동적 정수 배열 library입니다. allocator injection을 통해 다음 growth의 실패를 재현할 수 있고, 실패 시 기존 buffer와 원소를 그대로 유지합니다.

## 불변식

```text
size <= capacity
capacity == 0  => data == NULL && size == 0
capacity > 0   => data != NULL
valid index    => 0 <= index < size
```

## 주요 기능

- 기본 allocator와 사용자 allocator 지원
- 초기 capacity 4, 이후 doubling 성장
- element count와 byte size의 독립 overflow 검사
- 범위 검사 뒤에만 `out_value`를 갱신하는 lookup
- 할당 실패 뒤 강한 상태 보장
- 반복 호출 가능한 destroy

## 빌드와 사용

```sh
make
```

static library는 `build/libint_vector.a`에 생성됩니다.

```c
struct int_vector values;
int item;

int_vector_init(&values, NULL);
int_vector_push(&values, 10);
int_vector_push(&values, 20);
if (int_vector_get(&values, 1, &item) == 0)
{
    printf("%d\n", item);
}
int_vector_destroy(&values);
```

## 검증

```sh
make test
make sanitize
```

테스트는 여러 차례의 growth, 삽입 순서, 첫·마지막 index, 범위 밖 lookup의 출력 보존, invalid shape, allocator 실패와 반복 destroy를 확인합니다.

## 설계 결정

새 capacity와 allocation byte 수를 상태 변경 전에 계산합니다. `resize`가 성공한 뒤에만 `data`와 `capacity`를 commit하고, 원소는 확보된 slot에 기록한 뒤 `size`를 증가시킵니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Vector ownership and allocator contract | `include/int_vector.h` |
| 2 | Empty-state initialization and shape invariant | `src/int_vector.c` |
| 3 | Overflow-safe capacity growth | `src/int_vector.c` |
| 4 | Bounds-checked lookup | `src/int_vector.c` |
| 5 | Repeatable destruction | `src/int_vector.c` |

## 범위와 제한

정수 push와 index lookup만 제공합니다. remove, insert, iterator, shrink, thread safety는 범위에 포함되지 않습니다. 초기화된 vector를 다시 초기화하려면 먼저 destroy해야 합니다.
