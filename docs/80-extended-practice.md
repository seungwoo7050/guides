# 확장 문제와 검증 설계

이 문서는 핵심 경로를 마친 뒤 범위를 넓히기 위한 선택 과정이다. 예전 과정의 고급 문제 가운데 핵심 문서와 중복되지 않으면서 계약·증명·독립 검증을 훈련하는 문제만 남겼다. 문제 수를 채우는 것이 목적이 아니라, 같은 검증 루프를 낯선 조건에 다시 적용하는 것이 목적이다.

## 학습 목표

- 익숙한 알고리즘의 전조건이 바뀌었을 때 상태와 증명을 다시 설계한다.
- 최적값뿐 아니라 해의 존재·유일성·certificate까지 검증한다.
- 작은 입력용 exhaustive oracle, 성질 기반 검사, 상호 독립 구현을 문제에 맞게 선택한다.
- 시간 제한, overflow, 퇴화 입력처럼 정답 외의 실행 계약을 검사한다.

## 선행 개념

필수 Part와 [혼합 검증 capstone](07-mixed-review-and-capstone.md)을 완료하고 실패 입력을 최소화할 수 있어야 한다.

## 핵심 모델

확장 문제 하나를 다음 여섯 칸으로 고정한다.

```text
계약: 입력, 출력, 답 없음, 잘못된 입력, 동점
상태: 미래를 결정하는 최소 정보
정확성: 불변식, 교환, 절단, 귀납 또는 환원
비용: 입력 크기와 표현 길이에 대한 시간·공간
oracle: 후보와 다른 방식으로 계산한 작은 기준
failure: 한 가정만 깨는 최소 입력과 재현 명령
```

처음부터 효율적인 구현을 쓰지 않는다. `n <= 8` 같은 작은 범위에서 가능한 해를 모두 열거할 수 있다면 그 계산을 먼저 고정한다. 이후 최적화 구현과 같은 parser, 같은 정렬 순서, 같은 helper를 공유하지 않게 한다.

## 1. 구간·순서·탐색 확장

### Sliding-window maximum

길이 `k`인 모든 창의 최댓값을 반환한다. 단조 deque에는 값이 아니라 index를 넣어 만료 시점을 판정한다.

- 계약 경계: `k <= 0`, `k > n`, 빈 입력
- 불변식: deque index는 증가하고 해당 값은 감소한다.
- oracle: 각 창을 직접 순회한다.
- 결함 표적: 같은 값이 반복될 때 오래된 index를 잘못 제거하는 구현

### 첫 비반복 원소의 위치

전체 빈도와 첫 위치를 분리한다. streaming 결과인지 전체 입력을 본 뒤의 결과인지 계약을 먼저 정한다.

- oracle: 각 위치의 값을 전체 수열에서 다시 센다.
- 결함 표적: 마지막 위치를 첫 위치처럼 반환하는 map 갱신

### 답에 대한 이분 탐색

작업을 `T`시간 안에 끝낼 수 있는지 판정하는 함수로 최소 시간을 찾는다.

- 판정 함수의 단조성 방향을 먼저 적는다.
- 상한은 답을 반드시 포함하도록 지수적으로 늘릴 수 있다.
- oracle은 작은 범위의 시간을 0부터 순서대로 검사한다.
- `mid`, 누적 생산량, 상한 계산의 overflow를 검사한다.

### 3-way partition과 radix pass

중복이 많은 입력의 quicksort partition과 안정적인 radix pass를 비교한다.

- partition 뒤 `< pivot`, `== pivot`, `> pivot` 구간을 모두 확인한다.
- radix 각 pass 전후 같은 digit의 상대 순서가 유지되는지 record id로 검사한다.
- 정렬 결과는 순서뿐 아니라 원본과 같은 multiset인지 확인한다.

## 2. Tree와 동적 상태 확장

### 회전 검증기

BST subtree를 왼쪽·오른쪽으로 회전한 뒤 다음을 검사한다.

1. inorder key 수열이 보존된다.
2. root와 parent link가 서로 일치한다.
3. subtree 밖 연결이 끊기지 않는다.
4. 저장한 height 또는 size가 모두 다시 계산한 값과 같다.

작은 tree 모양을 생성해 가능한 모든 회전 위치를 적용하고, 회전 전후 inorder와 metadata를 독립 재계산한다.

### Order-statistics tree

각 subtree 크기를 저장해 k번째 원소와 rank를 지원한다.

- `k`의 index 기준을 0 또는 1 중 하나로 고정한다.
- 삽입·삭제·회전마다 size 갱신 경로를 설명한다.
- oracle은 inorder list의 index와 비교한다.
- 중복 key 허용 여부를 계약에 포함한다.

