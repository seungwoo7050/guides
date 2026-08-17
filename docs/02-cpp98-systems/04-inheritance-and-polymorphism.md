# 상속, 다형성과 대체 가능한 설계

## 대체 가능한 객체를 설계합니다

`Derived` 객체를 `Base`가 필요한 곳에 전달했을 때 기존 규칙이 깨진다면, 가상 함수가 정상적으로 호출되더라도 안전한 상속 관계가 아닙니다. 호출자가 구체 타입의 선택과 수명 관리에서 벗어날 수 있도록 대체 가능성, 소멸 정책과 조합 경계를 차례로 확인합니다.

## 호출자와 구현의 관계

```text
호출자 → 작은 인터페이스 → 구체 구현
                    ↑
               소유자가 수명 관리

상속: 대체 가능성에 대한 약속
조합: 부품과 수명의 관계
```

다형성의 목적은 클래스 수를 늘리는 것이 아니라, 호출자가 구체 구현의 선택과 수명 관리 방식에 의존하지 않게 하는 것입니다.

## 다형적 라우터로 동작 확인

[교체 가능한 핸들러 실습](../../exercises/02-cpp98-systems/object-model/command-service/04-polymorphism/README.md)은 `switch` 기반 시작 코드와 `Handler`/`Router` 기반 참조 구현을 함께 제공합니다.

```sh
cd exercises/02-cpp98-systems/object-model/command-service/04-polymorphism
make observe
```

위 명령은 저장소 루트에서 실행합니다. `make observe`는 먼저 결과를 예상한 뒤 `reference/` 소스를 열지 않고 실행 결과만 확인하는 선택적 블랙박스 관찰 도구입니다. 워크스페이스의 `skeleton/`을 구현한 뒤 저장소 루트에서 다음 명령으로 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/04-polymorphism
```

학습자 구현 검증을 통과한 뒤에만 참조 구현과 비교합니다. 기준 `fail-nonvirtual` 검사는 가상 함수는 있지만 소멸자가 가상이 아닌 기반 클래스를 통한 삭제를 컴파일러 경고로 검출합니다. 정의되지 않은 동작을 실제로 실행하고 그 결과에 의존하지 않습니다. 목표는 상속 계층을 늘리는 것이 아니라, 호출자가 구체 구현을 몰라도 되는 경계를 확인하는 것입니다.

---

## 1. 세 종류의 다형성

C++에서는 서로 다른 문제를 모두 다형성이라고 부르기도 합니다.

| 종류 | 예 | 선택 시점 |
|---|---|---|
| 임시 다형성(ad-hoc polymorphism) | 함수 오버로딩, 연산자 오버로딩 | 컴파일 시점 |
| 하위 타입 다형성(subtype polymorphism) | 가상 함수와 상속 | 실행 시점 |
| 매개변수 다형성(parametric polymorphism) | 템플릿 | 컴파일 시점 |

이 문서는 하위 타입 다형성을 중심으로 다룹니다. 템플릿은 별도 문서에서 설명합니다.

## 2. 공개 상속의 의미

```cpp
class Handler
{
public:
    virtual ~Handler();
    virtual Response handle(const Request &request) = 0;
};
```

`PutHandler`가 `Handler`를 공개로 상속한다면 다음 조건을 만족해야 합니다.

- `Handler&`가 필요한 모든 곳에서 사용할 수 있습니다.
- `handle`의 사전 조건을 더 강하게 만들지 않습니다.
- 호출자가 기대하는 결과와 실패 처리 규칙을 깨지 않습니다.
- 기반 클래스가 보장하는 불변식을 유지합니다.

몇 줄의 구현을 공유하고 싶다는 이유만으로 공개 상속을 사용하지 않습니다. 다른 객체를 부품으로 사용하려는 관계라면 조합이 대개 더 직접적입니다.

## 3. 생성과 소멸 순서

파생 클래스 객체를 생성할 때는 기반 클래스 부분이 먼저 생성되고 파생 클래스 부분이 나중에 완성됩니다. 소멸 순서는 그 반대입니다.

```text
Base 생성자
→ Derived 멤버
→ Derived 생성자 본문
→ 사용
→ Derived 소멸자
→ Base 소멸자
```

생성자나 소멸자 안에서 가상 함수를 호출하고 가장 파생된 클래스의 동작을 기대해서는 안 됩니다. 생성 중에는 파생 클래스 부분이 아직 완성되지 않았고, 소멸 중에는 이미 파괴 단계에 들어갔기 때문입니다.

## 4. 오버라이딩, 오버로딩과 이름 가리기

### 오버라이딩

파생 클래스가 기반 클래스의 가상 함수와 같은 시그니처로 함수를 다시 정의합니다.

```cpp
class TextHandler : public Handler
{
public:
    virtual Response handle(const Request &request);
};
```

C++98에는 `override` 키워드가 없습니다. `const`, 참조 한정이나 인자 타입이 조금만 달라도 오버라이딩이 아니라 새 함수가 됩니다. 관련 컴파일러 경고를 활성화하고 기반 클래스 선언과 시그니처를 정확히 맞춥니다.

### 오버로딩

같은 범위에서 같은 이름의 함수를 인자 타입이나 개수로 구분합니다.

```cpp
void write(int value);
void write(const std::string &value);
```

### 이름 가리기

파생 클래스가 같은 이름의 함수를 하나라도 선언하면 기반 클래스의 다른 오버로드가 이름 탐색에서 숨겨질 수 있습니다.

```cpp
class Base
{
public:
    void write(int value);
};

