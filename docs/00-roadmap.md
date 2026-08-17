# 학습 로드맵

이 문서는 가이드의 범위와 학습 시작점, 완료 기준을 정의합니다. 모든 장을 처음부터 순서대로 읽는 것이 목표는 아닙니다. 만들려는 프로그램에 필요한 경로를 선택하고, 각 단계의 연습문제를 통해 구현·실행·검증을 반복합니다.

## 대상 독자

이 가이드는 다음 두 유형의 독자를 대상으로 합니다.

1. 프로그래밍을 처음 배우며 C로 작은 명령행 프로그램부터 만들려는 사람
2. 다른 언어를 사용해 본 경험은 있지만 C의 객체 수명, 포인터, 빌드 과정, POSIX 자원 모델을 체계적으로 배우려는 사람

두 번째 유형에 해당하고 1부의 종료 과제를 이미 수행할 수 있다면 바로 2부부터 시작해도 됩니다.

## 완료 후 할 수 있는 일

전체 과정을 마치면 다음 작업을 스스로 수행할 수 있어야 합니다.

- 문제를 입력, 출력, 오류, 상태 불변식으로 나눕니다.
- 빈 디렉터리에서 다중 파일 C 프로그램과 정적 라이브러리의 구조를 구성합니다.
- 포인터의 유효 범위와 객체 수명, 동적 메모리의 소유자를 추적합니다.
- 메모리 할당 실패와 부분 성공 이후의 상태 계약을 설계합니다.
- Makefile로 의존 관계를 표현하고 반복 검사를 자동화합니다.
- 파일 디스크립터, 파이프, 프로세스, 시그널을 자원 누수 없이 다룹니다.
- 뮤텍스와 단조 시계를 이용해 공유 상태와 종료 조건을 처리합니다.
- 컴파일러 경고, 디버거, Sanitizer, 자동 테스트로 실패를 재현하고 원인을 좁힙니다.

## 학습 과정

### 1부. 프로그래밍 기초

| 문서 | 핵심 질문 | 연습 |
|---|---|---|
| [편집·컴파일·실행](01-foundations/01-edit-compile-run.md) | 소스 코드가 어떤 과정을 거쳐 실행 파일이 되는가 | number-report 시작 |
| [값·분기·반복](01-foundations/02-values-branches-loops.md) | 여러 입력을 처리하며 상태와 결과를 어떻게 누적하는가 | number-report 누적 상태 확장 |
| [함수·배열·텍스트](01-foundations/03-functions-arrays-text.md) | 문제를 명확한 계약을 가진 작은 함수로 어떻게 나누는가 | number-report 함수 계약 분리 |
| [입력 오류와 디버깅](01-foundations/04-input-errors-debugging.md) | 잘못된 입력과 프로그램 결함을 어떻게 구분하는가 | [number-report](../exercises/01-foundations/01-number-report/README.md) |

1부의 완료 기준은 숫자 목록을 안전하게 읽고 통계를 출력하는 CLI를 직접 구현하는 것입니다.

### 2부. C 언어·메모리·API·빌드

| 문서 | 핵심 질문 | 연습 |
|---|---|---|
| [C 프로그램 모델](02-c-language/01-c-program-model.md) | 번역 단위가 링크 단계에서 어떻게 결합되는가 | [textkit](../exercises/02-c-language/01-textkit/README.md) |
| [메모리·포인터·문자열](02-c-language/02-memory-pointers-strings.md) | 주소는 언제까지 유효하며 메모리는 누가 해제하는가 | [owned-string](../exercises/02-c-language/02-owned-string/README.md) |
| [자료구조와 API 계약](02-c-language/03-data-structures-api-design.md) | 실패 이후의 상태와 소유권을 API에 어떻게 드러내는가 | [int-vector](../exercises/02-c-language/03-int-vector/README.md) |
| [빌드·링크·테스트](02-c-language/04-build-link-test.md) | 반복 가능한 빌드와 검증 환경을 어떻게 구성하는가 | textkit에 제공된 빌드 그래프 관찰 |
| [가변 인자와 포맷 API](02-c-language/05-variadic-format-api.md) | 타입 정보가 없는 인자를 어떻게 안전하게 소비하는가 | [diagnostic-formatter](../exercises/02-c-language/04-diagnostic-formatter/README.md) |

2부를 마치면 `printf` 계열의 소형 라이브러리나 자료구조 프로젝트를 시작할 수 있습니다.

### 3부. Unix 시스템 프로그래밍

| 문서 | 핵심 질문 | 연습 |
|---|---|---|
| [POSIX I/O와 스트림 상태](03-unix-programming/01-posix-io-streams.md) | 부분 읽기와 EOF를 처리하면서 스트림 상태를 어떻게 보존하는가 | [record-stream](../exercises/03-unix-programming/01-record-stream/README.md) |
| [프로세스·FD·파이프](03-unix-programming/02-process-fd-pipe.md) | `fork` 이후 각 프로세스가 어떤 파일 디스크립터를 닫아야 하는가 | [command-pipeline](../exercises/03-unix-programming/02-command-pipeline/README.md) |
| [시그널과 이벤트 전달](03-unix-programming/03-signals-events.md) | 비동기 시그널 핸들러와 일반 제어 흐름을 어떻게 분리하는가 | [signal-loop](../exercises/03-unix-programming/03-signal-loop/README.md) |
| [셸 파서와 실행기](03-unix-programming/04-shell-parser-executor.md) | 입력 문법 처리와 명령 실행의 책임을 어떻게 분리하는가 | [command-runner](../exercises/03-unix-programming/04-command-runner/README.md) |

