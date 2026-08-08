# C++98 호환 개발 참고 자료

## 호환 트랙을 사용하는 경우

C++98로 작성된 코드를 유지보수하거나, 최신 언어 기능 없이 객체 수명과 소유권을 직접 다뤄 보고 싶을 때 참고하실 수 있습니다. GNU Make로 빌드하는 방법과 같은 의도를 현대 C++에서 더 분명하게 표현하는 방법도 함께 다룹니다.

핵심 원칙은 두 가지입니다.

1. **시대적 문법 제약과 언어 독립적인 설계 원칙을 구분합니다.**
2. **현대 기능을 흉내 내기보다 C++98에서 명확하고 검증 가능한 표현을 사용합니다.**

---

## 1. C++98과 C++03

C++03은 C++98의 결함을 정정하고 규칙을 명확히 한 판에 가깝습니다. 새로운 언어 기능이 대규모로 추가된 버전은 아닙니다. 사용하는 컴파일 옵션과 실행 환경이 `-std=c++98`인지 `-std=c++03`인지 확인하고, 둘의 차이에 의존하는 코드는 별도로 검증합니다.

```sh
c++ -std=c++98 -Wall -Wextra -Werror main.cpp
```

컴파일러가 기본으로 최신 표준을 사용하게 두면 의도치 않게 람다, `nullptr`, 범위 기반 `for` 같은 기능이 들어갈 수 있습니다. 표준 버전을 플래그로 고정합니다.

## 2. C++98에 없는 주요 기능

| 현대 기능 | C++98 상태 | C++98에서의 일반적 표현 |
|---|---|---|
| `nullptr` | 없음 | `0`, 필요한 C API에서 `NULL` |
| 타입 추론 `auto` | 없음 | 타입을 명시 |
| 범위 기반 `for` | 없음 | 반복자 루프 |
| 람다 | 없음 | 함수 포인터 또는 함수 객체 |
| `enum class` | 없음 | 네임스페이스/클래스 범위의 enum |
| `override`, `final` | 없음 | 정확한 시그니처와 경고 |
| `= delete` | 없음 | 비공개 복사 선언 |
| `= default` | 없음 | 생략하거나 직접 구현 |
| 이동 의미론 | 없음 | 복사, `swap`, 명시적 소유권 인계 |
| `unique_ptr` | 없음 | 복사 금지 RAII 소유자 |
| `std::optional` | 없음 | 결과 객체, `bool`과 출력 매개변수, 별도 상태 |
| variadic 템플릿 | 없음 | 고정 인자 오버로드 |
| `std::type_traits` | 없음 | 필요한 특성만 직접 구현 |

기능이 없다고 원리까지 없는 것은 아닙니다. 단독 소유, 읽기 전용 경계, 콜백, 값 없음과 타입 특성 같은 개념은 다른 문법으로 표현합니다.

## 3. 널 포인터

C++98에서는 정수 상수 `0`이 널 포인터 constant로 사용됩니다.

```cpp
Widget *widget = 0;
```

`NULL`은 구현에 따라 정수 매크로일 수 있어 오버로드에서 예상과 다른 함수가 선택될 수 있습니다.

```cpp
void call(int);
void call(Widget *);

call(NULL); // int overload가 선택될 수 있음
```

C++98 C++ 코드에서는 일반적으로 `0`을 사용하고, C API나 프로젝트 스타일이 `NULL`을 요구할 때만 일관되게 사용합니다. 현대 C++에서는 `nullptr`가 포인터 전용 타입이라 이 모호성을 해결합니다.

## 4. 복사 금지

C++98에는 `= delete`가 없습니다. 복사가 의미 없는 소유자는 복사 생성자와 대입을 비공개으로 선언하고 정의하지 않습니다.

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

실수로 복사하면 접근 오류 또는 링크 오류가 납니다. 현대 C++의 `= delete`는 같은 의도를 더 직접적으로 표현합니다.

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

이 타입은 단독 소유의 최소 형태입니다. 일반화된 스마트 포인터를 직접 만들기보다 필요한 자원에 맞는 작은 소유자를 작성합니다. 배열, 사용자 정의 해제자와 다형 삭제까지 억지로 한 타입에 넣으면 표준 구현을 다시 만드는 복잡도로 커집니다.

