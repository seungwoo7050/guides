# SIMD, 벡터화와 데이터 배치

SIMD는 한 명령어로 여러 데이터 원소에 같은 종류의 연산을 적용합니다. 슈퍼스칼라가 서로 다른 명령어를 동시에 발행하는 명령어 수준 병렬성이라면, SIMD는 한 명령어 안의 레인으로 데이터 수준 병렬성을 표현합니다. 스레드 병렬성과도 별도 축입니다.

## 학습 목표

- SIMD, superscalar와 thread 병렬성을 서로 다른 축으로 구분합니다.
- 정확한 checksum과 compiler 보고서를 함께 사용해 벡터화 주장을 검증합니다.

## 선행 개념

반복문 의존성, cache locality와 compiler 최적화 옵션을 알아야 합니다.

## 스칼라 연산과 벡터 연산을 구분합니다

scalar addition은 값 하나씩 계산합니다.

```text
c0 = a0 + b0
c1 = a1 + b1
c2 = a2 + b2
c3 = a3 + b3
```

4-lane vector addition은 다음을 한 instruction 의미로 묶을 수 있습니다.

```text
[c0 c1 c2 c3] = [a0 a1 a2 a3] + [b0 b1 b2 b3]
```

실제 hardware가 lane을 한 cycle에 모두 실행하는지, 여러 cycle로 나누는지는 microarchitecture입니다. ISA는 vector register, element type, mask와 instruction semantics를 정의합니다.

## SIMD와 여러 실행 장치는 같은 개념이 아닙니다

superscalar core는 scalar `add`, `load`, `branch` 같은 여러 instruction을 같은 cycle에 issue할 수 있습니다. SIMD instruction은 하나의 decoded operation이 여러 element에 같은 연산을 지정합니다.

```text
superscalar: instruction A + instruction B
SIMD:        instruction V가 element 0..N-1 처리
```

둘을 함께 사용할 수 있습니다. 여러 벡터 명령이 서로 독립이면 비순차 실행 코어가 겹쳐 실행할 수 있습니다.

## 벡터 폭은 ISA와 구현에 따라 다릅니다

x86 SSE/AVX 계열은 명령마다 고정된 레지스터 폭을 사용합니다. ARM NEON도 고정 폭 벡터를 제공합니다. RISC-V V 확장은 벡터 길이에 독립적인 프로그래밍을 지원하여 구현의 VLEN에 맞춰 처리할 원소 수를 설정할 수 있습니다.

소스 코드에서 특정 폭을 고정하면 다음 문제가 생길 수 있습니다.

- 더 넓은 하드웨어를 사용하지 못합니다.
- 다른 ISA로 이식하기 어렵습니다.
- 남는 원소 처리와 정렬 코드가 늘어납니다.

컴파일러 자동 벡터화나 이식 가능한 추상화를 먼저 검토하고, 내장 함수는 실제 병목과 대상 ISA가 명확할 때 사용하세요.

## 벡터화의 첫 조건은 반복 사이의 독립성입니다

다음 반복문은 각 `i`가 다른 출력 원소를 씁니다.

```c
for (i = 0; i < n; ++i)
    output[i] = left[i] * scale + right[i];
```

각 반복의 입력과 출력이 겹치지 않는다는 규칙이 있으면 여러 반복을 동시에 실행할 수 있습니다.

다음 점화식은 이전 결과가 필요합니다.

```c
for (i = 0; i < n; ++i)
    value = value * factor + input[i];
```

`i+1`번째 반복이 `i`번째 값에 의존하므로 같은 방식의 레인 병렬화가 어렵습니다. 알고리즘을 스캔 형태로 바꾸거나 수학적으로 재구성할 수 있는지 별도로 검토해야 합니다.

[벡터화 보고서](../../examples/vectorization-report/README.md)는 두 반복문을 함께 빌드합니다.

```sh
make -C examples/vectorization-report report
```

## 포인터 별칭은 컴파일러의 증명을 막을 수 있습니다

다음 함수에서 세 포인터가 겹칠 수 있다면 출력 쓰기가 다음 입력 읽기를 바꿀 수 있습니다.

```c
void transform(float *output, const float *left, const float *right, size_t n);
```

