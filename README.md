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

실패한 전체 로그는 기본적으로 `verify.log`에 남습니다. 성공하면 기존 `verify.log`를 제거합니다. 선택 기능까지 반드시 요구하려면 다음처럼 실행합니다.

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

## 예제와 연습문제

`examples/`와 `exercises/`는 역할이 다릅니다.

- `examples/`는 한 개념의 완성된 동작을 작게 관찰하는 프로그램입니다.
- `exercises/`는 제공된 공개 계약과 테스트를 바탕으로 학습자가 직접 구현하는 과정입니다.

각 연습문제는 다음 구성을 기본으로 합니다.

```text
README.md       문제와 완료 조건
include/        바꾸지 않는 공개 계약
skeleton/       학습자가 구현할 코드
reference/      검사와 비교를 위한 기준 구현
tests/          정상·경계·실패 계약 검사
Makefile        일관된 실행 명령
```

기준 구현 전체를 검사합니다.

```sh
make exercises-check
```

개별 skeleton을 구현한 뒤 검사합니다.

```sh
make -C exercises/02-c-language/02-owned-string exercise-test
```

초기 skeleton은 경고 없이 컴파일되어야 하지만 동작 검사는 실패해야 합니다. 구현을 완료한 뒤에만 `reference/`와 설계 차이를 비교하는 것이 좋습니다.

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