현대 C++에서는 `std::unique_ptr`를 사용합니다.

## 6. 함수 객체와 lambda의 관계

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

현대 C++ lambda:

```cpp
const std::string prefix = "GET";
auto match = [prefix](const std::string &value) {
    return value.compare(0, prefix.size(), prefix) == 0;
};
```

둘 다 상태를 가진 호출 가능한 객체입니다. 람다를 사용할 수 없는 환경에서도 콜백과 알고리즘 정책을 같은 방식으로 설계할 수 있습니다.

## 7. 열거형의 이름 범위 제한

C++98 enum은 정수로 암묵 변환되고 enumerator 이름이 주변 범위에 들어옵니다. 전역 이름 충돌을 줄이기 위해 클래스나 네임스페이스 안에 둡니다.

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

비트 연산 결과는 int가 되므로 필요한 위치에서 명시적으로 `Value`로 변환하거나 별도 helper를 제공합니다. 현대 `enum class`보다 타입 안전성은 낮으므로 API에서 임의 정수를 받지 않게 합니다.

## 8. 반복자 루프

```cpp
std::vector<int>::const_iterator it = values.begin();
for (; it != values.end(); ++it)
{
    std::cout << *it << '\n';
}
```

반복자 타입이 길더라도 생략할 수 없다는 이유만으로 원시 인덱스 루프를 쓰지 않습니다. 인덱스가 의미인지, 단순 순회가 의미인지 구분합니다.

## 9. 중첩 템플릿의 `> >`

C++98에서는 중첩 템플릿을 닫는 `>>`가 우측 shift 연산자로 해석될 수 있습니다.

```cpp
std::vector<std::vector<int> > matrix;
```

두 `>` 사이를 띄웁니다. 최신 표준에서는 `>>`가 허용됩니다.

## 10. 의존 이름

```cpp
template <class Container>
void clearAll(Container &container)
{
    typename Container::iterator it = container.begin();
    // ...
}
```

`Container::iterator`가 타입임을 `typename`으로 알려야 합니다.

Dependent 타입의 멤버 템플릿을 사용할 때는 `template` 키워드도 필요할 수 있습니다.

```cpp
typedef typename Allocator::template rebind<Node>::other NodeAllocator;
```

오류 메시지가 난해하므로 다음 순서로 읽습니다.

1. `T::name`이 템플릿 인자에 의존합니까?
2. `name`이 타입입니까? 그렇다면 `typename`을 검토합니다.
3. `name`이 멤버 템플릿입니까? 그렇다면 `template`을 검토합니다.

## 11. Rule of Three에서 Rule of Zero/Five로

| 설계 질문 | C++98 | 현대 C++ |
|---|---|---|
| 직접 자원 소유 | Rule of Three | Rule of Five 또는 전용 소유자 사용 |
| 소유권 이전 | `swap`, `release`, 명시적 계약 | 이동 의미론 |
| 단독 메모리 소유 | 사용자 RAII 소유자 | `unique_ptr` |
| 멤버가 모두 값 타입 | 기본 복사 활용 | Rule of Zero |

현대화의 목표는 특수 멤버 함수를 더 많이 작성하는 것이 아닙니다. 직접 자원 소유를 표준 소유자에 맡겨 사용자 타입이 값 의미만 다루게 하는 것입니다.

## 12. C++98 코드를 현대화하는 순서

1. 빌드 표준을 올리기 전에 기존 테스트와 검사 도구 기준을 고정합니다.
2. `NULL`/`0` 포인터를 `nullptr`로 바꿉니다.
3. 복사 금지 선언을 `= delete`로 명시합니다.
4. 원시 소유자를 `unique_ptr` 또는 컨테이너로 교체합니다.
5. 수동 반복자 루프를 범위 기반 for 또는 알고리즘으로 단순화합니다.
6. 함수 객체가 지역 동작이면 lambda로 줄입니다.
7. 이동 가능한 소유자에 move와 `noexcept`를 검토합니다.
8. Rule of Zero가 되도록 직접 소멸자와 복사 제어를 제거합니다.

