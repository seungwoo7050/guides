# 네트워크 유량과 이분 매칭

## 학습 목표

- capacity, flow, residual capacity와 flow conservation을 구분한다.
- augmenting path가 기존 선택을 되돌릴 수 있는 이유를 설명한다.
- max-flow min-cut 관계를 검증 기준으로 사용한다.
- bipartite matching을 flow로 환원한다.

## 선행 개념

[그래프 순회](01-traversal-and-topological-order.md), 경로와 잔여 상태의 불변식을 설명할 수 있어야 한다.

## 핵심 모델

flow network는 directed graph, source `s`, sink `t`, nonnegative capacity `c(u,v)`로 구성된다.

유효 flow는 다음을 만족한다.

```text
0 <= f(u,v) <= c(u,v)
source와 sink를 제외한 정점에서 유입 = 유출
```

## 1. 잔여 그래프

forward residual capacity:

```text
c_f(u,v) = c(u,v) - f(u,v)
```

reverse residual capacity:

```text
c_f(v,u) += f(u,v)
```

reverse edge는 이전 선택을 취소하고 다른 경로로 재배치할 가능성을 나타낸다. 원본 graph에 reverse edge가 없더라도 residual graph에는 존재한다.

## 2. augmenting path

residual graph에서 `s`에서 `t`로 가는 path를 찾는다. path의 bottleneck은 edge residual capacity의 최솟값이다. 그만큼 flow를 증가시키고 reverse residual을 늘린다.

각 단계는 capacity와 conservation을 보존한다.

## 3. Ford–Fulkerson과 Edmonds–Karp

Ford–Fulkerson은 augmenting path 선택 방법을 정하지 않은 틀이다. 정수 capacity에서는 각 증가가 최소 1이므로 종료하지만 path 선택에 따라 시간이 크게 달라진다.

Edmonds–Karp는 BFS로 edge 수가 가장 적은 augmenting path를 선택하며 `O(VE²)`의 다항 시간 상한을 갖는다.

더 큰 network에는 Dinic 같은 알고리즘이 적합할 수 있지만, 첫 구현에서는 residual invariant와 reverse edge가 더 중요하다.

## 4. 최대 유량·최소 컷

cut `(S,T)`는 `s ∈ S`, `t ∈ T`인 정점 분할이다. cut capacity는 `S`에서 `T`로 가는 원본 edge capacity 합이다.

모든 flow 값은 모든 cut capacity 이하이고, augmenting path가 더 없을 때 residual graph에서 source가 도달 가능한 집합이 minimum cut을 만든다. 따라서 최대 flow 값과 최소 cut capacity가 같다.

작은 graph에서는 모든 source-side subset을 열거해 독립 기준 계산으로 사용할 수 있다.

## 5. 이분 매칭 환원

왼쪽 정점 집합 `L`, 오른쪽 `R`이 있는 bipartite graph에서 최대 matching을 구한다.

구성:

```text
source → 각 L 정점 capacity 1
L → R의 원래 edge capacity 1
각 R 정점 → sink capacity 1
```

정수 capacity의 최대 flow는 정수 flow를 가지며 값이 matching 크기다. flow 1인 `L→R` edge가 선택된 pair다.

## 6. 모델링 질문

- 정점 하나가 여러 번 사용될 수 있는가?
- edge capacity인가, vertex capacity인가?
- 단위가 사람 수, 대역폭, 작업 수 중 무엇인가?
- source/sink가 하나가 아니면 super source/sink가 필요한가?
- 비용까지 최소화해야 하면 min-cost flow 문제인가?
- 시간에 따른 capacity 변화를 static network로 표현할 수 있는가?

vertex capacity는 정점을 `in`과 `out`으로 나누고 사이 edge에 capacity를 두어 표현할 수 있다.

## 7. 입력 계약

- capacity matrix는 정사각형인가?
- capacity가 음수가 아닌가?
- source와 sink가 유효한가?
- parallel edge를 합칠 것인가?
- source와 sink가 같을 때 결과는 무엇인가?

## 연결 실습

[그래프 exercise](../../exercises/04-graphs/README.md)에서 Edmonds–Karp 구현의 최대 유량 값을 모든 source-side cut의 최소 capacity와 대조하고, 함께 반환한 directed flow matrix의 capacity와 conservation을 독립적으로 검사한다.

## 완료 기준

- 모든 forward edge에 대응하는 reverse residual edge를 유지한다.
- `(value, flow)`를 반환하고 flow가 capacity와 conservation을 만족하는지 값과 별도로 검사한다.
- matching 또는 vertex-capacity 문제를 network로 바꿀 때 정점·edge 대응을 설명한다.

## 실패 조건

- reverse residual edge를 만들지 않는다.
- residual capacity와 원본 capacity를 같은 배열 의미로 섞는다.
- flow conservation을 확인하지 않는다.
- augmenting path가 없다는 것을 원본 graph에서 검사한다.
- matching 환원에서 vertex capacity 1을 빠뜨린다.
- 최대 flow 값만 맞고 실제 flow가 capacity를 위반한다.

## 연습

[그래프 exercise](../../exercises/04-graphs/README.md)에서 Edmonds–Karp를 구현하고 작은 graph의 모든 cut을 열거한 최소값과 비교한다.
