# Modern C++ application capstone: 로컬 작업 실행기

## 목표

빈 디렉터리에서 다음 능력을 하나의 작은 시스템으로 통합합니다.

- target 기반 CMake
- 강한 값 타입
- 값·비소유 view·자원 소유자 구분
- Rule of Zero와 이동 전용 경계
- result·optional·예외 경계
- algorithms·ranges·concepts
- `jthread`, stop token과 bounded queue
- chrono와 filesystem
- CTest, sanitizer와 결정적 동시성 test

완성 코드의 기능 수보다 상태·소유권·실패·검증 계약을 닫는 것이 목적입니다.

## 시작하기 전에

Modern C++ 01–08 문서와 다음 실습을 완료합니다.

- [강한 타입과 CMake](../../exercises/01-modern-cpp/01-strong-types-and-cmake/README.md)
- [이동 전용 파일 소유자](../../exercises/01-modern-cpp/02-unique-file/README.md)
- [조회 파이프라인](../../exercises/01-modern-cpp/03-query-pipeline/README.md)

최종 과제는 [로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)입니다.

## 1. 문제 경계

프로세스 안에서 이름과 작업 함수를 제출하면 하나의 worker가 순서대로 실행합니다. caller는 작업 ID를 받고 상태를 조회하거나 취소할 수 있습니다. 모든 상태 전이는 파일 journal에 append를 시도하며, 기록 실패는 별도 health 상태로 드러냅니다.

지원하는 범위:

```text
submit
snapshot
wait_for_terminal
cancel
stop
append-only journal
```

지원하지 않는 범위:

```text
process crash 뒤 작업 재실행
여러 worker와 우선순위
분산 queue
프로세스 간 동기화
강제 thread 종료
terminal record 자동 삭제·보존 기간 정책
JobId overflow 처리
fsync 기반 내구성 보장
```

비지원 범위를 명시해야 구현이 실제보다 강한 보장을 한다고 오해하지 않습니다.

## 2. 공개 모델

### `JobId`

정수와 암묵적으로 섞이지 않는 값 타입입니다.

```cpp
class JobId
{
public:
    explicit JobId(std::uint64_t value);
    auto operator<=>(const JobId&) const = default;
};
```

### `JobStatus`

```text
queued
running
succeeded
failed
cancelled
```

boolean `done`, `failed`, `cancelled`를 따로 두지 않습니다. 서로 모순되는 조합을 만들 수 있기 때문입니다.

### `SubmitResult`

```text
성공: JobId
실패: empty_name | empty_work | queue_full | stopped
```

정상적인 backpressure와 종료 거부는 예외가 아니라 값으로 반환합니다.

### `JobSnapshot`

caller는 내부 `Record&`를 받지 않고 값을 복사받습니다. lock 밖에서 안전하게 읽을 수 있으며 내부 수명을 노출하지 않습니다.

## 3. 상태와 소유권 표

| 상태·자원 | 소유자 | 보호·종료 계약 |
|---|---|---|
| worker thread | `JobRunner` | `jthread`, stop 후 join |
| queue | `JobRunner` | `mutex_` 아래 변경 |
| record map | `JobRunner` | terminal 뒤에도 snapshot 조회를 위해 유지하며, 기본 과제에는 자동 정리 정책이 없음 |
| Work callable | 각 `Record` | worker가 record 수명 안에서 호출 |
| per-job cancellation | 각 `Record` | `stop_source`가 token 발급 |
| journal path | `JobRunner` 값 | 생성 시 쓰기 가능성 확인 |
| journal stream | append 호출의 지역 RAII 객체 | 상태 mutex 아래 각 전이 후 소멸·flush; 느린 I/O가 상태 API를 지연시킬 수 있음 |
| journal health | `JobRunner` boolean | runtime append 실패를 관찰 가능하게 유지 |

이 표에서 소유자가 두 개 이상인 항목이 있다면 `shared_ptr`를 추가하기 전에 구조를 다시 검토합니다.

## 4. 상태 전이

