# Exercise 08 — Mica 언어 구현 capstone

이 capstone은 작은 정적 타입 언어를 여러 독립 단계로 구현합니다. 전체 정답 compiler는 제공하지 않습니다. 대신 언어·문법·진단·CLI·fixture와 공개 conformance runner를 제공해, 구현 언어나 내부 구조가 달라도 같은 외부 계약을 검증할 수 있게 합니다.

## 시작 상태

Python 기준 skeleton은 실행 가능한 package이지만 모든 phase가 의도적으로 미구현 상태입니다.

```sh
make capstone-start
```

직접 workspace를 만들려면 다음 명령을 사용합니다.

```sh
./scripts/new-workspace.sh .workspaces/mica
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace .workspaces/mica \
  --stage skeleton
```

`skeleton` 단계는 command가 종료 코드 `2`와 `MICA0000` 진단으로 명시적으로 실패하는지 확인합니다. 비어 있는 구현이 우연히 성공하는 상태를 허용하지 않습니다.

## 정본 문서

구현 전에 다음 순서로 읽습니다.

1. [언어 의미](spec/language.md)
2. [문법](spec/grammar.ebnf)
3. [진단과 JSON](spec/diagnostics.md)
4. [Conformance와 CLI](spec/conformance.md)
5. [Normalized AST](spec/normalized-ast.md)
6. VM 경로를 선택했다면 [bytecode 명세](spec/bytecode.md)

Schema 파일은 구조화 출력의 최소 외부 형태를 정합니다.

- [token schema](spec/token.schema.json)
- [AST schema](spec/ast.schema.json)
- [diagnostic schema](spec/diagnostic.schema.json)
- [semantic summary schema](spec/semantic.schema.json)
- [run result schema](spec/run-result.schema.json)

JSON Schema 자체가 모든 의미를 표현하지는 않습니다. 예를 들어 span이 실제 source byte 범위 안에 있는지, AST 자식 범위가 부모 범위에 포함되는지, branch merge stack type이 같은지는 별도 invariant 검사 대상입니다.

## 구현 단계

### Stage 1 — Source와 diagnostic

구현:

- immutable source snapshot
- UTF-8 byte offset 기반 half-open span
- line/column 변환
- structured diagnostic와 text renderer
- deterministic ordering와 error budget

검사:

```sh
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace .workspaces/mica \
  --stage source
```

### Stage 2 — Lexer

구현:

- keyword·identifier·operator·delimiter
- decimal integer와 string literal
- `//` comment와 trivia 정책
- longest match
- lexical diagnostic와 EOF token

검사:

```sh
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace .workspaces/mica \
  --stage lex
```

### Stage 3 — Parser와 AST

구현:

- top-level function
- declaration·statement·block
- recursive descent와 Pratt expression parser
- recovery node와 synchronization
- normalized AST JSON

검사:

```sh
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace .workspaces/mica \
  --stage parse
```

### Stage 4 — Name, type와 flow

구현:

- function signature 선등록
- lexical scope와 stable `SymbolId`
- same-scope duplicate와 shadowing 구분
- operator·call·condition·return type
- non-`Unit` function의 all-path return
- 정확한 `main` signature

검사:

```sh
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace .workspaces/mica \
  --stage check
```

### Stage 5 — Tree-walk interpreter

구현:

- left-to-right evaluation
- short-circuit
- immutable binding과 mutable cell
- function frame와 recursion budget
- checked signed 64-bit arithmetic
- output sink와 runtime diagnostic

검사:

```sh
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace .workspaces/mica \
  --stage run
```

여기까지는 `--stage all`이 검사하는 core 공개 conformance 경로이며 capstone 완료가 아닙니다.

### Stage 6 — IR·CFG·data-flow·pass 누적 증거

공개 runner가 이 단계의 교육적 완료를 자동 판정하지 않습니다. Exercise 05의 실행 가능한 oracle과 자신의 Mica 구현을 사용해 다음을 [`skeleton/EVIDENCE.md`](skeleton/EVIDENCE.md)에 기록합니다.

- typed AST→normalized IR lowering
- malformed CFG를 실행 전에 거부하는 verifier
- loop가 있는 CFG의 fixed-point trace
- pass 전후 IR, `changed`와 무효화한 analysis, verifier 재실행
- 정상 결과와 runtime diagnostic의 interpreter/IR differential
- trap/effect를 지우는 known-bad pass의 거부 결과

```sh
python3 exercises/05-ir-analysis-and-passes/check.py
```

### Stage 7 — 실행 확장 하나

다음 중 하나를 선택합니다.

#### A. Bytecode VM

- [bytecode 명세](spec/bytecode.md)
- verifier
- disassembler
- interpreter/VM differential test

```sh
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace .workspaces/mica \
  --stage vm
```

#### B. MIR/backend

공개 runner는 특정 LLVM binding이나 compiler를 강제하지 않습니다. 다음 증거를 별도로 제출합니다.

- MIR dump와 verifier
- target/data-layout 기록
- object 또는 JIT 실행 명령
- interpreter differential result
- 지원하지 않는 기능의 명시적 거부

### Stage 8 — Tooling 확장 하나

#### A. Formatter와 linter

