# 그래프 표현, 순회와 위상 순서

## 학습 목표

- directed/undirected, weighted/unweighted, simple/multigraph 계약을 구분한다.
- 인접 리스트와 행렬을 `V`, `E`에 따라 선택한다.
- BFS와 DFS의 상태·불변식·실패 조건을 설명한다.
- cycle detection과 topological order를 분리한다.
- component와 SCC의 의미를 구분한다.

## 선행 개념

[선형 자료구조](../02-data-structures/01-linear-structures-ranges-and-hashing.md)의 stack·queue와 집합 표현을 알고 있어야 한다.

## 핵심 모델

그래프 알고리즘은 정점 이름보다 관계의 방향과 간선 계약에서 시작한다.

```text
정점 집합 V
간선 집합 E
방향성
가중치 도메인
중복 간선·자기 루프 허용 여부
연결되지 않은 정점 처리
```

## 1. 표현

### 인접 리스트

공간 `Θ(V+E)`. 한 정점의 이웃 순회에 degree만큼 든다. 희소 그래프의 기본 선택이다.

### 인접 행렬

공간 `Θ(V²)`. 두 정점 사이 간선 존재 여부는 `O(1)`이며 밀집 그래프나 작은 모든 쌍 계산에 적합할 수 있다.

### edge list

모든 간선을 정렬하거나 반복 처리하는 Kruskal, Bellman–Ford에 단순하다.

표현 변경 비용과 중복 간선 병합 규칙도 계약에 포함한다.

## 2. BFS

무가중 그래프에서 시작점으로부터 최소 간선 수를 구한다.

```text
queue에 시작점 삽입
거리[start] = 0
queue에서 꺼낸 정점의 미방문 이웃에 거리+1을 기록하고 삽입
```

불변식:

```text
queue에서 먼저 나오는 정점의 거리는 뒤 정점보다 크지 않다.
처음 거리 값을 받은 순간 그 값은 최단 거리다.
```

방문 표시는 queue에 넣을 때 해야 중복 삽입을 막는다.

비용은 인접 리스트에서 `Θ(V+E)`다.

## 3. DFS

DFS는 한 경로를 끝까지 확장한 뒤 되돌아온다.

사용:

- component 탐색
- cycle detection
- topological order
- subtree 계산
- articulation/bridge 같은 심화 상태

재귀 DFS는 graph 깊이에 따라 stack overflow가 날 수 있다. 반복 구현은 `(vertex, next-neighbor-index)`처럼 복귀 상태가 필요할 수 있다.

## 4. cycle detection

### undirected graph

현재 정점의 parent edge를 제외하고 이미 방문한 이웃을 만나면 cycle이다. multigraph에서는 같은 두 정점 사이 평행 간선이 cycle 정의에 영향을 줄 수 있다.

### directed graph

세 상태를 사용한다.

```text
unseen
active: 현재 DFS stack에 있음
finished
```

active 정점으로 향하는 edge는 back edge이며 directed cycle을 뜻한다.

## 5. 위상 정렬

DAG의 모든 edge `u → v`에 대해 `u`가 `v`보다 앞서는 순서를 구한다.

### Kahn

- indegree 0 정점을 queue에 넣는다.
- 제거하며 이웃 indegree를 감소한다.
- 처리한 정점 수가 `V`보다 작으면 cycle이 있다.

### DFS postorder

cycle 검사를 함께 하고, 정점 종료 순서의 역순을 사용한다.

위상 순서는 일반적으로 하나가 아니다. 결정적인 결과가 필요하면 후보 queue의 tie-break를 정한다.

## 6. component와 SCC

undirected connected component는 서로 경로가 존재하는 최대 정점 집합이다.

directed graph에서 strongly connected component는 서로 양방향 경로가 존재하는 최대 집합이다. SCC를 하나의 정점으로 축약한 condensation graph는 DAG다.

SCC는 단순한 undirected component 계산으로 얻을 수 없다. Kosaraju, Tarjan 같은 별도 알고리즘이 필요하다.

## 7. 경로 복원

거리뿐 아니라 실제 경로가 필요하면 정점을 처음 발견할 때 predecessor를 기록한다.

```text
parent[start] = none
parent[next] = current
```

도착점에서 parent를 따라가 뒤집는다. 도달 불가능 상태와 시작점 상태를 구분한다.

## 연결 실습

[그래프 exercise](../../exercises/04-graphs/README.md)에서 BFS 거리를 구현하고, 범위 밖 정점·도달 불가능·중복 간선 계약을 각각 독립 입력으로 검사한다.

## 완료 기준

- directed/undirected 저장 방식과 `V`, `E` 비용을 입력 계약에 맞춘다.
- BFS 발견 시점과 DFS 회색 상태가 막는 중복·cycle을 trace로 보인다.
- cycle이 있는 입력에서는 부분 위상 순서를 성공 결과로 반환하지 않는다.

## 실패 조건

- directed edge를 양방향으로 저장한다.
- BFS에서 dequeue 시점에 방문 표시해 중복 삽입한다.
- DFS 재귀 깊이를 무시한다.
- directed cycle 검사를 단순 visited 하나로 처리한다.
- cycle이 있는 graph에서 위상 순서 일부를 전체 결과로 반환한다.
- 도달 불가능을 거리 0과 같은 값으로 표현한다.

## 연습

[그래프 exercise](../../exercises/04-graphs/README.md)에서 BFS 거리와 잘못된 정점 인덱스 계약을 구현한다.
