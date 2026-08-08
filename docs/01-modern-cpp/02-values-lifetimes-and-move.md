# 값·수명·복사·이동

## 목표

C++ 코드를 읽을 때 “포인터인가 값인가”만 확인하지 않고 다음을 추적합니다.

- 객체의 수명은 언제 시작하고 끝나는가
- 함수가 값을 소유하는가, 빌려 쓰는가
- 복사와 이동 중 무엇이 발생하는가
- view가 참조하는 원본은 언제까지 살아 있는가
- 이동된 객체가 어떤 상태로 남는가

이 모델은 성능 최적화보다 먼저 정확성을 지키기 위한 기반입니다.

## 시작하기 전에

[프로그램·빌드·CMake](01-program-build-cmake.md)를 완료하고, 생성자·함수 호출과 `const`의 기본 의미를 알고 있어야 합니다.

## 1. 객체 수명은 저장 위치와 다릅니다

객체가 stack에 있는지 heap에 있는지만으로 수명을 설명할 수 없습니다.

```cpp
std::string make_name()
{
    std::string name{"worker"};
    return name;
}
```

지역 변수 `name`의 수명은 함수 끝에서 종료되지만 반환값 객체는 caller 쪽에서 만들어집니다. compiler는 copy elision을 통해 불필요한 중간 복사를 제거할 수 있습니다.

반대로 heap에 있는 객체도 소유자가 해제하면 즉시 수명이 끝납니다.

```cpp
auto owner = std::make_unique<std::string>("worker");
std::string* observer = owner.get();
owner.reset();
// observer는 주소 값을 가지고 있지만 객체는 더 이상 살아 있지 않습니다.
```

주소가 남아 있다는 사실과 객체가 살아 있다는 사실을 구분합니다.

## 2. 초기화와 대입

초기화는 새 객체의 수명을 시작합니다. 대입은 이미 존재하는 객체의 값을 바꿉니다.

```cpp
std::string first{"alpha"};       // 초기화
std::string second{first};         // 복사 생성
second = first;                    // 복사 대입
std::string third{std::move(first)}; // 이동 생성
third = std::move(second);         // 이동 대입
```

생성자와 대입 연산자는 비슷해 보여도 기존 자원 정리 여부가 다릅니다. 이동 대입은 현재 객체가 이미 가진 자원을 처리한 뒤 새 자원을 인수해야 합니다.

## 3. 값 범주는 “표현식을 어떻게 사용할 수 있는가”를 나타냅니다

모든 분류 이름을 암기하는 것보다 다음 실용 규칙이 중요합니다.

- 이름이 있는 객체 표현식은 대개 lvalue입니다.
- 곧 사라질 임시값은 rvalue로 취급할 수 있습니다.
- `std::move`는 객체를 이동시키는 함수가 아니라 rvalue로 취급하도록 변환합니다.
- 실제 이동은 해당 타입의 이동 생성자 또는 이동 대입이 수행합니다.

```cpp
std::vector<std::string> names;
std::string name{"worker"};

names.push_back(name);            // name을 보존해야 하므로 복사
names.push_back(std::move(name)); // name의 자원을 넘길 수 있으므로 이동
```

`std::move(name)` 뒤 `name`은 파괴하거나 새 값을 대입할 수 있는 **유효하지만 값이 지정되지 않은 상태**입니다. 이전 문자열 내용이 남는다고 기대하면 안 됩니다.

## 4. 복사 가능한 값 타입

값 타입은 복사본이 원본과 독립적인 의미를 가져야 합니다.

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

`TaskId`는 복사해도 두 객체가 같은 외부 자원을 동시에 해제하지 않습니다. 비교와 파괴도 자연스럽습니다. 이런 타입은 container에 저장하고 함수에서 값으로 반환하기 쉽습니다.

강한 값 타입의 목적은 wrapper 수를 늘리는 것이 아니라 잘못된 단위와 의미를 섞지 않는 것입니다.

```cpp
void cancel(TaskId id);
void set_timeout(std::chrono::milliseconds timeout);
```

둘 다 정수라고 해서 같은 parameter로 받지 않습니다.

## 5. parameter 전달 선택

### 값으로 받기

함수가 복사본을 소유하거나 인자를 저장할 경우 값 전달이 단순할 수 있습니다.

```cpp
class Task
{
public:
    explicit Task(std::string title) : title_(std::move(title)) {}

private:
    std::string title_;
};
```

caller가 lvalue를 넘기면 한 번 복사되고, rvalue를 넘기면 이동될 수 있습니다. `const std::string&`와 `std::string&&` overload를 모두 만드는 것보다 단순할 때가 많습니다.

### `const T&`로 받기

함수가 호출 중 읽기만 하고 저장하지 않을 때 사용합니다.

```cpp
void print_task(const Task& task);
```

함수가 참조를 멤버에 저장한다면 caller 수명보다 오래 살지 않는지 별도 계약이 필요합니다.

### `T&`로 받기

호출자 객체를 반드시 변경할 때 사용합니다.

```cpp
void normalize(Task& task);
```

출력 parameter로 무분별하게 사용하면 실패 뒤 상태가 불명확해질 수 있습니다. 결과 타입이나 반환값이 더 명확한지 검토합니다.

