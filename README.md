# Python

Python의 언어 특성부터 CLI automation, subprocess lifecycle, concurrency, testing, packaging까지 단계적으로 정리한 가이드입니다.

문법 자체를 폭넓게 나열하기보다 실제 프로그램을 작성할 때 필요한 **runtime model, data ownership, error boundary, resource lifecycle, automation, verification**에 초점을 둡니다.

`docs/`는 개념과 설계를 설명하고, `exercises/`는 해당 내용을 실제 구현으로 통합한 완성형 standalone project를 제공합니다.

## 구성

```text
.
├── docs
│   ├── 00-roadmap.md
│   ├── 01-language-and-runtime
│   │   ├── 01-runtime-and-environment.md
│   │   ├── 02-objects-and-collections.md
│   │   ├── 03-functions-errors-and-types.md
│   │   └── 04-iterators-generators-and-context-managers.md
│   ├── 02-automation
│   │   ├── 01-files-structured-data-and-cli.md
│   │   ├── 02-subprocess-and-process-lifecycle.md
│   │   └── 03-concurrency-and-cancellation.md
│   └── 03-quality
│       ├── 01-testing.md
│       ├── 02-project-structure-packaging-and-typing.md
│       └── 03-cli-test-runner.md
└── exercises
    └── command-checker
```

## Documentation

전체 흐름은 [Roadmap](docs/00-roadmap.md)에서 확인할 수 있습니다.

### 1. Language and Runtime

Python 프로그램이 실행되고 객체와 상태가 다뤄지는 기본 모델을 정리합니다.

| 문서                                                                                                                         | 내용                              |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| [Runtime and Environment](docs/01-language-and-runtime/01-runtime-and-environment.md)                                      | Python 실행 환경과 module/runtime 경계 |
| [Objects and Collections](docs/01-language-and-runtime/02-objects-and-collections.md)                                      | 객체와 collection의 동작 및 데이터 모델     |
| [Functions, Errors and Types](docs/01-language-and-runtime/03-functions-errors-and-types.md)                               | 함수 경계, 예외 처리, type contract     |
| [Iterators, Generators and Context Managers](docs/01-language-and-runtime/04-iterators-generators-and-context-managers.md) | iteration과 resource lifecycle   |

### 2. Automation

파일과 외부 프로세스를 다루는 CLI automation을 중심으로 구성합니다.

| 문서                                                                                            | 내용                                                  |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [Files, Structured Data and CLI](docs/02-automation/01-files-structured-data-and-cli.md)      | 파일 I/O, structured data, CLI boundary               |
| [Subprocess and Process Lifecycle](docs/02-automation/02-subprocess-and-process-lifecycle.md) | subprocess 실행과 process/resource lifecycle           |
| [Concurrency and Cancellation](docs/02-automation/03-concurrency-and-cancellation.md)         | concurrent execution, cancellation, resource limits |

### 3. Quality

구현을 검증하고 독립적인 Python project로 구성하기 위한 내용을 다룹니다.

| 문서                                                                                                      | 내용                        |
| ------------------------------------------------------------------------------------------------------- | ------------------------- |
| [Testing](docs/03-quality/01-testing.md)                                                                | 재현 가능한 테스트와 검증 경계         |
| [Project Structure, Packaging and Typing](docs/03-quality/02-project-structure-packaging-and-typing.md) | package 구조, 배포 경계, typing |
| [CLI Test Runner](docs/03-quality/03-cli-test-runner.md)                                                | 앞선 내용을 통합한 CLI 검사기 설계     |

## Exercise

### [`command-checker`](exercises/command-checker)

JSON으로 정의한 case contract에 따라 외부 CLI program을 실행하고 결과를 검증하는 standalone project입니다.

주요 책임은 다음과 같습니다.

* JSON specification validation
* immutable case/result model
* executable resolution
* `stdin`, `stdout`, `stderr`, `returncode` verification
* timeout과 output limit
* POSIX process group lifecycle 관리
* non-blocking pipe I/O
* bounded concurrent execution
* deterministic result ordering
* atomic JSON/JUnit report generation
* Python package 및 console-script 구성

구현은 학습용 skeleton이나 reference answer 형태가 아니라 완성된 project 자체로 제공됩니다.

자세한 사용법과 설계는 [`exercises/command-checker/README.md`](exercises/command-checker/README.md)를 참조하세요.

## 권장 순서

문서는 다음 순서로 읽는 것을 권장합니다.

```text
00-roadmap
    ↓
01-language-and-runtime
    ↓
02-automation
    ↓
03-quality
    ↓
exercises/command-checker
```

각 문서를 모두 암기하는 것이 목적은 아닙니다. 먼저 Python의 execution/data/error model을 이해하고, 이후 file·process·concurrency 같은 operational concern을 확장한 뒤 testing과 packaging을 통해 하나의 project로 완성하는 흐름을 기준으로 구성되어 있습니다.

## Requirements

주요 예제와 `command-checker`는 Python 3.12 이상을 기준으로 합니다.

`command-checker`의 process lifecycle 구현은 POSIX process group과 non-blocking file descriptor를 사용하므로 macOS와 Linux를 대상으로 합니다.

## Repository Model

이 저장소에서 두 영역의 역할은 명확히 분리됩니다.

```text
docs/
    concepts, reasoning, design

exercises/
    completed standalone implementations
```

`docs/`는 구현에 필요한 개념을 설명하고, `exercises/`는 그 개념들이 실제 source code와 project boundary 안에서 어떻게 결합되는지를 보여줍니다.
