# RAII·스마트 포인터·Rule of Zero

## 목표

파일, 메모리, 잠금, 스레드, 등록 토큰을 정상 경로와 실패 경로에서 빠짐없이 정리합니다. 자원 획득을 객체 초기화와 결합하고, 소유권을 값, `unique_ptr`, `shared_ptr` 중 가장 단순하고 명확한 형태로 표현합니다.

## 시작하기 전에

[값·수명·복사·이동](02-values-lifetimes-and-move.md)을 완료하고 복사 가능한 값 타입과 이동 전용 타입의 차이를 설명할 수 있어야 합니다.

## 1. RAII는 소멸자에서 `delete`하는 기법보다 넓습니다

RAII(Resource Acquisition Is Initialization)는 자원의 유효 기간을 객체 수명에 연결하는 설계 원칙입니다.

```text
생성 성공
→ 객체가 자원을 소유
→ 정상 반환이나 예외로 범위를 벗어남
→ 객체 소멸
→ 자원 정리
```

RAII로 관리할 자원은 메모리에 한정되지 않습니다.

- 파일과 소켓 핸들
- 뮤텍스 잠금
- 스레드
- 임시 디렉터리
- 데이터베이스 트랜잭션
- 콜백 등록 토큰
- 성능 측정 구간

정리 책임을 수동 `cleanup()` 호출에 맡기면 중간 `return`이나 예외 경로에서 호출이 누락되기 쉽습니다.

## 2. 표준 RAII 타입을 우선 사용합니다

자원 래퍼를 직접 만들기 전에 표준 라이브러리에 적합한 타입이 있는지 확인합니다.

| 자원 | 우선 고려할 타입 |
|---|---|
| 동적 단일 객체 | 값 또는 `std::unique_ptr` |
| 동적 배열 | `std::vector`, `std::string` |
| 파일 스트림 | `std::ifstream`, `std::ofstream` |
| 뮤텍스 잠금 | `std::lock_guard`, `std::unique_lock`, `std::scoped_lock` |
| 중단 요청과 조인이 필요한 스레드 | `std::jthread` |
| 파일 시스템 경로 | `std::filesystem::path` |

`new[]`로 확보한 메모리를 감싸는 클래스를 만들기 전에 `vector`로 충분한지부터 검토합니다.

## 3. Rule of Zero

멤버가 각자의 자원을 올바르게 관리한다면 바깥 클래스는 소멸자와 복사·이동 연산을 직접 작성하지 않아도 됩니다.

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

컴파일러가 생성한 복사·이동·소멸 연산은 각 멤버의 대응 연산을 조합합니다. 일반 애플리케이션에서는 이를 기본 선택으로 삼습니다.

소멸자를 직접 작성했다면 다음 항목을 다시 확인합니다.

- 이 클래스가 원시 자원을 직접 소유해야 하는가
- 멤버를 표준 RAII 타입으로 바꿀 수 없는가
- 복사와 이동 동작도 함께 결정했는가

## 4. Rule of Five가 필요한 경계

원시 자원을 직접 소유하는 저수준 래퍼는 다음 다섯 특수 멤버 함수의 동작을 명시적으로 결정해야 합니다.

- 소멸자
- 복사 생성자
- 복사 대입 연산자
- 이동 생성자
- 이동 대입 연산자

다섯 함수를 모두 구현해야 한다는 뜻은 아닙니다. 유일 소유자라면 복사 연산을 삭제하고 이동 연산만 구현합니다.

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

저수준 래퍼 하나가 자원 관리와 Rule of Five를 담당하고, 이를 멤버로 사용하는 상위 클래스는 다시 Rule of Zero를 따르는 구조가 바람직합니다.

## 5. 동적 소유가 필요하면 `unique_ptr`부터 고려합니다

동적 다형성이나 선택적으로 존재하는 대형 객체처럼 힙 소유가 실제로 필요할 때는 `unique_ptr`를 우선 고려합니다.

