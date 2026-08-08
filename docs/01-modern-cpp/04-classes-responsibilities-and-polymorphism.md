# 클래스·책임·다형성

## 목표

class를 필드를 감추는 문법이 아니라 **유효한 상태와 허용된 변경의 경계**로 사용합니다. 상속을 먼저 선택하지 않고 값, composition, template, `variant`와 runtime polymorphism 중 문제에 맞는 수단을 고릅니다.

## 시작하기 전에

[RAII·smart pointer·Rule of Zero](03-raii-smart-pointers-and-rule-of-zero.md)를 완료하고 객체 수명과 자원 소유자를 설명할 수 있어야 합니다.

## 1. class의 첫 책임은 불변식입니다

다음 타입에서 잔액이 음수가 될 수 없다면 모든 변경 경로가 그 규칙을 지켜야 합니다.

```cpp
class Balance
{
public:
    explicit Balance(std::int64_t initial) : amount_(initial)
    {
        if (initial < 0)
            throw std::invalid_argument("negative balance");
    }

    [[nodiscard]] bool withdraw(std::int64_t amount)
    {
        if (amount <= 0 || amount > amount_)
            return false;
        amount_ -= amount;
        return true;
    }

    [[nodiscard]] std::int64_t amount() const noexcept { return amount_; }

private:
    std::int64_t amount_;
};
```

`amount_`를 private로 둔 것만으로 충분하지 않습니다. 생성자와 모든 public 함수가 불변식을 유지해야 합니다.

## 2. 생성이 실패할 수 있는 경우

객체가 생성된 뒤 `valid()`를 매번 확인하게 만들지 않습니다.

```cpp
class Port
{
public:
    explicit Port(std::uint16_t value) : value_(value) {}

private:
    std::uint16_t value_;
};
```

문자열 parsing이 실패할 수 있다면 생성자와 parsing을 분리할 수 있습니다.

```cpp
[[nodiscard]] Result<Port, ParseError> parse_port(std::string_view text); // 다음 문서의 결과 타입
```

성공한 뒤 얻은 `Port`는 항상 유효합니다. 실패는 객체 내부의 반쯤 초기화된 상태가 아니라 결과 타입에 남습니다.

## 3. aggregate와 class를 구분합니다

모든 구조체가 getter·setter를 가져야 하는 것은 아닙니다.

```cpp
struct Point
{
    double x;
    double y;
};
```

필드 사이에 특별한 불변식이 없고 단순한 데이터 전달이 목적이면 aggregate가 명확합니다.

반대로 변경 규칙, 수명 또는 권한이 있다면 class 경계가 필요합니다.

```cpp
class Session
{
public:
    void authenticate(UserId user);
    void close();

private:
    SessionState state_;
};
```

getter와 setter를 기계적으로 추가해 private 필드를 사실상 public으로 만들지 않습니다.

## 4. 책임을 상태와 함께 둡니다

상태를 가진 객체와 상태를 변경하는 규칙이 멀리 떨어지면 caller가 불변식을 기억해야 합니다.

나쁜 구조:

```text
Session은 상태만 저장
SessionService가 모든 변경
Controller도 일부 필드를 직접 변경
Timer callback도 상태를 직접 변경
```

개선된 구조:

```text
Session
├─ 현재 상태 소유
├─ 허용된 상태 전이 검사
└─ 전이 결과 반환

SessionService
├─ 여러 Session 조합
├─ 저장소·시간·외부 의존성 연결
└─ 업무 흐름 조정
```

객체 안에 모든 것을 넣으라는 뜻이 아닙니다. 상태 자체의 규칙과 외부 orchestration을 분리합니다.

## 5. composition이 기본입니다

상속은 “A가 B를 사용한다”가 아니라 “A를 B로 대체할 수 있다”는 계약입니다.

```cpp
class ReportService
{
public:
    ReportService(Clock& clock, ReportStore& store)
        : clock_(clock), store_(store)
    {}

private:
    Clock& clock_;
    ReportStore& store_;
};
```

