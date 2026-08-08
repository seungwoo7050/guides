# 주소 공간과 page fault

## 학습 목표

- address space, mapping, page, PTE와 physical frame을 구분합니다.
- not-present, protection, COW와 invalid-address fault의 처리 책임을 분류합니다.
- fault 처리 중 frame 할당·I/O·block·재시도 상태 전이를 추적합니다.

## 핵심 모델

프로그램이 사용하는 pointer는 곧바로 물리 메모리 칸을 뜻하지 않습니다. 각 process는 자신에게 보이는 가상 주소 공간을 가지며, 운영체제는 어느 영역이 유효한지, 어떤 권한을 가지는지, 실제 page가 현재 물리 메모리에 있는지 관리합니다. 이 장에서는 page table hardware를 세부적으로 구현하기보다 **주소 공간의 상태와 page fault 처리 정책**에 집중합니다.

## 주소 공간은 mapping의 집합입니다

하나의 process 주소 공간을 다음 영역으로 단순화할 수 있습니다.

```text
실행 코드와 읽기 전용 상수
초기화된 data와 zero-initialized 영역
heap
thread stack
shared library mapping
memory-mapped file
anonymous mapping
guard page와 사용하지 않는 hole
```

각 mapping에는 최소한 다음 정보가 필요합니다.

```text
가상 주소 범위
읽기·쓰기·실행 권한
anonymous 또는 file-backed 여부
private 또는 shared 여부
backing object와 offset
현재 resident 여부
COW·dirty·accessed 같은 관리 상태
```

“주소 범위가 존재합니다”와 “현재 물리 frame이 연결돼 있습니다”는 다른 주장입니다. demand paging에서는 mapping은 유효하지만 첫 접근 전까지 frame이 없을 수 있습니다.

## 주소 접근의 질문을 단계로 나눕니다

CPU가 가상 주소에 접근할 때 운영체제 관점에서 다음 질문이 필요합니다.

```text
1. 이 가상 주소가 process 주소 공간의 유효한 mapping 안에 있습니까?
2. 요청한 읽기·쓰기·실행이 mapping 권한과 맞습니까?
3. page가 현재 resident합니까?
4. resident하지 않다면 어떤 backing에서 채울 수 있습니까?
5. COW 또는 lazy allocation처럼 쓰기 때 특별한 처리가 필요합니까?
6. 처리 중 memory pressure나 I/O 실패가 발생하면 어떤 결과를 돌려줍니까?
```

hardware는 page table walk, TLB와 permission bit를 사용해 일부 질문을 빠르게 처리합니다. 가상 주소 bit 분해, TLB 구조, ASID와 cache 관계는 컴퓨터 구조 가이드의 주 범위입니다. 여기서는 hardware가 처리할 수 없는 상태를 kernel에 알린 뒤 어떤 정책이 실행되는지 봅니다.

## page fault는 항상 오류가 아닙니다

page fault는 현재 접근을 완료하기 위해 kernel 개입이 필요하다는 사건입니다. 원인에 따라 정상 복구가 가능할 수도 있고 process를 계속 실행할 수 없을 수도 있습니다.

### not-present fault

mapping은 유효하지만 page가 resident하지 않습니다.

```text
anonymous demand-zero
→ 새 frame을 확보하고 0으로 초기화합니다.

file-backed mapping
→ backing file에서 해당 page를 읽습니다.

swap 또는 compressed backing
→ 보관된 내용을 복원합니다.
```

### protection fault

mapping은 있지만 요청 권한이 허용되지 않습니다.

```text
read-only code page에 write
non-executable data page에서 instruction fetch
user mode가 kernel-only mapping에 접근
```

보통 복구할 수 없는 접근이지만 COW처럼 의도적으로 read-only로 표시한 page의 write는 특별 경로로 복구할 수 있습니다.

### invalid address

어떤 mapping에도 속하지 않거나 guard page처럼 의도적으로 접근이 금지된 주소입니다. kernel은 process에 signal 또는 예외를 전달할 수 있습니다.

## fault 처리도 상태 전이입니다

page가 disk I/O를 필요로 하면 fault handler가 즉시 끝나지 않습니다.

```text
RUNNING process가 주소 접근
→ page fault로 kernel 진입
→ mapping과 권한 검사
→ page-in I/O 제출
→ 현재 thread BLOCKED
→ 다른 thread 실행
→ 장치 completion interrupt
→ frame과 mapping 갱신
→ thread READY
→ 다시 선택됐을 때 faulting instruction 재시도
```

