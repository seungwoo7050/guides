# C와 POSIX 프로그래밍 가이드

이 저장소는 프로그래밍을 처음 시작하는 단계부터 여러 파일로 구성된 C 프로그램, 작은 라이브러리, POSIX 프로세스 프로그램과 동시성 프로그램을 독립적으로 만들 수 있는 단계까지 안내합니다.

학습의 목표는 문법을 한 번에 암기하는 것이 아닙니다. 각 단계에서 다음 반복을 스스로 수행하는 능력을 만드는 것입니다.

```text
문제를 작은 계약으로 정한다
→ 코드를 작성한다
→ 컴파일하고 실행한다
→ 정상·경계·실패 사례를 검사한다
→ 오류 원인을 분류하고 수정한다
```

## 저장소 준비와 전체 검증

저장소 루트에서 다음 두 명령을 순서대로 실행합니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 검증 전에 필요한 상태만 준비합니다.

- 이전 구조의 파일과 생성 로그를 제거합니다.
- 남아 있는 빌드 산출물을 정리합니다.
- 필수 도구와 Python 버전을 확인합니다.
- C99·POSIX, AddressSanitizer, ThreadSanitizer와 Readline 사용 가능 여부를 실제 컴파일·실행으로 확인합니다.
- 확인한 선택 기능과 빌드 플래그를 `.guide-prepare.env`에 기록합니다.

운영체제 패키지를 관리자 권한으로 임의 설치하지는 않습니다. 필수 도구가 없으면 필요한 항목을 정확히 출력하고 실패합니다. Readline과 sanitizer처럼 플랫폼에 따라 제공되지 않을 수 있는 검사는 선택 기능으로 기록합니다.

`verify.sh`는 준비가 끝난 저장소 전체를 임시 작업 디렉터리에서 검사합니다.

- 계획한 파일 구조와 구형 경로 부재
- Markdown 문서와 내부 링크
- 모든 예제와 기준 구현
- 모든 skeleton의 컴파일 성공과 동작 검사 실패
- 지원 환경의 sanitizer와 Readline 빌드
- 깨끗한 상태에서의 반복 빌드
- 검사 뒤 빌드 산출물 정리

전체 로그는 성공·실패와 관계없이 저장소 밖의 임시 디렉터리에 남고 마지막에 `VERIFY LOG` 경로가 출력됩니다. 다른 위치가 필요하면 저장소 밖의 절대 경로를 지정합니다.

```sh
VERIFY_LOG=/tmp/guide-c.log ./verify.sh
```

선택 기능까지 반드시 요구하려면 다음처럼 실행합니다.

```sh
VERIFY_REQUIRE_OPTIONAL=1 ./verify.sh
```

## 시작 위치

전체 학습 경로와 선택 경로는 [`docs/00-roadmap.md`](docs/00-roadmap.md)에서 확인합니다.

- 프로그래밍이 처음이면 `docs/01-foundations/`부터 시작합니다.
- 다른 언어로 작은 프로그램을 작성해 본 경험이 있으면 `docs/02-c-language/`부터 시작할 수 있습니다.
- 파일, 파이프, 프로세스와 시그널이 필요하면 `docs/03-unix-programming/`을 읽습니다.
- 공유 상태와 스레드를 다루려면 `docs/04-concurrency/`로 진행합니다.
- 디버거, Readline, Unix 텍스트 검사법은 `docs/90-appendix/`에서 필요할 때 찾아봅니다.

문서 전체를 먼저 읽은 뒤 실습을 몰아서 하지 않습니다. 아래 표의 한 행마다 관련 문서를 읽고, 이름이 있는 관찰 예제만 선택적으로 실행한 뒤, 해당 workspace를 구현·검증합니다. `number-report`는 첫 세 문서에서 수동 실행으로 조금씩 확장하고 네 번째 문서에서 전체 자동 검사를 통과시킵니다.

