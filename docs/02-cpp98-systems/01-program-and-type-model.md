# C++ 프로그램과 타입의 기본 모델

## 먼저 프로그램이 만들어지는 과정을 이해합니다

C 경험이 있어도 C++에서는 빌드 구조와 타입 규칙에서 자주 막힙니다. 헤더에 무엇을 둘지, 선언과 정의가 왜 구분되는지, 참조와 포인터를 언제 사용할지 모르면 작은 클래스도 파일별로 안정적으로 나누기 어렵습니다. 여러 소스 파일이 하나의 실행 파일이 되는 과정을 따라가며 오류가 발생한 단계를 좁힙니다.

## 소스 코드에서 실행 파일까지

```text
헤더의 선언 ─┐
             ├→ 번역 단위별 컴파일 → 오브젝트 파일 → 링크 → 실행 파일
.cpp의 정의 ─┘

값·참조·포인터·const → 함수 인터페이스 → 클래스의 공개 경계
```

첫 번째 줄은 프로그램이 만들어지는 과정이고, 두 번째 줄은 타입이 잘못된 사용을 어느 경계에서 막는지 보여 줍니다.

## 명령행 도구로 타입 모델 확인

이 문서와 연결된 실습은 [절차적 명령 처리기](../../exercises/02-cpp98-systems/object-model/command-service/01-procedural/README.md)입니다.

저장소 루트에서 다음 명령을 실행합니다.

```sh
cd exercises/02-cpp98-systems/object-model/command-service/01-procedural
make observe       # 선택: 소스를 열지 않고 입출력만 관찰합니다.
```

`make observe`는 선택적으로 사용하는 블랙박스 기준 프로그램입니다. 먼저 출력과 오류를 예상하고 `reference/` 소스는 열지 않은 채 실행 결과만 관찰합니다. [트랙 로드맵](00-roadmap.md)에 따라 만든 워크스페이스의 `skeleton/main.cpp` TODO를 구현한 뒤 저장소 루트에서 다음 명령으로 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/01-procedural
```

학습자 구현 검증을 통과한 뒤에만 참조 구현과 비교합니다. 실패 실험에서는 입력 종료 검사를 제거하거나 멤버 함수 포인터 호출식을 일반 함수 포인터처럼 바꿔 보고, 컴파일러와 실행 결과가 어느 단계에서 문제를 드러내는지 기록합니다.

---

## 1. 소스 파일과 번역 단위

컴파일러는 프로젝트 전체를 한 번에 읽지 않습니다. 각 `.cpp` 파일은 전처리 과정에서 자신이 `#include`한 헤더 내용이 반영된 뒤 **독립된 번역 단위**로 컴파일됩니다.

```text
main.cpp + 포함한 헤더  → main.o
store.cpp + 포함한 헤더 → store.o
main.o + store.o         → 실행 파일
```

이 모델에서는 실패가 크게 두 단계로 나뉩니다.

- **컴파일 오류**: 하나의 번역 단위 안에서 문법, 이름, 타입이 잘못됐습니다.
- **링크 오류**: 선언에 대응하는 정의를 찾지 못했거나 같은 정의가 중복됐습니다.

`undefined reference`는 선언한 함수를 구현하지 않았거나, 구현 파일 또는 라이브러리를 링크하지 않았거나, 선언과 정의의 시그니처가 다른 경우 등에 발생할 수 있습니다.

## 2. 선언과 정의

선언은 이름과 타입을 컴파일러에 알립니다. 정의는 함수 본문이나 객체의 실제 저장 공간을 제공합니다.

```cpp
// 선언
int parsePort(const std::string &text);

// 정의
int parsePort(const std::string &text)
{
    // ...
    return 0;
}
```

클래스 선언도 멤버의 이름과 타입을 알립니다. 인라인으로 정의하지 않을 멤버 함수의 본문은 일반적으로 `.cpp` 파일에 둡니다.

