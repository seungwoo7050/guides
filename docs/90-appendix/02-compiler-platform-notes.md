# 컴파일러와 플랫폼 노트

## 목적

가이드의 핵심 계약과 운영체제·컴파일러 차이를 분리합니다. 명령이 다르다는 이유로 언어 모델까지 다르게 이해하지 않도록 합니다.

저장소를 처음 적용했거나 구조가 바뀐 뒤에는 루트에서 준비합니다.

```sh
./prepare.sh
```

최종 검증의 정본 진입점은 다음 하나입니다.

```sh
./verify.sh
```

이 문서의 개별 명령은 플랫폼 차이를 조사하거나 특정 실패를 좁힐 때 사용합니다. 최종 완료 판정을 대체하지 않습니다.

## 공통 필수 조건

전체 가이드는 다음 조건을 기준으로 합니다.

- Bash
- Make
- CMake 3.20 이상과 CTest
- Python 3.9 이상
- C++20과 C++98을 모두 컴파일할 수 있는 C++ compiler
- C++98 네트워크 실습을 위한 POSIX 환경
- macOS에서 반복 연결 FD 누수를 세기 위한 `lsof`

`prepare.sh`는 저장소가 관리하는 외부 package가 없음을 확인하고 compiler 기능을 작은 프로그램으로 시험합니다. 운영체제 패키지를 자동 설치하지 않습니다. 도구가 없으면 필요한 항목과 설치 예시를 출력한 뒤 중단합니다.

## Modern C++ 과정

### Linux

GCC 또는 Clang을 사용할 수 있습니다. 공식 preset은 Ninja generator를 사용하지만, 루트 Makefile과 `verify.sh`는 직접 CMake configure를 사용하므로 설치된 기본 generator로도 검증할 수 있습니다.

```sh
c++ --version
cmake --version
ninja --version
cmake --preset debug -S exercises/01-modern-cpp
cmake --build exercises/01-modern-cpp/build/debug
ctest --test-dir exercises/01-modern-cpp/build/debug --output-on-failure
```

AddressSanitizer와 UndefinedBehaviorSanitizer를 함께 사용할 수 있습니다.

```sh
cmake --preset sanitize -S exercises/01-modern-cpp
cmake --build exercises/01-modern-cpp/build/sanitize
ctest --test-dir exercises/01-modern-cpp/build/sanitize --output-on-failure

cmake --preset thread-sanitize -S exercises/01-modern-cpp
cmake --build exercises/01-modern-cpp/build/thread-sanitize
ctest --test-dir exercises/01-modern-cpp/build/thread-sanitize --output-on-failure
```

### macOS

Apple Clang과 CMake를 사용합니다. 기본 build 명령은 Linux와 같습니다. LeakSanitizer 지원은 compiler와 macOS 버전에 따라 다르므로, 루트 검증기는 macOS의 기본 ASan probe에서 leak detection을 강제하지 않습니다. 필요한 경우 `leaks` 또는 Instruments로 별도 확인합니다.

POSIX socket의 `poll`, `fcntl`, `close`는 사용할 수 있지만 Linux 전용 `epoll`을 기본 계약으로 두지 않습니다. 네트워크 reference는 운영체제에 따라 `epoll` 또는 `kqueue` backend를 선택합니다. 반복 연결 뒤 열린 파일 디스크립터 수는 Linux의 `/proc/<pid>/fd` 대신 `lsof`로 비교하므로, macOS 전체 검증에서는 `lsof`가 필요합니다.

### Windows

MSVC 또는 Clang-cl로 Modern C++ 과정의 소스와 CMake target을 진행할 수 있습니다.

```powershell
cmake -S exercises/01-modern-cpp -B exercises/01-modern-cpp/build/msvc
cmake --build exercises/01-modern-cpp/build/msvc --config Debug
ctest --test-dir exercises/01-modern-cpp/build/msvc -C Debug --output-on-failure
```

다만 루트 `prepare.sh`·`verify.sh`와 C++98 POSIX 네트워크 과정은 Bash와 POSIX API를 기준으로 하므로 Windows native 전체 검증을 지원하지 않습니다. 전체 검증에는 WSL2의 Linux 환경을 사용합니다.

## C++98 POSIX 과정

Windows native socket API는 POSIX와 타입·초기화·종료 규칙이 다릅니다. C++98 networking exercise는 다음 환경 중 하나를 사용합니다.

- Linux
- macOS
- WSL2의 Linux 환경
- 동등한 POSIX 개발 환경

프로젝트 목적이 WinSock 학습이라면 별도 adapter를 설계해야 하며, 단순한 include 분기로 완전한 이식성을 얻는다고 가정하지 않습니다.

## compiler 선택과 matrix

기준 compiler는 `CXX`로 지정할 수 있습니다.

