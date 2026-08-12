# Modern C++ 실습 경로

## 목적

네 실습은 서로 다른 기능을 나열하지 않고 하나의 개발 능력을 단계적으로 만듭니다.

```text
강한 값 타입과 CMake
→ 이동 전용 자원 소유자
→ algorithms·ranges·concepts 조회
→ 종료 가능한 동시 작업 실행기
```

모든 실습은 다음 구조를 공유합니다.

```text
README.md     문제 계약과 완료 기준
skeleton/     학습자가 구현할 시작점
reference/    완료 뒤 비교할 정본 구현
tests/        두 구현에 동일하게 연결되는 계약 test
CMakeLists.txt
```

## 진행 규칙

1. 연결 문서를 먼저 읽습니다.
2. `README.md`에서 정상·실패 계약을 확인합니다.
3. `make workspace TRACK=modern`으로 전용 workspace를 한 번 생성합니다.
4. reference를 열지 않고 `.workspace/01-modern-cpp`의 skeleton TODO만 구현합니다.
5. `modern-exercise-test`로 현재 실습의 첫 실패를 하나씩 줄입니다.
6. Debug와 지원 환경의 sanitizer를 통과합니다.
7. 마지막에 reference와 diff를 비교합니다.
8. 구현 차이가 계약 차이인지 단순한 표현 차이인지 설명합니다.

reference를 복사하는 것으로 완료하지 않습니다. 테스트를 통과한 자신의 구현과 비교해야 reference가 설계 자료가 됩니다.

## 실습 목록

### 1. [강한 타입과 target 기반 CMake](01-strong-types-and-cmake/README.md)

- explicit 값 타입
- enum class
- `from_chars`
- 생성자 불변식
- library·test target

### 2. [RAII와 이동 전용 파일 소유자](02-unique-file/README.md)

- 단일 소유권
- 복사 삭제
- `noexcept` 이동
- 반복 가능한 close
- system error 보존

### 3. [조회 파이프라인](03-query-pipeline/README.md)

- `span` 비소유 입력
- lazy filter view
- reference materialization
- 결정적인 ranges sort
- concept 기반 template 계약

### 4. [로컬 작업 실행기](04-local-job-runner/README.md)

- result와 optional
- bounded queue
- `jthread`와 stop token
- mutex·condition variable
- 상태 전이와 예외 경계
- filesystem journal
- 결정적 동시성 test

## 저장소 준비

새 checkout 또는 overlay 적용 뒤 저장소 루트에서 한 번 실행합니다.

```sh
./prepare.sh
```

`prepare.sh`는 최종 트랙 구조, 실행 권한, 이전 build 부산물과 compiler 기능만 준비합니다. 실습 정답을 작성하거나 테스트를 대신 실행하지 않습니다.

이어서 canonical skeleton을 보존하는 learner workspace를 생성합니다.

```sh
make workspace TRACK=modern
```

이후에는 `.workspace/01-modern-cpp/<exercise>/skeleton/`만 수정합니다. 이미 workspace가 있으면 명령은 덮어쓰지 않고 실패합니다.

## 전체 검증

최종 저장소 전체는 루트에서 검사합니다.

```sh
./verify.sh
```

루트 검증은 Modern 실습에 대해 다음을 확인합니다.

- skeleton 네 개가 모두 컴파일됨
- 초기 skeleton이 exit code `1`과 공통 assertion 요약으로 실패함
- crash, loader 오류, timeout과 sanitizer abort는 예상된 실패로 인정하지 않음
- reference가 Debug와 Release CTest를 통과함
- runtime probe를 통과한 ASan·UBSan과 TSan 검사
- 사용 가능한 추가 compiler의 비-sanitizer build
- 검증 뒤 build/cache 부산물 부재

## learner workspace 검증

각 실습의 완성된 skeleton에 reference와 같은 계약 test를 실행합니다.

