# Modern C++ 프로그램·빌드·CMake

## 목표

C++ 소스가 실행 파일이 되는 경로를 이해하고, 빈 디렉터리에서 target 기반 CMake 프로젝트를 시작합니다. CMake 문법을 많이 외우는 것이 아니라 다음 질문에 답할 수 있어야 합니다.

- 어느 `.cpp`가 어느 target에 들어가는가
- 공개 헤더와 구현 전용 헤더의 경계는 어디인가
- C++ 표준, 경고와 의존성이 어느 target에 적용되는가
- compile 오류, link 오류와 test 실패가 각각 어느 단계의 문제인가

## 시작하기 전에

터미널에서 현재 디렉터리를 확인하고 파일을 만들 수 있어야 합니다. CMake 3.20 이상과 C++20을 지원하는 compiler가 필요합니다. 저장소의 preset 경로는 Ninja generator를 사용하므로 preset을 그대로 실행하려면 Ninja도 필요합니다. Ninja가 없다면 뒤에 나오는 `cmake -S ... -B ...` 직접 configure 경로를 사용할 수 있습니다.

```sh
c++ --version
cmake --version
ninja --version # preset 경로를 사용할 때
```

## 1. 소스에서 실행 파일까지

C++ compiler는 프로젝트 전체를 하나의 문서처럼 읽지 않습니다. 각 `.cpp`는 자신이 포함한 헤더와 함께 독립된 번역 단위가 됩니다.

```text
main.cpp + 포함된 헤더    → main.o
job_store.cpp + 헤더      → job_store.o
job_runner.cpp + 헤더     → job_runner.o

main.o + job_store.o + job_runner.o
    → linker
    → 실행 파일
```

이 과정에서 실패 위치가 갈립니다.

- preprocess·compile 실패: 현재 번역 단위의 문법, 이름 또는 타입이 잘못됐습니다.
- link 실패: 선언된 정의를 찾지 못했거나 같은 정의가 여러 번 생겼습니다.
- 실행 실패: 프로그램 계약, 수명, 입력 또는 환경의 문제입니다.
- test 실패: 예상한 계약과 관찰된 결과가 다릅니다.

오류 종류를 먼저 분류하면 검색 범위가 줄어듭니다. `undefined reference`를 보고 헤더 문법만 고치거나, compile 오류를 runtime debugger로 찾지 않습니다.

## 2. 선언·정의와 헤더 경계

헤더는 다른 번역 단위가 컴파일하는 데 필요한 계약을 제공합니다.

```cpp
// include/task_store.hpp
#ifndef TASK_STORE_HPP
#define TASK_STORE_HPP

#include <optional>
#include <string>

namespace app
{
class TaskStore
{
public:
    void put(int id, std::string value);
    [[nodiscard]] std::optional<std::string> find(int id) const;
};
}

#endif
```

구현은 `.cpp`에 둡니다.

```cpp
// src/task_store.cpp
#include "task_store.hpp"

namespace app
{
void TaskStore::put(int id, std::string value)
{
    // ...
}
}
```

헤더에는 다음만 둡니다.

- 공개 타입과 함수 선언
- caller가 크기 또는 template 정의를 알아야 하는 타입
- 실제로 inline이어야 하는 짧은 함수
- template 정의

구현 전용 helper와 무거운 의존성을 공개 헤더에 넣으면 모든 caller가 다시 컴파일되고 결합도가 높아집니다.

## 3. CMake는 target의 관계를 기록합니다

최소 프로젝트는 다음과 같습니다.

```cmake
cmake_minimum_required(VERSION 3.20)
project(task_app LANGUAGES CXX)

add_library(task_core
    src/task.cpp
    src/task_store.cpp
)

target_include_directories(task_core
    PUBLIC
        include
)

target_compile_features(task_core PUBLIC cxx_std_20)

add_executable(task_app src/main.cpp)
target_link_libraries(task_app PRIVATE task_core)
```

