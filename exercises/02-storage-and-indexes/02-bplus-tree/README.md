# B+ tree 구현

정렬된 키를 내부 노드와 leaf에 나누어 저장하고, leaf 연결을 이용해 범위 질의를 수행한다.

## 구현할 계약

- `insert(key, value)`는 유일 키를 삽입하고 기존 키는 값을 교체한다.
- 노드가 넘치면 leaf와 internal node를 서로 다른 규칙으로 분할한다.
- internal separator는 오른쪽 subtree의 최소 키를 나타낸다.
- 모든 값은 leaf에만 존재한다.
- leaf의 `next` 연결로 범위 질의를 정렬 순서대로 반환한다.
- `validate()`가 key 정렬, 자식 수, 높이와 leaf 연결을 확인한다.

## 실행

```bash
./scripts/new-workspace.sh exercises/02-storage-and-indexes/02-bplus-tree
PYTHONPATH=exercises/02-storage-and-indexes/02-bplus-tree/workspace \
  python3 -m unittest discover -s exercises/02-storage-and-indexes/02-bplus-tree/tests -v
```

문서: [`docs/02-storage-and-indexes/02-index-structures.md`](../../../docs/02-storage-and-indexes/02-index-structures.md)

## 목표

leaf와 internal node의 서로 다른 split 규칙을 보존하면서 point lookup과 연결 leaf range scan을 구현한다.

## 완료 기준

- 삽입 순서가 달라도 모든 key를 찾고 기존 key 갱신은 중복 entry를 만들지 않는다.
- leaf와 internal split 뒤 `validate()`가 동일 높이, separator, 자식 수 불변식을 통과한다.
- 경계가 포함된 range 결과가 leaf 여러 개를 넘어도 오름차순으로 정확히 반환된다.

## 자기 설명

1. internal separator를 왼쪽 최대가 아닌 오른쪽 subtree 최소로 정의했을 때 탐색 비교는 어떻게 달라지는가?
2. range scan이 root를 매번 다시 탐색하지 않도록 leaf 연결이 제공하는 이점은 무엇인가?

## 검증


```bash
./scripts/check-workspace.sh exercises/02-storage-and-indexes/02-bplus-tree
```

초기 skeleton은 `GUIDE_SEMANTIC:bplus-tree-insert`에서 실패하고, leaf/internal split과 range scan을 완성하면 같은 workspace 검사가 통과해야 한다.
