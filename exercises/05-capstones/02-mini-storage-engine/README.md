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
- recovery 뒤 transaction ID는 durable WAL의 최대 ID 다음에서 재개되어 과거 `COMMIT`과 충돌하지 않는다.

## 실행

```bash
./scripts/new-workspace.sh exercises/05-capstones/02-mini-storage-engine
PYTHONPATH=exercises/05-capstones/02-mini-storage-engine/workspace \
  python3 -m unittest discover -s exercises/05-capstones/02-mini-storage-engine/tests -v
```

설계 지침: [`docs/05-capstones/02-mini-storage-engine.md`](../../../docs/05-capstones/02-mini-storage-engine.md)

## 목표

append-only heap, buffer pool, ordered index와 truncate하지 않은 WAL을 연결해 auto-commit insert와 crash recovery를 구현한다.

## 완료 기준

- 여러 page에 insert한 key의 point/range 결과와 index RID가 실제 live record를 가리킨다.
- WAL보다 앞선 dirty page flush가 거부되고 committed WAL만으로 data page가 없어도 redo된다.
- disk까지 도달한 미완료 insert가 recovery에서 제거되고 다음 transaction ID가 durable max+1로 재개된다.

## 자기 설명

1. 이 축소 구현이 WAL 전체로 heap을 재구성하기 때문에 log truncation을 지원하지 못하는 이유는 무엇인가?
2. recovery 뒤 index를 WAL로 직접 복구하지 않고 heap에서 rebuild했을 때 얻는 단순성과 비용은 무엇인가?

## 검증

workspace 테스트와 `make python-check`를 실행해 WAL ordering, crash 경계, 반복 recovery를 모두 확인한다.
