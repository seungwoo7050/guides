# Unique File

## 개요

`std::FILE*`의 단일 소유권을 RAII로 관리하는 C++20 library입니다. 복사를 금지하고 이동으로만 소유권을 전달하며, 파일 획득 실패와 열린 파일의 I/O 실패를 서로 다른 오류 경계로 처리합니다.

## 기능

- move-only `UniqueFile`
- moved-from 객체의 유효한 closed 상태 보장
- 기존 handle을 정리하는 move assignment
- 여러 번 호출해도 안전한 `close()`
- `OpenResult`를 통한 예외 없는 open 실패 반환
- partial read/write와 flush 실패를 `std::system_error`로 보고

## 구조

- `include/unique_file.hpp`: ownership 및 오류 계약
- `src/unique_file.cpp`: handle lifecycle과 checked I/O
- `tests/unique_file_tests.cpp`: 이동, 닫힌 상태, binary I/O, 실패 경로 검증

## 빌드 및 테스트

```sh
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

## 주요 설계 결정

`open_file`은 유효하지 않은 owner를 만들지 않고 `FileError`에 원래 경로와 `error_code`를 보존합니다. 소멸자와 `close()`는 누수를 막는 정리 경계이므로 `fclose` 실패를 반환하지 않습니다. 영구 저장 성공을 확인해야 하는 API에는 별도의 명시적 완료 연산이 필요합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Ownership and acquisition contract | `include/unique_file.hpp` |
| 2 | Single-owner lifecycle | `src/unique_file.cpp` |
| 3 | Checked I/O boundary | `src/unique_file.cpp` |
| 4 | Resource acquisition result | `src/unique_file.cpp` |

## 범위와 한계

`open_file`은 `std::filesystem::path::string()`과 `std::fopen`을 사용하므로 Windows의 모든 non-ASCII path를 보장하지 않습니다. 소멸 시 발생하는 `fclose` 오류는 관찰할 수 없습니다.
