# 학습 로드맵

이 문서는 가이드의 범위, 시작 위치와 완료 기준을 정의합니다. 처음부터 모든 장을 읽는 것이 목표가 아닙니다. 만들려는 프로그램에 필요한 경로를 선택하고, 각 단계의 연습문제로 구현·실행·검증 순환을 반복합니다.

## 대상 독자

다음 두 종류의 독자를 모두 지원합니다.

1. 프로그래밍을 처음 시작하며 C로 작은 명령행 프로그램부터 만들려는 사람
2. 다른 언어 경험은 있지만 C의 수명, 포인터, 빌드와 POSIX 자원 모델을 체계적으로 배우려는 사람

두 번째 독자는 Part 1의 종료 과제를 먼저 읽고 이미 수행할 수 있다면 Part 2로 이동해도 됩니다.

## 완료 후 가능한 일

전체 과정을 마치면 다음을 스스로 수행할 수 있어야 합니다.

- 문제를 입력·출력·오류·상태 불변식으로 나눕니다.
- 빈 디렉터리에서 다중 파일 C 프로그램과 정적 라이브러리를 구성합니다.
- 포인터의 유효 범위, 객체 수명과 동적 메모리 소유자를 추적합니다.
- 할당 실패와 부분 성공 뒤의 상태 계약을 설계합니다.
- Makefile로 의존 관계와 반복 검사를 자동화합니다.
- 파일 디스크립터, 파이프, 프로세스와 시그널을 정리 누락 없이 사용합니다.
- mutex와 단조 시계를 이용해 공유 상태와 종료 조건을 다룹니다.
- 경고, 디버거, sanitizer와 자동 테스트로 실패를 재현하고 원인을 좁힙니다.

## 학습 과정

### Part 1. 프로그래밍 기초

| 문서 | 핵심 질문 | 연습 |
|---|---|---|
| [편집·컴파일·실행](01-foundations/01-edit-compile-run.md) | 소스가 어떻게 실행 결과가 되는가 | number-report 시작 |
| [값·분기·반복](01-foundations/02-values-branches-loops.md) | 여러 입력에서 결과를 누적하는가 | number-report 누적 상태 확장 |
| [함수·배열·텍스트](01-foundations/03-functions-arrays-text.md) | 문제를 계약이 작은 함수로 나누는가 | number-report 함수 계약 분리 |
| [입력 오류와 디버깅](01-foundations/04-input-errors-debugging.md) | 잘못된 입력과 코드 결함을 구분하는가 | [number-report](../exercises/01-foundations/01-number-report/README.md) |

Part 1의 종료 조건은 숫자 목록을 안전하게 읽고 통계를 출력하는 CLI를 직접 구현하는 것입니다.

### Part 2. C 언어·메모리·API·빌드

| 문서 | 핵심 질문 | 연습 |
|---|---|---|
| [C 프로그램 모델](02-c-language/01-c-program-model.md) | 번역 단위와 링크는 어떻게 연결되는가 | [textkit](../exercises/02-c-language/01-textkit/README.md) |
| [메모리·포인터·문자열](02-c-language/02-memory-pointers-strings.md) | 주소가 언제 유효하며 누가 해제하는가 | [owned-string](../exercises/02-c-language/02-owned-string/README.md) |
| [자료구조와 API 계약](02-c-language/03-data-structures-api-design.md) | 실패 뒤 상태와 소유권을 어떻게 공개하는가 | [int-vector](../exercises/02-c-language/03-int-vector/README.md) |
| [빌드·링크·테스트](02-c-language/04-build-link-test.md) | 반복 가능한 빌드와 검증을 어떻게 만드는가 | textkit의 제공된 build graph 관찰 |
| [가변 인자와 포맷 API](02-c-language/05-variadic-format-api.md) | 타입 정보가 없는 인자를 안전하게 소비하는가 | [diagnostic-formatter](../exercises/02-c-language/04-diagnostic-formatter/README.md) |

Part 2를 마치면 `printf` 계열의 작은 라이브러리나 자료구조 프로젝트를 시작할 수 있습니다.

### Part 3. Unix 시스템 프로그래밍

| 문서 | 핵심 질문 | 연습 |
|---|---|---|
| [POSIX I/O와 스트림 상태](03-unix-programming/01-posix-io-streams.md) | 부분 읽기와 EOF 사이에서 상태를 보존하는가 | [record-stream](../exercises/03-unix-programming/01-record-stream/README.md) |
| [프로세스·FD·파이프](03-unix-programming/02-process-fd-pipe.md) | fork 뒤 각 프로세스가 무엇을 닫아야 하는가 | [command-pipeline](../exercises/03-unix-programming/02-command-pipeline/README.md) |
| [시그널과 사건 전달](03-unix-programming/03-signals-events.md) | 비동기 handler와 일반 제어 흐름을 분리하는가 | [signal-loop](../exercises/03-unix-programming/03-signal-loop/README.md) |
| [셸 파서와 실행기](03-unix-programming/04-shell-parser-executor.md) | 입력 문법과 실행 책임을 분리하는가 | [command-runner](../exercises/03-unix-programming/04-command-runner/README.md) |

