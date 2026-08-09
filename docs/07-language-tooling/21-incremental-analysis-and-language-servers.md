# Incremental analysis와 language server

Batch compiler는 완성된 file set을 한 번 처리하지만 language server는 사용자가 입력하는 매 순간 불완전하고 빠르게 변하는 source를 다룹니다. 정확한 semantic core를 공유하되 snapshot, cancellation, cache invalidation과 protocol version을 추가해야 합니다.

## 학습 목표

- document snapshot과 request version을 language server 상태의 기준으로 사용합니다.
- incremental parsing·dependency cache의 무효화 범위를 설명합니다.
- LSP lifecycle, document synchronization과 capability negotiation을 이해합니다.
- stale result, cancellation과 concurrent request가 잘못된 diagnostic/edit를 만들지 않게 합니다.

## Language server의 책임

LSP는 editor와 language-specific process 사이의 JSON-RPC protocol입니다. 대표 기능:

- diagnostics
- hover
- go to definition
- references
- completion
- rename
- formatting
- semantic tokens
- workspace symbol

Protocol이 compiler architecture를 대신하지는 않습니다. LSP adapter는 position, version과 capability를 core query에 변환합니다.

## Lifecycle

대표 순서:

```text
initialize request
→ initialize response(capabilities)
→ initialized notification
→ document/workspace requests
→ shutdown request
→ exit notification
```

Initialize 이전 request, shutdown 이후 작업과 process exit code를 정책에 맞게 처리합니다. Client capability를 확인하지 않고 unsupported edit/resource operation을 반환하지 않습니다.

## Document synchronization

두 모델:

### Full sync

변경 때마다 전체 text를 받습니다. 구현은 단순하지만 큰 문서에서 전송·parse 비용이 큽니다.

### Incremental sync

Range와 replacement text를 받습니다. Server는 정확한 이전 version을 가지고 있어야 합니다.

```text
DocumentState
  uri
  version
  text snapshot
  line map
  syntax tree
  semantic caches
```

Version이 기대와 다르거나 edit range가 현재 snapshot에 맞지 않으면 조용히 적용하지 않습니다. Client와 resync 또는 full text 요청 정책이 필요합니다.

## Position encoding

Core는 UTF-8 byte span을 쓸 수 있고 LSP는 negotiated position encoding을 사용합니다. 문서 snapshot의 line map으로 변환합니다.

주의:

- line/character는 0-based입니다.
- UTF-16에서는 non-BMP 문자가 code unit 두 개입니다.
- stale version의 range를 현재 source에 변환하지 않습니다.
- URI normalization과 filesystem path를 동일시하지 않습니다.

## Snapshot과 query

Immutable snapshot architecture:

```text
WorkspaceSnapshot(version graph)
  source text
  syntax
  declarations
  type results
  dependency edges
```

Request는 시작 시 snapshot을 잡고 끝까지 같은 version을 봅니다. 중간 edit가 들어오면 새 snapshot을 만들고 이전 request는 old result를 폐기하거나 cancellation합니다.

Lock 하나로 전체 workspace를 막는 구조는 completion latency를 키웁니다. Immutable data와 query cache가 concurrent read를 단순화합니다.

## Incremental invalidation

Edit 영향은 phase마다 다릅니다.

- comment 변경: token/trivia와 formatter, semantic에는 영향 없을 수 있음
- local body 변경: function syntax/type/body analysis
- public signature 변경: dependent module type check
- exported name 변경: import/reference index
- compiler option 변경: 전체 cache

Cache key에 입력을 빠뜨리면 stale result를 재사용합니다.

```text
QueryKey = operation + input identity + source versions + options + dependency fingerprints
```

“파일이 바뀌면 모든 것을 다시 계산”은 정확하지만 느립니다. 먼저 correctness를 확보한 뒤 invalidation을 좁힙니다.

## Incremental parsing

Tree-sitter 같은 incremental parser는 old tree와 edit 정보를 사용해 unchanged subtree를 재사용할 수 있습니다. 그래도 lexical mode나 grammar recovery 때문에 변경 영향이 예상보다 넓을 수 있습니다.

검증:

```text
incremental_parse(old, edit, new_text)
≈ full_parse(new_text)
```

Tree identity는 달라도 normalized syntax와 error set이 동치인지 비교합니다.

## Cancellation

Completion, references와 workspace analysis는 오래 걸릴 수 있습니다.

- request별 cancellation token
- lexer/parser loop의 budget point
- graph/worklist의 주기적 확인
- external process 취소
- partial result publish 정책

취소를 내부 오류로 보고하지 않습니다. Cancelled analysis의 cache를 complete result처럼 저장하지 않습니다.

## Diagnostics push/pull

Diagnostic은 document version과 연결합니다. 오래된 analysis가 늦게 끝나 최신 diagnostic을 덮어쓰지 않게 합니다.

```text
if result.version != current_document.version:
    discard
```

Workspace-wide diagnostic은 dependency 변경과 project config를 포함합니다. 동일 code/span/message를 deterministic order로 정렬합니다.

## Completion

편집 위치에는 syntax가 미완성입니다.

```text
foo.
call(arg,
let x =
```

Recovery CST와 expected token/type context를 사용합니다. Completion item resolve를 분리해 초기 응답을 작게 만들 수 있습니다. 자동 import edit는 client capability와 conflict를 확인합니다.

## Hover와 definition

- cursor position → syntax token/node
- node → resolved SymbolId
- symbol → declaration/type/doc
- core span → protocol range

Whitespace나 punctuation에서 가장 가까운 node를 선택하는 정책을 명시합니다. ErrorSymbol은 definition이 없으며 unknown name diagnostic과 충돌하지 않게 합니다.

## Rename

[Formatter·refactoring 문서](20-formatters-linters-and-refactoring.md)의 symbol-aware transaction을 LSP `prepareRename`/`rename`에 연결합니다. Stale version, unsaved document와 client가 지원하지 않는 file rename을 확인합니다.

## Server 관측

성능 로그에 source 내용을 무조건 남기지 않습니다.

- request method
- queue/run duration
- cancellation 여부
- snapshot version
- cache hit/miss
- analyzed file/node 수
- error class

사용자 code와 절대 path는 privacy 정책에 따라 redact합니다.

## 대표 실패

- version 5 diagnostic이 version 6 문서를 덮어씁니다.
- UTF-8 byte offset을 UTF-16 character로 그대로 전송합니다.
- 취소된 type result를 cache에 complete로 저장합니다.
- public signature 변경이 dependent file을 invalidate하지 않습니다.
- incremental parse가 full parse와 달라도 재사용합니다.
- initialize capability를 무시하고 unsupported WorkspaceEdit를 보냅니다.
- 모든 request가 global write lock을 잡아 typing마다 UI가 멈춥니다.

## 실습 연결

[언어 도구 exercise](../../exercises/07-language-tools/README.md)와 [Tree-sitter/LSP 프로필](../90-implementation-profiles/tree-sitter-and-lsp.md)을 사용합니다. Mica LSP 선택 경로는 diagnostics, hover와 definition만 필수로 하고 completion·rename은 확장으로 둡니다.

## 점검 질문

1. request가 시작 뒤 edit가 들어오면 어떤 snapshot을 사용합니까?
2. document version이 없는 diagnostic은 어떤 race를 만듭니까?
3. incremental result의 정확성을 full recomputation과 어떻게 비교합니까?
4. public function signature 변경 시 어떤 dependent query를 무효화합니까?
5. cancellation 결과를 cache하지 않아야 하는 이유는 무엇입니까?
