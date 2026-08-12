# C++ 프로그램과 타입의 기본 모델

## 프로그램이 만들어지는 과정을 먼저 살펴봅니다

C를 아는 개발자도 C++에서는 빌드 구조와 타입 규칙부터 막히기 쉽습니다. 헤더에 무엇을 두는지, 선언과 정의가 왜 다른지, 참조와 포인터를 어떻게 구분하는지 모르면 작은 클래스도 안정적으로 나누기 어렵습니다. 여러 파일이 실행 파일로 이어지는 경로를 따라가며 오류가 생긴 단계를 좁힙니다.

## 소스 코드에서 실행 파일까지

```text
header의 선언 ─┐
               ├→ 번역 단위별 컴파일 → object file → link → 실행 파일
.cpp의 정의  ──┘

값·참조·포인터·const → 함수 계약 → class의 공개 경계
```

첫 줄은 프로그램이 만들어지는 경로이고, 둘째 줄은 타입이 잘못된 사용을 어디서 막는지를 보여 줍니다.

## 명령줄 도구로 타입 모델 확인

이 문서의 실행 단위는 [절차적 명령 처리기](../../exercises/02-cpp98-systems/object-model/command-service/01-procedural/README.md)입니다.

```sh
cd exercises/02-cpp98-systems/object-model/command-service/01-procedural
make observe       # 선택: source를 열지 않고 입출력만 관찰합니다.
```

위 명령은 저장소 루트에서 시작합니다. `make observe`는 선택적인 black-box oracle입니다. 먼저 출력과 오류를 예상하고, `reference/` source는 열지 않은 채 실행 결과만 관찰합니다. [트랙 roadmap](00-roadmap.md)에 따라 만든 workspace의 `skeleton/main.cpp` TODO를 채운 뒤, 다시 저장소 루트에서 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/01-procedural
```

learner 검증을 통과한 뒤에만 reference source와 비교합니다. 실패 실험에서는 입력 종료 검사를 제거하거나 멤버 함수 포인터 호출식을 일반 함수 포인터처럼 바꾸고, 컴파일러와 실행 결과가 어느 경계에서 문제를 드러내는지 기록합니다.

---

## 1. 소스 파일과 번역 단위

컴파일러는 프로젝트 전체를 한 번에 읽지 않습니다. 각 `.cpp` 파일은 자신이 `#include`한 헤더의 내용이 복사된 뒤 **독립된 번역 단위**로 컴파일됩니다.

```text
main.cpp + 포함된 헤더 → main.o
store.cpp + 포함된 헤더 → store.o
main.o + store.o         → 실행 파일
```

이 모델에서 두 종류의 실패가 갈립니다.

- **컴파일 오류**: 한 번역 단위 안에서 문법이나 타입이 잘못됐습니다.
- **링크 오류**: 선언은 보였지만 실제 정의를 찾지 못했거나 정의가 중복됐습니다.

`undefined reference`는 대개 헤더 문제가 아니라 “선언된 함수를 구현하지 않았거나 구현 파일을 링크하지 않았다”는 뜻입니다.

## 2. 선언과 정의

선언은 이름과 타입을 알립니다. 정의는 실제 함수 본문이나 저장 공간을 제공합니다.

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

클래스 선언도 멤버의 존재와 타입을 알립니다. 비인라인 멤버 함수의 본문은 보통 `.cpp`에 둡니다.

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

헤더에는 다른 번역 단위가 컴파일하기 위해 알아야 하는 **공개 계약**을 둡니다.

- 클래스와 함수 선언
- 필요한 타입의 선언
- 짧고 실제로 inline이어야 하는 함수
- 템플릿 정의

다음은 피합니다.

- 전역 `using namespace`
- 소유권이 불명확한 전역 객체
- 구현에만 필요한 헤더의 무분별한 포함
- 동일한 비인라인 함수 정의를 여러 번 만들 수 있는 본문

### 포함 가드

헤더가 한 번역 단위에 여러 번 포함되어도 한 번만 처리되게 합니다.

```cpp
#ifndef REQUEST_HPP
#define REQUEST_HPP

// 선언

#endif
```

### 전방 선언

포인터나 참조만 선언할 때는 완전한 클래스 정의가 필요하지 않을 수 있습니다.

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

