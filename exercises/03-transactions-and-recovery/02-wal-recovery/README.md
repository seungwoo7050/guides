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

## 목표

LSN, durable boundary, page LSN과 transaction 상태를 사용해 redo/undo의 대상과 순서를 구현한다.

## 완료 기준

- WAL이 durable하지 않은 page write는 거부되고 flush 뒤 같은 write는 성공한다.
- committed update는 redo되며 commit 없는 update는 역순 undo되어 이전 값이 복원된다.
- 여러 transaction의 로그를 섞고 recovery를 두 번 실행해도 page bytes와 LSN이 동일하다.

## 자기 설명

1. redo가 `record.lsn > page_lsn`인 record만 적용해야 멱등성이 생기는 이유는 무엇인가?
2. 같은 page의 미완료 update를 로그 정순이 아니라 역순으로 undo해야 하는 이유는 무엇인가?

## 검증

workspace 테스트와 `make python-check`를 실행해 WAL 선행 규칙 및 반복 recovery를 함께 확인한다.
