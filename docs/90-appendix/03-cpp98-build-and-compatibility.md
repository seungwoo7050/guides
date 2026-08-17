# C++98 호환 개발 참고 자료

## 이 문서를 사용하는 경우

C++98로 작성된 코드를 유지보수하거나 최신 언어 기능 없이 객체 수명과 소유권을 직접 다뤄 볼 때 참고합니다. GNU Make로 빌드하는 방법과 같은 의도를 Modern C++에서 더 명확하게 표현하는 방법도 함께 설명합니다.

핵심 원칙은 두 가지입니다.

1. 시대적인 문법 제약과 언어에 독립적인 설계 원칙을 구분합니다.
2. Modern C++ 기능을 흉내 내기보다 C++98에서 명확하고 검증 가능한 표현을 사용합니다.

---

## 1. C++98과 C++03

C++03은 C++98의 결함을 수정하고 일부 규칙을 명확히 한 개정판에 가깝습니다. 대규모 언어 기능이 추가된 버전은 아닙니다. 사용하는 컴파일 옵션이 `-std=c++98`인지 `-std=c++03`인지 확인하고, 둘 사이의 차이에 의존하는 코드는 대상 컴파일러에서 별도로 검증합니다.

```sh
c++ -std=c++98 -Wall -Wextra -Werror main.cpp
```

컴파일러 기본값에 맡기면 람다, `nullptr`, 범위 기반 `for` 같은 최신 기능이 의도치 않게 들어갈 수 있습니다. 표준 버전을 플래그로 고정합니다.

## 2. C++98에 없는 주요 기능

| Modern C++ 기능 | C++98 상태 | C++98의 일반적인 표현 |
|---|---|---|
| `nullptr` | 없음 | `0`, 필요한 C API에서 `NULL` |
| 타입 추론 `auto` | 없음 | 타입 명시 |
| 범위 기반 `for` | 없음 | 반복자 루프 |
| 람다 | 없음 | 함수 포인터 또는 함수 객체 |
| `enum class` | 없음 | 클래스·네임스페이스 범위의 열거형 |
| `override`, `final` | 없음 | 정확한 시그니처와 컴파일러 경고 |
| `= delete` | 없음 | 비공개 복사 선언 |
| `= default` | 없음 | 생략하거나 직접 구현 |
| 이동 의미론 | 없음 | 복사, `swap`, 명시적인 소유권 인계 |
| `unique_ptr` | 없음 | 복사 금지 RAII 소유자 |
| `std::optional` | 없음 | 결과 객체, `bool`과 출력 매개변수, 별도 상태 |
| 가변 인자 템플릿 | 없음 | 고정 인자 오버로드 |
| `std::type_traits` | 없음 | 필요한 특성만 직접 구현 |

기능이 없다고 개념까지 없는 것은 아닙니다. 단독 소유, 읽기 전용 경계, 콜백, 값의 부재와 타입 특성은 다른 문법으로 표현할 수 있습니다.

## 3. 널 포인터

C++98에서는 정수 상수 표현식 `0`을 널 포인터 상수로 사용할 수 있습니다.

```cpp
Widget *widget = 0;
```

`NULL`은 구현에 따라 정수 매크로이므로 오버로드에서 예상과 다른 함수가 선택될 수 있습니다.

```cpp
void call(int);
void call(Widget *);

call(NULL); // int 오버로드가 선택될 수 있음
```

C++98 C++ 코드에서는 일반적으로 `0`을 사용하고, C API나 프로젝트 규칙이 `NULL`을 요구할 때만 일관되게 사용합니다. Modern C++의 `nullptr`는 포인터 전용 타입이라 이 모호성을 해결합니다.

## 4. 복사 금지

C++98에는 `= delete`가 없습니다. 복사가 의미 없는 소유자는 복사 생성자와 복사 대입 연산자를 비공개로 선언하고 정의하지 않습니다.

```cpp
class File
{
public:
    File(const char *path);
    ~File();

private:
    File(const File &);
    File &operator=(const File &);
};
```

