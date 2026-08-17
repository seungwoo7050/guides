# C Exercises

`exercises/`는 C와 POSIX programming의 주요 engineering topic을 작은 standalone project 형태로 정리한 completed implementation collection입니다.

각 하위 디렉터리는 다른 project의 source, 상위 repository의 helper script, hidden reference implementation에 의존하지 않습니다. Project 하나를 별도 repository로 분리하더라도 자체 `README.md`, source, build configuration, tests만으로 build하고 검증할 수 있도록 구성되어 있습니다.

## Projects

| Project | Artifact | Main responsibilities |
| --- | --- | --- |
| [`account-simulator/`](account-simulator/)       | Concurrent C library         | `pthread_mutex_t` ownership, canonical lock ordering, atomic transfer, consistent snapshots |
| [`command-pipeline/`](command-pipeline/)         | POSIX process library        | `pipe`, `fork`, `dup2`, `execvp`, descriptor lifecycle, pipeline exit status                |
| [`command-runner/`](command-runner/)             | Standalone CLI               | command tokenization, quoting and escape rules, syntax validation, process execution        |
| [`diagnostic-formatter/`](diagnostic-formatter/) | Formatting library           | bounded output, `%s`/`%d`/`%%`, truncation semantics, `va_list` handling                    |
| [`int-vector/`](int-vector/)                     | Dynamic container library    | capacity growth, allocator injection, strong failure-state preservation                     |
| [`number-report/`](number-report/)               | Standalone CLI               | strict integer parsing, aggregate statistics, overflow-safe accumulation                    |
| [`owned-string/`](owned-string/)                 | Dynamic string library       | owned buffer lifecycle, alias-safe append, allocator failure handling                       |
| [`record-stream/`](record-stream/)               | Stateful I/O library         | fragmented reads, newline framing, embedded NUL, EOF and failure states                     |
| [`signal-loop/`](signal-loop/)                   | POSIX signal utility         | self-pipe pattern, async-signal-safe handlers, signal masking and teardown                  |
| [`textkit/`](textkit/)                           | String utility library + CLI | byte-string traversal, character counting, whitespace-delimited word counting               |

각 project의 상세 contract, architecture, scope, usage, tests와 project-wide **Implementation Order**는 해당 디렉터리의 `README.md`에 정리되어 있습니다.

## Structure

Collection-level curriculum category는 directory hierarchy에 반영하지 않습니다. `exercises/`의 direct child는 모두 최종 artifact의 identity를 기준으로 구성됩니다.

```text
exercises/
├── account-simulator/
├── command-pipeline/
├── command-runner/
├── diagnostic-formatter/
├── int-vector/
├── number-report/
├── owned-string/
├── record-stream/
├── signal-loop/
└── textkit/
```

각 project는 일반적으로 다음 요소만 포함합니다.

```text
<project>/
├── README.md
├── Makefile
├── include/        # public headers가 필요한 경우
├── src/            # implementation source가 분리된 경우
└── tests/          # project-local verification
```

Project 성격에 따라 source layout은 달라질 수 있습니다. 불필요한 `skeleton/`, `reference/`, learner workspace, answer directory나 repository-level verifier는 포함하지 않습니다.

## Build and verification

모든 project는 자신의 디렉터리에서 독립적으로 build하고 test합니다.

```sh
cd exercises/<project>

make
make test
make sanitize
```

공통적으로 사용할 수 있는 Make targets는 다음과 같습니다.

```text
all
test
sanitize
clean
fclean
re
```

`account-simulator`는 concurrent behavior를 추가로 검사하기 위해 지원 환경에서 다음 target도 제공합니다.

```sh
make thread-sanitize
```

Compiler나 platform의 ThreadSanitizer 지원 여부에 따라 이 검사는 사용할 수 없을 수 있습니다.

## Standalone use

Project는 `guides` repository 밖으로 복사해도 동작하도록 구성되어 있습니다.

```sh
cp -R exercises/record-stream /tmp/record-stream
cd /tmp/record-stream

make
make test
```

다른 project의 source나 root-level script를 참조해야 정상 동작한다면 standalone project로 간주하지 않습니다.

## Implementation Order

각 project의 source에는 architecture-driven construction sequence를 나타내는 `[Implementation N]` annotation이 있습니다.

이 numbering은 file order나 function order가 아니라 다음과 같은 engineering dependency를 기준으로 합니다.

```text
core model
→ ownership and invariants
→ core behavior
→ failure handling
→ resource lifecycle
→ integration
```

하나의 project 안에서는 여러 source file을 가로질러 동일한 global sequence를 사용하며, 해당 project의 `README.md`에 있는 **Implementation Order** table과 source annotation이 일치합니다.

Collection 전체에는 별도의 공통 Implementation Order를 두지 않습니다. 각 directory가 서로 독립적인 final artifact이므로 project 간 순서는 architecture dependency를 의미하지 않습니다.

## Scope

이 collection은 현재 project들이 구현하는 contract에 집중합니다. 각 project는 자신의 README에 명시한 behavior와 limitation만을 책임집니다.

규모가 작다는 이유로 project를 합치지 않으며, 반대로 같은 C/POSIX primitives를 사용한다는 이유만으로 서로 다른 artifact를 하나로 합치지도 않습니다. Directory boundary는 최종 program 또는 library의 독립적인 purpose, interface, ownership model과 runtime behavior를 기준으로 결정됩니다.
