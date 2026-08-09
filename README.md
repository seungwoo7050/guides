# 언어 구현과 개발 도구 가이드

소스 텍스트가 token, syntax tree, symbol, type, control-flow graph, intermediate representation, 실행 상태와 개발 도구 결과로 바뀌는 과정을 하나의 학습 경로로 연결합니다. compiler 이름과 parser generator 사용법을 외우기보다 **각 phase가 보존해야 하는 의미**, **오류가 속하는 경계**, **변환의 정확성을 검증하는 근거**를 중심으로 다룹니다.

```text
source text
→ tokens
→ CST / AST
→ name resolution / types
→ interpreter 또는 bytecode VM
→ CFG / IR / analysis / optimization
→ native·JIT·portable target
→ formatter·linter·language server
```

이 브랜치는 문서 중심입니다. 실행 코드는 작은 관찰 예제, `Mica` capstone의 명세·fixture·skeleton과 제출 검사기에 제한합니다. 완성 reference compiler를 제공하지 않으며, 학습자는 동일한 계약을 Python, C++ 또는 다른 언어로 구현할 수 있습니다.

## 시작

```sh
./prepare.sh
```

그 다음 [학습 로드맵](docs/00-roadmap.md)을 읽고 Part별 문서와 exercise를 진행합니다.

```sh
make check
```

전체 구조, 문서 링크, 예제, capstone 명세와 skeleton의 의도된 시작 상태는 다음 명령으로 검사합니다.

```sh
./verify.sh
```

## 읽는 순서

| Part | 주제 | 중심 질문 |
|---:|---|---|
| 1 | [언어 계약과 source model](docs/01-language-contract/) | 언어가 허용하는 프로그램과 도구가 보존할 source 정보는 무엇입니까? |
| 2 | [lexer, parser와 syntax tree](docs/02-front-end/) | 문자에서 구조를 만들며 모호성과 오류를 어떻게 통제합니까? |
| 3 | [이름, 타입과 정적 의미](docs/03-semantics/) | 문법적으로 맞는 프로그램 중 무엇을 의미 있는 프로그램으로 허용합니까? |
| 4 | [interpreter, VM과 runtime](docs/04-execution/) | 정적 의미를 실제 실행 상태와 실패로 어떻게 연결합니까? |
| 5 | [CFG, IR, data-flow와 optimization](docs/05-ir-and-analysis/) | 분석과 변환이 어떤 불변식을 보존해야 합니까? |
| 6 | [backend, LLVM, object와 FFI](docs/06-code-generation/) | 중간 표현을 실행 환경의 ABI·link·debug 계약으로 어떻게 낮춥니까? |
| 7 | [formatter, linter, LSP와 검증](docs/07-language-tooling/) | 불완전한 편집 상태에서도 정확하고 안정적인 도구를 어떻게 제공합니까? |
| 8 | [Mica capstone](docs/08-mica-capstone.md) | 작은 정적 타입 언어를 명세·진단·실행·도구 계약까지 어떻게 완성합니까? |

## 구현 경로

핵심 문서는 언어 중립입니다. 실행 가능한 예제와 skeleton은 Python 3.12 이상과 표준 라이브러리만 사용합니다.

- [Python 3.12 프로필](docs/90-implementation-profiles/python312.md): 가장 작은 구현 경로
- [C++20 프로필](docs/90-implementation-profiles/cpp20.md): 소유권·variant·visitor·build 경계
- [LLVM 프로필](docs/90-implementation-profiles/llvm.md): IR, verifier, JIT와 object code 선택 확장
- [Tree-sitter와 LSP 프로필](docs/90-implementation-profiles/tree-sitter-and-lsp.md): editor tooling 선택 확장

## 빠른 참조

- [용어](reference/glossary.md)
- [Phase contract 작성표](reference/phase-contracts.md)
- [설계 검토표](reference/design-review-checklist.md)
- [버전과 재현 기준](reference/version-baseline.md)
- [공식 명세와 추가 자료](reference/sources.md)
- [실제 프로젝트 진입 지도](reference/project-entry-map.md)

## 실습과 capstone

[실습 안내](exercises/README.md)는 다음 누적 흐름을 사용합니다.

```text
source span과 token
→ Pratt parser와 AST
→ scope·symbol·type
→ tree-walk execution
→ bytecode VM 또는 IR 경로
→ formatter·linter·LSP 중 하나
```

최종 capstone인 [`Mica`](exercises/08-mica-capstone/README.md)는 다음을 제공합니다.

- 언어·문법·진단·bytecode·conformance 명세
- 정상·실패 fixture
- 실행 가능한 Python package skeleton
- 단계별 CLI 계약
- 제출물을 실행하는 conformance runner
- 전체 답안 대신 설계 비교 기준을 제시하는 reference 안내

## 범위 경계

이 브랜치는 다음을 소유합니다.

- lexer, parser, CST/AST와 source location
- scope, symbol, name resolution과 type checking
- interpreter, bytecode VM과 runtime boundary
- CFG, IR, data-flow, SSA와 optimization 검증
- backend와 ABI·object·link·FFI의 접점
- formatter, linter, refactoring, incremental analysis와 LSP
- compiler와 언어 도구의 testing·fuzzing·compatibility

다음은 다른 브랜치의 소유입니다.

- 자료구조·그래프·복잡도 자체: [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms)
- ISA·pipeline·cache·실제 성능 모델: [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)
- process·virtual memory·filesystem 정책: [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- C, C++, Python 언어 입문과 일반 build: 해당 언어 브랜치

이 가이드의 종료점은 산업용 compiler 전체를 만드는 상태가 아닙니다. 작은 언어의 각 phase contract를 설계하고, 실패를 정확한 source 위치와 진단으로 보고하며, 하나의 실행 경로와 하나의 개발 도구를 구현한 뒤 실제 compiler·interpreter·analyzer 프로젝트에 진입할 수 있는 상태입니다.
