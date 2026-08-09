# Exercise 03 — Resolution, type와 flow

## 목표

AST의 identifier text를 stable SymbolId에 연결하고, type rule와 control-flow fact를 별도 phase로 계산합니다.

## 과제

### 1. Scope와 symbol

- top-level function signature collection
- function parameter와 block local scope
- same-scope duplicate
- child scope shadowing
- forward call과 recursion
- builtin symbol

Reference dump는 다음을 보여야 합니다.

```text
reference span
name
resolved SymbolId
symbol kind
declaration span
```

### 2. Type checker

Mica type과 operator rule table을 구현합니다.

필수 진단:

- 잘못된 unary/binary operand
- condition이 Bool이 아님
- call 대상/arity/argument 오류
- declaration type mismatch
- return type mismatch
- `main` signature 오류

ErrorSymbol/ErrorType이 같은 원인의 연쇄 진단을 억제하는지 확인합니다.

### 3. Flow

- all-path return
- unreachable statement warning 선택
- initializer 없는 `var` 확장을 구현한다면 definite assignment
- loop fixed point
- short-circuit CFG

[`examples/dataflow-fixed-point`](../../examples/dataflow-fixed-point/README.md)를 참고하되 fact의 의미를 자신의 언어 규칙으로 적습니다.

## 실패 case

```text
unknown name
duplicate local
shadowed name의 잘못된 binding
wrong argument count
Bool + Int
non-Bool while
missing return
```

## Known-bad

Scope exit에서 binding을 pop하지 않는 resolver 또는 definite assignment merge에 union을 쓰는 변형을 만듭니다.

## 제출

- scope stack과 declaration-order 정책
- symbol/type dump schema
- type rule 표
- CFG 또는 flow fact dump
- 오류 suppression 기록
- known-bad 거부 결과

## 완료 기준

같은 text의 shadowed 이름이 서로 다른 SymbolId를 가리키며, type checker가 parser data structure를 변경하지 않고, 모든 non-Unit function의 normal exit path를 정확히 판정합니다.