객체를 값으로 멤버에 저장하거나 크기를 알아야 하면 실제 헤더를 포함해야 합니다.

## 4. 네임스페이스

`namespace`는 이름을 논리 영역에 묶습니다.

```cpp
namespace protocol
{
    class Request;
    Request parse(const std::string &line);
}
```

호출자는 `protocol::parse`처럼 어느 계약을 쓰는지 드러낼 수 있습니다. 공개 헤더와 넓은 범위에서 `using namespace`를 사용하면 같은 이름이 어디서 왔는지 흐려집니다.

## 5. 문자열과 스트림

C++의 `std::string`은 크기와 저장 공간을 스스로 관리하는 값 타입입니다. 문자열을 직접 소유할 이유가 특별히 없다면 C 배열보다 우선합니다.

```cpp
std::string line;
if (!std::getline(std::cin, line))
{
    std::cerr << "입력이 끝났습니다\n";
}
```

스트림은 데이터뿐 아니라 EOF, 형식 실패, I/O 실패 상태도 가집니다. 입력 함수가 실패했는데 이전 변수 값을 계속 사용하지 않도록 반환 상태를 검사합니다.

출력 함수가 전역 `std::cout`에 직접 쓰게 하기보다 스트림을 인자로 받으면 테스트와 재사용이 쉬워집니다.

```cpp
void writeResult(std::ostream &out, const std::string &value)
{
    out << value << '\n';
}
```

## 6. 초기화와 대입

초기화는 객체의 수명을 시작합니다. 대입은 이미 존재하는 객체의 값을 바꿉니다.

```cpp
std::string first("alpha");  // 초기화
std::string second(first);    // 복사 초기화
second = first;               // 대입
```

클래스 멤버는 생성자 본문에 들어오기 전에 이미 초기화됩니다. 따라서 멤버 초기화 리스트를 사용합니다.

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

멤버의 실제 초기화 순서는 리스트의 표기 순서가 아니라 **클래스에 선언된 순서**입니다.

## 7. 값, 포인터와 참조

### 값

```cpp
void consume(Request request);
```

함수는 별도 객체를 받습니다. 복사가 일어날 수 있고, 함수가 변경해도 호출자 객체와 독립적일 수 있습니다.

### 참조

```cpp
void normalize(Request &request);
void inspect(const Request &request);
```

- `T&`: 기존 객체를 반드시 받아 변경할 수 있습니다.
- `const T&`: 기존 객체를 복사하지 않고 읽습니다.

참조는 널을 표현하지 않고 선언 뒤 다른 객체를 가리키도록 바꿀 수 없습니다.

### 포인터

```cpp
Request *findRequest(int id);
```

포인터는 “없음”을 표현하거나 배열·낮은 수준 API와 연결할 때 유용합니다. 하지만 `T*`만으로는 소유자인지 빌려 쓰는지 알 수 없습니다. 소유권은 별도 계약으로 명확히 해야 합니다.

## 8. `const`로 표현하는 변경 경계

멤버 함수 뒤의 `const`는 반환값이 아니라 `*this`를 변경하지 않는다는 약속입니다.

```cpp
class Entry
{
public:
    const std::string &name() const;
};
```

포인터에서는 어느 부분이 const인지 구분합니다.

```cpp
int value = 0;
const int *p1 = &value;       // 가리키는 int를 수정하지 않음
int *const p2 = &value;       // 포인터 자체를 바꾸지 않음
const int *const p3 = &value; // 둘 다 변경하지 않음
```

실제 코드에서는 널인 const 포인터를 만들 이유가 드뭅니다. 중요한 점은 `const`가 붙은 위치에 따라 다른 계약이 된다는 것입니다.

## 9. 함수 오버로딩

같은 이름을 인자 타입이나 개수로 구분할 수 있습니다.

```cpp
void print(int value);
void print(const std::string &value);
```

반환 타입만 다른 함수는 오버로드할 수 없습니다. 암묵 변환 후보가 여러 개면 호출이 모호해질 수 있으므로, 단일 인자 생성자는 필요한 경우 `explicit`로 막습니다.

```cpp
class Port
{
public:
    explicit Port(int value);
};
```

## 10. 클래스의 최소 모델

클래스는 필드를 숨기는 문법이 아니라 **유효한 상태와 허용된 동작의 경계**입니다.

