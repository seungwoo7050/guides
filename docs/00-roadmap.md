# 운영체제 원리 학습 경로

이 가이드는 특정 운영체제의 명령과 커널 소스 트리를 외우는 과정이 아닙니다. 운영체제가 여러 실행 주체 사이에서 CPU, 메모리, 저장장치와 장치를 중재할 때 유지하는 **상태**, 사용할 수 있는 **메커니즘**, 후보를 선택하는 **정책**, 실패 중에도 지켜야 하는 **불변식**을 학습합니다.

운영체제 지식은 모든 프로젝트의 선행조건은 아닙니다. 작은 애플리케이션은 필요한 언어와 프레임워크를 먼저 익혀 시작할 수 있습니다. 그러나 다음 질문을 설명해야 하는 순간에는 운영체제 모델이 필요합니다.

- 시스템 호출이 즉시 반환하지 않고 작업을 재우는 이유는 무엇입니까?
- 두 스레드가 각각 올바른 코드를 실행했는데 전체 결과가 틀릴 수 있는 이유는 무엇입니까?
- 메모리를 할당했지만 첫 접근에서 비용이 생기는 이유는 무엇입니까?
- 파일에 쓴 값과 장애 뒤 남는 값이 다를 수 있는 이유는 무엇입니까?
- 장치 요청을 취소했어도 buffer를 즉시 해제할 수 없는 경우는 언제입니까?

## 대상 독자와 선행지식

다음 정도의 프로그래밍 경험을 전제로 합니다.

- 변수, 조건문, 반복문과 함수를 읽을 수 있습니다.
- 배열, queue, set, graph 같은 기본 자료구조를 알고 있습니다.
- 프로그램을 실행하고 오류 출력을 확인할 수 있습니다.
- Python class와 collection을 읽을 수 있으면 상태 모델 실습을 바로 진행할 수 있습니다.
- C11과 POSIX 환경이 있으면 `examples/`의 관찰 프로그램을 실행할 수 있습니다.

Python 자체가 낯설다면 Python 가이드의 객체·collection·module·CLI 부분만 먼저 확인하면 충분합니다. POSIX API 구현법은 C 가이드가 담당하며, 이 가이드는 그 API 아래에서 커널이 관리하는 상태에 집중합니다.

## 이 가이드가 소유하는 범위

이 저장소가 주로 설명하는 영역은 다음과 같습니다.

```text
커널 진입과 사건 분류
프로세스·스레드 상태와 문맥 전환
CPU 스케줄링 정책
block·wakeup·wait queue와 IPC 경계
동시 실행의 원자성·순서·동기화
deadlock·starvation·livelock과 진행 보장
주소 공간·page fault·demand paging·COW
page replacement와 memory pressure
filesystem namespace·page cache·durability·journal recovery
장치 request·interrupt·DMA·completion lifetime
```

다음은 인접 가이드가 주 소유자입니다.

| 주제 | 주 소유 가이드 | 이 가이드에서 다루는 수준 |
|---|---|---|
| ISA, pipeline, cache, TLB hardware, coherence | 컴퓨터 구조 | 운영체제 정책을 이해하는 데 필요한 경계만 요약합니다. |
| `fork`, `exec`, `read`, `write`, signal API 구현 | C | 커널 상태 전이의 원인으로만 사용합니다. |
| 명령, path, process, FD와 service 상태 관찰 | Unix 시스템 | 운영체제 모델을 실제 관찰값에 연결할 때 참조합니다. |
| 언어별 atomic API와 정확한 memory model | C, C++, Java | acquire·release의 공통 직관까지만 다룹니다. |
| shell pipeline·redirection 문법 | Shell scripting | pipe와 block/wakeup의 운영체제 경계만 설명합니다. |

이 경계 덕분에 페이지 테이블 walk나 C11 memory order를 이 저장소에서 다시 전체 과정으로 가르치지 않습니다. 대신 커널이 page fault를 어떤 상태 전이로 처리하고, wait queue가 어떤 불변식을 지켜야 하는지에 집중합니다.

## 권장 읽기 순서

### 1부: 경계와 실행

| 순서 | 문서 | 중심 질문 | 연결 실습 |
|---:|---|---|---|
| 1 | [커널 경계와 사건](01-boundary-and-execution/01-kernel-boundary-and-events.md) | 프로그램은 언제, 왜 커널로 제어를 넘깁니까? | `syscall-boundary` |
| 2 | [프로세스, 스레드와 문맥 전환](01-boundary-and-execution/02-processes-threads-and-context-switches.md) | 한 실행 주체는 어떤 상태를 소유합니까? | `kernel-model/lifecycle.py` |
| 3 | [CPU 스케줄링](01-boundary-and-execution/03-cpu-scheduling.md) | 실행 가능한 후보 중 누구에게 CPU를 줍니까? | `kernel-model/scheduler.py` |
| 4 | [블록, 깨우기와 IPC](01-boundary-and-execution/04-blocking-wakeup-and-ipc.md) | 사건을 기다리는 작업을 어떻게 재우고 놓치지 않고 깨웁니까? | `lifecycle.py`, `synchronization.py` |

### 2부: 동시성과 진행

| 순서 | 문서 | 중심 질문 | 연결 실습 |
|---:|---|---|---|
| 5 | [경쟁, 원자성과 순서](02-concurrency/01-races-atomicity-and-ordering.md) | 개별 연산이 원자적이어도 전체 갱신이 틀릴 수 있는 이유는 무엇입니까? | `lost-update` |
| 6 | [동기화 도구와 조건 대기](02-concurrency/02-synchronization-primitives.md) | mutex, semaphore와 condition variable은 어떤 상태를 보호합니까? | `bounded-buffer`, `synchronization.py` |
| 7 | [데드락과 진행 보장](02-concurrency/03-deadlock-and-progress.md) | 멈춤, 기아와 쓸모없는 움직임을 어떻게 구분합니까? | `deadlock.py`, `dining-cycle` |

