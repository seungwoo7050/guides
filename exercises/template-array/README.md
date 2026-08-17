# Template Array

## 개요

C++98로 작성한 고정 길이 generic array입니다. heap storage의 깊은 복사, mutable/const iterator, checked access와 iterator 기반 `apply` algorithm을 제공합니다.

## 기능

- 유효한 empty array
- 고정 길이 heap storage
- 깊은 복사와 copy-and-swap assignment
- mutable/const `operator[]`, `at`, iterator
- container에 종속되지 않는 `apply`
- const 수정과 비-iterator 입력을 거부하는 compile-failure tests

## 빌드, 실행 및 테스트

```sh
make
./demo
make test
```

`make test`는 runtime tests와 의도적으로 컴파일되지 않아야 하는 API misuse tests를 모두 실행합니다.

## 주요 설계 결정

복사 생성 중 원소 대입이 실패하면 새 배열을 정리하고 예외를 다시 전달합니다. 대입은 완성된 복사본과 `swap`하므로 기존 값이 보존됩니다. 빈 배열은 `begin() == end()`인 유효 상태입니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Fixed storage model | `include/Array.hpp` |
| 2 | Deep-copy transaction | `include/Array.hpp` |
| 3 | Mutable and const range contract | `include/Array.hpp` |
| 4 | Iterator-based apply algorithm | `include/Array.hpp` |
| 5 | Public API composition demo | `examples/demo.cpp` |

## 범위와 한계

길이는 construction 이후 변경되지 않습니다. allocator customization, move semantics, initializer list와 bounds checking이 없는 `operator[]`의 대체 정책은 포함하지 않습니다.