외부에서 복사를 시도하면 접근 오류가 발생합니다. 클래스 내부나 친구 함수에서 실수로 호출하면 정의가 없어 링크 오류가 날 수 있습니다. Modern C++의 `= delete`는 같은 의도를 모든 호출 위치에서 더 직접적으로 진단합니다.

```cpp
File(const File &) = delete;
File &operator=(const File &) = delete;
```

## 5. C++98 RAII 소유자

```cpp
class OwnedPointer
{
public:
    explicit OwnedPointer(Widget *value) : value_(value) {}
    ~OwnedPointer() { delete value_; }

    Widget *get() const { return value_; }

    Widget *release()
    {
        Widget *result = value_;
        value_ = 0;
        return result;
    }

private:
    OwnedPointer(const OwnedPointer &);
    OwnedPointer &operator=(const OwnedPointer &);

    Widget *value_;
};
```

이 타입은 단일 객체의 단독 소유만 표현하는 최소 형태입니다. 배열, 사용자 정의 해제 함수와 다형적 삭제까지 한 타입에 억지로 넣으면 범용 스마트 포인터를 다시 구현하는 수준으로 복잡해집니다. 필요한 자원에 맞는 작은 소유자를 작성합니다.

기반 클래스 포인터를 소유하고 삭제한다면 기반 클래스 소멸자가 가상인지 확인합니다. 배열에는 `delete[]`를 사용하는 별도 소유자가 필요합니다. Modern C++에서는 이런 차이를 `std::unique_ptr<T>`와 `std::unique_ptr<T[]>`가 표현합니다.

C++98의 `std::auto_ptr`는 복사 시 소유권이 이전되는 특수한 의미 때문에 값처럼 다루기 어렵고 표준 컨테이너 원소로 사용할 수 없습니다. 그 동작을 이해하지 않은 채 `unique_ptr` 대용으로 사용하지 않습니다.

## 6. 함수 객체와 람다의 관계

C++98 함수 객체:

```cpp
class PrefixMatch
{
public:
    explicit PrefixMatch(const std::string &prefix)
        : prefix_(prefix)
    {}

    bool operator()(const std::string &value) const
    {
        return value.compare(0, prefix_.size(), prefix_) == 0;
    }

private:
    std::string prefix_;
};
```

Modern C++ 람다:

```cpp
const std::string prefix = "GET";
auto match = [prefix](const std::string &value) {
    return value.compare(0, prefix.size(), prefix) == 0;
};
```

둘 다 상태를 가진 호출 가능 객체입니다. 람다를 사용할 수 없는 환경에서도 콜백과 알고리즘 정책을 같은 모델로 설계할 수 있습니다.

## 7. 열거형 이름 범위 제한

C++98 열거형은 정수로 암묵 변환되고 열거자 이름이 주변 범위에 들어옵니다. 전역 이름 충돌을 줄이기 위해 클래스나 네임스페이스 안에 둡니다.

```cpp
class Interest
{
public:
    enum Value
    {
        NONE  = 0,
        READ  = 1 << 0,
        WRITE = 1 << 1
    };
};
```

비트 연산 결과 타입은 `int`이므로, 여러 비트를 함께 표현하는 인터페이스는 `unsigned int` 같은 마스크 타입을 별도로 사용하거나 안전한 보조 함수를 제공합니다. Modern C++의 `enum class`보다 타입 안전성이 낮으므로 API가 임의 정수를 상태값으로 받지 않게 합니다.

## 8. 반복자 루프

```cpp
std::vector<int>::const_iterator it = values.begin();
for (; it != values.end(); ++it)
{
    std::cout << *it << '\n';
}
```

반복자 타입이 길다는 이유만으로 원시 인덱스 루프를 사용하지 않습니다. 인덱스 자체가 의미 있는지, 단순 순회가 목적이어서 반복자가 더 적절한지 구분합니다.

## 9. 중첩 템플릿의 `> >`

C++98에서는 중첩 템플릿을 닫는 연속 `>>`가 오른쪽 시프트 연산자로 해석됩니다.

```cpp
std::vector<std::vector<int> > matrix;
```

두 `>` 사이를 띄웁니다. C++11 이후에는 `>>`를 그대로 사용할 수 있습니다.

