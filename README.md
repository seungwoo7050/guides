# 컴퓨터 구조와 성능 모델 가이드

프로그램의 값이 비트 패턴으로 표현되고, 명령어가 데이터패스와 실행 엔진을 지나며, 메모리 접근이 캐시·주소 변환·일관성 제어를 통과하는 흐름을 하나의 학습 경로로 연결합니다. 특정 CPU 제품의 기능을 외우기보다 **소프트웨어에 보이는 구조적 계약**, **내부 상태 전이**, **성능 비용**, **관찰 가능한 근거**를 구분하는 데 집중합니다.

이 저장소의 정본 구조를 준비하고 전체 검증을 실행하는 진입점은 다음 두 명령입니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 source와 Git index를 바꾸지 않고 Python, C11, pthread와 sanitizer 실행 가능성을 확인한 뒤 `.guide/computer-architecture/prepared.json`에 입력 지문을 기록합니다. `verify.sh`는 원본 밖 임시 복사본에서 문서·링크·상태 모델·C 예제·컴파일러 보고서를 검사하고 외부 로그 경로를 출력합니다.

전체 학습 계약과 운영체제·언어 가이드와의 경계는 [학습 로드맵](docs/00-roadmap.md)에 정리되어 있습니다.

## 읽는 순서

### Part 1. 표현, ISA와 성능식

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 01 | [데이터 표현과 산술](docs/01-representation-and-isa/01-data-representation-and-arithmetic.md) | 같은 비트 패턴을 어떤 값으로 해석하며 오버플로와 반올림은 언제 발생합니까? |
| 02 | [ISA, 어셈블리와 프로그램 실행](docs/01-representation-and-isa/02-isa-assembly-and-program-execution.md) | 소프트웨어와 프로세서가 합의하는 명령·레지스터·메모리 계약은 무엇입니까? |
| 03 | [성능식과 측정](docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md) | 실행 시간을 명령어 수, CPI와 클록으로 어떻게 분해하고 검증합니까? |

### Part 2. 순차 실행 엔진

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 04 | [데이터패스와 제어](docs/02-in-order-execution/04-datapath-and-control.md) | 한 명령을 실행하려면 어떤 저장소와 조합 회로가 동작합니까? |
| 05 | [파이프라인과 위험 요소](docs/02-in-order-execution/05-pipeline-hazards-and-branching.md) | 명령을 겹쳐 실행할 때 무엇을 전달·정지·비워야 합니까? |

### Part 3. 메모리 계층

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 06 | [캐시, 지역성과 AMAT](docs/03-memory-hierarchy/06-cache-locality-and-amat.md) | 작은 고속 저장소에 어떤 블록을 두고 실패 비용을 어떻게 계산합니까? |
| 07 | [주소 변환과 TLB](docs/03-memory-hierarchy/07-address-translation-and-tlb.md) | 가상 주소가 물리 주소와 접근 권한으로 어떻게 변환됩니까? |

### Part 4. 병렬 실행

| 장 | 문서 | 중심 질문 |
|---:|---|---|
| 08 | [슈퍼스칼라, 비순차 실행과 추측](docs/04-parallel-execution/08-superscalar-out-of-order-and-speculation.md) | 명령 수준 병렬성을 사용하면서 정확한 구조적 상태를 어떻게 보존합니까? |
| 09 | [SIMD와 데이터 배치](docs/04-parallel-execution/09-simd-vectorization-and-data-layout.md) | 한 명령으로 여러 원소를 처리하려면 반복문과 메모리 배치가 어떤 조건을 만족해야 합니까? |
| 10 | [멀티코어, 캐시 일관성과 거짓 공유](docs/04-parallel-execution/10-multicore-coherence-and-false-sharing.md) | 코어별 캐시가 값을 공유하며 언제 불필요한 일관성 트래픽이 발생합니까? |

장 번호는 학습 checkpoint 번호와 일치합니다. `01~08`은 Python 상태 모델을 누적 구현하고, `09`는 source를 수정하지 않는 벡터화 관찰 checkpoint이며, `10`에서 Python 모델 구현을 다시 이어 MESI까지 완성합니다. `01 → 10` 순서로 진행하면 명령 수준 병렬성, 데이터 수준 병렬성, 코어 수준 병렬성이 마지막 Part에서 차례로 연결됩니다.

