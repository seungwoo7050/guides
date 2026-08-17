# 클래스·책임·다형성

## 목표

클래스를 단순히 필드를 숨기는 문법이 아니라 **유효한 상태와 허용된 변경을 정의하는 경계**로 사용합니다. 상속을 먼저 선택하지 않고 값, 합성(composition), 템플릿, `variant`, 런타임 다형성 중 문제에 맞는 수단을 고릅니다.

## 시작하기 전에

[RAII·스마트 포인터·Rule of Zero](03-raii-smart-pointers-and-rule-of-zero.md)를 완료하고 객체 수명과 자원 소유자를 설명할 수 있어야 합니다.

## 1. 클래스의 첫 번째 책임은 불변식 유지입니다

다음 타입에서 잔액이 음수가 될 수 없다면 생성과 모든 변경 경로가 이 규칙을 지켜야 합니다.

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

`amount_`를 `private`으로 선언하는 것만으로는 충분하지 않습니다. 생성자와 모든 공개 함수가 불변식을 유지해야 합니다.

## 2. 생성 과정이 실패할 수 있는 경우

객체를 먼저 만든 뒤 모든 사용 지점에서 `valid()`를 확인하게 만들지 않습니다.

```cpp
class Port
{
public:
    explicit Port(std::uint16_t value) : value_(value) {}

private:
    std::uint16_t value_;
};
```

문자열 파싱처럼 실패할 수 있는 과정은 값 객체의 생성과 분리할 수 있습니다.

```cpp
[[nodiscard]] Result<Port, ParseError> parse_port(std::string_view text); // 다음 문서의 결과 타입
```

파싱에 성공해 얻은 `Port`는 항상 유효합니다. 실패 정보는 반쯤 초기화된 객체가 아니라 결과 타입에 담습니다.

## 3. 단순 데이터와 불변식을 가진 클래스를 구분합니다

모든 `struct`에 getter와 setter를 추가할 필요는 없습니다.

```cpp
struct Point
{
    double x;
    double y;
};
```

필드 사이에 별도 불변식이 없고 단순한 데이터 전달이 목적이라면 공개 멤버를 가진 집합체가 더 명확할 수 있습니다.

반대로 상태 변경 규칙, 수명, 권한을 관리해야 한다면 클래스 경계가 필요합니다.

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

getter와 setter를 기계적으로 추가해 `private` 필드를 사실상 공개 상태로 만들지 않습니다.

## 4. 상태와 그 상태를 바꾸는 규칙을 함께 둡니다

상태를 소유한 객체와 변경 규칙이 멀리 떨어져 있으면 각 호출자가 불변식을 직접 기억해야 합니다.

문제가 있는 구조:

```text
Session은 상태만 저장
SessionService가 모든 변경 수행
Controller도 일부 필드를 직접 변경
Timer 콜백도 상태를 직접 변경
```

책임을 나눈 구조:

```text
Session
├─ 현재 상태 소유
├─ 허용된 상태 전이 검사
└─ 전이 결과 반환

SessionService
├─ 여러 Session 조합
├─ 저장소·시간·외부 의존성 연결
└─ 애플리케이션 흐름 조정
```

모든 로직을 하나의 객체에 넣으라는 뜻은 아닙니다. 개별 상태의 규칙과 여러 객체를 조율하는 애플리케이션 로직을 분리합니다.

## 5. 합성을 기본으로 고려합니다

상속은 단순히 “A가 B를 사용한다”는 관계가 아니라, 파생 타입을 기반 타입으로 대체해도 기반 타입의 계약이 유지되어야 한다는 관계입니다.

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

`ReportService`는 `Clock`이나 `ReportStore`의 한 종류가 아닙니다. 두 의존성을 조합해 기능을 구성합니다.

합성의 장점은 다음과 같습니다.

