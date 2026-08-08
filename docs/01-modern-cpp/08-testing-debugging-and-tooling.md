# 테스트·디버깅·도구

## 목표

코드가 “한 번 실행됐다”는 사실을 완료 조건으로 사용하지 않습니다. compile-time 계약, 단위·통합 test, sanitizer, debugger와 profiler가 각각 어떤 실패를 찾는지 구분하고, 재현 가능한 명령과 증거를 남깁니다.

## 시작하기 전에

[동시성·시간·filesystem](07-concurrency-time-and-filesystem.md)을 완료하고 상태 전이, timeout과 종료 순서를 설명할 수 있어야 합니다.

## 1. 검증 질문을 먼저 씁니다

테스트 코드를 작성하기 전에 계약을 관찰 가능한 질문으로 바꿉니다.

예:

```text
TaskId는 정수에서 암묵적으로 생성되는가
이동 뒤 원본 파일 소유자는 닫힌 상태인가
queue가 가득 차면 어떤 값으로 거부되는가
작업 예외가 worker thread를 종료시키는가
stop 뒤 새 제출이 거부되는가
journal에 상태 전이가 순서대로 남는가
```

함수 구현 줄 수보다 실패 조건이 명확해야 좋은 테스트를 만들 수 있습니다.

## 2. compile-time 계약

일부 요구는 실행해서 확인하는 것보다 컴파일 시점에 막아야 합니다.

```cpp
static_assert(!std::is_convertible_v<std::uint64_t, TaskId>);
static_assert(!std::is_copy_constructible_v<UniqueFile>);
static_assert(std::is_nothrow_move_constructible_v<UniqueFile>);
```

잘못된 호출 자체가 컴파일되지 않아야 하는 경우 compile-fail test를 사용할 수 있습니다.

- concept 요구조건 불충족
- 복사 금지 타입의 복사
- const 객체에서 변경 함수 호출
- interface 구현 누락

compiler 진단 문구 전체는 버전에 따라 달라질 수 있으므로 성공·실패 여부와 핵심 위치를 검사합니다.

## 3. 단위 test와 통합 test

### 단위 test

작은 값·상태 전이·오류 분기를 process 외부 의존성 없이 검사합니다.

```text
TaskId parsing
Priority 변환
Query filter와 결정적 정렬
Result 접근 계약
```

### 통합 test

실제 thread, filesystem과 build graph를 함께 검사합니다.

```text
JobRunner worker
stop token 전달
journal 파일
CMake target 연결
```

모든 것을 mock으로 대체하면 실제 thread 종료와 파일 경계가 검증되지 않습니다. 반대로 모든 검사를 process E2E로만 만들면 실패 원인을 좁히기 어렵습니다.

## 4. reference와 skeleton의 같은 계약

Modern 실습은 같은 test source를 reference와 skeleton 구현에 연결합니다.

```text
tests/task_tests.cpp
├─ strong_types_reference library
└─ strong_types_skeleton library
```

출발점에서 필요한 조건은 다음입니다.

- skeleton이 컴파일됩니다.
- skeleton test는 최소 하나 이상 실패합니다.
- reference test는 모두 통과합니다.
- 학습자가 TODO를 해결하면 skeleton도 같은 test를 통과합니다.

별도의 느슨한 학습자 test를 두면 reference와 완료 기준이 달라질 수 있습니다.

## 5. CTest

CMake target을 build한 뒤 CTest가 test executable을 실행합니다.

```sh
cmake --preset debug -S exercises/01-modern-cpp
cmake --build exercises/01-modern-cpp/build/debug
ctest --test-dir exercises/01-modern-cpp/build/debug --output-on-failure
```

테스트 이름은 실패한 계약을 찾을 수 있게 영역을 포함합니다.

```text
modern.strong-types
modern.unique-file
modern.query-pipeline
modern.local-job-runner
```

동시 test에는 timeout을 둡니다. 무한 대기는 실패이지 “아직 실행 중”인 상태가 아닙니다.

## 6. 결정적인 동시성 test

다음 패턴은 불안정합니다.

```cpp
std::this_thread::sleep_for(100ms);
CHECK(job_is_running());
```

느린 CI에서는 아직 시작하지 않았을 수 있고 빠른 환경에서는 이미 끝났을 수 있습니다.

대신 사건을 직접 동기화합니다.

- `std::promise`와 `future`: 작업 시작·해제 신호
- `std::latch`: 정해진 참여자 도착
- condition variable predicate: 특정 상태 전이
- barrier: 반복 단계 정렬
- fake clock 또는 주입된 clock: 시간 의존 로직

실습의 queue full test는 첫 작업이 시작했다는 promise를 받은 뒤 두 번째를 queue에 넣습니다. 따라서 세 번째 거부가 scheduling 우연에 의존하지 않습니다.

## 7. 실패를 의도적으로 주입합니다

정상 입력만 통과하는 test는 실패 계약을 검증하지 않습니다.

- 잘못된 숫자와 범위 초과
- 빈 제목
- 존재하지 않는 경로
- 이동 대입으로 기존 자원 교체
- 같은 정렬 key
- callback 예외
- queue full
- running job 취소
- stop 뒤 제출

filesystem 실패는 읽기 전용 디렉터리, 존재하지 않는 parent 또는 주입된 adapter로 재현할 수 있습니다. platform 권한 차이에 의존하는 test는 환경 조건을 명시합니다.

## 8. sanitizer

### AddressSanitizer

다음을 찾는 데 유용합니다.

- use-after-free
- out-of-bounds
- double free
- 일부 leak

### UndefinedBehaviorSanitizer

다음을 찾는 데 유용합니다.