```cpp
class Balance
{
public:
    explicit Balance(long initial) : amount_(initial) {}

    bool withdraw(long value)
    {
        if (value < 0 || value > amount_)
            return false;
        amount_ -= value;
        return true;
    }

    long amount() const { return amount_; }

private:
    long amount_;
};
```

`amount_`를 공개으로 두면 모든 호출자가 불변식을 지켜야 합니다. `withdraw`로 변경 경로를 모으면 규칙을 한곳에서 검증합니다.

## 11. 함수 포인터와 멤버 함수 포인터

작은 명령 집합을 `if` 연쇄로 처리할 수 있습니다. 분기가 고정되고 작다면 그것이 가장 단순합니다. 명령과 함수의 대응을 데이터처럼 다루고 싶다면 함수 포인터를 쓸 수 있습니다.

```cpp
int add(int left, int right) { return left + right; }

typedef int (*BinaryOp)(int, int);
BinaryOp op = &add;
int result = op(2, 3);
```

멤버 함수에는 숨은 객체 인자 `this`가 있으므로 타입이 다릅니다.

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

포인터로 객체를 가지고 있다면 `(pointer->*action)()`을 사용합니다. 이 문법은 이후의 콜백, command 객체, `std::function`과 같은 동작 전달의 출발점입니다.

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

Make는 명령 모음이 아니라 파일 의존성과 수정 시각을 이용해 필요한 산출물만 다시 만드는 도구입니다. 헤더 자동 의존성과 플랫폼 분기는 보조 문서에서 다룹니다.

---

## 작은 실습: 절차적 명령 처리기

다음 명령을 한 줄씩 받는 프로그램을 만듭니다.

```text
PUT key value
GET key
DELETE key
LIST
COUNT
QUIT
```

첫 버전에서는 하나의 `main`, `if` 또는 `switch`, `std::map<std::string, std::string>`을 사용해도 됩니다. 목표는 좋은 객체 설계가 아니라 입력·분기·출력과 빌드를 안정적으로 만드는 것입니다.

### 진행 순서

1. 먼저 결과를 예상하고 완성된 한 파일 프로그램을 black-box로 실행합니다.
2. 입력 분리 함수만 가리고 다시 작성합니다.
3. `main.cpp`, `Parser.cpp`, `Store.cpp`로 나눕니다.
4. 새 명령 `COUNT`를 추가합니다.
5. 잘못된 인자 수가 들어올 때 결과를 예상하고 검사합니다.

## 컴파일·링크 단계에서 자주 생기는 오류

- 헤더에 정의한 비인라인 함수 때문에 중복 심볼이 발생합니다.
- 선언은 추가했지만 구현 파일을 링크하지 않습니다.
- `std::getline` 실패 뒤 이전 문자열을 다시 처리합니다.
- `const T&`가 가리키는 객체보다 오래 살아남습니다.
- 단일 인자 생성자의 암묵 변환 때문에 오버로드가 예상과 다르게 선택됩니다.
- 멤버 함수 포인터를 일반 함수 포인터처럼 호출합니다.

## Python·Java와 비교하는 실행 모델

번역 단위와 링크 모델은 JavaScript나 Python보다 C, Rust와 가깝습니다. 반면 네임스페이스, 클래스의 공개 계약, 읽기 전용 참조라는 설계 목적은 Java 패키지, C# 네임스페이스, Kotlin 클래스에서도 그대로 유지됩니다. 언어가 바뀌면 문법은 달라져도 “어떤 이름과 타입을 외부에 공개할 것인가”라는 질문은 남습니다.

## 프로그램·타입 모델 점검

- 헤더를 수정했을 때 어떤 `.cpp`가 다시 컴파일되어야 합니까?
- 선언과 정의를 각각 한 문장으로 설명할 수 있습니까?
- `T`, `T&`, `const T&`, `T*` 중 하나를 고른 이유를 말할 수 있습니까?
- 초기화 리스트가 생성자 본문 대입보다 앞서는 이유는 무엇입니까?
- 함수 포인터와 멤버 함수 포인터의 호출 형태가 다른 이유는 무엇입니까?
- 컴파일 오류와 링크 오류의 첫 조사 지점이 어떻게 다른가?
