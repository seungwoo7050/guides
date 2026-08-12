# Buffer pool과 페이지 교체

## 학습 목표

이 문서를 마치면 다음을 설명할 수 있어야 한다.

- buffer pool이 저장장치 page와 메모리 frame 사이의 mapping을 관리하는 이유
- page table, pin count, dirty bit와 reference bit의 역할
- fetch·unpin·flush·evict의 상태 전이
- Clock 정책이 최근 참조와 교체 가능 여부를 구분하는 방식
- dirty victim을 내보낼 때 필요한 순서
- cache hit ratio 하나만으로 buffer pool 품질을 판단하면 안 되는 이유

## 선행지식

[`페이지와 레코드`](01-pages-records-and-files.md)를 읽고 page ID와 record byte를 이해해야 한다.

## Buffer pool은 단순한 dictionary cache가 아니다

DBMS는 모든 page를 메모리에 둘 수 없다. buffer pool은 제한된 frame에 현재 필요한 page를 올리고, 다시 사용할 page를 남기며, 내보낼 page를 선택한다.

```text
disk page_id
    ↓ fetch
page table: page_id → frame_id
    ↓
frame: page bytes + pin_count + dirty + referenced
```

일반 cache와 다른 핵심은 다음이다.

- page를 사용 중인 실행기가 있으므로 마음대로 교체할 수 없다.
- 메모리에서 수정된 dirty page는 쓰지 않고 버리면 안 된다.
- transaction·WAL 순서와 함께 flush해야 한다.
- 같은 page 객체를 여러 operator가 공유할 수 있다.
- background writer, checkpoint와 eviction이 동시에 일어날 수 있다.

## Frame metadata

### `page_id`

현재 frame에 어느 disk page가 들어 있는지 나타낸다. 빈 frame이면 없음 상태다.

### `pin_count`

현재 page를 사용 중인 주체 수다.

```text
fetch → pin_count + 1
사용 종료 → unpin → pin_count - 1
```

`pin_count > 0`인 frame은 교체하면 안 된다. 실행기가 읽거나 수정하는 byte가 다른 page로 바뀌기 때문이다.

### `dirty`

메모리 page가 disk보다 새로운지 나타낸다. 한 사용자가 dirty로 unpin한 뒤 다른 사용자가 clean으로 unpin해도 dirty 상태를 지우면 안 된다.

```text
frame.dirty = frame.dirty OR caller_dirty
```

### `referenced`

교체 정책에서 최근 사용 여부를 나타낸다. Clock은 이 bit를 두 번째 기회로 사용한다.

## Fetch 상태 전이

### Cache hit

1. page table에서 frame을 찾는다.
2. pin count를 증가시킨다.
3. referenced를 켠다.
4. 같은 frame의 page bytes를 반환한다.

같은 page를 다시 disk에서 읽지 않아야 한다.

### Cache miss

1. 빈 frame을 찾거나 victim을 선택한다.
2. victim이 dirty면 안전한 순서로 flush한다.
3. 이전 page table mapping을 제거한다.
4. 새 page를 disk에서 읽는다.
5. frame metadata를 초기화한다.
6. 새 mapping을 등록하고 pin한다.

순서가 중요하다. 새 mapping을 먼저 등록한 뒤 disk read가 실패하면 page table이 존재하지 않는 page를 가리킬 수 있다. dirty victim을 mapping에서 먼저 지운 뒤 write가 실패하면 retry 대상이 사라질 수 있다.

## Pin contract

pin은 “이 page가 중요하다”는 점수라기보다 **현재 pointer를 사용하는 동안 교체하지 말라**는 수명 계약이다.

흔한 실패:

- fetch 뒤 예외 경로에서 unpin하지 않음
- 한 번 fetch하고 두 번 unpin
- 수정했지만 dirty=false로 unpin
- page pointer를 보관하면서 먼저 unpin
- nested operator가 pin ownership을 불명확하게 공유

실제 구현에서는 RAII guard나 context manager로 pin 수명을 표현할 수 있다.

```text
with buffer_pool.page(page_id, write=True) as page:
    modify(page)
# scope 종료에서 dirty unpin
```

## Clock 교체 정책

Clock은 frame을 원형으로 순회한다.

```text
if pinned:
    skip
else if referenced:
    referenced = false
    second chance
else:
    victim
```

LRU의 정확한 순서를 유지하는 비용을 줄이면서 최근 사용 page에 한 번의 기회를 준다.

### 모든 frame이 pin 상태인 경우

무한히 돌면 안 된다. 명시적으로 실패하거나 대기 정책을 사용해야 한다.

```text
BufferPoolFull
```

이 실패는 단순 용량 부족일 수도 있지만 pin leak의 신호일 수 있다. 관측할 항목:

