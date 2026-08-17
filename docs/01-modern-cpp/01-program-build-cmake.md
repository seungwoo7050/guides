# Modern C++ 프로그램·빌드·CMake

## 목표

C++ 소스가 실행 파일이 되는 과정을 이해하고, 빈 디렉터리에서 타깃 중심의 CMake 프로젝트를 시작합니다. CMake 문법을 많이 암기하는 것이 아니라 다음 질문에 답할 수 있어야 합니다.

- 각 `.cpp` 파일은 어느 타깃에 포함되는가
- 공개 헤더와 구현 전용 헤더의 경계는 어디인가
- C++ 표준, 경고 옵션, 의존성은 어느 타깃에 적용되는가
- 컴파일 오류, 링크 오류, 테스트 실패는 각각 어느 단계에서 발생하는가

## 시작하기 전에

터미널에서 현재 디렉터리를 확인하고 파일을 만들 수 있어야 합니다. CMake 3.20 이상과 C++20을 지원하는 컴파일러가 필요합니다. 저장소의 프리셋은 Ninja 생성기를 사용하므로 그대로 실행하려면 Ninja도 설치되어 있어야 합니다. Ninja가 없다면 뒤에서 설명하는 `cmake -S ... -B ...` 방식으로 직접 구성할 수 있습니다.

```sh
c++ --version
cmake --version
ninja --version # 프리셋을 사용할 때만 필요
```

## 1. 소스 파일에서 실행 파일까지

C++ 컴파일러는 프로젝트 전체를 하나의 문서처럼 읽지 않습니다. 각 `.cpp` 파일과 그 파일이 포함한 헤더는 하나의 번역 단위로 처리되어 독립적으로 컴파일됩니다.

```text
main.cpp + 포함한 헤더       → main.o
job_store.cpp + 포함한 헤더  → job_store.o
job_runner.cpp + 포함한 헤더 → job_runner.o

main.o + job_store.o + job_runner.o
    → 링커
    → 실행 파일
```

실패 지점에 따라 오류의 성격도 달라집니다.

- 전처리·컴파일 실패: 현재 번역 단위의 문법, 이름, 타입이 잘못됐습니다.
- 링크 실패: 선언에 대응하는 정의를 찾지 못했거나 같은 정의가 중복됐습니다.
- 실행 중 실패: 프로그램의 로직, 객체 수명, 입력, 실행 환경에 문제가 있습니다.
- 테스트 실패: 명시한 기대 결과와 실제 결과가 다릅니다.

오류 유형을 먼저 분류하면 확인할 범위를 줄일 수 있습니다. `undefined reference`가 발생했는데 헤더 문법만 수정하거나, 컴파일 오류를 실행 중 디버거로 찾으려 해서는 안 됩니다.

## 2. 선언·정의와 헤더 경계

헤더는 다른 번역 단위가 코드를 컴파일하는 데 필요한 인터페이스를 제공합니다.

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

구현은 `.cpp` 파일에 둡니다.

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

헤더에는 다음과 같이 사용하는 코드가 알아야 하는 내용만 둡니다.

- 공개 타입과 함수 선언
- 사용자가 객체의 크기를 알아야 하는 완전한 타입 정의
- 실제로 인라인 정의가 필요한 짧은 함수
- 템플릿 정의

구현 전용 도우미와 불필요하게 무거운 의존성을 공개 헤더에 넣으면 해당 헤더를 사용하는 소스가 함께 다시 컴파일되고 결합도도 높아집니다.

## 3. CMake에는 타깃 간 관계를 기록합니다

최소 프로젝트는 다음과 같이 구성할 수 있습니다.

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

핵심은 전역 옵션을 모든 대상에 일괄 적용하는 대신 **빌드 요구사항을 해당 타깃에 연결하는 것**입니다.

### `PUBLIC`, `PRIVATE`, `INTERFACE`

`target_link_libraries`와 `target_include_directories`의 범위는 다음 기준으로 선택합니다.

