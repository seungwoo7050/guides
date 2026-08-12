# 누적 실습: 프로세서 상태 모델

명령 하나의 최종 결과만 확인하면 파이프라인 정지, 캐시 교체, 주소 변환과 추측 실행의 오류를 설명하기 어렵습니다. `processor-model`은 비트 표현에서 멀티코어 일관성까지 이어지는 상태 변화를 작은 입력으로 재현합니다. Python 3.12 이상이면 외부 패키지나 교차 컴파일러 없이 실행할 수 있습니다.

`Tiny-RISC`는 실제 RISC-V, MIPS 또는 다른 상용 ISA의 바이너리와 호환되지 않습니다. 명령 의미, 데이터패스와 상태 전이를 학습하기 위한 교육용 ISA이며 정확한 계약은 [실습 ISA 명세](spec/tiny-risc-isa.md)에 있습니다.

## 목표

- 비트 표현부터 캐시 일관성까지 각 계층의 상태와 불변식을 코드로 구현합니다.
- 같은 공개 검사를 사용해 미완성 skeleton과 완성 reference의 차이를 관찰합니다.
- 성능 수치와 기능 정확성을 분리하고 재현 가능한 증거로 설명합니다.

## 작업 공간 만들기

저장소 루트에서 다음을 실행합니다.

```sh
cd exercises/processor-model
../../scripts/new-workspace.sh .
```

공용 스크립트는 `skeleton/`의 실제 파일만 `workspace/`로 복사합니다. symlink나 기존 작업 경로를 만나면 학습자 파일을 보호하기 위해 종료 상태 2로 끝납니다. `prepare.sh`와 `verify.sh`는 학습자의 `workspace/`를 삭제하거나 덮어쓰지 않습니다.

## 장별 학습·검증 순서

Stage 01~08의 `stage-NN` 대상은 해당 장까지의 Python 테스트를 누적 실행합니다. 아직 읽지 않은 뒤 장의 미구현 함수 때문에 현재 장 검사가 실패하지 않으며 이전 장의 회귀는 함께 확인합니다. Stage 09는 workspace source를 수정하지 않는 C compiler 관찰 checkpoint이고, Stage 10은 Stage 08까지의 Python 회귀에 coherence 검사를 더합니다.

| 장 | 직접 수행 | 수정 위치 | 새로 확인하는 상태 | 검사 명령 |
|---:|---|---|---|---|
| 01 | 고정 폭 산술 구현 | `workspace/processor_model/bits.py` | 정수, carry·overflow, IEEE 754 필드 | `make stage-01 EXERCISE_IMPL=workspace` |
| 02 | Tiny-RISC 실행 구현 | `workspace/processor_model/isa.py` | 레지스터, 메모리, 분기와 정렬 예외 | `make stage-02 EXERCISE_IMPL=workspace` |
| 03 | 성능식 구현 | `workspace/processor_model/perf.py` | CPU 시간, Amdahl과 AMAT | `make stage-03 EXERCISE_IMPL=workspace` |
| 04 | 제어표 구현 | `workspace/processor_model/control.py` | 명령별 데이터패스 제어 신호 | `make stage-04 EXERCISE_IMPL=workspace` |
| 05 | 파이프라인 구현 | `workspace/processor_model/pipeline.py` | 전달, load-use 정지와 분기 비우기 | `make stage-05 EXERCISE_IMPL=workspace` |
| 06 | 캐시 구현 | `workspace/processor_model/cache.py` | LRU, write-back과 3C 실패 분류 | `make stage-06 EXERCISE_IMPL=workspace` |
| 07 | 주소 변환 구현 | `workspace/processor_model/vm.py` | TLB, 페이지 테이블, 권한과 무효화 | `make stage-07 EXERCISE_IMPL=workspace` |
| 08 | 예측기와 ROB 구현 | `workspace/processor_model/predictor.py`, `rob.py` | 2비트 예측, aliasing, 순차 반영과 precise exception | `make stage-08 EXERCISE_IMPL=workspace` |
| 09 | [`vectorization-report`](../../examples/vectorization-report/README.md)의 checksum과 compiler 보고서 설명 | — | 벡터화된 loop, 실패한 loop와 compiler 근거 | `make stage-09` |
| 10 | MESI 구현 | `workspace/processor_model/coherence.py` | invalidation, write-back과 거짓 공유 | `make stage-10 EXERCISE_IMPL=workspace` |

