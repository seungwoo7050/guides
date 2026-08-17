# C++ 학습 경로와 범위

## 이 가이드의 목적

C++을 학습할 때는 서로 다른 시대와 목적의 규칙을 한 과정에 섞지 않는 것이 중요합니다. 일반적인 Modern C++ 애플리케이션에서는 값 의미론, Rule of Zero, 표준 컨테이너, 스마트 포인터, `std::jthread`를 기본 도구로 사용합니다. 반면 C++98 제약에서 POSIX 서버를 구현할 때는 이동 의미론과 스마트 포인터 없이 복사, 소유권, 파일 디스크립터 수명을 직접 설계해야 합니다.

이 저장소는 두 목적을 하나의 문법 목록으로 합치지 않고 별도 트랙으로 구성합니다.

```text
Modern C++ 일반 트랙
    C++20 언어·표준 라이브러리·CMake·테스트
    → 일반 애플리케이션을 독립적으로 시작

C++98 시스템 트랙
    객체 수명·STL·POSIX 소켓·이벤트 루프·HTTP
    → 제한된 언어 표준으로 서버 프로젝트를 시작
```

두 트랙 모두 객체 수명, 책임 분리, 오류 처리, 검증을 다루지만 사용하는 도구와 기본 설계 원칙은 다릅니다.

## 대상 독자

### Modern C++ 일반 트랙

다음 수준의 프로그래밍 경험을 전제로 합니다.

- 변수, 조건문, 반복문, 함수의 역할을 이해합니다.
- 터미널에서 파일을 만들고 명령을 실행할 수 있습니다.
- 컴파일 오류와 실행 중 오류를 구분할 수 있습니다.
- C를 알 필요는 없지만 작은 프로그램을 한 번 이상 작성해 본 경험이 필요합니다.

이 트랙의 목표는 C++ 문법 암기가 아니라 다음 개발 과정을 독립적으로 수행하는 것입니다.

```text
빈 디렉터리
→ CMake 타깃 구성
→ 값과 소유권 모델 작성
→ 테스트 실행
→ 실패 재현
→ 디버거·Sanitizer로 원인 확인
→ 설계와 요구사항 수정
```

### C++98 시스템 트랙

다음 조건을 전제로 합니다.

- C 또는 다른 언어로 여러 파일로 구성된 프로그램을 작성해 봤습니다.
- 포인터, 동적 메모리, 기본 자료구조를 이해합니다.
- Unix 계열 터미널과 Makefile을 사용할 수 있습니다.
- `-std=c++98` 제약을 의도적으로 적용합니다.

## 지원 기준

### Modern C++

- 언어 표준: C++20
- 선택 비교 항목: C++23의 `std::expected` 등
- 빌드 도구: CMake 3.20 이상
- 공식 프리셋 생성기: Ninja. 직접 구성할 때는 설치된 생성기를 사용할 수 있습니다.
- 공식 실습 의존성: C++ 표준 라이브러리
- 기준 컴파일러: GCC 또는 Clang
- 선택 검증 도구: AddressSanitizer, UndefinedBehaviorSanitizer, ThreadSanitizer

C++23 기능은 필수 요구사항이 아닙니다. 지원하는 컴파일러에서는 비교 대상으로 소개하지만 모든 참조 구현은 C++20으로 빌드됩니다.

Sanitizer 지원 여부는 컴파일러 이름만으로 판단하지 않습니다. `verify.sh`가 작은 컴파일·실행 검사를 통과한 기능만 실제 검증에 사용합니다. 지원하지 않는 환경에서는 `SKIP`으로 기록하며, `required` 또는 엄격 모드에서는 이를 실패로 처리할 수 있습니다.

### C++98 시스템

- 언어 표준: C++98
- 빌드 도구: Make
- 네트워크 API: POSIX 소켓 API
- 주요 실행 환경: Linux 또는 macOS

