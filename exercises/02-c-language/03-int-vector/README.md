# 연습문제: int-vector

## 목표

동적 정수 배열의 불변식과 공개 API를 구현합니다. 여러 번 성장해도 원소를 보존하고, 다음 성장의 할당 실패 뒤 호출 전 상태를 유지해야 합니다.

## 구현 위치

`skeleton/src/int_vector.c`를 구현합니다. 공개 헤더는 변경하지 않습니다.

## 계약

```text
size <= capacity
capacity == 0이면 data == NULL
0 <= index < size인 원소만 유효
```

- `init`은 아직 초기화되지 않은 객체에 호출합니다. 같은 객체를 다시 초기화하려면 먼저 destroy합니다.
- 공개 필드는 `init` 뒤 API만으로 변경합니다. 불변식이 깨진 객체의 `push`와 `get`은 -1입니다.
- `push` 성공은 0, 잘못된 인자·overflow·할당 실패는 -1입니다.
- 실패하면 data, size, capacity와 기존 원소가 모두 보존됩니다.
- `get`의 범위 오류는 `out_value`를 변경하지 않습니다.
- destroy 뒤 빈 상태가 되고 반복 호출할 수 있습니다.

## 검증

```sh
make exercise-test
make sanitize
```
