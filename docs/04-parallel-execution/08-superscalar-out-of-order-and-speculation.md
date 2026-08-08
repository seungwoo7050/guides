# 슈퍼스칼라, 비순차 실행과 추측

단일 발행 파이프라인은 여러 명령의 단계를 겹치지만 보통 한 사이클에 새 명령 하나를 발행합니다. 고성능 코어는 여러 명령을 가져오고 해석하며, 피연산자와 실행 자원이 준비된 연산을 프로그램 순서와 다르게 실행합니다. 내부 계산 순서가 달라져도 소프트웨어에는 ISA가 허용한 구조적 상태와 정확한 예외를 보여야 합니다.

이 장은 레지스터 이름 바꾸기, 발행 대기열, 재정렬 버퍼, load/store queue, 저장 버퍼와 ISA 메모리 순서를 다룹니다. C/C++ atomic, Java `volatile`과 언어별 happens-before 규칙은 해당 언어 가이드의 범위입니다.

## 학습 목표

- rename, issue, execute, complete와 retire의 상태 소유자를 구분합니다.
- 추측 실패와 precise exception이 architectural state에 미치는 경계를 설명합니다.

## 선행 개념

파이프라인 hazard와 branch flush, ISA 예외와 register write 시점을 알아야 합니다.

## 세 종류의 병렬성을 구분합니다

### 파이프라인 병렬성

서로 다른 명령이 서로 다른 단계에 있습니다. 자세한 정지·전달·비우기 규칙은 [파이프라인과 위험 요소](../02-in-order-execution/05-pipeline-hazards-and-branching.md)에서 다룹니다.

### 슈퍼스칼라 폭

한 사이클에 여러 명령 또는 내부 연산을 fetch, decode, issue, execute하거나 retire할 수 있습니다. 각 단계의 폭은 서로 같을 필요가 없습니다.

### 비순차 실행

프로그램 순서에서 뒤에 있는 연산도 실제 피연산자와 실행 자원이 준비되면 먼저 실행할 수 있습니다.

세 속성은 독립적입니다. 여러 명령을 동시에 발행하지만 순서를 유지하는 코어도 있고, 넓은 비순차 코어도 있습니다.

## 의존성 그래프가 가능한 병렬성을 제한합니다

```text
A: r1 = r2 + r3
B: r4 = r5 + r6
C: r7 = r1 + r8
```

A와 B는 독립이므로 함께 실행할 수 있지만 C는 A의 결과가 필요합니다.

```text
A → C
B는 별도 경로
```

실행 폭이 넓어도 긴 RAW 의존 사슬은 사라지지 않습니다. 성능을 분석할 때는 명령 수뿐 아니라 다음을 함께 봅니다.

- 의존 그래프의 임계 경로
- 실행 유닛의 latency와 reciprocal throughput
- 사용 가능한 실행 port
- frontend 공급 속도
- cache와 TLB 실패

복잡한 ISA 명령은 여러 micro-operation으로 나뉠 수 있고, 단순 명령 여러 개가 결합될 수도 있습니다. 소스 코드 줄 수나 ISA 명령 이름만으로 내부 연산 수를 단정할 수 없습니다.

## 레지스터 이름 바꾸기는 값 버전을 분리합니다

아키텍처 레지스터 수가 제한되어 서로 관계없는 값이 같은 이름을 재사용할 수 있습니다.

```text
I0: r1 = ...
I1: ... = r1
I2: r1 = ...
```

I2의 write가 I1의 read보다 먼저 보이면 WAR 위험이 생기고, 여러 write의 순서가 뒤집히면 WAW 위험이 생깁니다. rename 단계에서 새 물리 레지스터를 배정하면 값 버전을 분리할 수 있습니다.

```text
architectural r1 version 0 → physical p12
I2가 만드는 r1 version 1 → physical p37
```

register rename은 이름 때문에 생긴 WAR와 WAW를 제거할 수 있지만 실제 값 의존인 RAW는 제거하지 않습니다. rename table, free list와 이전 물리 레지스터의 회수 시점도 정확한 상태 복구와 연결됩니다.

