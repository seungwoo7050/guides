# 공식 명세와 추가 자료

최종 확인일: **2026-08-10**

이 목록은 문서의 소유권 경계를 확인하고 실제 프로젝트로 이동하기 위한 출발점입니다. 특정 버전의 동작을 구현할 때는 사용한 revision과 version을 별도로 기록합니다.

아래 URL은 최종 확인일에 읽기 전용으로 확인했습니다. 로컬 `verify.sh`는 재현성과 offline 실행을 위해 외부 URL을 요청하지 않으며, 링크의 장기 가용성이나 외부 문서의 기술 정확성을 자동 보장하지 않습니다.

## Python 표준 라이브러리

- [Lexical analysis — `tokenize`](https://docs.python.org/3.12/library/tokenize.html)
- [Abstract syntax trees — `ast`](https://docs.python.org/3.12/library/ast.html)
- [Symbol tables — `symtable`](https://docs.python.org/3.12/library/symtable.html)
- [Bytecode disassembly — `dis`](https://docs.python.org/3.12/library/dis.html)
- [Unicode database — `unicodedata`](https://docs.python.org/3.12/library/unicodedata.html)

Python의 AST나 bytecode를 Mica의 정답 형식으로 간주하지 않습니다. Production 언어가 source, symbol과 execution artifact를 어떤 API로 노출하는지 비교하는 자료입니다.

## LLVM

- [My First Language Frontend with LLVM](https://llvm.org/docs/tutorial/MyFirstLanguageFrontend/)
- [LLVM Language Reference Manual](https://llvm.org/docs/LangRef.html)
- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html)
- [Writing an LLVM New Pass](https://llvm.org/docs/WritingAnLLVMNewPMPass.html)
- [ORC Design and Implementation](https://llvm.org/docs/ORCv2.html)
- [Source Level Debugging with LLVM](https://llvm.org/docs/SourceLevelDebugging.html)

Tutorial은 빠른 code generation 진입점이며 production software engineering 전체의 모범 답안은 아닙니다. Mica backend는 LangRef의 type·control-flow·poison/undefined behavior와 verifier 조건을 별도로 확인합니다.

## Object, ABI와 debug

- [System V AMD64 ABI project](https://gitlab.com/x86-psABIs/x86-64-ABI)
- [ELF generic ABI](https://gabi.xinuos.com/)
- [PE/COFF specification](https://learn.microsoft.com/windows/win32/debug/pe-format)
- [DWARF standards](https://dwarfstd.org/)

Target 하나를 선택해 필요한 calling convention·object·relocation·debug 경계만 조사합니다. 여러 object format을 한 capstone에서 동시에 구현하지 않습니다.

## Language Server Protocol와 JSON-RPC

- [Language Server Protocol](https://microsoft.github.io/language-server-protocol/)
- [LSP 3.18 specification](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.18/specification/)
- [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification)

LSP adapter는 batch semantic core와 분리하며 lifecycle, document synchronization, capability negotiation, position encoding과 stale result를 실제 protocol transcript로 검사합니다.

## JSON과 schema

- [RFC 8259 — The JavaScript Object Notation Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259)
- [JSON Schema Core 2020-12](https://json-schema.org/draft/2020-12/json-schema-core)

Mica runner는 RFC 8259에 없는 `NaN`과 Infinity를 거부합니다. JSON Schema 2020-12는 문서화 형식이며, source identity·UTF-8 boundary·AST containment처럼 schema만으로 표현하기 어려운 invariant는 runner가 직접 검사합니다.

## Tree-sitter

- [Tree-sitter introduction](https://tree-sitter.github.io/tree-sitter/)
- [Creating parsers](https://tree-sitter.github.io/tree-sitter/creating-parsers/)
- [Grammar DSL](https://tree-sitter.github.io/tree-sitter/creating-parsers/2-the-grammar-dsl.html)
- [Using parsers](https://tree-sitter.github.io/tree-sitter/using-parsers/)
- [Queries](https://tree-sitter.github.io/tree-sitter/using-parsers/queries/)

Tree-sitter는 concrete syntax와 incremental edit에 유용하지만 name·type·flow의 정본을 자동으로 제공하지 않습니다. Core AST adapter와 semantic invalidation을 별도로 설계합니다.

## Unicode와 source position

- [Unicode Standard](https://www.unicode.org/versions/latest/)
- [Unicode Standard Annex #29: Text Segmentation](https://unicode.org/reports/tr29/)
- [Unicode Standard Annex #15: Normalization Forms](https://unicode.org/reports/tr15/)

Core span, display column, grapheme cluster와 protocol UTF-16 position을 하나의 숫자로 취급하지 않습니다.

## Portable execution target

- [WebAssembly Core Specification](https://webassembly.github.io/spec/core/)

LLVM/native backend 대신 portable stack machine target을 선택하는 확장에 사용할 수 있습니다. Mica semantics와 target trap/overflow 규칙의 차이는 adapter가 명시적으로 보정해야 합니다.

## 교과서와 공개 학습 자료

- Alfred V. Aho, Monica S. Lam, Ravi Sethi, Jeffrey D. Ullman, *Compilers: Principles, Techniques, and Tools*.
- Keith Cooper, Linda Torczon, *Engineering a Compiler*.
- Andrew W. Appel, *Modern Compiler Implementation* series.
- Bob Nystrom, [Crafting Interpreters](https://craftinginterpreters.com/).

이 자료의 예제 언어나 architecture를 그대로 복제하기보다 현재 phase contract와 실패 검증에 필요한 장을 선택합니다.