따라서 page fault는 메모리 관리와 scheduler·block/wakeup·device I/O를 연결합니다. fault handler가 lock을 보유한 채 sleep할 수 있는지, 같은 mapping을 여러 thread가 동시에 fault할 때 누가 I/O를 수행하는지, 실패 결과를 모든 waiter에게 어떻게 전달하는지가 중요합니다.

## 주소 공간 불변식

간단한 모델에서도 다음 관계를 지켜야 합니다.

```text
한 process의 한 VPN은 최대 하나의 현재 mapping을 가짐
resident PTE는 존재하는 frame을 가리킴
frame reference count는 그 frame을 가리키는 mapping 수와 일치
writable하지 않은 mapping에 일반 write를 허용하지 않음
COW 공유 frame은 여러 process가 함께 가리킬 수 있지만 직접 writable하지 않음
mapping 제거 뒤 stale PTE나 frame reference가 남지 않음
```

[`paging.py`](../../exercises/kernel-model/README.md)는 이 불변식을 단순한 Python object graph로 검사합니다. 실제 다단계 page table을 흉내 내기보다 process별 VPN mapping, frame content, write 권한과 COW reference를 모델링합니다.

```sh
make -C exercises/kernel-model reference-test
make -C exercises/kernel-model failure-test
```

`failure-fixtures/03-memory-shared-writable.json`은 같은 frame을 여러 process가 공유하면서 일반 writable 상태로 둔 모순을 거부합니다.

## demand-zero mapping

anonymous memory를 요청했다고 즉시 모든 page를 물리 메모리로 채울 필요는 없습니다.

```text
mapping 생성
→ 아직 frame 없음
→ 첫 read 또는 write
→ not-present fault
→ zero-filled frame 연결
```

이 방식은 실제로 접근하지 않는 page의 비용을 피합니다. 여러 read-only zero page를 공유하고 첫 write 때 private frame을 만들 수도 있습니다.

하지만 “메모리 할당 성공”이 이후 모든 접근 성공을 보장하지는 않습니다. overcommit 정책, memory pressure와 backing I/O에 따라 실제 page 확보 시점에 실패가 나타날 수 있습니다.

## stack growth와 guard page

일부 시스템은 stack 근처의 fault를 보고 mapping을 제한된 범위 안에서 확장할 수 있습니다. 그러나 임의의 먼 주소 접근까지 stack growth로 받아들이면 잘못된 pointer를 숨길 수 있습니다.

보통 다음 정책이 필요합니다.

```text
현재 stack pointer와의 거리 제한
최대 stack 크기
guard page 유지
다른 mapping과 충돌 금지
실행 중인 thread별 stack 구분
```

정확한 정책은 운영체제와 ABI에 따라 다릅니다.

## memory-mapped file의 세 가지 상태

file-backed mapping에서는 다음을 구분합니다.

1. process의 가상 mapping
2. page cache의 현재 내용
3. storage에 durable한 내용

`MAP_SHARED` 계열 mapping의 write가 page cache를 dirty하게 만들 수 있지만 즉시 storage durability를 보장하지 않습니다. `MAP_PRIVATE` 계열은 write 시 private COW page를 만들 수 있습니다. mapping을 해제하는 것, writeback을 요청하는 것과 file metadata를 durable하게 만드는 것은 서로 다른 계약입니다.

이 연결은 [파일시스템, page cache와 장애 일관성](../04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md)에서 이어집니다.

## TLB와 address-space switch를 필요한 만큼만 이해합니다

TLB는 최근 주소 변환과 permission을 cache합니다. 운영체제가 page table이나 mapping 권한을 바꾸면 CPU가 오래된 변환을 계속 사용하지 않도록 무효화가 필요합니다. 여러 CPU에서 같은 주소 공간을 실행했다면 다른 CPU에도 알리는 절차가 필요할 수 있습니다.

운영체제 관점의 핵심은 다음입니다.

```text
mapping 변경은 page table memory만 바꾸는 것으로 끝나지 않을 수 있음
stale translation을 사용하면 권한과 frame 수명 불변식이 깨질 수 있음
address-space switch와 mapping update에는 architecture별 동기화 계약이 있음
```

TLB set, page-walk cache, PCID·ASID와 exact instruction은 컴퓨터 구조 가이드에서 다룹니다.

## fork와 주소 공간 복제

