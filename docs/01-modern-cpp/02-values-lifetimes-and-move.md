# 값·수명·복사·이동

## 목표

C++ 코드를 읽을 때 객체가 포인터인지 값인지만 확인하지 않고 다음 항목을 함께 추적합니다.

- 객체의 수명은 언제 시작하고 끝나는가
- 함수가 값을 소유하는가, 잠시 빌려 쓰는가
- 복사와 이동 중 어느 연산이 발생하는가
- 뷰가 참조하는 원본은 언제까지 유효한가
- 이동 후 원본 객체에는 어떤 보장이 남는가

이 모델은 성능 최적화에 앞서 프로그램의 정확성을 지키기 위한 기반입니다.

## 시작하기 전에

[프로그램·빌드·CMake](01-program-build-cmake.md)를 완료하고 생성자, 함수 호출, `const`의 기본 의미를 이해해야 합니다.

## 1. 객체 수명은 저장 위치만으로 결정되지 않습니다

객체가 스택에 있는지 힙에 있는지만으로 수명을 설명할 수는 없습니다.

```cpp
std::string make_name()
{
    std::string name{"worker"};
    return name;
}
```

지역 변수 `name`의 수명은 함수가 끝날 때 종료됩니다. 그러나 반환값은 호출 측에서 사용할 별도의 결과 객체를 초기화하며, 컴파일러는 NRVO를 비롯한 복사 생략으로 불필요한 중간 객체를 없앨 수 있습니다.

반대로 힙에 할당된 객체도 소유자가 해제하면 수명이 끝납니다.

```cpp
auto owner = std::make_unique<std::string>("worker");
std::string* observer = owner.get();
owner.reset();
// observer에는 주소가 남아 있지만 해당 객체의 수명은 끝났습니다.
```

주소 값이 남아 있는 것과 그 주소에 유효한 객체가 존재하는 것은 서로 다른 문제입니다.

## 2. 초기화와 대입

초기화는 새 객체의 수명을 시작합니다. 대입은 이미 살아 있는 객체의 값을 바꿉니다.

```cpp
std::string first{"alpha"};         // 초기화
std::string second{first};           // 복사 생성
second = first;                      // 복사 대입
std::string third{std::move(first)}; // 이동 생성
third = std::move(second);           // 이동 대입
```

생성과 대입은 문법이 비슷해도 수행할 일이 다릅니다. 특히 이동 대입 연산자는 대상 객체가 기존에 소유하던 자원을 적절히 정리한 뒤 새 자원을 인수해야 합니다.

## 3. 값 범주는 표현식의 사용 방식을 나타냅니다

값 범주의 모든 세부 분류를 먼저 암기하기보다 다음 규칙부터 이해합니다.

- 이름이 있는 객체를 나타내는 표현식은 일반적으로 lvalue입니다.
- 곧 사라질 임시 객체는 rvalue로 사용할 수 있습니다.
- `std::move`는 객체를 실제로 옮기지 않습니다. 인자를 rvalue로 취급할 수 있도록 캐스팅합니다.
- 실제 자원 이전은 대상 타입의 이동 생성자나 이동 대입 연산자가 수행합니다.

```cpp
std::vector<std::string> names;
std::string name{"worker"};

names.push_back(name);            // name을 보존하므로 복사
names.push_back(std::move(name)); // name의 자원을 이전할 수 있으므로 이동
```

표준 라이브러리 객체는 일반적으로 이동 후에도 파괴하거나 새 값을 대입할 수 있는 **유효하지만 값이 지정되지 않은 상태**로 남습니다. 이전 문자열 내용이 유지된다고 가정해서는 안 됩니다. 사용자 정의 타입도 문서화한 이동 후 불변 조건을 지켜야 합니다.

## 4. 복사 가능한 값 타입

값 타입은 복사본이 원본과 독립적으로 사용할 수 있는 의미를 가져야 합니다.

```cpp
class TaskId
{
public:
    explicit TaskId(std::uint64_t value) : value_(value) {}
    [[nodiscard]] std::uint64_t value() const noexcept { return value_; }

    auto operator<=>(const TaskId&) const = default;

private:
    std::uint64_t value_;
};
```