```text
submit 성공
    ↓
 queued ───────────────→ cancelled
    ↓ worker dequeue
 running ──────────────→ cancelled
    ├──────────────────→ succeeded
    └──────────────────→ failed
```

규칙:

- terminal 상태는 다시 변하지 않습니다.
- queued 취소는 queue에서 제거하고 즉시 terminal로 만듭니다.
- running 취소는 stop을 요청하며 작업이 관찰한 뒤 terminal이 됩니다.
- `cancel`은 이 호출이 queued 상태를 바꾸거나 첫 stop 요청을 발행했을 때만 true를 반환합니다.
- 정상 반환과 취소 요청이 경합하면 terminal commit 직전 token을 다시 확인해 cancellation이 성공으로 덮이지 않게 합니다.
- callable exception은 worker 경계에서 failed로 번역합니다.
- snapshot의 status·output·error는 같은 lock 아래 commit합니다.
- submit은 record와 queue 설치가 모두 성공한 뒤 journal을 기록하며, 중간 allocation 실패에는 설치한 state를 rollback합니다.

## 5. lock 경계

worker는 다음 순서를 사용합니다.

```text
lock
→ predicate wait
→ queue에서 ID 제거
→ record를 running으로 전이
→ journal 기록
→ stable record pointer 확보
→ unlock

Work 실행

lock
→ succeeded | failed | cancelled 결과 commit
→ journal 기록
→ unlock
→ terminal waiters notify
```

외부 Work를 lock 아래에서 호출하지 않습니다. 그렇지 않으면 긴 작업이 submit·snapshot·cancel을 모두 막고 callback 재진입이 deadlock을 만들 수 있습니다.

## 6. bounded queue

capacity는 대기 중인 `queue_` 크기를 제한합니다.

예:

```text
capacity = 1
running = 1
queued = 1
새 submit = queue_full
```

실행 중 작업을 capacity에 포함하는 설계도 가능하지만 의미가 다릅니다. API와 test가 어느 정의를 사용하는지 일치해야 합니다.

## 7. 취소 계약

C++은 임의의 thread를 안전하게 강제 종료하는 일반 기능을 제공하지 않습니다. Work는 `std::stop_token`을 받습니다.

```cpp
using Work = std::function<std::string(std::stop_token)>;
```

`cancel()` 호출은 stop 요청을 발행한 뒤 반환할 수 있지만, 작업이 token을 무시하면 terminal 취소 전이는 늦어집니다. 외부 thread에서 호출한 `stop()`과 소멸자는 worker join을 기다리므로, Work가 영원히 반환하지 않으면 함께 끝나지 않습니다. 이 한계는 bug가 아니라 협력적 취소 계약입니다. blocking I/O를 취소하려면 해당 API의 timeout·취소 기능을 별도로 연결해야 합니다.

## 8. 오류 경계

| 실패 | 표현 | 이유 |
|---|---|---|
| 빈 이름 | `SubmitError::empty_name` | caller가 수정 가능한 예상 거부 |
| 빈 callable | `SubmitError::empty_work` | 실행 불가능한 제출을 별도 거부 |
| queue full | `SubmitError::queue_full` | backpressure 정상 분기 |
| stop 뒤 submit | `SubmitError::stopped` | 수명 상태 분기 |
| 없는 ID 조회 | `optional` 없음 | 정상적인 부재 |
| Work 표준 예외 | failed snapshot + message | worker thread 보호 |
| Work 알 수 없는 예외 | failed + 고정 메시지 | process 종료 방지 |
| journal 생성 불가 | constructor 예외 | 객체 자체를 유효하게 만들 수 없음 |
| 생성 뒤 journal append 실패 | `journal_healthy() == false` | worker를 죽이지 않고 관측 경계를 열어 둠 |

오류 문자열로 queue full과 I/O 실패를 모두 표현하지 않습니다.

## 9. journal 계약

형식:

```text
<id>\t<status>\t<name>\t<message>\n
```

name과 message의 tab·줄바꿈은 공백으로 정규화합니다. 한 줄이 하나의 상태 전이를 나타냅니다.

예:

```text
1 queued complete
1 running complete
1 succeeded complete done
```

실제 파일은 tab으로 구분됩니다.

생성자는 처음부터 journal을 열 수 없으면 실패합니다. 생성 뒤 디렉터리 삭제나 디스크 오류로 append가 실패하면 작업 상태 전이는 계속 진행하고 `journal_healthy()`가 false가 됩니다. 감사 기록과 작업 실행 중 어느 쪽을 우선할지 명시한 선택이며, durable queue를 구현한다면 다른 정책이 필요합니다.

기본 과제는 결정적인 전이 순서를 위해 journal I/O를 상태 mutex 아래에서 수행합니다. 이는 단순성의 대가로 느린 디스크가 상태 API를 지연시킬 수 있다는 뜻입니다. 별도 writer thread로 확장할 때는 기록 queue의 backpressure와 종료·flush 순서를 새로 검증해야 합니다.

journal의 목적은 다음입니다.

- 상태 전이 관찰
- 실패 test 근거
- 수명·종료 순서 확인

목적이 아닌 것:

- restart recovery
- exactly-once 실행
- 전원 손실 뒤 내구성 보장

## 10. 단계별 작업

### 단계 1. 값 모델과 결과

[spec 01](../../exercises/01-modern-cpp/04-local-job-runner/specs/01-model-and-result.md)

- 강한 `JobId`
- 닫힌 상태 enum
- `Result<JobId, SubmitError>`
- 값 snapshot

### 단계 2. bounded queue와 상태

[spec 02](../../exercises/01-modern-cpp/04-local-job-runner/specs/02-bounded-queue-and-state.md)

- queue capacity
- record map
- queued·running·terminal 전이
- snapshot과 wait predicate

### 단계 3. thread와 취소

[spec 03](../../exercises/01-modern-cpp/04-local-job-runner/specs/03-jthread-and-cancellation.md)

- `jthread` 수명
- stop-aware worker wait
- per-job stop source
- queued와 running 취소 차이

### 단계 4. 예외·journal·종료

[spec 04](../../exercises/01-modern-cpp/04-local-job-runner/specs/04-errors-journal-and-shutdown.md)

- callable exception translation
- append-only journal
- idempotent stop과 동시 stop 수렴
- 외부 stop의 worker join, callback 내부 stop의 self-join 회피
- runtime journal 장애 health
- terminal notification

각 단계 종료 시 다음을 남깁니다.

```text
구현한 계약
추가한 test
의도적으로 재현한 실패
상태·소유권 변경
아직 보장하지 않는 범위
```

## 11. 검증 계획

### build

```sh
make modern-skeleton-build
```

모든 TODO 구현이 끝나지 않았어도 public API와 target graph는 컴파일되어야 합니다.

### reference test와 실행 파일

```sh
make modern-test
cmake --build exercises/01-modern-cpp/build/debug \
  --target local_job_runner_reference_app
./exercises/01-modern-cpp/build/debug/04-local-job-runner/local_job_runner_reference_app \
  "${TMPDIR:-/tmp}/guide-cpp-jobs-$$.tsv"
```

CTest는 API 계약 테스트와 CLI smoke test를 함께 실행합니다.

확인 항목:

- 정상 완료
- 표준·비표준 callable 예외와 worker 생존
- 결정적인 queue full
- queued 취소 뒤 capacity 회수
- running 취소
- 빈 callable 거부와 stop 뒤 submit 거부
- 없는 ID wait의 즉시 실패
- runtime journal 실패 뒤 작업 지속과 health 저하
- stop의 동기 join과 callback 재진입
- journal 상태 행

### sanitizer

```sh
make modern-sanitize
make modern-thread-sanitize
```

첫 명령은 memory·UB 오류를, 둘째 명령은 지원 compiler에서 data race를 확인합니다. sanitizer는 정상 test를 대체하지 않으며 서로 다른 sanitizer 조합은 별도 build directory에서 실행합니다.

### skeleton 완료

skeleton test executable을 직접 실행합니다.

```sh
./exercises/01-modern-cpp/build/debug/04-local-job-runner/local_job_runner_skeleton_tests
```