- frame별 pin count
- 가장 오래 pin된 page
- caller 또는 operator
- buffer wait 시간

### 최근 참조 page만 있는 경우

첫 바퀴에서 reference bit를 내리고 두 번째 바퀴에서 victim을 선택한다. 따라서 구현은 충분한 순회 횟수와 “pin 때문에 불가능” 상태를 구분해야 한다.

## Dirty page flush

dirty victim을 내보내기 전에 다음을 보존한다.

```text
memory page의 최신 bytes
page LSN
해당 변경의 WAL durable 여부
write 성공 여부
```

WAL을 사용하는 시스템에서는 다음 순서가 필요하다.

```text
log record append
→ log flush through page_lsn
→ data page write
```

data page가 먼저 disk에 도달하면 crash 뒤 변경 이유를 설명할 durable log가 없을 수 있다. 이 계약은 [`MVCC·WAL·복구`](../03-transactions-and-recovery/02-mvcc-wal-and-recovery.md)에서 이어진다.

write가 실패하면 frame은 dirty 상태를 유지해야 한다. 성공 확인 전에 dirty bit를 내리면 변경을 잃는다.

## Flush와 eviction을 구분한다

- **flush**: frame은 그대로 두고 dirty bytes를 disk에 반영한다.
- **eviction**: frame을 다른 page에 재사용한다.

flush한 page는 cache에 남아 다시 hit할 수 있다. checkpoint나 background writer는 eviction 없이 flush할 수 있다.

## New page와 allocation

새 page를 만들 때도 두 계층이 있다.

```text
disk/file manager: 새 page_id 할당
buffer pool: 그 page를 frame에 fetch 또는 생성
```

allocation이 성공했지만 buffer frame을 얻지 못하면 새 page를 어떻게 정리할지 계약이 필요하다. 반대로 frame만 초기화하고 page allocation이 실패하면 mapping을 남기면 안 된다.

교육용 exercise는 기존 disk page fetch에 집중하지만, capstone에서는 page allocation과 buffer pool을 함께 사용한다.

## Prefetch와 sequential scan

큰 sequential scan은 한 번 읽고 다시 쓰지 않을 page로 buffer를 채워 hot working set을 밀어낼 수 있다. 실제 시스템은 다음을 사용할 수 있다.

- scan 전용 작은 ring buffer
- sequential prefetch
- bulk read hint
- page access strategy 분리

모든 read를 동일한 replacement 정책으로 처리하는 것이 항상 최선은 아니다.

## Hit ratio의 한계

높은 hit ratio가 반드시 빠른 것은 아니다.

- 매우 느린 query가 같은 page를 반복해 hit할 수 있다.
- dirty flush가 몰려 write latency가 커질 수 있다.
- pin wait가 길어도 최종 hit로 기록될 수 있다.
- sequential scan은 낮은 hit ratio여도 최적일 수 있다.

함께 볼 지표:

```text
read/write page 수
cache hit/miss
flush latency
dirty frame 비율
pin wait
eviction 수
checkpoint write burst
```

## Buffer pool 불변식

구현에서 최소한 다음을 검사한다.

- page table의 각 mapping은 정확히 한 frame을 가리킨다.
- resident frame의 page ID는 page table과 일치한다.
- pin count는 음수가 아니다.
- pinned frame은 victim이 아니다.
- dirty page는 성공한 write 전까지 dirty다.
- 빈 frame은 page table에 등록되지 않는다.
- eviction 뒤 이전 mapping은 남지 않는다.

이 불변식이 깨지면 서로 다른 page가 같은 frame을 가리키거나, 최신 data가 조용히 사라진다.

## 연결 연습

- [`Buffer pool 예제`](../../examples/buffer_pool.py): pinned frame과 second chance를 작은 상태로 관찰한다.
- [`Clock buffer pool 구현`](../../exercises/02-storage-and-indexes/03-buffer-pool-clock/README.md): 예제를 관찰한 뒤 cache hit, pin, dirty eviction과 Clock을 구현한다.
- [`Mini storage engine`](../../exercises/05-capstones/02-mini-storage-engine/README.md): buffer flush와 WAL durable boundary를 통합한다.

## 완료 기준

다음 시나리오의 상태 전이를 그릴 수 있어야 한다.

1. clean page cache miss
2. dirty victim을 사용한 cache miss
3. 같은 page를 두 operator가 fetch하고 순서대로 unpin
4. 모든 frame이 pin되어 새 page를 가져오지 못함
5. write 실패 뒤 dirty bit 유지
6. WAL이 page LSN까지 flush되지 않은 상태에서 eviction 시도

각 전이에서 page table, frame metadata와 disk state가 어떻게 바뀌는지 설명한다.
