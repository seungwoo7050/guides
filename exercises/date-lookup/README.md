# Date Lookup

## 개요

날짜별 rate CSV를 읽고 요청 날짜와 같거나 이전인 가장 가까운 rate를 조회하는 C++98 CLI입니다. calendar validation, finite-number parsing, transactional dataset load와 `std::map::upper_bound` 조회를 결합합니다.

## 빌드 및 사용

```sh
make
printf '2024-01-12 | 2\n' | ./date_lookup data.csv
make test
```

입력 형식은 `YYYY-MM-DD | amount`이며 amount 범위는 `0..1000`입니다.

## 주요 설계 결정

CSV는 임시 `std::map`에 전부 검증한 뒤 기존 dataset과 교체합니다. 따라서 중복 날짜, 잘못된 row, 음수 rate가 발견되면 부분 load 상태가 공개되지 않습니다. canonical 날짜 문자열은 lexicographical ordering과 chronological ordering이 일치합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Canonical calendar date | `src/main.cpp` |
| 2 | Total finite-number parsing | `src/main.cpp` |
| 3 | Transactional CSV load | `src/main.cpp` |
| 4 | At-or-before rate lookup | `src/main.cpp` |
| 5 | Query and process error boundaries | `src/main.cpp` |

## 범위와 한계

CSV schema는 `date,rate` 두 column으로 고정됩니다. timezone, time-of-day, locale-specific date format, streaming reload와 arbitrary precision decimal은 지원하지 않습니다.
