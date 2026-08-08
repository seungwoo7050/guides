# 요구 페이징, COW와 page replacement

## 학습 목표

- mapping 생성과 실제 frame allocation 시점을 분리합니다.
- COW 공유·write fault·private copy·refcount 수명을 추적합니다.
- FIFO·LRU·Clock의 상태와 반례를 같은 reference string으로 비교합니다.

## 핵심 모델

가상 주소 공간은 process가 사용할 수 있는 논리적 범위이고, 물리 메모리는 현재 resident한 working set을 담는 제한된 자원입니다. 운영체제는 page를 **언제 들일지**, 여러 mapping이 **언제 공유할지**, memory pressure에서 **무엇을 내보낼지**, dirty data를 **어디에 보존할지** 결정합니다. 이 장에서는 demand paging, copy-on-write와 replacement를 하나의 frame 수명 문제로 연결합니다.

## demand paging은 비용을 실제 사용 시점으로 미룹니다

실행 파일과 mapping의 모든 page를 process 시작 시점에 읽는 대신 접근할 때 채웁니다.

```text
mapping 존재, PTE not-present
→ 첫 접근 fault
→ 빈 frame 확보
→ anonymous면 zero-fill
→ file-backed면 해당 offset 읽기
→ PTE 갱신
→ 접근 instruction 재시도
```

장점은 다음과 같습니다.

- 사용하지 않는 code와 data를 읽지 않습니다.
- process 시작 latency와 physical memory 사용을 줄일 수 있습니다.
- 같은 file-backed read-only page를 여러 process가 공유할 수 있습니다.

비용과 위험도 있습니다.

- 첫 접근 latency가 커집니다.
- fault 처리 중 I/O가 필요하면 thread가 block됩니다.
- memory pressure에서 frame 확보가 실패할 수 있습니다.
- random working set은 반복 fault를 만들 수 있습니다.

## frame 수명과 소유권

frame 하나에는 다음 상태가 연결될 수 있습니다.

```text
어떤 mapping들이 참조하는가
anonymous 또는 file-backed인가
clean 또는 dirty인가
최근 접근됐는가
writeback 중인가
pinned돼 교체할 수 없는가
COW 공유 중인가
reference count가 얼마인가
```

frame을 재사용하려면 이전 mapping들이 더 이상 접근하지 못해야 합니다. page table에서 entry를 지우고 stale TLB를 처리하기 전에 frame을 다른 용도로 재사용하면 이전 주소 공간이 새 data를 볼 수 있습니다.

운영체제의 정확한 reclamation 경로는 복잡하지만 최소 불변식은 다음입니다.

```text
참조 중인 frame을 free list에 두지 않음
pinned 또는 I/O 중인 frame을 교체하지 않음
dirty page의 backing 보존 전 재사용 금지
mapping 제거와 translation 무효화 뒤에만 안전한 재사용
```

## copy-on-write의 상태 전이

COW는 “복사를 하지 않는 기술”이 아니라 **write가 실제로 발생할 때만 복사하는 정책**입니다.

### fork 직후

```text
부모 PTE ─┐
          ├→ frame F, refcount=2
자식 PTE ─┘

두 PTE는 COW이며 일반 write 불가
```

### 자식 write fault

```text
1. mapping이 유효하고 COW인지 확인
2. 새 frame N 확보
3. F의 내용을 N으로 복사
4. 자식 PTE를 N의 writable mapping으로 변경
5. F refcount 감소
6. 필요한 translation 무효화
7. faulting write 재시도
```

F의 refcount가 이미 1이라면 복사 없이 해당 mapping을 writable로 전환할 수 있는 최적화도 가능합니다. 단, 다른 reference나 snapshot 정책이 없는지 확인해야 합니다.

### 동시 COW fault

같은 process의 여러 thread가 같은 COW page에 동시에 write하거나 부모와 자식이 함께 write할 수 있습니다. 다음 경쟁을 막아야 합니다.

- 같은 mapping에 private frame을 두 번 할당합니다.
- reference count를 두 번 줄입니다.
- 한쪽이 아직 복사 중인 frame을 다른 쪽이 재사용합니다.
- stale writable translation이 공유 frame을 바꿉니다.

따라서 mapping lock, page lock과 retry protocol이 필요할 수 있습니다.

[`paging.py`](../../exercises/kernel-model/README.md)는 단순한 단일-thread 모델이지만 다음 의미를 검사합니다.

```text
parent write 7
fork
child read → 7
child write 9 → COW fault
parent read → 7
child read → 9
frame 수 → 2
```

## 공유와 복사는 목적에 따라 다릅니다