`TaskId`를 복사해도 두 객체가 같은 외부 자원을 중복 해제하지 않습니다. 비교와 소멸도 자연스럽게 동작하므로 컨테이너에 저장하거나 함수에서 값으로 반환하기 쉽습니다.

강한 값 타입의 목적은 래퍼 타입을 무조건 늘리는 것이 아니라 서로 다른 단위와 의미가 실수로 섞이지 않게 하는 것입니다.

```cpp
void cancel(TaskId id);
void set_timeout(std::chrono::milliseconds timeout);
```

두 값의 내부 표현이 모두 정수이더라도 같은 매개변수 타입으로 받을 이유는 없습니다.

## 5. 매개변수 전달 방식

### 값으로 받기

함수가 인자의 복사본을 소유하거나 내부에 저장한다면 값으로 받는 방식이 단순할 수 있습니다.

```cpp
class Task
{
public:
    explicit Task(std::string title) : title_(std::move(title)) {}

private:
    std::string title_;
};
```

호출자가 lvalue를 넘기면 매개변수를 만들 때 복사가 발생하고, rvalue를 넘기면 이동할 수 있습니다. 그 뒤 매개변수의 값을 멤버로 이동합니다. 이 방식은 `const std::string&`와 `std::string&&` 오버로드를 모두 제공하는 것보다 인터페이스가 단순한 경우가 많습니다.

### `const T&`로 받기

함수 호출 중에 객체를 읽기만 하고 저장하지 않을 때 사용합니다.

```cpp
void print_task(const Task& task);
```

참조를 멤버나 비동기 작업에 보관한다면 참조 대상이 그 사용 시점까지 살아 있다는 별도의 수명 조건이 필요합니다.

### `T&`로 받기

호출자가 넘긴 객체를 직접 변경해야 할 때 사용합니다.

```cpp
void normalize(Task& task);
```

출력 매개변수로 남용하면 함수가 실패했을 때 객체가 어느 상태인지 알기 어려워질 수 있습니다. 결과 타입이나 반환값이 더 명확한지 먼저 검토합니다.

### 포인터로 받기

값이 없을 수 있음을 표현하거나 C API·배열과 연동할 때 사용합니다. 원시 포인터만으로는 소유권 이전 여부가 드러나지 않으므로 소유 포인터로 사용하지 않습니다.

```cpp
Task* find_task(TaskId id);       // null일 수 있는 비소유 포인터
const Task* find_task(TaskId id) const;
```

인터페이스 문서에 비소유 여부와 포인터가 유효한 기간을 명시합니다.

## 6. 반환은 값부터 고려합니다

지역 객체에 대한 참조를 반환하면 함수가 끝난 뒤 수명이 종료된 객체를 가리키게 됩니다.

```cpp
const std::string& bad_name()
{
    std::string name{"worker"};
    return name; // 댕글링 참조
}
```

작은 값과 표준 컨테이너는 우선 값으로 반환하는 방식을 검토합니다.

```cpp
std::vector<Task> load_tasks();
```

복사 생략과 이동 연산이 불필요한 복사 비용을 줄일 수 있습니다. 실제 측정으로 성능 문제가 확인되기 전부터 복잡한 출력 매개변수나 호출자 소유 버퍼를 기본 인터페이스로 만들 필요는 없습니다.

## 7. `string_view`와 `span`은 원본을 소유하지 않습니다

`std::string_view`는 문자열을 복사하지 않고 연속된 문자 구간을 참조합니다.

```cpp
std::string_view command_name(std::string_view line);
```

다음 코드는 댕글링 뷰를 반환합니다.

```cpp
std::string_view bad()
{
    return std::string{"temporary"};
}
```

반환 시점에 임시 문자열이 파괴되므로 반환된 뷰를 사용할 수 없습니다.

`std::span<T>`도 연속된 객체 구간을 소유하지 않습니다.

```cpp
int sum(std::span<const int> values);
```

배열, `vector`, 포인터와 길이로 표현된 연속 구간을 하나의 인터페이스로 받을 수 있지만 원본 컨테이너가 파괴되거나 재할당되면 뷰가 무효화될 수 있습니다.

## 8. 이동 전용 타입

파일, 뮤텍스, 스레드, 고유 등록 토큰처럼 한 번에 하나의 소유자만 있어야 하는 자원은 복사를 금지하고 이동만 허용할 수 있습니다.