- `PRIVATE`: 현재 타깃을 빌드할 때만 필요합니다.
- `PUBLIC`: 현재 타깃과 이 타깃을 사용하는 다른 타깃 모두에 필요합니다.
- `INTERFACE`: 현재 타깃 자체에는 필요하지 않고 사용하는 타깃에만 필요합니다.

예를 들어 공개 헤더가 표준 라이브러리의 `std::filesystem`만 사용한다면 별도 링크 의존성은 필요하지 않습니다. 반면 공개 헤더에 외부 라이브러리의 타입이 노출되면 그 헤더를 사용하는 타깃에도 해당 include 경로와 관련 요구사항을 전달해야 할 수 있습니다.

## 4. 소스 목록을 glob으로 숨기지 않습니다

초기 학습 프로젝트에서는 소스 목록을 명시합니다.

```cmake
add_library(job_core
    src/job.cpp
    src/job_runner.cpp
    src/journal.cpp
)
```

이렇게 하면 새 파일을 만들고도 빌드 그래프에 추가하지 않은 실수를 쉽게 확인할 수 있습니다. 생성 파일이 매우 많은 프로젝트에서는 다른 방식을 선택할 수 있지만, 작은 프로젝트에서 `file(GLOB ...)`이 반드시 구성을 더 명확하게 만드는 것은 아닙니다.

## 5. 언어 표준과 경고 정책을 한곳에서 관리합니다

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

# 공개 헤더가 C++20 타입·문법을 사용하므로 사용하는 타깃에도 표준 요구사항을 전달합니다.
target_link_libraries(task_core PUBLIC project_options PRIVATE project_warnings)
```

공개 헤더를 컴파일하는 타깃에도 필요한 언어 표준과, 현재 저장소의 소스에만 적용할 경고 정책을 분리합니다. 컴파일러별 pragma를 소스 곳곳에 추가하기보다 빌드 정책을 타깃 경계에 모읍니다. 이 저장소의 실습은 `CMAKE_CXX_EXTENSIONS=OFF`를 사용해 GNU 확장이 아닌 표준 C++20 모드로 빌드합니다.

공식 실습은 `GUIDE_WARNINGS_AS_ERRORS=ON`을 기본값으로 사용하여 참조 구현과 스켈레톤이 경고 없이 빌드되는지 검사합니다. 새 컴파일러 경고의 이식성 영향을 먼저 조사해야 할 때만 구성 단계에서 `-DGUIDE_WARNINGS_AS_ERRORS=OFF`를 지정하고, 경고의 원인과 판단 근거를 기록합니다. 단순히 옵션을 끄는 것은 해결이 아닙니다.

## 6. 구성·빌드·테스트를 구분합니다

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
ctest --test-dir build --output-on-failure
```

각 명령의 역할은 다릅니다.

- 구성(configure): CMake 파일과 환경을 읽어 빌드 그래프를 생성합니다.
- 빌드(build): 빌드 그래프에 따라 컴파일러와 링커를 실행합니다.
- 테스트(test): 빌드된 테스트 실행 파일을 실행합니다.

`CMAKE_BUILD_TYPE`은 Ninja와 Unix Makefiles 같은 단일 구성 생성기에서 사용합니다. Visual Studio와 Xcode 같은 다중 구성 생성기에서는 구성 단계 이후 `cmake --build build --config Debug`와 `ctest --test-dir build -C Debug`처럼 빌드 구성을 선택합니다.

CMake 파일을 수정하고도 컴파일 명령만 직접 반복하면 빌드 그래프의 변경 사항을 반영하지 못할 수 있습니다.

## 7. Debug·Release와 프리셋

Debug와 Release는 단순히 실행 속도만 다른 구성이 아닙니다.

- Debug: 일반적으로 디버그 심볼을 포함하며 디버거, assertion, Sanitizer를 사용한 검증에 적합합니다.
- Release: 최적화가 적용된 코드에서도 동작과 성능 특성이 유지되는지 확인하는 데 사용합니다.

정확한 옵션은 사용하는 툴체인과 프로젝트 설정에 따라 달라집니다.

반복되는 구성 옵션은 `CMakePresets.json`에 기록할 수 있습니다.

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