```cpp
// Counter.hpp
#ifndef COUNTER_HPP
#define COUNTER_HPP

class Counter
{
public:
    Counter();
    void increment();
    int value() const;

private:
    int value_;
};

#endif
```

```cpp
// Counter.cpp
#include "Counter.hpp"

Counter::Counter() : value_(0) {}

void Counter::increment()
{
    ++value_;
}

int Counter::value() const
{
    return value_;
}
```

## 3. 헤더의 책임

헤더에는 다른 번역 단위가 코드를 컴파일하는 데 필요한 공개 인터페이스를 둡니다.

- 클래스와 함수 선언
- 공개 인터페이스에 필요한 타입 선언
- 실제로 인라인 정의가 필요한 짧은 함수
- 템플릿 정의

다음 내용은 피합니다.

- 전역 범위의 `using namespace`
- 소유권이 불명확한 전역 객체
- 구현에서만 필요한 헤더의 불필요한 포함
- 여러 번역 단위에 중복 정의될 수 있는 비인라인 함수 본문

### 포함 가드

같은 헤더가 하나의 번역 단위에 여러 경로로 포함되더라도 내용이 한 번만 처리되게 합니다.

```cpp
#ifndef REQUEST_HPP
#define REQUEST_HPP

// 선언

#endif
```

### 전방 선언

클래스의 포인터나 참조만 선언할 때는 완전한 타입 정의가 필요하지 않을 수 있습니다.

```cpp
class Logger;

class Service
{
public:
    explicit Service(Logger &logger);

private:
    Logger &logger_;
};
```

객체를 값으로 멤버에 저장하거나 타입의 크기와 구성을 알아야 하는 코드에서는 해당 타입의 실제 헤더를 포함해야 합니다.

## 4. 네임스페이스

`namespace`는 관련된 이름을 하나의 논리 영역에 묶습니다.

```cpp
namespace protocol
{
    class Request;
    Request parse(const std::string &line);
}
```

호출 코드는 `protocol::parse`처럼 어느 영역의 함수를 사용하는지 드러낼 수 있습니다. 공개 헤더나 넓은 범위에서 `using namespace`를 사용하면 같은 이름의 출처가 불분명해지고 충돌 가능성이 커집니다.

## 5. 문자열과 스트림

`std::string`은 길이와 저장 공간을 직접 관리하는 값 타입입니다. C API와의 연동 등 특별한 이유가 없다면 직접 관리하는 문자 배열보다 먼저 고려합니다.

```cpp
std::string line;
if (!std::getline(std::cin, line))
{
    std::cerr << "입력이 끝났습니다\n";
}
```

스트림은 데이터뿐 아니라 EOF, 형식 변환 실패, I/O 오류 상태도 가집니다. 입력 함수가 실패한 뒤 이전 변수 값을 다시 처리하지 않도록 반환 상태를 검사합니다.

출력 함수가 전역 `std::cout`에 직접 쓰는 대신 출력 스트림을 인자로 받으면 테스트와 재사용이 쉬워집니다.

```cpp
void writeResult(std::ostream &out, const std::string &value)
{
    out << value << '\n';
}
```

## 6. 초기화와 대입

초기화는 객체의 수명을 시작합니다. 대입은 이미 존재하는 객체의 값을 변경합니다.

```cpp
std::string first("alpha"); // 직접 초기화
std::string second(first);   // 복사 생성
second = first;              // 복사 대입
```

클래스 멤버는 생성자 본문이 실행되기 전에 이미 초기화됩니다. 따라서 생성자 본문에서 대입하기보다 멤버 초기화 리스트를 사용합니다.

```cpp
class User
{
public:
    User(const std::string &name, int level)
        : name_(name), level_(level)
    {}

private:
    std::string name_;
    int level_;
};
```

멤버의 실제 초기화 순서는 초기화 리스트에 적은 순서가 아니라 **클래스에 선언된 순서**입니다.

## 7. 값, 참조, 포인터