```cpp
std::unique_ptr<Renderer> make_renderer(const Config& config)
{
    if (config.text_mode)
        return std::make_unique<TextRenderer>();
    return std::make_unique<HtmlRenderer>();
}
```

함수 선언만으로도 유일 소유권 이전을 표현할 수 있습니다.

```cpp
void install(std::unique_ptr<Renderer> renderer);
```

호출자는 `std::move`로 소유권을 넘깁니다. 함수가 호출 중에만 객체를 사용한다면 소유권을 받지 말고 `Renderer&` 또는 `const Renderer&`를 사용합니다.

## 6. 사용자 정의 deleter

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

단순히 `close` 계열 함수만 호출하면 된다면 사용자 정의 deleter로 충분합니다. 다음과 같이 별도 동작과 명확한 상태 규칙이 필요하다면 전용 래퍼 클래스가 더 적합합니다.

- `read_all`, `write`, `flush`
- 이동 후 상태 검사
- C API 오류를 C++ 오류 모델로 변환
- 원시 핸들 관찰 API 제한

## 7. `shared_ptr`는 편의를 위한 기본값이 아닙니다

`shared_ptr`는 같은 제어 블록을 공유하는 소유 참조의 개수가 0이 되면 객체를 파괴합니다. 그러나 여러 곳에서 손쉽게 복사하면 수명을 끝낼 책임이 어디에 있는지 불분명해질 수 있습니다.

사용하기 전에 다음 항목을 확인합니다.

- 실제로 수명을 독립적으로 연장해야 하는 소유자가 여러 개인가
- 하나의 상위 소유자와 비소유 관찰자로 표현할 수 없는가
- 파괴 시점이 마지막 소유자 해제 시점이어도 되는가
- 순환 참조가 생길 가능성은 없는가

```cpp
struct Node
{
    std::shared_ptr<Node> next;
};
```

객체들이 서로를 `shared_ptr`로 소유하는 순환 구조에서는 참조 횟수가 0이 되지 않아 객체가 파괴되지 않을 수 있습니다. 비소유 방향은 `weak_ptr`로 표현하거나 그래프의 소유 구조를 다시 설계합니다.

## 8. `weak_ptr`는 소유권 없이 대상을 관찰합니다

```cpp
std::weak_ptr<Session> session;

if (auto locked = session.lock())
{
    locked->send("ping");
}
```

`lock()`이 성공해 반환한 `shared_ptr`가 살아 있는 범위에서만 대상의 수명을 임시로 확보합니다. `expired()`만 먼저 확인한 뒤 나중에 별도로 사용하면 검사와 사용 사이에 마지막 소유자가 사라질 수 있으므로 `lock()`의 결과를 직접 사용합니다.

## 9. 컨테이너와 소유권

다음 컨테이너는 서로 다른 소유 구조를 나타냅니다.

```cpp
std::vector<Task> tasks;                        // 값을 직접 소유
std::vector<std::unique_ptr<Task>> tasks;       // 이동 전용 힙 객체를 소유
std::vector<std::shared_ptr<Task>> tasks;       // 객체를 공유 소유
std::vector<std::reference_wrapper<Task>> view; // 비소유 참조 모음
```

다형성이 필요하지 않고 객체 크기나 이동 비용에 문제가 없다면 값 컨테이너가 가장 단순합니다. `vector<unique_ptr<T>>`는 동적 다형성, 가리키는 객체 주소의 안정성, 이동할 수 없는 객체의 간접 저장 등이 필요할 때 고려합니다.

## 10. 잠금도 RAII로 관리합니다

```cpp
void Counter::increment()
{
    std::lock_guard lock{mutex_};
    ++value_;
}
```

수동 `lock()`과 `unlock()` 사이에서 함수가 반환되거나 예외가 발생하면 잠금이 해제되지 않을 수 있습니다.

여러 뮤텍스를 한 번에 잠가야 할 때는 `std::scoped_lock`을 사용해 지정한 뮤텍스들을 교착 상태를 피하는 방식으로 획득할 수 있습니다.

