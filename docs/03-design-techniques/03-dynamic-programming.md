# 동적 계획법

## 학습 목표

- 상태가 미래 결과를 결정하는 최소 정보를 담도록 설계한다.
- recurrence, base case, 계산 순서를 분리한다.
- memoization과 tabulation을 같은 상태 DAG의 두 실행 방식으로 이해한다.
- 값뿐 아니라 실제 해를 복원한다.

## 선행 개념

재귀적 문제 분해, [점화식](../01-foundations/03-recurrences-and-divide-and-conquer.md)과 상태 불변식을 알고 있어야 한다.

## 핵심 모델

동적 계획법은 다음 세 조건을 갖는다.

```text
같은 하위 문제가 반복된다.
하위 문제 결과로 현재 결과를 계산할 수 있다.
상태 사이 의존 관계가 순환 없이 계산 가능하다.
```

## 1. 상태 문장부터 쓴다

좋은 상태 정의는 반환값을 완전한 문장으로 설명한다.

```text
dp[i] = 처음 i개 원소를 처리했을 때의 최적값
dp[i][c] = 처음 i개 물건과 용량 c에서 얻는 최대 가치
dp[i][j] = A[:i]와 B[:j]의 LCS 길이
```

“현재까지의 답”처럼 입력 범위가 없는 정의는 recurrence를 결정하지 못한다.

## 2. recurrence

### 0/1 knapsack

물건 `(weight,value)`를 사용하지 않거나 한 번 사용한다.

```text
dp[i][c] = max(
    dp[i-1][c],
    dp[i-1][c-weight_i] + value_i  if weight_i <= c
)
```

같은 행 `dp[i]`를 참조하면 한 물건을 여러 번 사용할 수 있어 unbounded knapsack으로 바뀐다.

1차원으로 줄일 때 capacity를 큰 값에서 작은 값으로 순회해야 0/1 계약이 유지된다.

## 3. LCS

```text
if A[i-1] == B[j-1]:
    dp[i][j] = dp[i-1][j-1] + 1
else:
    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
```

동점에서 어느 방향을 택할지에 따라 복원되는 실제 subsequence가 달라진다. 길이만 계약이면 둘 다 맞지만, lexicographic 최소까지 요구하면 추가 상태나 다른 설계가 필요하다.

## 4. 계산 순서

상태 의존 graph의 topological order로 계산한다.

- prefix 상태: 작은 index에서 큰 index
- interval DP: 짧은 구간에서 긴 구간
- DAG path DP: topological order
- 0/1 knapsack 1차원: capacity 내림차순
- unbounded knapsack: capacity 오름차순

순서를 외우기보다 현재 갱신이 같은 item을 다시 읽는지 확인한다.

## 5. memoization과 tabulation

### memoization

필요한 상태만 계산하기 쉽고 recurrence를 직접 표현한다. recursion depth와 hash key 비용을 고려한다.

### tabulation

계산 순서와 memory layout을 제어하기 쉽다. 불필요한 상태까지 계산할 수 있다.

둘은 상태 정의와 recurrence가 같다면 같은 알고리즘 구조다.

## 6. 공간 최적화

현재 상태가 직전 row만 필요하면 두 row 또는 한 row로 줄일 수 있다. 그러나 다음을 먼저 확인한다.

- 갱신 전 값과 갱신 후 값을 같은 배열에서 구분할 수 있는가?
- 해 복원에 전체 predecessor 정보가 필요한가?
- cache locality와 구현 복잡도의 tradeoff는 어떤가?

공간을 줄이며 계산 순서를 바꾸면 recurrence 의미도 바뀔 수 있다.

## 7. 해 복원

값만 저장한 뒤 recurrence를 역추적하거나 각 상태에 predecessor choice를 저장한다.

복원 계약:

- 최적값과 일치하는 해인가?
- 동점 규칙을 지키는가?
- 선택한 원소가 중복 사용되지 않았는가?
- 복원 비용이 전체 complexity를 바꾸지 않는가?

## 8. DP가 아닌 경우

- 상태에 과거 전체가 필요해 압축할 수 없음
- 동일해 보이는 state가 미래 제약에서 다름
- 의존 관계에 cycle이 있고 fixed point 의미가 정의되지 않음
- 상태 수가 입력 제한보다 큼
- 그리디 교환 논리로 더 단순하게 해결 가능

## 연결 실습

[설계 기법 exercise](../../exercises/03-design-techniques/README.md)에서 0/1 knapsack과 LCS를 작은 exhaustive oracle과 비교하고, 갱신 순서를 바꾼 결함 입력을 고정한다.

## 완료 기준

- DP 상태 하나가 답하는 질문과 처리한 입력 범위를 한 문장으로 정의한다.
- recurrence의 모든 의존 상태가 먼저 계산되는 순서를 설명한다.
- 공간 최적화 전후 값이 같고 해 복원 계약이 필요한지 별도로 확인한다.

## 실패 조건

- 상태 정의에 처리한 입력 범위가 없다.
- base case가 계약의 빈 입력과 다르다.
- 0/1 knapsack에서 capacity를 오름차순 갱신한다.
- memo key에서 미래에 필요한 정보를 빠뜨린다.
- 공간 최적화 뒤 해 복원 계약을 잃는다.
- 최적 부분 구조를 증명하지 않고 DP table부터 만든다.

## 연습

[설계 기법 exercise](../../exercises/03-design-techniques/README.md)에서 0/1 knapsack과 LCS를 exhaustive oracle과 비교하고, 잘못된 갱신 순서의 반례를 작성한다.
