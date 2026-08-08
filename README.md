# C++ 개발 가이드

이 저장소는 목적과 언어 제약이 다른 C++ 학습을 두 트랙으로 분리합니다.

```text
Modern C++ 일반 과정
    C++20 · CMake · 값 의미론 · RAII · ranges · 동시성 · 테스트
    → 일반 애플리케이션을 빈 디렉터리에서 시작

C++98 시스템 과정
    객체 수명 · Rule of Three · STL · POSIX socket · event loop · HTTP
    → 제한된 표준에서 서버 프로젝트를 시작
```

두 트랙은 객체 수명, 책임, 실패 조건과 검증을 공통 기준으로 사용합니다. 다만 Modern C++의 기본 설계를 C++98에 억지로 흉내 내거나, C++98의 직접 자원 관리 방식을 현대 애플리케이션의 기본값으로 제시하지 않습니다.

대상 독자, 선행지식, 지원 환경과 경로 선택은 [C++ 학습 경로와 범위 계약](docs/00-roadmap.md)에서 확인합니다.

## Modern C++ 일반 과정

C++20을 기준으로 다음 순서로 진행합니다.

1. [프로그램·빌드·CMake](docs/01-modern-cpp/01-program-build-cmake.md)
2. [값·수명·복사·이동](docs/01-modern-cpp/02-values-lifetimes-and-move.md)
3. [RAII·smart pointer·Rule of Zero](docs/01-modern-cpp/03-raii-smart-pointers-and-rule-of-zero.md)
4. [클래스·책임·다형성](docs/01-modern-cpp/04-classes-responsibilities-and-polymorphism.md)
5. [오류·optional·variant·expected](docs/01-modern-cpp/05-errors-optional-variant-and-expected.md)
6. [알고리즘·ranges·templates·concepts](docs/01-modern-cpp/06-algorithms-ranges-templates-and-concepts.md)
7. [동시성·시간·filesystem](docs/01-modern-cpp/07-concurrency-time-and-filesystem.md)
8. [테스트·디버깅·도구](docs/01-modern-cpp/08-testing-debugging-and-tooling.md)
9. [로컬 작업 실행기 capstone](docs/01-modern-cpp/09-application-capstone.md)

실습은 [Modern C++ 실습 경로](exercises/01-modern-cpp/README.md)에 있습니다.

```text
강한 타입과 target 기반 CMake
→ 이동 전용 파일 소유자
→ ranges 기반 조회 파이프라인
→ 종료 가능한 로컬 작업 실행기
```

각 실습은 `skeleton`, `reference`, 공통 계약 테스트와 CMake target을 제공합니다. 먼저 skeleton을 직접 완성하고 같은 테스트를 통과한 뒤 reference와 설계 차이를 비교합니다.

## C++98 시스템 과정

C++98 제약이 있는 객체·STL·네트워크 프로젝트는 [C++98 시스템 프로그래밍 트랙](docs/02-cpp98-systems/00-roadmap.md)을 따릅니다.

```text
객체 모델과 책임
→ 템플릿·반복자·STL
→ POSIX socket과 event loop
→ 객체지향 HTTP 서버
```

Modern C++을 먼저 학습했다면 [Modern C++에서 C++98로 이동할 때의 대응표](docs/90-appendix/01-modern-to-cpp98-crosswalk.md)를 함께 사용합니다.

## 처음 준비하기

저장소 루트에서 한 번 실행합니다.

```sh
./prepare.sh
```

`prepare.sh`는 다음 작업만 담당합니다.

- 이동 전 구형 경로를 현재 트랙 구조로 안전하게 정리
- 일회성 마이그레이션 파일과 이전 빌드 부산물 제거
- 루트·실습 스크립트의 실행 권한 정리
- C++20, C++98 POSIX, CMake와 Python 실행 조건 확인
- 저장소 관리 의존성 준비

