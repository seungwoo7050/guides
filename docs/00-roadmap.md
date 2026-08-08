# 학습 로드맵과 범위 계약

이 문서는 컴퓨터 구조 가이드의 대상 독자, 읽는 순서, 실습 계약과 다른 시스템 가이드와의 경계를 고정합니다. 각 장을 개별 용어집처럼 읽기보다 **비트 표현 → ISA → 실행 엔진 → 메모리 계층 → 병렬 실행**으로 이어지는 하나의 상태 경로로 읽습니다.

## 대상 독자

다음 가운데 하나에 해당하는 학습자를 대상으로 합니다.

- C, C++, Java, Python 같은 언어로 작은 프로그램을 작성해 본 학습자
- 어셈블리, 캐시, 파이프라인과 가상 메모리라는 용어는 알지만 서로 어떻게 연결되는지 설명하기 어려운 개발자
- 성능 차이를 코드 줄 수나 실행 시간 한 번으로만 설명하지 않고 구조적 원인과 측정 근거로 좁히려는 개발자

컴퓨터 구조를 처음 배우는 사람도 시작할 수 있지만 변수, 함수, 배열, 반복문과 명령행 실행에 대한 일반 프로그래밍 경험은 필요합니다. C 포인터나 운영체제 내부 구현을 선행 학습할 필요는 없습니다.

## 선행지식

변수·함수·배열·반복문을 사용한 작은 프로그램과 명령행 실행 경험이면 충분합니다. C pointer, 운영체제 kernel 구현과 실제 assembly 작성 경험은 필수 조건이 아닙니다.

## 완료 후 할 수 있어야 하는 일

가이드를 마친 독자는 다음을 수행할 수 있어야 합니다.

1. 정수·부동소수점 값과 고정 폭 비트 패턴을 구분합니다.
2. ISA 계약과 마이크로아키텍처 구현을 분리합니다.
3. 명령 실행 시간의 변화를 명령어 수, CPI, 클록 주기와 병목으로 분해합니다.
4. 단일 사이클 데이터패스와 파이프라인의 상태 전이를 추적합니다.
5. 캐시 주소를 tag·set·offset으로 나누고 AMAT와 실패 원인을 계산합니다.
6. 가상 주소를 페이지 번호와 오프셋으로 나누고 TLB·페이지 테이블·권한 검사를 추적합니다.
7. 레지스터 이름 바꾸기, 발행, 완료와 순차 반영을 구분해 정확한 예외를 설명합니다.
8. SIMD, 데이터 배치와 캐시 일관성의 성능 조건을 관찰합니다.
9. 단순 상태 모델과 실제 하드웨어 측정을 구분하고, 모델이 생략한 조건을 명시합니다.

## 네 Part의 역할

### Part 1. 표현, ISA와 성능식

프로세서가 처리하는 값의 폭과 인코딩을 고정하고, 소프트웨어에 보이는 명령 계약을 정의한 뒤 성능 주장을 식과 측정 조건으로 표현합니다.

- [01 데이터 표현과 산술](01-representation-and-isa/01-data-representation-and-arithmetic.md)
- [02 ISA, 어셈블리와 프로그램 실행](01-representation-and-isa/02-isa-assembly-and-program-execution.md)
- [03 성능식과 측정](01-representation-and-isa/03-performance-cpi-and-amdahl.md)

### Part 2. 순차 실행 엔진

한 명령의 데이터 흐름에서 시작해 여러 명령을 순차 파이프라인으로 겹칩니다. 데이터 의존, 구조 충돌과 제어 흐름 변화가 있을 때 무엇을 전달·정지·비울지 추적합니다.

- [04 데이터패스와 제어](02-in-order-execution/04-datapath-and-control.md)
- [05 파이프라인과 위험 요소](02-in-order-execution/05-pipeline-hazards-and-branching.md)

### Part 3. 메모리 계층

메모리 접근을 캐시의 데이터 배치와 주소 변환이라는 서로 다른 두 경로로 나눕니다.

- [06 캐시, 지역성과 AMAT](03-memory-hierarchy/06-cache-locality-and-amat.md)
- [07 주소 변환과 TLB](03-memory-hierarchy/07-address-translation-and-tlb.md)

### Part 4. 병렬 실행

명령 수준 병렬성, 데이터 수준 병렬성, 코어 수준 병렬성을 차례로 확장합니다. 같은 “병렬성”이라도 의존성 그래프, 벡터 lane, cache-coherence domain이라는 서로 다른 상태를 사용합니다.

- [08 슈퍼스칼라, 비순차 실행과 추측](04-parallel-execution/08-superscalar-out-of-order-and-speculation.md)
- [09 SIMD와 데이터 배치](04-parallel-execution/09-simd-vectorization-and-data-layout.md)
- [10 멀티코어, 캐시 일관성과 거짓 공유](04-parallel-execution/10-multicore-coherence-and-false-sharing.md)

## 기본 읽기 순서

처음 학습할 때는 다음 순서를 사용합니다.

**필수 경로**는 01부터 10까지 순서대로 읽고 같은 번호의 누적 실습을 통과하는 과정입니다.

```text
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10
```

**선택 경로**는 이미 알고 있는 선행 개념을 건너뛰고 목적별로 확인하는 다음 경로입니다.

| 목적 | 권장 경로 |
|---|---|
| 어셈블리와 명령 실행 이해 | 01 → 02 → 04 → 05 |
| 성능 분석과 캐시 최적화 | 01 → 03 → 05 → 06 → 09 |
| 가상 주소와 TLB 이해 | 01 → 02 → 06 → 07 |
| 현대 CPU 실행 구조 이해 | 03 → 05 → 06 → 07 → 08 |
| 멀티코어 성능 문제 분석 | 03 → 06 → 08 → 09 → 10 |