Part 3을 마치면 파이프라인, 작은 셸과 메시지 전달 프로그램 같은 POSIX 프로젝트를 시작할 수 있습니다.

### Part 4. 동시성

| 문서 | 핵심 질문 | 연습 |
|---|---|---|
| [스레드·동기화·시간](04-concurrency/01-threads-time.md) | 공유 불변식과 종료가 모든 interleaving에서 유지되는가 | [account-simulator](../exercises/04-concurrency/01-account-simulator/README.md) |

## 예제와 연습문제 사용법

먼저 문서의 문제와 계약을 읽습니다. [root README의 ordered mapping](../README.md#학습-순서)에 예제가 지정된 행에서만 작은 완성 동작을 선택적으로 관찰합니다. 현재 관찰 예제는 FD 리다이렉션, process-group forwarding, Readline adapter와 Unix 텍스트 검사로 좁혀져 있으며 exercise 답안을 대신하지 않습니다.

연습을 시작할 때는 저장소 루트에서 canonical skeleton을 learner-owned workspace로 복사합니다.

```sh
scripts/new-workspace.sh exercises/02-c-language/03-int-vector
```

기존 workspace는 덮어쓰지 않습니다. 학습자는 `workspace/`만 수정하며 `skeleton/`은 공식 초기 실패 검사를 위해 그대로 둡니다.

canonical skeleton은 다음 두 계약을 모두 만족해야 합니다.

1. `exercise-build`가 경고 없이 성공합니다.
2. 아직 구현되지 않았으므로 `exercise-test`는 실패합니다.

```sh
make -C exercises/02-c-language/03-int-vector exercise-build EXERCISE_IMPL=skeleton
make -C exercises/02-c-language/03-int-vector exercise-test EXERCISE_IMPL=skeleton
```

컴파일 오류는 올바른 초기 실패가 아닙니다. 학습자는 빌드 가능한 프로그램에서 동작 계약을 하나씩 완성해야 합니다.

workspace 구현이 통과하면 스스로 failure case를 추가하고, 마지막에만 `reference/README.md`의 권장 구현 순서와 source를 비교합니다. `make sanitize`도 reference가 아니라 현재 workspace를 검사합니다.

```sh
make -C exercises/02-c-language/03-int-vector exercise-test
make -C exercises/02-c-language/03-int-vector sanitize
```

완료 뒤 비교가 필요할 때만 다음을 실행합니다.

```sh
make -C exercises/02-c-language/03-int-vector reference-test
```

## 저장소 전체 검증

최종 저장소를 검사할 때는 루트에서 다음 두 명령을 순서대로 실행합니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 구형 경로와 이전 산출물을 제거하고 현재 환경의 선택 기능을 probe합니다. `verify.sh`는 준비된 저장소를 임시 디렉터리에서 검사하고, 끝나면 빌드 캐시와 실행 산출물을 제거합니다.

좁은 범위를 반복할 때는 개별 Make target을 사용할 수 있지만 전달·커밋 전 정본 검사는 두 루트 스크립트를 기준으로 합니다.

## 필수와 선택의 구분

- Part 1은 프로그래밍이 처음인 경우 필수입니다.
- Part 2의 1~4장은 모든 C 프로젝트의 공통 기반입니다.
- 가변 인자는 포맷 API를 만들 때 읽습니다.
- Part 3은 POSIX 파일·프로세스 프로젝트에 필요합니다.
- Part 4는 여러 스레드가 상태를 공유할 때 필요합니다.
- [디버거](90-appendix/01-debugger-reference.md), [Readline](90-appendix/02-readline-integration.md), [Unix 텍스트 검사](90-appendix/03-unix-text-testing.md)는 막힌 문제를 진단할 때 찾아봅니다.

## 의도적으로 다루지 않는 것

이 가이드는 다음을 완전한 과정으로 다루지 않습니다.

- 자료구조·알고리즘 문제 풀이 전체
- GUI와 그래픽스
- 임베디드 레지스터·인터럽트
- 커널 모듈과 디바이스 드라이버
- 네트워크 프로토콜과 서버 설계
- C11 원자 연산의 전체 메모리 모델
- 특정 IDE 사용법

이 범위를 명시하는 이유는 입문 과정이 관련 기술을 무한히 흡수하지 않도록 하기 위해서입니다.

## 검증의 한계

경고와 테스트가 통과했다고 프로그램의 모든 동작이 증명되는 것은 아닙니다. 자동 검증은 확인한 입력과 환경에 대한 근거입니다. 다음을 함께 기록해야 합니다.

- 사용한 컴파일러와 옵션
- 운영체제와 라이브러리 조건
- 실행한 정상·경계·실패 사례
- sanitizer와 디버거 결과
- 아직 검사하지 않은 경로와 비보장 범위
