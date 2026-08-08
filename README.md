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

학습자는 `skeleton/`에서 구현하고, 완료한 뒤 `reference/`와 설계 선택을 비교합니다.

```sh
./scripts/new-workspace.sh exercises/kernel-model
make -C exercises/kernel-model verify
```

`new-workspace.sh`는 skeleton을 `workspace/`에 한 번만 복사하며 기존 workspace, symlink나 저장소 밖 경로를 덮어쓰지 않습니다.
`make clean`은 build와 source cache만 제거하며 ignored `.guide/`와 학습자의 `workspace/` bytes·mode·symlink를 보존합니다.

## 빠른 참조

- [용어집](reference/glossary.md)
- [정책과 불변식 점검표](reference/policy-and-invariant-checklists.md)
- [추가 읽을거리](reference/further-reading.md)

이 저장소의 중심 질문은 “실제 Linux가 어떤 구조체 이름을 사용하는가”가 아니라 “누가 상태를 소유하고, 어떤 사건이 상태를 바꾸며, 실패 중에도 무엇이 항상 참이어야 하는가”입니다.
