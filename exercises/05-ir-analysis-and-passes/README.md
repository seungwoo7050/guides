# Exercise 05 — IR, analysis와 pass

## 목표

Typed AST를 explicit CFG로 낮추고 data-flow와 작은 optimization을 verifier와 의미 동치 검사로 검증합니다.

## 과제

### 실행 가능한 시작과 비교 근거

```sh
python3 exercises/05-ir-analysis-and-passes/check.py
python3 examples/ir-pipeline/ir_pipeline.py --self-test
```

- [`fixtures/ir-cases.json`](fixtures/ir-cases.json)은 정상 실행, division trap과 invalid CFG를 고정합니다.
- [`reference/ir-pipeline.json`](reference/ir-pipeline.json)은 reachability 고정점, pass 전후 normalized IR와 differential 결과입니다.
- [`examples/ir-pipeline`](../../examples/ir-pipeline/README.md)은 verifier를 pass 전후 실행하고 checked fold만 허용합니다.
- 검사기는 `x / x → 1` known-bad가 `x = 0`의 `MICA4001`을 없애는 것을 거부합니다. 작은 verifier가 dominance·phi의 완전성을 증명하지는 않습니다.

### 1. IR schema

- Function, Block, Instruction, ValueId
- typed operand/result
- exactly one terminator
- source origin
- deterministic dump

### 2. Lowering

- if/else
- while
- short-circuit
- return
- call argument evaluation order

### 3. Verifier

- target block 유효
- terminator 정확히 하나
- terminated block 뒤 instruction 없음
- value definition/use와 type
- stack/phi/block-argument shape 선택

### 4. Analysis

하나 이상:

- liveness
- definite assignment
- reaching definitions
- dominance

Loop가 있는 CFG에서 fixed point를 구합니다.

### 5. Pass

최소 두 개:

- constant folding
- unreachable block removal
- trivial jump/threading
- dead pure instruction elimination

각 pass에 precondition, changed flag, preserved analysis와 verifier 실행을 기록합니다.

## 의미 보존

- unoptimized IR executor 또는 기존 interpreter와 비교
- may-trap/effect instruction 유지
- checked overflow policy 동일
- source runtime error code 동일

## Known-bad

`x / x → 1`을 zero check 없이 적용하거나, CFG 변경 뒤 stale phi/predecessor를 남기는 pass를 만듭니다.

## 제출

- normalized IR dump
- verifier code/error 목록
- worklist convergence 기록
- pass 전후 diff
- known-bad 거부
- differential output

## 완료 기준

Invalid IR는 실행 전에 거부되고, optimization 전후의 관찰 결과가 정상·runtime failure fixture에서 동일하며, pass가 무효화한 analysis를 다시 사용하지 않습니다.
