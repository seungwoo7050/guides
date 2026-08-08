# 결정론적 커널 상태 모델

이 실습은 실제 커널 코드를 흉내 내는 프로젝트가 아닙니다. 시간·하드웨어·운영체제 구현에 따라 달라지는 요소를 제거하고, 운영체제가 관리하는 **상태**, 후보를 고르는 **정책**, 중간 실패에도 지켜야 하는 **불변식**을 Python으로 구현합니다.

## 목표

- 실행·동기화·스케줄링·deadlock·메모리·storage·device 상태를 8개 checkpoint로 구현합니다.
- 정상 fixture의 선언된 결과와 잘못된 snapshot의 정확한 거부 이유를 함께 검증합니다.
- 비종료, 경로 이탈, 중복 test와 중복 assertion까지 checker 품질 계약으로 다룹니다.

## 시작 방법

저장소 루트에서 학습용 작업 공간을 만듭니다.

```sh
./scripts/new-workspace.sh exercises/kernel-model
cd exercises/kernel-model/workspace
```

작업 공간은 `skeleton/`의 현재 파일을 복사하며 기존 `workspace/`를 덮어쓰지 않습니다. 기준 구현을 바로 수정하지 말고 단계별로 자신의 구현을 완성합니다.

루트에서 skeleton 계약, 기준 구현과 실패 fixture를 모두 검사할 수 있습니다.

```sh
make -C exercises/kernel-model check
```

모든 JSON fixture와 Python bytecode 검사까지 실행합니다.

```sh
make -C exercises/kernel-model verify
```

자신의 `workspace/` 구현은 reference와 같은 공개 계약으로 검사합니다.

```sh
make -C exercises/kernel-model workspace-test
```

## 체크포인트

| checkpoint | 모듈 | 구현할 모델 | 연결 문서 |
|---|---|---|---|
| `01-lifecycle` | `lifecycle.py` | `NEW`, `READY`, `RUNNING`, `BLOCKED`, `TERMINATED`와 큐 위치 불변식 | [프로세스와 문맥 전환](../../docs/01-boundary-and-execution/02-processes-threads-and-context-switches.md) |
| `02-synchronization` | `synchronization.py` | 조건 검사와 대기 등록 사이의 깨우기 손실, 세마포어 허가 전달 | [블록·깨우기·IPC](../../docs/01-boundary-and-execution/04-blocking-wakeup-and-ipc.md) |
| `03-scheduler` | `scheduler.py` | FCFS, SJF, 우선순위, RR, MLFQ와 I/O wakeup | [CPU 스케줄링](../../docs/01-boundary-and-execution/03-cpu-scheduling.md) |
| `04-deadlock` | `deadlock.py` | 대기 그래프 순환, 다중 인스턴스 탐지, 안전 순서 | [데드락과 진행](../../docs/02-concurrency/03-deadlock-and-progress.md) |
| `05-paging` | `paging.py` | not-present 폴트, 보호 오류, COW와 FIFO·LRU·Clock | [주소 공간과 폴트](../../docs/03-virtual-memory/01-address-spaces-and-faults.md), [요구 페이징과 교체](../../docs/03-virtual-memory/02-demand-paging-cow-and-replacement.md) |
| `06-storage` | `filesystem.py`, `journal.py` | page cache와 durable 상태, commit된 저널만 복구 | [파일시스템과 장애 일관성](../../docs/04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md) |
| `07-device-io` | `device_io.py` | 요청 큐, DMA pin, 인터럽트 완료, 취소와 회수 | [장치 I/O와 DMA](../../docs/04-storage-and-io/02-device-io-interrupts-and-dma.md) |
| `08-cli` | `cli.py` | JSON 입력을 모델에 연결하고 `expected` 결과를 출력 | [학습 경로](../../docs/00-roadmap.md) |

checkpoint 하나만 실행할 때는 저장소 루트에서 다음 형식을 사용합니다.

```sh
make checkpoint-check IMPL=workspace CHECKPOINT=01-lifecycle
make checkpoint-check IMPL=workspace CHECKPOINT=02-synchronization
make checkpoint-check IMPL=workspace CHECKPOINT=03-scheduler
make checkpoint-check IMPL=workspace CHECKPOINT=04-deadlock
make checkpoint-check IMPL=workspace CHECKPOINT=05-paging
make checkpoint-check IMPL=workspace CHECKPOINT=06-storage
make checkpoint-check IMPL=workspace CHECKPOINT=07-device-io
make checkpoint-check IMPL=workspace CHECKPOINT=08-cli
```

## 단계별 완료 계약

각 단계는 단순히 예시 출력과 같은 문자열을 만드는 것으로 끝나지 않습니다.

```text
상태: 어떤 객체가 어떤 상태를 소유합니까?
전이: 누가 어떤 전이를 요청할 수 있습니까?
불변식: 한 객체가 동시에 존재할 수 없는 위치는 어디입니까?
부분 실패: 전이 도중 실패하면 이전 상태와 새 상태 중 무엇이 남습니까?
검증: 잘못된 snapshot을 실제로 거부합니까?
```

`failure-fixtures/`에는 동일 작업이 두 큐에 동시에 존재하거나, 공유 COW 프레임이 쓰기 가능이거나, DMA 요청이 두 상태에 동시에 놓이는 등 의도적으로 잘못된 상태가 있습니다. 기준 구현은 이 상태를 모두 거부해야 합니다.

## skeleton과 reference의 사용법

- [`skeleton/README.md`](skeleton/README.md)는 구현 순서와 공개 인터페이스를 설명합니다.
- [`reference/README.md`](reference/README.md)는 구현을 마친 뒤 비교해야 할 설계 선택과 비보장 범위를 설명합니다.
- `fixtures/`는 정상 실행 입력입니다.
- `failure-fixtures/`는 불변식 검사가 잡아야 하는 상태입니다.

reference를 먼저 복사하면 테스트는 통과할 수 있지만 정책 선택과 불변식을 설명하는 능력은 생기지 않습니다. 각 단계의 상태표를 먼저 작성하고, 자신의 구현이 통과한 뒤에만 reference와 비교합니다.

## 완료 기준

- 8개 checkpoint를 순서대로 통과하고 마지막 `all` 검사에서 reference와 같은 공개 계약을 만족합니다.
- 정상 fixture 9개의 `expected` subset과 failure fixture 8개의 `expected_error`를 설명합니다.
- 각 checkpoint마다 상태표, 허용 전이, 하나의 잘못된 snapshot과 거부 이유를 기록합니다.
- checker timeout 안에 모든 입력이 종료하고 생성한 workspace 밖 source를 바꾸지 않습니다.

## 자기 설명

- 한 작업 또는 request가 두 상태 위치에 동시에 있으면 어떤 전이의 원자성이 깨진 것입니까?
- 정상 completion, cancel과 timeout이 경쟁할 때 마지막 자원 회수 권한은 어떻게 하나로 정합니까?
- fixture의 `expected`가 전체 implementation snapshot과 똑같을 필요 없이 관찰 계약만 담는 이유는 무엇입니까?
- skeleton, reference와 failure fixture를 함께 검사해야 test의 거짓 양성을 줄일 수 있는 이유는 무엇입니까?

## 검증

```sh
make -C exercises/kernel-model check
make -C exercises/kernel-model verify
```

`KERNEL_MODEL_TIMEOUT=1`처럼 양수 제한을 줄여 checker timeout 동작을 시험할 수 있습니다. 0, 음수와 숫자가 아닌 값은 입력 오류로 거부합니다.
