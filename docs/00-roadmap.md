# C++ 학습 경로와 범위 계약

## 이 가이드가 해결하는 문제

C++을 배울 때 가장 흔한 실패는 서로 다른 시대와 목적의 규칙을 한 과정에 섞는 것입니다. Modern C++ 애플리케이션에서는 값 의미론, Rule of Zero, 표준 컨테이너, smart pointer와 `std::jthread`가 기본입니다. 반면 C++98 제약 아래 POSIX 서버를 구현할 때는 이동 의미론과 smart pointer 없이 복사·소유권·파일 디스크립터 수명을 직접 설계해야 합니다.

이 저장소는 두 목적을 하나의 문법 목록으로 합치지 않습니다.

```text
Modern C++ 일반 과정
    C++20 언어·표준 라이브러리·CMake·테스트
    → 일반 애플리케이션을 독립적으로 시작

C++98 시스템 과정
    객체 수명·STL·POSIX socket·event loop·HTTP
    → 제약된 표준에서 서버 프로젝트를 시작
```

두 트랙은 객체 수명, 책임, 실패와 검증이라는 공통 원리를 공유하지만 사용하는 도구와 기본 설계가 다릅니다.

## 대상 독자

### Modern C++ 일반 과정

다음 수준의 프로그래밍 경험을 전제로 합니다.

- 변수, 조건문, 반복문과 함수의 역할을 알고 있습니다.
- 터미널에서 파일을 만들고 명령을 실행할 수 있습니다.
- 컴파일 오류와 실행 결과가 다르다는 것을 알고 있습니다.
- C를 알 필요는 없지만, 작은 프로그램을 한 번 이상 작성해 본 경험이 필요합니다.

이 과정은 C++ 문법을 암기시키는 입문서가 아니라 다음 개발 루프를 독립적으로 돌리는 데 목적이 있습니다.

```text
빈 디렉터리
→ CMake target 구성
→ 값과 소유권 모델 작성
→ 테스트 실행
→ 실패 재현
→ debugger·sanitizer로 원인 확인
→ 계약 수정
```

### C++98 시스템 과정

다음 조건을 전제로 합니다.

- C 또는 다른 언어로 여러 파일 프로그램을 작성해 봤습니다.
- 포인터, 동적 메모리와 기본 자료구조를 알고 있습니다.
- Unix 계열 터미널과 Makefile을 사용할 수 있습니다.
- `-std=c++98` 제약을 의도적으로 받아들입니다.

## 지원 기준

### Modern C++

- 언어 기준: C++20
- 선택 비교: C++23의 `std::expected` 등
- 빌드 도구: CMake 3.20 이상
- 공식 preset generator: Ninja; 직접 configure에서는 설치된 generator 사용 가능
- 공식 실습: 표준 라이브러리만 사용
- 기준 compiler: GCC 또는 Clang
- 선택 검증: AddressSanitizer·UndefinedBehaviorSanitizer·ThreadSanitizer

C++23 기능은 과정의 필수 계약으로 삼지 않습니다. 사용할 수 있는 compiler에서는 비교 대상으로 소개하되, 모든 reference 구현은 C++20으로 빌드됩니다.

Sanitizer는 compiler 이름만 보고 지원을 가정하지 않습니다. `verify.sh`가 작은 compile·runtime probe를 통과시킨 뒤 실제 검사를 실행합니다. 지원되지 않는 환경에서는 `SKIP`을 기록하며, `required` 또는 strict mode에서는 이를 실패로 바꿀 수 있습니다.

### C++98 시스템 과정

- 언어 기준: C++98
- 빌드 도구: Make
- 네트워크 과정: POSIX socket API
- 주요 환경: Linux 또는 macOS

Windows에서는 Modern C++ 과정은 진행할 수 있지만 전체 루트 검증과 POSIX 네트워크 과정은 WSL 또는 별도 Unix 환경이 필요합니다.

## 권장 읽기 경로

### 일반 C++ 애플리케이션을 만들려는 경우

1. [프로그램·빌드·CMake](01-modern-cpp/01-program-build-cmake.md)
2. [값·수명·이동](01-modern-cpp/02-values-lifetimes-and-move.md)
3. [RAII·smart pointer·Rule of Zero](01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md)
4. [클래스·책임·다형성](01-modern-cpp/04-classes-responsibilities-and-polymorphism.md)
5. [오류·optional·variant·expected](01-modern-cpp/05-errors-optional-variant-and-expected.md)
6. [알고리즘·ranges·templates·concepts](01-modern-cpp/06-algorithms-ranges-templates-and-concepts.md)
7. [동시성·시간·filesystem](01-modern-cpp/07-concurrency-time-and-filesystem.md)
8. [테스트·디버깅·도구](01-modern-cpp/08-testing-debugging-and-tooling.md)
9. [로컬 작업 실행기 capstone](01-modern-cpp/09-application-capstone.md)

