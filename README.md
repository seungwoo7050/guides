# 프로그래밍 언어 구현과 도구

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

이 브랜치는 `specialization` 경로입니다. 실행 코드는 작은 관찰 예제, `Mica` capstone의 명세·fixture·skeleton과 제출 검사기에 제한합니다. 완성 reference compiler를 제공하지 않으며, 학습자는 공개 phase 계약과 reference trace를 사용해 Python, C++ 또는 다른 언어로 독립 구현합니다.

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

`prepare.sh`와 `verify.sh`는 추적 source와 Git index를 바꾸지 않습니다. `make clean`도 `.workspaces`의 학습자 구현을 보존하며, 특정 workspace를 없앨 때만 `make purge-workspace WORKSPACE=.workspaces/<name>`을 명시적으로 사용합니다.

## 선행 계약

이 브랜치의 직접 필수 선행은 다음 세 브랜치입니다.

- [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp): C++의 수명·값·build·오류 경계를 설명하고 적용합니다.
- [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms): tree·graph·fixed-point·복잡도와 반례 검증을 사용합니다.
- [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture): ISA·stack·call·memory 실행 경계를 추적합니다.

[`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)는 runtime 자원과 process·virtual memory 진단에 유용한 권장 선행입니다. Python 3.12는 저장소 예제와 검사기의 실행 환경이지 `cpp` 선행 계약을 대체하는 언어 선택지가 아닙니다.

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

핵심 문서는 언어 중립입니다. 저장소가 즉시 실행하는 예제와 skeleton은 Python 3.12 이상과 표준 라이브러리만 사용합니다.

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
→ CFG·IR·data-flow·의미 보존 pass
→ bytecode VM 또는 backend 경로
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

- 문법·parser·CST/AST와 이를 만드는 lexer 경계
- scope·symbol·type checking·diagnostic
- interpreter·VM·runtime
- IR·CFG·data-flow·optimization
- formatter·linter·static analyzer·language server

다음은 의도적으로 소유하지 않습니다.

- C++ 언어 기초: [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp)
- 특정 상용 compiler 전체의 구조와 제품별 API
- CPU microarchitecture 설계: [`computer-architecture`](https://github.com/seungwoo7050/guides/tree/computer-architecture)

자료구조·그래프·복잡도 자체는 `algorithms`, process·virtual memory·filesystem 정책은 `operating-systems`가 소유합니다. Part 6의 ABI·object·link·FFI는 IR과 runtime이 외부 실행 계약을 넘기는 접점만 다루며, 인접 분야의 일반 원리를 다시 가르치지 않습니다.

## 트랙 위치와 종료점

- `language-tooling` 트랙의 필수 경로: `git → c → cpp → algorithms → computer-architecture → language-implementation`
- `systems-programming`과 `game-rendering` 트랙의 완료 뒤 심화 경로
- `game-engine-core` 트랙의 권장 보완 경로

이 브랜치는 별도 `connects`나 `continues_to` 브랜치를 선언하지 않습니다. 완료 뒤에는 다음 세 능력을 실제 trace와 구현 결과로 보여야 합니다.

1. 작은 언어의 frontend를 만듭니다.
2. 정적 타입과 실행 모델을 구현합니다.
3. 분석·진단·변환 도구를 확장합니다.

이 가이드의 종료점은 산업용 compiler 전체를 만드는 상태가 아닙니다. 작은 언어의 각 phase contract를 설계하고, 실패를 정확한 source 위치와 진단으로 보고하며, 하나의 실행 경로와 하나의 개발 도구를 구현한 뒤 실제 compiler·interpreter·analyzer 프로젝트에 진입할 수 있는 상태입니다.

## 실행 안전

Capstone runner는 command를 현재 사용자 권한으로 실행합니다. timeout, 출력 상한과 process-group 정리를 제공하지만 OS sandbox는 아닙니다. 출처를 신뢰할 수 없는 구현은 network와 개인 파일에 접근할 수 없는 container 또는 VM에서 실행합니다. LLVM JIT, native object와 FFI 확장은 필수가 아니며, 선택할 때는 실행 권한·symbol 수명·임시 artifact·cleanup과 복구 절차를 별도로 기록합니다.
