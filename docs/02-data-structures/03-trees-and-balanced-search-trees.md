# 트리와 균형 탐색 트리

## 학습 목표

- rooted tree의 부모·자식·subtree·깊이·높이를 구분한다.
- DFS 순회 순서가 상태 계산에 미치는 영향을 설명한다.
- BST 순서 불변식과 회전이 보존해야 할 것을 추적한다.
- 레드블랙트리의 색 규칙이 높이를 로그 범위로 제한하는 이유를 설명한다.

## 선행 개념

[순서와 탐색](02-order-search-heaps-and-priority.md), 재귀 호출과 트리의 부모·자식 관계를 설명할 수 있어야 한다.

## 핵심 모델

트리는 순환이 없는 연결 구조라는 성질보다 “하위 문제를 subtree로 분리할 수 있다”는 점이 중요하다.

```text
subtree 결과 → 부모에서 결합
부모 상태 → 자식에게 전달
```

## 1. 기본 용어

- root: 부모가 없는 기준 정점
- parent/child: root 방향의 인접 관계
- depth: root에서 정점까지 간선 수
- height: 정점에서 가장 깊은 leaf까지 간선 수 또는 정한 node 수
- subtree: 한 정점과 모든 descendant
- leaf: child가 없는 정점

높이를 edge 수로 셀지 node 수로 셀지 API에서 정한다.

## 2. 순회와 계산 방향

### preorder

부모를 먼저 처리한다. 경로 상태, 누적 값, 권한처럼 부모 정보가 자식에게 필요한 경우에 적합하다.

### postorder

자식을 먼저 처리한다. subtree 크기, 높이, 균형 여부처럼 하위 결과를 합치는 경우에 적합하다.

### inorder

이진 탐색 트리에서 정렬된 key 순서를 만든다. 일반 트리에는 같은 의미가 없다.

### level order

깊이별 처리와 최소 간선 거리에는 queue 기반 BFS를 사용한다.

## 3. 재귀와 반복 구현

재귀는 subtree 계약을 직접 표현하지만 깊은 편향 트리에서 call stack을 넘을 수 있다. 반복 구현은 명시적 stack에 다음 상태를 저장한다.

```text
현재 node
부모 또는 이전 node
자식 방문 단계
현재 경로 정보
```

postorder를 반복으로 구현할 때는 “처음 진입”과 “자식 처리 후 복귀”를 구분해야 한다.

## 4. BST 불변식

각 node의 key가 `k`라면 다음 범위를 유지한다.

```text
left subtree의 모든 key < k
right subtree의 모든 key > k
```

중복을 허용한다면 어느 쪽에 두는지 또는 count로 합치는지 계약에 포함한다.

탐색 비용은 높이 `h`에 비례한다. 균형이 없으면 `h=n`이 될 수 있다.

## 5. 회전

회전은 local parent-child 관계를 바꾸지만 inorder key 순서를 보존한다.

오른쪽 회전 전:

```text
        y
       / \
      x   C
     / \
    A   B
```

회전 후:

```text
      x
     / \
    A   y
       / \
      B   C
```

`A < x < B < y < C` 순서는 그대로다. 구현은 child뿐 아니라 parent 연결과 root 변경도 갱신해야 한다.

## 6. 레드블랙트리 규칙

일반적인 규칙:

1. 각 node는 red 또는 black이다.
2. root는 black이다.
3. 비어 있는 leaf 경계는 black으로 본다.
4. red node의 child는 black이다.
5. 한 node에서 descendant leaf까지 모든 경로의 black node 수가 같다.

red node가 연속할 수 없고 모든 root-leaf 경로의 black height가 같으므로 가장 긴 경로는 가장 짧은 경로의 두 배를 넘지 않는다. 따라서 높이는 `O(log n)`이다.

## 7. 검증 함수의 계약

레드블랙트리 검증은 한 번의 postorder로 다음을 반환할 수 있다.

```text
subtree가 유효한가?
subtree의 key 범위가 BST 조건을 만족하는가?
왼쪽·오른쪽 black height가 같은가?
현재 node가 red일 때 red child가 없는가?
```

잘못된 트리에서 일부 숫자를 반환하는 것보다 오류를 명시적으로 보고하는 편이 계약이 선명하다.

## 8. 트리 문제의 상태 설계

- subtree 크기: `1 + left + right`
- 높이: `1 + max(left, right)`
- 균형 여부: 높이와 유효 여부를 함께 반환
- 경로 합: 현재까지 합을 자식에게 전달
- lowest common ancestor: 두 target의 발견 상태를 부모에서 결합

같은 subtree를 여러 번 다시 순회하지 않도록 필요한 값을 한 번에 반환한다.

## 연결 실습

[자료구조 exercise](../../exercises/02-data-structures/README.md)에서 레드블랙 검증 함수가 key 범위·색·black height를 한 번의 postorder로 결합하도록 구현한다.

## 완료 기준

- BST 검증에서 부모 비교가 아니라 subtree 전체 허용 범위를 전달한다.
- 회전 전후에 보존되는 inorder 순서와 갱신해야 할 연결을 표시한다.
- 색 규칙 각각을 하나만 깨는 작은 tree를 만들어 검증기가 거부함을 확인한다.

## 실패 조건

- depth와 height의 단위를 섞는다.
- BST 검증에서 부모와의 직접 비교만 하고 전체 범위를 확인하지 않는다.
- 회전 후 parent 또는 root 연결을 놓친다.
- 레드블랙 black height에서 빈 leaf의 규칙이 불명확하다.
- 편향 트리의 재귀 깊이를 고려하지 않는다.

## 연습

[자료구조 exercise](../../exercises/02-data-structures/README.md)에서 레드블랙트리 검증 함수를 작성하고 모든 7-node 색 조합을 독립 검사기와 대조한다.