## 학습 워크플로와 단계 대응

Stage 01을 시작하기 전에 `scripts/new-workspace.sh`로 `processor-model`의 `workspace/`를 한 번 만듭니다. 학습자가 직접 수정하는 곳은 이 workspace뿐이며 repository-owned `skeleton/`과 `reference/`는 수정하지 않습니다. reference CLI의 출력은 source를 열지 않는 선택적 black-box oracle로 관찰할 수 있지만, reference source는 자신의 예상과 workspace 구현을 먼저 검사한 뒤 비교합니다. 루트의 `reference/`는 답안이 아니라 공식 자료와 계산식을 모은 빠른 참조입니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 01 | [데이터 표현과 산술](docs/01-representation-and-isa/01-data-representation-and-arithmetic.md) | — | [`processor-model` Stage 01](exercises/processor-model/README.md) 고정 폭 산술 | `exercises/processor-model/workspace/processor_model/bits.py` | `make stage-01 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/bits.py` 비교 → 02 |
| 02 | [ISA, 어셈블리와 프로그램 실행](docs/01-representation-and-isa/02-isa-assembly-and-program-execution.md) | — | [`processor-model` Stage 02](exercises/processor-model/README.md) Tiny-RISC 실행 | `exercises/processor-model/workspace/processor_model/isa.py` | `make stage-02 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/isa.py` 비교 → 03 |
| 03 | [성능식과 측정](docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md) | [데이터 배치](examples/layout-benchmark/README.md) | [`processor-model` Stage 03](exercises/processor-model/README.md) 성능식 | `exercises/processor-model/workspace/processor_model/perf.py` | `make stage-03 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/perf.py` 비교 → 04 |
| 04 | [데이터패스와 제어](docs/02-in-order-execution/04-datapath-and-control.md) | — | [`processor-model` Stage 04](exercises/processor-model/README.md) 제어표 | `exercises/processor-model/workspace/processor_model/control.py` | `make stage-04 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/control.py` 비교 → 05 |
| 05 | [파이프라인과 위험 요소](docs/02-in-order-execution/05-pipeline-hazards-and-branching.md) | [분기 벤치마크](examples/branch-benchmark/README.md) | [`processor-model` Stage 05](exercises/processor-model/README.md) 파이프라인 | `exercises/processor-model/workspace/processor_model/pipeline.py` | `make stage-05 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/pipeline.py` 비교 → 06 |
| 06 | [캐시, 지역성과 AMAT](docs/03-memory-hierarchy/06-cache-locality-and-amat.md) | [데이터 배치](examples/layout-benchmark/README.md) | [`processor-model` Stage 06](exercises/processor-model/README.md) 캐시 | `exercises/processor-model/workspace/processor_model/cache.py` | `make stage-06 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/cache.py` 비교 → 07 |
| 07 | [주소 변환과 TLB](docs/03-memory-hierarchy/07-address-translation-and-tlb.md) | — | [`processor-model` Stage 07](exercises/processor-model/README.md) 주소 변환 | `exercises/processor-model/workspace/processor_model/vm.py` | `make stage-07 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/vm.py` 비교 → 08 |
| 08 | [슈퍼스칼라, 비순차 실행과 추측](docs/04-parallel-execution/08-superscalar-out-of-order-and-speculation.md) | — | [`processor-model` Stage 08](exercises/processor-model/README.md) predictor와 ROB | `exercises/processor-model/workspace/processor_model/{predictor,rob}.py` | `make stage-08 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/{predictor,rob}.py` 비교 → 09 |
| 09 | [SIMD와 데이터 배치](docs/04-parallel-execution/09-simd-vectorization-and-data-layout.md) | [벡터화 보고서](examples/vectorization-report/README.md) | checksum과 compiler 보고서 증거 기록 | — | `make stage-09` | 관찰 증거를 설명하고 기록 → 10 |
| 10 | [멀티코어, 캐시 일관성과 거짓 공유](docs/04-parallel-execution/10-multicore-coherence-and-false-sharing.md) | [거짓 공유](examples/false-sharing/README.md) | [`processor-model` Stage 10](exercises/processor-model/README.md) MESI | `exercises/processor-model/workspace/processor_model/coherence.py` | `make stage-10 EXERCISE_IMPL=workspace` | `exercises/processor-model/reference/processor_model/coherence.py` 비교 → 전체 workspace·공식 검증 |

