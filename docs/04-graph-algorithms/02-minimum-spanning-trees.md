# 최소 스패닝 트리

## 학습 목표

- shortest path tree와 minimum spanning tree를 구분한다.
- cut property와 cycle property로 안전한 간선을 설명한다.
- Kruskal과 Prim의 상태·자료구조·비용을 비교한다.
- disconnected graph와 중복 가중치 계약을 명시한다.

## 선행 개념

[그리디 교환 논리](../03-design-techniques/02-greedy-methods.md), [분리 집합](../02-data-structures/04-disjoint-sets-and-amortized-analysis.md)과 연결성을 알고 있어야 한다.

## 핵심 모델

연결된 무방향 가중 graph의 spanning tree는 모든 정점을 연결하는 `V-1`개 간선의 cycle 없는 부분 graph다. MST는 그중 가중치 합이 최소인 tree다.

MST는 특정 시작점에서 각 정점까지의 경로를 최소화하지 않는다.

## 1. 절단 성질

정점 집합을 두 부분으로 나눈 cut을 생각한다. 어떤 MST와도 충돌하지 않는 조건 아래, 그 cut을 가로지르는 최소 가중치 간선은 안전하다.

직관:

- 최적 tree가 그 최소 간선 `e`를 포함하지 않으면 `e`를 추가할 때 cycle이 생긴다.
- 그 cycle에는 같은 cut을 가로지르는 다른 간선 `f`가 있다.
- `w(e) <= w(f)`이므로 `f`를 `e`로 바꿔도 비용이 늘지 않는다.

## 2. Kruskal

1. 모든 간선을 `(weight, tie-break)` 순으로 정렬한다.
2. 서로 다른 component를 잇는 간선만 선택한다.
3. `V-1`개를 선택하면 종료한다.

DSU가 component를 관리한다.

불변식:

```text
선택한 간선은 forest다.
현재 forest를 포함하는 MST가 적어도 하나 존재한다.
```

비용은 정렬 `O(E log E)`가 지배하며 DSU 연산은 거의 선형에 가깝다.

## 3. Prim

하나의 tree를 확장한다.

```text
inside 집합과 outside 집합 사이의 최소 간선을 선택
새 정점을 inside에 추가
그 정점에서 나가는 후보를 heap에 추가
```

lazy heap을 사용하면 이미 inside인 정점으로 가는 오래된 후보를 pop 시 버릴 수 있다.

인접 리스트와 binary heap에서는 보통 `O(E log V)`다.

## 4. 알고리즘 선택

- edge list가 이미 있고 희소 graph: Kruskal이 단순
- 한 정점에서 인접 edge를 쉽게 얻음: Prim
- 매우 밀집 graph와 배열 기반 최소 key 선택: `O(V²)` Prim도 실용적
- 추가되는 간선을 offline으로 처리: Kruskal 구조가 자연스러움

## 5. 중복 가중치와 유일성

가중치가 모두 다르면 MST는 유일하다. 중복이 있으면 여러 MST가 존재할 수 있다.

계약이 총 가중치만 요구하는지, 특정 간선 목록과 tie-break를 요구하는지 구분한다. 테스트는 유일한 edge set을 강제하기보다 다음을 확인하는 편이 안전하다.

- 간선 수 `V-1`
- 연결성과 cycle 없음
- 원본 간선 사용
- 총 가중치가 최적값과 같음

## 6. disconnected graph

선택지는 API에서 정한다.

- 오류로 거부
- 각 component의 minimum spanning forest 반환
- 연결 여부와 결과를 함께 반환

연결 graph 전조건을 숨기지 않는다.

## 7. cycle property

어떤 cycle에서 유일하게 가장 무거운 간선은 어떤 MST에도 포함될 수 없다. 이를 사용해 간선 제거의 안전성을 설명할 수 있다.

## 8. 작은 기준 계산

작은 graph에서 `V-1`개 간선 조합을 모두 열거한다.

1. cycle이 없는지 확인
2. 모든 정점이 연결되는지 확인
3. 가중치 합 최소 선택

Kruskal reference test가 같은 DSU 구현을 기준으로 사용하지 않도록 한다.

## 연결 실습

[그래프 exercise](../../exercises/04-graphs/README.md)에서 Kruskal 결과를 작은 graph의 모든 `V-1` edge 조합과 대조하고 disconnected 계약도 검사한다.

## 완료 기준

- 선택한 edge가 cycle을 만들지 않는 DSU 불변식을 설명한다.
- 절단을 가로지르는 안전한 최소 edge가 존재하는 근거를 적는다.
- 중복 가중치에서는 특정 edge 집합이 아니라 총가중치와 tree 조건을 검증한다.

## 실패 조건

- directed graph에 MST를 그대로 적용한다.
- 가장 싼 간선을 cycle 여부 없이 고른다.
- shortest path tree와 MST를 혼동한다.
- disconnected graph의 결과 계약이 없다.
- 중복 가중치에서 특정 edge set만 정답으로 가정한다.
- 기준 검사도 Kruskal을 사용한다.

## 연습

[그래프 exercise](../../exercises/04-graphs/README.md)에서 Kruskal을 구현하고 작은 graph의 모든 spanning tree와 총 가중치를 대조한다.
