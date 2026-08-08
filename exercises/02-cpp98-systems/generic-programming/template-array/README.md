# 템플릿 배열과 반복자

고정 길이 `Array<T>`를 통해 함수·클래스 템플릿, 깊은 복사, `const` 반복자와 반열린 범위를 익힙니다. 잘못된 사용이 실행 시간이 아니라 컴파일 단계에서 거부되는지도 확인합니다.

## 구조

- `skeleton/Array.hpp`: 구현할 템플릿
- `reference/Array.hpp`: 비교용 구현
- `tests.cpp`: 값·문자열·const 순회 검사
- `compile_fail/`: 의도적으로 컴파일되지 않아야 하는 사용

## 실행

```sh
make observe
make exercise-test
make test
make compile-fail
```

## 확인할 동작

복사한 배열이 독립적이고, 빈 배열의 범위가 안전하며, const 배열을 수정하거나 반복자가 아닌 값을 범위로 넘기는 코드가 컴파일되지 않습니다.
