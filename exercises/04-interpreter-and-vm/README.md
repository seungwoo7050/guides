# Exercise 04 — Interpreter와 VM

## 목표

Typed program의 동적 의미를 tree-walk interpreter로 구현하고, 선택적으로 동일한 의미를 bytecode VM으로 옮깁니다.

## 필수 과제: interpreter

- tagged runtime value
- immutable binding와 mutable cell
- lexical block environment
- left-to-right operand/argument evaluation
- `&&`/`||` short-circuit
- function frame와 recursion
- checked i64 arithmetic
- output sink
- runtime diagnostic와 call stack
- step/call-depth budget

## Runtime case

- arithmetic와 comparison
- shadowed local
- mutable assignment
- nested if/while
- recursive function
- short-circuit 오른쪽 function이 실행되지 않음
- division by zero
- overflow와 `MIN / -1`
- call-depth 초과

## 선택 과제: bytecode VM

- opcode와 stack-effect table
- constant pool와 function chunk
- compiler emission
- jump patching
- local slot와 call frame
- verifier
- disassembler
- source map

[`examples/bytecode-vm`](../../examples/bytecode-vm/README.md)는 opcode loop의 최소 예입니다.

## Differential test

```text
same typed source
→ interpreter JSON result
→ VM JSON result
→ stdout, return, diagnostic code 비교
```

둘이 parser/type checker를 공유한다는 한계를 기록합니다.

## Known-bad

- short-circuit를 eager evaluation으로 변경
- `RETURN` 뒤 frame stack을 정리하지 않음
- jump target off-by-one
- overflow check 제거

## 제출

- runtime state와 outcome type
- evaluation order 문서
- runtime fixture 8개 이상
- VM 선택 시 bytecode verifier failure fixture 3개 이상
- differential result
- host runtime에 맡긴 memory/runtime 보장

## 완료 기준

사용자 runtime 오류는 host traceback 없이 stable code와 source call stack으로 보고되고, 모든 정상 fixture는 반복 실행에서 같은 output과 return value를 냅니다.