```sh
make modern-exercise-test MODERN_EXERCISE=01-strong-types-and-cmake
make modern-exercise-test MODERN_EXERCISE=02-unique-file
make modern-exercise-test MODERN_EXERCISE=03-query-pipeline
make modern-exercise-test MODERN_EXERCISE=04-local-job-runner
```

해당 compiler/runtime이 sanitizer를 지원하면 같은 `MODERN_EXERCISE`를 전달해 `modern-exercise-sanitize` 또는 `modern-exercise-thread-sanitize`를 실행합니다.

## canonical 저장소 검증 명령

수정 중인 실습만 빠르게 확인할 수 있습니다.

```sh
make modern-skeleton-build
make modern-start-state
make modern-test
make modern-release
make modern-sanitize
make modern-thread-sanitize
```

이 target들은 추적된 미완성 skeleton의 출발 상태와 canonical reference를 검사합니다. learner 완료 판정용이 아닙니다.

직접 CMake를 사용할 수도 있습니다.

```sh
cmake --preset debug -S exercises/01-modern-cpp
cmake --build exercises/01-modern-cpp/build/debug
ctest --test-dir exercises/01-modern-cpp/build/debug --output-on-failure
```

개별 명령은 개발 피드백용입니다. 저장소 완료 판정은 `./verify.sh`를 기준으로 합니다.

## 시작점 검사

skeleton은 컴파일되지만 테스트는 실패해야 합니다. Debug build 뒤 다음 실행 파일이 생깁니다.

```text
build/debug/01-strong-types-and-cmake/strong_types_skeleton_tests
build/debug/02-unique-file/unique_file_skeleton_tests
build/debug/03-query-pipeline/query_pipeline_skeleton_tests
build/debug/04-local-job-runner/local_job_runner_skeleton_tests
```

출발점이 통과한다면 테스트가 계약을 충분히 구분하지 못하거나 skeleton에 정답이 들어간 것입니다. 반대로 임의의 non-zero 종료를 올바른 시작점으로 간주해서도 안 됩니다. 공통 test harness의 assertion 실패와 suite 요약이 있어야 합니다.

학습자가 TODO를 모두 구현한 뒤에는 workspace의 같은 skeleton test executable이 성공해야 합니다. 저장소의 정본 검증은 배포된 미완성 skeleton의 시작 상태를 검사하므로 learner 구현은 `.workspace/`에서만 진행합니다.

## 완료 조건

- 네 skeleton이 같은 reference test를 모두 통과합니다.
- Debug와 Release에서 계약이 같습니다.
- 지원 환경에서 AddressSanitizer·UndefinedBehaviorSanitizer와 ThreadSanitizer를 통과합니다.
- 각 실습의 실패 조건을 최소 하나씩 의도적으로 재현합니다.
- 소유권, 상태 전이, 실패 표현과 검증 근거를 설명할 수 있습니다.

## 공유 build workspace 권장 구현 순서

이 branch의 실습 프로젝트는 이미 CMake workspace와 compiler 계약을 제공합니다. 실제 project generator, package manager init, dependency install 또는 framework init 명령을 사용하지 않으므로 `Implementation 0`은 두지 않습니다. migration·schema/code generation 같은 중간 CLI도 없으며, CMake configure·build·CTest는 구현 단계가 아니라 build/verification 명령으로 기록합니다.

<!-- implementation-scope: modern-cmake -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `CMakeLists.txt` | C++20 workspace와 platform thread 탐색 경계를 세웁니다. |
| `2` | `CMakeLists.txt` | target이 공유하는 언어·경고·sanitizer 정책을 고정합니다. |
| `3` | `CMakeLists.txt` | 네 실습과 official reference/learner test 등록 경계를 조립합니다. |
| `[Implementation 4]` | `CMakePresets.json` | 주석을 허용하지 않는 preset 파일의 Debug·Release·sanitizer build 계약을 연결합니다. |
<!-- /implementation-scope -->