class Derived : public Base
{
public:
    void write(const std::string &value); // Base::write가 숨겨짐
};
```

필요하면 클래스 범위의 `using` 선언으로 기반 클래스 오버로드를 다시 노출합니다.

```cpp
class Derived : public Base
{
public:
    using Base::write;
    void write(const std::string &value);
};
```

## 5. 포인터와 참조를 통한 가상 디스패치

```cpp
Handler &handler = putHandler;
Response response = handler.handle(request);
```

호출식의 정적 타입은 `Handler&`지만, 실제 객체의 동적 타입에 맞는 오버라이딩 함수가 선택됩니다.

객체를 기반 클래스 값으로 복사하면 파생 클래스 부분이 잘립니다.

```cpp
Base copy = derived; // 객체 슬라이싱
```

다형적 객체는 보통 포인터나 참조로 다룹니다. 이때 객체의 수명과 소유권을 별도로 결정해야 합니다.

## 6. 가상 소멸자

다음과 같이 기반 클래스 포인터로 객체를 삭제할 수 있다면 기반 클래스 소멸자는 가상이어야 합니다.

```cpp
Handler *handler = new PutHandler;
delete handler;
```

가상 소멸자가 없으면 위 삭제는 정의되지 않은 동작입니다. 파생 클래스 자원이 일부 누수되는 정도로 끝난다고 가정할 수 없습니다.

```cpp
class Handler
{
public:
    virtual ~Handler() {}
    virtual Response handle(const Request &) = 0;
};
```

기반 클래스 포인터로 삭제하지 못하게 할 타입이라면 보호된 비가상 소멸자 같은 정책을 사용할 수 있습니다. 다만 호출자가 그 수명 제약을 명확히 알 수 있어야 합니다.

## 7. 추상 클래스와 인터페이스

순수 가상 함수가 하나라도 있는 클래스는 추상 클래스이며 직접 생성할 수 없습니다.

```cpp
class Clock
{
public:
    virtual ~Clock() {}
    virtual long now() const = 0;
};
```

인터페이스는 구현이 가진 기능 목록이 아니라 호출자가 실제로 필요한 기능에 맞춰 작게 설계합니다. 사용하지 않는 함수까지 포함한 큰 인터페이스는 구현체와 테스트 대역을 불필요하게 복잡하게 만듭니다.

공통 상태와 구현을 가진 추상 기반 클래스도 만들 수 있습니다. 다만 그 상태가 모든 파생 클래스에 실제로 공통이며 같은 불변식을 따르는지 확인해야 합니다.

## 8. 조합과 상속 비교

다음 질문을 기준으로 선택합니다.

- 호출자가 여러 구현을 같은 인터페이스로 교체해야 합니까?
- 파생 클래스가 기반 클래스의 모든 공개 규칙을 지킬 수 있습니까?
- 관계가 “일종의 객체”입니까, 아니면 “부품으로 가진 객체”입니까?
- 공통 구현을 보조 함수나 멤버 객체에 위임할 수 있습니까?

다음 `LoggingStore`는 `Store`로 대체될 수 있도록 공개 상속을 사용하면서, 실제 저장 작업은 내부의 다른 `Store` 객체에 위임하는 데코레이터입니다. 인터페이스 구현에는 상속을, 기능 위임에는 조합을 함께 사용합니다.

```cpp
class LoggingStore : public Store
{
public:
    LoggingStore(Store &inner, std::ostream &log)
        : inner_(inner), log_(log)
    {}