`ReportService`는 Clock이나 Store가 아닙니다. 두 의존성을 조합합니다.

composition의 장점은 다음입니다.

- 각 객체의 수명과 소유자가 보입니다.
- 테스트에서 작은 대체 구현을 전달할 수 있습니다.
- 상위 타입의 protected 상태에 의존하지 않습니다.
- 기능을 여러 축으로 조합할 수 있습니다.

## 6. dependency injection은 framework가 아닙니다

필요한 의존성을 생성자 또는 함수 parameter로 받으면 됩니다.

```cpp
class FileJournal
{
public:
    explicit FileJournal(std::filesystem::path path);
    void append(const Event& event);
};

class JobRunner
{
public:
    JobRunner(Journal& journal, std::size_t capacity);
};
```

의존성을 전역 singleton에서 가져오면 실제 필요 관계, 초기화 순서와 테스트 격리가 숨겨집니다.

소유권도 함께 결정합니다.

- `T&`: caller가 더 오래 소유합니다.
- `std::unique_ptr<T>`: 객체가 유일하게 소유합니다.
- 값 `T`: 작은 정책 객체를 복사해 소유합니다.
- `std::shared_ptr<T>`: 실제 공유 소유가 필요합니다.

## 7. runtime polymorphism

실행 중 구현을 바꿔야 하고 공통 interface가 안정적이면 virtual dispatch를 사용할 수 있습니다.

```cpp
class Formatter
{
public:
    virtual ~Formatter() = default;
    [[nodiscard]] virtual std::string format(const Job& job) const = 0;
};

class TextFormatter final : public Formatter
{
public:
    [[nodiscard]] std::string format(const Job& job) const override;
};
```

필수 규칙:

- base pointer로 파괴할 수 있으면 virtual destructor가 필요합니다.
- override 함수에는 `override`를 붙입니다.
- base 생성자·소멸자에서 virtual dispatch에 의존하지 않습니다.
- derived가 base의 불변식을 약화시키지 않습니다.
- protected mutable state보다 작고 안정된 public interface를 선호합니다.

## 8. object slicing

```cpp
void print(Formatter formatter); // base 값으로 복사
```

derived 객체를 값으로 전달하면 base 부분만 복사되는 slicing이 발생할 수 있습니다. runtime polymorphism은 reference 또는 pointer 경계를 사용합니다.

```cpp
void print(const Formatter& formatter);
```

polymorphic object를 소유하는 container는 대개 `std::unique_ptr<Base>`를 사용합니다.

```cpp
std::vector<std::unique_ptr<Formatter>> formatters;
```

## 9. `variant` 기반 value polymorphism

가능한 타입 집합이 닫혀 있고 모두 값 의미론을 가질 수 있다면 `std::variant`가 더 단순할 수 있습니다.

```cpp
struct Submit { JobSpec spec; };
struct Cancel { JobId id; };
struct List {};

using Command = std::variant<Submit, Cancel, List>;

template <class... Visitors>
struct Overloaded : Visitors...
{
    using Visitors::operator()...;
};
template <class... Visitors>
Overloaded(Visitors...) -> Overloaded<Visitors...>;

std::visit(
    Overloaded{
        [&](const Submit& command) { submit(command.spec); },
        [&](const Cancel& command) { cancel(command.id); },
        [&](const List&) { list(); },
    },
    command);
```

장점:

- heap allocation과 공유 소유가 필요하지 않을 수 있습니다.
- 가능한 타입 집합이 compiler에 보입니다.
- visitor가 모든 경우를 처리하는지 확인할 수 있습니다.

단점:

- 새 타입을 추가할 때 모든 visitor를 수정합니다.
- 외부 plugin이 타입을 추가하는 열린 확장에는 맞지 않습니다.

## 10. static polymorphism과 concepts

template은 caller 타입에 맞춰 compile-time으로 코드를 생성합니다.

