# number-report

## 개요

`number-report`는 명령행으로 받은 정수 목록을 엄격하게 검증하고 통계를 출력하는 작은 C CLI입니다. 입력 전체가 유효할 때만 stdout에 결과를 기록하며, 구문 오류와 합계 overflow를 서로 다른 종료 상태로 구분합니다.

## 주요 기능

- `strtol` 기반의 완전 일치 정수 parsing
- `long` 범위 검사와 덧셈 전 overflow 검사
- count, minimum, maximum, sum, average, even, odd 집계
- 정상 출력과 진단 출력의 stdout/stderr 분리
- 입력 오류 상태 `2`, 합계 overflow 상태 `3`

## 빌드

```sh
make
```

실행 파일은 `build/number-report`에 생성됩니다.

## 사용법

```sh
./build/number-report 10 -3 8 8 42
```

```text
count=5
minimum=-3
maximum=42
sum=65
average=13.00
even=4
odd=1
```

인자가 없거나 일부만 숫자인 문자열, 앞뒤 공백이 포함된 문자열, `long` 범위를 벗어난 값은 거부됩니다. 오류가 발생하면 stdout은 비어 있습니다.

## 검증

```sh
make test
make sanitize
```

테스트는 정상 통계, 단일 값, 허용되는 부호와 leading zero, 잘못된 문자열, `LONG_MIN`·`LONG_MAX`, 상쇄 합계와 양·음수 overflow를 확인합니다.

## 설계 결정

집계 상태는 `struct statistics` 하나가 소유합니다. minimum과 maximum은 첫 입력에서 확정되며, 합계는 undefined behavior가 발생하기 전에 범위를 검사합니다. `parse_long`은 입력 전체가 유효한 경우에만 출력 매개변수를 갱신합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Statistics state | `src/number_report.c` |
| 2 | Strict numeric parsing | `src/number_report.c` |
| 3 | Overflow-safe aggregation | `src/number_report.c` |
| 4 | Deterministic report rendering | `src/number_report.c` |
| 5 | CLI orchestration and exit semantics | `src/number_report.c` |

## 범위와 제한

입력은 현재 플랫폼의 `long` 범위로 제한됩니다. 평균은 `double`로 계산해 소수점 둘째 자리까지 표시하므로 매우 큰 정수 집합에서는 표현 정밀도가 제한될 수 있습니다.
