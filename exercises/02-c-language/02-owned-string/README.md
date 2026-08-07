# 연습문제: owned-string

## 목표

성장 가능한 소유 문자열을 구현하고 불변식, self-append, 크기 overflow와 할당 실패 뒤 강한 상태 보장을 검증합니다.

## 구현 위치

`skeleton/src/owned_string.c`를 구현합니다. 공개 헤더는 변경하지 않습니다.

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

## 검증

```sh
make exercise-test
make sanitize
```