## 발행 대기열은 준비된 연산과 자원을 맞춥니다

rename 뒤 연산은 다음 상태를 가질 수 있습니다.

- 소스 물리 레지스터 tag
- 각 소스의 준비 여부 또는 값
- 목적지 물리 레지스터
- 필요한 실행 유닛과 port
- 프로그램 순서를 나타내는 나이
- 예외와 추측 메타데이터

소스가 준비되고 필요한 자원이 비면 발행할 수 있습니다. 여러 ready 연산 가운데 무엇을 고르는지는 스케줄러 정책에 따라 다릅니다. 오래된 연산 우선 정책도 실행 port 충돌이나 cache miss 때문에 전체 프로그램 순서와 같은 완료 순서를 만들지는 않습니다.

latency는 한 연산의 결과가 준비될 때까지의 시간이고, throughput은 같은 실행 유닛이 새 연산을 받을 수 있는 빈도입니다. 두 수치를 혼동하면 독립 연산의 처리량과 의존 사슬의 지연을 잘못 예측합니다.

## 재정렬 버퍼는 비순차 완료와 순차 반영을 연결합니다

연산이 완료되는 즉시 아키텍처 레지스터와 메모리에 결과를 확정하면 앞 명령의 예외를 정확히 처리하기 어렵습니다. Reorder Buffer는 프로그램 순서를 보존하며 완료 값, 목적지와 예외를 추적합니다.

```text
비순차 execute
→ 결과 ready
→ ROB head부터 in-order retire
→ architectural state 확정
```

앞 명령이 fault를 일으키면 그보다 젊은 speculative 결과를 버리고 faulting 명령 직전의 구조적 상태를 복원할 수 있습니다. 이를 precise exception이라고 합니다.

다음 상태를 구분합니다.

```text
issued   실행 준비를 기다립니다.
executed 계산은 끝났지만 아직 구조적으로 확정되지 않았습니다.
retired  프로그램 순서에 따라 구조적 상태에 반영되었습니다.
```

“먼저 계산되었다”와 “소프트웨어에 먼저 보였다”는 같은 말이 아닙니다.

## 추측은 틀렸을 때 되돌릴 경계를 요구합니다

분기 예측기는 다음 PC를 추측하고, memory disambiguation은 load가 앞선 store와 충돌하지 않을 것으로 추측할 수 있습니다. 추측이 맞으면 대기 시간을 숨기고, 틀리면 관련 연산을 squash하거나 replay합니다.

구조적 상태를 되돌려도 캐시, TLB와 predictor 같은 마이크로아키텍처 상태에는 흔적이 남을 수 있습니다. 따라서 다음 두 문장을 구분해야 합니다.

```text
추측 결과가 retire되지 않았습니다.
추측 실행이 관찰 가능한 미세구조 흔적을 전혀 남기지 않았습니다.
```

첫 문장이 참이어도 두 번째 문장은 자동으로 참이 아닙니다. 이 장에서는 상태 경계를 설명하고 구체적인 side-channel 공격과 완화 기법은 별도 보안 과정으로 넘깁니다.

## load/store queue는 주소 의존을 추적합니다

레지스터 의존과 달리 두 메모리 연산이 같은 주소인지 주소 계산 전에는 모를 수 있습니다.

```text
store [r1 + offsetA] = value
load  result = [r2 + offsetB]
```

비순차 코어는 다음 상태를 처리해야 합니다.

- load가 앞선 store와 같은 주소인지 검사합니다.
- 같은 주소이고 store data가 준비되면 forwarding합니다.
- 주소를 아직 모르는 앞선 store를 load가 추월할지 예측합니다.
- 예측이 틀리면 load와 그 결과에 의존한 연산을 replay합니다.
- store가 retire되기 전에 외부 상태를 잘못 바꾸지 않도록 보류합니다.

포인터 aliasing이 컴파일러 최적화뿐 아니라 하드웨어 스케줄링에도 영향을 주는 이유입니다.

## 저장 버퍼는 store의 완료 지연을 숨깁니다

