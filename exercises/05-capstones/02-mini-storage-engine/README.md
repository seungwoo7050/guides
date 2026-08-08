# Mini storage engine capstone

앞선 내부구조 연습을 하나의 작은 key-value 저장 엔진으로 통합한다. 페이지에 레코드를 넣고, buffer pool로 캐시하며, B+ tree index로 찾고, WAL을 이용해 crash 뒤 committed insert를 복구한다.

## 완료 계약

- 가변 길이 value를 slotted page에 저장한다.
- `(page_id, slot_id)`가 index의 record identifier다.
- 고정 크기 buffer pool이 dirty page를 교체한다.
- page flush 전에 해당 page LSN까지 WAL이 durable해야 한다.
- 고유 integer key를 B+ tree index에서 찾고 범위 조회한다.
- committed log만 recovery 대상이 된다.
- committed log는 남았지만 data page가 없는 crash를 redo한다.
- uncommitted insert는 recovery 결과에 나타나지 않는다.
- recovery를 반복해도 결과가 달라지지 않는다.

## 실행

```bash
./scripts/new-workspace.sh exercises/05-capstones/02-mini-storage-engine
PYTHONPATH=exercises/05-capstones/02-mini-storage-engine/workspace \
  python3 -m unittest discover -s exercises/05-capstones/02-mini-storage-engine/tests -v
```

설계 지침: [`docs/05-capstones/02-mini-storage-engine.md`](../../../docs/05-capstones/02-mini-storage-engine.md)
