# 페이지, 레코드와 파일 구성

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 한다.

- DBMS가 tuple을 개별 파일 조각이 아니라 고정 크기 page 단위로 읽고 쓰는 이유
- 가변 길이 record를 slotted page에 배치하는 방법
- `(page_id, slot_id)`가 record identifier로 유용한 이유
- delete·update·compaction이 slot 안정성에 미치는 영향
- heap file과 sorted file의 읽기·쓰기 trade-off
- page layout 손상이 왜 index와 transaction 계층까지 전파되는지

## 선행지식

관계의 tuple과 key 개념을 알아야 한다. 내부구조 경로라면 [`관계 모델`](../01-relational-semantics-and-design/01-relational-model-and-algebra.md)을 먼저 읽는다.

## 저장장치는 page 단위 비용을 만든다

애플리케이션은 row 하나를 읽는다고 생각하지만 DBMS는 보통 page 단위로 저장장치와 메모리 사이를 이동한다. page 크기는 시스템마다 다르지만 핵심 계약은 같다.

```text
논리 tuple
→ record encoding
→ page 안의 slot
→ file 안의 page
→ storage block과 I/O
```

한 byte만 필요해도 그 byte가 들어 있는 page를 읽어야 할 수 있다. 따라서 다음이 성능에 영향을 준다.

- 한 page에 몇 record가 들어가는가
- 함께 읽는 record가 가까이 있는가
- update가 record를 page 밖으로 밀어내는가
- scan이 연속 page를 읽는가
- index가 heap page를 얼마나 흩어져 방문하는가

page는 단순한 구현 세부가 아니라 비용 모델의 기본 단위다.

## 고정 길이와 가변 길이 record

모든 field가 고정 길이면 offset 계산이 단순하다.

```text
record 0: base + 0 * record_size
record 1: base + 1 * record_size
```

현실의 row에는 text, nullable field와 variable-length value가 있다. record마다 길이가 달라지면 단순한 배열 배치로는 delete와 update가 어렵다.

record encoding에는 보통 다음 정보가 필요하다.

- null bitmap
- 고정 길이 field
- 가변 길이 field의 offset 또는 length
- record header
- transaction visibility metadata

이 문서의 연습은 전체 SQL row format을 복제하지 않고, 가변 길이 byte record와 안정적인 slot ID에 집중한다.

## Slotted page

slotted page는 page 앞쪽에 header와 slot directory를 두고, record byte는 뒤쪽에서 역방향으로 쌓는 대표 구조다.

```text
낮은 offset
┌──────────────────────────────┐
│ page header                  │
├──────────────────────────────┤
│ slot 0: offset, length       │
│ slot 1: offset, length       │
│ ...                          │
├──────── free space ──────────┤
│ record bytes                 │
│ record bytes                 │
└──────────────────────────────┘
높은 offset
```

slot은 record의 현재 byte 위치를 가리킨다. 외부에서는 record를 `(page_id, slot_id)`로 참조한다.

### 왜 byte offset을 직접 식별자로 사용하지 않는가

page compaction은 record byte를 이동시킨다. offset을 외부 식별자로 사용하면 모든 index entry와 참조를 갱신해야 한다. slot ID를 안정적으로 유지하고 slot의 offset만 바꾸면 외부 record identifier는 그대로다.

```text
이전: slot 3 → offset 220
compaction 뒤: slot 3 → offset 180
외부 RID: (page 17, slot 3) 그대로
```

이 간접 참조가 slotted page의 핵심 가치다.

## Insert 계약

insert는 다음 순서로 판단한다.

1. payload가 format에 맞는가
2. 새 slot directory entry가 필요한가
3. 총 free space가 충분한가
4. free space가 흩어졌다면 compaction으로 연속 공간을 만들 수 있는가
5. 실패할 경우 page를 변경하지 않는가

free space는 단순히 `page_size - record_bytes`가 아니다.

```text
free space = free_end - directory_end
```

새 slot을 추가하면 directory도 커진다. tombstone slot을 재사용하면 directory 비용을 줄일 수 있다.

insert 실패 후 header, slot directory나 record byte가 반쯤 바뀌면 page가 손상된다. 공간 확인과 실제 변경 순서를 분리해야 한다.

## Delete와 tombstone

delete 때 slot을 즉시 제거하고 뒤 slot 번호를 당기면 RID가 바뀐다. 보통 slot을 tombstone으로 남긴다.

```text
slot 0 → live
slot 1 → deleted
slot 2 → live
```

