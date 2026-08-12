# 02 — 값 의미론과 소유권

`TextBuffer`는 힙 문자열 하나를 직접 소유합니다. `skeleton`는 빌드되지만 복사 의미가 올바르지 않습니다. Rule of Three와 copy-and-swap을 구현해 복사 뒤 독립성과 실패 뒤 상태 보존을 확인합니다.

## 구조

- `skeleton/TextBuffer.*`: 구현할 소유 타입
- `reference/TextBuffer.*`: 비교용 구현
- `test_textbuffer.cpp`: 깊은 복사와 자기 대입 검사
- `failure_test.cpp`: 메모리 할당 실패 주입

## 실행

```sh
make observe
make exercise-test
make test
make fail-copy
```

## 복사 실패 확인하기

대입 연산에서 기존 자원을 먼저 버린 뒤 새 메모리를 할당하도록 바꿉니다. 후보를 복사하는 중 메모리 할당이 실패하면 대상 값이 사라지는지 확인합니다.

## 확인할 동작

복사한 두 객체가 독립적이고, 자기 대입이 안전하며, 실패한 대입 뒤 대상 값과 살아 있는 객체 수가 그대로입니다.

## 권장 구현 순서

<!-- implementation-scope: cpp98-command-02 -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/TextBuffer.hpp` | heap 문자열의 표현과 Rule of Three 공개 계약을 정의합니다. |
| `2` | `reference/TextBuffer.cpp` | 할당과 생성·소멸 경계에서 object와 memory 수명을 함께 관리합니다. |
| `3` | `reference/TextBuffer.cpp` | copy-and-swap으로 자기 대입과 할당 실패에도 기존 값을 보존합니다. |
| `4` | `reference/main.cpp` | TextBuffer의 값 소유권을 명령 service store에 통합합니다. |
<!-- /implementation-scope -->
