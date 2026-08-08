# 운영체제 추가 읽을거리

본문은 운영체제 원리를 특정 kernel 구현과 분리해 상태·정책·불변식으로 설명합니다. 아래 자료를 사용할 때는 **사용자에게 보이는 계약, kernel의 상태 소유자, 정책 선택, 오류·복구 경로와 대상 버전**을 함께 기록합니다.

## 사용자 공간 계약

### POSIX.1-2024, The Open Group Base Specifications Issue 8

- <https://pubs.opengroup.org/onlinepubs/9799919799/>
- <https://standards.ieee.org/ieee/1003.1/7700/>

process, thread, file, synchronization과 system interface가 application에 어떤 동작을 보장하는지 확인합니다. POSIX가 kernel 내부 자료구조와 scheduler 정책까지 규정한다고 해석하지 않습니다.

### C 언어 memory model

- C11 초안 N1570: <https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf>

C atomic, data race와 memory order의 정확한 언어 규칙이 필요할 때 사용합니다. 이 저장소의 acquire·release 설명은 공통 직관이며 실제 코드는 해당 언어 표준을 따라야 합니다.

## 결정론적 운영체제 모델

### Operating Systems: Three Easy Pieces

- <https://pages.cs.wisc.edu/~remzi/OSTEP/>

CPU virtualization, concurrency, virtual memory와 persistence를 작은 simulator와 함께 학습할 수 있습니다. 이 저장소의 `kernel-model`을 끝낸 뒤 더 다양한 scheduling trace, paging policy와 filesystem failure를 비교하기에 적합합니다.

### MIT xv6 for RISC-V

- 과정과 교재: <https://pdos.csail.mit.edu/6.828/2025/xv6.html>
- kernel source: <https://github.com/mit-pdos/xv6-riscv>
- book source: <https://github.com/mit-pdos/xv6-riscv-book>

작은 교육용 kernel에서 trap, process, scheduler, address space, lock, filesystem과 device path가 실제 코드로 연결되는 과정을 볼 수 있습니다. 다음 순서로 읽습니다.

```text
1. 본문의 상태 전이와 불변식을 먼저 적습니다.
2. 그 상태를 소유하는 xv6 구조체를 찾습니다.
3. 상태를 바꾸는 함수와 lock을 표시합니다.
4. 정상 경로와 실패·종료 경로를 함께 따라갑니다.
5. 본문 모델이 생략한 hardware·multiprocessor 조건을 기록합니다.
```

## Linux kernel 공식 문서

Linux는 원리를 구현한 하나의 현재 시스템입니다. 문서의 kernel version과 configuration을 확인하고 다른 운영체제에 그대로 일반화하지 않습니다.

### scheduler와 실행 상태

- Scheduler 문서 색인: <https://docs.kernel.org/scheduler/index.html>
- EEVDF 설명: <https://docs.kernel.org/scheduler/sched-eevdf.html>

단순 FCFS·RR·MLFQ 모델과 실제 Linux scheduler의 state, fairness 목표와 wakeup preemption을 비교할 때 사용합니다.

### locking과 memory barrier

- Locking 문서: <https://docs.kernel.org/locking/index.html>
- Memory barrier: <https://docs.kernel.org/core-api/wrappers/memory-barriers.html>

kernel execution context, spinlock, sleep 가능한 lock과 hardware ordering의 연결을 확인합니다. 언어 atomic 규칙과 kernel primitive를 같은 계층으로 섞지 않습니다.

### memory management

- Memory management 색인: <https://docs.kernel.org/mm/index.html>
- Page table 개요: <https://docs.kernel.org/mm/page_tables.html>

address space, fault, reclaim, COW와 page cache가 실제 하위 시스템에서 어떻게 연결되는지 확인합니다. page-table bit와 TLB hardware 자체는 컴퓨터 구조 자료를 함께 읽습니다.

### virtual filesystem과 writeback

- VFS: <https://docs.kernel.org/filesystems/vfs.html>
- Filesystem 문서 색인: <https://docs.kernel.org/filesystems/index.html>

inode, dentry, file object, page cache와 filesystem operation의 책임을 확인합니다. API 호출 성공과 crash durability를 구분해 읽습니다.

### device와 DMA

- DMA API 안내: <https://docs.kernel.org/core-api/dma-api-howto.html>
- DMA API 참조: <https://docs.kernel.org/core-api/dma-api.html>
- Driver API 색인: <https://docs.kernel.org/driver-api/index.html>

CPU virtual address, physical address와 device-visible address가 다른 이유, DMA mapping direction, buffer lifetime과 completion 경계를 확인합니다.

## 컴퓨터 구조와의 경계

다음 질문은 컴퓨터 구조 가이드가 주로 소유합니다.

```text
page-table walk를 hardware가 어떤 단계로 수행합니까?
TLB는 어떤 tag와 replacement를 사용합니까?
cache coherence와 store buffer는 어떤 관찰 순서를 만듭니까?
interrupt와 privilege transition이 ISA에 어떻게 표현됩니까?
IOMMU가 device address를 어떻게 변환합니까?
```

운영체제 가이드에서는 이러한 mechanism이 존재한다는 사실을 전제로 mapping 변경, fault 처리, scheduler와 resource lifetime 정책을 설명합니다.

## 실제 source를 읽는 기록 양식

```text
대상 repository와 commit:
configuration:
사용자에게 보이는 계약:
상태 object와 소유자:
정상 상태 전이:
lock과 reference:
block 가능한 지점:
interrupt·worker 경로:
실패와 rollback:
관측 지점과 metric:
본문 모델에서 생략한 조건:
```

함수 한 개나 구조체 이름만 보고 전체 정책을 단정하지 않습니다. scheduler, reclaim, writeback과 device completion은 여러 실행 문맥과 background worker에 걸쳐 동작합니다.

## `kernel-model` 후속 확장

다음 확장은 현재 저장소의 운영체제 범위 안에 있습니다.

1. lifecycle 모델에 timeout, cancellation과 여러 wait channel 선택을 추가합니다.
2. scheduler에 선점형 SJF, priority inheritance와 다중 CPU ready queue를 추가합니다.
3. synchronization 모델에 reader-writer policy와 barrier generation failure를 추가합니다.
4. paging 모델에 working-set 추정, dirty writeback와 pinned frame을 추가합니다.
5. filesystem 모델에 safe replace crash point와 generation manifest를 추가합니다.
6. device 모델에 reset generation, partial completion과 queue backpressure를 추가합니다.
7. 각 확장 전에 잘못된 snapshot과 최소 반례 fixture를 먼저 작성합니다.

다단계 page-table hardware, TLB replacement와 cache coherence 구현은 컴퓨터 구조 가이드의 exercise로 확장하는 편이 경계가 명확합니다.
