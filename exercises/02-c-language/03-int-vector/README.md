# 연습문제: int-vector

## 목표

동적 정수 배열의 불변식과 공개 API를 구현합니다. 여러 번 성장해도 원소를 보존하고, 다음 성장의 할당 실패 뒤 호출 전 상태를 유지해야 합니다.

## 구현 위치

저장소 루트에서 다음 명령을 실행한 뒤 `workspace/src/int_vector.c`를 구현합니다. 공개 헤더는 변경하지 않습니다.

```sh
scripts/new-workspace.sh exercises/02-c-language/03-int-vector
cd exercises/02-c-language/03-int-vector
```

기준 구현과 권장 구현 순서는 자신의 검사가 통과한 뒤 [`reference/`](reference/README.md)에서 비교합니다.

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

## 완료 기준

- `make exercise-test`와 `make sanitize`가 통과하며 0개에서 시작해 여러 번 capacity를 늘려도 삽입 순서와 모든 기존 원소가 보존됩니다.
- 유효한 첫·마지막 index 조회와 범위 밖 조회를 확인하고, 실패한 `get`이 `out_value`를 바꾸지 않음을 sentinel 값으로 증명합니다.
- 잘못된 불변식, capacity 계산 overflow와 다음 성장의 할당 실패 뒤 data·size·capacity·원소가 호출 전 상태 그대로임을 확인합니다.

## 자기 설명

- `size == capacity`일 때 새 capacity와 바이트 수를 계산하는 각 단계에서 어떤 overflow를 막아야 하나요?
- 실패할 수 있는 할당과 상태 갱신의 순서를 어떻게 정해야 기존 vector를 계속 사용할 수 있나요?

## 검증

```sh
make exercise-test
make sanitize
```
