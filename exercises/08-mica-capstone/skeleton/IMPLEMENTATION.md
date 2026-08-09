# 구현 구조

## Phase graph

구현하면서 실제 module과 dependency direction을 기록합니다.

```text
source/diagnostic
→ lexer/token
→ parser/syntax
→ resolver/symbol
→ type/flow
→ interpreter 또는 VM/backend
→ formatter/linter/LSP adapter
```

## Phase contract

| Phase | Input | Output | User error | Internal invariant |
|---|---|---|---|---|
| source | | | | |
| lexer | | | | |
| parser | | | | |
| resolution | | | | |
| type/flow | | | | |
| execution | | | | |
