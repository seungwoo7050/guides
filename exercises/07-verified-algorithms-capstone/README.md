# 07. 검증 가능한 알고리즘 capstone

이 capstone은 완성 예제를 복사하는 문제가 아니다. 공개 API와 test oracle을 제공하고 학습자가 `workspace/algorithms.py`를 직접 구현한다.

## 목표

동일한 공개 API를 학습자 구현·reference·의도적 결함으로 실행해 구현과 test의 품질을 함께 증명한다.

## 디렉터리

```text
skeleton/   공개 함수와 TODO
workspace/  학습자 구현, Git 추적 제외
reference/  전체 계약을 만족하는 비교 구현
broken/     test 품질을 확인하는 의도적 결함
tests/      고정 경계 사례와 작은 독립 기준 계산
```

## 시작

저장소 루트에서 실행한다.

```sh
scripts/new-workspace.sh exercises/07-verified-algorithms-capstone
```

생성 명령은 기존 workspace를 덮어쓰지 않는다. 이미 만든 학습 결과가 있으면 오류로 멈추며 학습자 파일의 보존·backup·삭제는 자동으로 결정하지 않는다.

직접 수정하는 파일은 `workspace/algorithms.py`뿐이다. `skeleton/`은 read-only 시작 계약이며 `reference/`, `tests/`, `broken/`, `check.py`는 learner 수정 위치가 아니다.

## 단계

| stage | 함수 |
|---|---|
| `data-structures` | prefix sum, range sum, lower bound, red-black validation |
| `design-techniques` | 0/1 knapsack, interval selection, LCS |
| `graphs` | BFS, Dijkstra, Kruskal, Bellman–Ford, max flow |
| `strings` | KMP |
| `all` | 전체 |

```sh
make stage-check STAGE=data-structures
```

checker stage는 선택한 함수군만 검사하며 이전 stage를 자동 재실행하지 않는다. 구현은 같은 workspace에 누적하고, 각 함수군을 마친 뒤 마지막으로 다음 전체 회귀를 실행한다.

```sh
make stage-check STAGE=all
```

`make stage-check`는 learner-owned `workspace`를 기본으로 선택한다. workspace가 없으면 reference로 대신 성공하지 않고 위 생성 명령을 안내하며 실패한다.

## 공개 API

| 함수 | 결과 | 주요 실패 |
|---|---|---|
| `prefix_sums`, `range_sum` | 반열린 구간 합 | 범위 오류 |
| `lower_bound` | 첫 삽입 위치 | 정렬은 호출자 전조건 |
| `bfs_distances` | 최소 edge 수 | 잘못된 정점 |
| `dijkstra` | nonnegative shortest paths | 음수 edge |
| `knapsack_01` | 최대 가치 | 음수 capacity, nonpositive weight |
| `select_intervals` | 최대 호환 구간 집합 | 잘못된 구간 |
| `red_black_height` | black height | 색·BST·red-red·height 위반 |
| `kruskal_mst` | MST 가중치와 edge | disconnected graph |
| `bellman_ford` | shortest paths | reachable negative cycle |
| `kmp_find` | 첫 일치 위치 | 빈 패턴은 0 |
| `max_flow` | 최대 유량 값과 directed flow matrix | 음수·비정사각 capacity |
| `lcs_length` | LCS 길이 | 빈 문자열 허용 |

## 기준 구현 읽기 순서

이 capstone의 annotation scope는 `reference/algorithms.py` 전체 하나다. 아래 번호는 source line, runtime 호출, checker stage 또는 실제 Git 작성 이력이 아니라 **학습을 위한 권장 구현 순서**다. 파일마다 번호를 다시 시작하지 않는다.

먼저 workspace의 `all` 검사를 통과시킨다. 그 뒤 이 표와 reference source의 `Implementation N` 주석을 함께 읽으며 자신의 상태 owner, 불변식과 실패 처리를 비교한다.