    virtual PutResult put(const Key &key, const Value &value);

private:
    Store &inner_;
    std::ostream &log_;
};
```

구현 재사용만 필요하다면 상속 없이 보조 객체를 조합하는 편이 더 단순할 수 있습니다.

## 9. 다중 상속

다중 상속은 한 객체가 여러 기반 클래스의 인터페이스를 동시에 구현하게 합니다.

```cpp
class Readable
{
public:
    virtual ~Readable() {}
    virtual std::string read() const = 0;
};

class Writable
{
public:
    virtual ~Writable() {}
    virtual void write(const std::string &) = 0;
};

class Buffer : public Readable, public Writable
{
    // ...
};
```

작고 독립적인 인터페이스 여러 개를 구현하는 경우는 비교적 명확합니다. 상태를 가진 기반 클래스 여러 개를 상속하면 다음 문제가 복잡해집니다.

- 같은 이름의 멤버로 인한 모호성
- 여러 기반 클래스 하위 객체
- 포인터 조정
- 생성과 소멸 순서
- 공통 기반 클래스의 중복

## 10. 다이아몬드 상속과 가상 상속

```text
        Entity
       /      \
   Reader    Writer
       \      /
       Device
```

`Reader`와 `Writer`가 각각 `Entity`를 일반 상속하면 `Device` 안에는 `Entity` 하위 객체가 두 개 생깁니다. `Device`에서 `Entity` 멤버에 접근할 때 어느 경로의 객체인지 모호해질 수 있습니다.

가상 상속은 공통 기반 클래스 하위 객체를 하나만 공유합니다.

```cpp
class Reader : virtual public Entity {};
class Writer : virtual public Entity {};
class Device : public Reader, public Writer {};
```

이 경우 가장 파생된 클래스인 `Device`가 가상 기반 클래스 `Entity`를 초기화할 책임을 집니다. 동작을 이해하기 위해 학습할 필요는 있지만, 실제 설계에서는 복잡한 상태 상속 계층보다 작은 인터페이스와 조합을 먼저 검토합니다.

## 11. 다형적 복사와 `clone`

기반 클래스 포인터가 가리키는 실제 타입을 보존해 복사하려면 가상 `clone` 함수를 사용할 수 있습니다.

```cpp
class Handler
{
public:
    virtual ~Handler() {}
    virtual Handler *clone() const = 0;
    virtual Response handle(const Request &) = 0;
};

