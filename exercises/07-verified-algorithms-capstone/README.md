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
 tests/     고정 경계 사례와 작은 독립 기준 계산
```

## 시작

```sh
cd ../../
scripts/new-workspace.sh exercises/07-verified-algorithms-capstone
cd exercises/07-verified-algorithms-capstone
```

생성 명령은 기존 workspace를 덮어쓰지 않는다. 이미 만든 학습 결과가 있으면 오류로 멈추며 학습자 파일의 보존·backup·삭제는 자동으로 결정하지 않는다.

## 단계

| stage | 함수 |
|---|---|
| `data-structures` | prefix sum, range sum, lower bound, red-black validation |
| `design-techniques` | 0/1 knapsack, interval selection, LCS |
| `graphs` | BFS, Dijkstra, Kruskal, Bellman–Ford, max flow |
| `strings` | KMP |
| `all` | 전체 |

```sh
python3 check.py --impl workspace --stage data-structures --expect pass
```

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
| `max_flow` | 최대 유량 값 | 음수·비정사각 capacity |
| `lcs_length` | LCS 길이 | 빈 문자열 허용 |

## 검사 철학

후보 구현과 다른 계산 방법을 사용한다.

- 직접 합산, 표준 bisect
- Floyd–Warshall
- 부분집합·spanning tree·cut 열거
- 모든 짧은 subsequence
- 레드블랙 규칙 독립 검증

무작위 입력은 고정 시드를 사용한다. 실패를 발견하면 시드를 바꾸기 전에 입력을 최소화하고 regression 사례로 남긴다.

## Skeleton과 결함 fixture

```sh
python3 check.py --impl skeleton --stage all --expect not-implemented
python3 check.py --impl broken/off-by-one --stage data-structures --expect fail
python3 check.py --impl broken/wrong-greedy --stage design-techniques --expect fail
python3 check.py --impl broken/missed-negative-cycle --stage graphs --expect fail
python3 check.py --impl broken/empty-pattern --stage strings --expect fail
EXERCISE_TIMEOUT=1 python3 check.py --impl broken/non-terminating --stage strings --expect timeout
```

검사가 결함 fixture를 통과시키면 구현이 아니라 test가 불충분한 것이다.

## 완료 기준

- stage 순서대로 구현해 workspace의 `all` 검사가 시간 제한 안에 통과한다.
- skeleton 네 stage가 미구현 경계로 실패하고 결함 fixture 다섯 개가 기대 이유로 거부된다.
- reference와 test oracle이 공유하지 않는 계산 경로를 함수군마다 하나 이상 설명한다.

## 자기 설명

- 후보와 reference가 같은 핵심 helper를 공유하면 어떤 공통 결함을 놓칠 수 있는가?
- 비종료 fixture와 잘못된 정답 fixture를 서로 다른 기대 결과로 다뤄야 하는 이유는 무엇인가?

## 검증

저장소 루트에서 전체 checker 계약을 실행한다.

```sh
make checker-check
```
