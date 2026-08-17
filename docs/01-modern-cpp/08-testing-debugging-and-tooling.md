# 테스트·디버깅·도구

## 목표

코드가 한 번 실행됐다는 사실만으로 작업이 끝났다고 판단하지 않습니다. 컴파일 시점 검사, 단위·통합 테스트, Sanitizer, 디버거, 프로파일러가 각각 어떤 문제를 찾는지 구분하고 재현 가능한 명령과 결과를 남깁니다.

## 시작하기 전에

[동시성·시간·파일 시스템](07-concurrency-time-and-filesystem.md)을 완료하고 상태 전이, 시간 제한, 종료 순서를 설명할 수 있어야 합니다.

## 1. 검증할 질문부터 작성합니다

테스트 코드를 작성하기 전에 요구사항을 관찰 가능한 질문으로 바꿉니다.

예:

```text
TaskId는 정수에서 암묵적으로 생성되는가
이동 후 원본 파일 소유자는 비소유 상태인가
큐가 가득 차면 어떤 오류값으로 거부되는가
작업에서 발생한 예외가 워커 스레드를 종료시키는가
stop 이후 새 제출이 거부되는가
저널에 상태 전이가 정해진 순서로 기록되는가
```

구현한 함수의 수보다 성공과 실패 조건이 명확해야 유효한 테스트를 만들 수 있습니다.

## 2. 컴파일 시점 계약

일부 요구사항은 실행 중 검사하는 것이 아니라 잘못된 코드가 컴파일되지 않게 해야 합니다.

```cpp
static_assert(!std::is_convertible_v<std::uint64_t, TaskId>);
static_assert(!std::is_copy_constructible_v<UniqueFile>);
static_assert(std::is_nothrow_move_constructible_v<UniqueFile>);
```

잘못된 사용 자체가 컴파일에 실패해야 하는 경우에는 컴파일 실패 테스트를 사용할 수 있습니다.

- concept 요구사항을 만족하지 않는 타입 사용
- 복사 금지 타입의 복사
- `const` 객체에서 변경 함수 호출
- 순수 가상 함수 구현 누락

컴파일러 진단 문구 전체는 버전마다 달라질 수 있으므로 컴파일 성공·실패 여부를 기본으로 검사하고, 필요할 때만 안정적인 핵심 위치나 패턴을 확인합니다.

## 3. 단위 테스트와 통합 테스트

### 단위 테스트

작은 값, 상태 전이, 오류 분기를 프로세스 외부 의존성 없이 검사합니다.

```text
TaskId 파싱
Priority 변환
조회 필터와 결정적 정렬
Result 접근 규칙
```

### 통합 테스트

실제 스레드, 파일 시스템, 빌드 구성을 함께 검사합니다.

```text
JobRunner 워커
stop_token 전달
저널 파일
CMake 타깃 연결
```

모든 의존성을 목(mock) 객체로 바꾸면 실제 스레드 종료와 파일 경계를 검증하지 못합니다. 반대로 모든 검사를 프로세스 전체 E2E 테스트로만 만들면 실패 원인을 좁히기 어렵습니다. 확인하려는 계약에 맞는 가장 작은 경계를 선택합니다.

## 4. 참조 구현과 스켈레톤에 같은 계약 적용

Modern C++ 실습은 같은 테스트 소스를 참조 구현과 스켈레톤 구현에 각각 연결합니다.

```text
tests/task_tests.cpp
├─ strong_types_reference 라이브러리
└─ strong_types_skeleton 라이브러리
```

시작 상태는 다음 조건을 만족해야 합니다.

- 스켈레톤이 컴파일됩니다.
- 스켈레톤 테스트는 구현되지 않은 계약 때문에 하나 이상 실패합니다.
- 참조 구현 테스트는 모두 통과합니다.
- 학습자가 TODO를 구현하면 스켈레톤도 같은 테스트를 통과합니다.

학습자용 테스트를 별도로 느슨하게 만들면 참조 구현과 완료 기준이 달라질 수 있습니다.

## 5. CTest

CMake로 테스트 실행 파일을 빌드한 뒤 CTest로 실행합니다.

```sh
cd exercises/01-modern-cpp
cmake --preset debug
cmake --build --preset debug
ctest --preset debug --output-on-failure
```

테스트 이름에는 실패한 영역을 찾을 수 있는 구분자를 포함합니다.

```text
modern.strong-types
modern.unique-file
modern.query-pipeline
modern.local-job-runner
```