문서를 1번부터 끝까지 읽은 뒤 실습을 몰아서 시작하지 않습니다. 다만 문서 번호와 실습 번호가 1:1인 것도 아닙니다. 실제 순서는 아래 대응표처럼 01–02 뒤 첫 실습, 03 뒤 둘째 실습, 06 뒤 셋째 실습을 수행하고, 04–05에서 설계한 capstone은 07–09까지 읽은 뒤 구현합니다. 정본 skeleton을 직접 바꾸지 않고 `make workspace TRACK=modern`으로 만든 `.workspace/01-modern-cpp`에서 작업하며, reference source는 학습자 검증을 통과한 뒤 비교합니다.

### 42 C++98 객체·STL 과정을 진행하는 경우

[C++98 시스템 트랙 지도](02-cpp98-systems/00-roadmap.md)에서 01–07을 따릅니다.

### IRC 같은 비차단 서버를 구현하는 경우

C++98 트랙의 01–08을 따릅니다. IRC 명령과 RFC는 프로젝트 도메인 지식이므로 이 저장소가 대신 가르치지 않습니다. 이 가이드는 객체 수명, 컨테이너, 파일 디스크립터 소유권, 부분 입출력과 event loop를 시작할 기반을 제공합니다.

### HTTP 서버를 구현하는 경우

C++98 트랙 전체를 따릅니다. 증분 parser, route 결정, static file, CGI process와 nonblocking connection 상태를 통합합니다.

## 문서와 실습 대응

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---|---|---|---|---|---|---|
| M1 | 01 프로그램·빌드·CMake | — | workspace와 첫 실습의 target·공개 헤더 경계 확인 | `.workspace/01-modern-cpp/01-strong-types-and-cmake/` | `make modern-start-state` | M2에서 값 계약 뒤 구현 |
| M2 | 02 값·수명·이동 | — | `01-strong-types-and-cmake` | `.workspace/01-modern-cpp/01-strong-types-and-cmake/skeleton/` | `make modern-exercise-test MODERN_EXERCISE=01-strong-types-and-cmake` | 해당 `reference/` → M3 |
| M3 | 03 RAII·smart pointer | — | `02-unique-file` | `.workspace/01-modern-cpp/02-unique-file/skeleton/` | `make modern-exercise-test MODERN_EXERCISE=02-unique-file` | 해당 `reference/` → M4 |
| M4 | 04 클래스·책임 | — | capstone 상태 소유자·책임 경계 설계 | 학습 메모 | 문서 checklist | M5 |
| M5 | 05 오류 모델 | — | capstone 거부·예외·terminal 상태 설계 | 학습 메모 | 문서 checklist | M6 |
| M6 | 06 algorithms·ranges·concepts | — | `03-query-pipeline` | `.workspace/01-modern-cpp/03-query-pipeline/skeleton/` | `make modern-exercise-test MODERN_EXERCISE=03-query-pipeline` | 해당 `reference/` → M7 |
| M7 | 07 동시성·시간·filesystem | — | capstone queue·취소·journal 수명 설계 | 학습 메모 | 문서 checklist | M8 |
| M8 | 08 테스트·도구 | — | capstone deterministic test·실패 근거 설계 | 학습 메모 | 문서 checklist | M9 |
| M9 | 09 capstone | 완료 뒤 application driver | `04-local-job-runner` spec 01–04 | `.workspace/01-modern-cpp/04-local-job-runner/skeleton/` | `make modern-exercise-test MODERN_EXERCISE=04-local-job-runner` | 해당 `reference/` → Modern C++ 종료 |

실습 루트는 [`exercises/01-modern-cpp`](../exercises/01-modern-cpp/README.md)입니다.

## 준비와 전체 검증

새 checkout 또는 구조 변경 뒤 저장소 루트에서 준비합니다.

```sh
./prepare.sh
```

`prepare.sh`는 이동 전 구형 경로, 일회성 마이그레이션 파일, 이전 build 부산물과 실행 조건을 정리합니다. source 구현을 자동 수정하거나 전체 테스트를 실행하지 않습니다. 외부 C++·Python package 의존성은 없으며, 운영체제 도구가 빠졌을 때는 자동 설치하지 않고 필요한 항목을 보고합니다.

준비가 끝나면 정본 진입점 하나로 전체를 검사합니다.

```sh
./verify.sh
```

`verify.sh`는 임시 복사본에서 다음을 검사합니다.

- 최종 구조, 문서 공통 절, 상대 링크와 이동 전 경로 부재
- Modern skeleton 네 개가 crash가 아닌 공통 assertion으로 실패하는 출발점
- Modern Debug·Release reference와 CTest
- C++98 skeleton build, reference, 실패 주입, 반복 연결과 네트워크 부하 계약
- runtime probe를 통과한 ASan·UBSan과 ThreadSanitizer
- 사용 가능한 서로 다른 compiler의 기본 build matrix
- 검증기 자체가 crash와 임의의 non-zero를 거부하는지 확인하는 메타 검사
- cleanup 뒤 생성 산출물 부재와 원본 source snapshot·tracked Git 상태 불변

