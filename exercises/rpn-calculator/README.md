# RPN Calculator

## 개요

공백으로 구분된 Reverse Polish Notation expression을 계산하는 C++98 CLI입니다. `std::stack<int>`를 사용하며 token, operand 수, 0 나눗셈과 signed integer overflow를 검증합니다.

## 빌드 및 사용

```sh
make
./rpn '3 4 + 2 *'
make test
```

지원 operator는 `+`, `-`, `*`, `/`입니다. 각 operand는 `int` 범위여야 합니다.

## 주요 설계 결정

operator는 오른쪽 operand와 왼쪽 operand를 분리한 뒤 정확한 순서로 적용합니다. 산술 오류는 결과 계산 전에 검사해 undefined signed overflow를 피합니다. 전체 입력 처리 후 stack에는 값 하나만 남아야 합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Total operand parsing | `src/main.cpp` |
| 2 | Checked arithmetic | `src/main.cpp` |
| 3 | Stack reduction | `src/main.cpp` |
| 4 | Final expression invariant | `src/main.cpp` |

## 범위와 한계

정수 연산만 지원하며 변수, unary operator, floating point, arbitrary precision과 interactive prompt는 제공하지 않습니다. 나눗셈은 C++ 정수 나눗셈 규칙을 따릅니다.
