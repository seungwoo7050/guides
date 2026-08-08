# Slotted page 구현

가변 길이 레코드를 한 페이지에 저장하면서 `(page_id, slot_id)`가 레코드 이동 뒤에도 유지되도록 구현한다.

## 구현할 계약

- 빈 레코드는 거부한다.
- insert는 안정적인 slot ID를 반환한다.
- delete는 slot을 tombstone으로 남긴다.
- compact는 레코드 바이트만 이동하고 slot ID를 바꾸지 않는다.
- update는 공간이 부족하면 페이지를 변경하지 않는다.
- serialize/from_bytes 왕복 뒤에도 동일한 레코드를 읽을 수 있다.

## 시작

```bash
./scripts/new-workspace.sh exercises/02-storage-and-indexes/01-slotted-page
PYTHONPATH=exercises/02-storage-and-indexes/01-slotted-page/workspace \
  python3 -m unittest discover -s exercises/02-storage-and-indexes/01-slotted-page/tests -v
```

문서: [`docs/02-storage-and-indexes/01-pages-records-and-files.md`](../../../docs/02-storage-and-indexes/01-pages-records-and-files.md)