- 각 객체의 수명과 소유 관계를 드러낼 수 있습니다.
- 적절한 인터페이스를 사용하면 테스트에서 작은 대체 구현을 주입할 수 있습니다.
- 기반 클래스의 `protected` 상태에 결합되지 않습니다.
- 서로 독립적인 기능 축을 조합하기 쉽습니다.

## 6. 의존성 주입은 프레임워크가 아닙니다

객체가 필요한 의존성을 생성자나 함수 매개변수로 받는 것부터 시작합니다.

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

의존성을 전역 싱글턴에서 가져오면 실제 의존 관계, 초기화 순서, 테스트 격리가 코드에서 드러나지 않습니다.

의존성을 전달할 때는 소유권도 함께 결정합니다.

- `T&`: 호출 측이 객체를 더 오래 소유합니다.
- `std::unique_ptr<T>`: 받는 객체가 유일 소유권을 인수합니다.
- 값 `T`: 작은 정책 객체를 복사하거나 이동해 직접 소유합니다.
- `std::shared_ptr<T>`: 여러 객체가 실제로 수명을 공유해야 할 때 사용합니다.

## 7. 런타임 다형성

실행 중 구현을 교체해야 하고 공통 인터페이스가 안정적이라면 가상 함수 디스패치를 사용할 수 있습니다.

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

다음 규칙을 지킵니다.

- 기반 클래스 포인터나 참조를 통해 객체를 소멸할 수 있다면 기반 소멸자는 가상이어야 합니다.
- 재정의한 함수에는 `override`를 붙입니다.
- 기반 생성자와 소멸자에서는 파생 타입의 재정의 함수가 호출될 것이라고 가정하지 않습니다.
- 파생 클래스가 기반 클래스의 불변식과 사전·사후 조건을 약화시키지 않게 합니다.
- 변경 가능한 `protected` 상태보다 작고 안정적인 공개 인터페이스를 선호합니다.

## 8. 객체 슬라이싱

다형적 기반 타입을 값으로 복사하면 파생 타입 부분이 사라지는 객체 슬라이싱이 발생할 수 있습니다. 다음 예제의 기반 타입은 설명을 위해 추상 클래스로 만들지 않았습니다.

```cpp
class Message
{
public:
    virtual ~Message() = default;
    [[nodiscard]] virtual std::string text() const { return "message"; }
};

class DetailedMessage : public Message
{
public:
    [[nodiscard]] std::string text() const override { return "detailed"; }
};

void print(Message message); // DetailedMessage를 넘기면 Message 부분만 복사됨
```

런타임 다형성을 유지하려면 참조나 포인터 경계를 사용합니다.

```cpp
void print(const Message& message);
```

다형적 객체를 소유하는 컨테이너는 일반적으로 `std::unique_ptr<Base>`를 저장합니다.

```cpp
std::vector<std::unique_ptr<Formatter>> formatters;
```

## 9. `variant`를 이용한 값 기반 다형성

가능한 타입 집합이 닫혀 있고 각 타입이 값 의미론을 가질 수 있다면 `std::variant`가 더 단순할 수 있습니다.

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

장점은 다음과 같습니다.

- 힙 할당이나 공유 소유권이 필요하지 않을 수 있습니다.
- 가능한 타입 집합이 컴파일러에 드러납니다.
- 방문자가 모든 대안을 처리하는지 컴파일 시점에 확인할 수 있습니다.

단점도 있습니다.

- 새 대안을 추가하면 관련된 모든 방문자를 수정해야 합니다.
- 외부 플러그인이 새 타입을 추가하는 열린 확장 구조에는 적합하지 않습니다.

## 10. 정적 다형성과 concepts

템플릿은 전달된 타입에 맞춰 컴파일 시점에 코드를 생성합니다.

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

런타임 교체가 필요 없고 인라인 최적화나 값 조합이 중요한 경우에 적합합니다. 대신 구현이 헤더에 노출되고 컴파일 시간이 늘거나 같은 템플릿의 여러 인스턴스 때문에 바이너리 크기가 증가할 수 있습니다.

