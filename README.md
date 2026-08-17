# C와 POSIX 프로그래밍 가이드

C 언어의 기초부터 메모리와 API 설계, build와 test, POSIX I/O·process·signal, `pthread` 기반 concurrency까지 다루는 실전형 가이드입니다.  
이 repository는 하나의 거대한 tutorial이나 단계별 starter project를 제공하지 않습니다. 대신 다음 세 종류의 자료를 분리합니다.

```text
docs/
    개념, 원리, 설계 기준과 기술 설명

examples/
    특정 동작이나 시스템 경계를 좁게 보여 주는 완성 예제

exercises/
    독립적으로 build·run·test할 수 있는 완성된 standalone project
```

학습 순서는 문서를 처음부터 끝까지 암기하는 방식보다, 필요한 개념을 읽고 실제 구현을 확인하고 실행하면서 검증하는 흐름을 권장합니다.

```text
개념 이해
→ 작은 example로 동작 확인
→ standalone project의 구현과 contract 확인
→ 직접 build·test
→ 필요한 부분을 다시 docs에서 보강
```

## Repository structure

최종 repository는 다음 네 항목만을 top-level entry로 사용합니다.

```text
.
├── README.md
├── docs/
├── examples/
└── exercises/
```

### `docs/`

C와 POSIX programming의 개념적 기반을 설명합니다.

주요 범위는 다음과 같습니다.

```text
01-foundations/
    편집·컴파일·실행
    값·분기·반복
    함수·배열·텍스트
    입력 검증·오류 처리·디버깅

02-c-language/
    C program model
    memory·pointer·string
    data structure와 API design
    build·link·test
    variadic formatting API

03-unix-programming/
    POSIX I/O와 stream state
    process·file descriptor·pipe
    signal과 event 전달
    shell parser와 executor

04-concurrency/
    thread·synchronization·time

90-appendix/
    debugger
    Readline integration
    Unix text testing
```

전체 경로와 각 문서의 관계는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에서 확인할 수 있습니다.

### `examples/`

한 가지 기술적 동작이나 시스템 경계를 작은 완성 프로그램으로 보여 줍니다.

현재 예제는 다음과 같습니다.

| Example | Focus |
| --- | --- |
| [`fd-redirection`](examples/fd-redirection/)                     | stdout file descriptor ownership, truncate/append redirection |
| [`process-group-forwarding`](examples/process-group-forwarding/) | child process group과 signal forwarding                       |
| [`readline-repl`](examples/readline-repl/)                       | plain input loop와 optional Readline adapter                  |
| [`text-checks`](examples/text-checks/)                           | Unix text tools를 이용한 output verification                  |

`examples/`는 exercise의 정답이나 intermediate stage가 아닙니다. 특정 mechanism을 독립적으로 관찰하거나 검증하기 위한 작은 runnable artifact입니다.

### `exercises/`

완성된 standalone implementation project collection입니다.

각 project는 learner skeleton이나 reference answer 구조를 사용하지 않으며, 자신의 디렉터리만 복사해 별도 repository처럼 사용할 수 있도록 구성되어 있습니다.

현재 project는 다음과 같습니다.

| Project | Focus |
| --- | --- |
| [`number-report`](exercises/number-report/)               | strict integer parsing, statistics, overflow handling |
| [`textkit`](exercises/textkit/)                           | byte-string traversal과 word counting                 |
| [`owned-string`](exercises/owned-string/)                 | dynamic string ownership과 alias-safe append          |
| [`int-vector`](exercises/int-vector/)                     | dynamic container growth와 failure-state preservation |
| [`diagnostic-formatter`](exercises/diagnostic-formatter/) | bounded variadic formatting                           |
| [`record-stream`](exercises/record-stream/)               | stateful record framing over POSIX file descriptors   |
| [`command-pipeline`](exercises/command-pipeline/)         | `pipe`·`fork`·`dup2`·`execvp` lifecycle               |
| [`signal-loop`](exercises/signal-loop/)                   | self-pipe 기반 signal event 전달                      |
| [`command-runner`](exercises/command-runner/)             | quoting·parsing·pipeline execution                    |
| [`account-simulator`](exercises/account-simulator/)       | mutex ordering과 concurrent state consistency         |

Collection 전체 설명은 [`exercises/README.md`](exercises/README.md)에서 확인할 수 있습니다.

각 project README에는 다음 내용이 포함됩니다.

* project overview와 purpose
* public contract
* architecture와 ownership
* build와 usage
* project-local tests
* 주요 design decision
* scope와 limitation
* source annotation과 일치하는 global **Implementation Order**

## Recommended path

처음부터 학습한다면 다음 순서를 권장합니다.