Windows에서도 Modern C++ 트랙은 진행할 수 있습니다. 다만 저장소 전체 검증과 POSIX 네트워크 실습에는 WSL 또는 별도의 Unix 계열 환경이 필요합니다.

## 권장 학습 경로

### 일반 C++ 애플리케이션을 만드는 경우

1. [프로그램·빌드·CMake](01-modern-cpp/01-program-build-cmake.md)
2. [값·수명·이동](01-modern-cpp/02-values-lifetimes-and-move.md)
3. [RAII·스마트 포인터·Rule of Zero](01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md)
4. [클래스·책임·다형성](01-modern-cpp/04-classes-responsibilities-and-polymorphism.md)
5. [오류·optional·variant·expected](01-modern-cpp/05-errors-optional-variant-and-expected.md)
6. [알고리즘·ranges·templates·concepts](01-modern-cpp/06-algorithms-ranges-templates-and-concepts.md)
7. [동시성·시간·파일 시스템](01-modern-cpp/07-concurrency-time-and-filesystem.md)
8. [테스트·디버깅·도구](01-modern-cpp/08-testing-debugging-and-tooling.md)
9. [로컬 작업 실행기 종합 실습](01-modern-cpp/09-application-capstone.md)

문서를 모두 읽은 뒤 실습을 한꺼번에 시작하지 않습니다. 문서 번호와 실습 번호도 일대일로 대응하지 않습니다. 아래 표의 순서대로 01–02 문서 뒤 첫 번째 실습, 03 문서 뒤 두 번째 실습, 06 문서 뒤 세 번째 실습을 진행합니다. 04–05 문서에서 설계한 종합 실습은 07–09 문서까지 학습한 뒤 구현합니다.

배포된 `skeleton/`을 직접 수정하지 않습니다. `make workspace TRACK=modern`으로 생성한 `.workspace/01-modern-cpp`에서 작업하고, 학습자 구현이 검증을 통과한 뒤 `reference/`와 비교합니다.

### 42 C++98 객체·STL 과정을 진행하는 경우

[C++98 시스템 트랙 로드맵](02-cpp98-systems/00-roadmap.md)의 01–07 문서를 따릅니다.

### IRC와 같은 논블로킹 서버를 구현하는 경우

C++98 트랙의 01–08 문서를 따릅니다. IRC 명령과 RFC는 프로젝트 도메인 지식이므로 이 저장소에서 다루지 않습니다. 이 가이드는 객체 수명, 컨테이너, 파일 디스크립터 소유권, 부분 입출력, 이벤트 루프를 설계하는 데 필요한 기반을 제공합니다.

### HTTP 서버를 구현하는 경우

C++98 트랙 전체를 따릅니다. 증분 파서, 라우팅, 정적 파일, CGI 프로세스, 논블로킹 연결 상태를 하나의 서버로 통합합니다.