### 삭제가 있는 연결성

DSU만으로 online edge 삭제를 처리하려 하지 않는다. 전체 연산열이 미리 주어지면 시간을 거꾸로 읽어 삭제를 추가로 바꾸는 offline 설계를 검토한다.

- 같은 edge가 여러 번 추가·삭제되는 계약을 정한다.
- 각 시점의 작은 graph를 BFS로 다시 계산한 값을 oracle로 쓴다.
- rollback을 선택하면 변경 stack과 snapshot 경계를 불변식으로 둔다.

## 3. Graph 확장

### 두 번째 spanning tree

MST와 다른 spanning tree 중 최소 가중치를 구한다.

- 같은 가중치의 서로 다른 MST가 있을 때 “두 번째”의 의미를 정한다.
- 작은 graph에서는 모든 `V-1` edge 조합을 열거한다.
- 후보 tree의 연결·acyclic 조건을 가중치 계산 전에 확인한다.

### Bottleneck path

경로에서 가장 큰 edge를 최소화하거나 가장 작은 edge를 최대화하는 두 계약을 구분한다. 일반 최단 거리의 합과 섞지 않는다.

- 작은 simple path를 모두 열거해 bottleneck 값을 계산한다.
- MST 경로 성질을 사용할 때 undirected graph 전조건을 밝힌다.

### 정확히 `K`개 edge를 쓰는 최단 경로

상태를 `(사용한 edge 수, 정점)`으로 둔다. 단순 shortest-path 배열 하나로는 같은 정점의 서로 다른 남은 예산을 구분할 수 없다.

- `dp[k][v]`가 정확히 `k`개인지 최대 `k`개인지 고정한다.
- 음수 edge를 허용하되 edge 수가 유한하므로 상태 graph는 유한하다.
- oracle은 길이 `K`인 walk를 작은 graph에서 모두 열거한다.

### 차분 제약과 arbitrage

부등식 `x_v <= x_u + w`를 edge로 바꾸고 feasible 여부를 음수 cycle로 판정한다. 환율 곱셈은 log 변환 뒤 합으로 바꿀 수 있다.

- 부동소수점 오차와 이익 임계값을 계약에 둔다.
- 도달 가능한 cycle만 볼지 super source로 전체를 볼지 목적에 맞게 정한다.
- 작은 cycle을 직접 열거한 oracle과 비교한다.

## 4. 문자열 확장

### 모든 겹치는 일치

첫 위치 대신 모든 일치 위치를 반환한다. match 뒤 KMP 상태를 0으로 만들면 겹치는 결과를 잃는다.

- 빈 패턴 결과를 위치 `0..n` 또는 오류 중 하나로 고정한다.
- oracle은 모든 시작 위치에서 slice를 직접 비교한다.
- `aaaa`에서 `aa`처럼 겹침이 최대인 입력을 포함한다.

### 최소 주기

prefix function 마지막 값으로 후보 주기를 얻되 문자열 길이가 그 후보로 나누어지는지 확인한다.

- 주기가 반복 횟수 1도 허용하는지 정한다.
- oracle은 가능한 길이를 1부터 시험한다.
- 빈 문자열과 한 문자 계약을 별도로 둔다.

### Streaming KMP

본문이 chunk로 들어와도 pattern 상태를 유지한다. chunk 경계가 일치 결과에 영향을 주면 안 된다.

- 같은 본문을 가능한 모든 두 chunk 분할로 공급한다.
- 전체 본문 한 번 실행 결과와 위치가 같은지 비교한다.
- byte stream과 Unicode text stream의 index 단위를 섞지 않는다.

## 5. Complexity·reduction·flow 확장

### Certificate를 반환하는 알고리즘

값만 반환하던 함수가 실제 선택 집합이나 경로도 반환하게 한다. 검증기는 답을 다시 최적화하지 않고 다음을 확인한다.

- certificate 크기가 입력 크기의 다항식이다.
- 원본 입력의 제약을 만족한다.
- 선언한 값과 certificate에서 계산한 값이 같다.
- 최적성은 작은 oracle 또는 별도의 bound로 확인한다.

### Vertex splitting

정점 capacity가 있는 flow 문제에서 각 정점을 `v_in -> v_out`으로 나눈다. 원본 edge가 어느 방향의 새 정점을 연결하는지 표로 만든다.

- source와 sink도 분할할지 정한다.
- 무한 capacity sentinel은 가능한 총 flow보다 크고 overflow하지 않아야 한다.
- 원본 경로와 변환 network flow의 양방향 대응을 설명한다.

### Lower-bound circulation

각 edge의 lower bound를 먼저 보내고 정점 demand를 계산해 feasible circulation 문제로 바꾼다.

