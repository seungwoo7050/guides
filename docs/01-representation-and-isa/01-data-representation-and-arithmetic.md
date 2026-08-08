# 데이터 표현과 산술

프로세서는 레지스터와 메모리에 비트 패턴을 저장합니다. `11111111`이 `255`, `-1`, 명령어 일부 또는 문자 바이트 가운데 무엇인지는 이 패턴을 읽는 연산과 자료형 계약이 결정합니다. 값과 비트 패턴을 구분하면 오버플로, 바이트 순서, 정렬과 부동소수점 반올림을 같은 모델로 설명할 수 있습니다.

## 학습 목표

- 고정 폭 정수, 부동소수점과 메모리 바이트를 동일한 비트 패턴 모델로 해석합니다.
- carry와 signed overflow, 값과 표현을 서로 다른 계약으로 설명합니다.

## 선행 개념

2진수와 16진수 표기, 정수 사칙연산과 Python 함수 호출을 알고 있어야 합니다.

## 비트에는 자료형이 붙어 있지 않습니다

8비트 패턴 `11111111`을 두 방식으로 읽을 수 있습니다.

```text
unsigned 8-bit: 255
signed 8-bit two's complement: -1
```

메모리에는 `signed` 표시가 따로 저장되지 않습니다. `lb`처럼 부호 확장을 수행하는 명령인지, `lbu`처럼 0 확장을 수행하는 명령인지, 컴파일러가 어떤 연산을 골랐는지가 해석을 정합니다.

폭이 `w`인 부호 없는 정수 범위는 다음과 같습니다.

```text
0 .. 2^w - 1
```

2의 보수 부호 있는 정수 범위는 다음과 같습니다.

```text
-2^(w-1) .. 2^(w-1) - 1
```

음수 하나가 더 많은 이유는 최상위 비트가 1인 절반의 패턴을 음수에 배정하기 때문입니다. `10000000`은 8비트 signed에서 `-128`이고 같은 폭의 `+128`은 표현할 수 없습니다.

## 2의 보수와 고정 폭 덧셈

폭을 `w`로 고정하고 하위 `w`비트만 남기면 modulo `2^w` 연산과 같습니다.

```text
8-bit unsigned: 255 + 1 = 0, carry out = 1
8-bit signed:   127 + 1 = -128, signed overflow = 1
```

두 경우 모두 같은 덧셈기의 하위 비트를 사용하지만 오류 판정 계약은 다릅니다.

### 부호 없는 carry

최상위 비트 밖으로 carry가 나가면 부호 없는 표현 범위를 넘었습니다.

### 부호 있는 overflow

같은 부호의 두 값을 더했는데 결과 부호가 바뀌면 signed 범위를 넘었습니다.

```text
positive + positive → negative
negative + negative → non-negative
```

carry와 signed overflow는 같은 플래그가 아닙니다. `127 + 1`은 carry 없이 signed overflow가 나고, `255 + 1`은 carry가 나지만 같은 패턴을 signed로 읽으면 `-1 + 1 = 0`이므로 signed overflow가 아닙니다.

완성된 계산기는 다음처럼 관찰할 수 있습니다.

```sh
python3 exercises/processor-model/reference/processor-model.py \
  bits add 127 1 --width 8
python3 exercises/processor-model/reference/processor-model.py \
  bits add 255 1 --width 8
```

## 확장과 축소

작은 폭을 큰 폭으로 옮길 때는 상위 비트를 어떻게 채울지 정해야 합니다.

```text
8-bit pattern: 11111111
zero extension to 16-bit: 00000000 11111111 = 255
sign extension to 16-bit: 11111111 11111111 = -1
```

signed 값을 보존하려면 sign bit를 복제하고, unsigned 값을 보존하려면 0을 채웁니다. 피연산자 폭과 signedness를 확인하지 않고 cast를 추가하면 값이 보존되는 것이 아니라 해석이 바뀔 수 있습니다.

좁히는 변환은 상위 비트를 버립니다. 버린 비트가 sign extension 또는 zero extension으로 복원 가능한지 확인하지 않으면 정보가 손실됩니다.

## 시프트

왼쪽 shift는 표현 범위를 넘지 않는 조건에서 `2^n` 곱셈과 같은 결과를 낼 수 있습니다. 오른쪽 shift는 빈 상위 비트를 채우는 정책을 구분합니다.