`fork` 계열 의미를 단순하게 구현하면 부모의 모든 writable page를 즉시 복사해야 합니다. 대부분의 page가 자식이나 부모에서 바뀌지 않는다면 낭비입니다. COW는 다음 장의 중심 주제지만 주소 공간 관점에서는 다음 상태가 필요합니다.

```text
부모와 자식 PTE가 같은 frame 참조
둘 다 즉시 writable하지 않음
COW 표시와 frame reference count 유지
한쪽 write fault에서 private copy 생성
다른 쪽 mapping은 기존 frame 유지
```

[`cow-observer.c`](../../examples/cow-observer.c)는 부모와 자식이 같은 가상 주소를 출력하지만 자식 write 뒤 값이 분리되는 사용자 공간 계약을 관찰합니다.

```sh
make -C examples build/cow-observer
./examples/build/cow-observer
```

같은 숫자 주소가 출력됐다는 사실은 같은 물리 frame을 직접 증명하지 않습니다. user-space program만으로 정확한 COW 시점이나 PFN을 단정하지 않습니다.

## page fault 관찰의 한계

[`page-fault-observer.c`](../../examples/page-fault-observer.c)는 anonymous allocation의 page마다 첫 byte를 쓰고 minor fault 통계 변화량을 출력합니다.

```sh
make -C examples build/page-fault-observer
./examples/build/page-fault-observer 128
```

다음 값은 환경에 따라 달라질 수 있습니다.

- allocator가 이미 확보한 mapping
- transparent huge page 정책
- zero page 공유
- compiler와 runtime의 주변 접근
- kernel의 fault accounting 방식

따라서 정확한 fault 수를 고정 정답으로 쓰지 않습니다. “page 단위 첫 접근이 fault와 resident 상태 변화로 이어질 수 있다”는 모델과 관찰이 양립하는지 확인합니다.

## fault 폭증을 진단하는 질문

page fault 수가 증가했을 때 곧바로 “RAM이 부족합니다”라고 결론 내리지 않습니다.

```text
minor입니까 major입니까?
anonymous입니까 file-backed입니까?
처음 접근입니까 반복 접근입니까?
working set이 physical memory보다 큽니까?
같은 page가 반복해서 evict·fault됩니까?
random access가 locality를 깨뜨립니까?
COW write가 예상보다 많습니까?
mapping을 지나치게 자주 만들고 없앱니까?
```

실제 process의 mapping, RSS와 fault를 관찰하는 명령은 Unix 시스템 가이드에서 다룹니다.

## 연결 실습

[`translation.json`](../../exercises/kernel-model/fixtures/translation.json)의 상태 전이와 [`page-fault-observer.c`](../../examples/page-fault-observer.c)의 환경 의존 관측값을 구분합니다.

다음 접근마다 필요한 추가 정보와 가능한 결과를 적습니다.

1. 유효한 anonymous mapping의 첫 read
2. read-only mapping의 write
3. fork 뒤 COW page의 자식 write
4. file-backed mapping의 resident하지 않은 page read
5. guard page 접근
6. mapping은 유효하지만 page-in I/O가 실패
7. 같은 VPN을 두 thread가 동시에 처음 접근

각 상황에서 다음을 구분합니다.

```text
mapping 유효성
권한
resident 여부
필요한 backing
thread block 가능성
instruction 재시도 가능성
최종 오류 전달
```

## 완료 기준

- 일곱 접근을 mapping·권한·resident·backing·재시도 결과로 분류합니다.
- translation fixture에서 parent/child PTE와 frame refcount 변화를 확인합니다.
- read-only demand-zero write가 frame을 할당하지 않고 보호 오류가 됨을 검증합니다.

## 실패 조건

- 모든 page fault를 비정상 종료나 물리 메모리 부족으로 해석합니다.
- 같은 virtual address가 process마다 같은 physical frame을 뜻한다고 가정합니다.
- 공유 frame을 writable로 남긴 채 COW 상태라고 표시합니다.

## 자기 설명

- 주소 공간, mapping, page와 frame을 서로 바꾸어 쓰지 않을 수 있습니까?
- not-present, protection, COW와 invalid-address fault를 구분할 수 있습니까?
- 정상 page fault가 thread block과 device I/O를 일으킬 수 있는 경로를 설명할 수 있습니까?
- frame reference count와 mapping 권한의 불변식을 적을 수 있습니까?
- 같은 가상 주소가 같은 물리 frame을 뜻하지 않는 이유를 설명할 수 있습니까?
- user-space fault 관찰이 kernel 내부 구현을 직접 증명하지 않는다는 한계를 말할 수 있습니까?