retire된 store가 cache hierarchy에 완전히 반영될 때까지 파이프라인이 기다리면 자주 멈춥니다. 저장 버퍼는 주소와 데이터를 보관하고 뒤에서 일관성 트랜잭션과 캐시 갱신을 진행합니다.

같은 코어의 뒤 load가 같은 주소를 읽으면 store-to-load forwarding이 필요합니다. 다른 코어가 write를 언제 관찰할 수 있는지는 [멀티코어와 캐시 일관성](10-multicore-coherence-and-false-sharing.md)과 ISA 메모리 순서 계약이 함께 결정합니다.

## ISA 메모리 순서는 여러 위치의 관찰 가능 순서를 제한합니다

다음 두 store를 생각합니다.

```text
data = 42
ready = 1
```

다른 코어가 `ready == 1`을 관찰한 뒤 `data == 42`도 반드시 관찰한다고 모든 ISA가 자동 보장하지는 않습니다. store buffer, load speculation과 coherence transaction의 진행 순서가 여러 주소의 관찰 순서에 영향을 줄 수 있습니다.

### 캐시 일관성

한 메모리 위치의 write가 코어별 캐시에 어떻게 전파되고 오래된 복사본이 어떻게 무효화되는지 다룹니다.

### 메모리 일관성 모델

여러 위치의 load와 store가 다른 실행 주체에 어떤 순서로 관찰될 수 있는지 다룹니다.

한 위치의 coherence가 맞아도 `data`와 `ready` 사이의 ordering edge가 자동으로 생기는 것은 아닙니다.

## fence는 허용되는 재배치 범위를 줄입니다

ISA fence는 특정 종류의 메모리 연산이 다른 연산보다 먼저 관찰되도록 제한합니다. 강한 fence를 모든 접근 사이에 넣으면 저장 버퍼와 비순차 실행이 제공하는 병렬성을 잃습니다.

저수준 메모리 순서를 분석할 때는 다음 순서를 사용합니다.

1. 공유 상태의 불변식을 적습니다.
2. 어느 write가 어느 read보다 먼저 보여야 하는지 edge를 그립니다.
3. 언어 수준에서는 atomic이나 lock으로 그 edge를 표현합니다.
4. compiler와 toolchain이 언어 계약을 ISA 명령과 fence로 내리는 방식을 확인합니다.
5. 필요하면 생성된 어셈블리와 동시성 검증 도구로 확인합니다.

응용 프로그램에서 ISA fence를 직접 삽입하는 것은 일반적인 기본 해법이 아닙니다. 언어·컴파일러 계약을 우회하면 컴파일러 재배치를 막지 못하거나 플랫폼 이식성을 잃을 수 있습니다.

## 언어·동시성 가이드와의 경계

이 장은 저장 버퍼, load speculation, coherence와 ISA fence가 필요한 하드웨어 이유를 설명합니다. C와 C++의 atomic memory order, Java의 `volatile`·monitor·happens-before, lock과 condition variable의 정확한 사용법은 각 언어·동시성 가이드가 소유합니다.

응용 코드에서는 먼저 언어 수준 계약으로 동기화를 표현하고, 성능이나 저수준 런타임 구현을 분석할 때만 compiler가 생성한 ISA 명령과 fence를 추적합니다. 언어 규칙을 ISA 규칙으로 직접 치환하거나 ISA fence만 추가해 data race를 해결하려 해서는 안 됩니다.

## 비순차 코어의 병목을 분류합니다

IPC 하나만 보고 원인을 정할 수 없습니다. 다음 후보를 분리합니다.

- 의존성 사슬이 길어 ready 연산이 부족합니다.
- 특정 실행 port가 포화됩니다.
- frontend가 충분한 내부 연산을 공급하지 못합니다.
- ROB, 물리 레지스터 또는 issue queue가 가득 찹니다.
- load/store queue가 가득 찹니다.
- cache 또는 TLB miss를 기다립니다.
- branch misprediction으로 speculative work를 버립니다.