빠른 경로는 선행 개념을 이미 안다는 전제입니다. 용어가 불명확하면 기본 순서로 돌아갑니다.

## 문서와 실습의 대응

[`processor-model`](../exercises/processor-model/README.md)은 장 번호와 동일한 누적 단계를 제공합니다.

| 장 | 상태 모델 또는 관찰 예제 | 검증 명령 |
|---:|---|---|
| 01 | 고정 폭 산술과 IEEE 754 필드 | `make stage-01 EXERCISE_IMPL=workspace` |
| 02 | Tiny-RISC 순차 실행 | `make stage-02 EXERCISE_IMPL=workspace` |
| 03 | CPU 시간, Amdahl과 AMAT | `make stage-03 EXERCISE_IMPL=workspace` |
| 04 | 명령별 제어 신호 | `make stage-04 EXERCISE_IMPL=workspace` |
| 05 | 전달, 정지와 비우기 | `make stage-05 EXERCISE_IMPL=workspace` |
| 06 | LRU, write-back과 3C 실패 | `make stage-06 EXERCISE_IMPL=workspace` |
| 07 | TLB, 페이지 테이블과 권한 | `make stage-07 EXERCISE_IMPL=workspace` |
| 08 | 분기 예측기와 재정렬 버퍼 | `make stage-08 EXERCISE_IMPL=workspace` |
| 09 | 컴파일러 벡터화 보고서 | `make stage-09` |
| 10 | MESI와 거짓 공유 | `make stage-10 EXERCISE_IMPL=workspace` |

작업 공간은 다음처럼 만듭니다.

```sh
cd exercises/processor-model
../../scripts/new-workspace.sh .
```

완성된 reference를 먼저 복사하지 않습니다. 각 장의 결과를 예상하고 workspace를 구현한 뒤, 실패한 상태 전이만 reference와 비교합니다.

## 구조와 정책의 경계

### 컴퓨터 구조가 소유하는 범위

- 정수·부동소수점 표현과 ISA 연산 의미
- 명령 인코딩, 레지스터, 예외와 메모리 접근 계약
- 데이터패스, 파이프라인, 분기 예측과 비순차 실행
- 캐시 구조, 지역성, 교체·쓰기 정책과 AMAT
- 페이지 테이블 순회에 필요한 주소 비트, PTE 권한, TLB와 ASID
- store buffer, ISA 메모리 순서와 fence의 하드웨어 경계
- SIMD, cache coherence와 false sharing

### 운영체제 가이드가 소유하는 범위

- 가상 주소 공간의 생성과 영역 관리
- demand paging, page allocation과 reclaim
- copy-on-write, file mapping과 page cache 정책
- page replacement와 swap
- page fault 처리기의 정책과 프로세스 종료
- 여러 코어에 대한 TLB shootdown을 언제 수행할지 결정하는 커널 정책

이 가이드에서는 운영체제 정책이 하드웨어 계약을 사용하는 지점까지만 설명합니다.

### 언어·동시성 가이드가 소유하는 범위

- C/C++ atomic과 memory order
- Java `volatile`, monitor와 happens-before
- mutex, condition variable와 lock-free 알고리즘의 정확성
- 컴파일러가 언어 메모리 모델을 ISA 명령으로 내리는 구체 규칙

이 가이드에서는 store buffer, coherence, ISA ordering과 fence가 필요한 하드웨어 이유를 설명하고 언어별 API 사용법은 반복하지 않습니다.

## 범위 밖

실제 CPU의 proprietary transient state, 운영체제의 page replacement 정책, 언어별 atomic API와 특정 processor의 cycle 정확한 timing은 이 과정의 완료 범위가 아닙니다. 상태 모델의 결과를 실제 제품의 성능·보안 보장으로 확대 해석하지 않습니다.

## 지원 환경과 재현성

필수 환경은 Python 3.12 이상, C11 컴파일러, POSIX `sh`, `make`, Git입니다. 상태 모델은 Python 표준 라이브러리만 사용합니다. C 예제의 시간은 자동 합격 조건이 아니며 다음 정보를 함께 남겨야 합니다.

- 운영체제와 CPU
- 컴파일러와 버전
- 최적화 옵션
- 입력 크기와 반복 횟수
- 결과 합계 또는 checksum
- 측정 분포

실제 하드웨어 계수기를 사용할 수 없더라도 결정적 상태 모델과 예제의 기능 검증은 완료할 수 있습니다.

## 자동 검증의 한계

자동 검증은 교육용 Tiny-RISC, 단순 pipeline·cache·TLB·MESI 모델과 현재 compiler가 만든 예제 결과를 확인합니다. 실제 processor의 모든 speculative state, timing, errata와 운영체제 정책을 증명하지 않습니다. 실제 하드웨어 주장은 CPU model, 운영체제, compiler, 원시 측정값과 공식 문서 판본을 별도로 남겨야 합니다.

## 완료 기준

다음을 모두 만족하면 가이드를 완료한 것으로 봅니다.

- `./prepare.sh`를 실행한 최종 구조에서 `./verify.sh`가 성공합니다.
- `processor-model` workspace가 `make exercise-test EXERCISE_IMPL=workspace`를 통과합니다.
- 각 상태 모델에서 구조적 상태, 마이크로아키텍처 상태와 관찰값을 구분해 설명합니다.
- 벤치마크 결과를 단일 시간값이 아니라 가설, 입력, 빌드와 검증 결과와 함께 해석합니다.
- 가상 메모리 정책이나 언어 atomic 규칙을 컴퓨터 구조의 고유 계약처럼 설명하지 않습니다.