핵심은 전역 변수처럼 flag를 뿌리는 대신 **사용 요구사항을 target에 붙이는 것**입니다.

### `PUBLIC`, `PRIVATE`, `INTERFACE`

`target_link_libraries`와 `target_include_directories`의 범위를 다음처럼 판단합니다.

- `PRIVATE`: 현재 target을 빌드할 때만 필요합니다.
- `PUBLIC`: 현재 target과 이를 사용하는 caller 모두 필요합니다.
- `INTERFACE`: 현재 target 자체보다 caller에게만 필요합니다.

예를 들어 공개 헤더가 `std::filesystem`만 사용한다면 별도 link 의존성이 없습니다. 공개 헤더에 외부 라이브러리 타입이 노출된다면 caller에도 그 include 경계가 전달될 수 있습니다.

## 4. 소스 파일을 glob으로 숨기지 않습니다

초기 학습 프로젝트에서는 source 목록을 명시합니다.

```cmake
add_library(job_core
    src/job.cpp
    src/job_runner.cpp
    src/journal.cpp
)
```

새 파일을 추가했는데 build graph에 넣지 않은 실수를 즉시 볼 수 있습니다. 대규모 생성 파일에는 다른 선택이 있을 수 있지만, 작은 프로젝트에서 `file(GLOB ...)`이 명료함을 높인다고 가정하지 않습니다.

## 5. 경고와 표준은 한곳에서 관리합니다

```cmake
add_library(project_options INTERFACE)
target_compile_features(project_options INTERFACE cxx_std_20)

add_library(project_warnings INTERFACE)
if(MSVC)
    target_compile_options(project_warnings INTERFACE /W4 /permissive-)
else()
    target_compile_options(
        project_warnings
        INTERFACE
            -Wall
            -Wextra
            -Wpedantic
            -Wconversion
            -Wshadow
    )
endif()

# 공개 헤더가 C++20 타입·문법을 사용하므로 caller에도 표준 요구사항을 전달합니다.
target_link_libraries(task_core PUBLIC project_options PRIVATE project_warnings)
```

언어 표준처럼 caller가 공개 헤더를 컴파일할 때도 필요한 요구사항과, 현재 저장소 소스에만 적용할 경고 정책을 분리합니다. 소스에 compiler별 pragma를 무분별하게 넣지 않고 빌드 정책은 target 경계에 모읍니다. 이 저장소의 실습은 `CMAKE_CXX_EXTENSIONS=OFF`로 GNU 확장 대신 표준 C++20 모드를 사용합니다.

이 저장소의 공식 실습은 `GUIDE_WARNINGS_AS_ERRORS=ON`을 기본으로 두어 reference와 skeleton이 경고 없이 빌드되는지 확인합니다. 새로운 compiler 경고 때문에 이식성 조사가 먼저 필요할 때만 configure에서 `-DGUIDE_WARNINGS_AS_ERRORS=OFF`로 낮추고, 경고 원인과 결정 내용을 기록합니다. 무조건 끄는 것은 해결이 아닙니다.

## 6. configure·build·test를 구분합니다

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

각 명령의 책임은 다릅니다.

- configure: CMake 파일과 환경을 읽고 build graph를 생성합니다.
- build: graph에 따라 compiler와 linker를 실행합니다.
- test: 빌드된 test executable을 실행합니다.

`CMAKE_BUILD_TYPE`은 Ninja·Unix Makefiles 같은 single-config generator에서 사용합니다. Visual Studio·Xcode 같은 multi-config generator에서는 configure 뒤 `cmake --build build --config Debug`와 `ctest --test-dir build -C Debug`처럼 구성을 선택합니다.

CMake 파일을 고쳤는데 compile 명령만 직접 반복하면 build graph의 문제를 놓칠 수 있습니다.

## 7. Debug·Release와 preset

Debug와 Release는 단순히 “느림·빠름”의 차이가 아닙니다.