컴파일러는 실행 중 별칭 검사를 만들거나 벡터화를 포기할 수 있습니다. C의 `restrict`는 해당 포인터 기반 접근이 겹치지 않는다는 강한 규칙을 제공합니다.

```c
void transform(
    float *restrict output,
    const float *restrict left,
    const float *restrict right,
    size_t n);
```

호출자가 규칙을 어기면 정의되지 않은 동작이 발생할 수 있습니다. `restrict`를 성능을 위한 장식처럼 붙이면 안 됩니다.

## 정렬된 벡터 접근과 정렬되지 않은 벡터 접근

벡터 적재가 특정 경계 정렬을 요구하는 ISA도 있고, 정렬되지 않은 접근을 허용하지만 캐시 줄·페이지 경계를 넘을 때 비용이 달라지는 구현도 있습니다.

컴파일러는 다음 방식을 사용할 수 있습니다.

- 정렬되지 않은 벡터 적재·저장
- 정렬된 지점까지의 스칼라 앞부분
- 실행 중 정렬 검사로 두 경로 생성
- 마스크를 적용한 적재·저장

정렬 메모리 할당을 추가하면 할당기, 객체 수명과 해제 API가 맞아야 합니다. 측정 없이 모든 버퍼를 과도하게 정렬하면 메모리가 낭비됩니다.

## 남는 원소를 처리해야 합니다

`n`이 레인 수의 배수가 아니면 마지막 원소가 남습니다.

대표 방식은 다음과 같습니다.

- 스칼라 나머지 반복문
- 마스크를 적용한 벡터 연산
- 패딩한 입력
- 벡터 길이 설정으로 남은 수만 처리

패딩은 범위 밖 읽기를 허용하는 이유가 되지 않습니다. 실제 할당 범위와 초기화한 데이터 범위를 보장해야 합니다.

## 마스크는 레인별 실행 여부를 표현합니다

조건문이 레인마다 다를 때 마스크를 만들 수 있습니다.

```text
mask = values > threshold
result = select(mask, transformed, original)
```

분기를 없앴다고 항상 빨라지는 것은 아닙니다. 양쪽 계산을 모두 수행하거나 마스크 연산 비용이 들 수 있습니다. 조건 분포와 연산 비용을 측정해야 합니다.

GPU의 워프 분기와 CPU SIMD 마스크는 비슷한 질문을 공유하지만 실행 모델이 같지는 않습니다.

## AoS와 SoA가 벡터 적재 방식을 바꿉니다

입자 data를 AoS로 저장하면 다음과 같습니다.

```text
x0 y0 z0 x1 y1 z1 x2 y2 z2 ...
```

`x`만 처리하려면 stride가 생기거나 gather가 필요합니다.

SoA는 다음과 같습니다.

```text
x0 x1 x2 x3 ...
y0 y1 y2 y3 ...
z0 z1 z2 z3 ...
```

연속한 `x`를 vector load하기 쉽습니다. 반대로 object 하나의 모든 field를 자주 쓰면 여러 stream을 읽어야 합니다.

layout은 SIMD만이 아니라 cache line utilization, serialization, API와 update locality를 함께 바꿉니다.

## gather와 scatter는 불규칙한 접근을 지원하지만 비쌀 수 있습니다

index 배열로 여러 address의 element를 모으는 gather와 여러 address에 쓰는 scatter instruction이 있을 수 있습니다.

```text
values = gather(base, indices)
scatter(base, indices, results)
```

연속 load보다 address generation과 cache miss가 많고, 중복 destination의 의미도 확인해야 합니다. gather가 있다는 이유로 random memory access가 연속 access와 같은 비용이 되는 것은 아닙니다.

## 축약 연산은 연산 순서를 바꿉니다

sum reduction은 여러 lane의 partial sum을 마지막에 합칩니다.

```text
lane partial sums
→ tree reduction
→ scalar result
```

integer에서 overflow가 modulo로 정의된 환경인지, signed overflow가 undefined인 언어인지 확인해야 합니다. floating point에서는 결합 순서가 달라져 마지막 bit가 바뀔 수 있습니다.

정확도 요구에 따라 다음을 검토합니다.

- pairwise summation
- Kahan summation
- wider accumulator
- deterministic reduction order
- 허용 오차 기반 test