```cpp
std::scoped_lock lock{left.mutex_, right.mutex_};
```

이는 해당 호출에 전달한 뮤텍스들의 획득 순서를 조정해 주지만 프로그램 전체의 다른 잠금 순서까지 자동으로 안전하게 만드는 것은 아닙니다. 잠금 범위는 가능한 짧게 유지하되 하나의 불변 조건을 바꾸는 전체 연산은 같은 임계 구역에서 보호합니다.

## 11. 예외 안전성과 RAII

함수 실행 중 예외가 발생하면 이미 생성된 지역 RAII 객체는 스택 풀기 과정에서 생성의 역순으로 파괴됩니다.

```cpp
void update()
{
    TemporaryFile temp{/* ... */};
    DatabaseTransaction tx{/* ... */};
    write_data(temp);
    tx.commit();
}
```

`write_data`가 예외를 던지면 `tx`와 `temp`의 소멸자가 호출됩니다. 단, RAII가 애플리케이션 상태의 롤백까지 자동으로 보장하지는 않습니다. 어떤 변경을 확정하고 실패할 때 어떻게 되돌릴지는 트랜잭션 인터페이스에서 별도로 정의해야 합니다.

## 12. 소멸자에서 오류를 전파하지 않습니다

소멸자는 기본적으로 예외를 던지지 않는 함수로 취급됩니다. 특히 스택 풀기 중 소멸자가 다시 예외를 던지면 `std::terminate`가 호출될 수 있습니다. 정리 과정의 실패를 호출자가 알아야 한다면 다음과 같이 역할을 분리합니다.

- 명시적인 `flush`·`commit` 함수에서 오류를 보고합니다.
- 소멸자에서는 예외를 밖으로 내보내지 않고 가능한 정리를 수행합니다.
- 소멸 중 발생한 부가적인 오류를 로그나 진단 상태로 남길지 결정합니다.

파일 내용이 실제 저장 장치에 반영됐는지 확인하는 일이 업무상 중요하다면 소멸자에만 맡기지 말고 명시적 연산의 결과를 검사합니다.

## 연결 실습

[RAII와 이동 전용 파일 소유자](../../exercises/01-modern-cpp/02-unique-file/README.md)를 구현합니다.

실습에서 다음 두 설계를 비교합니다.

1. `std::unique_ptr<std::FILE, FileCloser>`
2. 동작과 오류 규칙을 제공하는 `UniqueFile` 클래스

소멸 시 자원을 닫는 기능만 필요하면 1번이 더 작습니다. 읽기·쓰기, 이동 후 상태 검사, 오류 변환까지 공개 인터페이스에 포함해야 한다면 2번이 더 명확합니다.

## 실패 실험

- 이동 생성자에서 원본 핸들을 비우지 않습니다.
- 이동 대입 연산자에서 대상이 기존에 소유하던 핸들을 닫지 않습니다.
- 소멸자를 직접 작성하면서 복사 연산은 컴파일러 기본값으로 둡니다.
- `shared_ptr` 순환 참조를 만든 뒤 소멸자 호출 여부를 확인합니다.
- 수동 `unlock()` 전에 예외를 발생시킵니다.

## 완료 기준

- Rule of Zero를 기본 설계로 선택합니다.
- 원시 자원을 직접 소유하는 저수준 타입에서만 Rule of Five를 다룹니다.
- 값, `unique_ptr`, `shared_ptr`, `weak_ptr`, 비소유 참조의 수명 규칙을 구분합니다.
- 잠금과 스레드의 종료를 적절한 RAII 타입으로 관리합니다.
- 업무상 중요한 오류를 소멸자 안에 숨기지 않습니다.

## 다음 문서

[클래스·책임·다형성](04-classes-responsibilities-and-polymorphism.md)에서 자원을 안전하게 보유하는 문제를 넘어, 상태를 변경할 권한과 정책을 어느 객체에 둘지 결정합니다.
