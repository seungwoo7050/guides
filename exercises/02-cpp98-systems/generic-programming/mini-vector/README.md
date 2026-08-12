# 예외 안전성을 갖춘 동적 배열

할당자로 저장 공간 확보와 객체 생성을 분리합니다. 재할당은 새 영역을 완성한 뒤에만 기존 상태를 교체하며, 복사 실패 시 생성이 끝난 원소만 정확히 되돌립니다.

## 구조

- `skeleton/MiniVector.hpp`: 구현할 동적 배열
- `reference/MiniVector.hpp`: 비교용 구현
- `ThrowOnCopy.hpp`: 지정한 복사 횟수에서 예외를 던지는 값 타입
- `tests.cpp`, `failure.cpp`: 정상 계약과 롤백 검사

## 실행

```sh
make observe
make exercise-test
make test
make fail-copy
```

## 복사 실패를 확인하기

`reserve` 도중 원본 저장소를 먼저 파괴하거나, `push_back(vector[0])`에서 인자 별칭을 무시합니다. 테스트가 어떤 수명 위반을 잡는지 확인합니다.

## 확인할 동작

재할당과 추가 복사 실패 뒤 원본 크기·값·살아 있는 인스턴스 수가 보존됩니다.

## 권장 구현 순서

<!-- implementation-scope: cpp98-mini-vector -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/MiniVector.hpp` | allocator storage와 size·capacity 불변식을 정의합니다. |
| `2` | `reference/MiniVector.hpp` | constructed 원소와 raw storage의 복사·소멸 수명을 관리합니다. |
| `3` | `reference/MiniVector.hpp` | checked access와 반열린 iterator 범위를 제공합니다. |
| `4` | `reference/MiniVector.hpp` | candidate storage를 완성한 뒤 reserve를 commit합니다. |
| `5` | `reference/MiniVector.hpp` | self-alias와 복사 실패에 안전한 push_back transaction을 구현합니다. |
| `6` | `demo.cpp` | 연속 삽입에서 size와 capacity 전이를 관찰합니다. |
<!-- /implementation-scope -->