| Order | Documentation | Related artifact |
| ---: | --- | --- |
|  1 | [`01-edit-compile-run.md`](docs/01-foundations/01-edit-compile-run.md)                    | [`number-report`](exercises/number-report/)                                                                     |
|  2 | [`02-values-branches-loops.md`](docs/01-foundations/02-values-branches-loops.md)          | [`number-report`](exercises/number-report/)                                                                     |
|  3 | [`03-functions-arrays-text.md`](docs/01-foundations/03-functions-arrays-text.md)          | [`textkit`](exercises/textkit/)                                                                                 |
|  4 | [`04-input-errors-debugging.md`](docs/01-foundations/04-input-errors-debugging.md)        | [`number-report`](exercises/number-report/)                                                                     |
|  5 | [`01-c-program-model.md`](docs/02-c-language/01-c-program-model.md)                       | [`textkit`](exercises/textkit/)                                                                                 |
|  6 | [`02-memory-pointers-strings.md`](docs/02-c-language/02-memory-pointers-strings.md)       | [`owned-string`](exercises/owned-string/)                                                                       |
|  7 | [`03-data-structures-api-design.md`](docs/02-c-language/03-data-structures-api-design.md) | [`int-vector`](exercises/int-vector/)                                                                           |
|  8 | [`04-build-link-test.md`](docs/02-c-language/04-build-link-test.md)                       | project-local `Makefile`과 tests                                                                                |
|  9 | [`05-variadic-format-api.md`](docs/02-c-language/05-variadic-format-api.md)               | [`diagnostic-formatter`](exercises/diagnostic-formatter/)                                                       |
| 10 | [`01-posix-io-streams.md`](docs/03-unix-programming/01-posix-io-streams.md)               | [`record-stream`](exercises/record-stream/)                                                                     |
| 11 | [`02-process-fd-pipe.md`](docs/03-unix-programming/02-process-fd-pipe.md)                 | [`fd-redirection`](examples/fd-redirection/), [`command-pipeline`](exercises/command-pipeline/)                 |
| 12 | [`03-signals-events.md`](docs/03-unix-programming/03-signals-events.md)                   | [`signal-loop`](exercises/signal-loop/)                                                                         |
| 13 | [`04-shell-parser-executor.md`](docs/03-unix-programming/04-shell-parser-executor.md)     | [`process-group-forwarding`](examples/process-group-forwarding/), [`command-runner`](exercises/command-runner/) |
| 14 | [`01-threads-time.md`](docs/04-concurrency/01-threads-time.md)                            | [`account-simulator`](exercises/account-simulator/)                                                             |

부록은 순차적으로 읽기보다 필요할 때 참조합니다.

| Appendix | Related example |
| --- | --- |
| [`01-debugger-reference.md`](docs/90-appendix/01-debugger-reference.md)     | 현재 debugging 대상 project                |
| [`02-readline-integration.md`](docs/90-appendix/02-readline-integration.md) | [`readline-repl`](examples/readline-repl/) |
| [`03-unix-text-testing.md`](docs/90-appendix/03-unix-text-testing.md)       | [`text-checks`](examples/text-checks/)     |

이미 C 경험이 있다면 foundations를 반드시 순서대로 진행할 필요는 없습니다. 필요한 topic의 문서와 artifact를 직접 선택해도 됩니다.

## Building and testing

Repository 전체를 하나의 root build system으로 묶지 않습니다.

`examples/`와 `exercises/`의 각 artifact가 자신의 build와 verification boundary를 소유합니다.

예를 들어:

```sh
cd exercises/owned-string

make
make test
make sanitize
```

또는:

```sh
cd examples/fd-redirection

make
make test
```

정확한 command와 optional verification은 각 디렉터리의 `README.md`와 `Makefile`을 기준으로 합니다.

Standalone project는 parent repository에 의존하지 않아야 합니다. 예를 들어 다음처럼 project 하나만 복사해도 build와 test가 가능해야 합니다.

```sh
cp -R exercises/command-pipeline /tmp/command-pipeline
cd /tmp/command-pipeline

make
make test
```

## Implementation annotations

`exercises/`의 completed source에는 project-wide construction sequence를 나타내는 `[Implementation N]` annotation이 있습니다.

이 번호는 source file 순서나 function 순서를 뜻하지 않습니다. Architecture, state dependency, ownership, failure handling과 integration 관계를 기준으로 재구성한 구현 순서입니다.

예를 들면 다음과 같은 흐름을 표현합니다.

```text
data model
→ invariant and ownership
→ core operation
→ failure boundary
→ resource lifecycle
→ integration
```

각 project의 `README.md`에 있는 **Implementation Order** table과 source annotation은 동일한 global numbering을 사용합니다.

Project끼리는 서로 독립된 artifact이므로 collection 전체를 관통하는 Implementation Order는 두지 않습니다.

## Design principles

이 repository의 code와 project 구조는 다음 원칙을 우선합니다.

### Explicit contracts

함수와 program의 success, failure, output, ownership과 lifetime을 명시적으로 구분합니다.

### Failure before mutation

Parsing, allocation, size calculation이나 system call처럼 실패 가능한 작업은 가능한 한 public state를 변경하기 전에 검증합니다.

### Resource ownership

Heap memory, file descriptor, process, mutex와 같은 resource의 owner와 release point를 명확하게 유지합니다.

### Observable verification

정상 case뿐 아니라 boundary condition, invalid input, overflow, allocation failure, descriptor cleanup, signal termination과 concurrent invariant를 tests로 확인합니다.

### Standalone boundaries

한 project가 다른 exercise나 repository-level helper에 기대지 않도록 project-local source, build configuration과 tests를 유지합니다.

## Environment and scope

주요 기준은 다음과 같습니다.

* Language: C99
* Unix API: POSIX.1-2008
* Primary environment: Linux와 macOS의 command-line environment
* Common tools: POSIX shell, `make`, C compiler
* 일부 verification: Python 3
* Optional features: AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer, Readline

Platform이나 compiler가 특정 sanitizer 또는 Readline을 지원하지 않을 수 있습니다. Optional 기능의 사용 가능 여부는 각 artifact의 README와 build target을 확인합니다.

이 가이드는 C standard library와 POSIX를 이용한 single-host user-space programming을 중심으로 합니다.

다음 영역은 주요 범위가 아닙니다.

* GUI application
* embedded hardware
* kernel development
* network protocol implementation
* distributed systems
