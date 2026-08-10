# Exercise 07 — 언어 도구

## 목표

Compiler core의 syntax·symbol·type 정보를 formatter/linter 또는 language server에 연결합니다.

## 실행 가능한 비교 근거

```sh
python3 exercises/07-language-tools/check.py
python3 examples/language-tools/tools.py --self-test
```

- [`fixtures/messy-with-comment.mica`](fixtures/messy-with-comment.mica)와 [`reference/formatted.mica`](reference/formatted.mica)은 exact output, comment 보존, idempotence와 token projection을 고정합니다.
- [`fixtures/lint-model.json`](fixtures/lint-model.json)과 [`reference/lint.json`](reference/lint.json)은 unused·unreachable·shadowing 진단의 stable code, 정렬과 unsafe fix 거부를 고정합니다.
- [`reference/lsp-transcript.json`](reference/lsp-transcript.json)은 UTF-16 emoji 위치와 version 2 이후 version 1 결과 폐기를 보여 줍니다.
- 작은 formatter의 token round-trip은 full parse/check 의미 동치를 대신하지 않습니다. capstone에서 실제 parser/type 결과도 비교하고 LSP 경로를 선택하면 JSON-RPC framing·cancellation을 사람 검토합니다.

## 경로 A: Formatter와 linter

### Formatter

- comment/trivia ownership
- precedence 기반 parenthesis
- line width와 indentation
- invalid source 정책
- idempotence
- parse/semantic round-trip

### Linter

최소 3개 rule:

- unused local
- unreachable statement
- shadowing 또는 constant condition

각 rule에 stable code, 필요한 analysis, severity, suppression와 fix applicability를 기록합니다.

Fix 적용 뒤 unrelated text와 effect가 보존되는지 확인합니다.

## 경로 B: LSP subset

필수:

- initialize/shutdown/exit
- open/change/close
- diagnostics
- hover
- definition

계약:

- document version
- negotiated position encoding
- stale result discard
- stdout protocol/log 분리
- cancellation 또는 time budget

## 공통 test

- Unicode position
- incomplete syntax
- stale edit/version
- deterministic diagnostic order
- syntax-only 기능과 semantic 기능 구분
- large file/resource budget

## Known-bad

- formatter가 comment를 삭제
- rename이 shadowed symbol까지 수정
- LSP가 version 1 diagnostic을 version 2에 게시
- JSON-RPC stdout에 log 출력

## 제출

- protocol/tool contract
- feature별 필요한 phase
- fixture/transcript
- idempotence 또는 stale-version test
- known-bad 거부
- 자동 적용하지 않은 unsafe fix 목록

## 완료 기준

도구가 compiler와 다른 의미 규칙을 만들지 않고, source version과 position을 정확히 처리하며, 잘못된 입력에서도 사용자 text를 조용히 손상시키지 않습니다.
