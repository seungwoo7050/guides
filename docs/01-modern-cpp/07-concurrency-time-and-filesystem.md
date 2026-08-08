# 동시성·시간·filesystem

## 목표

여러 실행 흐름이 같은 상태를 사용할 때 데이터 race를 제거하고, 종료 가능한 worker를 설계합니다. 시간과 파일 시스템을 단순 값처럼 다루지 않고 각각의 실패·변경 모델을 API에 반영합니다.

이 문서의 중심은 thread를 많이 만드는 것이 아니라 다음 계약을 닫는 것입니다.

- 공유 상태를 누가 소유하는가
- 어떤 불변식을 어느 mutex가 보호하는가
- wait가 어떤 predicate를 기다리는가
- 종료 요청이 어디까지 전달되는가
- timeout이 어느 clock을 사용하는가
- 파일 변경이 중간 실패 뒤 어떤 상태를 남기는가

## 시작하기 전에

[알고리즘·ranges·templates·concepts](06-algorithms-ranges-templates-and-concepts.md)를 완료하고 container의 변경·무효화 규칙을 설명할 수 있어야 합니다.

## 1. data race와 논리 race

data race는 한 thread가 메모리에 쓰는 동안 다른 thread가 동기화 없이 같은 위치를 읽거나 쓰는 경우 발생할 수 있습니다. C++에서는 data race가 undefined behavior입니다.

```cpp
int counter = 0;

// 여러 thread에서 동기화 없이 실행
++counter;
```

`++counter`는 하나의 원자적 동작이 아닐 수 있습니다.

논리 race는 data race가 없어도 발생합니다.

```text
thread A: 잔액 확인 100
thread B: 잔액 확인 100
thread A: 80 출금
thread B: 80 출금
```

각 read/write가 mutex로 안전해도 “확인 후 변경” 전체가 하나의 임계 구역이 아니면 불변식이 깨집니다. mutex는 변수 하나가 아니라 **불변식 변경 단위**를 보호해야 합니다.

## 2. mutex와 lock 범위

```cpp
class Counter
{
public:
    void increment()
    {
        std::lock_guard lock{mutex_};
        ++value_;
    }

    [[nodiscard]] int value() const
    {
        std::lock_guard lock{mutex_};
        return value_;
    }

private:
    mutable std::mutex mutex_;
    int value_{0};
};
```

lock을 잡은 상태에서 다음을 오래 수행하지 않습니다.

- 외부 callback
- 느린 filesystem I/O
- network I/O
- 다른 component의 알 수 없는 함수

다만 lock을 너무 일찍 풀어 불변식 변경이 분리되어도 안 됩니다. 일반적인 흐름은 다음입니다.

```text
lock
→ 공유 상태 검사·예약
→ 필요한 지역 복사 생성
→ unlock
→ 외부 작업
→ lock
→ 결과 commit
→ unlock
```

중간에 다른 thread가 상태를 바꿀 수 있으므로 예약 token, version 또는 상태 전이가 필요할 수 있습니다.

## 3. 여러 mutex와 lock 순서

서로 다른 순서로 두 mutex를 잡으면 deadlock이 발생할 수 있습니다.

```text
thread A: left lock → right 대기
thread B: right lock → left 대기
```

가능하면 하나의 불변식을 하나의 mutex 아래에 둡니다. 여러 mutex가 필요하면 전역 순서를 정하거나 `std::scoped_lock`을 사용합니다.

```cpp
std::scoped_lock lock{left_mutex, right_mutex};
```

lock 구조가 복잡해질수록 상태 소유 경계를 다시 검토합니다.

## 4. atomic의 범위

단순 counter·flag 하나는 `std::atomic`으로 표현할 수 있습니다.

```cpp
std::atomic<bool> stopping{false};
```

하지만 여러 필드의 관계를 atomic 변수 여러 개로 나누면 일관된 snapshot을 얻기 어렵습니다.

```text
status = succeeded
output = 아직 빈 문자열
```

두 필드가 함께 바뀌어야 한다면 하나의 mutex로 보호하는 편이 단순합니다. memory order를 직접 선택해야 하는 lock-free 설계는 측정된 필요와 전문 검증 없이 기본값으로 삼지 않습니다.

## 5. condition variable은 predicate를 기다립니다

```cpp
std::unique_lock lock{mutex_};
changed_.wait(lock, [this] {
    return !queue_.empty() || stopping_;
});
```

condition variable은 “알림 한 번”을 소비하는 event가 아닙니다. spurious wakeup이 있을 수 있고, 알림 전에 상태가 바뀔 수 있으므로 항상 공유 상태 predicate를 다시 검사합니다.

잘못된 구조:

```cpp
changed_.wait(lock);
use(queue_.front());
```

올바른 질문은 “notify를 받았는가”가 아니라 “진행 조건이 참인가”입니다.

## 6. `jthread`와 thread 수명

`std::thread`는 joinable 상태로 파괴하면 프로그램을 종료시킵니다. `std::jthread`는 파괴 시 stop을 요청하고 join합니다.

```cpp
class Worker
{
public:
    Worker()
        : thread_([this](std::stop_token token) { run(token); })
    {}

private:
    void run(std::stop_token token);
    std::jthread thread_;
};
```

`jthread`가 모든 종료 문제를 해결하지는 않습니다.

- 작업이 stop token을 관찰해야 합니다.
- blocking API가 token을 지원하지 않을 수 있습니다.
- 공유 상태의 종료 순서를 정해야 합니다.
- member 파괴 순서상 thread가 먼저 끝나야 합니다.

thread member는 자신이 접근하는 상태보다 나중에 선언되어 먼저 파괴되도록 배치하거나, destructor에서 명시적으로 stop·join 순서를 닫습니다.

## 7. `stop_token`은 협력적 취소입니다

```cpp
std::string work(std::stop_token token)
{
    while (!token.stop_requested())
    {
        if (one_step_completed())
            return "done";
    }
    return "cancelled";
}
```

취소 요청은 thread를 강제로 중단하지 않습니다. 작업은 안전한 경계에서 요청을 관찰하고 자신의 자원을 정리한 뒤 반환합니다.

stop-aware wait를 사용할 수 있습니다.

```cpp
std::condition_variable_any changed;
std::unique_lock lock{mutex};
changed.wait(lock, token, [&] { return ready; });
```

callback 등록이 필요하면 `std::stop_callback`을 사용할 수 있지만 callback 수명과 lock 재진입을 주의합니다.

## 8. bounded queue와 backpressure

무한 queue는 메모리만 늘리고 지연을 숨깁니다. 생산 속도가 소비 속도보다 빠르면 시스템이 어떤 행동을 할지 정합니다.

- 즉시 거부
- 일정 시간 대기
- 오래된 항목 제거
- 우선순위별 제한
- caller에게 재시도 시점 제공

```cpp
enum class SubmitError
{
    stopped,
    queue_full,
    empty_name,
    empty_work
};
```

queue capacity가 무엇을 세는지 명확히 합니다.

```text
대기 중 항목만 제한하는가
실행 중 항목까지 포함하는가
항목 수인가 byte 수인가
```

실습의 `JobRunner`는 **대기 중 작업 수**를 제한합니다. 실행 중 하나와 대기 중 하나가 있을 때 capacity 1은 가득 찬 상태입니다.

## 9. 상태 전이와 terminal 상태

동시 객체는 boolean 여러 개보다 명시적 상태가 낫습니다.

```text
queued → running → succeeded
                 → failed
                 → cancelled
queued ─────────→ cancelled
```

terminal 상태가 다시 running으로 돌아가면 안 됩니다. 상태와 output·error를 같은 mutex 아래에서 갱신해 caller가 모순된 snapshot을 보지 않게 합니다.

## 10. time point와 duration

시간 간격은 `std::chrono::duration`으로 표현합니다.

```cpp
using namespace std::chrono_literals;
auto timeout = 500ms;
```

단위가 타입에 포함되므로 초와 밀리초를 정수로 섞는 실수를 줄입니다.

### `steady_clock`

경과 시간과 timeout에 사용합니다. 시스템 시각 조정에 따라 역행하지 않는 monotonic clock입니다.

```cpp
const auto deadline = std::chrono::steady_clock::now() + 2s;
```

### `system_clock`

사용자에게 표시할 wall-clock 시각과 외부 timestamp에 사용합니다. NTP·관리자 변경으로 점프할 수 있으므로 timeout 계산의 기본으로 삼지 않습니다.

## 11. timeout은 deadline으로 전달합니다

하위 함수마다 같은 duration을 다시 주면 전체 시간이 늘어날 수 있습니다.

```text
상위 timeout 2초
├─ step A 최대 2초
├─ step B 최대 2초
└─ step C 최대 2초
```

전체 budget을 지키려면 deadline을 만들고 남은 시간을 계산합니다.

```cpp
const auto remaining = deadline - std::chrono::steady_clock::now();
```

남은 시간이 0 이하라면 새 작업을 시작하지 않습니다.

## 12. filesystem path와 오류

문자열 덧셈으로 경로를 만들지 않습니다.

```cpp
std::filesystem::path root{"data"};
auto file = root / "jobs.tsv";
```

filesystem 작업은 다음 이유로 실패할 수 있습니다.