현재 디렉터리에서 실행하는 예는 다음과 같습니다.

```sh
make stage-01 EXERCISE_IMPL=workspace
make stage-05 EXERCISE_IMPL=workspace
make stage-10 EXERCISE_IMPL=workspace
```

저장소 루트에서는 다음처럼 실행합니다.

```sh
make -C exercises/processor-model stage-05 EXERCISE_IMPL=workspace
```

## 전체 구현 검사

모든 Python 모듈을 완성한 뒤 전체 테스트를 실행합니다.

```sh
make exercise-test EXERCISE_IMPL=workspace
```

reference 전체와 skeleton의 의도된 미완성 상태는 다음 명령으로 확인합니다. 이 명령은 learner workspace 완료 검사가 아닙니다.

```sh
make check
```

저장소의 문서·예제까지 포함한 전체 검증은 루트에서 실행합니다.

```sh
./verify.sh
```

`verify.sh`는 `prepare.sh`를 대신 실행하지 않으며 learner workspace도 검사하지 않습니다. 따라서 `make exercise-test EXERCISE_IMPL=workspace`와 루트의 `./prepare.sh`, `./verify.sh`를 각각 실행해야 합니다.

## reference 관찰과 직접 구현을 구분합니다

다음 명령은 완성된 reference의 여러 계층을 한 번에 보여 주는 전체 개요입니다.

```sh
make observe
```

1장 작업을 시작하는 명령으로 사용하지 않습니다. 아직 읽지 않은 파이프라인, 캐시, 주소 변환과 일관성 출력이 함께 나오기 때문입니다. 좁은 reference CLI는 source를 열지 않고 결과 형태만 보는 선택적 black-box oracle입니다.

```sh
python3 reference/processor-model.py bits add 127 1 --width 8
python3 reference/processor-model.py perf amdahl --fraction 0.4 --speedup 8
```

결과를 예상하고 workspace를 구현해 해당 `stage-NN`을 실행한 뒤에 reference source를 엽니다. 통과하지 않는 상태 전이와 자신의 설계 선택만 비교하며 reference 전체를 workspace로 복사하지 않습니다.

## 모듈별 공개 역할

| 모듈 | 역할 |
|---|---|
| `bits.py` | 값과 고정 폭 비트 패턴의 변환 |
| `isa.py` | 구조적 상태를 바꾸는 순차 명령 실행 |
| `perf.py` | 단위가 명시된 성능식 계산 |
| `control.py` | Tiny-RISC 명령별 제어표 |
| `pipeline.py` | 5단계 파이프라인의 정지·전달·비우기 |
| `cache.py` | set·tag·dirty bit와 교체 상태 |
| `vm.py` | TLB와 페이지 테이블의 주소 변환 |
| `predictor.py` | PC별 2비트 포화 계수기 |
| `rob.py` | 비순차 완료와 프로그램 순서 반영 |
| `coherence.py` | 단순화한 안정 MESI 상태 전이 |

모델의 사이클 수를 실제 x86-64, Arm 또는 RISC-V 프로세서의 타이밍으로 사용하지 않습니다. 실행 port, 물리 레지스터, transient coherence state, prefetcher와 장치 지연은 이 모델이 의도적으로 생략한 별도 계약입니다.

## 권장 구현 순서