- logical right shift는 0을 채웁니다.
- arithmetic right shift는 sign bit를 복제합니다.

ISA에서는 두 명령을 별도로 둘 수 있습니다. 프로그래밍 언어에서 부호 있는 음수를 이동하는 규칙과 ISA 규칙을 섞지 않습니다. 이동량이 피연산자 폭 이상일 때도 언어와 ISA의 계약이 다를 수 있습니다.

## 바이트 순서

`0x12345678`을 네 바이트로 나누면 `12 34 56 78`입니다.

```text
낮은 주소 → 높은 주소
big-endian:    12 34 56 78
little-endian: 78 56 34 12
```

endianness는 바이트 안의 비트 순서를 뒤집는 개념이 아닙니다. 레지스터에서 계산되는 정수값 자체가 바뀌는 것도 아닙니다. 여러 바이트를 메모리나 바이트 스트림에 놓고 다시 조립할 때 드러납니다.

네트워크 프로토콜, 파일 형식과 직렬화는 바이트 순서를 명시해야 합니다. 호스트 바이트 순서를 그대로 영구 형식에 쓰면 다른 아키텍처나 언어 구현에서 읽지 못할 수 있습니다.

```sh
python3 exercises/processor-model/reference/processor-model.py \
  bits int 0x12345678 --width 32
```

## 정렬

4바이트 word를 4의 배수 주소에서 읽는 규칙을 예로 들 수 있습니다.

```text
aligned:   0, 4, 8, 12, ...
unaligned: 1, 2, 3, 5, ...
```

정렬되지 않은 접근의 결과는 ISA에 따라 다릅니다.

- trap이 발생할 수 있습니다.
- 하드웨어가 여러 접근으로 나눌 수 있습니다.
- 일부 명령에서만 허용할 수 있습니다.
- 동작은 허용하지만 더 많은 사이클이 필요할 수 있습니다.

C 구조체에는 각 멤버의 정렬을 맞추기 위한 padding이 들어갈 수 있습니다.

```c
struct item {
    char kind;
    int value;
};
```

`sizeof(struct item)`이 단순히 `1 + 4`라고 단정할 수 없습니다. 멤버 순서를 바꾸면 크기가 줄 수 있지만 ABI, 직렬화, 원자성과 캐시 라인 배치도 영향을 받습니다.

Tiny-RISC는 word 접근을 4바이트 정렬로 고정하고 잘못된 주소를 거부합니다.

```sh
cd exercises/processor-model
EXERCISE_IMPL=reference python3 -m unittest \
  tests.test_processor_model.IsaTests.test_unaligned_access_fails -v
```

## 정수와 포인터 폭

주소를 `int`에 저장할 수 있다고 가정하면 64비트 프로세스에서 상위 비트를 잃을 수 있습니다. C에서 객체 포인터를 정수로 옮겨야 하는 특별한 경계에는 `uintptr_t`처럼 목적이 드러나는 타입을 검토합니다.

폭이 충분하다는 사실만으로 유효한 포인터가 되지는 않습니다. 주소가 매핑되어 있고 권한과 정렬이 맞으며 해당 객체의 수명 안이어야 합니다. 이 조건은 [가상 메모리와 TLB](../03-memory-hierarchy/07-address-translation-and-tlb.md), C 메모리 문서와 연결됩니다.

## IEEE 754 부동소수점

대표적인 이진 부동소수점 형식은 다음 필드를 사용합니다.

| 형식 | sign | exponent | fraction | 전체 폭 |
|---|---:|---:|---:|---:|
| binary32 | 1 | 8 | 23 | 32 |
| binary64 | 1 | 11 | 52 | 64 |

정규값은 개념적으로 다음과 같습니다.

```text
(-1)^sign × 1.fraction × 2^(exponent-bias)
```

유한한 비트로 모든 실수를 정확히 표현할 수는 없습니다. 십진수 `0.1`은 이진 분수로 유한하게 끝나지 않으므로 binary32와 binary64 모두 근삿값을 저장합니다.

```sh
python3 exercises/processor-model/reference/processor-model.py \
  bits float 0.1 --format f32
python3 exercises/processor-model/reference/processor-model.py \
  bits float 0.1 --format f64
```

### 특별한 지숫값

