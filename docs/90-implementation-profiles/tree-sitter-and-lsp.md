# Tree-sitter와 LSP 구현 프로필

이 프로필은 Mica core compiler가 완성된 뒤 editor tooling을 확장하는 경로입니다. Tree-sitter는 incremental CST를 제공하고 LSP는 editor와 language server 사이 protocol을 제공합니다. 둘 중 하나가 type checker나 project model을 대신하지는 않습니다.

## Tree-sitter를 사용할 때

적합:

- 편집할 때마다 빠른 syntax tree 필요
- error recovery가 있는 syntax highlighting/folding
- 여러 editor에서 parser 재사용
- CST query 기반 tooling

직접 parser를 유지할 이유:

- compiler diagnostic/recovery를 세밀하게 통제
- grammar가 작고 dependency를 줄이고 싶음
- semantic parse와 syntax highlighting 요구가 다름

두 parser를 쓰면 normalized tree equivalence와 grammar drift를 test해야 합니다.

## Grammar

- named/anonymous node 정책
- precedence와 conflict
- extras(comment/whitespace)
- field 이름
- error/missing node
- external scanner가 필요한 lexical mode

Generated parser output을 수동 수정하지 않습니다. Corpus test에 정상·오류·ambiguity case를 둡니다.

## Incremental 검증

```text
old tree + edit + new text
→ incremental tree

full parse(new text)
→ full tree
```

두 결과의 normalized CST와 error range를 비교합니다. Tree identity 재사용 자체보다 의미 동치가 중요합니다.

## Core AST adapter

Tree-sitter CST를 compiler AST로 낮추는 adapter를 둡니다.

```text
Tree-sitter node
→ source span/field validation
→ Mica AST
→ 기존 resolver/type checker
```

Batch direct parser와 Tree-sitter adapter가 같은 AST schema를 만들 수 있습니다. Recovery 차이는 ErrorNode 정책으로 흡수합니다.

## LSP baseline

현재 공식 LSP 3.18 문서를 기준으로 하되 client capability를 협상합니다. Protocol version을 hard-code한 가정으로 모든 client가 같은 feature를 지원한다고 생각하지 않습니다.

최소:

- initialize/shutdown/exit
- didOpen/didChange/didClose
- diagnostics
- hover
- definition

## Transport와 JSON-RPC

표준 입출력 transport에서는 header와 byte length를 정확히 읽습니다.

```text
Content-Length: N\r\n
\r\n
<JSON bytes>
```

Character count가 아니라 UTF-8 byte length입니다. Logging을 stdout에 쓰면 protocol stream이 깨지므로 stderr/file로 분리합니다.

## Document state

```text
URI
version
text snapshot
line map
syntax tree
semantic snapshot
```

Incremental edit를 적용하기 전에 version과 range를 확인합니다. Core byte span을 negotiated position encoding으로 변환합니다.

## Request architecture

```text
protocol adapter
→ workspace/document snapshot
→ syntax/semantic query
→ protocol result conversion
```

Core diagnostic과 LSP Diagnostic을 같은 type으로 만들지 않습니다. LSP severity/range/relatedInformation/capability는 adapter가 변환합니다.

## Cancellation과 concurrency

- request id별 cancellation token
- stale version result discard
- immutable snapshot read
- expensive workspace query 제한
- shutdown 후 새 task 거부

Response는 request id와 정확히 연결하고 notification에는 response를 보내지 않습니다.

## Test

Tree-sitter:

- corpus
- error/missing node
- edit sequence incremental/full equivalence
- query capture stability

LSP:

- framed JSON-RPC transcript
- initialize capability
- open/change/version
- UTF-16 또는 negotiated encoding
- stale diagnostic discard
- cancellation
- stdout에 log가 섞이지 않음

## 범위 제한

Editor extension UI, marketplace packaging과 모든 LSP method는 이 프로필의 범위가 아닙니다. Server core와 protocol conformance를 완료한 뒤 client packaging을 별도 프로젝트로 진행합니다.
