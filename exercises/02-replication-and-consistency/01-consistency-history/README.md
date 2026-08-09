# 실습: consistency history 판정

## 목표

client operation history를 linearizable, sequential, causal·session 또는 그보다 약한 계약으로 분류합니다. final state가 아니라 invocation·completion과 observed result를 사용합니다.

## 입력

[`histories.json`](histories.json)은 register와 두 register를 사용한 여섯 history를 제공합니다. `complete=null`은 pending operation입니다.

## 작업

각 history에 다음을 작성합니다.

1. non-overlapping real-time edge
2. process order
3. 가능한 sequential order 하나 이상
4. linearizable 여부
5. sequentially consistent 여부
6. causal 또는 session guarantee 위반 여부
7. pending operation 처리 방식
8. 최소 counterexample

### 직접 checker 작성

선택 구현은 작은 backtracking checker입니다.

```text
state
remaining operations
completed predecessors
observed result
```

operation을 legal하게 적용할 수 있을 때만 탐색하고, 같은 `(state, remaining)`을 memoization합니다.

## 주의

- `invoke` timestamp와 `complete` timestamp는 하나의 monotonic test timeline이라고 가정합니다.
- 겹치는 operation은 여러 위치에 linearize될 수 있습니다.
- pending write는 제거하거나 결과를 가정해 볼 수 있습니다.
- `h5`는 key별 final value만 보지 않고 causal dependency를 봅니다.

## 대표 오답

- JSON 배열 순서를 sequential order로 고정합니다.
- 겹치는 operation의 completion 순서만 사용합니다.
- pending write를 definite failure로 제거합니다.
- 각 key를 따로 검사하고 cross-key causal dependency를 놓칩니다.
- history 하나가 legal하면 구현 전체가 해당 consistency를 보장한다고 결론냅니다.

## 완료 조건

- 각 판정에 legal order 또는 모순을 제시합니다.
- linearizability와 sequential consistency의 real-time 차이를 설명합니다.
- causal dependency를 별도 edge로 다룹니다.
- pending operation의 여러 해석을 기록합니다.
