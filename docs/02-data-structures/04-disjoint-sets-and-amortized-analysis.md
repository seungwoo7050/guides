# 분리 집합과 상각 분석

## 학습 목표

- 서로소 집합 자료구조의 상태와 연산 계약을 설명한다.
- union by rank/size와 path compression의 역할을 구분한다.
- aggregate, accounting, potential 방법으로 연산열 비용을 분석한다.
- 한 번의 비싼 연산과 상각 비용을 혼동하지 않는다.

## 선행 개념

[트리 구조](03-trees-and-balanced-search-trees.md), 점근 비용과 여러 연산의 총비용을 구분할 수 있어야 한다.

## 핵심 모델

상각 분석은 입력 확률을 가정하지 않는다. 어떤 허용 연산열에서도 전체 비용이 제한됨을 보인다.

```text
총 실제 비용 <= 연산 수 × 상각 비용 + 초기/최종 potential 차이
```

## 1. 서로소 집합(DSU)

DSU는 원소들이 어떤 연결 component에 속하는지 관리한다.

```text
make_set(x): x만 포함한 집합 생성
find(x): x가 속한 집합의 대표 반환
union(a,b): 두 집합 결합
```

forest로 표현하며 각 root가 대표다.

## 2. union by size/rank

작은 tree의 root를 큰 tree root 아래에 붙이면 높이가 빠르게 증가하지 않는다.

size 기준 불변식:

```text
root의 size는 subtree 원소 수다.
두 집합을 합칠 때 작은 root를 큰 root 아래에 둔다.
새 root의 size는 두 size의 합이다.
```

한 node의 깊이가 증가할 때 그 node가 속한 집합 크기는 최소 두 배가 되므로 path compression이 없어도 깊이는 `O(log n)`이다.

## 3. path compression

`find(x)`가 root까지 올라간 뒤 경로의 모든 node를 root에 직접 연결한다.

```text
find(x):
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]
```

union by rank/size와 함께 사용하면 `m`개 연산의 비용은 매우 느리게 증가하는 inverse Ackermann 함수와 관련된 `O(m α(n))`으로 알려져 있다. 실무 입력에서는 거의 상수처럼 보이지만 이론적으로 “항상 O(1)”이라고 표현하지 않는다.

## 4. aggregate 방법

연산열 전체 비용을 직접 합산한다.

예: 동적 배열이 가득 찰 때 용량을 두 배로 늘린다. `n`번 append 동안 이동 수는 대략 다음과 같다.

```text
1 + 2 + 4 + ... < 2n
```

append 자체 `n`번과 이동을 합쳐 `O(n)`이므로 append 하나의 상각 비용은 `O(1)`이다.

## 5. accounting 방법

싼 연산에 실제 비용보다 큰 가상 비용을 부과하고 credit을 저장해 미래의 비싼 연산을 지불한다.

동적 배열 append에 일정한 credit을 추가로 부과하면 다음 resize 때 이동 비용을 충당할 수 있다. credit이 음수가 되지 않음을 보여야 한다.

## 6. potential 방법

상태 `D`에 potential `Φ(D) >= 0`을 정의한다.

```text
상각 비용 = 실제 비용 + Φ(새 상태) - Φ(이전 상태)
```

연산열을 합하면 중간 potential 변화가 상쇄된다. 초기 potential이 0이고 최종 potential이 음수가 아니면 총 실제 비용은 총 상각 비용보다 크지 않다.

## 7. stack의 multi-pop 예

연산:

- `push(x)`
- `pop()`
- `multipop(k)` 최대 k개 제거

한 번의 `multipop`은 `O(n)`일 수 있다. 그러나 각 원소는 한 번 push되고 최대 한 번 pop되므로 `m`개 연산 전체 비용은 `O(m)`이다.

이 논리는 단조 stack·queue의 선형 시간 분석에도 사용된다.

## 8. DSU가 맞지 않는 경우

DSU는 결합을 되돌리기 어렵다.

- 간선 삭제가 빈번함
- 시간에 따라 연결 상태가 바뀜
- 각 component의 복잡한 경로 질의가 필요함
- 대표가 단순 집합 식별자 이상이어야 함

offline reverse processing, rollback DSU, dynamic connectivity 같은 다른 설계가 필요할 수 있다.

## 연결 실습

[자료구조 exercise](../../exercises/02-data-structures/README.md)에서는 개인 학습 노트로 DSU의 대표·size 불변식을 추적하고 같은 집합 union이 상태를 바꾸지 않는지 확인한다. 실제 DSU 구현은 Part 4의 [그래프 exercise](../../exercises/04-graphs/README.md)에서 `kruskal_mst`와 함께 완성한다.

## 완료 기준

- `find`와 `union` 뒤 각 원소의 대표가 정의되는 방식을 설명한다.
- 단일 연산 최악 비용과 연산열 전체의 상각 비용을 구분한다.
- aggregate·accounting·potential 중 하나로 실제 연산열의 총비용 상한을 계산한다.

## 실패 조건

- 상각 `O(1)`을 한 번의 최악 `O(1)`로 표현한다.
- path compression 중 rank/size를 일반 node에도 의미 있게 유지한다고 가정한다.
- potential이 음수가 될 수 있는데 상한 증명에 사용한다.
- union에서 이미 같은 집합인지 확인하지 않는다.
- DSU로 간선 삭제를 자연스럽게 처리할 수 있다고 가정한다.

## 연습

[자료구조 exercise](../../exercises/02-data-structures/README.md)에서 DSU 불변식과 동적 배열 append의 aggregate 분석을 개인 학습 노트에 작성하고, [그래프 exercise](../../exercises/04-graphs/README.md)의 Kruskal 구현에서 그 불변식을 적용한다.
