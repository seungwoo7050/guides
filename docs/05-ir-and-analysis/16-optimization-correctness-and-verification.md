# Optimization, correctness와 verifier

Optimization은 코드를 더 빠르게 만드는 아이디어 목록이 아니라 **관찰 가능한 의미를 보존하는 변환**입니다. Target language의 overflow, trap, evaluation order, I/O와 concurrency 규칙을 모르면 수학적으로 맞아 보이는 변환도 잘못될 수 있습니다.

## 학습 목표

- optimization의 precondition과 preserved semantics를 작성합니다.
- local rewrite, data-flow 기반 pass와 interprocedural pass의 차이를 설명합니다.
- verifier, differential test와 translation validation을 결합합니다.
- 성능 개선과 compiler 비용·code size·debuggability의 trade-off를 측정합니다.

## 관찰 가능한 의미

프로그램 관찰 결과에 무엇을 포함하는지 정합니다.

Mica core:

- stdout byte sequence
- main return value
- runtime diagnostic code와 발생 source origin
- 종료/비종료

포함하지 않는 것:

- 내부 temporary 이름
- block numbering
- 실행 instruction 수 자체

Debug build에서는 step location이나 stack trace shape를 추가 보장할 수 있습니다. Optimization level별 계약을 구분합니다.

## Rewrite rule

```text
x + 0 → x
```

항상 안전해 보이지만 다음을 확인합니다.

- `x` 평가가 정확히 한 번 유지됩니까?
- `+`가 user-defined overload를 호출합니까?
- type coercion 또는 checked operation이 있습니까?
- source-level trap이나 debug event가 사라집니까?

Mica `Int`의 built-in addition에서 오른쪽 literal 0이고 `x`를 한 번 유지한다면 안전합니다. General language에서는 rule precondition이 더 큽니다.

## Constant folding

Host 연산을 그대로 사용하지 않습니다.

- integer width와 signedness
- overflow/wrap/trap
- floating NaN, signed zero와 rounding
- division policy
- string encoding과 locale

Compile-time 오류를 runtime 오류로 당길 수 있는지 언어가 정의해야 합니다. `1 / 0`을 type phase에서 error로 만들지, executable이 runtime에 fail하게 둘지 정책을 고정합니다.

## Dead code elimination

Result가 사용되지 않는다고 instruction을 제거할 수는 없습니다.

제거 조건:

```text
result has no uses
AND no externally visible effect
AND cannot trap under language semantics
AND removal does not change debug/termination guarantee if preserved
```

Function call은 effect summary가 없으면 보수적으로 유지합니다. Infinite loop나 blocking call은 output이 없어도 termination을 바꿉니다.

## Common subexpression elimination

```text
a = x + y
b = x + y
```

두 번째 계산을 재사용하려면 operand가 바뀌지 않고 operation이 pure하며 첫 결과가 모든 path에서 도달해야 합니다. Memory load는 aliasing과 intervening store를 고려합니다.

## Control-flow simplification

- unreachable block 제거
- constant branch folding
- empty block jump threading
- single predecessor block merge

Edge를 바꾼 뒤 phi/block argument, source origin, loop metadata와 analysis를 갱신합니다. Terminator만 바꾸고 predecessor list를 그대로 두면 verifier가 잡아야 합니다.

## Function inlining

이점:

- call overhead 제거
- 상수 전파와 specialization 기회

비용:

- code size 증가
- compile time 증가
- instruction cache 압력
- debug stack과 source mapping 복잡

Recursive function, large body, cold call과 exception/cleanup을 고려합니다. “작은 함수는 모두 inline” 같은 규칙 대신 cost model을 측정합니다.

## Pass contract

```text
Pass
  input IR level
  preconditions
  transformation
  preserved analyses
  changed flag
  verification policy
```

각 pass 전후에 verifier를 실행하면 느릴 수 있지만 debug/test mode에서 강한 근거가 됩니다. Release compiler에서는 pipeline checkpoint별로 실행할 수 있습니다.

## Correctness test

### Unit rewrite test

작은 pattern과 precondition을 직접 검사합니다.

### Differential execution

같은 source를 unoptimized와 optimized backend로 실행해 관찰 결과를 비교합니다.

### Random program generation

Type-correct하고 종료가 제한된 작은 프로그램을 생성해 여러 backend 결과를 비교합니다.

### Metamorphic test

의미가 같아야 하는 source 변형을 만듭니다.

```text
괄호 추가
unused local 이름 변경
alpha-renaming
독립 declaration 순서 변경 정책상 허용 시
```

### Translation validation

각 optimization 결과가 원본과 동치인지 별도 checker가 확인합니다. 모든 pass를 수학적으로 증명하기 어려울 때 강한 접근입니다.

## Known-bad fixture

Verifier와 test가 실제로 오류를 잡는지 확인합니다.

- wrong jump target
- stale phi operand
- `x / x → 1`을 `x=0`에서 잘못 적용
- may-trap instruction 제거
- short-circuit를 eager evaluation으로 변경
- checked overflow를 host wrap으로 변경

Known-bad가 통과하면 검사기의 거짓 성공입니다.

## 성능 측정

Optimization 성공을 IR instruction 감소만으로 판정하지 않습니다.

- representative input
- compile time
- code size
- runtime과 variance
- warm-up/JIT 상태
- hardware·compiler·flags
- correctness result

Microbenchmark와 end-to-end workload를 구분합니다. 작은 Mica capstone에서는 변환 count와 differential correctness를 우선하고 실제 속도 향상 주장은 제한합니다.

## Optimization level

```text
-O0: source 대응과 빠른 compile
-O1: 값싼 local simplification
-O2: data-flow와 inlining 일부
-O3: 더 공격적 cost/size trade-off
```

Level 이름은 관례일 뿐 보장 목록을 문서화해야 합니다. `-O0`도 반드시 “변환 없음”은 아닙니다. Well-formedness를 위한 lowering과 mandatory cleanup은 필요합니다.

## 대표 실패

- host arithmetic이 target overflow 의미를 바꿉니다.
- effect 없는 것으로 잘못 표시한 call을 제거합니다.
- pass가 CFG를 바꾸고 dominance를 preserved라고 선언합니다.
- instruction 수 감소를 runtime 향상으로 단정합니다.
- optimized와 unoptimized가 같은 잘못된 interpreter helper를 공유해 differential test가 놓칩니다.
- source map을 갱신하지 않아 runtime error 위치가 달라집니다.

## 실습 연결

[IR와 pass exercise](../../exercises/05-ir-analysis-and-passes/README.md)에서 constant folding, unreachable removal과 known-bad pass를 작성합니다. 모든 pass는 verifier 전후 통과와 interpreter differential result를 남깁니다.

## 점검 질문

1. `x / x → 1`의 precondition은 무엇입니까?
2. dead result와 dead instruction은 어떻게 다릅니까?
3. pass가 보존하는 analysis를 잘못 선언하면 어떤 종류의 bug가 생깁니까?
4. differential test가 공유 bug를 놓칠 수 있는 이유는 무엇입니까?
5. optimization의 성공을 어떤 correctness와 performance 증거로 판단합니까?
