# 실습 안내

실습은 완성 답안을 복사하는 과정이 아니라 phase별 입력·출력·오류·검증을 직접 고정하는 과정입니다. 핵심 문서를 읽은 뒤 같은 번호의 exercise를 진행합니다.

## 전체 경로

| 단계 | Exercise | 주요 산출물 |
|---:|---|---|
| 1 | [Source와 diagnostic](01-source-and-diagnostics/README.md) | span, line map, diagnostic schema·renderer |
| 2 | [Lexer·parser·AST](02-lexer-parser-and-ast/README.md) | token contract, Pratt parser, AST dump |
| 3 | [Resolution·type·flow](03-resolution-types-and-flow/README.md) | SymbolId, type table, CFG fact |
| 4 | [Interpreter와 VM](04-interpreter-and-vm/README.md) | evaluator, frame, runtime error, bytecode 선택 |
| 5 | [IR·analysis·pass](05-ir-analysis-and-passes/README.md) | CFG verifier, data-flow, optimization proof |
| 6 | [Backend 경계](06-backend-boundaries/README.md) | target/ABI/FFI 계약, object/JIT 선택 |
| 7 | [언어 도구](07-language-tools/README.md) | formatter·linter 또는 LSP subset |
| 8 | [Mica capstone](08-mica-capstone/README.md) | 하나의 통합 언어 구현과 conformance 기록 |

## 공통 제출 형식

각 exercise directory와 별개 workspace에 다음 기록을 남깁니다.

```text
CONTRACT.md
- 입력
- 출력
- invariant
- 사용자 오류
- internal error
- 다음 phase가 의존하는 보장

CASES.md
- 정상
- 경계
- 실패
- known-bad

EVIDENCE.md
- 실행 명령
- 결과
- 자동 검사가 보장하는 것
- 보장하지 못하는 것
```

[templates](templates/)를 복사해 사용할 수 있습니다.

## 구현 언어

- Python 3.12 프로필이 저장소 runner의 기준입니다.
- C++20 또는 다른 언어를 사용해도 됩니다.
- 다른 언어를 사용하면 Mica CLI/JSON contract에 맞는 adapter를 제공해야 공개 conformance runner를 사용할 수 있습니다.

## Reference 정책

이 branch는 전체 reference compiler를 제공하지 않습니다. `examples`는 한 개념만 관찰하는 작은 완성 코드이고, capstone `reference/README.md`는 설계 비교 기준만 제공합니다.

답안이 없는 이유는 구현을 방치하기 위해서가 아닙니다. 다음을 명세와 검사로 고정해 독립 구현이 가능하게 합니다.

- stable input/output schema
- phase ownership
- 정상·오류 fixture
- CLI exit/channel contract
- known-bad가 거부되어야 하는 이유

## 완료 판정

- 공개 fixture를 통과합니다.
- 각 단계에 자신의 case를 추가합니다.
- 검사가 거짓 성공하지 않도록 known-bad 하나를 만듭니다.
- 설계 선택과 미구현 범위를 기록합니다.
- 다음 phase가 이전 phase의 내부 자료구조를 몰래 읽지 않게 합니다.