### pointer로 받기

없음을 표현하거나 C API·배열과 연결할 때 사용합니다. raw pointer만으로 소유권 이전을 표현하지 않습니다.

```cpp
Task* find_task(TaskId id);       // nullable observer일 수 있음
const Task* find_task(TaskId id) const;
```

API 문서에서 비소유라는 점과 유효 기간을 명시합니다.

## 6. 반환값은 값으로 시작합니다

지역 객체의 참조를 반환하면 수명이 끝난 객체를 가리킵니다.

```cpp
const std::string& bad_name()
{
    std::string name{"worker"};
    return name; // dangling reference
}
```

작은 값과 표준 container는 값으로 반환하는 것을 기본으로 고려합니다.

```cpp
std::vector<Task> load_tasks();
```

copy elision과 이동이 불필요한 복사 비용을 줄입니다. 성능 문제가 실제 측정되기 전에 복잡한 출력 parameter 또는 caller-owned buffer를 기본값으로 만들지 않습니다.

## 7. `string_view`와 `span`은 소유하지 않습니다

`std::string_view`는 문자열을 복사하지 않고 문자 구간을 봅니다.

```cpp
std::string_view command_name(std::string_view line);
```

다음 코드는 위험합니다.

```cpp
std::string_view bad()
{
    return std::string{"temporary"};
}
```

반환 직후 임시 문자열이 파괴되어 view가 dangling 상태가 됩니다.

`std::span<T>`도 연속된 객체 구간을 소유하지 않습니다.

```cpp
int sum(std::span<const int> values);
```

array, vector와 pointer+length를 하나의 안전한 경계로 받을 수 있지만 원본 container의 재할당과 파괴에 영향을 받습니다.

## 8. 이동 전용 타입

파일, mutex, thread와 유일한 등록 token처럼 하나의 소유자만 있어야 하는 자원은 복사를 금지하고 이동을 허용할 수 있습니다.

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

container가 재배치할 때 이동을 안정적으로 선택하도록 이동 연산에 `noexcept`가 중요한 경우가 많습니다.

이동 대입은 다음 순서를 지킵니다.

```text
자기 대입 확인
→ 현재 소유 자원 정리
→ 상대의 자원 인수
→ 상대를 비소유 유효 상태로 전환
```

## 9. copy elision과 `std::move` 남용

지역 변수를 반환할 때 무조건 `std::move`하지 않습니다.

```cpp
Task make_task()
{
    Task task{/* ... */};
    return task; // copy elision 기회
}
```

`return std::move(task);`는 일부 copy elision 기회를 방해할 수 있습니다. compiler가 반환 최적화를 적용할 수 있도록 일반적인 값 반환을 우선합니다.

## 10. 소유권을 signature에 드러냅니다

다음 signature는 서로 다른 계약입니다.

```cpp
void inspect(const Task& task);             // 호출 중 비소유 읽기
void update(Task& task);                    // 호출 중 비소유 변경
void consume(Task task);                    // 함수가 독립 값 소유
void install(std::unique_ptr<Task> task);   // 유일 소유권 이전
std::shared_ptr<Task> subscribe();           // 공유 소유권 반환
Task* find(TaskId id);                       // nullable 비소유 관찰
```

모든 문제를 smart pointer로 해결하지 않습니다. 값으로 표현할 수 있으면 값이 더 단순합니다.

## 연결 실습

먼저 [강한 타입과 CMake](../../exercises/01-modern-cpp/01-strong-types-and-cmake/README.md)에서 복사 가능한 값 타입을 구현합니다. 이어서 [이동 전용 파일 소유자](../../exercises/01-modern-cpp/02-unique-file/README.md)에서 이동 생성·이동 대입과 moved-from 상태를 구현합니다.

두 실습을 비교하며 다음을 기록합니다.

- `TaskId`가 복사 가능해야 하는 이유
- `UniqueFile`이 복사되면 안 되는 이유
- 각각 container에 저장될 때 필요한 연산
- 참조 또는 view를 반환했을 때 생기는 수명 전제

## 자주 발생하는 실패

- 모든 큰 객체를 `const&`로 받아 저장한 뒤 caller보다 오래 사용합니다.
- `std::move`를 호출하면 원본이 즉시 파괴된다고 생각합니다.
- moved-from 객체의 이전 값을 검사합니다.
- 지역 객체의 참조·pointer·view를 반환합니다.
- 값 타입에 raw owning pointer를 넣고 compiler가 만든 복사를 그대로 사용합니다.

## 완료 기준

- 초기화와 대입을 구분합니다.
- 값, 소유자와 비소유 view를 signature에서 설명합니다.
- 복사와 이동의 의미를 타입별로 결정합니다.
- moved-from 상태의 보장 범위를 설명합니다.
- `string_view`와 `span`의 수명 실패를 재현합니다.

## 다음 문서

[RAII·smart pointer·Rule of Zero](03-raii-smart-pointers-and-rule-of-zero.md)에서 자원 수명을 객체 수명에 결합하고, 직접 소멸자를 작성해야 하는 경우와 작성하지 않아야 하는 경우를 구분합니다.
