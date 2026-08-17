# 컴파일러와 플랫폼 참고 사항

## 목적

가이드의 공통 요구사항과 운영체제·컴파일러 차이를 분리합니다. 명령이나 지원 API가 다르다는 이유로 C++ 언어 모델까지 다르게 이해하지 않도록 합니다.

저장소를 처음 준비했거나 구조가 바뀐 뒤에는 루트에서 다음 명령을 실행합니다.

```sh
./prepare.sh
```

최종 검증의 기준 진입점은 다음 하나입니다.

```sh
./verify.sh
```

아래의 개별 명령은 플랫폼 차이를 조사하거나 특정 실패를 좁힐 때 사용합니다. 최종 완료 판정을 대체하지 않습니다.

## 공통 필수 조건

전체 가이드는 다음 환경을 기준으로 합니다.

- Bash
- GNU Make 또는 호환되는 Make
- CMake 3.20 이상과 CTest
- Python 3.9 이상
- C++20과 C++98을 모두 컴파일할 수 있는 C++ 컴파일러
- C++98 네트워크 실습을 위한 POSIX 환경
- macOS에서 반복 연결의 파일 디스크립터 누수를 세기 위한 `lsof`

`prepare.sh`는 저장소가 별도로 관리하는 외부 패키지가 없음을 확인하고, 필요한 컴파일러 기능을 작은 프로그램으로 검사합니다. 운영체제 패키지를 자동 설치하지 않습니다. 도구가 없으면 필요한 항목과 설치 예시를 출력한 뒤 중단합니다.

## Modern C++ 과정

### Linux

GCC 또는 Clang을 사용할 수 있습니다. 공식 프리셋은 Ninja 생성기를 사용하지만, 루트 `Makefile`과 `verify.sh`는 CMake 설정을 직접 수행하므로 설치된 기본 생성기로도 검증할 수 있습니다.

```sh
c++ --version
cmake --version
ninja --version
cmake --preset debug -S exercises/01-modern-cpp
cmake --build exercises/01-modern-cpp/build/debug
ctest --test-dir exercises/01-modern-cpp/build/debug --output-on-failure
```

AddressSanitizer와 UndefinedBehaviorSanitizer는 같은 빌드에서 사용할 수 있습니다. ThreadSanitizer는 별도 빌드로 실행합니다.

```sh
cmake --preset sanitize -S exercises/01-modern-cpp
cmake --build exercises/01-modern-cpp/build/sanitize
ctest --test-dir exercises/01-modern-cpp/build/sanitize --output-on-failure

cmake --preset thread-sanitize -S exercises/01-modern-cpp
cmake --build exercises/01-modern-cpp/build/thread-sanitize
ctest --test-dir exercises/01-modern-cpp/build/thread-sanitize --output-on-failure
```

### macOS

Apple Clang과 CMake를 사용합니다. 기본 빌드 명령은 Linux와 같습니다. LeakSanitizer와 ThreadSanitizer의 실제 동작 범위는 Apple Clang과 macOS 버전에 따라 달라질 수 있습니다. 루트 검증기는 기능 검사에 실패한 선택 검사를 지원되지 않는 항목으로 처리할 수 있습니다. 필요한 경우 `leaks`나 Instruments로 별도 확인합니다.

POSIX의 `poll`, `fcntl`, `close`는 사용할 수 있지만 Linux 전용 `epoll`을 공통 요구사항으로 두지 않습니다. 네트워크 참조 구현은 운영체제에 따라 `epoll` 또는 `kqueue` 백엔드를 선택합니다. 반복 연결 뒤 열린 파일 디스크립터 수는 Linux의 `/proc/<pid>/fd` 대신 `lsof`로 비교하므로 macOS 전체 검증에는 `lsof`가 필요합니다.

### Windows

MSVC나 Clang-cl로 Modern C++ 과정의 소스와 CMake 타깃을 빌드할 수 있습니다.

```powershell
cmake -S exercises/01-modern-cpp -B exercises/01-modern-cpp/build/msvc
cmake --build exercises/01-modern-cpp/build/msvc --config Debug
ctest --test-dir exercises/01-modern-cpp/build/msvc -C Debug --output-on-failure
```

다만 루트 `prepare.sh`·`verify.sh`와 C++98 POSIX 네트워크 과정은 Bash와 POSIX API를 기준으로 하므로 Windows 네이티브 환경의 전체 검증은 지원하지 않습니다. 전체 검증에는 WSL2의 Linux 환경을 사용합니다.

## C++98 POSIX 과정

Windows의 WinSock은 POSIX 소켓과 타입, 초기화, 오류와 종료 규칙이 다릅니다. C++98 네트워크 실습은 다음 환경 중 하나를 사용합니다.

- Linux
- macOS
- WSL2의 Linux 환경
- 동등한 POSIX 개발 환경

프로젝트 목적이 WinSock 학습이라면 별도 어댑터와 수명 규칙을 설계해야 합니다. 헤더 분기 몇 개만으로 완전한 이식성을 얻는다고 가정하지 않습니다.

## 컴파일러 선택과 매트릭스

기준 컴파일러는 `CXX` 환경 변수로 지정할 수 있습니다.

```sh
CXX=clang++ ./prepare.sh
CXX=clang++ ./verify.sh
```

`CXX`에는 옵션을 섞은 명령 문자열이 아니라 실행 가능한 컴파일러 하나를 지정합니다. 추가 옵션은 개별 CMake·Make 타깃을 조사할 때 별도로 전달합니다.

