# 03. 설계 기법

## 목표

완전탐색 oracle을 기준으로 그리디와 동적 계획법의 선택 근거를 검증한다.

## 구현 대상

- `knapsack_01`
- `select_intervals`
- `lcs_length`

## 계약

### 0/1 knapsack

- 각 물건은 `(positive_weight, value)`다.
- value는 음수일 수 있으며 아무것도 고르지 않은 가치 0이 허용된다.
- 음수 capacity 또는 0 이하 weight는 `ValueError`다.

### Interval selection

- 구간은 반열린 `[start,end)`이고 `start < end`다.
- 서로 겹치지 않는 최대 개수의 구간을 반환한다.
- 결과는 `(end,start)` 선택 순서로 결정적이어야 한다.

### LCS

- 두 문자열의 longest common subsequence 길이를 반환한다.
- substring이 아니라 subsequence다.
- 빈 문자열을 허용한다.

## 독립 기준

- knapsack: 모든 부분집합
- interval: 모든 부분집합 중 호환 가능한 최대 개수
- LCS: 짧은 문자열의 모든 subsequence

## 실행

```sh
cd exercises/07-verified-algorithms-capstone
python3 check.py --impl workspace --stage design-techniques --expect pass
```

## 결함 분석

`broken/wrong-greedy`는 시작 시간이 빠른 구간부터 고른다. 검사가 어떤 입력에서 이를 거부하는지 찾아 최소화한다.

## 완료 기준

- knapsack 구현이 음수 value와 아무것도 고르지 않는 선택을 올바르게 처리한다.
- interval 결과가 최대 개수이며 `(end,start)` tie-break로 결정적이다.
- LCS 길이가 빈 문자열과 짧은 전수 입력에서 subsequence oracle과 일치한다.

## 자기 설명

- 종료 시간 우선 선택을 포함하는 최적해로 임의 최적해를 바꿀 수 있는 이유는 무엇인가?
- 0/1 knapsack의 1차원 table을 capacity 내림차순으로 갱신해야 하는 이유는 무엇인가?

## 검증

```sh
cd exercises/07-verified-algorithms-capstone
python3 check.py --impl workspace --stage design-techniques --expect pass
python3 check.py --impl broken/wrong-greedy --stage design-techniques --expect fail
```