```cpp
class Handle
{
public:
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;

    Handle(Handle&& other) noexcept;
    Handle& operator=(Handle&& other) noexcept;
};
```

컨테이너가 재할당할 때 복사 대신 이동을 사용하면서도 강한 예외 보장을 유지하려면 이동 생성자의 `noexcept` 여부가 중요할 수 있습니다. 특히 복사 가능한 타입은 이동이 예외를 던질 수 있을 때 컨테이너가 복사를 선택할 수 있습니다.

이동 대입을 구현할 때는 다음 사항을 처리합니다.

```text
자기 자신으로부터의 이동에도 안전하도록 설계
→ 대상이 기존에 소유한 자원 정리
→ 원본의 자원 인수
→ 원본을 문서화된 비소유 유효 상태로 전환
```

명시적으로 자기 이동을 검사할 수도 있고, 별도 분기 없이도 안전한 구현을 선택할 수도 있습니다.

## 9. 복사 생략과 `std::move` 남용

지역 변수를 반환할 때 무조건 `std::move`를 붙이지 않습니다.

```cpp
Task make_task()
{
    Task task{/* ... */};
    return task; // NRVO 대상
}
```

`return std::move(task);`는 이름 있는 지역 변수에 적용할 수 있는 NRVO를 방해할 수 있습니다. 일반적인 값 반환을 사용해 컴파일러가 복사 생략을 적용할 여지를 남깁니다.

## 10. 소유권을 함수 선언에 드러냅니다

다음 함수 선언은 서로 다른 수명과 소유권 규칙을 나타냅니다.

```cpp
void inspect(const Task& task);            // 호출 중 비소유 읽기
void update(Task& task);                   // 호출 중 비소유 변경
void consume(Task task);                   // 함수가 독립된 값을 소유
void install(std::unique_ptr<Task> task);  // 유일 소유권 이전
std::shared_ptr<Task> subscribe();         // 공유 소유권 반환
Task* find(TaskId id);                     // null일 수 있는 비소유 관찰
```

모든 수명 문제를 스마트 포인터로 해결하려 해서는 안 됩니다. 값으로 자연스럽게 표현할 수 있는 데이터는 값으로 두는 편이 더 단순합니다.

## 연결 실습

먼저 [강한 타입과 CMake](../../exercises/01-modern-cpp/01-strong-types-and-cmake/README.md)에서 복사 가능한 값 타입을 구현합니다. 이어서 [이동 전용 파일 소유자](../../exercises/01-modern-cpp/02-unique-file/README.md)에서 이동 생성자, 이동 대입 연산자, 이동 후 상태를 구현합니다.

두 실습을 비교하며 다음 항목을 기록합니다.

- `TaskId`가 복사 가능해야 하는 이유
- `UniqueFile`의 복사를 금지해야 하는 이유
- 각 타입을 컨테이너에 저장할 때 필요한 연산
- 참조나 뷰를 반환할 때 성립해야 하는 수명 조건

## 자주 발생하는 문제

- 큰 객체는 모두 `const&`로 받은 뒤 호출이 끝난 후까지 참조를 보관합니다.
- `std::move`를 호출하면 원본 객체가 즉시 파괴된다고 오해합니다.
- 이동 후 객체에 이전 값이 그대로 남아 있다고 가정합니다.
- 지역 객체의 참조·포인터·뷰를 반환합니다.
- 원시 소유 포인터를 가진 값 타입에서 컴파일러가 생성한 복사 연산을 그대로 사용합니다.

## 완료 기준

- 초기화와 대입을 구분합니다.
- 값, 소유자, 비소유 뷰를 함수 선언에서 식별합니다.
- 타입의 의미에 맞게 복사와 이동 가능 여부를 결정합니다.
- 이동 후 객체에 보장되는 상태를 설명합니다.
- `string_view`와 `span`에서 발생하는 수명 오류를 재현합니다.

## 다음 문서

[RAII·스마트 포인터·Rule of Zero](03-raii-smart-pointers-and-rule-of-zero.md)에서 자원의 수명을 객체 수명에 결합하고, 특수 멤버 함수를 직접 작성해야 하는 경우와 기본 동작에 맡겨야 하는 경우를 구분합니다.