```sh
CXX=clang++ ./prepare.sh
CXX=clang++ ./verify.sh
```

`CXX`에는 옵션이 섞인 명령이 아니라 실행 가능한 compiler 하나를 지정합니다. 추가 옵션은 개별 CMake·Make target을 조사할 때 별도로 전달합니다.

기본 `verify.sh`는 기준 compiler 외에 서로 다른 GCC 또는 Clang을 찾으면 같은 비-sanitizer 계약을 한 번 더 검사합니다.

```sh
VERIFY_COMPILER_MATRIX=off ./verify.sh       # 기준 compiler만 검사
VERIFY_COMPILER_MATRIX=required ./verify.sh  # 서로 다른 두 compiler가 없으면 실패
```

두 실행 이름이 같은 compiler symlink를 가리키면 별도 matrix 항목으로 세지 않습니다.

## compiler 경고

Modern 실습은 GCC·Clang에서 다음 수준의 경고를 사용합니다.

```text
-Wall -Wextra -Wpedantic -Wconversion -Wshadow
```

경고를 무조건 억제하지 않습니다.

1. 실제 narrowing, shadowing 또는 수명 문제인지 확인합니다.
2. 타입과 API를 수정해 경고 원인을 제거합니다.
3. 의도가 분명한 변환이라면 가장 좁은 위치에서 명시적으로 변환합니다.
4. 외부 헤더 경고라면 target의 system include 경계를 검토합니다.

Modern 실습은 reference와 skeleton의 경고 회귀를 막기 위해 `GUIDE_WARNINGS_AS_ERRORS=ON`을 기본으로 사용합니다. compiler 버전 차이를 조사하는 동안만 `-DGUIDE_WARNINGS_AS_ERRORS=OFF`로 configure할 수 있습니다. C++98 과정도 `-Werror` 계약을 유지합니다.

## Debug와 Release

Debug build만 성공했다고 완료로 보지 않습니다.

- Debug: assertion, debugger, 빠른 진단
- Release: 최적화된 배치 조건과 잠재적 undefined behavior 노출
- ASan·UBSan: 메모리와 일부 undefined behavior
- TSan: data race

루트 검증은 Modern reference를 Debug와 Release로 각각 빌드합니다. 성능 수치는 Release build, 고정 입력, compiler·CPU·명령을 함께 기록해야 의미가 있습니다.

## sanitizer 지원 판정

compiler가 옵션을 받아들인다는 사실만으로 sanitizer를 지원한다고 보지 않습니다. `verify.sh`는 작은 프로그램을 실제로 compile하고 실행한 뒤 본 검사를 시작합니다.

```sh
VERIFY_SANITIZERS=auto ./verify.sh      # 기본값: ASan·UBSan probe 실패 시 SKIP
VERIFY_TSAN=auto ./verify.sh            # 기본값: TSan probe 실패 시 SKIP
VERIFY_SANITIZERS=required ./verify.sh  # probe 실패도 전체 실패
VERIFY_TSAN=required ./verify.sh
VERIFY_STRICT=1 ./verify.sh             # 선택 검사 하나라도 SKIP이면 실패
```

probe가 성공한 뒤 실제 검사에서 실패하면 환경 미지원으로 낮추지 않습니다. reference, 테스트, 런타임 또는 플랫폼 계약의 실제 실패로 처리합니다.

필요하면 sanitizer 환경 변수를 명시적으로 덮어쓸 수 있습니다.

```sh
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 ./verify.sh
TSAN_OPTIONS=halt_on_error=1 ./verify.sh
```

## 검증 격리와 부산물

`verify.sh`는 원본 저장소에서 전체 build를 수행하지 않습니다.

```text
원본의 비생성 파일 snapshot 기록
→ 원본의 이전 build 부산물 정리
→ 저장소를 임시 작업 디렉터리로 복사
→ compiler별 build·test·sanitizer 실행
→ 임시 작업 디렉터리 제거
→ 원본 부산물 정리
→ source snapshot과 tracked Git 상태 비교
```

성공·실패·중단과 관계없이 build 디렉터리, object/archive, 실행 파일, Python cache와 임시 probe를 제거합니다. 기본 로그는 저장소 밖의 임시 경로에 보존됩니다.

```sh
VERIFY_LOG="${TMPDIR:-/tmp}/guide-cpp-verify-$$.log" ./verify.sh
```

## 재현 가능한 환경 기록

문제 보고에는 다음을 포함합니다.

```text
운영체제와 버전
compiler 이름과 버전
CMake·Make·Python 버전
실패한 CHECK 이름
실패한 test 이름
최소 재현 입력
sanitizer 또는 backtrace 원문
verify.sh가 출력한 로그 경로
```

“내 컴퓨터에서는 된다”는 관찰은 환경 차이를 좁힐 정보가 없으면 검증 근거가 아닙니다.
