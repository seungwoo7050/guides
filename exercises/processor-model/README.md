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

## 장별 구현 순서

각 `stage-NN` 대상은 해당 장까지의 테스트를 누적 실행합니다. 아직 읽지 않은 뒤 장의 미구현 함수 때문에 현재 장 검사가 실패하지 않으며 이전 장의 회귀는 함께 확인합니다.

| 장 | 구현 파일 또는 관찰 예제 | 새로 확인하는 상태 | 검사 명령 |
|---:|---|---|---|
| 01 | `bits.py` | 고정 폭 정수, carry·overflow, IEEE 754 필드 | `make stage-01 EXERCISE_IMPL=workspace` |
| 02 | `isa.py` | 레지스터, 메모리, 분기와 정렬 예외 | `make stage-02 EXERCISE_IMPL=workspace` |
| 03 | `perf.py` | CPU 시간, Amdahl과 AMAT | `make stage-03 EXERCISE_IMPL=workspace` |
| 04 | `control.py` | 명령별 데이터패스 제어 신호 | `make stage-04 EXERCISE_IMPL=workspace` |
| 05 | `pipeline.py` | 전달, load-use 정지와 분기 비우기 | `make stage-05 EXERCISE_IMPL=workspace` |
| 06 | `cache.py` | LRU, write-back과 3C 실패 분류 | `make stage-06 EXERCISE_IMPL=workspace` |
| 07 | `vm.py` | TLB, 페이지 테이블, 권한과 무효화 | `make stage-07 EXERCISE_IMPL=workspace` |
| 08 | `predictor.py`, `rob.py` | 2비트 예측, aliasing, 순차 반영과 precise exception | `make stage-08 EXERCISE_IMPL=workspace` |
| 09 | C 예제 | SIMD와 데이터 배치는 `examples/`에서 관찰 | `make stage-09` |
| 10 | `coherence.py` | MESI, invalidation, write-back과 거짓 공유 | `make stage-10 EXERCISE_IMPL=workspace` |

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

reference 전체와 skeleton의 의도된 미완성 상태는 다음 명령으로 확인합니다.

```sh
make check
```

저장소의 문서·예제까지 포함한 전체 검증은 루트에서 실행합니다.

```sh
./verify.sh
```

`verify.sh`는 `prepare.sh`를 대신 실행하지 않습니다. 최종 문서 구조가 준비되지 않았으면 먼저 루트에서 `./prepare.sh`를 실행해야 합니다.

## reference 관찰과 직접 구현을 구분합니다

다음 명령은 완성된 reference의 여러 계층을 한 번에 보여 주는 전체 개요입니다.

```sh
make observe
```

1장 작업을 시작하는 명령으로 사용하지 않습니다. 아직 읽지 않은 파이프라인, 캐시, 주소 변환과 일관성 출력이 함께 나오므로 각 장에서는 먼저 해당 `stage-NN`과 좁은 reference 명령을 사용합니다.

```sh
python3 reference/processor-model.py bits add 127 1 --width 8
python3 reference/processor-model.py perf amdahl --fraction 0.4 --speedup 8
```

결과를 예상하고 workspace를 구현한 뒤 통과하지 않는 상태 전이만 reference와 비교합니다.

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