동시성 테스트에는 시간 제한을 둡니다. 무한 대기는 아직 실행 중인 상태가 아니라 실패입니다.

## 6. 결정적인 동시성 테스트

다음 테스트는 실행 환경의 스케줄링에 따라 결과가 달라질 수 있습니다.

```cpp
std::this_thread::sleep_for(100ms);
CHECK(job_is_running());
```

느린 CI에서는 작업이 아직 시작되지 않았을 수 있고, 빠른 환경에서는 이미 끝났을 수 있습니다.

임의의 대기 시간 대신 사건을 직접 동기화합니다.

- `std::promise`와 `future`: 작업 시작과 해제 신호
- `std::latch`: 정해진 참여자가 특정 지점에 도착할 때까지 대기
- 조건 변수의 조건식: 특정 상태 전이 대기
- `std::barrier`: 반복되는 단계의 참여자 정렬
- 가짜 clock 또는 주입한 clock: 시간 의존 로직 제어

실습의 큐 포화 테스트는 첫 번째 작업이 시작됐다는 `promise` 신호를 받은 뒤 두 번째 작업을 큐에 넣습니다. 따라서 세 번째 제출의 거부 여부가 우연한 스케줄링에 좌우되지 않습니다.

## 7. 실패를 의도적으로 주입합니다

정상 입력만 통과하는 테스트로는 실패 시 동작을 검증할 수 없습니다.

- 잘못된 숫자와 범위 초과
- 빈 제목
- 존재하지 않는 경로
- 이동 대입으로 기존 자원 교체
- 같은 정렬 키
- 콜백 예외
- 큐 포화
- 실행 중인 작업 취소
- 종료 후 작업 제출

파일 시스템 오류는 읽기 전용 디렉터리, 존재하지 않는 상위 경로, 주입한 파일 시스템 어댑터 등으로 재현할 수 있습니다. 권한 동작은 운영체제와 실행 사용자에 따라 다를 수 있으므로 테스트가 요구하는 환경 조건을 명시합니다.

## 8. Sanitizer

### AddressSanitizer

다음과 같은 메모리 오류를 찾는 데 유용합니다.

- use-after-free
- out-of-bounds 접근
- double free
- 지원 환경에서 감지 가능한 일부 메모리 누수

### UndefinedBehaviorSanitizer

지원하는 검사 항목 안에서 다음과 같은 정의되지 않은 동작을 찾는 데 유용합니다.

- 잘못된 정수 연산과 shift
- 정렬 조건을 위반한 메모리 접근
- 유효하지 않은 일부 다운캐스트

실행 명령은 다음과 같습니다.

```sh
make modern-sanitize
make modern-thread-sanitize
```

메모리·UB 검사와 ThreadSanitizer 검사는 별도 빌드 디렉터리에서 실행합니다. Sanitizer가 통과했다고 논리 오류가 없다는 뜻은 아닙니다. 데이터 레이스 검사는 ThreadSanitizer처럼 별도 도구가 필요하며, ASan과 TSan은 일반적으로 같은 실행 파일에 함께 적용하지 않습니다.

## 9. 디버거의 기본 사용 흐름

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

디버거에서는 다음 정보를 확인합니다.

- 실제 호출 스택
- 예외가 발생한 지점과 처리된 경계
- 이동 후 객체의 핸들 상태
- 뮤텍스를 기다리는 스레드
- 상태 전이 직전과 직후의 값

오류 메시지와 재현 조건을 확인하지 않은 채 처음부터 한 줄씩 실행하지 않습니다. 가능한 원인에 대한 가설을 세우고 필요한 위치에 중단점을 둡니다.

## 10. 코어 덤프와 비정상 종료

운영체제와 보안 설정이 허용하면 비정상 종료 후 코어 덤프를 분석할 수 있습니다.

```sh
ulimit -c unlimited
./program

gdb ./program core
(gdb) backtrace
```

코어 덤프에는 비밀번호, 토큰, 사용자 데이터 등 프로세스 메모리의 민감한 정보가 포함될 수 있으므로 저장과 공유 정책을 정해야 합니다.

## 11. 정적 분석과 포매팅

컴파일러 경고에 더해 `clang-tidy` 같은 정적 분석 도구를 사용할 수 있습니다.

```sh
clang-tidy src/job_runner.cpp -- -std=c++20 -Iinclude
```

가능한 규칙을 모두 켜고 경고 개수만 줄이는 것이 목적은 아닙니다. 프로젝트의 오류 모델과 코딩 규칙에 맞는 검사를 선택하고, 오탐 억제는 가능한 좁은 위치에 근거와 함께 둡니다.

