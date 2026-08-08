# 최단 경로

## 학습 목표

- edge weight 조건에 따라 BFS, DAG relaxation, Dijkstra, Bellman–Ford를 선택한다.
- relaxation의 의미와 확정 조건을 설명한다.
- 도달 불가능과 음수 cycle을 구분한다.
- all-pairs 문제에서 Floyd–Warshall의 상태를 설명한다.

## 선행 개념

[그래프 순회](01-traversal-and-topological-order.md), 우선순위 queue와 동적 계획의 상태 갱신을 알고 있어야 한다.

## 핵심 모델

최단 경로 알고리즘의 공통 연산은 relaxation이다.

```text
if dist[u]가 알려져 있고 dist[u] + weight(u,v) < dist[v]:
    dist[v] = dist[u] + weight(u,v)
    parent[v] = u
```

알고리즘마다 “어떤 순서로 몇 번 relaxation하면 값이 확정되는가”가 다르다.

## 1. 선택표

| 조건 | 알고리즘 | 대표 비용 |
|---|---|---:|
| 모든 edge 비용 동일 | BFS | `O(V+E)` |
| DAG, 음수 가능 | topological relaxation | `O(V+E)` |
| 음수 없음 | Dijkstra | `O((V+E) log V)` |
| 음수 가능, reachable negative cycle 검출 | Bellman–Ford | `O(VE)` |
| 작은 all-pairs | Floyd–Warshall | `O(V³)` |

## 2. BFS

모든 edge가 비용 1이면 queue의 레벨 순서가 거리 순서다. 가중치가 0과 1뿐이면 deque 기반 0-1 BFS를 사용할 수 있다.

## 3. DAG 최단 경로

위상 순서대로 각 정점의 outgoing edge를 relaxation한다. 뒤 정점에서 앞 정점으로 돌아오는 edge가 없으므로 한 번의 순회로 충분하다. 음수 edge가 있어도 cycle이 없으므로 문제되지 않는다.

## 4. Dijkstra

전조건: 모든 edge weight가 음수가 아니다.

```text
priority queue에서 현재 최소 tentative distance를 가진 정점을 꺼낸다.
이미 더 좋은 거리로 처리된 오래된 entry는 버린다.
그 정점의 outgoing edge를 relaxation한다.
```

불변식:

```text
queue에서 최소 거리로 확정한 정점의 dist는 최단 거리다.
```

음수 edge가 있으면 나중 경로가 이미 확정한 값을 낮출 수 있어 이 불변식이 깨진다.

## 5. Bellman–Ford

모든 edge를 `V-1`번 relaxation한다.

```text
k번째 반복 뒤에는 시작점에서 edge 수가 최대 k인 모든 경로가 반영된다.
```

단순 최단 경로는 cycle을 제거할 수 있으므로 reachable negative cycle이 없다면 최대 `V-1`개 edge면 충분하다.

추가 한 번의 relaxation에서 값이 줄어들면 시작점에서 도달 가능한 음수 cycle이 있다. 시작점에서 도달할 수 없는 음수 cycle은 single-source 결과에 영향을 주지 않는다.

## 6. Floyd–Warshall

상태:

```text
dist[i][j] = 허용된 중간 정점 집합을 사용한 i→j 최단 거리
```

정점 `k`를 새 중간 후보로 허용한다.

```text
dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])
```

loop 순서에서 `k`가 가장 바깥이어야 해당 상태 의미가 유지된다.

`dist[v][v] < 0`이면 `v`에서 도달할 수 있고 그곳에서 다시 `v`로 돌아올 수 있는
음수 cycle이 존재한다. 그 음수 cycle 자체가 반드시 `v`를 포함하는 것은 아니다.

## 7. overflow와 무한대

도달 불가능을 매우 큰 정수로 표현할 때 두 값을 더해 overflow하지 않게 한다. 가능한 방법:

- nullable distance
- 명시적 infinity 객체
- `dist[u]`가 유한할 때만 덧셈
- 입력 상한으로 안전한 sentinel 계산

## 8. 경로 복원

relaxation에서 값이 실제로 줄어들 때 predecessor를 갱신한다. 음수 cycle이 있으면 최단 경로 자체가 정의되지 않는 정점 집합이 있을 수 있다.

## 9. 작은 동치 검사

작은 graph에서는 Floyd–Warshall 결과를 single-source 후보와 비교한다. Dijkstra와 Bellman–Ford를 서로 기준으로만 비교하면 공통 graph parsing 결함을 놓칠 수 있으므로 입력 validation도 독립적으로 검사한다.

## 연결 실습

[그래프 exercise](../../exercises/04-graphs/README.md)에서 Dijkstra와 Bellman–Ford를 Floyd–Warshall oracle과 비교하고, 도달 가능한 음수 cycle만 오류가 되는 입력을 만든다.

## 완료 기준

- edge 가중치 조건에 따라 BFS·DAG·Dijkstra·Bellman–Ford를 선택한다.
- unreachable, 거리 0, 음수 cycle 영향 상태를 서로 다른 결과로 표현한다.
- relaxation 불변식과 sentinel 덧셈의 안전 범위를 작은 graph에서 확인한다.

## 실패 조건

- 음수 edge가 있는 graph에 Dijkstra를 사용한다.
- stale heap entry를 처리하지 않아 불필요한 확장이 폭증한다.
- unreachable과 거리 0을 같은 값으로 표현한다.
- Bellman–Ford가 도달 불가능한 음수 cycle까지 오류로 처리한다.
- Floyd–Warshall loop 순서를 바꿔 state 의미를 잃는다.
- sentinel 덧셈이 overflow한다.

## 연습

[그래프 exercise](../../exercises/04-graphs/README.md)에서 Dijkstra와 Bellman–Ford를 독립 all-pairs 기준 계산과 비교하고, 도달 가능한 음수 cycle을 거부한다.