이후 insert가 deleted slot을 재사용할 수 있다. 그러나 재사용 시 이전 RID를 오래 보관한 외부 참조가 새 record를 가리키는 ABA 문제가 생길 수 있다. 실제 시스템은 page generation, transaction visibility, index 정리 같은 추가 계약으로 이를 다룬다. 교육용 exercise는 slot 안정성과 tombstone 재사용까지만 다룬다.

## Update와 record 이동

새 payload가 기존 공간보다 작으면 같은 위치에서 길이만 줄일 수 있다. 더 크면 선택지가 생긴다.

- page 안에서 다른 위치로 이동하고 slot offset 갱신
- page를 compact한 뒤 다시 시도
- 다른 page로 이동하고 forwarding pointer 사용
- update를 delete+insert로 처리

어느 방식이든 실패 원자성이 중요하다. “기존 record를 지운 뒤 새 record를 넣으려 했는데 공간 부족”이면 원래 값까지 잃는다.

안전한 순서는 다음에 가깝다.

```text
필요 공간 계산
→ 가능한지 검증
→ 새 layout 준비
→ slot과 bytes를 한 번에 교체
```

## Compaction

삭제와 축소 update가 반복되면 free byte가 여러 곳에 흩어진다. compaction은 live record를 한쪽으로 모으고 slot offset을 갱신한다.

compaction 전후에 보존해야 할 것:

- live slot ID
- 각 slot이 가리키는 payload
- tombstone 여부
- page header의 free-space 경계
- page LSN과 checksum 같은 metadata

compaction은 record의 논리 순서를 바꾸지 않는 내부 작업이다. 외부 RID를 바꾸면 안 된다.

## Page 직렬화와 손상 검증

메모리 객체를 그대로 디스크에 쓰는 대신 명시적인 on-page format을 둔다.

```text
magic/version
page type
slot count
free-space boundary
page LSN
checksum
slot entries
record bytes
```

읽을 때 최소한 다음을 검증한다.

- magic과 version이 맞는가
- directory가 free-space 경계를 넘지 않는가
- slot offset+length가 page 범위 안인가
- slot끼리 비정상적으로 겹치지 않는가
- checksum이 맞는가

손상된 offset을 그대로 신뢰하면 다른 record나 page 밖 메모리를 읽을 수 있다.

## Heap file과 정렬 파일

### Heap file

빈 공간이 있는 page에 record를 넣는다.

- insert가 단순하다.
- 전체 scan은 page 순서로 가능하다.
- 특정 key 탐색은 index 없이는 많은 page를 읽는다.
- update와 delete에 적합한 일반 기본 구조다.

free-space map을 두면 모든 page를 열어 보지 않고 insert 후보를 찾을 수 있다.

### Sorted file

특정 key 순서로 record를 유지한다.

- 범위 scan과 순차 읽기에 유리하다.
- 중간 insert와 page split·재배치 비용이 크다.
- update가 정렬 key를 바꾸면 이동이 필요하다.

실제 DBMS는 table heap과 별도 B+ tree index를 조합하는 경우가 많다. table 자체를 항상 정렬 상태로 유지할 필요 없이 index가 key 순서를 제공한다.

## Record identifier가 상위 계층과 만나는 지점

RID는 여러 계층을 연결한다.

```text
B+ tree leaf: key → RID
RID: page_id + slot_id
buffer pool: page_id → frame
slotted page: slot_id → record bytes
transaction: record version의 visibility 판단
```

slot 안정성이 깨지면 index가 잘못된 record를 가리킨다. buffer pool이 dirty page를 잃으면 RID가 존재하지만 record가 사라진다. WAL recovery가 page LSN을 잘못 처리하면 오래된 record가 되살아날 수 있다.

따라서 page exercise는 단순 byte 배열 문제가 아니라 전체 저장 엔진의 기반 계약이다.

## 연결 연습

- [`Slotted page 구현`](../../exercises/02-storage-and-indexes/01-slotted-page/README.md): insert·delete·update·compaction·serialization을 구현한다.
- [`Slotted page 예제`](../../examples/slotted_page.py): slot ID가 delete 뒤에도 유지되는 최소 예제를 실행한다.
- 다음 문서인 [`인덱스 구조`](02-index-structures.md)는 key가 RID로 연결되는 구조를 다룬다.

## 완료 기준

다음을 코드와 그림으로 설명할 수 있어야 한다.

1. slotted page에서 directory와 record byte가 서로 반대 방향으로 자라는 이유
2. offset 대신 `(page_id, slot_id)`를 사용하는 이유
3. delete 때 slot을 당겨 제거하면 안 되는 이유
4. update 공간 부족이 기존 record를 손상시키지 않게 하는 방법
5. compaction 전후에 반드시 보존할 불변식
6. heap file과 sorted file의 대표 read/write trade-off
