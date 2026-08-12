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

## date-lookup 권장 구현 순서

<!-- implementation-scope: cpp98-date-lookup -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `date-lookup/reference/main.cpp` | 유효한 달력 날짜와 canonical 표현을 값으로 만듭니다. |
| `2` | `date-lookup/reference/main.cpp` | 공백을 정리하고 입력 전체가 유한한 수인지 검증합니다. |
| `3` | `date-lookup/reference/main.cpp` | CSV 전체를 candidate map으로 검증한 뒤 commit합니다. |
| `4` | `date-lookup/reference/main.cpp` | upper_bound로 기준 날짜 이전의 가장 가까운 값을 찾습니다. |
| `5` | `date-lookup/reference/main.cpp` | 파일 실패와 개별 조회 실패를 서로 다른 실행 경계로 처리합니다. |
<!-- /implementation-scope -->

## rpn 권장 구현 순서

<!-- implementation-scope: cpp98-rpn -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `rpn/reference/main.cpp` | token 전체를 소비해 int 범위의 피연산자로 변환합니다. |
| `2` | `rpn/reference/main.cpp` | operand 순서와 산술 오류를 stack 변경 전에 검증합니다. |
| `3` | `rpn/reference/main.cpp` | 입력 token을 stack reduction 흐름으로 계산합니다. |
| `4` | `rpn/reference/main.cpp` | 마지막 값 하나의 invariant와 CLI 실패 결과를 고정합니다. |
<!-- /implementation-scope -->

## sorter 권장 구현 순서

<!-- implementation-scope: cpp98-sorter -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `sorter/reference/main.cpp` | 정렬 key와 원래 입력 순서를 함께 보존하는 Record를 만듭니다. |
| `2` | `sorter/reference/main.cpp` | argument 전체를 소비해 음이 아닌 int만 받습니다. |
| `3` | `sorter/reference/main.cpp` | 검증된 argument를 Record 목록으로 materialize합니다. |
| `4` | `sorter/reference/main.cpp` | stable_sort 결과와 측정 구간을 관찰 가능한 출력으로 만듭니다. |
<!-- /implementation-scope -->
