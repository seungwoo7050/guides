# 문자, source span과 위치

언어 도구가 다루는 첫 번째 상태는 “문자열”이 아니라 **버전이 있는 source snapshot과 그 안의 위치 체계**입니다. byte offset, Unicode code point, UTF-16 code unit과 화면 column을 섞으면 diagnostic, rename, incremental edit가 서로 다른 위치를 가리킵니다.

## 학습 목표

- source snapshot과 file path를 분리합니다.
- half-open byte span을 core identity로 사용하는 이유를 설명합니다.
- line/column, UTF-8 byte와 UTF-16 position 사이의 변환 경계를 설계합니다.
- newline, tab, Unicode와 generated source가 diagnostic에 미치는 영향을 다룹니다.

## Source는 immutable snapshot으로 봅니다

편집기에서 같은 경로의 파일은 계속 변합니다. 따라서 위치는 경로만으로 식별할 수 없습니다.

```text
SourceId: 논리 문서 식별자
Version:  편집 snapshot 번호
Bytes:    그 버전의 immutable UTF-8 입력
LineMap:  줄 시작 offset 색인
```

Diagnostic은 최소한 `SourceId + Version + Span`에 속해야 합니다. version 12의 span을 version 13의 문서에 그대로 적용하면 다른 텍스트를 강조할 수 있습니다.

Batch compiler에서는 content hash나 invocation-local source table index로 version을 대신할 수 있습니다. 중요한 것은 source가 바뀐 뒤 오래된 위치를 새 입력에 자동 적용하지 않는 것입니다.

## Core span은 half-open interval로 둡니다

이 가이드와 Mica 명세는 UTF-8 byte offset의 반열린 구간을 사용합니다.

```text
Span(start, end)   # start <= end
포함 범위: start <= offset < end
길이: end - start
```

장점은 다음과 같습니다.

- 빈 삽입 지점을 `start == end`로 표현합니다.
- 인접 token `[0, 3)`과 `[3, 4)`가 겹치지 않습니다.
- substring과 길이 계산이 단순합니다.
- EOF 위치를 `[len, len)`으로 표현합니다.

모든 constructor에서 다음 invariant를 검사합니다.

```text
0 <= start <= end <= len(source_bytes)
```

서로 다른 `SourceId`의 span을 합치는 연산은 허용하지 않습니다.

## Byte, code point, UTF-16 unit과 display column은 다릅니다

문자열 `a한🙂`를 생각해 봅니다.

- Unicode scalar/code point 수는 3입니다.
- UTF-8 byte 수는 1 + 3 + 4입니다.
- UTF-16 code unit 수는 1 + 1 + 2입니다.
- 화면 너비는 font와 terminal 규칙에 따라 다시 달라집니다.

Compiler core가 UTF-8 byte offset을 사용해도 editor protocol이 UTF-16 position을 요구할 수 있습니다. 변환은 protocol adapter가 담당하고 다음을 명시합니다.

- line은 0-based인지 1-based인지
- character가 byte, code point, UTF-16 unit 중 무엇인지
- newline 문자를 position에 포함하는지
- 잘못된 UTF-8을 허용하는지

LSP adapter는 document version과 협상된 position encoding을 확인한 뒤 core span을 protocol range로 바꿉니다.

## Line map은 줄 시작 offset을 색인합니다

전체 source를 매번 처음부터 세어 line/column을 만들면 많은 diagnostic에서 비용이 커집니다.

```text
line_starts = [0, 12, 27, 27 + ...]
```

Byte offset의 line은 `line_starts`에서 마지막 `<= offset` 위치를 binary search해 찾습니다. column은 line start부터 offset까지의 bytes를 선택한 단위로 해석합니다.

Line map의 invariant:

- 첫 원소는 항상 `0`입니다.
- 엄격히 증가합니다.
- 각 원소는 실제 newline 다음 byte입니다.
- source version이 바뀌면 함께 무효화하거나 edit delta로 갱신합니다.

## Newline 정책을 정합니다

입력에는 `LF`, `CRLF`와 드물게 `CR`이 있을 수 있습니다. 선택지는 두 가지입니다.

### 원본 byte를 보존

Lexer가 모든 newline 형식을 인식하고 span은 원본 byte를 가리킵니다. Formatter가 line ending 보존 정책을 선택할 수 있습니다.

### 읽을 때 정규화

내부 source를 `LF`로 바꾸고 원본과 내부 offset mapping을 따로 유지합니다. mapping이 없으면 diagnostic range가 editor 원문과 어긋납니다.

작은 compiler에서는 원본을 보존하는 편이 단순합니다. Mica core는 `LF`와 `CRLF`를 newline으로 인식하며 byte를 변경하지 않습니다.

## Tab과 화면 column을 분리합니다

Source column은 보통 text offset이고 display column은 tab stop과 grapheme width를 적용한 렌더링 위치입니다.

```text
\tfoo
```

Tab을 1 column으로 세는 source coordinate와 4 또는 8칸으로 그리는 underline은 동시에 존재할 수 있습니다. Diagnostic renderer는 다음을 별도 계산합니다.

1. source span → line과 text column
2. text slice → display cell
3. tab·wide character 정책에 따라 caret 폭 계산

Renderer의 화면 모양을 source protocol의 coordinate로 재사용하지 않습니다.

## Token span과 full span을 구분할 수 있습니다

주석과 공백(trivia)을 token에서 제거하면 formatter나 refactoring이 원본 범위를 복원하기 어렵습니다.

```text
// comment
let x = 1;
```

다음 두 범위를 둘 수 있습니다.

- `span`: token 자체의 범위
- `full_span`: 앞선 trivia 또는 node 전체를 포함한 범위

CST는 trivia를 node로 보존할 수 있고 AST는 semantic span만 가질 수 있습니다. 어느 구조를 선택하든 comment ownership 규칙을 문서화합니다.

## Generated source와 macro origin

Desugaring이나 macro expansion이 새 node를 만들면 source에 직접 대응하는 byte가 없을 수 있습니다.

단순한 선택:

```text
Origin = Direct(Span) | Synthetic(parent_span, reason)
```

더 복잡한 macro system에서는 call site, definition site와 expansion stack이 필요합니다. Diagnostic은 사용자에게 수정 가능한 위치를 primary span으로 제시하고, 생성 경로를 secondary note로 설명합니다.

## 위치 관련 대표 오류

- Unicode 문자를 1 byte로 가정합니다.
- EOF token의 span이 source 길이를 넘습니다.
- parser가 두 source file의 span을 합칩니다.
- `CRLF`의 `\r`을 별도 잘못된 문자로 보고합니다.
- 오래된 LSP diagnostic을 새 document version에 게시합니다.
- formatter가 comment가 붙은 node를 이동하면서 comment를 잃습니다.
- line/column을 저장하고 source edit 뒤 재계산하지 않습니다.

## 실습 연결

[Source와 diagnostic exercise](../../exercises/01-source-and-diagnostics/README.md)에서 byte span, line map과 diagnostic renderer를 구현합니다. `examples/diagnostic-renderer`는 UTF-8 byte span을 line과 caret로 바꾸는 작은 기준 예제입니다.

## 점검 질문

1. core span 단위를 UTF-8 byte로 선택했을 때 LSP 경계에서 무엇을 변환합니까?
2. 빈 span은 어떤 오류에서 필요합니까?
3. line ending을 정규화하면 원문 offset을 어떻게 보존합니까?
4. comment는 어느 syntax node에 소유됩니까?
5. generated node의 primary diagnostic 위치는 어떻게 선택합니까?