| mapping | 일반적인 의미 |
|---|---|
| read-only file-backed | 같은 내용의 page cache frame을 공유할 수 있습니다. |
| private file-backed | read는 공유할 수 있고 write는 private COW가 될 수 있습니다. |
| shared file-backed | write가 공유 page cache를 바꾸고 writeback 대상이 될 수 있습니다. |
| anonymous private | fork 전에는 process 전용이며 fork 뒤 COW 공유할 수 있습니다. |
| explicit shared memory | 참여자가 같은 frame의 변경을 보며 별도 동기화가 필요합니다. |

“같은 frame을 공유합니다”는 visibility와 atomicity가 자동으로 안전하다는 뜻이 아닙니다. 공유 memory의 상태 계약은 동기화 장에서 다룬 원칙을 따릅니다.

## memory pressure와 reclaim

free frame이 부족하면 운영체제는 다음 후보를 검토할 수 있습니다.

```text
clean file-backed page
→ backing file에서 다시 읽을 수 있으므로 비교적 쉽게 제거

dirty file-backed page
→ writeback 뒤 제거

anonymous page
→ swap·compressed memory 같은 backing에 보존하거나 회수 불가

page cache
→ 최근 사용, dirty, writeback와 reclaim 우선순위 고려

pinned page
→ DMA나 kernel 작업이 끝날 때까지 제거 불가
```

reclaim 정책은 process page와 page cache를 완전히 별개로 보지 않습니다. file I/O cache가 memory를 사용하지만 필요할 때 회수될 수 있고, anonymous working set과 경쟁합니다.

## replacement 알고리즘의 모델

### FIFO

가장 먼저 들어온 page를 먼저 내보냅니다.

```text
상태: resident 순서
장점: 단순함
약점: 최근 자주 쓰는 page도 오래됐다는 이유로 제거
```

Belady anomaly처럼 frame 수를 늘렸는데 fault가 늘 수 있습니다.

### LRU

가장 오래 사용하지 않은 page를 제거합니다.

```text
상태: 모든 접근의 최근성 순서
장점: temporal locality를 직접 반영
약점: 정확한 구현 비용이 큼
```

실제 kernel은 hardware accessed bit, active/inactive list와 sampling을 사용해 근사할 수 있습니다.

### Clock

원형 queue와 reference bit를 사용합니다.

```text
candidate의 reference bit=1
→ bit를 0으로 만들고 다음 후보

reference bit=0
→ 교체
```

정확한 LRU보다 상태와 갱신 비용이 작습니다. enhanced Clock은 dirty 여부도 고려할 수 있습니다.

### working set과 page-fault frequency

최근 일정 구간에 사용한 page 집합을 working set으로 보고, process가 필요한 resident set을 추정할 수 있습니다. fault frequency가 너무 높으면 frame을 더 주거나 process 수를 줄이는 정책을 고려합니다.

## 정책 비교에는 trace가 필요합니다

같은 알고리즘도 access pattern에 따라 결과가 달라집니다.

```text
순차 scan
작은 hot set 반복
두 working set 사이 교대
큰 random access
한 번만 읽는 streaming
```

[`simulate_replacement`](../../exercises/kernel-model/README.md)는 같은 reference string에 FIFO, LRU와 Clock을 적용해 fault 수와 evicted page를 비교합니다.

```sh
cd exercises/kernel-model
python3 reference/kernel-model.py replacement fixtures/replacement.json
```

이 모델은 real kernel의 page cache, NUMA와 background writeback을 재현하지 않습니다. 정책의 최소 상태와 반례를 확인하는 용도입니다.

## thrashing은 단순히 fault가 많은 상태가 아닙니다

working set이 resident capacity를 넘으면 process가 유효한 계산보다 page-in·eviction에 대부분의 시간을 쓸 수 있습니다.

```text
fault 발생
→ 필요한 page를 들이기 위해 다른 hot page 제거
→ 곧 제거한 page를 다시 접근
→ 다시 fault
```

증상은 다음처럼 나타날 수 있습니다.

- CPU utilization은 낮거나 kernel fault 처리 비율이 높습니다.
- storage I/O가 지속됩니다.
- throughput이 크게 떨어집니다.
- process를 하나 더 추가했는데 전체 완료량이 감소합니다.

대응은 단순히 swap을 늘리는 것이 아닙니다.

```text
multiprogramming 정도 감소
working set에 맞는 memory 배분
access locality 개선
streaming과 cache pollution 분리
memory limit과 admission control
algorithm 또는 data layout 변경
```

## dirty page와 writeback