- exponent가 모두 0이면 zero 또는 subnormal입니다.
- exponent가 모두 1이면 infinity 또는 NaN입니다.
- `+0`과 `-0`은 비트가 다르지만 비교에서는 같은 값으로 취급될 수 있습니다.
- NaN 비교는 일반적인 실수 비교와 다릅니다.
- subnormal은 0 근처의 간격을 줄이지만 일부 하드웨어에서 비용이 다를 수 있습니다.

## 부동소수점 연산 순서

실수 수학에서는 덧셈의 결합법칙이 성립하지만 부동소수점은 각 중간 결과를 반올림합니다.

```text
(a + b) + c != a + (b + c) 일 수 있음
```

컴파일러의 벡터화나 병렬 reduction이 연산 순서를 바꾸면 마지막 몇 비트가 달라질 수 있습니다. 다음 요구를 구분합니다.

- 허용 오차가 있는 수치 계산
- 비트 단위 재현성이 필요한 계산
- overflow, underflow와 NaN 전파를 검사하는 계산

`fast-math` 계열 옵션은 단순한 속도 스위치가 아니라 IEEE 754 관련 가정을 완화할 수 있습니다. 허용하는 변환을 컴파일러 문서에서 확인합니다.

## 고정소수점

화폐처럼 소수 자릿수가 고정되고 정확한 정수 연산이 중요하면 최소 단위를 정수로 저장할 수 있습니다.

```text
10.25 단위 → 1025 최소 단위
```

이 방식도 자동으로 안전하지 않습니다. scale을 모든 API에서 일치시키고 곱셈 중간값의 폭, 나눗셈 반올림과 overflow를 명시해야 합니다.

## 직접 구현하기

`skeleton/processor_model/bits.py`에서 다음 함수를 완성합니다.

```text
to_signed
represent_integer
add_fixed
_float_fields
represent_float
```

구현 순서는 다음이 안전합니다.

1. `mask(width)`로 하위 `width`비트를 고정합니다.
2. 최상위 비트를 검사해 2의 보수 signed 값으로 바꿉니다.
3. 덧셈 결과, carry와 signed overflow를 별도 필드로 만듭니다.
4. `struct`로 binary32·binary64의 원시 비트를 얻습니다.
5. sign, exponent, fraction과 zero·subnormal·normal·infinity·NaN을 분류합니다.

현재 장까지의 누적 검사는 다음과 같습니다.

```sh
cd exercises/processor-model
make stage-01 EXERCISE_IMPL=workspace
```

이 대상은 `BitsTests`만 실행하므로 아직 구현하지 않은 ISA, 파이프라인과 캐시 코드가 먼저 실패하지 않습니다. 완성된 동작을 좁게 관찰하려면 reference의 `bits` 하위 명령만 사용합니다.

## 문제를 좁히는 순서

1. 값의 폭과 signedness를 적습니다.
2. 연산 전 피연산자를 같은 폭의 비트 패턴으로 씁니다.
3. extension 또는 truncation 위치를 표시합니다.
4. unsigned carry와 signed overflow를 별도로 계산합니다.
5. 메모리를 거치면 바이트 순서와 정렬을 확인합니다.
6. floating point라면 중간 반올림과 특수값을 확인합니다.

## 직접 확인할 문제

1. 8비트 패턴 `10000001`을 부호 없는 값과 부호 있는 값으로 각각 해석해 보세요.
2. `-128 - 1`을 8비트 2의 보수로 계산하고 signed overflow를 판정해 보세요.
3. `0x01020304`가 little-endian 메모리의 주소 `100`부터 어떤 바이트 순서로 놓이는지 적어 보세요.
4. binary32에서 `1.0f + 2^-25`가 다시 `1.0f`가 될 수 있는 이유를 설명해 보세요.
5. 구조체 멤버 재배치가 메모리를 줄여도 공개 바이너리 형식에 바로 적용하면 안 되는 이유를 설명해 보세요.

## 연결 실습

[`processor-model` stage-01](../../exercises/processor-model/README.md)에서 고정 폭 정수와 IEEE 754 field를 구현합니다.

## 완료 기준

- 같은 8비트 패턴을 signed와 unsigned 값으로 각각 해석할 수 있습니다.
- carry와 signed overflow가 다른 입력을 직접 만들 수 있습니다.
- `make stage-01 EXERCISE_IMPL=workspace`가 통과합니다.