class PutHandler : public Handler
{
public:
    virtual PutHandler *clone() const
    {
        return new PutHandler(*this);
    }
};
```

C++에서는 오버라이딩 함수의 반환형을 더 구체적인 포인터나 참조 타입으로 좁히는 공변 반환형을 지원합니다. 그러나 `clone`은 동적 타입을 보존한 복사만 해결합니다. 반환 포인터의 소유자와 여러 복사 중 일부가 실패했을 때의 정리 방식은 별도로 정해야 합니다.

## 12. 팩터리

팩터리는 입력을 구체 타입 선택으로 변환합니다.

```cpp
class HandlerFactory
{
public:
    Handler *create(const std::string &name) const;
};
```

팩터리 인터페이스에서는 성공보다 실패와 소유권이 중요합니다.

- 알 수 없는 이름을 어떻게 보고합니까?
- 생성자 예외를 그대로 전달합니까, 다른 오류로 변환합니까?
- 성공 시 반환된 포인터를 누가 삭제합니까?
- 생성 후 등록 과정이 실패하면 누가 객체를 정리합니까?

생성 직후에는 지역 RAII 가드가 포인터를 소유하게 하고, 최종 소유자가 성공적으로 인수한 뒤에만 소유권을 넘깁니다. C++98의 `std::auto_ptr`는 단일 객체를 잠시 보호하는 데 사용할 수 있지만 복사 시 소유권이 이전되는 특수한 의미가 있으므로, 컨테이너 원소나 일반 값처럼 사용해서는 안 됩니다. 프로젝트 전용 범위 가드를 두는 편이 더 명확할 수 있습니다.

## 13. 의존성 주입

객체가 내부에서 구체 의존성을 직접 생성하면 구현 교체와 테스트가 어려워집니다.

```cpp
class Service
{
public:
    Service(Store &store, Clock &clock)
        : store_(store), clock_(clock)
    {}

private:
    Store &store_;
    Clock &clock_;
};
```

생성자 주입은 객체가 유효하려면 필요한 의존성을 생성 시점에 강제합니다. 주입된 참조는 소유하지 않으므로 참조 대상이 `Service`보다 오래 살아야 합니다.

모든 클래스를 인터페이스로 만들 필요는 없습니다. 실제로 구현을 교체해야 하거나 파일 시스템, 시간, 외부 프로세스 같은 경계를 격리할 때 사용합니다.

## 14. 콜백과 명령 디스패치

다형성 외에도 외부 동작을 전달하는 방법이 있습니다.

- 함수 포인터
- 멤버 함수 포인터
- 함수 객체
- Modern C++의 람다와 `std::function`

고정된 작은 명령 집합은 `switch`가 더 명확할 수 있습니다. 명령마다 독립적인 상태나 구현이 있고 새 명령이 자주 추가된다면 `Handler` 인터페이스가 유리할 수 있습니다. 분기를 없애는 것 자체가 목표는 아닙니다. 변경 책임을 적절한 위치로 옮겼는지가 기준입니다.

## 15. 대체 가능한 테스트 구현

- **스텁**: 정해진 응답을 반환합니다.
- **페이크**: 단순하지만 실제로 동작하는 대체 구현입니다.
- **목**: 호출 횟수나 순서 같은 상호작용을 검증합니다.

테스트만을 위해 의미 없는 인터페이스를 만들지 않습니다. 시간, 파일 시스템, 외부 프로세스처럼 실제 경계가 있는 의존성을 분리하면 테스트 가능성도 자연스럽게 생깁니다.

---

## 단계형 실습: 교체 가능한 명령 처리기

### 시작점

`CommandService`가 명령 이름을 `if` 연쇄로 분기하는 코드에서 시작합니다.

### 1단계: 작은 인터페이스

```cpp
class Handler
{
public:
    virtual ~Handler() {}
    virtual Response handle(
        const Request &request,
        KeyValueStore &store) const = 0;
};
```

### 2단계: 구체 핸들러

- `PutHandler`
- `GetHandler`
- `DeleteHandler`
- `ListHandler`
- `QuitHandler`

### 3단계: `Router`

명령 이름과 비소유 `Handler*`를 연결합니다. 핸들러의 실제 소유자는 별도로 둡니다.

### 4단계: 변경 요구사항

- 존재하지 않는 명령을 처리하는 기본 핸들러
- 읽기 전용 저장소 구현
- 요청을 기록하는 데코레이터
- 팩터리로 핸들러 생성
- `Clock`을 주입해 응답에 시각 추가

### 5단계: 설계 비교

같은 요구사항을 `switch` 버전에도 적용하고 수정 범위, 객체 수와 테스트 난이도를 비교합니다. 다형성 버전이 항상 더 낫다고 결론 내리지 않습니다.

## 상속과 소멸에서 자주 발생하는 오류

- 기반 클래스 소멸자가 가상이 아닌데 기반 클래스 포인터로 삭제합니다.
- 값 컨테이너에 기반 클래스 객체를 저장해 슬라이싱을 일으킵니다.
- 시그니처가 달라 오버라이딩 대신 새 함수를 만듭니다.
- 구현 재사용만을 위해 공개 상속을 사용합니다.
- 다이아몬드 상속에서 공통 기반 클래스 객체가 하나라고 근거 없이 가정합니다.
- 팩터리가 반환한 포인터의 소유자를 정하지 않습니다.
- 의존성을 주입했지만 참조 대상이 먼저 파괴됩니다.
- 모든 구체 클래스에 의미 없는 인터페이스를 추가합니다.

## Java·Rust와 비교하는 다형성

C++의 순수 가상 기반 클래스는 Java·C#의 인터페이스, Swift의 프로토콜, Rust의 트레이트 객체와 비슷한 역할을 합니다. 다만 C++에서는 객체 수명과 삭제 정책까지 인터페이스 설계에 포함됩니다. 가비지 컬렉션을 사용하는 언어에서도 대체 가능성, 작은 인터페이스, 조합과 생성자 주입의 원칙은 그대로 적용됩니다.

## 다형적 객체의 수명 점검

- 오버라이딩, 오버로딩과 이름 가리기를 코드로 구분할 수 있습니까?
- 기반 클래스 포인터를 통한 삭제가 안전하려면 어떤 조건이 필요합니까?
- 객체 슬라이싱과 `clone`이 해결하는 문제는 어떻게 다릅니까?
- 현재 상속 관계를 조합으로 바꿀 수 있습니까?
- 다이아몬드 상속에서 공통 기반 클래스 하위 객체가 몇 개인지 설명할 수 있습니까?
- 새 구체 핸들러를 추가할 때 기존 호출자를 수정해야 합니까?
- 인터페이스가 실제 호출자에게 필요한 기능보다 크지 않습니까?