## 학습 순서

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 1 | [편집·컴파일·실행](docs/01-foundations/01-edit-compile-run.md) | — | [number-report](exercises/01-foundations/01-number-report/README.md) 시작 | `workspace/number_report.c` | 직접 컴파일하고 usage·종료 상태 확인 | 값·분기·반복으로 확장 |
| 2 | [값·분기·반복](docs/01-foundations/02-values-branches-loops.md) | — | number-report 누적·경계 상태 추가 | 같은 workspace | 정상·잘못된 입력을 직접 실행 | 함수로 책임 분리 |
| 3 | [함수·배열·텍스트](docs/01-foundations/03-functions-arrays-text.md) | — | number-report 함수 계약 분리 | 같은 workspace | 함수별 성공·실패 상태 직접 확인 | 입력 오류와 전체 검사 |
| 4 | [입력 오류와 디버깅](docs/01-foundations/04-input-errors-debugging.md) | — | number-report 완성 | 같은 workspace | `make exercise-test && make sanitize` | `reference/` 비교 후 Part 2 |
| 5 | [C 프로그램 모델](docs/02-c-language/01-c-program-model.md) | — | [textkit](exercises/02-c-language/01-textkit/README.md) | `workspace/src/textkit.c` | `make exercise-test && make sanitize` | `reference/` 비교 후 메모리 모델 |
| 6 | [메모리·포인터·문자열](docs/02-c-language/02-memory-pointers-strings.md) | — | [owned-string](exercises/02-c-language/02-owned-string/README.md) | `workspace/src/owned_string.c` | `make exercise-test && make sanitize` | `reference/` 비교 후 API 설계 |
| 7 | [자료구조와 API 계약](docs/02-c-language/03-data-structures-api-design.md) | — | [int-vector](exercises/02-c-language/03-int-vector/README.md) | `workspace/src/int_vector.c` | `make exercise-test && make sanitize` | `reference/` 비교 후 빌드 관찰 |
| 8 | [빌드·링크·테스트](docs/02-c-language/04-build-link-test.md) | — | textkit의 제공된 build graph 재관찰 | textkit workspace와 shared `Makefile` | `make exercise-build`, `ar t build/exercise/libtextkit.a` | 가변 인자 API로 진행 |
| 9 | [가변 인자와 포맷 API](docs/02-c-language/05-variadic-format-api.md) | — | [diagnostic-formatter](exercises/02-c-language/04-diagnostic-formatter/README.md) | `workspace/src/diagnostic_formatter.c` | `make exercise-test && make sanitize` | `reference/` 비교 후 Part 3 |
| 10 | [POSIX I/O와 스트림 상태](docs/03-unix-programming/01-posix-io-streams.md) | — | [record-stream](exercises/03-unix-programming/01-record-stream/README.md) | `workspace/src/record_stream.c` | `make exercise-test && make sanitize` | `reference/` 비교 후 프로세스 |
| 11 | [프로세스·FD·파이프](docs/03-unix-programming/02-process-fd-pipe.md) | [fd-redirection](examples/fd-redirection/README.md) | [command-pipeline](exercises/03-unix-programming/02-command-pipeline/README.md) | `workspace/src/command_pipeline.c` | `make exercise-test && make sanitize` | `reference/` 비교 후 시그널 |
| 12 | [시그널과 사건 전달](docs/03-unix-programming/03-signals-events.md) | — | [signal-loop](exercises/03-unix-programming/03-signal-loop/README.md) | `workspace/signal_loop.c` | `make exercise-test && make sanitize` | `reference/` 비교 후 셸 경계 |
| 13 | [셸 파서와 실행기](docs/03-unix-programming/04-shell-parser-executor.md) | 완료 뒤 [process-group-forwarding](examples/process-group-forwarding/README.md) | [command-runner](exercises/03-unix-programming/04-command-runner/README.md) | `workspace/command_runner.c` | `make exercise-test && make sanitize` | `reference/` 비교, 예제 관찰 후 Part 4 |
| 14 | [스레드·동기화·시간](docs/04-concurrency/01-threads-time.md) | — | [account-simulator](exercises/04-concurrency/01-account-simulator/README.md) | `workspace/src/account.c` | `make exercise-test && make sanitize`; 지원 시 `make thread-sanitize` | `reference/` 비교 후 필수 경로 종료 |