- Debug: debugger, assertion과 sanitizer에 적합합니다.
- Release: 최적화가 적용된 실제 배치 조건을 확인합니다.

반복되는 configure 옵션은 `CMakePresets.json`에 기록할 수 있습니다.

```json
{
  "version": 2,
  "configurePresets": [
    {
      "name": "debug",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/debug",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Debug"
      }
    }
  ]
}
```

source directory에서 실행은 다음과 같습니다.

```sh
cd exercises/01-modern-cpp
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
```

preset은 사람이 기억한 shell history가 아니라 저장소에 기록된 실행 계약입니다.

## 8. 라이브러리·실행 파일·테스트를 분리합니다

`main.cpp`에 모든 로직을 넣으면 테스트가 process 실행과 문자열 비교에만 의존하게 됩니다. 핵심 로직을 library target으로 분리합니다.

```cmake
add_library(job_core
    src/job.cpp
    src/job_runner.cpp
)

add_executable(job_app src/main.cpp)
target_link_libraries(job_app PRIVATE job_core)

include(CTest)

add_executable(job_core_tests tests/job_core_tests.cpp)
target_link_libraries(job_core_tests PRIVATE job_core)
add_test(NAME job.core COMMAND job_core_tests)
```

이 구조에서 command-line parsing과 process 종료 코드는 얇게 유지하고, 상태·오류·소유권 계약은 library 수준에서 검사할 수 있습니다.

## 9. 설치와 package manager는 첫 조건이 아닙니다

작은 학습 프로젝트를 시작하기 위해 package manager 전체를 먼저 배울 필요는 없습니다. 표준 라이브러리만으로 core 계약을 만들고, 실제 외부 의존성이 생겼을 때 다음을 결정합니다.

- 의존성을 source로 포함하는가
- system package를 사용하는가
- CMake package config를 사용하는가
- Conan·vcpkg 같은 package manager를 사용하는가
- 버전과 lock을 어디에 기록하는가

도구 선택보다 먼저 “어떤 target이 무엇을 필요로 하는가”가 명확해야 합니다.

## 연결 실습

[강한 타입과 target 기반 CMake](../../exercises/01-modern-cpp/01-strong-types-and-cmake/README.md)를 진행합니다.

다음 순서로 관찰합니다.

1. top-level CMake가 exercise 하위 target을 조립합니다.
2. reference와 skeleton이 같은 공개 헤더 계약을 제공합니다.
3. 같은 test source가 서로 다른 구현 library에 연결됩니다.
4. CTest에는 reference test만 등록됩니다.
5. skeleton test executable은 컴파일되지만 TODO가 남아 있어 실행 시 실패합니다.

## 자주 발생하는 실패

### 헤더에서 `using namespace`

모든 caller의 이름 탐색 결과를 바꿉니다. 공개 헤더에서는 사용하지 않습니다.

### include 경로를 소스에 상대 경로로 박음

```cpp
#include "../../../include/task.hpp"
```

build target이 include 경계를 제공하도록 수정합니다.

### 모든 target에 전역 flag 사용

외부 library나 다른 표준 target까지 같은 flag를 강제할 수 있습니다. target별 사용 요구사항으로 옮깁니다.

### source 파일을 추가했지만 target에 연결하지 않음

compile은 일부 성공해도 link에서 정의를 찾지 못합니다. source 목록과 link graph를 확인합니다.

## 완료 기준

- compile·link·test 실패를 구분합니다.
- library, executable과 test target을 직접 만듭니다.
- `PUBLIC`, `PRIVATE`, `INTERFACE`를 사용 이유와 함께 선택합니다.
- C++20 요구사항과 경고를 target에 연결합니다.
- Debug·Release와 sanitizer build를 서로 다른 디렉터리에서 재현합니다.

## 다음 문서

[값·수명·복사·이동](02-values-lifetimes-and-move.md)에서 target 안의 객체가 언제 생성되고 파괴되며, 값 전달이 복사 또는 이동으로 이어지는지 다룹니다.