각 단계 뒤 테스트합니다. 문법 변환과 동작 변경을 한 반영에 섞지 않습니다.

## 13. 현대 기능을 흉내 내지 말아야 하는 경우

C++98에서 다음을 범용으로 재현하려 하지 않습니다.

- 완전한 `shared_ptr`
- 표준 수준의 `function`
- 모든 호출 형태를 받는 bind
- 범용 optional/variant
- 생산용 STL 컨테이너

원리를 확인하는 작은 구현은 가능하지만 제품 기능처럼 재사용하면 경계 사례와 예외 안전성 비용이 급격히 커집니다. 필요한 좁은 책임만 구현합니다.

---

## GNU Make로 C++98 프로젝트 빌드하기

### 14. Make의 핵심 모델

Make는 의존성 그래프와 파일 수정 시각을 이용하는 증분 빌드 도구입니다. 셸 스크립트처럼 명령 순서만 나열해서는 의존 관계를 정확히 표현할 수 없습니다.

```make
대상: 선행 조건
	대상을 만드는 명령
```

선행 조건 중 하나라도 대상보다 새로우면 빌드 명령이 실행됩니다.

```text
program
├── main.o
│   └── main.cpp + headers
└── Store.o
    └── Store.cpp + headers
```

의존성 선언이 틀리면 빌드 판단도 틀립니다. 헤더를 고쳤는데 관련 `.o`가 다시 컴파일되지 않는 오래된 build가 대표적입니다.

### 15. 최소 변수

```make
NAME := app
CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror
CPPFLAGS := -Iinclude
```

| 연산자 | 의미 |
|---|---|
| `=` | 참조될 때 재귀적으로 전개 |
| `:=` | 정의 시 즉시 전개 |
| `?=` | 아직 정의되지 않았을 때만 설정 |
| `+=` | 기존 값 뒤에 추가 |

상수와 `$(shell ...)` 결과는 대개 `:=`가 예측 가능합니다. 컴파일러와 플래그는 `?=`로 두면 `make CXX=clang++`처럼 외부에서 덮어쓸 수 있습니다.

### 16. 소스에서 산출물 목록 파생

```make
SRCS := src/main.cpp src/Parser.cpp src/Store.cpp
OBJS := $(SRCS:.cpp=.o)
DEPS := $(OBJS:.o=.d)
```

소스 목록 하나를 단일 진실 공급원으로 두고 객체와 의존 관계 목록을 파생합니다.

### 17. 패턴 규칙과 자동 변수

```make
%.o: %.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@
```

| 변수 | 의미 |
|---|---|
| `$@` | 현재 대상 |
| `$<` | 첫 선행 조건 |
| `$^` | 모든 선행 조건, 중복 제거 |
| `$*` | 패턴에서 `%`에 대응하는 부분 |

링크:

```make
$(NAME): $(OBJS)
	$(CXX) $(CXXFLAGS) $^ -o $@
```

빌드 명령 줄은 TAB으로 시작해야 합니다.

### 18. 헤더 자동 의존성

단순 `%.o: %.cpp`는 포함한 헤더를 모릅니다. GCC와 Clang의 `-MMD -MP`로 컴파일 중 `.d` 파일을 만듭니다.

```make
%.o: %.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@
```

파일 끝에서 읽습니다.

```make
-include $(DEPS)
```

- `-MMD`: 사용자 헤더 의존성 생성
- `-MP`: 삭제된 헤더용 빈 대상 생성
- `-include`: 최초 빌드에 `.d`가 없어도 실패하지 않음

이 세 요소를 함께 사용합니다.

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

Makefile 파싱 시점의 `ifeq`와 빌드 명령 안의 셸 `if`를 혼동하지 않습니다. 지원하지 않는 환경에서 잘못된 소스를 조용히 빌드하기보다 명시적으로 중단합니다.

교차 컴파일 환경에서는 `uname`이 대상이 아니라 빌드 호스트를 가리킬 수 있습니다. 그런 환경까지 지원한다면 사용자가 플랫폼 변수를 명시하도록 설계합니다.