빠른 vector reduction과 bitwise 동일 결과를 동시에 요구할 수 없는 경우가 있습니다.

## 컴파일러의 벡터화 보고서를 읽습니다

보고서에서 다음 질문을 확인하세요.

1. 어느 loop가 vectorized되었습니까?
2. 어떤 dependency 또는 alias 때문에 실패했습니까?
3. runtime versioning을 만들었습니까?
4. vector width와 element type은 무엇입니까?
5. 나머지와 마스크 처리는 어떻게 했습니까?
6. 부동소수점 의미를 완화하는 선택 사항이 필요했습니까?

“vectorized”라는 메시지가 있어도 병목 반복문이 아닌 초기화 반복문일 수 있습니다. 어셈블리와 프로파일을 함께 봐야 합니다.

## 내장 함수는 ISA에 종속된 계약입니다

내장 함수는 컴파일러에게 특정 벡터 연산을 명시합니다. 다음 장점이 있습니다.

- 명령 선택을 세밀하게 제어합니다.
- 마스크, 섞기와 포화 연산을 직접 표현합니다.
- 자동 벡터화기가 놓친 패턴을 구현할 수 있습니다.

동시에 다음 비용이 있습니다.

- ISA와 벡터 폭에 종속됩니다.
- 기능 탐지와 대체 경로가 필요합니다.
- 컴파일러의 레지스터 할당과 스케줄링을 방해할 수 있습니다.
- 코드 검토와 정확성 검사가 어려워집니다.

먼저 스칼라 기준 구현과 고정 시드 무작위 동치 검사를 만들고, 대상 기능이 없는 CPU에서 실행되지 않도록 실행 경로 선택을 설계해야 합니다.

## SIMD가 효과를 내지 못하는 대표 조건

- 데이터 의존성이 이어집니다.
- 작업 집합이 메모리 대역폭을 포화합니다.
- 원소 수가 너무 작습니다.
- 분기와 마스크가 대부분의 레인을 비활성화합니다.
- gather/scatter가 캐시 실패를 만듭니다.
- 변환과 묶음 처리 비용이 계산보다 큽니다.
- 벡터 폭 증가로 주파수가 달라지는 프로세서가 있습니다.
- 컴파일러가 이미 같은 최적화를 수행합니다.

이 경우 알고리즘, 데이터 배치, 일괄 처리 또는 스레드 병렬화가 더 큰 효과를 낼 수 있습니다.

## SIMD 실험 절차

1. 스칼라 기준 구현과 출력 검증을 만듭니다.
2. 프로파일로 병목 반복문과 입력 크기를 확인합니다.
3. 의존성과 별칭을 적습니다.
4. 컴파일러 보고서와 어셈블리를 확인합니다.
5. 자동 벡터화된 경로를 먼저 측정합니다.
6. 필요하면 내장 함수 경로를 추가합니다.
7. 남는 원소, 정렬, NaN, 오버플로와 별칭 조건을 검사합니다.
8. 여러 CPU 기능과 대체 경로를 검증합니다.
9. 사이클, 명령 수, 대역폭과 경과 시간을 함께 기록합니다.

## 직접 확인할 문제

1. SIMD, 슈퍼스칼라와 다중 스레딩을 각각 명령, 레인, 코어 관점에서 구분해 보세요.
2. 점화식 반복문이 일반 원소별 반복문보다 벡터화하기 어려운 이유를 의존성 그래프로 그려 보세요.
3. `restrict` 규칙을 어기는 호출 예를 만들고 왜 단순한 최적화 힌트가 아닌지 설명해 보세요.
4. 원소 10개를 4레인 벡터로 처리할 때 스칼라 나머지와 마스크 방식을 각각 그려 보세요.
5. AoS를 SoA로 바꿨을 때 캐시 사용량과 API 복잡성의 절충을 적어 보세요.

## 연결 실습

루트의 `make stage-09`로 vector checksum과 compiler vectorization 보고서를 함께 확인합니다.

## 완료 기준

- 벡터화 가능한 loop와 recurrence loop의 의존성 차이를 그릴 수 있습니다.
- AoS와 SoA가 cache line과 vector load에 미치는 영향을 설명할 수 있습니다.
- `make stage-09`가 정확한 checksum으로 통과합니다.
