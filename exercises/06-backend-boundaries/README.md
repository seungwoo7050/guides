# Exercise 06 — Backend 경계

## 목표

IR에서 target artifact로 이동할 때 data layout, call, object, runtime와 FFI의 계약을 문서화하고 선택 target에서 작은 프로그램을 실행합니다.

## 실행 가능한 기본 경로

Virtual ISA는 외부 compiler나 장비 없이 수행하는 기본 경로입니다.

```sh
python3 exercises/06-backend-boundaries/check.py
python3 examples/bytecode-vm/vm.py --self-test
```

- [`reference/virtual-target.json`](reference/virtual-target.json)은 value representation, call/return, builtin ABI, 한계와 신뢰 경계를 고정합니다.
- [`reference/bytecode-trace.json`](reference/bytecode-trace.json)은 valid compile, deterministic disassembly와 interpreter/VM differential 결과입니다.
- LLVM은 선택 경로이며 설치되지 않았다는 이유로 Virtual ISA 검사를 skip하지 않습니다. 실제 object/JIT를 선택하면 판본·triple·data layout·cleanup 증거를 별도로 제출합니다.

## 공통 과제

### Target manifest

```text
target triple 또는 virtual target
data layout
integer/bool/string representation
calling convention
symbol naming
object/JIT mode
runtime builtin ABI
unsupported feature
```

### Runtime builtin 하나

`print_int` 또는 string builtin에 대해 다음을 적습니다.

- symbol
- parameter/return representation
- ownership/lifetime
- error channel
- thread/re-entry
- cleanup

## 경로 A: Virtual ISA

- three-address IR→virtual instruction
- virtual register 또는 stack
- call convention
- disassembler
- interpreter와 differential execution

## 경로 B: LLVM

- module target/data layout
- function prototype pass
- checked arithmetic lowering
- verifier pre/post optimization
- JIT 또는 object emission
- runtime symbol resolution
- interpreter differential

## 관찰 과제

실제 object를 만든다면 다음을 기록합니다.

- section
- symbol
- relocation
- entry/runtime dependency
- disassembly 일부와 source operation 대응

## 실패 case

- runtime signature mismatch
- target feature 미지원
- wrong call arity/representation
- invalid relocation 또는 symbol 없음
- JIT resource lifetime 종료
- unsupported language feature가 silent wrong code를 만듦

## Known-bad

Mica checked addition을 plain target add로 낮춰 overflow fixture가 다른 결과를 내게 하거나 runtime parameter width를 바꿉니다.

## 제출

- target/runtime manifest
- 실행 명령
- verifier/object inspection 결과
- interpreter differential result
- sandbox와 신뢰 범위
- version/toolchain 기록

## 완료 기준

Target code가 실행된다는 사실뿐 아니라 frontend semantics와 같은 결과를 내고, 지원하지 않는 기능은 명시적으로 거부하며, runtime ABI가 문서와 artifact inspection에서 일치해야 합니다.
