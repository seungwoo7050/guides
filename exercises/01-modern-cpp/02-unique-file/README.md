# RAII와 이동 전용 파일 소유자

## 목표

`std::FILE*`을 직접 전달하는 대신 파일 핸들의 유일한 소유자를 만듭니다. 소멸자, 이동 생성자, 이동 대입, 실패 표현을 함께 구현하며 “자원을 누가 언제 정리하는가”를 타입으로 고정합니다.

## 시작하기 전에

[값·수명·이동](../../../docs/01-modern-cpp/02-values-lifetimes-and-move.md)과 [RAII·스마트 포인터·Rule of Zero](../../../docs/01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md)를 먼저 읽습니다.

## 구현할 계약

- `UniqueFile`은 복사할 수 없습니다.
- 이동 뒤 원본은 닫힌 상태이지만 소멸 가능한 유효 객체입니다.
- 이동 대입은 기존 파일을 먼저 닫습니다.
- `close`는 여러 번 호출해도 안전합니다.
- 열기 실패는 예외가 아니라 `FileError` 값으로 반환합니다.
- 이미 열린 파일의 읽기·쓰기 실패는 `std::system_error`로 보고합니다.

## 작업 순서

1. 소멸자와 `close`의 관계를 확인합니다.
2. 이동 생성자에서 `std::exchange`를 사용해 단일 소유권을 옮깁니다.
3. 이동 대입의 자기 대입과 기존 자원 정리를 처리합니다.
4. `open_file`에서 `errno`를 즉시 보존합니다.
5. 닫힌 핸들, 부분 I/O와 flush 실패를 구분합니다.

## 실패 실험

다음 결함을 한 번씩 넣고 테스트 또는 sanitizer가 무엇을 발견하는지 기록합니다.

- 이동 뒤 원본 포인터를 `nullptr`로 만들지 않습니다.
- 이동 대입 전에 기존 핸들을 닫지 않습니다.
- `fwrite` 반환값을 검사하지 않습니다.
- `close` 후 포인터를 그대로 둡니다.

## 검증

```sh
make modern-skeleton-build
make modern-test
make modern-sanitize
```

## 명시적인 한계

소멸자와 `close()`는 자원 누수를 막기 위한 정리 경계이며 최종 `fclose` 오류를 caller에게 반환하지 않습니다. 영구 저장 성공을 반드시 확인해야 하는 API라면 오류를 보고할 수 있는 `finish()` 같은 명시적 연산을 별도로 설계해야 합니다. reference의 `open_file`은 학습 범위를 위해 `std::fopen(path.string().c_str(), mode)`을 사용하므로 Windows의 모든 비 ASCII 경로를 보장하지 않습니다. 그런 요구가 있다면 platform adapter 또는 wide-character API 경계를 추가합니다.

## 완료 기준

- 타입 특성 검사에서 복사는 금지되고 이동은 `noexcept`입니다.
- 이동 전·후 소유 상태가 정확합니다.
- 열기 실패에 경로와 오류 코드가 남습니다.
- 테스트와 sanitizer를 모두 통과합니다.