부록은 막힌 문제나 선택 기능이 있을 때 사용합니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 선택 A | [디버거 참고](docs/90-appendix/01-debugger-reference.md) | — | 현재 실패를 debugger로 재현 | 현재 workspace | 문서의 관찰 기록 | 필수 경로로 복귀 |
| 선택 B | [Readline 통합](docs/90-appendix/02-readline-integration.md) | [readline-repl](examples/readline-repl/README.md) | plain/Readline 입력 경계 비교 | 예제는 읽기 전용 | `make -C examples/readline-repl readline-check` | 필수 경로로 복귀 |
| 선택 C | [Unix 텍스트 검사](docs/90-appendix/03-unix-text-testing.md) | [text-checks](examples/text-checks/README.md) | 검사 도구별 evidence 비교 | 예제는 읽기 전용 | `make -C examples/text-checks check` | 필수 경로로 복귀 |

## 예제와 연습문제

`examples/`와 `exercises/`는 역할이 다릅니다.

- `examples/`는 한 개념의 완성된 동작을 작게 관찰하는 프로그램입니다.
- `exercises/`는 제공된 공개 계약과 테스트를 바탕으로 학습자가 직접 구현하는 과정입니다.

최종적으로 남긴 예제는 exercise 답안이 아니라 다음 네 개의 좁은 관찰 단위입니다.

- `fd-redirection`: 한 명령의 stdout FD 소유권과 truncate/append
- `process-group-forwarding`: 고정 argv 실행과 process-group signal 전달
- `readline-repl`: plain 입력과 선택적 Readline adapter
- `text-checks`: Unix 텍스트 도구로 evidence와 known-bad를 판별하는 검사

각 연습문제는 다음 구성을 기본으로 합니다.

```text
README.md       문제와 완료 조건
include/        바꾸지 않는 공개 계약
skeleton/       변경하지 않는 초기 실패 기준
workspace/      학습자가 구현할 코드(생성 뒤 Git 비추적)
reference/      검사와 비교를 위한 기준 구현
tests/          정상·경계·실패 계약 검사
Makefile        일관된 실행 명령
```

기준 구현 전체를 검사합니다.

```sh
make exercises-check
```

저장소 루트에서 연습문제별 workspace를 한 번만 만듭니다. 기존 workspace나 symlink가 있으면 덮어쓰지 않고 실패합니다.

```sh
scripts/new-workspace.sh exercises/02-c-language/02-owned-string
```

생성된 workspace를 구현한 뒤 해당 연습문제 디렉터리에서 검사합니다. 위 ordered mapping의 `make exercise-*`와 `make sanitize`도 같은 위치에서 실행합니다.

```sh
make -C exercises/02-c-language/02-owned-string exercise-test
```

`make exercise-test`와 `make sanitize`는 기본적으로 workspace를 검사합니다. 초기 skeleton은 공식 품질 검사에서 경고 없이 컴파일되어야 하지만 동작 검사는 실패해야 합니다. 구현을 완료한 뒤에만 `reference/README.md`의 권장 구현 순서와 source를 비교합니다.

workspace는 공식 `prepare.sh`, `make clean`, `verify.sh`가 삭제하거나 기준 source로 검사하지 않습니다. 따라서 학습 완료 상태와 canonical skeleton의 초기 실패 계약이 충돌하지 않습니다.

## 부분 검사

전체 검증보다 좁은 범위를 반복할 때는 Make target을 직접 사용할 수 있습니다.

```sh
make check
make quality-check
make sanitize
make thread-sanitize
make readline-check
make clean
```

- `make check`는 구조, 문서, 예제와 모든 기준 구현을 검사합니다.
- `make quality-check`는 기준 구현 통과, skeleton 빌드 성공과 초기 동작 실패를 확인합니다.
- sanitizer와 Readline target은 해당 기능을 제공하는 환경에서 사용합니다.
- 저장소를 전달하거나 커밋하기 전의 정본 검사는 항상 `./prepare.sh`와 `./verify.sh` 조합입니다.

## 기준과 범위

- 언어 기준: C99
- Unix API 기준: POSIX.1-2008
- 기본 도구: POSIX shell, `make`, C 컴파일러, Python 3.10 이상
- 주요 대상: Linux와 macOS의 명령행 환경

이 가이드는 C 표준 라이브러리와 POSIX를 이용한 단일 호스트 프로그램을 다룹니다. GUI, 임베디드 하드웨어, 커널 개발, 네트워크 프로토콜 구현과 분산 시스템은 별도 과정의 범위입니다.