### 값

```cpp
void consume(Request request);
```

함수는 별도의 객체를 받습니다. C++98에서는 복사가 발생할 수 있으며 함수 안에서 값을 변경해도 호출자가 넘긴 원본과는 독립적입니다.

### 참조

```cpp
void normalize(Request &request);
void inspect(const Request &request);
```

- `T&`: 기존 객체를 받아 직접 변경할 수 있습니다.
- `const T&`: 기존 객체를 복사하지 않고 읽습니다.

참조는 정상적인 사용에서 null을 나타내지 않으며 초기화 후 다른 객체를 가리키도록 다시 지정할 수 없습니다. 참조 대상은 참조를 사용하는 동안 살아 있어야 합니다.

### 포인터

```cpp
Request *findRequest(int id);
```

포인터는 대상이 없을 수 있음을 표현하거나 배열·저수준 API와 연결할 때 유용합니다. 그러나 `T*`만으로는 해당 포인터가 자원을 소유하는지 잠시 관찰하는지 알 수 없습니다. 소유권과 유효 기간을 별도 인터페이스 규칙으로 명시해야 합니다.

## 8. `const`로 변경 경계 표현

멤버 함수 뒤의 `const`는 반환값이 아니라 `*this`를 통해 객체의 논리적 상태를 변경하지 않는다는 인터페이스 약속입니다.

```cpp
class Entry
{
public:
    const std::string &name() const;
};
```

포인터에서는 `const`가 적용되는 위치를 구분합니다.

```cpp
int value = 0;
const int *p1 = &value;       // p1을 통해 가리키는 int를 수정하지 않음
int *const p2 = &value;       // 포인터 p2 자체를 다른 주소로 바꾸지 않음
const int *const p3 = &value; // 가리키는 값과 포인터 자체를 모두 변경하지 않음
```

`const`가 붙은 위치에 따라 서로 다른 변경 제한을 표현합니다.

## 9. 함수 오버로딩

함수 이름이 같아도 매개변수의 타입이나 개수가 다르면 오버로드할 수 있습니다.

```cpp
void print(int value);
void print(const std::string &value);
```

반환 타입만 다른 함수는 오버로드할 수 없습니다. 여러 암묵 변환 후보가 있으면 호출이 모호하거나 예상하지 않은 오버로드가 선택될 수 있으므로, 변환을 의도하지 않는 단일 인자 생성자에는 `explicit`를 사용합니다.

```cpp
class Port
{
public:
    explicit Port(int value);
};
```

## 10. 클래스의 최소 모델

클래스는 필드를 숨기는 문법이 아니라 **유효한 상태와 허용된 동작을 정의하는 경계**입니다.

```cpp
class Balance
{
public:
    explicit Balance(long initial) : amount_(initial)
    {
        if (initial < 0)
            throw std::invalid_argument("negative initial balance");
    }

    bool withdraw(long value)
    {
        if (value <= 0 || value > amount_)
            return false;
        amount_ -= value;
        return true;
    }

    long amount() const { return amount_; }

private:
    long amount_;
};
```

이 예제를 컴파일하려면 `<stdexcept>`를 포함해야 합니다. `amount_`를 공개하면 모든 호출자가 잔액 불변식을 직접 지켜야 합니다. 생성자와 `withdraw`로 변경 경로를 제한하면 검사를 한곳에 모을 수 있습니다.

## 11. 함수 포인터와 멤버 함수 포인터

명령 집합이 작고 고정되어 있다면 `if` 연쇄가 가장 단순할 수 있습니다. 명령과 함수의 대응을 데이터처럼 저장해야 한다면 함수 포인터를 사용할 수 있습니다.

```cpp
int add(int left, int right) { return left + right; }

typedef int (*BinaryOp)(int, int);
BinaryOp op = &add;
int result = op(2, 3);
```

비정적 멤버 함수에는 대상 객체를 나타내는 숨은 `this` 인자가 있으므로 일반 함수 포인터와 타입 및 호출 문법이 다릅니다.