- `0 <= lower <= upper`를 입력에서 검증한다.
- demand 부호와 super source/sink edge 방향을 작은 예로 추적한다.
- 반환 flow를 원래 lower/upper와 conservation으로 다시 검사한다.

### König 대응

이분 graph의 maximum matching과 minimum vertex cover 크기가 같다는 구조를 이용한다.

- matching 결과에서 alternating reachability를 구성한다.
- 만든 cover가 모든 edge를 덮는지 독립 검사한다.
- 작은 graph의 모든 vertex subset을 열거해 최소 cover 크기와 비교한다.

## 6. Legacy challenge catalog

다음 catalog는 이전 과정의 문제 이름만 보존한 목록이 아니다. 핵심 문서에 완전히 흡수되지 않은 계약 변형과 제출 증거를 한 줄씩 고정한다. 앞 절에서 자세히 다룬 challenge와 겹치는 항목은 생략했다.

### 문제 계약과 선형 상태

| Challenge | 고유 조건 | 제출 증거 |
|---|---|---|
| 목표 합의 첫 위치 쌍 | 같은 원소 재사용 금지, 여러 답의 tie-break | `O(n²)` oracle과 최초 index map 비교 |
| 서로 다른 값 `K`개 이하인 최장 구간 | 빈 구간·`K=0`, left 이동 뒤 빈도 제거 | 모든 구간 열거와 양끝 trace |
| 중복 없는 방문 기록 | 입력 순서 보존과 membership 분리 | set 없이 만든 선형 oracle |
| 단조 증가 구간의 경계 | strict/non-strict 증가 계약 분리 | 같은 값이 연속되는 최소 반례 |
| 괄호 오류 위치 | 잘못 닫힘과 입력 종료 시 미닫힘 구분 | stack 상태와 최초 오류 index |
| 작업실의 다음 완료 시각 | 동일 시각 작업의 결정적 순서 | 작은 event simulation oracle |
| 가장 가까운 두 수 | 동일 값·복수 최소 차이 tie-break | 모든 쌍 열거와 정렬 scan 비교 |

### 분석·상각·정렬

| Challenge | 고유 조건 | 제출 증거 |
|---|---|---|
| 역전 쌍의 수 | 같은 값은 inversion이 아님 | 이중 loop와 merge 계수 비교 |
| 분할 정복 최대 부분 배열 | 빈 결과 허용 여부, 음수만 있는 입력 | 모든 구간 합 oracle |
| 빠른 모듈러 거듭제곱 | 음수 지수 거부, 곱셈 전 modulo | 지수 감소식과 작은 반복 oracle |
| Fibonacci 호출 폭발 | 함수 호출 수와 산술 결과 비용 분리 | 호출 tree 점화식 전개 |
| Euclid 종료와 비용 | 나머지의 strict 감소 | 연속 Fibonacci 입력 trace |
| 두 stack queue | 한 번의 이동은 선형, 연산열은 선형 | 각 원소 이동 횟수 회계 |
| 두 배 확장 동적 배열 | capacity와 size 구분 | 실제 복사 횟수 합계 |
| binary counter | 한 increment의 최악과 전체 flip 수 구분 | bit별 flip 횟수 표 |
| 축소 정책 재할당 진동 | grow/shrink 임계값 간 여유 | 진동을 만드는 push/pop 입력 |
| 정렬 block 병합 | 원소가 참여하는 병합 단계 수 | binary counter와의 potential 대응 |
| 거의 정렬된 입력의 insertion sort | inversion 수에 민감한 비용 | shift 횟수와 inversion 수 비교 |
| 여러 key의 안정 정렬 | 낮은 우선순위 key부터 stable pass | 원래 record id 순서 검사 |

### 균형 tree와 spanning structure

| Challenge | 고유 조건 | 제출 증거 |
|---|---|---|
| 삽입 가능한 red-black set | recolor와 rotation 뒤 모든 규칙 복원 | 각 삽입 prefix를 독립 validator로 검사 |
| 일반 BST 최악 높이 | 삽입 순서와 tree 높이의 관계 | 정렬·역순·무작위 순서 비교 |
| key 구간 출력 | 출력 크기 `k`를 비용에 포함 | inorder filter oracle과 `O(h+k)` 설명 |
| red-black 삭제 | double-black 상태와 sentinel 색 | 삭제마다 전체 규칙 재검증 |
| minimum/maximum spanning forest | disconnected 결과가 forest임 | component별 tree와 모든 조합 비교 |
| 이미 연결된 도로망 확장 | 기존 연결은 비용 0 union으로 반영 | super-node 또는 선행 union 대응 |

### 경로·문자열·복잡도

