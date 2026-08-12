# 연습문제: owned-string

## 목표

성장 가능한 소유 문자열을 구현하고 불변식, self-append, 크기 overflow와 할당 실패 뒤 강한 상태 보장을 검증합니다.

## 구현 위치

저장소 루트에서 다음 명령을 실행한 뒤 `workspace/src/owned_string.c`를 구현합니다. 공개 헤더는 변경하지 않습니다.

```sh
scripts/new-workspace.sh exercises/02-c-language/02-owned-string
cd exercises/02-c-language/02-owned-string
```

기준 구현과 권장 구현 순서는 자신의 검사가 통과한 뒤 [`reference/`](reference/README.md)에서 비교합니다.

## 불변식

```text
빈 상태:
  data == NULL, length == 0, capacity == 0

할당 상태:
  data != NULL, length < capacity, data[length] == '\0'
```

## API 계약

- `init`은 아직 초기화되지 않은 객체에 호출합니다. 같은 객체를 다시 초기화하려면 먼저 destroy합니다.
- 공개 필드는 `init` 뒤 API만으로 변경합니다. 불변식이 깨진 객체의 append는 -1입니다.
- append 성공은 0, 잘못된 인자·overflow·할당 실패는 -1입니다.
- 실패하면 data 포인터, 내용, length와 capacity를 모두 보존합니다.
- 현재 문자열 전체 또는 내부의 NUL 종료 suffix를 source로 전달하는 alias append를 지원합니다.
- 성장 중 `realloc`이 메모리를 옮겨도 source offset을 보존해야 합니다.
- destroy 뒤 빈 상태가 되며 반복 호출할 수 있습니다.
- allocator는 테스트가 특정 resize 호출을 실패시키기 위한 경계입니다.

## 완료 기준

- `make exercise-test`와 `make sanitize`가 통과하며 초기화, 여러 번의 성장, 빈 문자열 append와 반복 destroy 뒤에도 불변식이 유지됩니다.
- 문자열 전체와 내부 suffix를 source로 넘기는 alias append가 `realloc`의 이동 여부와 관계없이 정확한 결과를 만듭니다.
- 잘못된 객체, 크기 overflow와 지정한 할당 실패 뒤 data 포인터·내용·length·capacity가 호출 전과 동일함을 테스트로 증명합니다.

## 자기 설명

- alias source를 포인터가 아니라 기존 data로부터의 offset으로 기억해야 `realloc` 뒤에도 안전한 이유는 무엇인가요?
- 새 capacity 계산과 할당을 먼저 성공시킨 뒤 공개 상태를 갱신하는 순서가 강한 실패 보장을 어떻게 만드는지 설명할 수 있나요?

## 검증

```sh
make exercise-test
make sanitize
```