```cpp
template <typename Sink>
concept EventSink = requires(Sink sink, const Event& event)
{
    { sink.append(event) } -> std::same_as<void>;
};

template <EventSink Sink>
void replay(Sink& sink, std::span<const Event> events)
{
    for (const Event& event : events)
        sink.append(event);
}
```

runtime 교체가 필요 없고 성능·인라인 또는 값 조합이 중요한 경우 적합합니다. 그러나 implementation이 header에 노출되고 compile 시간이 늘며 binary가 커질 수 있습니다.

## 11. 어느 다형성을 선택할 것인가

| 조건 | 우선 선택 |
|---|---|
| 작은 데이터와 일반 연산 | 값 타입 |
| 다른 객체 기능을 사용 | composition |
| 타입 집합이 닫혀 있음 | `variant` |
| 외부 구현 추가와 runtime 교체 | virtual interface |
| compile-time 조합과 제약 | template + concept |

“다형성 문제이므로 상속”이라는 자동 선택을 피합니다.

## 12. interface를 작게 유지합니다

큰 interface는 구현마다 필요 없는 함수와 상태를 강제합니다.

```cpp
class Repository
{
public:
    virtual ~Repository() = default;
    virtual void save(const Job&) = 0;
    virtual std::optional<Job> find(JobId) = 0;
};
```

읽기만 필요한 caller에는 더 작은 view를 줄 수 있습니다.

```cpp
class JobReader
{
public:
    virtual ~JobReader() = default;
    virtual std::optional<Job> find(JobId) const = 0;
};
```

interface 분리는 변경 권한을 줄이고 test double을 단순하게 합니다.

## 13. Pimpl은 필요할 때 사용합니다

Pimpl(pointer to implementation)은 공개 헤더에서 구현 의존성을 숨기고 ABI 경계를 안정화할 수 있습니다.

```cpp
class Client
{
public:
    Client();
    ~Client();

    Client(Client&&) noexcept;
    Client& operator=(Client&&) noexcept;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};
```

하지만 heap allocation, 간접 호출과 boilerplate가 생깁니다. 작은 내부 애플리케이션에 무조건 적용하지 않습니다.

## 연결 실습

[로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)의 상태와 책임을 먼저 그림으로 작성합니다.

```text
JobRunner
├─ worker thread 수명 소유
├─ queue와 record 동기화
├─ submit·cancel·stop 상태 전이
└─ journal 호출 순서

Record
├─ JobSnapshot 값
├─ Work callable
└─ per-job stop_source
```

다음 대안을 비교합니다.

- 모든 상태를 public struct로 두고 caller가 변경
- `JobRunner`가 상태 전이를 독점
- Work를 virtual class hierarchy로 표현
- Work를 `std::function` 값으로 표현

현재 과제는 동작 집합이 단순하고 caller lambda를 받을 수 있으므로 `std::function`을 선택합니다. plugin 수명과 복잡한 다형적 상태가 필요해지면 다른 경계가 적절할 수 있습니다.

## 자주 발생하는 실패

- 모든 class에 getter와 setter를 추가합니다.
- “재사용”을 이유로 상태 상속 계층을 깊게 만듭니다.
- base destructor를 virtual로 만들지 않고 base pointer로 파괴합니다.
- `shared_ptr`로 책임 배치를 대신합니다.
- service locator와 singleton으로 의존성을 숨깁니다.
- interface가 저장·조회·네트워크·log를 모두 담당합니다.

## 완료 기준

- aggregate와 invariant class를 구분합니다.
- 상태 변경 책임과 외부 orchestration을 나눕니다.
- composition을 기본으로 선택합니다.
- virtual, `variant`, template polymorphism의 적용 조건을 설명합니다.
- object slicing과 virtual destructor 실패를 재현합니다.

## 다음 문서

[오류·optional·variant·expected](05-errors-optional-variant-and-expected.md)에서 constructor, method와 시스템 경계가 실패를 어떤 타입으로 표현할지 결정합니다.
