# WAL과 crash recovery 구현

데이터 페이지보다 로그를 먼저 영속화하고, 재시작 시 committed transaction은 redo하고 미완료 transaction은 undo한다.

## 구현할 계약

- update log는 before/after image와 증가하는 LSN을 가진다.
- `Disk.write()`는 page LSN까지 로그가 flush되지 않았으면 거부한다.
- recovery는 page LSN보다 새로운 update만 redo한다.
- commit record가 없는 transaction은 로그 역순으로 undo한다.
- 같은 로그로 recovery를 반복해도 최종 상태가 바뀌지 않는다.
- 여러 transaction이 같은 페이지를 변경한 경우에도 commit 여부를 보존한다.

## 실행

```bash
./scripts/new-workspace.sh exercises/03-transactions-and-recovery/02-wal-recovery
PYTHONPATH=exercises/03-transactions-and-recovery/02-wal-recovery/workspace \
  python3 -m unittest discover -s exercises/03-transactions-and-recovery/02-wal-recovery/tests -v
```

문서: [`docs/03-transactions-and-recovery/02-mvcc-wal-and-recovery.md`](../../../docs/03-transactions-and-recovery/02-mvcc-wal-and-recovery.md)