## 10. 의존 이름

```cpp
template <class Container>
void clearAll(Container &container)
{
    typename Container::iterator it = container.begin();
    // ...
}
```

`Container::iterator`가 타입이라는 사실을 `typename`으로 알려야 합니다.

의존 타입의 멤버 템플릿을 사용할 때는 `template` 구분자가 필요할 수 있습니다.

```cpp
typedef typename Allocator::template rebind<Node>::other NodeAllocator;
```

오류 메시지가 복잡할 때는 다음 순서로 확인합니다.

1. `T::name`이 템플릿 인자에 의존합니까?
2. `name`이 타입입니까? 그렇다면 `typename`이 필요한지 확인합니다.
3. `name`이 멤버 템플릿입니까? 그렇다면 `template` 구분자가 필요한지 확인합니다.

## 11. Rule of Three에서 Rule of Zero·Five로

| 설계 질문 | C++98 | Modern C++ |
|---|---|---|
| 직접 자원 소유 | Rule of Three | Rule of Five 또는 전용 표준 소유자 |
| 소유권 이전 | `swap`, `release`, 명시적 인계 | 이동 의미론 |
| 단독 메모리 소유 | 사용자 정의 RAII 소유자 | `unique_ptr` |
| 멤버가 모두 값 타입 | 컴파일러 생성 복사 활용 | Rule of Zero |

현대화의 목표는 특수 멤버 함수를 더 많이 작성하는 것이 아닙니다. 직접 자원 소유를 표준 소유자에 맡겨 사용자 타입이 업무 불변식과 값 의미만 다루게 하는 것입니다.

## 12. C++98 코드 현대화 순서

1. 표준 버전을 올리기 전에 기존 테스트와 경고 기준을 고정합니다.
2. 포인터 문맥의 `NULL`과 `0`을 `nullptr`로 바꿉니다.
3. 복사 금지 선언을 `= delete`로 명시합니다.
4. 원시 소유자를 `unique_ptr`나 표준 컨테이너로 교체합니다.
5. 수동 반복자 루프를 범위 기반 `for`나 알고리즘으로 단순화합니다.
6. 지역적인 함수 객체를 람다로 바꿉니다.
7. 소유자 타입의 이동 연산과 `noexcept` 조건을 검토합니다.
8. 직접 작성한 소멸자와 복사 제어를 제거해 Rule of Zero로 이동합니다.

각 단계 뒤에 테스트합니다. 문법 변경과 동작 변경을 한 커밋에 섞지 않습니다.

## 13. Modern C++ 기능을 범용으로 흉내 내지 말아야 하는 경우

C++98에서 다음 기능을 범용 라이브러리 수준으로 다시 구현하려 하지 않습니다.

- 완전한 `shared_ptr`
- 표준 수준의 호출 래퍼
- 모든 호출 형태를 처리하는 `bind`
- 범용 `optional`·`variant`
- 제품용 STL 컨테이너

원리를 확인하는 제한된 학습 구현은 가능하지만, 제품 기능처럼 재사용하면 수명, 예외 안전성, 정렬, ABI와 스레드 안전성의 경계 사례가 급격히 늘어납니다. 필요한 범위의 책임만 구현합니다.

---

## GNU Make로 C++98 프로젝트 빌드하기

### 14. Make의 핵심 모델

Make는 의존성 그래프와 파일 수정 시각을 이용하는 증분 빌드 도구입니다. 셸 스크립트처럼 명령 순서만 나열해서는 파일 간 의존 관계를 정확히 표현할 수 없습니다.

```make
대상: 선행 조건
	대상을 만드는 명령
```

대상이 없거나 선행 조건 중 하나가 대상보다 새로우면 빌드 명령이 실행됩니다.

```text
program
├── main.o
│   └── main.cpp + 포함 헤더
└── Store.o
    └── Store.cpp + 포함 헤더
```

의존성 선언이 틀리면 빌드 판단도 틀립니다. 헤더를 수정했는데 관련 객체 파일이 다시 컴파일되지 않는 문제가 대표적입니다.

### 15. 최소 변수