소스 디렉터리에서 다음과 같이 실행합니다.

```sh
cd exercises/01-modern-cpp
cmake --preset debug
cmake --build --preset debug
ctest --preset debug
```

프리셋은 개인의 셸 기록에 의존하지 않고 저장소에 재현 가능한 빌드 구성을 남기는 방법입니다.

## 8. 라이브러리·실행 파일·테스트를 분리합니다

`main.cpp`에 모든 로직을 넣으면 테스트가 프로세스를 실행하고 문자열 출력을 비교하는 방식에 지나치게 의존하게 됩니다. 핵심 로직은 라이브러리 타깃으로 분리합니다.

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

이 구조에서는 명령행 인자 처리와 프로세스 종료 코드를 얇게 유지하면서 상태, 오류, 소유권 규칙을 라이브러리 수준에서 직접 테스트할 수 있습니다.

## 9. 설치와 패키지 관리자는 시작 조건이 아닙니다

작은 학습 프로젝트를 시작하기 위해 패키지 관리자 전체를 먼저 배울 필요는 없습니다. 표준 라이브러리만으로 핵심 인터페이스를 구성하고, 실제 외부 의존성이 생겼을 때 다음 항목을 결정합니다.

- 의존성 소스를 저장소에 포함할 것인가
- 운영체제 패키지를 사용할 것인가
- CMake package config를 사용할 것인가
- Conan이나 vcpkg 같은 패키지 관리자를 사용할 것인가
- 버전과 잠금 정보를 어디에 기록할 것인가

도구를 선택하기 전에 어느 타깃이 무엇을 필요로 하는지부터 명확히 해야 합니다.

## 연결 실습

[강한 타입과 타깃 중심 CMake](../../exercises/01-modern-cpp/01-strong-types-and-cmake/README.md)를 진행합니다.

다음 순서로 구조를 확인합니다.

1. 최상위 CMake에서 각 실습의 하위 타깃을 구성합니다.
2. `reference/`와 `skeleton/`은 같은 공개 헤더 인터페이스를 제공합니다.
3. 같은 테스트 소스가 서로 다른 구현 라이브러리에 연결됩니다.
4. CTest에는 참조 구현 테스트만 등록됩니다.
5. 스켈레톤 테스트 실행 파일은 컴파일되지만 TODO가 남아 있으므로 실행하면 실패합니다.

## 자주 발생하는 문제

### 헤더에서 `using namespace` 사용

공개 헤더의 `using namespace`는 해당 헤더를 포함하는 모든 코드의 이름 탐색에 영향을 줍니다. 공개 헤더에서는 사용하지 않습니다.

### include 경로를 소스에 상대 경로로 직접 지정

```cpp
#include "../../../include/task.hpp"
```

타깃이 올바른 include 경로를 제공하도록 수정합니다.

### 모든 타깃에 전역 옵션 적용

외부 라이브러리나 다른 언어 표준을 사용하는 타깃에도 같은 옵션을 강제할 수 있습니다. 타깃별 사용 요구사항으로 옮깁니다.

### 소스 파일을 만들었지만 타깃에 추가하지 않음

일부 번역 단위는 컴파일되더라도 링크 단계에서 정의를 찾지 못할 수 있습니다. 소스 목록과 링크 관계를 확인합니다.

## 완료 기준

- 컴파일·링크·테스트 실패를 구분합니다.
- 라이브러리, 실행 파일, 테스트 타깃을 직접 구성합니다.
- `PUBLIC`, `PRIVATE`, `INTERFACE`를 각각의 사용 이유와 함께 선택합니다.
- C++20 요구사항과 경고 정책을 적절한 타깃에 연결합니다.
- Debug·Release·Sanitizer 빌드를 서로 다른 빌드 디렉터리에서 재현합니다.

## 다음 문서

[값·수명·복사·이동](02-values-lifetimes-and-move.md)에서 타깃 안의 객체가 언제 생성되고 파괴되는지, 값을 전달할 때 복사와 이동이 어떻게 선택되는지 다룹니다.
