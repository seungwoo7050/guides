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