다음 번호는 Git history나 runtime 호출 순서가 아니라 `reference/` 전체를 다시 구성할 때의 학습 지향 권장 순서입니다. 번호는 파일마다 다시 시작하지 않으며 package와 얇은 CLI entrypoint를 하나의 scope로 봅니다. 별도 framework, dependency 또는 project generator가 없으므로 0 단계는 없습니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---|---|---|
| 1 | `bits.py::_validate_width` | 폭, mask와 signed/unsigned 해석이 공유하는 비트 불변식 |
| 1-1 | `bits.py::add_fixed` | carry·unsigned overflow와 signed overflow의 분리 |
| 1-2 | `bits.py::_float_fields` | IEEE 754 raw field 분해와 값 분류 |
| 2 | `isa.py::Instruction` | 불변 명령 표현, label과 피연산자 검증 |
| 2-1 | `isa.py::sources_and_destination` | ISA 의미를 hazard metadata와 공유하는 연결점 |
| 2-2 | `isa.py::Machine` | register·memory·PC 소유권과 정렬·폭 불변식 |
| 3 | `perf.py::cpu_time` | 단위가 드러나는 CPU time, Amdahl과 AMAT 순수 모델 |
| 4 | `control.py::CONTROL` | ISA 실행 의미와 일치하는 선언적 제어표 |
| 5 | `pipeline.py::_has_data_hazard` | source/destination metadata에 따른 전달·정지 정책 |
| 5-1 | `pipeline.py::simulate` | snapshot, retire, flush, stall, advance와 fetch 전이 순서 |
| 6 | `cache.py::CacheSimulator` | 실제 set 상태, 분류용 shadow 상태와 seen 집합의 소유권 |
| 6-1 | `cache.py::CacheSimulator.access` | 주소 분해, 3C 분류, dirty eviction과 event 기록 |
| 7 | `vm.py::VirtualMemorySimulator` | 원본 page table과 파생 TLB cache의 수명 경계 |
| 7-1 | `vm.py::VirtualMemorySimulator._translate` | TLB, walk, 권한과 physical address 결정 순서 |
| 7-2 | `vm.py::VirtualMemorySimulator.run` | mapping 변경 뒤 stale TLB entry 무효화 |
| 8 | `predictor.py::TwoBitPredictor` | 정렬 PC index, aliasing과 포화 계수기 갱신 |
| 9 | `rob.py::ReorderBuffer` | tag, capacity, issue와 비순차 complete 상태 |
| 9-1 | `rob.py::ReorderBuffer.retire` | ready head만 순차 반영하고 fault 뒤 younger state 폐기 |
| 10 | `coherence.py::MESISimulator` | block별 안정 MESI state vector와 모델 범위 |
| 10-1 | `coherence.py::MESISimulator.access` | bus event, invalidation·write-back과 전후 증거 |
| 11 | `cli.py::build_parser` | 공개 command와 option schema |
| 11-1 | `cli.py::run` | path·trace 입력 위임, JSON·text 출력과 main의 exit 2 정규화 |

## 완료 기준

- 각 단계가 이전 단계의 회귀를 함께 확인합니다.
- 뒤 장의 미구현 함수가 현재 단계에서 먼저 호출되지 않습니다.
- 제어표와 ISA 실행기가 같은 명령 의미를 사용합니다.
- 파이프라인과 ROB가 잘못된 젊은 명령의 구조적 상태 반영을 막습니다.
- cache, TLB와 coherence의 상태 수명을 서로 다른 계층으로 설명합니다.
- 전체 완료 뒤 `make exercise-test EXERCISE_IMPL=workspace`가 성공합니다.

## 자기 설명

- 파이프라인의 완료 순서와 ROB의 반영 순서를 분리해야 precise exception을 보장할 수 있는 이유는 무엇인가요?
- TLB, cache와 coherence가 각각 소유하는 상태와 무효화 조건은 어떻게 다른가요?
- stage-09의 체크섬과 compiler 벡터화 보고서가 서로 다른 종류의 증거인 이유는 무엇인가요?

## 검증

저장소 루트에서 단계별 검사와 전체 검증을 실행합니다.

```sh
make stage-01 EXERCISE_IMPL=workspace
make stage-09
make stage-10 EXERCISE_IMPL=workspace
./prepare.sh
./verify.sh
```
