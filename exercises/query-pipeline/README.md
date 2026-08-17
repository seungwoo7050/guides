# Query Pipeline

## 개요

C++20 ranges와 concepts를 사용해 `Job` collection을 필터링하고 정렬하는 library입니다. 조회 결과는 원본 객체를 복사하지 않는 `std::reference_wrapper<const Job>` 목록이며, 원본 순서와 값은 변경하지 않습니다.

## 기능

- status, maximum duration, required tag의 독립적 조합
- ID 또는 duration 기준 정렬
- duration이 같은 경우 ID 기반 deterministic tie-breaker
- ascending/descending 지원
- `JobReference` range로 제한된 `summarize`

## 구조

- `include/query.hpp`: domain model, query contract, concept, summary API
- `src/query.cpp`: filter view materialization과 deterministic sorting
- `tests/query_tests.cpp`: 필터 조합, 정렬, 비소유 결과, source 보존 검증

## 빌드 및 테스트

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

## 주요 설계 결정

조회 결과는 `Job`을 소유하지 않습니다. 따라서 결과의 모든 참조는 입력 collection보다 짧게 사용해야 합니다. 정렬은 참조 목록에만 적용되어 원본 collection을 변경하지 않습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Query and non-owning result model | `include/query.hpp` |
| 2 | Constrained summary contract | `include/query.hpp` |
| 3 | Filter materialization | `src/query.cpp` |
| 4 | Deterministic result ordering | `src/query.cpp` |

## 범위와 한계

결과 수명은 caller가 소유한 입력에 종속됩니다. 병렬 실행, persistent index, locale-aware tag matching과 pagination은 포함하지 않습니다.