- 경로 없음
- 권한 부족
- 같은 이름의 다른 타입 존재
- disk full
- 읽기 전용 filesystem
- 다른 process의 동시 변경
- symlink와 경로 정규화 문제

exception overload 또는 `error_code` overload를 의도적으로 선택합니다.

```cpp
std::error_code error;
std::filesystem::create_directories(root, error);
if (error)
{
    // caller가 실패를 값으로 처리
}
```

## 13. 파일 교체와 crash 경계

설정 또는 snapshot을 갱신할 때 대상 파일을 직접 truncate한 뒤 쓰면 중간 실패로 빈 파일이 남을 수 있습니다.

일반적인 단일 filesystem 전략:

```text
같은 디렉터리에 temporary 파일 작성
→ flush와 close 확인
→ 필요하면 fsync 정책 적용
→ rename으로 교체
```

`rename`의 원자성·내구성은 운영체제와 filesystem 조건에 따라 다릅니다. “함수 호출이 성공했다”와 “전원 손실 뒤 영구 보존된다”를 구분합니다.

실습 journal은 append-only 관찰 기록이며 crash-safe queue를 약속하지 않습니다. 생성 뒤 append가 실패해도 worker를 종료시키지 않고 health 값을 낮추는 정책을 사용합니다. 이 제한을 명시하는 것이 거짓 내구성 주장을 하는 것보다 낫습니다.

## 14. callback과 lock

사용자가 제공한 `Work` callback을 mutex 아래에서 실행하지 않습니다.

```text
lock
→ record를 running으로 전이
→ callback과 token을 지역 변수로 확보
→ unlock
→ callback 실행
→ lock
→ terminal 결과 commit
```

callback이 오래 걸리거나 다시 `JobRunner`를 호출해도 내부 mutex를 영구 점유하지 않습니다. 다만 record 수명은 callback 실행 중 유지되어야 합니다.

실습은 상태 전이와 journal 행의 순서를 단순하게 맞추기 위해 짧은 append·flush를 상태 mutex 아래에서 수행합니다. 따라서 느린 저장 장치는 submit·snapshot을 지연시킬 수 있습니다. 생산 환경에서 journal writer를 별도 queue로 분리한다면 상태 commit과 기록 완료 사이의 일관성, queue 포화와 종료 순서를 새 계약으로 정의해야 합니다.

## 15. 종료 순서

서비스 객체의 종료는 다음 순서가 명확해야 합니다.

```text
새 제출 거부
→ 대기 작업 취소 또는 drain
→ 실행 작업에 stop 요청
→ wait 깨우기
→ worker 종료·join
→ journal·상태 자원 파괴
```

`stop`을 여러 번 호출해도 안전하도록 idempotent하게 만들고, 여러 외부 호출은 하나의 join으로 수렴시킵니다. Work callback에서 stop을 호출하면 self-join을 피하고 이후 외부 stop 또는 destructor가 join합니다. destructor만이 아니라 명시적 stop에서도 같은 상태 전이 계약을 사용합니다.

## 연결 실습

[로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)를 단계별로 구현합니다.

특히 다음 테스트는 `sleep` 없이 사건을 동기화합니다.

- 첫 작업이 실제 running 상태에 들어감
- 두 번째 작업이 queue에 대기함
- 세 번째 제출이 capacity 때문에 거부됨
- stop 요청이 실행 작업에 전달됨
- 외부 stop이 worker 종료를 기다림
- callback 내부 stop이 self-join 없이 끝남
- terminal 상태가 condition variable로 관찰됨

## 실패 실험

- predicate 없이 condition variable을 기다립니다.
- callback을 mutex 아래에서 실행합니다.
- unbounded queue로 바꾸고 producer를 빠르게 반복합니다.
- 취소 시 running 상태를 즉시 cancelled로 표시하지만 callback은 계속 공유 상태를 변경하게 둡니다.
- timeout에 `system_clock`을 사용하고 시각 변화 영향을 생각합니다.
- target 파일을 먼저 truncate하고 중간에 예외를 던집니다.

## 완료 기준

- data race와 논리 race를 구분합니다.
- mutex가 보호하는 불변식을 문서화합니다.
- condition variable predicate와 stop-aware wait를 구현합니다.
- bounded queue의 capacity 의미를 설명합니다.
- `steady_clock`과 `system_clock`을 목적에 따라 선택합니다.
- filesystem 실패와 crash 내구성의 한계를 구분합니다.
- 종료 순서가 모든 thread와 자원의 수명을 닫습니다.

## 다음 문서

[테스트·디버깅·도구](08-testing-debugging-and-tooling.md)에서 동시성·수명·filesystem 계약이 실제로 지켜지는지 재현 가능한 근거를 만듭니다.
