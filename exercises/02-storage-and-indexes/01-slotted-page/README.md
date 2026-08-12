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

## 목표

slot directory와 record 영역을 분리해 가변 길이 bytes가 이동해도 논리 RID가 안정적으로 남는 페이지를 구현한다.

## 완료 기준

- 서로 다른 크기의 record를 넣고 읽었을 때 key와 bytes가 손실 없이 돌아온다.
- delete와 compact 뒤 live record의 기존 slot ID가 바뀌지 않는다.
- 공간 부족 update와 손상된 serialized page가 부분 변경 없이 명시적 예외로 끝난다.

## 자기 설명

1. slot ID 대신 byte offset을 RID로 노출하면 compaction이 어떤 상위 계층을 깨뜨리는가?
2. header·slot directory·record 영역이 서로 겹치지 않음을 어떤 경계식으로 증명하는가?

## 권장 구현 순서

아래 번호는 `reference/slotted_page.py` project 전체의 권장 construction order다. 과거 이력이 아니며 file-local 번호가 아니다. 먼저 workspace를 통과시킨 뒤 reference의 authoritative 주석과 비교한다.

| 순서 | 파일·symbol | 책임 |
|---:|---|---|
| 1 | binary format constants | header와 slot encoding |
| 2 | `Slot`, `SlottedPage` | 논리 slot과 page-owned boundary |
| 3 | `_validate_payload`, `_slot` | mutation 전 입력·수명 검증 |
| 4 | `insert` | capacity preflight, compaction, slot reuse |
| 5 | read/update/delete lifecycle | stable slot ID와 record rebuild |
| 6 | `serialize` | memory state를 page layout으로 고정 |
| 7 | `from_bytes` | untrusted page boundary 검증 |

## 검증

학습자 workspace를 공용 테스트에 직접 연결한다.

```bash
./scripts/check-workspace.sh exercises/02-storage-and-indexes/01-slotted-page
```

초기 skeleton은 `GUIDE_SEMANTIC:slotted-page-insert`에서 실패하고, 구현 후 같은 명령이 통과해야 한다. `make python-check`는 배포본 자체의 reference/skeleton 계약을 검사한다.
