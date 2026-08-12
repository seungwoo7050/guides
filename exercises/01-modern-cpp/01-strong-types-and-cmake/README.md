# 강한 타입과 target 기반 CMake

## 목표

정수와 문자열을 그대로 전달하는 대신 의미가 있는 값 타입으로 계약을 표현합니다. `TaskId`, `Priority`, `Task`를 구현하고 CMake target이 헤더, 구현, 테스트와 C++20 요구사항을 연결하는 방식을 확인합니다.

## 시작하기 전에

[프로그램·빌드·CMake](../../../docs/01-modern-cpp/01-program-build-cmake.md)와 [값·수명·이동](../../../docs/01-modern-cpp/02-values-lifetimes-and-move.md)을 먼저 읽습니다.

## 구현할 계약

- `TaskId`는 정수에서 암묵적으로 만들어지지 않습니다.
- `TaskId::parse`는 문자열 전체가 부호 없는 정수일 때만 성공합니다.
- `Priority`는 `low`, `normal`, `high`만 허용합니다.
- `Task`는 빈 제목으로 만들어질 수 없습니다.
- 출력 형식은 `#<id> [<priority>] <title>`로 고정합니다.

## 작업 순서

1. `skeleton/src/task.cpp`의 TODO를 읽고 각 함수의 실패 조건을 먼저 적습니다.
2. `TaskId::parse`를 `std::from_chars`로 구현합니다.
3. 열거형과 문자열 사이의 변환을 완성합니다.
4. 생성자에서 불변식을 확립합니다.
5. 전체 테스트를 실행하고 reference와 구현 차이를 비교합니다.

## 검증

저장소 루트에서 다음 명령을 사용합니다.

```sh
make modern-exercise-test MODERN_EXERCISE=01-strong-types-and-cmake
```

명령은 `.workspace/01-modern-cpp/01-strong-types-and-cmake/skeleton/`을 build하고 완성 계약 test를 실행합니다. 처음에는 실패하며, TODO를 모두 구현한 뒤 같은 명령이 통과해야 합니다.

## 완료 기준

- 잘못된 숫자와 우선순위를 거부합니다.
- 빈 제목으로 유효하지 않은 `Task`가 생기지 않습니다.
- `TaskId`의 명시적 변환 계약을 컴파일 시점에 확인합니다.
- reference를 보지 않고 테스트를 통과한 뒤 구현 차이를 설명할 수 있습니다.

## 권장 구현 순서

<!-- implementation-scope: modern-strong-types -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `CMakeLists.txt` | 동일한 공개 계약을 reference와 skeleton target에 연결합니다. |
| `2` | `reference/include/task.hpp` | 원시 값 대신 강한 ID·우선순위·Task 모델을 정의합니다. |
| `3` | `reference/src/task.cpp` | 입력 전체를 검증한 뒤 domain 값으로 변환합니다. |
| `4` | `reference/src/task.cpp` | Task 생성 시 빈 제목을 거부합니다. |
| `5` | `reference/src/task.cpp` | 유효한 Task를 안정된 외부 형식으로 직렬화합니다. |
<!-- /implementation-scope -->
