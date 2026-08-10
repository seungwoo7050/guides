# Reference 설계 비교 기준

이 capstone은 전체 reference compiler를 제공하지 않습니다. 학습자가 독립적인 phase 경계를 설계하고 public contract를 구현하는 과정이 핵심이기 때문입니다.

완료 뒤 다음 기준으로 자신의 구현을 검토합니다.

[`../skeleton/EVIDENCE.md`](../skeleton/EVIDENCE.md)에 아래 세 종료 능력의 산출물, 자동 증거와 사람 질문을 함께 기록합니다. 판정은 `충족`, `보완 필요`, `허용된 변형` 중 하나이며 미해결 `보완 필요`가 있으면 완료가 아닙니다.

| 종료 능력 | 필수 산출물 | 자동 증거 | 사람 검토 질문 | 판정 |
|---|---|---|---|---|
| 작은 언어의 frontend를 만듭니다 | source/token/normalized AST와 recovery diagnostic | `--stage lex`, `--stage parse`, token/AST golden 및 failure mutant | 모든 recovery 경로가 전진·종료하고 source identity를 보존합니까? |  |
| 정적 타입과 실행 모델을 구현합니다 | SymbolId/type/flow summary, tree-walk state와 runtime failure | `--stage check`, `--stage run`, semantic/runtime reference | ErrorType 보장 범위와 host runtime 의존성을 설명할 수 있습니까? |  |
| 분석·진단·변환 도구를 확장합니다 | verified IR/CFG/fixed-point/pass, 실행 확장 하나, tooling 확장 하나 | Exercise 05–07 checker, VM/format 선택 runner, known-bad | pass 의미 보존과 analyzer false positive/negative, backend/LSP 한계가 무엇입니까? |  |

자동 결과는 공개 행동의 대표 사례를 확인할 뿐 type soundness, 모든 parser 입력의 종료, optimizer의 전체 의미 보존이나 editor 상호운용성을 증명하지 않습니다.

## Source와 diagnostic

- Source snapshot이 immutable인가?
- Byte span과 protocol position을 분리했는가?
- Diagnostic code와 primary span이 message 문구와 독립적인가?
- Recovery 뒤 잘못된 span이나 중복 오류가 생기지 않는가?

## Front-end

- Lexer가 parser/type 의미를 과도하게 결정하지 않는가?
- Parser가 모든 오류에서 token을 소비하거나 종료하는가?
- CST/trivia와 semantic AST의 목적을 구분했는가?
- AST dump가 host object address에 의존하지 않는가?

## Semantic

- 문자열 이름 대신 `SymbolId`로 reference를 연결하는가?
- Function signature collection과 body resolution을 분리했는가?
- Error symbol/type으로 연쇄 진단을 통제하는가?
- All-path return이 syntax 모양이 아니라 CFG 또는 동등한 상태 분석을 사용하는가?

## Runtime

- Host value를 Mica value로 명시적으로 감싸는가?
- Evaluation order와 short-circuit를 test하는가?
- Checked i64 helper를 모든 실행 경로가 공유하는가?
- Runtime 오류가 source span과 Mica call stack을 보존하는가?

## VM/backend

- 실행 전에 verifier가 malformed IR/bytecode를 거부하는가?
- Interpreter와 differential test를 사용하는가?
- Backend verifier 통과와 Mica 의미 보존을 구분하는가?
- Target·ABI·runtime version을 artifact와 함께 기록하는가?

## Tooling

- Formatter가 idempotent하며 comment와 의미를 보존하는가?
- Lint/refactor가 semantic identity를 사용하고 unsafe fix를 구분하는가?
- LSP adapter가 source version과 position encoding을 검사하는가?
- Batch compiler의 semantic core를 재사용하는가?

## 비교할 실제 프로젝트

하나의 프로젝트가 모든 기준의 정답은 아닙니다. 최소 두 종류를 비교합니다.

- 작은 interpreter/compiler: phase 연결과 교육용 단순성
- production compiler 또는 analyzer: incremental state, diagnostics, compatibility, scale
- editor parser/server: incomplete source와 source version

프로젝트 이름보다 실제 source path, test, issue와 확인한 revision을 기록합니다.
