# 운영체제 원리 가이드

운영체제는 CPU, 메모리, 저장장치와 입출력 장치를 여러 실행 주체가 함께 사용하도록 중재합니다. 이 저장소는 특정 명령이나 커널 구조체를 암기하는 대신 **메커니즘, 정책, 상태, 불변식과 관측 근거**를 연결합니다.

시작점은 [운영체제 원리 학습 경로](docs/00-roadmap.md)입니다. 전체 과정은 다음 네 부분으로 구성됩니다.

```text
경계와 실행
→ 동시성과 진행
→ 가상 메모리 정책
→ 저장장치와 I/O
```

## 준비와 전체 검증

Python 3.12 이상, C11 compiler, POSIX shell, `make`, `git`과 `rsync`가 필요합니다. checkout 직후에는 source를 바꾸지 않는 준비 검사를 실행합니다.

```sh
./prepare.sh
```

`prepare.sh`는 문서·실습 source를 생성하거나 삭제하지 않습니다. 임시 디렉터리에서 `make`, C11·sanitizer build, `rsync`, timeout runner와 macOS/Linux의 배타적 directory rename을 실제로 probe합니다. 현재 HEAD, raw Git index, source의 파일·directory mode·symlink fingerprint와 정확한 tool version을 ignored `.guide/operating-systems/prepared.json` marker에 기록합니다. 같은 상태에서 다시 실행해도 source와 결과는 같습니다.

준비가 끝난 동일한 상태에서 저장소 전체를 격리된 임시 복사본으로 검사합니다.

```sh
./verify.sh
```

`verify.sh`는 prepare를 대신하지 않으며 marker와 현재 상태가 다르면 즉시 중단합니다. 검증 로그는 기본적으로 저장소 밖 임시 디렉터리에 남고 `VERIFY_LOG=/absolute/path`로 위치를 지정할 수 있습니다. leaf symlink와 저장소 내부 log는 target을 건드리기 전에 거부합니다. 문서·링크·정확한 레이아웃, validator 음수 테스트, raw index·`make clean` 보존, workspace 경쟁 안전성, C 예제와 sanitizer, 8개 checkpoint, skeleton·기준 구현·fixture·timeout·signal cleanup 계약을 한 번에 검사합니다.

marker 없이도 현재 source의 공개 검사를 빠르게 실행할 수 있습니다.

```sh
make check
```

## 전체 학습 순서

roadmap과 핵심 문서의 `1`부터 `11`은 **읽기 순서**이고, 상태 모델의 `01`부터 `08`은 **권장 구현 순서**입니다. 두 번호는 역할과 의존성이 다르므로 서로 맞추기 위해 checkpoint를 다시 번호 매기지 않습니다. 첫 번째 읽기에서는 핵심 문서를 `1 → 11`로 읽고 연결된 C 예제만 관찰합니다. 문서 안의 workspace 명령은 이때 실행하지 않고, 아래 명령으로 안전한 workspace를 한 번 만든 뒤 두 번째 구현 pass에서 checkpoint를 `01 → 08`로 누적 실행합니다.

```sh
./scripts/new-workspace.sh exercises/kernel-model
```

