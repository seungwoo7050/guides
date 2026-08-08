# RAII·smart pointer·Rule of Zero

## 목표

파일, 메모리, lock, thread와 등록 token을 정상 경로와 실패 경로 모두에서 정확히 정리합니다. 자원 획득을 객체 초기화와 결합하고, 소유권을 값·`unique_ptr`·`shared_ptr` 중 가장 단순한 형태로 표현합니다.

## 시작하기 전에

[값·수명·복사·이동](02-values-lifetimes-and-move.md)을 완료하고 복사 가능한 값 타입과 이동 전용 타입의 차이를 설명할 수 있어야 합니다.

## 1. RAII는 “소멸자에서 delete”보다 넓습니다

RAII(Resource Acquisition Is Initialization)는 자원의 유효 기간을 객체 수명에 연결하는 원칙입니다.

```text
생성 성공
→ 객체가 자원을 소유
→ 모든 정상·예외 경로에서 객체 소멸
→ 자원 정리
```

자원에는 메모리만 포함되지 않습니다.

- 파일과 socket handle
- mutex lock
- thread
- temporary directory
- database transaction
- callback 등록 token
- 성능 측정 구간

정리 책임이 수동 `cleanup()` 호출에 의존하면 중간 return과 예외 경로에서 빠지기 쉽습니다.

## 2. 먼저 표준 RAII 타입을 사용합니다

직접 자원 wrapper를 만들기 전에 표준 타입을 찾습니다.

| 자원 | 우선 도구 |
|---|---|
| 동적 단일 객체 | 값 또는 `std::unique_ptr` |
| 동적 배열 | `std::vector`, `std::string` |
| 파일 stream | `std::ifstream`, `std::ofstream` |
| mutex 잠금 | `std::lock_guard`, `std::unique_lock`, `std::scoped_lock` |
| thread | `std::jthread` |
| filesystem 경로 | `std::filesystem::path` |

`new[]`를 직접 감싸는 class를 만드는 대신 vector가 필요한지 먼저 묻습니다.

## 3. Rule of Zero

멤버들이 자신의 자원을 올바르게 관리하면 바깥 class는 destructor, copy, move를 직접 작성하지 않아도 됩니다.

```cpp
class UserProfile
{
public:
    UserProfile(std::string name, std::vector<std::string> roles)
        : name_(std::move(name)), roles_(std::move(roles))
    {}

private:
    std::string name_;
    std::vector<std::string> roles_;
};
```

compiler가 만든 복사·이동·소멸은 각 멤버의 올바른 연산을 조합합니다. 이것이 일반 애플리케이션에서 가장 안전한 기본입니다.

직접 destructor를 작성했다면 다음을 다시 검토합니다.

- 이 class가 정말 raw 자원을 직접 소유해야 하는가
- 표준 RAII 타입으로 멤버를 바꿀 수 없는가
- 복사와 이동도 함께 결정했는가

## 4. Rule of Five가 필요한 경계

raw 자원을 직접 소유하는 낮은 수준 wrapper는 다음 다섯 연산을 의식해야 합니다.

- destructor
- copy constructor
- copy assignment
- move constructor
- move assignment

모두 구현해야 한다는 뜻은 아닙니다. 유일 소유자라면 복사를 삭제하고 이동만 구현합니다.

```cpp
class UniqueFile
{
public:
    ~UniqueFile();

    UniqueFile(const UniqueFile&) = delete;
    UniqueFile& operator=(const UniqueFile&) = delete;

    UniqueFile(UniqueFile&& other) noexcept;
    UniqueFile& operator=(UniqueFile&& other) noexcept;
};
```

낮은 수준 wrapper 하나가 Rule of Five를 담당하고, 이를 사용하는 상위 class는 다시 Rule of Zero로 돌아가는 구조가 좋습니다.

## 5. `unique_ptr`가 기본 owning pointer입니다

동적 다형성 또는 선택적 대형 객체처럼 heap 소유가 실제로 필요하면 `unique_ptr`를 먼저 고려합니다.

```cpp
std::unique_ptr<Renderer> make_renderer(const Config& config)
{
    if (config.text_mode)
        return std::make_unique<TextRenderer>();
    return std::make_unique<HtmlRenderer>();
}
```

signature가 소유권을 드러냅니다.

```cpp
void install(std::unique_ptr<Renderer> renderer);
```

caller는 `std::move`로 소유권을 넘깁니다. 함수가 단지 호출 중 사용한다면 pointer 소유권을 받지 말고 `Renderer&` 또는 `const Renderer&`를 사용합니다.

## 6. custom deleter

C API가 반환한 자원도 `unique_ptr`의 deleter로 감쌀 수 있습니다.

```cpp
struct FileCloser
{
    void operator()(std::FILE* file) const noexcept
    {
        if (file != nullptr)
            std::fclose(file);
    }
};

using FilePtr = std::unique_ptr<std::FILE, FileCloser>;
```

단순 close만 필요하면 custom deleter가 충분합니다. 다음처럼 추가 동작과 명확한 API가 필요하면 별도 wrapper class가 낫습니다.

- `read_all`, `write`, `flush`
- moved-from 상태 검사
- 오류 변환
- handle 관찰 API 제한