```cpp
class Machine
{
public:
    void start() { std::cout << "start\n"; }
    void stop()  { std::cout << "stop\n"; }
};

typedef void (Machine::*Action)();

Machine machine;
Action action = &Machine::start;
(machine.*action)();
```

객체 포인터를 사용한다면 `(pointer->*action)()`으로 호출합니다. 이 개념은 콜백과 명령 객체를 이해하는 기반이며, 이후 언어 표준의 `std::function`과도 연결됩니다.

## 12. 최소 Makefile

```make
NAME := command_app
CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror

SRCS := main.cpp Parser.cpp Store.cpp
OBJS := $(SRCS:.cpp=.o)

.PHONY: all clean

all: $(NAME)

$(NAME): $(OBJS)
	$(CXX) $(CXXFLAGS) $(OBJS) -o $@

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(NAME)

```

Make는 단순한 명령 모음이 아니라 파일 의존성과 수정 시각을 바탕으로 필요한 산출물만 다시 만드는 도구입니다. 헤더 자동 의존성과 플랫폼별 분기는 부록에서 다룹니다.

---

## 작은 실습: 절차적 명령 처리기

다음 명령을 한 줄씩 받는 프로그램을 작성합니다.

```text
PUT key value
GET key
DELETE key
LIST
COUNT
QUIT
```

첫 버전에서는 하나의 `main`, `if` 또는 `switch`, `std::map<std::string, std::string>`을 사용해도 됩니다. 이 단계의 목표는 객체 설계가 아니라 입력, 분기, 출력, 빌드를 안정적으로 구성하는 것입니다.

### 진행 순서

1. 먼저 결과를 예상하고 완성된 단일 파일 프로그램을 블랙박스로 실행합니다.
2. 입력 분리 함수만 보지 않고 직접 다시 작성합니다.
3. 코드를 `main.cpp`, `Parser.cpp`, `Store.cpp`로 나눕니다.
4. 새 명령 `COUNT`를 추가합니다.
5. 인자 수가 잘못됐을 때의 결과를 예상하고 검증합니다.

## 컴파일·링크 단계에서 자주 발생하는 문제

- 헤더에 비인라인 함수를 정의해 중복 심볼이 발생합니다.
- 선언은 추가했지만 구현 파일을 링크 타깃에 넣지 않습니다.
- `std::getline` 실패 후 이전 문자열을 다시 처리합니다.
- `const T&`가 참조 대상보다 오래 살아남습니다.
- 단일 인자 생성자의 암묵 변환 때문에 예상과 다른 오버로드가 선택됩니다.
- 멤버 함수 포인터를 일반 함수 포인터처럼 호출합니다.

## 다른 언어와 비교

번역 단위와 링크 모델은 Python이나 JavaScript보다 C와 Rust에 가깝습니다. 반면 네임스페이스, 공개 인터페이스, 읽기 전용 참조를 통해 변경 범위를 제한하는 설계 원칙은 Java 패키지, C# 네임스페이스, Kotlin 클래스에서도 형태를 달리해 나타납니다. 문법이 달라져도 외부에 어떤 이름과 타입을 공개할지는 항상 결정해야 합니다.

## 프로그램·타입 모델 점검

- 헤더를 수정했을 때 어느 `.cpp` 파일을 다시 컴파일해야 합니까?
- 선언과 정의를 각각 한 문장으로 설명할 수 있습니까?
- `T`, `T&`, `const T&`, `T*` 중 하나를 선택한 이유를 설명할 수 있습니까?
- 멤버 초기화 리스트가 생성자 본문 대입보다 앞서 실행되는 이유는 무엇입니까?
- 함수 포인터와 멤버 함수 포인터의 호출 문법이 다른 이유는 무엇입니까?
- 컴파일 오류와 링크 오류는 각각 어디부터 조사해야 합니까?