각 checkpoint는 자신의 workspace가 통과한 뒤에만 같은 이름의 `reference/` 모듈과 비교합니다. `make -C exercises/kernel-model verify`는 저장소가 제공하는 skeleton과 reference를 검사하는 maintainer 명령이며 학습자의 workspace 완료를 판정하지 않습니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 관찰 | [1. 커널 경계](docs/01-boundary-and-execution/01-kernel-boundary-and-events.md), [5. 경쟁과 원자성](docs/02-concurrency/01-races-atomicity-and-ordering.md), [6. 동기화](docs/02-concurrency/02-synchronization-primitives.md), [7. 진행](docs/02-concurrency/03-deadlock-and-progress.md), [8. 주소 공간](docs/03-virtual-memory/01-address-spaces-and-faults.md), [9. 요구 페이징](docs/03-virtual-memory/02-demand-paging-cow-and-replacement.md) | `syscall-boundary`, `lost-update`, `bounded-buffer`, `dining-cycle`, `page-fault-observer`, `cow-observer` | 실행 전 관찰 계약을 쓰고 여섯 프로그램 실행 | — | `make -C examples verify`, `make -C examples sanitizer-check` | 핵심 문서 `1 → 11` 완료 후 workspace 생성 |
| 1 | [2. 프로세스와 문맥 전환](docs/01-boundary-and-execution/02-processes-threads-and-context-switches.md), [4. 블록과 깨우기](docs/01-boundary-and-execution/04-blocking-wakeup-and-ipc.md) | — | `01-lifecycle` | `exercises/kernel-model/workspace/kernel_model/lifecycle.py` | `make checkpoint-check IMPL=workspace CHECKPOINT=01-lifecycle` | `exercises/kernel-model/reference/kernel_model/lifecycle.py` 비교 후 `02-synchronization` |
| 2 | [4. 블록과 깨우기](docs/01-boundary-and-execution/04-blocking-wakeup-and-ipc.md), [5. 경쟁과 원자성](docs/02-concurrency/01-races-atomicity-and-ordering.md), [6. 동기화](docs/02-concurrency/02-synchronization-primitives.md) | `lost-update`, `bounded-buffer` | `02-synchronization` | `exercises/kernel-model/workspace/kernel_model/synchronization.py` | `make checkpoint-check IMPL=workspace CHECKPOINT=02-synchronization` | `exercises/kernel-model/reference/kernel_model/synchronization.py` 비교 후 `03-scheduler` |
| 3 | [3. CPU scheduling](docs/01-boundary-and-execution/03-cpu-scheduling.md) | — | `03-scheduler` | `exercises/kernel-model/workspace/kernel_model/scheduler.py` | `make checkpoint-check IMPL=workspace CHECKPOINT=03-scheduler` | `exercises/kernel-model/reference/kernel_model/scheduler.py` 비교 후 `04-deadlock` |
| 4 | [7. deadlock과 진행](docs/02-concurrency/03-deadlock-and-progress.md) | `dining-cycle` | `04-deadlock` | `exercises/kernel-model/workspace/kernel_model/deadlock.py` | `make checkpoint-check IMPL=workspace CHECKPOINT=04-deadlock` | `exercises/kernel-model/reference/kernel_model/deadlock.py` 비교 후 `05-paging` |
| 5 | [8. 주소 공간과 fault](docs/03-virtual-memory/01-address-spaces-and-faults.md), [9. 요구 페이징과 교체](docs/03-virtual-memory/02-demand-paging-cow-and-replacement.md) | `page-fault-observer`, `cow-observer` | `05-paging` | `exercises/kernel-model/workspace/kernel_model/paging.py` | `make checkpoint-check IMPL=workspace CHECKPOINT=05-paging` | `exercises/kernel-model/reference/kernel_model/paging.py` 비교 후 `06-storage` |
| 6 | [10. filesystem과 장애 일관성](docs/04-storage-and-io/01-filesystems-page-cache-and-crash-consistency.md) | — | `06-storage` | `exercises/kernel-model/workspace/kernel_model/filesystem.py`, `exercises/kernel-model/workspace/kernel_model/journal.py` | `make checkpoint-check IMPL=workspace CHECKPOINT=06-storage` | `exercises/kernel-model/reference/kernel_model/filesystem.py`, `exercises/kernel-model/reference/kernel_model/journal.py` 비교 후 `07-device-io` |
| 7 | [11. 장치 I/O와 DMA](docs/04-storage-and-io/02-device-io-interrupts-and-dma.md) | — | `07-device-io` | `exercises/kernel-model/workspace/kernel_model/device_io.py` | `make checkpoint-check IMPL=workspace CHECKPOINT=07-device-io` | `exercises/kernel-model/reference/kernel_model/device_io.py` 비교 후 `08-cli` |
| 8 | [roadmap과 앞선 전체 모델](docs/00-roadmap.md) | — | `08-cli` | `exercises/kernel-model/workspace/kernel_model/cli.py` | `make checkpoint-check IMPL=workspace CHECKPOINT=08-cli`, `make -C exercises/kernel-model workspace-test` | `exercises/kernel-model/reference/kernel_model/cli.py` 비교 후 선택 확장 |
| 선택 | [확장 상태·binary image 실습](docs/80-extended-labs.md) | — | 네 주제 중 둘의 expected evidence | 저장소 밖 disposable workspace | 문서의 manual review rubric; official `verify.sh` 대상 아님 | 과정 종료 |

## 실행 예제

[`examples/`](examples/README.md)는 사용자 공간에서 관찰할 수 있는 작은 C 프로그램을 제공합니다.

```sh
make -C examples check
make -C examples verify
```

| 예제 | 관찰할 경계 |
|---|---|
| `syscall-boundary` | system call 성공과 `errno`를 통한 실패 |
| `lost-update` | 개별 atomic load/store와 복합 갱신의 차이 |
| `bounded-buffer` | 조건 predicate와 wait loop |
| `dining-cycle` | 전역 lock order가 순환 대기를 제거하는 방식 |
| `cow-observer` | `fork` 뒤 동일 가상 주소와 분리된 값 |
| `page-fault-observer` | 페이지 첫 접근과 관측 가능한 minor fault 변화 |

## 결정론적 상태 모델

[`exercises/kernel-model/`](exercises/kernel-model/README.md)은 다음 상태를 Python으로 구현합니다.

```text
작업 수명과 wait queue
CPU scheduling과 I/O wakeup
깨우기 손실과 semaphore
wait-for graph와 다중 인스턴스 deadlock
page fault, COW와 replacement
page cache, fsync와 journal recovery
device request, DMA pin과 interrupt completion
```

학습자는 `skeleton/`을 안전하게 복사한 `workspace/`에서 구현하고, 각 checkpoint가 통과한 뒤 `reference/`와 설계 선택을 비교합니다.

```sh
# 위 전체 학습 순서에서 만든 workspace를 계속 사용합니다.
make checkpoint-check IMPL=workspace CHECKPOINT=01-lifecycle
# 8개 checkpoint를 마친 뒤
make -C exercises/kernel-model workspace-test
```

`new-workspace.sh`는 skeleton을 `workspace/`에 한 번만 복사하며 기존 workspace, symlink나 저장소 밖 경로를 덮어쓰지 않습니다.
`make clean`은 build와 source cache만 제거하며 ignored `.guide/`와 학습자의 `workspace/` bytes·mode·symlink를 보존합니다.

## 빠른 참조

이 root-level `reference/`는 용어와 점검표를 빠르게 찾는 문서 모음이며 exercise 답안이 아닙니다. 완료 구현은 `exercises/kernel-model/reference/`에 있습니다.

- [용어집](reference/glossary.md)
- [정책과 불변식 점검표](reference/policy-and-invariant-checklists.md)
- [추가 읽을거리](reference/further-reading.md)

이 저장소의 중심 질문은 “실제 Linux가 어떤 구조체 이름을 사용하는가”가 아니라 “누가 상태를 소유하고, 어떤 사건이 상태를 바꾸며, 실패 중에도 무엇이 항상 참이어야 하는가”입니다.
