# Task Model

## 개요

`TaskId`, `Priority`, `Task`로 작업 도메인의 입력 검증과 불변식을 표현하는 C++20 library입니다. 원시 정수와 문자열을 그대로 전달하지 않고, 파싱된 값과 유효한 객체만 공개 API를 통과하게 합니다.

## 기능

- `TaskId`의 명시적 생성과 전체 문자열 기반 파싱
- `low`, `normal`, `high`로 제한된 `Priority`
- 빈 제목을 허용하지 않는 `Task`
- `#<id> [<priority>] <title>` 형식의 안정적인 직렬화

## 구조

- `include/task.hpp`: 공개 domain model과 변환 계약
- `src/task.cpp`: 파싱, 불변식 검증, 직렬화
- `tests/task_tests.cpp`: 타입 특성, 경계 입력, 예외 계약 검증

## 빌드 및 테스트

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

## 주요 설계 결정

`TaskId::parse`는 입력 일부만 숫자인 경우를 허용하지 않습니다. `Task`는 생성 시점에 제목 불변식을 확립하므로 이후 코드가 빈 제목을 반복 검사할 필요가 없습니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Domain value model | `include/task.hpp` |
| 2 | Total identifier parsing | `src/task.cpp` |
| 2-1 | Closed priority conversion | `src/task.cpp` |
| 3 | Task invariant | `src/task.cpp` |
| 4 | Stable serialization | `src/task.cpp` |

## 범위와 한계

이 library는 메모리 내 domain model만 제공합니다. 영속화, ID 발급, 국제화된 priority 이름과 사용자 입력 UI는 포함하지 않습니다.
