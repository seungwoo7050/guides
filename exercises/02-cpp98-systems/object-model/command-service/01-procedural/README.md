# 01 — 절차적 명령 처리기

C++의 입출력, 문자열, 컨테이너와 함수 호출 규칙을 확인하는 첫 실행 단위입니다. 아직 객체 구조를 설계하지 않습니다. 작동하는 작은 프로그램을 만든 뒤 이후 단계에서 같은 동작을 리팩터링합니다.

## 구조

- `skeleton/main.cpp`: `split`과 명령 분기를 채우는 시작 코드
- `reference/main.cpp`: 비교용 완성 구현
- `test.sh`: 외부 입출력 계약 검사

## 실행

```sh
make observe       # 실행 전에 출력 순서를 예상합니다.
make exercise-test # skeleton 구현을 검증합니다.
make test          # reference 구현을 검증합니다.
```

## 입력 종료 처리 확인하기

`std::getline`의 반환값을 무시한 루프로 바꾸고 EOF 뒤 동작을 관찰합니다. 일반 함수 포인터와 멤버 함수 포인터의 호출식을 서로 바꾸면 어느 시점에 타입 오류가 드러나는지도 확인합니다.

## 확인할 동작

`PUT`, `GET`, `DELETE`, `COUNT`, `LIST`, `QUIT`의 출력이 테스트와 일치하고, 잘못된 명령과 인자 수를 명시적으로 거부합니다.

## 권장 구현 순서

<!-- implementation-scope: cpp98-command-01 -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/main.cpp` | 입력 줄을 명령과 인자로 분리합니다. |
| `2` | `reference/main.cpp` | store 상태와 명령별 arity·출력 계약을 한 실행 흐름으로 연결합니다. |
<!-- /implementation-scope -->