### 20. `.PHONY`와 정리 대상

```make
.PHONY: all clean test

all: $(NAME)

clean:
	rm -f $(OBJS) $(DEPS) $(NAME)
```

동작 이름과 같은 파일이 존재해도 빌드 명령이 항상 실행되게 `.PHONY`를 선언합니다.

### 21. 디버그와 릴리스

한 변수에 사용자가 준 플래그를 덮어쓰지 않도록 합니다.

```make
BASE_FLAGS := -std=c++98 -Wall -Wextra -Werror

ifeq ($(DEBUG),1)
    CXXFLAGS ?= $(BASE_FLAGS) -O0 -g
else
    CXXFLAGS ?= $(BASE_FLAGS) -O2
endif
```

실제 프로젝트에서는 `CXXFLAGS ?=`와 내부 공통 플래그를 조합하는 정책을 명확히 합니다. `-Werror`는 프로젝트 코드 품질을 높이지만 외부 헤더의 경고까지 통제할 수 없는 환경에서는 적용 범위를 나눌 수 있습니다.

### 22. 빌드 오류 조사 순서

### `missing separator`

빌드 명령이 탭 문자가 아닌 공백으로 시작했는지 봅니다.

### 헤더 수정이 반영되지 않음

`.d` 파일이 생성되고 `-include`되는지 확인합니다.

### `undefined reference`

- 구현이 존재합니까?
- 네임스페이스와 시그니처가 선언과 같은가?
- 해당 `.o`가 링크 명령에 포함됩니까?

### 중복 심볼(`duplicate symbol`)

- 헤더에 비인라인 정의가 있습니까?
- 동일 `.cpp`가 여러 번 링크됩니까?
- 전역 변수 정의가 여러 번 생깁니까?

### 매번 전체 재빌드

- `.PHONY` 대상이 실제 파일 대상의 선행 조건으로 들어갔습니까?
- 항상 새로 생성되는 파일을 선행 조건으로 뒀습니까?
- 생성 파일의 타임스탬프가 비정상입니까?

### 23. 최소 완성 Makefile

```make
NAME := app
CXX ?= c++
CXXFLAGS ?= -std=c++98 -Wall -Wextra -Werror -g
CPPFLAGS := -Iinclude

SRCS := src/main.cpp src/Parser.cpp src/Store.cpp
OBJS := $(SRCS:.cpp=.o)
DEPS := $(OBJS:.o=.d)

.PHONY: all clean test

all: $(NAME)

$(NAME): $(OBJS)
	$(CXX) $(CXXFLAGS) $^ -o $@

%.o: %.cpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -MMD -MP -c $< -o $@

test: all
	./tests/run.sh

clean:
	rm -f $(OBJS) $(DEPS) $(NAME)

-include $(DEPS)
```

### 24. 호환성 점검

### 언어

- 표준 버전을 컴파일러 플래그로 고정했습니까?
- 최신 기능이 실수로 들어오지 않았습니까?
- 소유자 타입의 복사를 막거나 깊은 복사를 구현했습니까?
- 반복자 루프가 const 경계를 지킵니까?
- 중첩 템플릿 `> >` 문법을 지킵니까?
- 의존 타입에 `typename`이 필요합니까?

### 빌드

- 소스 목록에서 객체와 의존 관계를 파생합니까?
- 헤더 변경이 관련 객체 재컴파일로 이어집니까?
- 동작 대상을 `.PHONY`로 선언했습니까?
- 컴파일러와 플래그를 외부에서 덮어쓸 수 있습니까?
- 지원하지 않는 플랫폼에서 명확히 실패합니까?
- clean 뒤 완전 재빌드와 테스트가 통과합니까?

### 현대화 준비

- 직접 소유자를 표준 소유자로 바꿀 경계가 보입니까?
- 특수 멤버 함수를 제거해 Rule of Zero로 갈 수 있습니까?
- 함수 객체를 lambda로 바꾸기 전에 테스트가 있습니까?
- 문법 현대화와 동작 변경을 분리했습니까?