```make
NAME := app
CXX ?= c++
CPPFLAGS := -Iinclude
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror
LDFLAGS ?=
LDLIBS ?=
```

| 연산자 | 의미 |
|---|---|
| `=` | 참조할 때 재귀적으로 전개 |
| `:=` | 정의할 때 즉시 전개 |
| `?=` | 아직 정의되지 않았을 때만 설정 |
| `+=` | 기존 값 뒤에 추가 |

상수와 `$(shell ...)` 결과는 일반적으로 `:=`가 예측하기 쉽습니다. 컴파일러와 사용자 옵션을 `?=`로 두면 `make CXX=clang++`처럼 외부에서 덮어쓸 수 있습니다.

전처리 옵션은 `CPPFLAGS`, C++ 컴파일 옵션은 `CXXFLAGS`, 링크 옵션은 `LDFLAGS`, 라이브러리는 `LDLIBS`에 두면 역할이 명확해집니다.

### 16. 소스에서 산출물 목록 파생

```make
SRCS := src/main.cpp src/Parser.cpp src/Store.cpp
OBJS := $(SRCS:.cpp=.o)
DEPS := $(OBJS:.o=.d)
```

소스 목록을 한곳에 두고 객체 파일과 의존성 파일 목록을 파생합니다.

### 17. 패턴 규칙과 자동 변수

```make
%.o: %.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
```

| 변수 | 의미 |
|---|---|
| `$@` | 현재 대상 |
| `$<` | 첫 번째 선행 조건 |
| `$^` | 중복을 제거한 모든 선행 조건 |
| `$*` | 패턴의 `%`에 대응하는 부분 |

링크 규칙:

```make
$(NAME): $(OBJS)
	$(CXX) $(LDFLAGS) $^ $(LDLIBS) -o $@
```

기본 Make 문법에서 빌드 명령 줄은 탭 문자로 시작해야 합니다.

### 18. 헤더 자동 의존성

단순한 `%.o: %.cpp` 규칙만으로는 소스가 포함한 헤더를 알 수 없습니다. GCC와 Clang에서는 `-MMD -MP`로 컴파일 중 `.d` 파일을 생성할 수 있습니다.

```make
%.o: %.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@
```

Makefile 끝에서 읽습니다.

```make
-include $(DEPS)
```

- `-MMD`: 사용자 헤더 의존성 생성
- `-MP`: 삭제된 헤더 이름에 대한 빈 대상 생성
- `-include`: 첫 빌드에 `.d` 파일이 없어도 중단하지 않음

이 옵션은 GCC·Clang 계열 기능입니다. 다른 컴파일러를 지원한다면 해당 컴파일러의 의존성 생성 방식을 별도로 구성합니다.

### 19. 플랫폼 분기

```make
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Linux)
    PLATFORM_SRC := src/PollerEpoll.cpp
    CPPFLAGS += -DUSE_EPOLL
else ifeq ($(UNAME_S),Darwin)
    PLATFORM_SRC := src/PollerKqueue.cpp
    CPPFLAGS += -DUSE_KQUEUE
else
    $(error 지원하지 않는 플랫폼입니다: $(UNAME_S))
endif
```

Makefile 파싱 시점의 `ifeq`와 빌드 명령 안에서 실행되는 셸의 `if`를 혼동하지 않습니다. 지원하지 않는 환경에서 잘못된 소스를 조용히 빌드하기보다 명시적으로 중단합니다.

교차 컴파일에서는 `uname`이 대상 플랫폼이 아니라 빌드 호스트를 가리킬 수 있습니다. 교차 컴파일까지 지원한다면 사용자가 대상 플랫폼 변수를 명시하게 합니다.

### 20. `.PHONY`와 정리 대상

```make
.PHONY: all clean test

all: $(NAME)

clean:
	rm -f $(OBJS) $(DEPS) $(NAME)
```

동작 이름과 같은 파일이 존재해도 명령을 실행하도록 파일을 만들지 않는 대상을 `.PHONY`로 선언합니다. 실제 산출물 타깃을 `.PHONY`로 선언하면 매번 다시 빌드되므로 구분해야 합니다.

### 21. 디버그와 릴리스