검증 환경에서 지원 여부를 엄격하게 요구할 수 있습니다.

```sh
VERIFY_SANITIZERS=required VERIFY_TSAN=required VERIFY_STRICT=1 ./verify.sh
```

수정 중인 영역만 빠르게 확인할 때는 다음 개별 target을 사용합니다.

```sh
make workspace TRACK=modern
make workspace TRACK=cpp98
make modern-skeleton-build
make modern-test
make modern-exercise-test MODERN_EXERCISE=01-strong-types-and-cmake
make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/01-procedural
make modern-release
make modern-sanitize
make modern-thread-sanitize
make cpp98-verify
```

`make modern-start-state`와 루트 검증은 배포된 canonical skeleton의 초기 실패를 검사합니다. `make modern-test`는 reference-only 검사입니다. `.workspace`의 학습자 구현은 `modern-exercise-test` 또는 `cpp98-exercise-test`로 검사합니다. 개별 target은 개발 피드백용이며 최종 저장소 완료 판정은 `./verify.sh`를 기준으로 합니다.

skeleton 테스트 실행 파일은 의도적으로 실패합니다. 출발점이 이미 정답이면 학습자가 구현할 계약이 없기 때문입니다. 반면 skeleton 자체는 컴파일되어야 하고, 실패는 exit code `1`과 공통 test failure 요약으로 끝나야 합니다. crash, timeout, loader 오류 또는 sanitizer abort를 올바른 출발점으로 인정하지 않습니다.

## 완료 후 할 수 있어야 하는 일

### Modern C++ 완료 기준

- CMake로 실행 파일·라이브러리·테스트 target을 구성합니다.
- 값, 비소유 view와 자원 소유자를 구분합니다.
- 복사·이동·수명과 예외 안전성을 설명합니다.
- `unique_ptr`, `shared_ptr`, `optional`, `variant`의 사용 조건을 구분합니다.
- algorithms·ranges·concepts로 제네릭 계약을 표현합니다.
- `jthread`, `stop_token`, mutex와 condition variable로 종료 가능한 작업기를 만듭니다.
- filesystem 실패와 시간 제한을 값 또는 예외 경계로 처리합니다.
- CTest, 지원되는 sanitizer와 debugger로 실패 근거를 남깁니다.

### C++98 시스템 완료 기준

- Rule of Three와 명시적 소유권으로 자원을 관리합니다.
- STL 컨테이너와 알고리즘을 복잡도·무효화 규칙에 따라 선택합니다.
- 비차단 socket, 부분 읽기·쓰기와 event loop 상태를 관리합니다.
- HTTP parser, router, connection과 CGI process의 책임을 분리합니다.

## 의도적으로 다루지 않는 범위

이 저장소는 다음의 전문 과정이 아닙니다.

- GUI framework와 graphics API
- 게임 엔진과 실시간 렌더링
- template metaprogramming의 고급 기법
- compiler 구현과 ABI 세부
- lock-free 자료구조 전체
- distributed system과 database 설계
- C++ package manager별 전체 사용법

프로젝트에서 필요해진 시점에 별도 전문 자료를 학습합니다. 이 가이드의 종료점은 모든 C++ 지식을 아는 상태가 아니라, 첫 일반 애플리케이션 또는 시스템 서버를 스스로 시작하고 실패를 검증할 수 있는 상태입니다.

## 경로 안정성에 대한 결정

현재 정본 경로는 트랙별로 하나만 유지합니다.

```text
docs/01-modern-cpp/       Modern C++ 문서
exercises/01-modern-cpp/  Modern C++ 실습
docs/02-cpp98-systems/    C++98 시스템 문서
exercises/02-cpp98-systems/ C++98 시스템 실습
docs/90-appendix/         두 트랙의 비교와 보충 자료
```

이동 전 평면 경로와 `reference/` 복사본은 남기지 않습니다. `prepare.sh`는 구형 경로만 존재하면 정본 위치로 이동하고, 구형·정본 경로가 같은 내용이면 중복을 제거합니다. 두 경로가 서로 다른 내용이면 사용자 변경을 임의로 버리지 않고 충돌로 중단합니다.

이 결정은 다음 원칙에 따릅니다.

- 학습 구조는 파일 트리에서 드러나야 합니다.
- 같은 정본을 두 경로에 복제하지 않습니다.
- 이동은 반복 가능하고 데이터 손실 없이 수행되어야 합니다.
- roadmap, 실습과 검증 target이 같은 경계를 가리켜야 합니다.
