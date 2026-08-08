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