기본 `verify.sh`는 기준 컴파일러 외에 다른 종류의 GCC 또는 Clang을 찾으면 Sanitizer를 사용하지 않는 같은 요구사항을 한 번 더 검사합니다.

```sh
VERIFY_COMPILER_MATRIX=off ./verify.sh       # 기준 컴파일러만 검사
VERIFY_COMPILER_MATRIX=required ./verify.sh  # 서로 다른 두 컴파일러가 없으면 실패
```

실행 파일 이름이 달라도 같은 컴파일러 바이너리를 가리키는 심볼릭 링크라면 별도 매트릭스 항목으로 세지 않습니다.

## 컴파일러 경고

Modern 실습은 GCC·Clang에서 다음 수준의 경고를 사용합니다.

```text
-Wall -Wextra -Wpedantic -Wconversion -Wshadow
```

경고를 무조건 억제하지 않습니다.

1. 실제 축소 변환, 이름 가리기나 수명 문제인지 확인합니다.
2. 타입과 인터페이스를 수정해 원인을 제거합니다.
3. 의도한 변환이라면 가장 좁은 위치에서 명시적으로 변환합니다.
4. 외부 헤더의 경고라면 타깃의 시스템 포함 경계를 검토합니다.

Modern 실습은 참조 구현과 스켈레톤의 경고 회귀를 막기 위해 `GUIDE_WARNINGS_AS_ERRORS=ON`을 기본값으로 사용합니다. 컴파일러 버전 차이를 조사할 때만 `-DGUIDE_WARNINGS_AS_ERRORS=OFF`로 설정할 수 있습니다. C++98 과정도 프로젝트 코드에 `-Werror`를 적용합니다.

경고 옵션의 정확한 집합은 컴파일러마다 다를 수 있습니다. 한 컴파일러 전용 옵션을 다른 컴파일러에 그대로 전달하지 않습니다.

## Debug와 Release

Debug 빌드만 성공했다고 완료로 판단하지 않습니다.

- Debug: 단언문, 디버거와 빠른 진단
- Release: 최적화된 조건에서의 동작과 성능
- ASan·UBSan: 메모리 오류와 일부 정의되지 않은 동작
- TSan: 데이터 경쟁

루트 검증은 Modern 참조 구현을 Debug와 Release로 각각 빌드합니다. 성능 수치는 Release 빌드, 고정 입력, 컴파일러·CPU·명령을 함께 기록해야 의미가 있습니다.

최적화가 오류를 만드는 것이 아니라, 이미 존재하던 정의되지 않은 동작이나 타이밍 의존성을 더 쉽게 드러낼 수 있다는 점을 구분합니다.

## Sanitizer 지원 판정

컴파일러가 옵션을 받아들였다는 사실만으로 Sanitizer가 실행 환경에서 동작한다고 판단하지 않습니다. `verify.sh`는 작은 프로그램을 실제로 컴파일하고 실행한 뒤 본 검사를 시작합니다.

```sh
VERIFY_SANITIZERS=auto ./verify.sh      # 기본값: ASan·UBSan 검사 실패 시 SKIP
VERIFY_TSAN=auto ./verify.sh            # 기본값: TSan 검사 실패 시 SKIP
VERIFY_SANITIZERS=required ./verify.sh  # 기능 검사 실패도 전체 실패
VERIFY_TSAN=required ./verify.sh
VERIFY_STRICT=1 ./verify.sh             # 선택 검사 하나라도 SKIP이면 실패
```

기능 검사가 성공한 뒤 실제 프로젝트 검사에서 실패하면 환경 미지원으로 낮추지 않습니다. 참조 구현, 테스트, 런타임이나 플랫폼 규칙의 실제 실패로 처리합니다.

필요하면 Sanitizer 환경 변수를 명시적으로 덮어쓸 수 있습니다.

```sh
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 ./verify.sh
TSAN_OPTIONS=halt_on_error=1 ./verify.sh
```

옵션을 바꾸면 어떤 검사를 비활성화했는지 검증 기록에 남깁니다.

## 검증 격리와 생성 부산물

`verify.sh`는 원본 저장소에서 전체 빌드를 계속 진행하지 않습니다.

```text
원본의 비생성 파일 스냅샷 기록
→ 원본의 기존 빌드 부산물 정리
→ 저장소를 임시 작업 디렉터리로 복사
→ 컴파일러별 빌드·테스트·Sanitizer 실행
→ 임시 작업 디렉터리 제거
→ 원본 부산물 정리
→ 소스 스냅샷과 추적 중인 Git 상태 비교
```

성공, 실패나 중단 여부와 관계없이 빌드 디렉터리, 객체·아카이브, 실행 파일, Python 캐시와 임시 기능 검사 파일을 제거합니다. 기본 로그는 저장소 밖의 임시 경로에 보존됩니다.

```sh
VERIFY_LOG="${TMPDIR:-/tmp}/guide-cpp-verify-$$.log" ./verify.sh
```

## 재현 가능한 환경 기록

문제를 보고할 때는 다음 정보를 포함합니다.

```text
운영체제와 버전
컴파일러 이름과 버전
CMake·Make·Python 버전
실패한 CHECK 이름
실패한 테스트 이름
최소 재현 입력
Sanitizer 보고서 또는 백트레이스 원문
verify.sh가 출력한 로그 경로
```

환경 정보가 없는 “내 컴퓨터에서는 된다”는 관찰만으로는 차이를 좁힐 수 없습니다.