이 저장소는 외부 C++ package나 Python package를 사용하지 않으므로 자동 설치할 프로젝트 의존성은 없습니다. compiler, Make, CMake와 Python 같은 운영체제 도구가 없으면 `prepare.sh`가 필요한 항목과 설치 예시를 출력한 뒤 중단합니다. 시스템 패키지를 임의로 설치하지 않습니다.

`prepare.sh`는 반복 실행할 수 있습니다. 이동 전·후 경로가 서로 다른 내용으로 함께 존재하면 사용자 파일을 삭제하지 않고 충돌을 보고합니다.

## 전체 검증

준비가 끝난 저장소 루트에서 실행합니다.

```sh
./verify.sh
```

`verify.sh`는 원본 작업 트리에서 직접 빌드하지 않습니다. 임시 복사본에서 다음을 한 번에 검사하고 성공·실패·중단 뒤 생성 산출물을 제거합니다.

- 최종 디렉터리 구조, 문서 공통 절과 상대 링크
- Modern C++ skeleton의 정상적인 초기 계약 실패
- Modern C++ Debug·Release reference와 CTest
- C++98 skeleton build, reference, 실패 주입, 반복 연결과 네트워크 부하 검사
- 지원되는 환경의 ASan·UBSan과 ThreadSanitizer
- 사용 가능한 두 번째 compiler의 기본 build matrix
- 검증기 자체의 거짓 성공 방지 메타 검사
- 검증 전후 원본 source snapshot과 tracked Git 상태 동일성

기본 로그는 저장소 밖의 임시 디렉터리에 남고 마지막에 경로가 출력됩니다. 다른 위치가 필요하면 지정할 수 있습니다.

```sh
VERIFY_LOG=/tmp/guide-cpp.log ./verify.sh
```

환경에 따라 선택 검사의 정책을 바꿀 수 있습니다.

```sh
VERIFY_SANITIZERS=required ./verify.sh   # ASan·UBSan 미지원도 실패
VERIFY_TSAN=required ./verify.sh         # TSan 미지원도 실패
VERIFY_COMPILER_MATRIX=off ./verify.sh   # 현재 CXX 하나만 검사
VERIFY_STRICT=1 ./verify.sh              # 건너뛴 검사가 있으면 실패
CXX=clang++ ./verify.sh                  # 기준 compiler 선택
```

`auto`가 기본값인 sanitizer와 compiler matrix는 실제 compiler·runtime probe를 통과한 경우에만 실행됩니다. 환경 미지원은 명시적인 `SKIP`으로 남고, 실행된 검사의 실패는 항상 전체 실패로 반영됩니다.

## 개별 개발 명령

전체 검증과 별도로 수정 중인 영역만 빠르게 실행할 수 있습니다.

```sh
make check
make modern-start-state
make modern-test
make modern-release
make modern-sanitize
make modern-thread-sanitize
make cpp98-verify
make clean
```

개별 target은 개발 피드백을 줄이기 위한 도구이고, 최종 완료 판정은 `./verify.sh`를 기준으로 합니다. 컴파일러와 운영체제 차이는 [컴파일러와 플랫폼 노트](docs/90-appendix/02-compiler-platform-notes.md)를 확인합니다.

## 실습 원칙

- 정상 경로뿐 아니라 실패 뒤 상태를 검사합니다.
- 자원의 소유자와 종료 순서를 타입과 문서에 드러냅니다.
- 미완성 skeleton은 컴파일되지만 공통 계약 테스트에는 정상적인 assertion 실패로 끝나야 합니다.
- reference는 답안을 복사하기 위한 시작점이 아니라 자신의 구현과 비교하는 정본입니다.
- 성능·안전성 주장은 재현 가능한 명령과 관찰 근거가 있을 때만 기록합니다.

이 가이드의 종료점은 C++ 전체를 암기한 상태가 아닙니다. 첫 애플리케이션 또는 시스템 서버를 스스로 시작하고, 필요한 도메인 지식을 구현 과정에서 추가할 수 있는 상태입니다.