[캐시와 AMAT](../03-memory-hierarchy/06-cache-locality-and-amat.md), [주소 변환과 TLB](../03-memory-hierarchy/07-address-translation-and-tlb.md)의 실패 비용을 실행 엔진의 대기 상태와 연결해야 합니다.

## 독립 accumulator는 의존 사슬을 나눕니다

하나의 reduction은 매 반복이 이전 합계에 의존합니다.

```c
for (...) {
    sum += values[i];
}
```

여러 accumulator를 사용하면 의존 사슬을 나눌 수 있습니다.

```c
sum0 += values[i];
sum1 += values[i + 1];
```

마지막에 합치면 명령 수준 병렬성이 늘 수 있습니다. 반대로 레지스터 압박, 코드 크기와 부동소수점 연산 순서가 바뀔 수 있으며 컴파일러가 이미 unroll 또는 vectorization을 수행하는지도 확인해야 합니다.

## 직접 구현하기

`exercises/processor-model/skeleton/processor_model/predictor.py`와 `rob.py`를 완성합니다.

### 2비트 분기 예측기

- 각 항목은 0~3의 포화 계수기입니다.
- 0·1은 not-taken, 2·3은 taken을 예측합니다.
- 실제 taken이면 최대 3까지 증가하고 아니면 최소 0까지 감소합니다.
- PC 정렬과 table index aliasing을 결정적으로 처리합니다.
- 예측 횟수와 실패 횟수를 누적합니다.

### 재정렬 버퍼

- 발행 순서대로 증가하는 tag를 부여합니다.
- capacity를 넘는 발행을 거부합니다.
- 완료 값 또는 fault를 기존 미완료 항목에 한 번만 기록합니다.
- head의 ready 항목부터만 retire합니다.
- fault 항목을 만나면 그 항목과 더 젊은 항목을 제거합니다.
- fault보다 오래된 이미 retire 가능한 값은 유지합니다.

```sh
cd exercises/processor-model
make stage-08 EXERCISE_IMPL=workspace
```

이 단계는 01~08장의 회귀와 다음 테스트를 함께 실행합니다.

```text
BranchPredictorTests
ReorderBufferTests
```

reference만 관찰하려면 다음을 실행합니다.

```sh
EXERCISE_IMPL=reference python3 -m unittest \
  tests.test_processor_model.BranchPredictorTests \
  tests.test_processor_model.ReorderBufferTests -v
```

## 분석할 때 만드는 세 그림

### 의존성 그래프

내부 연산 사이의 RAW edge와 임계 경로를 표시합니다.

### 자원표

각 연산의 실행 유닛, latency, throughput과 port 제약을 적습니다.

### 완료·반영 순서표

execute 완료 순서와 ROB retire 순서를 분리합니다.

세 그림을 함께 보면 뒤 명령이 먼저 계산되었지만 앞선 fault나 잘못된 추측 때문에 버려지는 이유를 설명할 수 있습니다.

## 직접 확인할 문제

1. register renaming이 WAR와 WAW는 제거하지만 RAW는 제거하지 못하는 이유를 값 버전으로 설명해 보세요.
2. ROB 없이 완료 결과를 즉시 아키텍처 레지스터에 기록하면 precise exception이 왜 어려운지 설명해 보세요.
3. load가 앞선 store를 추월한 뒤 같은 주소임이 밝혀졌을 때 어떤 연산을 replay해야 하는지 적어 보세요.
4. 저장 버퍼가 단일 코어 처리량을 높이면서 멀티코어 관찰 순서를 복잡하게 만드는 이유를 설명해 보세요.
5. coherence와 memory consistency가 서로 다른 질문에 답하는 이유를 두 주소의 예로 설명해 보세요.

## 연결 실습

[`processor-model` stage-08](../../exercises/processor-model/README.md)에서 2비트 predictor와 ROB를 구현합니다.

## 완료 기준

- WAR·WAW가 rename으로 사라지고 RAW는 남는 이유를 설명할 수 있습니다.
- 완료 순서와 retire 순서가 다른 trace에서 precise exception을 복원할 수 있습니다.
- `make stage-08 EXERCISE_IMPL=workspace`가 통과합니다.