Stage 10 뒤에는 `make -C exercises/processor-model exercise-test EXERCISE_IMPL=workspace`로 learner 구현을 검사하고, 이어서 `./prepare.sh`와 `./verify.sh`로 repository 정본을 검증합니다. 별도 capstone은 없으며 완성한 `processor-model`이 이 branch의 종료 프로젝트입니다.

## 누적 상태 모델 실습

[`processor-model`](exercises/processor-model/README.md)은 고정 폭 산술, Tiny-RISC 실행, 성능식, 데이터패스, 파이프라인, 캐시, TLB, 분기 예측기, 재정렬 버퍼와 MESI를 결정적인 상태 모델로 연결합니다. Tiny-RISC의 정확한 계약은 [실습 ISA 명세](exercises/processor-model/spec/tiny-risc-isa.md)에 있습니다.

```sh
cd exercises/processor-model
../../scripts/new-workspace.sh .
make stage-01 EXERCISE_IMPL=workspace
```

각 `stage-NN`은 해당 장까지의 테스트만 누적 실행합니다. 전체 구현이 끝난 뒤 다음 명령을 사용합니다.

```sh
make exercise-test EXERCISE_IMPL=workspace
```

`make exercise-test EXERCISE_IMPL=workspace`는 학습자 구현을 검사합니다. 완성된 reference와 skeleton의 의도된 미완성 상태는 루트의 `./verify.sh`가 별도로 확인하며, 이 공식 검증은 learner workspace 검사를 대신하지 않습니다.

## 실행 환경

필수 도구는 다음과 같습니다.

- Python 3.12 이상
- C11을 빌드할 수 있는 `cc`
- POSIX 호환 `sh`와 `make`
- POSIX 스레드와 단조 시계를 제공하는 Linux, macOS 또는 WSL2
- Git 저장소

Python 실습은 표준 라이브러리만 사용하므로 별도 패키지 설치가 필요하지 않습니다. Linux `perf`와 하드웨어 성능 계수기는 선택 사항이며 자동 검증의 필수 조건이 아닙니다.

## 관찰 예제

| 예제 | 관찰 대상 |
|---|---|
| [데이터 배치 벤치마크](examples/layout-benchmark/README.md) | 순회 순서와 공간 지역성 |
| [분기 벤치마크](examples/branch-benchmark/README.md) | 예측 가능한 분기와 불규칙한 분기 |
| [벡터화 보고서](examples/vectorization-report/README.md) | 독립 반복문과 순환 의존성이 있는 반복문 |
| [거짓 공유](examples/false-sharing/README.md) | 서로 다른 계수기가 같은 캐시 라인을 공유하는 비용 |

실행 시간 자체는 합격 조건이 아닙니다. 예제는 결과 합계와 실행 계약을 먼저 검사하고, 시간은 CPU·컴파일러·입력 조건과 함께 해석합니다.

## 빠른 참조

- [성능식과 설계 검토표](reference/formulas-and-checklist.md)
- [MIPS와 RISC-V 개념 대응표](reference/mips-riscv-crosswalk.md)
- [버전 기준과 재현 환경](reference/version-baseline.md)
- [공식 명세와 도구 자료](reference/sources.md)

## 범위 경계

- 이 가이드는 ISA, 데이터패스, 파이프라인, 캐시, 주소 변환 하드웨어, 추측 실행, SIMD와 캐시 일관성을 주로 다룹니다.
- 운영체제가 페이지를 언제 배정·회수·교체하는지, copy-on-write와 파일 매핑을 어떻게 관리하는지는 운영체제 가이드의 영역입니다.
- C/C++ atomic, Java `volatile`, lock과 언어별 happens-before 규칙은 해당 언어·동시성 가이드의 영역입니다. 여기서는 그 계약이 ISA의 메모리 순서와 fence에 연결되는 경계까지만 다룹니다.
- 상태 모델의 사이클 수를 실제 x86-64, Arm 또는 RISC-V 코어의 타이밍으로 사용하지 않습니다. 실제 성능 주장은 입력, 빌드 옵션, 하드웨어와 측정 근거를 함께 제시해야 합니다.