3부를 마치면 파이프라인, 소형 셸, 프로세스 간 메시지 전달 프로그램과 같은 POSIX 프로젝트를 시작할 수 있습니다.

### 4부. 동시성

| 문서 | 핵심 질문 | 연습 |
|---|---|---|
| [스레드·동기화·시간](04-concurrency/01-threads-time.md) | 스레드 실행 순서가 어떻게 교차하더라도 공유 상태의 불변식과 종료 조건이 유지되는가 | [account-simulator](../exercises/04-concurrency/01-account-simulator/README.md) |

## 예제와 연습문제 사용법

먼저 문서에 설명된 문제와 계약을 읽습니다. [루트 README의 학습 순서](../README.md#학습-순서)에서 예제가 지정된 항목에 한해 작은 완성 예제를 선택적으로 살펴봅니다. 현재 제공하는 관찰용 예제는 FD 리다이렉션, 프로세스 그룹 포워딩, Readline 어댑터, Unix 텍스트 검사로 한정되며 연습문제의 답안을 대신하지 않습니다.

연습을 시작할 때는 저장소 루트에서 공식 스켈레톤을 학습자 작업 공간으로 복사합니다.

```sh
scripts/new-workspace.sh exercises/02-c-language/03-int-vector
```

기존 작업 공간은 덮어쓰지 않습니다. 학습자는 `workspace/`만 수정하고, `skeleton/`은 공식 초기 실패 검사를 위해 그대로 둡니다.

공식 스켈레톤은 다음 두 조건을 모두 만족해야 합니다.

1. `exercise-build`가 경고 없이 성공합니다.
2. 기능이 아직 구현되지 않았으므로 `exercise-test`는 실패합니다.

```sh
make -C exercises/02-c-language/03-int-vector exercise-build EXERCISE_IMPL=skeleton
make -C exercises/02-c-language/03-int-vector exercise-test EXERCISE_IMPL=skeleton
```

컴파일 오류는 올바른 초기 실패 상태가 아닙니다. 빌드 가능한 프로그램에서 동작 계약을 하나씩 완성해야 합니다.

작업 공간의 구현이 테스트를 통과하면 실패 사례를 직접 추가합니다. 마지막 단계에서만 `reference/README.md`의 권장 구현 순서와 소스 코드를 비교합니다. `make sanitize`도 참조 구현이 아니라 현재 작업 공간을 검사합니다.

```sh
make -C exercises/02-c-language/03-int-vector exercise-test
make -C exercises/02-c-language/03-int-vector sanitize
```

구현을 마친 뒤 참조 구현과 비교할 필요가 있을 때만 다음 명령을 실행합니다.

```sh
make -C exercises/02-c-language/03-int-vector reference-test
```

## 저장소 전체 검증

최종 상태를 검사할 때는 저장소 루트에서 다음 두 명령을 순서대로 실행합니다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 오래된 경로와 이전 빌드 산출물을 제거하고, 현재 환경에서 선택 기능을 사용할 수 있는지 확인합니다. `verify.sh`는 준비된 저장소를 임시 디렉터리에서 검사한 뒤 빌드 캐시와 실행 산출물을 정리합니다.

반복 작업 중에는 범위가 좁은 개별 Make 타깃을 사용할 수 있습니다. 다만 제출하거나 커밋하기 전의 최종 검증은 위 두 루트 스크립트를 기준으로 합니다.

## 필수 과정과 선택 과정

- 프로그래밍을 처음 배우는 경우 1부는 필수입니다.
- 2부의 1~4장은 모든 C 프로젝트의 공통 기반입니다.
- 가변 인자는 포맷 API를 구현할 때 학습합니다.
- 3부는 POSIX 파일·프로세스 기능을 사용하는 프로젝트에 필요합니다.
- 4부는 여러 스레드가 상태를 공유하는 프로그램에 필요합니다.
- [디버거](90-appendix/01-debugger-reference.md), [Readline](90-appendix/02-readline-integration.md), [Unix 텍스트 검사](90-appendix/03-unix-text-testing.md)는 문제를 진단할 때 참고합니다.

## 의도적으로 다루지 않는 내용

이 가이드는 다음 주제를 완전한 과정으로 다루지 않습니다.

- 자료구조·알고리즘 문제 풀이 전반
- GUI와 그래픽스
- 임베디드 레지스터와 인터럽트
- 커널 모듈과 디바이스 드라이버
- 네트워크 프로토콜과 서버 설계
- C11 원자 연산의 전체 메모리 모델
- 특정 IDE 사용법

범위를 명시하는 이유는 입문 과정이 관련 기술을 무제한으로 포함하지 않도록 하기 위해서입니다.

## 검증의 한계

컴파일러 경고가 없고 테스트가 통과하더라도 프로그램의 모든 동작이 증명되는 것은 아닙니다. 자동 검증 결과는 실제로 확인한 입력과 환경에 대한 근거일 뿐입니다. 다음 항목도 함께 기록해야 합니다.

- 사용한 컴파일러와 옵션
- 운영체제와 라이브러리 조건
- 실행한 정상·경계·실패 사례
- Sanitizer와 디버거 실행 결과
- 아직 검사하지 않은 경로와 보장하지 않는 범위