사용자가 전달한 플래그를 무심코 덮어쓰지 않도록 정책을 정합니다.

```make
BASE_CXXFLAGS := -std=c++98 -Wall -Wextra -Werror
CXXFLAGS ?=

ifeq ($(DEBUG),1)
    CXXFLAGS += $(BASE_CXXFLAGS) -O0 -g
else
    CXXFLAGS += $(BASE_CXXFLAGS) -O2
endif
```

외부에서 `CXXFLAGS`를 지정했을 때 공통 필수 플래그를 계속 추가할지, 완전히 대체하게 할지는 프로젝트 정책입니다. 위 예시는 사용자 플래그 뒤에 프로젝트 필수 플래그를 추가합니다. 같은 옵션이 중복되거나 상충하지 않게 실제 출력 명령을 확인합니다.

`-Werror`는 프로젝트 코드의 경고 회귀를 막는 데 유용하지만 외부 헤더 경고까지 통제할 수 없는 환경에서는 시스템 헤더 경계를 분리합니다.

### 22. 빌드 오류 조사 순서

#### `missing separator`

빌드 명령이 탭 문자가 아니라 공백으로 시작했는지 확인합니다.

#### 헤더 수정이 반영되지 않음

`.d` 파일이 생성되고 `-include`되는지 확인합니다.

#### `undefined reference`

- 구현이 존재합니까?
- 네임스페이스와 시그니처가 선언과 일치합니까?
- 해당 객체 파일과 라이브러리가 링크 명령에 포함됐습니까?
- 라이브러리 링크 순서가 필요한 환경입니까?

#### 중복 심볼

- 헤더에 비인라인 함수나 전역 변수 정의가 있습니까?
- 같은 `.cpp`에서 생성된 객체 파일을 여러 번 링크합니까?
- 동일 정의가 여러 정적 라이브러리에 들어갔습니까?

#### 매번 전체 재빌드

- `.PHONY` 대상이 실제 파일 대상의 선행 조건에 들어갔습니까?
- 매번 새로 생성되는 파일을 불필요한 선행 조건으로 뒀습니까?
- 생성 파일의 시각이 비정상입니까?

### 23. 최소 완성 Makefile

```make
NAME := app
CXX ?= c++
CPPFLAGS := -Iinclude
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -g
LDFLAGS ?=
LDLIBS ?=

SRCS := src/main.cpp src/Parser.cpp src/Store.cpp
OBJS := $(SRCS:.cpp=.o)
DEPS := $(OBJS:.o=.d)

.PHONY: all clean test

all: $(NAME)

$(NAME): $(OBJS)
	$(CXX) $(LDFLAGS) $^ $(LDLIBS) -o $@

%.o: %.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@

test: all
	./tests/run.sh

clean:
	rm -f $(OBJS) $(DEPS) $(NAME)

-include $(DEPS)
```

### 24. 호환성 점검

#### 언어

- 표준 버전을 컴파일러 플래그로 고정했습니까?
- 최신 기능이 실수로 들어오지 않았습니까?
- 소유자 타입의 복사를 막거나 깊은 복사를 구현했습니까?
- 반복자 루프가 `const` 경계를 지킵니까?
- 중첩 템플릿의 `> >` 문법을 지킵니까?
- 의존 타입에 `typename`이나 `template` 구분자가 필요합니까?

#### 빌드

- 소스 목록에서 객체와 의존성 파일을 파생합니까?
- 헤더 변경이 관련 객체의 재컴파일로 이어집니까?
- 동작 타깃을 `.PHONY`로 선언했습니까?
- 컴파일러와 선택 옵션을 외부에서 덮어쓸 수 있습니까?
- 지원하지 않는 플랫폼에서 명확히 실패합니까?
- `clean` 뒤 완전 재빌드와 테스트가 통과합니까?

#### 현대화 준비

- 직접 소유자를 표준 소유자로 바꿀 경계가 보입니까?
- 특수 멤버 함수를 제거해 Rule of Zero로 갈 수 있습니까?
- 함수 객체를 람다로 바꾸기 전에 테스트가 있습니까?
- 문법 현대화와 동작 변경을 분리했습니까?
