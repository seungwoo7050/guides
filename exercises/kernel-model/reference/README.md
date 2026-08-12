# 기준 구현 안내

기준 구현은 운영체제의 실제 커널 자료구조를 재현하지 않습니다. 한 CPU, 정수 tick, 페이지당 정수 값 하나, 단일 디렉터리와 단일 장치 큐라는 제한된 모델에서 상태 전이와 불변식을 명확히 보여 줍니다.

## 권장 구현 순서

이 `reference/` 전체가 하나의 annotation scope입니다. 번호는 source order나 실제 Git history가 아니라 **learning-oriented recommended construction order**이며 파일마다 다시 시작하지 않습니다. source comment가 각 단계의 authoritative anchor이고 이 표는 파일·symbol과 의존 관계를 한곳에 모읍니다. 이 project에는 generator, package/dependency init이나 framework bootstrap이 없으므로 `Implementation 0`이 없습니다. `make`, checkpoint 실행과 fixture CLI는 검증·실행 명령이며 중간 construction 단계가 아닙니다.

| 단계 | 파일·symbol | 책임과 다음 의존성 |
|---:|---|---|
| 1 | `lifecycle.py:TaskState` | task, CPU와 queue 위치의 상태 vocabulary |
| 1-1 | `KernelState.add` | `NEW → READY → RUNNING` 진입 전이 |
| 1-2 | `KernelState.block` | block, wakeup, preempt와 exit의 배타적 위치 전이 |
| 1-3 | `KernelState.assert_invariants` | 위치·wait metadata·snapshot 불변식 |
| 2 | `synchronization.py:WaitToken` | condition 사건 generation과 대기 등록 state |
| 2-1 | `ConditionChannel.commit_wait` | check-register 사이 lost wakeup 방지 |
| 2-2 | `CountingSemaphore` | permit owner, FIFO waiter와 직접 handoff |
| 3 | `scheduler.py:JobSpec` | workload, tick과 metric vocabulary |
| 3-1 | `simulate` | 검증된 runtime scheduling state |
| 3-2 | `choose` | policy 선택과 deterministic tie-break |
| 3-3 | scheduling tick loop | arrival부터 completion까지의 사건 순서 |
| 4 | `deadlock.py:find_wait_cycle` | 단일 인스턴스 wait-for graph |
| 4-1 | `visit` | DFS cycle reconstruction |
| 4-2 | `detect_deadlocked` | 다중 인스턴스 reduction |
| 4-3 | `safe_sequence` | maximum-need avoidance 판정 |
| 5 | `paging.py:FaultKind` | fault, PTE, frame와 address-space vocabulary |
| 5-1 | `MemoryManager` | mapping과 frame allocator ownership |
| 5-2 | `read`/`write` | mapping·permission·presence·COW 판정 순서 |
| 5-3 | `fork` | COW share와 refcount 기반 회수 |
| 5-4 | `assert_invariants` | PTE/frame/refcount·snapshot 불변식 |
| 5-5 | `simulate_replacement` | FIFO, LRU와 Clock 정책 실험 |
| 6 | `filesystem.py:Inode` | live cache/namespace와 durable state 분리 |
| 6-1 | `FileSystemModel.create` | namespace·inode mutation |
| 6-2 | `fsync_file` | file data와 directory durability·crash |
| 6-3 | `apply_operation` | journal replay operation 경계 |
| 6-4 | `snapshot` | live/durable 관찰 계약 |
| 6-5 | `assert_invariants` | link count, reachability와 clean data |
| 7 | `journal.py:JournalRecord` | append-only transaction log state |
| 7-1 | `Journal.begin` | txid 수명 시작 |
| 7-2 | `Journal.append` | open transaction operation과 commit 경계 |
| 7-3 | `Journal.recover` | committed-only replay와 duplicate ownership |
| 7-4 | `Journal.validate` | log ordering과 snapshot reconstruction |
| 8 | `device_io.py:RequestState` | request 위치, DMA pin과 completion owner |
| 8-1 | `DeviceQueue.submit` | depth reservation, pending과 in-flight 전이 |
| 8-2 | `DeviceQueue.cancel` | queued/in-flight cancel과 interrupt race |
| 8-3 | `DeviceQueue.reap` | terminal result의 exactly-once 전달 |
| 8-4 | `DeviceQueue.assert_invariants` | queue 위치, pin, owner와 depth 불변식 |
| 9 | `cli.py:_load` | fixture decode·최상위 object 검사와 canonical 성공 출력 경계 |
| 9-1 | `run_lifecycle`과 `run_*` | JSON operation을 domain API로 번역 |
| 9-2 | `build_parser`/`main` | model dispatch와 domain 실행 오류·exit 계약; file/JSON load 오류 변환은 비보장 |
| 9-3 | `kernel-model.py` | package main을 process status로 연결 |

## 구현 선택

- 실행 상태는 작업 객체의 `state`와 각 큐의 위치를 함께 검사합니다.
- 조건 대기는 세대 번호를 사용해 조건 검사와 대기 등록 사이의 사건 유실을 드러냅니다.
- 스케줄러는 도착·깨우기·선택·한 tick 실행·완료 순서로 처리합니다.
- COW는 PTE를 쓰기 금지로 바꾸고 frame refcount를 증가시킵니다.
- 파일 내용의 cache 상태와 이름 매핑의 durable 상태를 분리합니다.
- 장치 완료는 인터럽트 단계에서 buffer pin을 풀고, 사용자 소유자가 결과를 회수할 때 요청 수명을 끝냅니다.
- journal 복구는 commit된 operation의 선택과 중복 적용 방지를 모델링하며, replay 도중 임의 operation이 실패했을 때의 transaction rollback은 모델링하지 않습니다.
- CLI 검사는 fixture의 전체 내부 표현이 아니라 각 `expected` mapping이 선언한 관찰 결과를 비교합니다.

8개 checkpoint는 독립 실행할 수 있습니다.

```sh
python3 ../check.py reference 01-lifecycle
python3 ../check.py reference 06-storage
python3 ../check.py reference 08-cli
```

## 의도적으로 보장하지 않는 것

- 실제 CPU의 명령어, TLB, cache coherence를 모델링하지 않습니다.
- 실제 커널 스케줄러의 시간 단위와 다중 CPU 부하 분산을 재현하지 않습니다.
- 파일시스템 block allocator, B-tree와 실제 on-disk format을 구현하지 않습니다.
- 장치 드라이버 register와 IOMMU page table을 구현하지 않습니다.

기준 구현을 평가할 때는 코드 모양보다 `check.py`가 확인하는 외부 상태와 실패 거부 능력을 기준으로 삼습니다.