## 7. `shared_ptr`는 편한 기본값이 아닙니다

`shared_ptr`는 control block의 reference count가 0일 때 자원을 파괴합니다. 하지만 “누가 수명을 끝낼 책임이 있는가”를 흐릴 수 있습니다.

사용 전에 다음을 확인합니다.

- 실제로 독립된 여러 소유자가 존재하는가
- 단일 상위 소유자와 비소유 observer로 표현할 수 없는가
- 파괴 시점을 예측할 필요가 없는가
- cycle 가능성이 없는가

```cpp
struct Node
{
    std::shared_ptr<Node> next;
};
```

서로를 `shared_ptr`로 참조하는 cycle은 reference count가 0이 되지 않습니다. 비소유 방향은 `weak_ptr`로 표현하거나 그래프의 소유 구조를 다시 설계합니다.

## 8. `weak_ptr`는 수명 연장이 아닌 관찰입니다

```cpp
std::weak_ptr<Session> session;

if (auto locked = session.lock())
{
    locked->send("ping");
}
```

`lock`이 성공한 범위에서만 shared ownership을 임시 확보합니다. `expired()`를 확인한 뒤 별도로 사용하면 검사와 사용 사이에 상태가 바뀔 수 있습니다.

## 9. container와 소유권

다음 container는 의미가 다릅니다.

```cpp
std::vector<Task> tasks;                       // 값 소유
std::vector<std::unique_ptr<Task>> tasks;      // 이동 전용 heap 객체 소유
std::vector<std::shared_ptr<Task>> tasks;      // 공유 소유
std::vector<std::reference_wrapper<Task>> view; // 비소유 관찰
```

polymorphism이 필요하지 않고 object 크기가 정상적이면 값 container가 가장 단순합니다. `unique_ptr` vector는 주소 안정성, polymorphism 또는 non-copyable object가 필요한 경우에 사용합니다.

## 10. lock도 RAII로 관리합니다

```cpp
void Counter::increment()
{
    std::lock_guard lock{mutex_};
    ++value_;
}
```

수동 `lock()`과 `unlock()` 사이에 return 또는 예외가 생기면 lock이 남을 수 있습니다.

여러 mutex를 함께 잡아야 하면 `std::scoped_lock`으로 deadlock-safe 획득을 사용합니다.

```cpp
std::scoped_lock lock{left.mutex_, right.mutex_};
```

lock 수명은 가능한 짧게 유지하되, 불변식 변경 전체를 보호해야 합니다.

## 11. 예외 안전성과 RAII

함수 중간에 예외가 발생해도 이미 생성된 지역 RAII 객체는 역순으로 파괴됩니다.

```cpp
void update()
{
    TemporaryFile temp{/* ... */};
    DatabaseTransaction tx{/* ... */};
    write_data(temp);
    tx.commit();
}
```

`write_data`가 실패하면 `tx`와 `temp`가 정리됩니다. 그러나 RAII가 업무 상태 rollback을 자동으로 보장하는 것은 아닙니다. 어떤 변경이 commit되었는지 별도 transaction 계약이 필요합니다.

## 12. 소멸자는 실패를 밖으로 던지지 않습니다

stack unwinding 중 destructor가 다시 예외를 던지면 프로그램이 종료될 수 있습니다. 정리 함수가 실패할 수 있다면 다음을 분리합니다.

- 명시적 `flush`·`commit`에서 오류 보고
- destructor에서는 가능한 최선의 정리
- destructor의 실패를 log 또는 상태로 남길지 결정

파일 flush 성공이 업무적으로 중요하다면 소멸자에만 맡기지 않고 명시적으로 검사합니다.

## 연결 실습

[RAII와 이동 전용 파일 소유자](../../exercises/01-modern-cpp/02-unique-file/README.md)를 구현합니다.

실습에서 다음 두 설계를 비교합니다.

1. `std::unique_ptr<std::FILE, FileCloser>`
2. 동작과 오류 계약을 가진 `UniqueFile` class

단순 소멸만 필요하면 1번이 작고, 읽기·쓰기·moved-from 검사와 오류 변환이 공개 계약이라면 2번이 더 명확합니다.

## 실패 실험

- 이동 생성에서 원본 handle을 비우지 않습니다.
- 이동 대입에서 현재 handle을 먼저 닫지 않습니다.
- destructor를 작성하고 복사를 compiler 기본값으로 둡니다.
- `shared_ptr` cycle을 만든 뒤 destructor 호출 여부를 관찰합니다.
- 수동 mutex unlock 앞에서 예외를 던집니다.

## 완료 기준

- Rule of Zero를 기본으로 선택합니다.
- 낮은 수준 소유자에서만 Rule of Five를 직접 다룹니다.
- 값, `unique_ptr`, `shared_ptr`, `weak_ptr`와 비소유 참조를 구분합니다.
- lock과 thread를 RAII로 정리합니다.
- 소멸자에 업무상 중요한 오류 보고를 숨기지 않습니다.

## 다음 문서

[클래스·책임·다형성](04-classes-responsibilities-and-polymorphism.md)에서 자원을 안전하게 보유하는 것에서 더 나아가, 상태를 변경할 권한과 정책을 어느 객체에 둘지 결정합니다.