### 3부: 가상 메모리 정책

| 순서 | 문서 | 중심 질문 | 연결 실습 |
|---:|---|---|---|
| 8 | [주소 공간과 page fault](03-virtual-memory/01-address-spaces-and-faults.md) | 주소 접근은 언제 정상 폴트이고 언제 보호 오류입니까? | `paging.py`, `page-fault-observer` |
| 9 | [요구 페이징, COW와 교체](03-virtual-memory/02-demand-paging-cow-and-replacement.md) | 어떤 페이지를 들이고, 공유하고, 내보냅니까? | `paging.py`, `cow-observer` |

### 4부: 저장장치와 I/O

| 순서 | 문서 | 중심 질문 | 연결 실습 |
|---:|---|---|---|
| 10 | [파일시스템, page cache와 장애 일관성](04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md) | 현재 보이는 상태와 장애 뒤 남는 상태를 어떻게 분리합니까? | `filesystem.py`, `journal.py` |
| 11 | [장치 I/O, interrupt와 DMA](04-storage-and-io/02-device-io-interrupts-and-dma.md) | 비동기 장치 요청의 buffer와 completion은 언제까지 살아 있어야 합니까? | `device_io.py` |

### 선택 확장

[확장 상태·binary image 실습](80-extended-labs.md)은 주소 변환 산술, MLFQ trace, checksum을 포함한 학습용 filesystem image, descriptor ring ownership을 다룹니다. 핵심 11장과 8개 checkpoint를 완료한 뒤 선택하며 핵심 완료 기준을 대신하지 않습니다.

## 목적별 짧은 경로

처음에는 전체를 순서대로 읽는 편이 가장 자연스럽습니다. 특정 문제를 조사하는 경우에는 다음 경로를 사용할 수 있습니다.

```text
스레드가 멈춤
→ 02 프로세스 상태
→ 04 block/wakeup
→ 06 동기화
→ 07 deadlock

메모리 사용량·fault 급증
→ 08 주소 공간과 fault
→ 09 demand paging과 replacement

파일이 장애 뒤 사라짐
→ 10 filesystem과 durability

장치 요청 취소·timeout
→ 04 block/wakeup
→ 11 device request lifetime
```

짧은 경로로 시작했더라도 생소한 상태나 용어가 나오면 앞 장으로 돌아갑니다. 운영체제 문제는 한 계층의 단어만으로 결론을 내리기보다 사건이 지나가는 상태 경계를 연결해야 합니다.

## 실습의 두 종류

### 사용자 공간 관찰 예제

[`examples/`](../examples/README.md)는 C 프로그램으로 사용자 공간에서 관측 가능한 계약을 확인합니다.

```sh
make -C examples check
make -C examples verify
```

예제는 커널 내부 구현을 증명하지 않습니다. 동일 가상 주소, minor fault 통계, 종료 상태 같은 관찰값으로 모델과 양립하는지 확인할 뿐입니다.

### 결정론적 상태 모델

[`exercises/kernel-model/`](../exercises/kernel-model/README.md)은 실제 시간과 스케줄러 우연성을 제거합니다. 상태 전이를 입력으로 주고, 불변식을 만족하는 결과 또는 명시적인 거부를 확인합니다.

```sh
make -C exercises/kernel-model verify
```

상태 모델에는 다음 두 종류의 입력이 있습니다.

- `fixtures/`: 올바른 정책 실행과 상태 전이를 재현합니다.
- `failure-fixtures/`: 작업 중복, COW 위반, double completion처럼 반드시 거부해야 하는 상태를 제공합니다.

## 완료 기준

이 가이드를 마쳤다면 다음 능력을 설명과 실행 결과로 보여 줄 수 있어야 합니다.

1. system call, exception, fault와 interrupt를 발생 원인과 재개 가능성으로 구분합니다.
2. 실행 주체가 `READY`, `RUNNING`, `BLOCKED` 사이를 이동하는 원인을 추적합니다.
3. 스케줄링 정책을 latency, throughput, fairness와 starvation 위험으로 비교합니다.
4. 조건 검사와 대기 등록이 분리될 때 깨우기 손실이 생기는 이유를 설명합니다.
5. 동기화 도구를 이름이 아니라 보호하는 predicate와 수명으로 선택합니다.
6. deadlock, starvation, livelock과 priority inversion을 서로 구분합니다.
7. not-present fault, protection fault와 COW fault의 복구 책임을 구분합니다.
8. cache에 보이는 write, file durability와 directory durability를 따로 검증합니다.
9. DMA 요청의 제출, 실행, interrupt completion과 사용자 회수 사이에서 buffer 소유권을 추적합니다.
10. 잘못된 snapshot을 불변식 검사로 거부하고 그 이유를 설명합니다.

## 지원 환경과 비보장 범위

필수 검증은 다음 환경을 전제로 합니다.

- POSIX `sh`
- Python 3.12 이상
- `make`
- C11 compiler
- POSIX thread, `fork`, `waitpid`, `getrusage`를 제공하는 Unix 계열 환경

Linux와 macOS에서 동작하도록 구성하며 정확한 page fault 수, scheduler timing과 주소 값은 고정된 정답으로 사용하지 않습니다. Windows에서는 WSL 같은 POSIX 환경이 필요합니다.

이 가이드는 실제 kernel module, device driver, 완전한 filesystem 또는 특정 운영체제 scheduler를 구현하는 과정이 아닙니다. 또한 real-time scheduling, NUMA, distributed filesystem, full memory reclamation과 production kernel debugging은 후속 전문 영역으로 남깁니다.
