# 완전탐색과 백트래킹

## 학습 목표

- 상태 공간과 선택 순서를 명시한다.
- 중복 없이 모든 후보를 생성하는 방법을 설계한다.
- pruning이 정답을 제거하지 않는 근거를 설명한다.
- brute-force reference와 최적 구현의 역할을 구분한다.

## 선행 개념

문제 계약, 재귀 호출의 종료 조건과 [정확성 불변식](../01-foundations/04-correctness-and-invariants.md)을 알고 있어야 한다.

## 핵심 모델

완전탐색은 “느린 풀이”가 아니라 가능한 해 공간의 정의다.

```text
상태: 지금까지 한 선택
다음 선택: 아직 결정하지 않은 한 항목
종료: 완성된 후보 또는 더 진행할 수 없는 상태
검사: 계약을 만족하는가?
```

백트래킹은 이 상태 공간에서 정답이 될 수 없는 subtree를 안전하게 잘라낸다.

## 1. 상태 공간 크기

- 부분집합: `2^n`
- 순열: `n!`
- 각 위치에 k개 선택: `k^n`
- 격자 경로: 분기 수와 깊이에 따른 지수 증가

입력 제한을 보기 전에 재귀 코드를 작성하지 않는다. 상태 수와 각 상태의 검사 비용을 곱한다.

## 2. 선택·진행·복구

```text
search(state):
    if state가 완성됨:
        결과 처리
        return

    for choice in 가능한 선택:
        choice 적용
        search(새 state)
        choice 복구
```

복구가 빠지면 형제 branch가 이전 branch의 상태를 물려받는다. immutable state를 복사할 수도 있지만 복사 비용을 분석해야 한다.

## 3. 중복 제거

같은 값이 반복될 때 순열을 index 기준으로 생성하면 같은 결과가 여러 번 나온다.

방법:

- 먼저 정렬하고 같은 깊이에서 같은 값을 한 번만 선택
- 빈도 map으로 남은 개수 관리
- canonical order를 강제

중복 제거 조건은 서로 다른 유효 해를 합치지 않아야 한다.

## 4. pruning의 종류

### 제약 위반

현재까지 이미 용량·합·충돌 조건을 위반했다면 더 진행해도 회복할 수 없는 경우 중단한다.

### bound

현재 결과와 남은 최대 가능 이득을 합쳐도 best를 넘지 못하면 중단한다.

```text
current + optimistic_remaining <= best
```

bound는 실제 가능한 이득보다 작아서는 안 된다. 지나치게 낙관적인 bound는 느릴 뿐 정확성은 유지하지만, 비관적인 bound는 정답을 잘라낼 수 있다.

### 대칭 제거

서로 이름만 다른 동일 상태를 하나의 대표만 탐색한다. 대칭임을 증명할 수 있어야 한다.

## 5. memoization과의 경계

다른 선택 경로가 같은 미래 상태에 도달한다면 결과를 재사용할 수 있다.

```text
state key가 미래 결과를 결정하는 모든 정보를 포함하는가?
```

현재 경로의 일부 정보가 결과에 영향을 주는데 key에서 빠지면 잘못된 재사용이 일어난다. 상태가 DAG를 이루고 최적 부분 구조가 있으면 동적 계획법으로 정리할 수 있다.

## 6. 기준 풀이로서의 완전탐색

작은 입력에서는 최적 구현보다 단순한 완전탐색이 더 좋은 test oracle이다.

- interval scheduling: 모든 부분집합 중 호환 가능한 최대 개수
- knapsack: 모든 선택 집합의 최대 가치
- MST: `V-1`개 간선 조합 중 tree인 최소 가중치
- max flow: 모든 source-side cut의 최소 용량
- LCS: 짧은 문자열의 모든 subsequence

기준 풀이도 독립 test를 가져야 한다.

## 7. 예제: N-Queens

상태:

```text
row: 다음에 배치할 행
used_columns
used_diag_down: row-col
used_diag_up: row+col
```

불변식:

```text
[0,row) 각 행에는 queen이 하나 있다.
어떤 두 queen도 같은 열·대각선에 없다.
```

다음 행에서 충돌하지 않는 열만 선택한다. 제약 위반 상태를 생성하지 않으므로 pruning은 안전하다.

## 연결 실습

[설계 기법 exercise](../../exercises/03-design-techniques/README.md)에서 배낭의 모든 부분집합 oracle을 먼저 만들고, 효율적인 구현과 같은 입력을 공유하지 않도록 복제해 비교한다.

## 완료 기준

- 선택 수와 깊이로 탐색 전 상태 공간 상한을 계산한다.
- 재귀 호출 전후에 mutable 상태가 정확히 복구됨을 trace로 확인한다.
- pruning이 제거한 branch에 최적해가 없다는 상한 또는 제약 근거를 적는다.

## 실패 조건

- 상태 공간 크기를 계산하지 않는다.
- mutable state를 복구하지 않는다.
- 중복 제거가 서로 다른 해까지 제거한다.
- optimistic bound가 실제 가능한 최댓값보다 작다.
- memo key가 미래를 결정하는 정보를 빠뜨린다.
- reference가 후보와 같은 알고리즘을 사용한다.

## 연습

[설계 기법 exercise](../../exercises/03-design-techniques/README.md)에서 배낭과 구간 선택의 exhaustive oracle을 먼저 설명한 뒤 효율적인 구현과 비교한다.