- 잘못된 정수·shift 연산
- 정렬되지 않은 접근
- invalid downcast 등 일부 UB

실행:

```sh
make modern-sanitize
make modern-thread-sanitize
```

두 sanitizer 계열은 별도 build directory에서 실행합니다. sanitizer가 통과했다고 논리 오류가 없다는 뜻은 아닙니다. race 검사는 별도 ThreadSanitizer가 필요할 수 있고, ASan과 TSan을 보통 같은 build에 함께 켜지 않습니다.

## 9. debugger의 최소 루프

### GDB

```sh
gdb ./program
(gdb) break guide::jobs::JobRunner::submit
(gdb) run
(gdb) next
(gdb) print queue_.size()
(gdb) backtrace
```

### LLDB

```sh
lldb ./program
(lldb) breakpoint set --name guide::jobs::JobRunner::submit
(lldb) run
(lldb) next
(lldb) frame variable
(lldb) thread backtrace
```

debugger에서 다음을 관찰합니다.

- 실제 호출 stack
- 예외가 던져진 지점과 잡힌 경계
- moved-from 객체의 handle
- mutex를 기다리는 thread
- 상태 전이 직전·직후 값

오류 메시지를 보지 않고 무작정 한 줄씩 실행하지 않습니다. 실패 가설을 세우고 필요한 위치에 breakpoint를 둡니다.

## 10. core dump와 비정상 종료

운영체제 설정이 허용하면 crash 뒤 core dump를 분석할 수 있습니다.

```sh
ulimit -c unlimited
./program

gdb ./program core
(gdb) backtrace
```

core dump에는 민감한 메모리가 포함될 수 있으므로 저장·공유 정책을 정합니다.

## 11. 정적 분석과 formatting

compiler 경고 뒤에 `clang-tidy` 같은 정적 분석을 추가할 수 있습니다.

```sh
clang-tidy src/job_runner.cpp -- -std=c++20 -Iinclude
```

정적 분석 규칙을 대량으로 켜고 경고 수만 줄이는 것이 목적이 아닙니다. 프로젝트 계약에 맞는 규칙을 선택하고 false positive 억제는 가장 좁은 위치에 이유와 함께 둡니다.

formatter는 의미 없는 스타일 diff를 줄입니다. 그러나 formatter가 이름, 책임과 오류 모델을 개선해 주지는 않습니다.

## 12. profiler와 benchmark

성능을 말할 때 다음을 함께 기록합니다.

- Release build
- compiler와 옵션
- CPU와 운영체제
- 입력 크기와 분포
- 반복 횟수와 warmup
- wall time인지 CPU time인지
- allocation과 I/O 포함 여부

작은 microbenchmark 결과를 전체 application 처리량으로 일반화하지 않습니다.

## 13. build matrix

가능하면 최소 matrix를 사용합니다.

```text
GCC + Debug
Clang + Debug
GCC 또는 Clang + ASan·UBSan
GCC 또는 Clang + TSan
Release build
```

모든 compiler·운영체제를 지원한다고 주장할 필요는 없습니다. 실제로 검증한 범위를 명시합니다.

## 14. 문서도 검사 대상입니다

이 저장소의 `scripts/validate_docs.py`는 다음을 확인합니다.

- 필수 문서 존재
- Markdown H1 하나
- 닫히지 않은 code fence
- 깨진 상대 링크
- Modern exercise의 skeleton·reference·tests·CMake 구조
- reference에 남은 TODO와 skeleton에 없는 TODO

문서의 기술적 내용 전체를 자동 증명하지는 못하지만, 구조가 조용히 깨지는 것을 막습니다.

## 15. 증거 기록

좋은 검증 보고는 다음 형태입니다.

```text
작업 디렉터리: exercises/01-modern-cpp
명령: cmake --preset sanitize
명령: cmake --build --preset sanitize
환경: GCC 14.2, CMake 3.31, Ninja 1.12, Linux x86_64
결과: reference test executable 4개와 CLI target 1개 build 성공

명령: ctest --preset sanitize
결과: API 계약 4개와 CLI smoke test 1개, 총 5/5 통과

의도적 실패:
- skeleton strong-types: invalid parse 계약 실패
- skeleton unique-file: open·move 계약 실패
- skeleton query: filter·sort 계약 실패
- skeleton job-runner: submit 상태 계약 실패
- runtime journal 경로 제거: 작업은 완료되고 health 검사는 실패 상태 관찰
```

“테스트 완료”만 적는 것보다 재현 가능한 명령과 관찰을 남깁니다.

## 연결 실습

모든 Modern 실습에 다음을 적용합니다.

```sh
make modern-skeleton-build
make modern-test
make modern-sanitize
make modern-thread-sanitize
```

그다음 각 skeleton test executable을 직접 실행해 시작점이 실패하는지 확인합니다. TODO를 구현한 뒤 같은 executable이 통과해야 합니다.

[로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)에서는 concurrency test를 `sleep` 기반으로 바꿔 본 뒤 반복 실행하여 불안정성을 관찰합니다. 그다음 promise와 predicate 기반 원래 구조로 복구합니다.

## 완료 기준

- compile-time, unit, integration과 E2E 검증을 구분합니다.
- skeleton과 reference에 같은 계약 test를 사용합니다.
- 동시성 test를 사건 기반으로 동기화합니다.
- sanitizer와 debugger가 찾는 실패 범위를 구분합니다.
- Release 성능 주장을 재현 가능한 환경 정보와 함께 기록합니다.
- 문서·build·test를 하나의 검증 계약으로 연결합니다.

## 다음 문서

[Modern C++ application capstone](09-application-capstone.md)에서 지금까지의 언어·설계·도구를 하나의 완료 기준으로 통합합니다.