| Challenge | 고유 조건 | 제출 증거 |
|---|---|---|
| 음수 cycle 영향을 표시하는 거리 | cycle에서 도달 가능한 정점만 `-∞` | relaxation 후보에서 추가 reachability |
| DAG 최단 경로 복원 | 음수 edge 허용, cycle 입력 거부 | topological order와 predecessor trace |
| Floyd–Warshall 경로 복원 | `next` 갱신과 도달 불가능 구분 | 복원 경로의 edge 합 재계산 |
| 검증을 포함한 Rabin–Karp | hash 일치 뒤 실제 문자 확인 | 인위적 충돌 또는 작은 modulus fixture |
| 문자열 회전 판정 | 길이 같음 전제와 빈 문자열 | 직접 가능한 모든 rotation oracle |
| 모든 border 길이와 등장 횟수 | border chain과 prefix 빈도 누적 | 모든 prefix/suffix 직접 비교 |
| Vertex Cover verifier | 최적성을 다시 풀지 않고 cover만 검증 | 모든 edge coverage와 certificate 크기 |
| 3-SAT에서 Clique | clause마다 한 정점, 모순 literal edge 제외 | satisfying assignment와 clique 양방향 |
| Independent Set–Vertex Cover | 같은 graph에서 complement 관계 | 두 certificate의 크기 합 `|V|` 검사 |
| Subset Sum pseudo-polynomial DP | 숫자 값과 입력 bit 길이 분리 | `O(nT)`가 bit 길이 다항식이 아님을 설명 |
| optimization과 decision oracle | threshold 질의 횟수와 해 복원 | 이분 탐색 및 self-reduction 호출 기록 |

### Flow 결과 복원

| Challenge | 고유 조건 | 제출 증거 |
|---|---|---|
| 최대 유량과 최소 cut 복원 | residual reachable 집합으로 cut 구성 | cut capacity와 flow 값 비교 |
| 최대 bipartite matching | 두 partition 검증과 unit capacity | 선택 edge가 정점 중복 없이 연결됨 |
| 최소 bipartite vertex cover | alternating path에서 cover 복원 | 모든 edge coverage와 matching 크기 비교 |
| 최대 edge-disjoint path | 원본 edge capacity 1 | 복원 path가 edge를 공유하지 않음 |

Catalog 항목은 완성 코드 수를 늘리기 위한 과제가 아니다. 각 표에서 challenge 하나를 고를 때 고유 조건과 제출 증거를 함께 만족해야 완료로 센다.

## 연결 실습

자료구조 문제는 [자료구조 exercise](../exercises/02-data-structures/README.md), graph·flow 문제는 [그래프 exercise](../exercises/04-graphs/README.md), 문자열 문제는 [문자열 exercise](../exercises/05-strings/README.md)의 계약과 실행 방식을 재사용한다. 새 함수는 [검증 capstone](../exercises/07-verified-algorithms-capstone/README.md)의 stage를 임의로 늘리지 말고 별도 disposable 실험에서 먼저 검증한다.

## 완료 기준

- 서로 다른 영역에서 문제 세 개를 골라 계약·정확성·비용·oracle을 모두 작성한다.
- 각 문제에 정상·경계·잘못된 입력과 의도적 결함을 한 개 이상 만든다.
- 고정 시드 또는 완전 열거 범위를 기록해 다른 사람이 같은 실패를 재현한다.
- 최적화 구현과 독립 기준 계산이 parser·핵심 helper·상태 전이를 공유하지 않음을 검토한다.

## 실패 조건

- 문제 이름을 보고 core 알고리즘을 그대로 적용하면서 바뀐 전조건을 적지 않는다.
- 후보 구현의 출력만 snapshot으로 저장해 잘못된 결과를 oracle로 고정한다.
- exhaustive 검사의 입력 상한이 없어 검증 자체가 종료하지 않는다.
- 값만 맞으면 잘못된 certificate, overflow, timeout을 성공으로 취급한다.
- 여러 문제를 풀었지만 최소 반례와 실패 원인을 하나도 보존하지 않는다.

## 연습

다음 순서로 한 문제를 완료한다.

1. 효율적인 풀이를 보지 않고 작은 oracle의 입력 상한을 정한다.
2. 계약과 실패 결과를 표로 쓴다.
3. 의도적 결함 구현 하나를 만들고 oracle이 거부하는 최소 입력을 찾는다.
4. 후보 구현을 작성해 작은 입력 공간 또는 고정 시드 표본과 비교한다.
5. 입력 크기를 키워 timeout 상한 안에서 종료하는지 확인한다.
6. 구현을 닫고 정확성 근거와 비용을 다시 설명한다.