dirty page를 제거하기 전에는 backing에 내용을 반영해야 합니다. 동기 writeback을 eviction path에서 수행하면 latency가 커질 수 있어 background writeback이 미리 진행될 수 있습니다.

여기서 다음 상태를 구분합니다.

```text
clean resident
 dirty resident
writeback in progress
writeback failed
clean after writeback
invalidated or evicted
```

writeback 중 같은 page에 다시 write가 발생하면 새 dirty generation을 놓치지 않아야 합니다. I/O completion과 page state update의 순서가 중요합니다.

file data의 durability와 directory metadata의 durability는 [파일시스템 장](../04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md)에서 더 자세히 다룹니다.

## pinned page가 reclaim을 막습니다

DMA, direct I/O, kernel reference 또는 user-space pin API는 page를 이동·교체할 수 없게 만들 수 있습니다. pin이 오래 유지되면 다음 문제가 생깁니다.

- reclaim 후보 감소
- memory fragmentation
- COW와 migration 제약
- device가 사용하는 물리 주소 수명 증가
- process 종료 뒤에도 completion까지 자원 유지 필요

장치 요청의 pin과 completion 수명은 [장치 I/O 장](../04-storage-and-io/02-device-io-interrupts-and-dma.md)과 `device_io.py` 실습으로 연결됩니다.

## overcommit과 allocation 성공의 의미

일부 시스템은 가상 memory reservation 합계가 실제 physical memory와 backing보다 커도 allocation을 허용합니다. 따라서 다음을 구분해야 합니다.

```text
주소 범위 예약 성공
mapping metadata 생성 성공
첫 page fault에서 frame 확보 성공
전체 working set을 지속적으로 유지 가능
```

allocation API가 성공했다고 모든 page의 물리 자원이 확정된 것은 아닐 수 있습니다. 정확한 정책은 운영체제 설정과 API 계약에 따라 다릅니다.

## COW 관찰의 범위

[`cow-observer.c`](../../examples/cow-observer.c)를 실행합니다.

```sh
make -C examples build/cow-observer
./examples/build/cow-observer
```

예상하는 계약은 다음입니다.

```text
fork 전 value=41
child가 같은 가상 주소의 값을 99로 변경
parent의 값은 41로 유지
```

이 결과로 알 수 없는 것은 다음입니다.

- fork 직후 실제 physical frame이 공유됐는지
- 어느 write instruction에서 정확히 copy가 일어났는지
- huge page가 split됐는지
- kernel이 어떤 allocator와 lock을 사용했는지

관찰 결과와 내부 구현 주장을 분리합니다.

## 연결 실습

[`replacement.json`](../../exercises/kernel-model/fixtures/replacement.json)의 trace를 바꾸고 `05-paging` checkpoint로 결과를 검사합니다.

1. FIFO가 LRU보다 fault가 많아지는 짧은 reference string을 찾습니다.
2. FIFO에서 frame 수를 늘렸는데 fault가 증가하는 trace를 찾아봅니다.
3. 순차 scan 뒤 hot set을 반복하는 trace에서 LRU가 어떤 page를 보존하는지 설명합니다.
4. Clock의 reference bit가 모두 1인 순간 hand가 어떻게 움직이는지 단계별로 적습니다.
5. dirty page, pinned page와 COW-shared page가 동시에 후보일 때 어떤 상태를 더 확인해야 하는지 적습니다.

## 완료 기준

- replacement fixture에서 각 fault·eviction·최종 frame을 손으로 재현합니다.
- COW write 전후 두 address space의 permission과 refcount를 비교합니다.
- Belady anomaly와 hot-set scan을 드러내는 reference string을 하나씩 보존합니다.

## 실패 조건

- allocation 성공을 모든 page가 resident하다는 보장으로 해석합니다.
- dirty, pinned, shared page의 회수 비용과 금지 조건을 무시합니다.
- 평균 fault 수 하나만 보고 trace별 정책 반례를 확인하지 않습니다.

## 자기 설명

- demand paging이 mapping 생성과 physical allocation을 분리하는 이유를 설명할 수 있습니까?
- COW frame의 reference count, write permission과 private copy 수명을 추적할 수 있습니까?
- FIFO, LRU와 Clock이 유지하는 상태와 반례를 비교할 수 있습니까?
- clean file-backed, dirty file-backed, anonymous와 pinned page의 reclaim 비용을 구분할 수 있습니까?
- thrashing을 단순한 높은 memory 사용량과 구분할 수 있습니까?
- allocation 성공, resident memory와 지속 가능한 working set을 서로 다른 계약으로 설명할 수 있습니까?