| 권장 순서 | 기준 구현 symbol | 먼저 고정하는 책임과 다음 연결 |
|---:|---|---|
| 1 | `prefix_sums`, `range_sum` | 첫 0 sentinel이 있는 누적 상태와 반열린 구간 계약을 고정한 뒤 탐색 경계로 이동 |
| 2 | `lower_bound` | 호출자의 정렬 전조건과 `[lo,hi)` 후보 구간·종료 상태를 고정 |
| 3 | `RedBlackNode`, `red_black_height` | node가 소유하는 key·color·child, subtree에 전달하는 BST bound와 반환하는 black height를 연결 |
| 4 | `knapsack_01` | 처리한 item까지의 최적값을 각 `best[c]`가 소유하고 역순 갱신으로 재사용을 막음 |
| 5 | `select_intervals` | earliest-finish frontier, 결정적 tie-break와 잘못된 interval 실패를 고정 |
| 6 | `lcs_length` | 두 prefix 사이의 LCS를 row가 소유하고 짧은 축으로 공간을 제한 |
| 7 | `_validate_vertex`, `bfs_distances` | graph 공통 입력 경계와 `None`인 미방문 거리, queue의 최초 거리 확정을 연결 |
| 8 | `dijkstra` | edge iterable을 adjacency가 소유하는 시점, nonnegative 전조건과 stale heap entry 제거를 고정 |
| 9 | `_DisjointSet`, `kruskal_mst` | component 대표·size와 chosen-edge certificate를 연결하고 disconnected 실패를 고정 |
| 10 | `bellman_ford` | 반복 가능한 edge 상태, edge 수별 relaxation 불변식과 reachable negative cycle 실패를 고정 |
| 11 | `max_flow` | directed flow certificate, residual cancellation, augmenting path와 conservation을 연결 |
| 12 | `kmp_find` | proper-prefix table의 상태, mismatch fallback과 빈 pattern 계약을 고정 |

application framework, dependency 또는 package bootstrap이 없으므로 이 scope에는 Implementation 0이 없다. workspace 생성과 `check.py` 실행은 구현 번호가 아니라 학습·검증 workflow이며 migration·codegen 같은 중간 CLI도 없다.

## 검사 철학

후보 구현과 다른 계산 방법을 사용한다.

- 직접 합산, 표준 bisect
- Floyd–Warshall
- 부분집합·spanning tree·cut 열거
- 모든 짧은 subsequence
- 레드블랙 규칙 독립 검증

무작위 입력은 고정 시드를 사용한다. 실패를 발견하면 시드를 바꾸기 전에 입력을 최소화하고 regression 사례로 남긴다.

`max_flow`는 `(value, flow)`를 반환한다. `flow[u][v]`는 원본 directed edge
`u→v`에 보낸 nonnegative 정수이며 `0 <= flow[u][v] <= capacity[u][v]`를
만족한다. 중간 정점의 유입과 유출은 같고 source의 순유출 및 sink의 순유입은
`value`와 같아야 한다.

## Skeleton과 결함 fixture

```sh
make checker-check
```

검사가 결함 fixture를 통과시키면 구현이 아니라 test가 불충분한 것이다.
루트 `make checker-check`는 여기에 더해 interval 동점, MST edge certificate와
max-flow certificate를 각각 깨뜨린 임시 semantic mutant도 거부한다.

known-bad의 실패는 `ImportError`, `SyntaxError`, `NotImplementedError` 같은 infrastructure 오류가 아니라 각 fixture가 겨냥한 contract assertion이어야 한다.

workspace의 `all` 통과 뒤 reference baseline과 quality fixture를 확인한다. 아래 명령도 저장소 루트에서 실행한다.

```sh
make reference-check
make checker-check
```

`make checker-check`는 repository-owned baseline의 방향성을 확인하며 learner workspace의 완료 판정을 대신하지 않는다.

## 완료 기준

- stage 순서대로 구현해 workspace의 `all` 검사가 시간 제한 안에 통과한다.
- skeleton 네 stage가 미구현 경계로 실패하고 결함 fixture 다섯 개가 기대 이유로 거부된다.
- 실패한 최소 입력·깨진 계약·수정·회귀 expected result를 저장소 밖 개인 학습 노트에 보존한다.
- workspace 완료 뒤 reference와 test oracle이 공유하지 않는 계산 경로를 함수군마다 하나 이상 설명한다.

## 자기 설명

- 후보와 reference가 같은 핵심 helper를 공유하면 어떤 공통 결함을 놓칠 수 있는가?
- 비종료 fixture와 잘못된 정답 fixture를 서로 다른 기대 결과로 다뤄야 하는 이유는 무엇인가?

## 검증

저장소 루트에서 전체 checker 계약을 실행한다.

```sh
make checker-check
```