```sh
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace .workspaces/mica \
  --stage format
```

Formatter는 idempotence와 parse round-trip을 만족해야 합니다. Linter는 최소 세 rule의 code·severity·analysis dependency·fix safety를 기록합니다.

`--stage format`은 formatter와 `lint --json`을 함께 검사합니다. Comment 보존, exact output, 고정점, normalized AST round-trip, unused·unreachable·shadowing code와 unsafe fix 거부가 공개 증거입니다.

#### B. LSP subset

공개 runner 대신 JSON-RPC transcript와 stale-version fixture를 제출합니다.

- initialize/shutdown/exit
- open/change/close
- diagnostics
- hover
- definition
- position encoding과 document version

## Workspace 계약

Python profile의 기본 구조는 다음과 같습니다.

```text
workspace/
├── pyproject.toml
├── IMPLEMENTATION.md
├── DECISIONS.md
├── LIMITATIONS.md
├── EVIDENCE.md
├── src/mica/
│   ├── __init__.py
│   ├── __main__.py
│   ├── source.py
│   ├── diagnostic.py
│   └── driver.py
└── tests/
```

다른 언어를 사용해도 됩니다. 이 경우 `--command`로 adapter command를 지정합니다.

```sh
python3 exercises/08-mica-capstone/check_submission.py \
  --workspace path/to/workspace \
  --command './build/mica' \
  --stage all
```

Runner는 command 뒤에 `lex`, `parse`, `check`, `run`, `format`, `lint`, `verify-bytecode`, `disassemble` 같은 하위 command와 fixture path를 붙입니다. VM 경로의 `run`은 `--engine interpreter|vm`을 받습니다.

## Workspace lifecycle과 실행 안전

- `make workspace WORKSPACE=.workspaces/<name>`은 기존 대상이 있으면 덮어쓰지 않고 실패합니다.
- `make clean`은 `.workspaces`의 학습자 구현을 보존합니다.
- `make purge-workspace WORKSPACE=.workspaces/<name>`은 명시한 workspace 하나만 영구 삭제하므로 먼저 백업합니다.
- workspace가 손상되면 기존 것을 지우지 말고 다른 이름으로 새 workspace를 만든 뒤 필요한 변경만 복구합니다.
- Runner의 기본 5초 timeout, stdout/stderr 각 1 MiB와 process-group 정리는 OS sandbox가 아닙니다. 신뢰하지 않는 구현, native/JIT/FFI는 network·credential·개인 파일이 차단된 container/VM에서 실행합니다.

## Fixture 정책

`fixtures/manifest.json`은 공개 입력과 최소 기대 결과를 정합니다.

- `valid`: 정상 실행과 stdout·return value
- `invalid`: compile phase와 stable diagnostic code
- `runtime`: 정의된 runtime failure
- `format`: canonical output과 idempotence
- `lint`: stable lint diagnostic과 fix safety
- `bytecode_invalid`: verifier가 거부해야 하는 모듈

공개 fixture를 하드코딩하면 완료가 아닙니다. 다음을 추가합니다.

- 정상 프로그램 3개 이상
- lexical·parse·resolution·type·flow 오류를 합쳐 5개 이상
- 자신의 구현에서 발견한 regression fixture 1개 이상
- known-bad 구현이 실패하는 검사 1개 이상

## 제출 기록

`IMPLEMENTATION.md`:

- phase graph와 dependency direction
- phase별 input/output schema
- state ownership
- error recovery와 invalid state 표현

`DECISIONS.md`:

- 명세에서 선택 가능한 부분
- 선택한 자료구조와 이유
- 다른 대안과 trade-off

`LIMITATIONS.md`:

- 미구현 command와 language feature
- resource limit
- 자동 검사가 보장하지 않는 것
- host runtime에 의존하는 동작

[`EVIDENCE.md`](skeleton/EVIDENCE.md):

- core conformance와 추가 fixture
- 필수 IR/analysis/pass 근거
- 선택 실행·tooling 경로와 differential
- known-bad, 자동 검사의 한계, 사람 판정
- cleanup과 복구 기록

## 완료 기준

- core Stage 1–5 공개 계약을 모두 통과합니다.
- Stage 6의 필수 IR/CFG analysis와 verifier-backed pass 증거를 제출합니다.
- 실행 확장 하나와 tooling 확장 하나를 완료합니다.
- 같은 source에서 반복 결과와 diagnostic 순서가 같습니다.
- invalid input에서 host traceback, assertion text 또는 임의 crash를 사용자 결과로 노출하지 않습니다.
- 자신의 known-bad 변경이 검사에 거부됩니다.
- 실제 compiler/interpreter/analyzer 저장소 하나에서 Mica phase와 대응하는 코드·test·issue 경계를 조사합니다.

공개 runner는 구현의 완전성이나 type soundness를 증명하지 않습니다. 완료 기록에는 runner가 보장하는 것과 보장하지 않는 것을 분리해 적습니다.

`scripts/testdata/conformance`의 positive adapter는 runner 자체를 검증하는 fixture-backed test double이며 learner compiler 답안이 아닙니다. `--stage all` 성공만으로 capstone 완료를 선언하지 않습니다.