## 문서와 실습 대응표

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 후 비교·다음 단계 |
|---|---|---|---|---|---|---|
| M1 | 01 프로그램·빌드·CMake | — | 워크스페이스와 첫 실습의 타깃·공개 헤더 경계 확인 | `.workspace/01-modern-cpp/01-strong-types-and-cmake/` | `make modern-start-state` | M2에서 값 계약을 학습한 뒤 구현 |
| M2 | 02 값·수명·이동 | — | `01-strong-types-and-cmake` | `.workspace/01-modern-cpp/01-strong-types-and-cmake/skeleton/` | `make modern-exercise-test MODERN_EXERCISE=01-strong-types-and-cmake` | 해당 `reference/`와 비교 → M3 |
| M3 | 03 RAII·스마트 포인터 | — | `02-unique-file` | `.workspace/01-modern-cpp/02-unique-file/skeleton/` | `make modern-exercise-test MODERN_EXERCISE=02-unique-file` | 해당 `reference/`와 비교 → M4 |
| M4 | 04 클래스·책임 | — | 종합 실습의 상태 소유자와 책임 경계 설계 | 학습 메모 | 문서 체크리스트 | M5 |
| M5 | 05 오류 모델 | — | 종합 실습의 제출 거부·예외·종료 상태 설계 | 학습 메모 | 문서 체크리스트 | M6 |
| M6 | 06 알고리즘·ranges·concepts | — | `03-query-pipeline` | `.workspace/01-modern-cpp/03-query-pipeline/skeleton/` | `make modern-exercise-test MODERN_EXERCISE=03-query-pipeline` | 해당 `reference/`와 비교 → M7 |
| M7 | 07 동시성·시간·파일 시스템 | — | 종합 실습의 큐·취소·저널 수명 설계 | 학습 메모 | 문서 체크리스트 | M8 |
| M8 | 08 테스트·도구 | — | 종합 실습의 결정적 테스트와 실패 근거 설계 | 학습 메모 | 문서 체크리스트 | M9 |
| M9 | 09 종합 실습 | 완료 후 애플리케이션 드라이버 확인 | `04-local-job-runner` 명세 01–04 | `.workspace/01-modern-cpp/04-local-job-runner/skeleton/` | `make modern-exercise-test MODERN_EXERCISE=04-local-job-runner` | 해당 `reference/`와 비교 → Modern C++ 트랙 완료 |

실습 진입점은 [`exercises/01-modern-cpp`](../exercises/01-modern-cpp/README.md)입니다.

## 준비와 전체 검증

새로 체크아웃했거나 디렉터리 구조를 변경했다면 저장소 루트에서 다음 명령을 실행합니다.

```sh
./prepare.sh
```

`prepare.sh`는 이전 경로, 일회성 마이그레이션 파일, 기존 빌드 산출물, 실행 권한을 정리합니다. 소스 구현을 자동으로 수정하거나 전체 테스트를 실행하지는 않습니다. 외부 C++·Python 패키지 의존성은 없으며, 운영체제 도구가 누락되어도 자동으로 설치하지 않고 필요한 항목만 보고합니다.

준비가 끝나면 다음 명령으로 저장소 전체를 검사합니다.

```sh
./verify.sh
```

`verify.sh`는 임시 복사본에서 다음 항목을 검사합니다.

- 최종 디렉터리 구조, 문서 공통 절, 상대 링크, 이전 경로의 잔존 여부
- Modern C++ 스켈레톤 네 개가 충돌이 아닌 공통 assertion 실패로 시작하는지 여부
- Modern C++ 참조 구현의 Debug·Release 빌드와 CTest
- C++98 스켈레톤 빌드, 참조 구현, 실패 주입, 반복 연결, 네트워크 부하 요구사항
- 실행 검사를 통과한 ASan·UBSan·ThreadSanitizer
- 사용 가능한 서로 다른 컴파일러로 구성한 기본 빌드 매트릭스
- 검증기 자체가 충돌이나 임의의 0이 아닌 종료 코드를 올바른 실패로 오인하지 않는지 확인하는 메타 검사
- 정리 후 생성 산출물이 남지 않는지, 원본 소스 스냅샷과 추적 중인 Git 상태가 바뀌지 않는지 여부

검증 환경에서 선택 기능의 지원 여부까지 필수로 요구하려면 다음과 같이 실행합니다.

```sh
VERIFY_SANITIZERS=required VERIFY_TSAN=required VERIFY_STRICT=1 ./verify.sh
```

수정 중인 영역만 빠르게 확인할 때는 다음 개별 타깃을 사용합니다.

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

`make modern-start-state`와 저장소 전체 검증은 배포된 기준 스켈레톤의 초기 실패 상태를 검사합니다. `make modern-test`는 참조 구현만 검사합니다. `.workspace`에 작성한 학습자 구현은 `modern-exercise-test` 또는 `cpp98-exercise-test`로 검사합니다. 개별 타깃은 개발 중 빠른 피드백을 위한 것이며, 최종 완료 여부는 `./verify.sh` 결과로 판단합니다.