포매터는 의미 없는 스타일 차이를 줄여 줍니다. 이름, 책임 분리, 오류 모델까지 개선해 주는 도구는 아닙니다.

## 12. 프로파일러와 벤치마크

성능 결과를 기록할 때는 다음 조건을 함께 남깁니다.

- Release 빌드 여부
- 컴파일러와 주요 옵션
- CPU와 운영체제
- 입력 크기와 분포
- 반복 횟수와 워밍업 조건
- wall time과 CPU time 중 무엇을 측정했는가
- 메모리 할당과 I/O를 포함했는가

작은 마이크로벤치마크의 결과를 애플리케이션 전체 처리량으로 곧바로 일반화하지 않습니다.

## 13. 빌드 매트릭스

가능한 환경에서는 다음과 같은 최소 매트릭스를 구성합니다.

```text
GCC + Debug
Clang + Debug
GCC 또는 Clang + ASan·UBSan
지원되는 GCC 또는 Clang + TSan
Release 빌드
```

검사하지 않은 모든 컴파일러와 운영체제를 지원한다고 주장할 필요는 없습니다. 실제로 검증한 범위를 명시합니다.

## 14. 문서도 검증 대상입니다

이 저장소의 `scripts/validate_docs.py`는 다음 구조를 검사합니다.

- 필수 문서의 존재 여부
- Markdown 문서당 H1 하나
- 닫히지 않은 코드 펜스
- 깨진 상대 링크
- Modern C++ 실습의 `skeleton/`·`reference/`·`tests/`·CMake 구조
- 참조 구현에 남은 TODO와 스켈레톤에 필요한 TODO

자동 검사는 문서의 기술적 내용을 모두 증명할 수 없지만, 파일 이동이나 편집으로 구조가 조용히 깨지는 문제를 막을 수 있습니다.

## 15. 검증 결과 기록

다음은 재현 가능한 검증 기록의 예입니다.

```text
작업 디렉터리: exercises/01-modern-cpp
명령: cmake --preset sanitize
명령: cmake --build --preset sanitize
환경: GCC 14.2, CMake 3.31, Ninja 1.12, Linux x86_64
결과: 참조 테스트 실행 파일 4개와 CLI 타깃 1개 빌드 성공

명령: ctest --preset sanitize
결과: API 계약 테스트 4개와 CLI 스모크 테스트 1개, 총 5/5 통과

의도적 실패:
- strong-types 스켈레톤: 잘못된 파싱 규칙으로 실패
- unique-file 스켈레톤: 열기·이동 규칙으로 실패
- query 스켈레톤: 필터·정렬 규칙으로 실패
- job-runner 스켈레톤: 제출 상태 규칙으로 실패
- 실행 중 저널 경로 제거: 작업은 완료되고 저널 상태는 실패로 바뀜
```

단순히 “테스트 완료”라고 적지 말고 사용한 명령, 환경, 관찰 결과를 남깁니다.

## 연결 실습

모든 Modern C++ 실습에 다음 검증을 적용합니다.

```sh
make modern-skeleton-build
make modern-test
make modern-sanitize
make modern-thread-sanitize
```

그다음 각 스켈레톤 테스트 실행 파일을 직접 실행해 초기 상태가 의도대로 실패하는지 확인합니다. TODO를 구현한 뒤에는 같은 실행 파일이 통과해야 합니다.

[로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)에서는 동시성 테스트를 임의의 `sleep` 기반으로 바꾸고 반복 실행해 불안정성을 관찰합니다. 이후 `promise`와 조건식 기반의 원래 구조로 복구합니다.

## 완료 기준

- 컴파일 시점 검사, 단위 테스트, 통합 테스트, E2E 검증을 구분합니다.
- 스켈레톤과 참조 구현에 같은 계약 테스트를 사용합니다.
- 동시성 테스트의 사건 순서를 명시적으로 동기화합니다.
- 각 Sanitizer와 디버거가 찾을 수 있는 문제의 범위를 구분합니다.
- Release 성능 결과를 재현 가능한 환경 정보와 함께 기록합니다.
- 문서, 빌드, 테스트를 하나의 검증 체계로 연결합니다.

## 다음 문서

[Modern C++ 애플리케이션 종합 실습](09-application-capstone.md)에서 지금까지 다룬 언어, 설계, 검증 도구를 하나의 완료 기준으로 통합합니다.
