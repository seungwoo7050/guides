# command-runner

`command-runner`는 command string 하나를 tokenization, syntax validation, process execution 단계로 처리하는 standalone C utility다. 작은따옴표, 큰따옴표, escape, 빈 argument와 최대 한 개의 pipeline을 지원한다.

## Features

- unquoted whitespace 기반 argument 분리
- single-quoted literal text
- double quotes와 unquoted context의 backslash escape
- 인접한 quoted/unquoted fragments를 하나의 word로 결합
- `''`와 `""`를 실제 빈 argument로 보존
- 최대 한 개의 unquoted `|` pipeline
- unquoted `<`, `>`, `;`, `&`를 명시적 syntax error로 거부
- 전체 parsing 성공 뒤에만 child process 생성
- shell-style `126`, `127`, `128 + signal`, last-command status
- standard FD `0`/`1` 재사용과 large pipeline 처리

## Architecture

`builder`가 현재 word bytes를 소유하고, `command`가 null-terminated `argv`와 각 word allocation을 소유한다. `pipeline`은 최대 두 command의 전체 lifetime을 관리한다. Parser는 임시 pipeline 전체를 완성한 뒤에만 executor로 넘기므로 syntax error는 process side effect를 만들지 않는다.

## Build

```sh
make
```

Executable은 `build/command-runner`에 생성된다.

## Usage

```sh
./build/command-runner "printf '%s\\n' 'two words'"
./build/command-runner "printf 'alpha\\nbeta\\n' | wc -l"
```

Program exit status는 single command 또는 pipeline의 마지막 command status다. Syntax error는 `2`, parent-side process lifecycle failure는 `125`다.

## Supported Grammar

- Unquoted whitespace separates words.
- Single quotes preserve every enclosed character.
- In double quotes, backslash makes the next character literal.
- Outside quotes, backslash also makes the next character literal.
- Adjacent fragments form one word.
- One unquoted pipe is supported.
- Redirection, sequencing, background execution, expansion은 지원하지 않는다.

## Verification

```sh
make test
make sanitize
```

Process test는 정확한 `argv` boundaries, empty arguments, quoted control characters, malformed syntax, no-side-effect parsing failure, 4 MiB pipeline, standard FD reuse, exit/signal status, missing/non-executable commands를 확인한다.

## Design Decisions

- Parser가 전체 input을 성공적으로 commit하기 전에는 `fork`하지 않는다.
- Word allocation과 `argv` allocation을 pipeline lifetime에 묶어 모든 syntax failure path에서 일괄 정리한다.
- Pipeline child를 모두 시작한 뒤 wait해 pipe backpressure deadlock을 피한다.
- `execvp` failure는 child status `126` 또는 `127`로 표현하고 parent lifecycle failure와 분리한다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ----: | -------------- | -------------- |
| 1 | Growable word buffer | `src/command_runner.c` |
| 2 | Command and pipeline ownership | `src/command_runner.c` |
| 3 | Quote and escape tokenization | `src/command_runner.c` |
| 4 | Whole-line syntax commit | `src/command_runner.c` |
| 5 | Wait and descriptor policy | `src/command_runner.c` |
| 6 | Child exec boundary | `src/command_runner.c` |
| 7 | Single-command and pipeline execution | `src/command_runner.c` |
| 8 | CLI composition and cleanup | `src/command_runner.c` |

## Scope and Limitations

Interactive prompt, variable expansion, command substitution, globbing, redirection, logical operators, arbitrary pipeline length, job control은 구현하지 않는다. 이 program은 일반 shell 대체가 아니라 명시된 grammar의 deterministic runner다.