스켈레톤 테스트 실행 파일은 의도적으로 실패합니다. 시작점이 이미 정답이면 학습자가 구현할 내용이 없기 때문입니다. 단, 스켈레톤 자체는 컴파일되어야 하며 테스트 실패는 종료 코드 `1`과 공통 실패 요약으로 끝나야 합니다. 충돌, 시간 초과, 로더 오류, Sanitizer 중단은 정상적인 초기 실패로 인정하지 않습니다.

## 완료 기준

### Modern C++

- CMake로 실행 파일·라이브러리·테스트 타깃을 구성합니다.
- 값, 비소유 뷰, 자원 소유자를 구분합니다.
- 복사·이동·수명·예외 안전성을 설명합니다.
- `unique_ptr`, `shared_ptr`, `optional`, `variant`의 사용 조건을 구분합니다.
- 알고리즘·ranges·concepts로 제네릭 코드의 요구사항을 표현합니다.
- `jthread`, `stop_token`, 뮤텍스, 조건 변수로 안전하게 종료할 수 있는 작업 실행기를 구현합니다.
- 파일 시스템 오류와 시간 제한을 값 또는 예외 경계에서 처리합니다.
- CTest, 지원되는 Sanitizer, 디버거를 사용해 실패 원인을 재현하고 기록합니다.

### C++98 시스템

- Rule of Three와 명시적 소유권으로 자원을 관리합니다.
- 복잡도와 무효화 규칙을 고려해 STL 컨테이너와 알고리즘을 선택합니다.
- 논블로킹 소켓, 부분 읽기·쓰기, 이벤트 루프 상태를 관리합니다.
- HTTP 파서, 라우터, 연결 객체, CGI 프로세스의 책임을 분리합니다.

## 다루지 않는 범위

이 저장소는 다음 분야의 전문 과정이 아닙니다.

- GUI 프레임워크와 그래픽스 API
- 게임 엔진과 실시간 렌더링
- 고급 템플릿 메타프로그래밍
- 컴파일러 구현과 ABI 세부 사항
- lock-free 자료구조 전반
- 분산 시스템과 데이터베이스 설계
- C++ 패키지 관리자별 전체 사용법

이러한 주제는 프로젝트에서 필요해진 시점에 별도 자료로 학습합니다. 이 가이드의 목표는 C++ 전반을 모두 익히는 것이 아니라, 일반 애플리케이션 또는 시스템 서버를 스스로 시작하고 실패를 검증할 수 있는 수준에 도달하는 것입니다.

## 경로 안정성

트랙별 기준 경로는 하나만 유지합니다.

```text
docs/01-modern-cpp/         Modern C++ 문서
exercises/01-modern-cpp/    Modern C++ 실습
docs/02-cpp98-systems/      C++98 시스템 문서
exercises/02-cpp98-systems/ C++98 시스템 실습
docs/90-appendix/           두 트랙의 비교와 보충 자료
```

이전의 평면 경로와 중복된 `reference/` 복사본은 유지하지 않습니다. `prepare.sh`는 이전 경로만 존재하면 기준 위치로 이동하고, 이전 경로와 기준 경로의 내용이 같으면 중복을 제거합니다. 두 경로의 내용이 다르면 사용자 변경 사항을 임의로 버리지 않고 충돌을 보고한 뒤 중단합니다.

이 결정은 다음 원칙에 따릅니다.

- 학습 구조가 파일 트리에서 드러나야 합니다.
- 같은 기준 파일을 여러 경로에 복제하지 않습니다.
- 경로 이동은 반복 실행해도 안전하고 데이터 손실이 없어야 합니다.
- 로드맵, 실습, 검증 타깃이 같은 경로를 가리켜야 합니다.