## 11. 다형성 방식 선택

| 조건 | 우선 고려할 방식 |
|---|---|
| 작은 데이터와 일반 연산 | 값 타입 |
| 다른 객체의 기능을 사용 | 합성 |
| 타입 집합이 닫혀 있음 | `variant` |
| 외부 구현 추가와 런타임 교체가 필요 | 가상 인터페이스 |
| 컴파일 시점 조합과 타입 제약이 중요 | 템플릿 + concept |

다형성이 필요하다는 이유만으로 상속부터 선택하지 않습니다.

## 12. 인터페이스를 작게 유지합니다

큰 인터페이스는 각 구현에 필요하지 않은 함수까지 강제합니다.

```cpp
class Repository
{
public:
    virtual ~Repository() = default;
    virtual void save(const Job&) = 0;
    virtual std::optional<Job> find(JobId) = 0;
};
```

읽기만 필요한 코드에는 더 작은 인터페이스를 제공할 수 있습니다.

```cpp
class JobReader
{
public:
    virtual ~JobReader() = default;
    virtual std::optional<Job> find(JobId) const = 0;
};
```

인터페이스를 역할별로 분리하면 변경 권한이 줄고 테스트 대역도 단순해집니다.

## 13. Pimpl은 필요한 경계에만 사용합니다

Pimpl(pointer to implementation)은 공개 헤더에서 구현 의존성을 숨기고 바이너리 인터페이스를 비교적 안정적으로 유지하는 데 사용할 수 있습니다.

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

대신 힙 할당, 간접 접근, 추가 상용구가 생깁니다. 작은 내부 애플리케이션에 일괄 적용하지 않습니다.

## 연결 실습

[로컬 작업 실행기](../../exercises/01-modern-cpp/04-local-job-runner/README.md)의 상태와 책임을 먼저 그림으로 정리합니다.

```text
JobRunner
├─ 워커 스레드 수명 소유
├─ 큐와 작업 레코드 동기화
├─ submit·cancel·stop 상태 전이
└─ 저널 호출 순서 관리

Record
├─ JobSnapshot 값
├─ Work callable
└─ 작업별 stop_source
```

다음 대안을 비교합니다.

- 모든 상태를 공개 `struct`에 두고 호출자가 직접 변경
- `JobRunner`가 상태 전이를 전담
- `Work`를 가상 클래스 계층으로 표현
- `Work`를 `std::function` 값으로 표현

현재 실습은 동작 집합이 단순하고 호출자가 람다를 전달할 수 있으므로 `std::function`을 사용합니다. 플러그인의 독립적인 수명이나 복잡한 다형적 상태가 필요해지면 다른 경계를 검토합니다.

## 자주 발생하는 문제

- 모든 클래스에 getter와 setter를 추가합니다.
- 재사용을 이유로 상태를 가진 상속 계층을 깊게 만듭니다.
- 기반 소멸자를 가상으로 만들지 않은 채 기반 포인터로 객체를 삭제합니다.
- `shared_ptr`를 사용해 책임과 수명 설계를 대신합니다.
- service locator와 싱글턴으로 의존성을 숨깁니다.
- 하나의 인터페이스가 저장·조회·네트워크·로그를 모두 담당합니다.

## 완료 기준

- 단순 데이터 집합과 불변식을 가진 클래스를 구분합니다.
- 상태 변경 책임과 외부 조율 로직을 분리합니다.
- 합성을 기본 설계로 고려합니다.
- 가상 함수, `variant`, 템플릿 다형성의 적용 조건을 설명합니다.
- 객체 슬라이싱과 비가상 기반 소멸자의 문제를 재현합니다.

## 다음 문서

[오류·optional·variant·expected](05-errors-optional-variant-and-expected.md)에서 생성자, 멤버 함수, 시스템 경계의 실패를 어떤 타입으로 표현할지 결정합니다.
