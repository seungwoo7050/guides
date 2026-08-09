# 버전과 재현 기준

기준일: **2026-08-09**

## 필수 실행 환경

| 항목 | 기준 | 사용 범위 |
|---|---|---|
| Python | 3.12 이상 | 예제, skeleton, 공개 conformance와 저장소 검사 |
| POSIX shell | `sh` | 준비·검증·workspace script |
| Make | POSIX에서 일반적으로 제공되는 `make` | 공개 개발 target |
| Git | 2.x | source 상태와 프로젝트 기여 흐름 |

Python 예제는 표준 라이브러리만 사용합니다. 저장소 script가 package manager나 system package를 자동 설치하지 않습니다.

## 선택 toolchain

| 항목 | 정책 |
|---|---|
| C++ | C++20을 지원하는 compiler를 선택하고 exact compiler/version을 제출 기록에 남깁니다. |
| LLVM | 특정 version을 branch 필수 조건으로 고정하지 않습니다. LLVM 경로를 구현하면 `llvm-config --version`, target triple, data layout과 사용 API를 기록합니다. |
| Tree-sitter | Core 경로의 필수 dependency가 아닙니다. 선택 grammar는 CLI/runtime version과 generated artifact를 고정합니다. |
| LSP | Specification 3.18을 baseline으로 사용하며 client capability negotiation 결과를 기록합니다. |
| JSON Schema | 2020-12 문법을 schema 문서 표기에 사용합니다. Runner는 외부 validator 없이 핵심 invariant를 직접 검사합니다. |

## 재현 기록

실제 구현 제출에는 다음을 남깁니다.

```text
운영체제와 architecture
Python/compiler/LLVM version
dependency lock 또는 commit
build mode와 option
target triple과 data layout
실행 명령과 environment variable
fixture revision
선택 검사에서 건너뛴 항목과 이유
```

## 업데이트 정책

- 필수 version을 올릴 때 `prepare.sh`, CI와 문서를 같은 변경에서 수정합니다.
- 최신 tool 문서를 사용하더라도 capstone language semantics를 자동으로 바꾸지 않습니다.
- LSP·LLVM·Tree-sitter version 변화는 adapter/profile 문서가 소유하며 core docs는 원리와 contract를 유지합니다.
- Deprecated API를 교체할 때 observable CLI, diagnostic와 artifact compatibility를 별도로 검토합니다.
