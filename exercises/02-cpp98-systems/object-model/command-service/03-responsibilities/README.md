# 03 — 책임 분리

동작은 맞지만 파싱, 상태 규칙과 출력 형식이 한 함수에 섞인 코드를 작은 협력으로 나눕니다. 출력 결과뿐 아니라 의존 방향과 공개 경계도 검증합니다.

## 구조

- `skeleton/legacy.cpp`: 리팩터링 전 관찰 대상
- `skeleton/`: 제한된 인터페이스와 TODO
- `reference/`: `RequestParser`, `KeyValueStore`, `CommandService`, `ResponseFormatter`로 나눈 구현
- `interface_test.cpp`: 공개 헤더를 함께 사용하는 호출자 관점의 검사

## 실행

```sh
make observe
make exercise-test
make test
make interface-check
```

## 책임을 다시 섞어 보기

저장 용량 검사나 응답 문자열 조립을 다시 `main`으로 옮깁니다. 동작 테스트는 통과할 수 있지만 변경 이유가 다시 섞이는 것을 의존 관계로 설명합니다.

## 확인할 동작

각 클래스의 변경 이유를 한 문장으로 설명할 수 있고, 저장 규칙은 `KeyValueStore`, 문법은 파서, 외부 문자열은 포매터가 책임집니다.
