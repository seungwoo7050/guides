# Mini Vector

## 개요

C++98 allocator를 사용해 raw storage와 constructed object의 수명을 분리한 동적 배열입니다. 깊은 복사, checked access, iterator, capacity growth와 강한 예외 보장을 제공합니다.

## 기능

- `size`, `capacity`, `empty`
- mutable/const `operator[]`, `at`
- 반열린 pointer iterator 범위
- `reserve`, `push_back`, `clear`
- copy construction과 copy-and-swap assignment
- 재할당 또는 마지막 원소 복사 실패 시 원래 상태 보존
- self-aliasing `push_back(vector[0])` 지원

## 빌드, 실행 및 테스트

```sh
make
./demo
make test
```

## 주요 설계 결정

새 storage에서 모든 원소 생성이 성공하기 전까지 기존 storage를 파괴하지 않습니다. 실패 시 새 영역에서 생성이 끝난 원소만 역순으로 파괴하므로 `size`, `capacity`, 값과 live object 수가 유지됩니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Storage and size invariants | `include/MiniVector.hpp` |
| 2 | Copy and destruction lifecycle | `include/MiniVector.hpp` |
| 3 | Checked access and iterators | `include/MiniVector.hpp` |
| 4 | Transactional reserve | `include/MiniVector.hpp` |
| 5 | Alias-safe push transaction | `include/MiniVector.hpp` |
| 6 | Capacity transition demo | `examples/demo.cpp` |

## 범위와 한계

`erase`, `insert`, allocator propagation, custom growth policy, move semantics과 C++11 이후 allocator traits는 제공하지 않습니다. 이 구현은 C++98 value semantics와 exception safety에 범위를 제한합니다.
