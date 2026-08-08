# Capstone B: 미니 저장 엔진

## 학습 목표

이 capstone은 범용 DBMS를 완성하는 프로젝트가 아니다. 앞선 내부구조 개념을 하나의 작은 요청 경로로 연결한다.

- 논리 record를 slotted page에 저장한다.
- page를 buffer pool로 읽고 pin·dirty·eviction을 관리한다.
- key를 ordered index에 연결한다.
- 변경 전에 WAL을 기록하고 flush 순서를 지킨다.
- truncate하지 않은 WAL을 source of truth로 삼아 crash 뒤 committed insert만 다시 만들고 미완료 insert를 제거한다.
- 복구 뒤 table과 index가 같은 논리 상태를 가리키는지 검사한다.
- memory·disk·WAL·index의 소유권과 실패 후 상태를 설명한다.

## 범위와 비범위

구현 범위:

```text
고정된 page 크기
가변 길이 record
stable record identifier
작은 buffer pool
단일 process
단일 writer 중심의 축소 transaction
ordered key index
WAL과 crash recovery
```

의도적으로 다루지 않는 범위:

- 완전한 SQL parser와 optimizer
- 실제 OS page cache 제어
- 여러 process의 lock manager
- 완전한 MVCC
- replica와 distributed transaction
- production-grade checksum·encryption·compression

범위를 줄이는 이유는 각 계층의 계약을 테스트 가능하게 만드는 데 집중하기 위해서다.

## 전체 요청 경로

Reference의 `insert(key, value)`를 다음처럼 분해한다.

```text
transaction 시작
→ key 중복·현재 위치 확인
→ 대상 page 선택·pin
→ WAL update record append
→ WAL flush 조건 확인
→ slotted page insert
→ page dirty 표시와 page_lsn 갱신
→ ordered index 갱신
→ commit record append·flush
→ page unpin
```

`get(key)`는 다음 경로를 따른다.

```text
ordered index lookup
→ record identifier(page_id, slot_id)
→ buffer pool fetch·pin
→ slot에서 record 읽기
→ unpin
```

각 화살표에 실패가 생겼을 때 남는 상태를 적어야 한다.

## 계층별 책임

### Slotted page

소유:

- slot ID와 record bytes의 매핑
- free space 경계
- append-only insert와 serialize·deserialize의 page 내부 상태
- serialize·deserialize

보장하지 않음:

- page를 언제 disk에 쓸지
- transaction commit
- key uniqueness

### Disk manager

소유:

- page ID별 bytes 읽기·쓰기
- 새 page 할당
- durable storage의 축소 모델

보장하지 않음:

- cache eviction
- WAL ordering을 스스로 판단

### Buffer pool

소유:

- page frame
- pin count
- dirty 상태
- Clock victim 선택
- eviction 전 flush 요청

보장하지 않음:

- 업무 transaction
- index consistency

### WAL manager

소유:

- 단조 증가 LSN
- update·commit record
- stable LSN
- page write 전에 필요한 WAL flush 검사
- recovery 뒤 durable WAL의 최대 transaction ID보다 큰 ID를 할당

### Ordered index

소유:

- key에서 record identifier 찾기
- key 순서 scan
- unique key 계약

보장하지 않음:

- record bytes의 durability
- stale RID 자동 복구

### Storage engine coordinator

계층 사이의 순서를 소유한다.

- WAL append와 page mutation 순서
- index와 heap의 함께 변경
- auto-commit insert와 commit WAL flush
- crash recovery 후 index rebuild 또는 replay

모든 책임을 page class나 index class 하나에 넣지 않는다.

## Record identifier의 안정성

RID를 `(page_id, slot_id)`로 둔다. Page compaction이 record bytes를 옮겨도 slot ID가 유지되어야 index entry를 모두 갱신하지 않는다.

Reference가 의도적으로 구현하지 않는 다음 변경은 확장 과제다.

- record가 커져 같은 page에 들어가지 않음
- delete 뒤 slot 재사용
- page split 또는 record forwarding

Reference는 update와 delete를 제공하지 않는다. 이를 확장할 때는 update 크기를 제한하거나 새 RID를 생성하고 index를 원자적으로 바꾸는 규칙을 README와 테스트에 먼저 명시한다.

## Buffer pool과 WAL 순서

Dirty page를 eviction하려면 다음을 확인한다.

```text
page.page_lsn <= WAL stable_lsn
```

아니면 WAL을 먼저 flush해야 한다. Page가 disk에 먼저 기록되면 crash 뒤 uncommitted 또는 설명할 수 없는 변경이 남을 수 있다.

Commit은 다음 최소 계약을 가진다.

```text
commit WAL이 stable해진 뒤 성공 반환
```

Data page는 나중에 flush될 수 있다. Recovery가 이를 redo할 수 있어야 한다.

## Index와 heap consistency

실패가 다음 사이에 발생할 수 있다.

```text
heap insert 완료
→ index insert 전 crash
```

또는 반대 순서일 수 있다. 축소 구현에서 선택할 수 있는 방법:

1. WAL에 heap과 index 변경을 모두 기록해 replay한다.
2. heap을 source of truth로 두고 recovery 뒤 index를 rebuild한다.
3. atomic page group 같은 더 복잡한 구조를 구현한다.

Exercise reference는 truncate하지 않은 durable WAL을 heap의 source of truth로 사용해 committed insert만 page에 다시 만들고, 그 heap에서 index를 rebuild한다. 이 축소 규칙 때문에 log truncation과 update/delete는 비범위다.

## Transaction 상태

Reference는 한 호출이 한 transaction인 auto-commit만 지원한다.

```text
INSERT WAL append
  ├─ COMMIT WAL flush → 성공 반환
  └─ commit 없음      → recovery에서 제외
```

명시적 `begin`, 여러 write transaction, abort API는 제공하지 않는다. Recovery 뒤 transaction ID는 durable WAL의 최대 ID 다음부터 할당해 과거 COMMIT과 새 미완료 INSERT가 같은 ID를 공유하지 않게 한다.

## Crash 지점

Reference 테스트가 재현하는 crash 경계는 다음과 같다.

```text
INSERT WAL만 durable하고 page는 쓰이지 않음
INSERT WAL만 durable한 상태가 page까지 쓰임
COMMIT WAL은 durable하지만 page는 쓰이지 않음
recovery를 완료한 직후 같은 WAL로 다시 recovery
```

각 crash 뒤 검사:

- committed key가 조회된다.
- uncommitted key가 조회되지 않는다.
- WAL stable 범위보다 앞선 page가 없다.
- index RID가 존재하는 record를 가리킨다.
- 모든 page invariant가 참이다.
- recovery를 두 번 실행해도 결과가 같다.

## 검증 가능한 불변식

### Page

```text
header + slot directory + records <= page size
slot은 page 경계 안을 가리킴
live record 영역은 겹치지 않음
free space 경계가 역전되지 않음
```

### Buffer pool

```text
frame당 page 하나
page table과 frame 일치
pin_count >= 0
pinned frame은 victim이 아님
dirty eviction 전 WAL·page flush 순서 보존
```

### Index

```text
key 정렬
unique key 중복 없음
모든 RID가 live record를 가리킴
모든 live key가 index에 있음
```

### Recovery

```text
committed effect 포함
uncommitted effect 제외
page_lsn 단조성
반복 recovery 멱등
복구 뒤 새 transaction ID가 과거 COMMIT namespace와 겹치지 않음
```

## 선택 확장: 성능 계측

Reference에는 counter가 없다. 구조를 바꾸지 않고 다음 counter를 추가하는 것은 선택 확장이다.

- page read/write
- buffer hit/miss
- eviction과 dirty flush
- WAL append/flush bytes
- index comparison
- recovery redo/undo record 수

Counter가 있으면 page 크기, buffer frame 수와 access pattern을 바꿔 결과를 설명할 수 있다. 실제 DBMS 성능으로 일반화하지 않지만, 구조적 trade-off를 관찰할 수 있다.

## 구현 순서

한 번에 coordinator 전체를 작성하지 않는다.

```text
1. slotted page와 round-trip serialization
2. disk manager
3. buffer pool과 Clock
4. ordered index
5. WAL append·flush
6. 단일 put/get 경로
7. commit과 crash recovery
8. index rebuild·consistency check
9. 네 crash 경계와 반복 recovery
10. 선택 사항: counter와 종합 테스트
```

각 단계의 test가 통과한 뒤 다음 계층을 연결한다. Failure가 발생했을 때 어느 계층 불변식이 깨졌는지 좁힐 수 있어야 한다.

## 연결 연습

[`Mini storage engine`](../../exercises/05-capstones/02-mini-storage-engine/README.md)은 다음을 제공한다.

- skeleton
- reference
- page·buffer·WAL·index 통합 테스트
- crash와 recovery 테스트
- reference 통과·skeleton 실패를 확인하는 루트 검증

Reference의 `OrderedLeafIndex`는 정렬된 leaf 배열의 split과 range scan만 제공하며 root·internal node·separator를 구현한 B+ tree라고 부르지 않는다. 완전한 B+ tree나 MVCC로 확장하기 전에 현재 불변식과 실패 지점을 유지하는지 확인한다.

## 완료 기준

다음 요청을 whiteboard와 코드에서 끝까지 추적할 수 있어야 한다.

```text
insert(42, bytes)
→ 어느 WAL record가 생기는가
→ 어느 page와 slot이 바뀌는가
→ buffer frame의 pin·dirty 상태는 무엇인가
→ index에는 어떤 RID가 들어가는가
→ commit 성공 전에 무엇이 flush되어야 하는가
→ page flush 전 crash하면 어떻게 복구하는가
```

그리고 다음을 자동 검사로 증명해야 한다.

- serialize 왕복 뒤 RID 안정성
- pinned frame 미축출
- dirty page의 write-ahead 규칙
- duplicate key 거부
- committed write redo
- uncommitted write 제거
- recovery 멱등성
- heap/index consistency

두 학습 경로를 모두 끝냈다면 [`시스템 종합 검토`](../90-system-review.md)로 이동한다.
