# Stable Sorter

## 개요

command-line의 non-negative integer record를 `std::stable_sort`로 정렬하고 순수 정렬 구간의 CPU 시간을 출력하는 C++98 utility입니다. 각 record는 원래 입력 위치를 함께 보존합니다.

## 빌드 및 사용

```sh
make
./stable_sorter 9 3 7 1 3
make test
```

stdout에는 `before:`와 `after:` 값 목록이, stderr에는 측정 시간이 출력됩니다.

## 주요 설계 결정

입력 검증과 record materialization을 완료한 뒤에만 측정을 시작합니다. comparator는 value만 비교하므로 equal key의 순서는 `std::stable_sort` 계약으로 보존됩니다. randomized test는 다양한 중복 입력을 Python의 기준 정렬과 비교합니다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Stable record model | `src/main.cpp` |
| 2 | Total argument validation | `src/main.cpp` |
| 3 | Record materialization | `src/main.cpp` |
| 4 | Stable sort and measurement | `src/main.cpp` |

## 범위와 한계

입력은 `int` 범위의 음이 아닌 값만 지원합니다. 측정값은 `std::clock` 기반이며 microbenchmark의 통계적 신뢰도나 wall-clock latency를 보장하지 않습니다.