출발점에서는 실패하고, 구현 완료 뒤 통과해야 합니다.

## 12. 실패를 재현하는 순서

### queue full

```text
blocking job 제출
→ promise로 running 확인
→ 두 번째 job queue에 제출
→ 세 번째 submit
→ queue_full 확인
→ blocking job 해제
```

`sleep`으로 running을 추측하지 않습니다.

### running 취소

```text
stop-aware wait를 수행하는 job 제출
→ 시작 promise 확인
→ cancel
→ token으로 wait 해제
→ cancelled terminal 확인
```

### worker 예외

```text
runtime_error를 던지는 Work 제출
→ wait_for_terminal
→ worker는 살아 있음
→ snapshot failed와 메시지 확인
→ 다음 정상 작업도 실행 가능
```

## 13. 설계 검토 질문

- `JobRunner` 파괴 중 worker가 이미 파괴된 member를 읽을 수 있는가
- `cancel`과 worker 완료가 동시에 일어날 때 terminal 상태가 두 번 기록되는가
- queue에서 제거한 ID의 record 수명이 유지되는가
- callback이 `JobRunner`를 재호출해도 deadlock이 없는가
- journal 실패가 상태 commit과 어떤 관계인가
- stop을 두 번 또는 여러 thread에서 동시에 호출하면 하나의 join으로 수렴하는가
- Work callback이 stop을 호출해도 self-join이 발생하지 않는가
- `wait_for_terminal`이 존재하지 않는 ID를 즉시 거부하는가
- Work가 stop token을 무시할 때 외부 `stop()`이 기다린다는 한계가 문서와 일치하는가
- terminal record를 계속 보존할 때 장기 실행 프로세스의 메모리 정책은 무엇인가

reference는 학습 범위 안의 선택 하나를 보여 줍니다. 다른 선택이 가능하지만 계약과 test가 함께 바뀌어야 합니다.

## 14. 합리적인 확장

기본 과제를 완료한 뒤 하나씩 추가합니다.

### 여러 worker

- worker 수 parameter
- queue와 record 동기화 유지
- 동일 ID 중복 실행 금지
- 종료와 join 전체 관리

### priority queue

- 우선순위와 FIFO tie-breaker
- starvation 정책
- capacity 의미 유지

### restart recovery

- spec와 상태를 durable format으로 저장
- running 상태의 불확실성 처리
- replay와 중복 실행 정책
- atomic replace·fsync 범위

### deadline

- 각 JobSpec에 `steady_clock::time_point`
- queue 대기 중 만료
- 실행 작업에 남은 budget 전달

한 번에 모두 추가하지 않습니다. 각 확장은 새로운 실패 조건과 검증 비용을 가집니다.

## 연결 실습

[로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)의 skeleton을 단계별 spec에 따라 구현합니다. reference는 모든 검사 통과 뒤 상태·오류·join 정책을 비교하는 용도로만 사용합니다.

## 완료 기준

### 기능

- 정상 작업, 실패 작업과 취소 작업을 처리합니다.
- bounded queue가 결정적으로 거부합니다.
- stop 뒤 새 작업을 받지 않습니다.
- 정상 상태 전이가 journal에 남고 runtime journal 장애가 health로 드러납니다.

### 설계

- 값·소유자·비소유자를 구분합니다.
- 상태와 output을 하나의 lock 아래 commit합니다.
- thread 수명, 동시 stop 수렴과 self-join 회피를 포함해 종료 순서를 닫습니다.
- 실패 표현을 의미별로 구분합니다.

### 검증

- reference와 완성 skeleton test가 통과합니다.
- ASan·UBSan과 지원 환경의 TSan이 통과합니다.
- 동시성 test에 임의 sleep이 없습니다.
- 비지원 범위와 내구성 한계를 설명합니다.

이 기준을 만족하면 Modern C++ 일반 과정을 마친 것입니다. 다음 프로젝트에서는 모든 언어 기능을 다시 공부하기보다, 필요한 domain 지식을 구현 과정에서 추가할 수 있습니다.
