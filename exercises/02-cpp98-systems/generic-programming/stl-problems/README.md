# STL로 작은 문제 해결하기

세 프로그램은 자료구조를 직접 재구현하지 않고 요구사항에 맞는 STL 계약을 선택합니다.

- `date-lookup`: 엄격한 날짜 파싱과 `map::upper_bound`
- `rpn`: `stack`을 이용한 후위 표기식 계산
- `sorter`: 입력 순서를 보존하는 레코드 정렬과 측정

## 실행

```sh
make observe
make exercise-test
make test
make randomized-test
```

각 하위 디렉터리는 독립된 Makefile과 `skeleton`, `reference`을 갖습니다. `randomized-test`는 여러 입력에서 정렬 결과를 기준 구현과 대조합니다.

## 확인할 동작

입력을 완전히 소비해 검증하고, 빈 범위·중복·경계값을 처리하며, 자료구조를 선택한 이유를 주요 연산과 복잡도로 설명합니다.
