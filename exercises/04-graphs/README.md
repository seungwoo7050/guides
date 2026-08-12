# 04. 그래프

## 목표

graph 입력 전조건, 최적화 불변식, 오류 결과를 독립 oracle과 함께 구현한다.

## 구현 대상

- `bfs_distances`
- `dijkstra`
- `kruskal_mst`
- `bellman_ford`
- `max_flow`

위상 순서·SCC·이분 매칭은 현재 checker stage의 별도 공개 함수가 아니다. 개인 학습 노트에 directed cycle을 거부하는 위상 정렬 trace, SCC의 양방향 reachability 근거, matching을 unit-capacity flow로 옮기는 정점·edge 대응을 기록한다.

## 공통 계약

- 정점은 `0..vertex_count-1`다.
- 범위 밖 정점은 `ValueError`다.
- 도달 불가능 거리는 `None`이다.
- 입력 iterable은 구현에서 한 번만 순회될 수 있으므로 필요하면 내부 list로 고정한다.

## 세부 계약

- Dijkstra는 음수 edge를 거부한다.
- Bellman–Ford는 시작점에서 도달 가능한 음수 cycle을 `ValueError`로 보고한다.
- Kruskal은 연결되지 않은 graph를 거부하고 `(total_weight, chosen_edges)`를 반환한다.
- 최대 유량은 정사각 nonnegative capacity matrix를 요구하고 `(value, flow)`를
  반환한다. `flow[u][v]`는 원본 `u→v` capacity 안의 directed flow다.

## 독립 기준

- shortest path: Floyd–Warshall
- MST: `V-1`개 edge 조합 열거
- max flow: 모든 source-side cut 열거

## 실행

```sh
make stage-check STAGE=graphs
```

## 결함 분석

`broken/missed-negative-cycle`은 음수 cycle 검출을 무시한다. 단순 distance 사례는 통과할 수 있으므로 오류 계약을 별도로 검사해야 한다.

## 완료 기준

- BFS·Dijkstra·Bellman–Ford가 정점 범위와 도달 불가능 표현을 일관되게 처리한다.
- Kruskal 결과가 작은 graph의 모든 spanning tree 중 최소이며 disconnected 입력을 거부한다.
- 최대 유량 값이 작은 network의 최소 cut과 같고, 반환 flow가 capacity와
  conservation을 만족하며, 잘못된 capacity matrix를 거부한다.
- 자동 stage 밖의 위상 순서·SCC·matching 계약을 개인 학습 노트의 trace 또는 certificate로 검토한다.

## 자기 설명

- Dijkstra가 확정한 정점의 거리를 다시 줄일 수 없게 하는 가중치 전조건은 무엇인가?
- 최대 유량 검사에서 값 외에 capacity와 conservation을 별도로 확인해야 하는 이유는 무엇인가?

## 검증

```sh
make stage-check STAGE=graphs
```

workspace의 `all` 통과 뒤 repository-owned negative-cycle 결함 방향은 루트 `make checker-check`로 확인한다.
