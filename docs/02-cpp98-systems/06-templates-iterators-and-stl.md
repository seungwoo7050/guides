# 템플릿, 반복자와 STL 알고리즘

## 타입이 달라도 같은 책임을 구현합니다

같은 코드를 타입마다 복사하면 수정과 검증도 반복됩니다. 실행 시점의 구현 교체가 필요하지 않은 차이까지 가상 인터페이스로 감추면 불필요한 객체 계층이 생깁니다. C++ 템플릿은 타입이 달라도 같은 표현과 책임을 수행하는 코드를 컴파일 시점에 생성합니다.

STL은 템플릿을 바탕으로 컨테이너, 반복자와 알고리즘을 분리합니다. 알고리즘을 적용할 수 있는지는 구체적인 컨테이너 이름이 아니라 반복자가 제공하는 연산으로 판단합니다.

## 템플릿과 STL의 연결

```text
템플릿 + 타입에 필요한 연산 → 인스턴스화 → 구체 코드

컨테이너 ── begin/end 반복자 범위 ── 알고리즘
```

컨테이너와 알고리즘이 서로의 구체 타입을 몰라도 되는 이유는 반복자가 이동과 역참조에 필요한 연산을 제공하기 때문입니다.

## 배열과 반복자를 구현하며 확인

[템플릿 배열과 반복자 실습](../../exercises/02-cpp98-systems/generic-programming/template-array/README.md)에서 함수 템플릿, 반복자 범위와 `Array<T>`를 순서대로 구현합니다.

```sh
cd exercises/02-cpp98-systems/generic-programming/template-array
make observe
```

위 명령은 저장소 루트에서 실행합니다. `make observe`는 작은 `demo.cpp`를 참조 구현의 공개 API에 연결해 결과만 관찰하는 선택 실험입니다. 워크스페이스의 `skeleton/`을 구현한 뒤 저장소 루트에서 다음 명령으로 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=generic-programming/template-array
```

학습자 구현 검증을 통과한 뒤에만 참조 구현과 비교합니다. 기준 `compile-fail` 검사는 반복자 요구사항을 만족하지 않는 타입과 `const` 경계를 의도적으로 사용합니다. 컴파일 실패도 라이브러리 인터페이스를 검증하는 테스트임을 확인합니다.

---

## 1. 제네릭 프로그래밍

다음 두 함수는 구조가 같습니다.

```cpp
int smaller(int left, int right)
{
    return right < left ? right : left;
}

double smaller(double left, double right)
{
    return right < left ? right : left;
}
```

템플릿은 타입을 매개변수로 만듭니다.

```cpp
template <class T>
const T &smaller(const T &left, const T &right)
{
    return right < left ? right : left;
}
```

이 함수가 모든 타입에 동작하는 것은 아닙니다. 본문에서 사용한 표현이 타입 요구사항이 됩니다.

- `T`에 `<` 연산이 정의되어야 합니다.
- 두 인자가 같은 의미로 비교 가능해야 합니다.
- 반환 참조를 저장한다면 선택된 인자의 수명이 참조보다 길어야 합니다.

특히 임시 객체를 인자로 넘긴 결과를 참조로 오래 보관하면 댕글링 참조가 됩니다. 참조 반환이 필요하지 않다면 값으로 반환하는 편이 더 안전할 수 있습니다.

C++98에는 콘셉트 문법이 없으므로 요구사항을 문서, 테스트와 의도적인 컴파일 실패로 드러냅니다.

## 2. 함수 템플릿

```cpp
template <class T>
void swapValue(T &left, T &right)
{
    T temporary(left);
    left = right;
    right = temporary;
}
```

호출할 때 컴파일러가 인자 타입에서 `T`를 추론합니다.

```cpp
int a = 1;
int b = 2;
swapValue(a, b);
```

타입 추론이 불가능하거나 원하는 타입을 명시해야 한다면 템플릿 인자를 직접 지정할 수 있습니다.

```cpp
const long result = smaller<long>(3, 7);
```

위 식에서는 반환 참조를 같은 전체 표현식 안에서 `long` 값으로 복사하므로 안전합니다. 반환값을 `const long&`에 저장해 다음 문장까지 사용해서는 안 됩니다.

함수 템플릿과 일반 함수가 함께 후보가 되면 일반 오버로드 해석 규칙이 적용됩니다. 특정 타입만 다른 동작이 필요하다면 함수 템플릿 특수화보다 일반 함수 오버로드가 더 명확한 경우가 많습니다.

`swapValue`의 두 대입 중 하나가 예외를 던지면 두 객체가 일부 변경된 상태로 남을 수 있습니다. 일반화된 코드도 실패 뒤 상태 보장을 별도로 정해야 합니다.

## 3. 클래스 템플릿

```cpp
template <class T>
class Box
{
public:
    explicit Box(const T &value) : value_(value) {}
    const T &value() const { return value_; }

private:
    T value_;
};
```

`Box<int>`와 `Box<std::string>`은 서로 다른 구체 타입입니다.

```cpp
Box<int> number(42);
Box<std::string> text("hello");
```

클래스 템플릿은 원소 타입마다 같은 구조의 코드가 필요할 때 유용합니다. 대신 컴파일 시간과 생성되는 코드 크기가 늘 수 있습니다. 일반적으로 실제 사용된 타입과 멤버 함수 조합만 인스턴스화됩니다.

## 4. 인스턴스화와 오류 위치

템플릿에 구체 타입을 넣으면 필요한 코드가 생성됩니다. 정의 자체는 유효해 보여도 특정 타입에서 표현이 성립하지 않을 수 있습니다.

```cpp
template <class T>
void printTwice(const T &value)
{
    std::cout << value << value;
}
```

`operator<<`를 제공하지 않는 타입으로 호출하면 인스턴스화 지점에서 긴 오류가 발생할 수 있습니다. 다음 순서로 원인을 좁힙니다.

1. 사용자 코드에서 템플릿이 처음 인스턴스화된 위치를 찾습니다.
2. 템플릿 본문에서 실패한 표현을 찾습니다.
3. 실제 `T`가 그 표현에 필요한 연산을 제공하는지 확인합니다.
4. 템플릿이 구현상 필요하지 않은 연산까지 요구하는지 검토합니다.

## 5. 템플릿 정의 위치

컴파일러가 템플릿을 인스턴스화하려면 선언뿐 아니라 정의도 볼 수 있어야 합니다. 따라서 템플릿 함수와 멤버 함수의 본문은 보통 헤더에 둡니다.

```cpp
// Array.hpp
#ifndef ARRAY_HPP
#define ARRAY_HPP

template <class T>
class Array
{
public:
    explicit Array(std::size_t size);
    ~Array();

private:
    T *data_;
    std::size_t size_;
};

template <class T>
Array<T>::Array(std::size_t size)
    : data_(new T[size]), size_(size)
{}

#endif
```

이 구현은 `T`가 기본 생성 가능해야 한다는 추가 요구사항을 가집니다. 배열 원소 일부를 생성하다가 예외가 발생하면 `new[]`가 이미 생성된 원소를 역순으로 소멸시키고 저장 공간을 해제합니다.

본문을 별도 `.tpp` 파일에 두고 헤더 끝에서 포함해도 원리는 같습니다. 명시적 인스턴스화로 정의를 `.cpp`에 둘 수도 있지만 지원할 타입을 미리 고정하는 별도 설계이므로 입문 단계에서는 사용하지 않습니다.

## 6. 의존 이름과 특수화

### `typename`

템플릿 인자에 따라 의미가 달라지는 멤버 이름이 타입일 때는 `typename`으로 명시합니다.

```cpp
template <class Container>
void printAll(const Container &values)
{
    typename Container::const_iterator it = values.begin();
    for (; it != values.end(); ++it)
        std::cout << *it << '\n';
}
```

템플릿을 정의하는 시점에는 `Container::const_iterator`가 타입인지 정적 멤버인지 알 수 없기 때문입니다.

### 완전 특수화와 부분 특수화

클래스 템플릿은 특정 타입이나 타입 패턴에 별도 정의를 제공할 수 있습니다.

```cpp
template <class T>
struct IsPointer
{
    enum { value = 0 };
};

template <class T>
struct IsPointer<T *>
{
    enum { value = 1 };
};
```

두 번째 정의는 `T*` 패턴을 처리하므로 부분 특수화입니다. 특수화는 일반 구현으로 표현하기 어려운 구조적인 차이가 있을 때만 사용합니다.

## 7. 실행 시점 다형성과 비교

| 질문 | 템플릿 | 가상 인터페이스 |
|---|---|---|
| 구현 선택 시점 | 컴파일 시점 | 실행 시점 |
| 호출 방식 | 보통 직접 호출 | 가상 함수 간접 호출 |
| 타입 집합 | 컴파일 시점에 결정 | 실행 중 여러 구현 사용 가능 |
| 요구사항 표현 | 템플릿 본문과 문서 | 기반 클래스 인터페이스 |
| 정의 가시성 | 인스턴스화 지점에서 필요 | 인터페이스 선언만으로 호출 가능 |

원소 타입만 달라지고 같은 알고리즘을 적용한다면 템플릿이 자연스럽습니다. 설정에 따라 실행 중 백엔드를 바꾸거나 서로 다른 구현을 하나의 컬렉션에 보관한다면 가상 인터페이스가 더 적합할 수 있습니다.

## 8. STL의 세 축

```text
컨테이너: 데이터를 보관합니다.
반복자:   범위 안의 위치와 이동 능력을 표현합니다.
알고리즘: 반복자 범위에 동작합니다.
```

알고리즘은 `std::vector`나 `std::list`라는 이름보다 반복자가 제공하는 연산에 의존합니다.

```cpp
std::vector<int> values;
std::sort(values.begin(), values.end());
```

## 9. 반열린 범위 `[first, last)`

`first`는 첫 원소를 가리키고 `last`는 마지막 원소 다음 위치를 가리킵니다.

```text
[first, last)
```

이 규칙에는 다음 장점이 있습니다.

- 빈 범위는 `first == last`로 표현됩니다.
- 처리한 원소 수와 다음 위치를 자연스럽게 연결할 수 있습니다.
- 한 범위를 `[first, middle)`, `[middle, last)`로 겹치지 않게 나눌 수 있습니다.

`end()`는 원소를 가리키지 않으므로 역참조하지 않습니다.

## 10. 반복자 범주

| 범주 | 핵심 능력 | 대표 예 |
|---|---|---|
| 입력 반복자 | 한 방향 읽기 | 입력 스트림 반복자 |
| 전방 반복자 | 여러 번 순회, 한 방향 이동 | 전방 연결 구조 |
| 양방향 반복자 | `++`, `--` | `list`, `map` |
| 임의 접근 반복자 | 덧셈, 거리, 인덱스, 순서 비교 | 포인터, `vector`, `deque` |

더 강한 범주의 반복자는 더 약한 범주가 요구하는 연산도 제공합니다. `std::sort`는 임의 접근 반복자를 요구하므로 `vector`에는 사용할 수 있지만 `list`에는 사용할 수 없습니다. `list`는 연결 구조에 맞는 멤버 함수 `sort`를 제공합니다.

## 11. 상수 반복자

상수 컨테이너를 통해 원소를 변경할 수 없어야 합니다.

```cpp
void print(const std::vector<int> &values)
{
    std::vector<int>::const_iterator it = values.begin();
    for (; it != values.end(); ++it)
        std::cout << *it << '\n';
}
```

`const_iterator`는 단순한 편의 기능이 아니라 변경 권한을 제한하는 인터페이스입니다. 사용자 정의 컨테이너를 구현할 때도 상수·비상수 `begin`과 `end`를 구분합니다.

## 12. 반복자, 참조와 포인터 무효화

컨테이너를 변경하면 기존 원소나 위치를 가리키던 반복자, 참조와 포인터가 무효화될 수 있습니다.

### `vector`

- 재할당 발생: 모든 반복자, 참조와 포인터가 무효화됩니다.
- 재할당 없는 삽입: 삽입 위치와 그 이후를 가리키는 반복자, 참조와 포인터가 무효화됩니다.
- 삭제: 삭제 위치와 그 이후를 가리키는 반복자, 참조와 포인터가 무효화됩니다.

### `deque`

삽입·삭제 위치와 연산 종류에 따라 무효화 규칙이 달라집니다. 사용하는 연산의 표준 라이브러리 계약을 확인합니다.

### `list`

삽입은 기존 원소를 가리키는 반복자와 참조를 무효화하지 않습니다. 삭제한 원소를 가리키던 것만 무효화됩니다.

### `map`

삽입은 기존 원소의 반복자와 참조를 무효화하지 않습니다. 삭제는 삭제된 원소를 가리키던 것만 무효화합니다.

무효화 가능성이 있는 변경 뒤에는 오래 보관한 반복자를 계속 사용하지 말고 필요한 위치를 다시 찾습니다.

## 13. 표준 알고리즘

수동 반복문보다 알고리즘 이름이 의도를 더 직접적으로 표현할 수 있습니다.

```cpp
std::vector<int>::iterator found =
    std::find(values.begin(), values.end(), target);
```

자주 사용하는 알고리즘은 다음과 같습니다.

- 검색: `find`, `find_if`
- 비교: `equal`, `lexicographical_compare`
- 변환·복사: `copy`, `transform`
- 정렬·범위 검색: `sort`, `lower_bound`
- 순회: `for_each`

알고리즘을 선택할 때는 다음을 확인합니다.

- 필요한 반복자 범주
- 원소를 변경하는지
- 출력 범위가 충분한지
- 비교 함수가 지켜야 하는 규칙
- 연산 중 반복자가 무효화되는지

## 14. 함수 객체

C++98에는 람다가 없으므로 상태를 가진 호출 가능 객체를 클래스로 만듭니다.

```cpp
class LongerThan
{
public:
    explicit LongerThan(std::size_t limit) : limit_(limit) {}

    bool operator()(const std::string &value) const
    {
        return value.size() > limit_;
    }

private:
    std::size_t limit_;
};
```

```cpp
std::find_if(values.begin(), values.end(), LongerThan(8));
```

함수 객체는 조건자, 비교 함수와 변환 정책을 알고리즘에 전달하는 C++98의 핵심 수단입니다.

## 15. 비교 함수 규칙

정렬 비교 함수는 엄격 약순서를 만족해야 합니다.

- `comp(x, x)`는 `false`입니다.
- `comp(a, b)`가 참이면 `comp(b, a)`는 거짓입니다.
- 선후 관계와 동치 관계가 일관된 추이성을 가집니다.

정수 비교를 `left - right < 0`으로 구현하면 뺄셈에서 부호 있는 정수 오버플로가 발생할 수 있습니다. `left < right`를 직접 사용합니다.

비교 결과가 현재 시각, 가변 전역 상태나 난수에 의존하면 정렬 알고리즘의 전제가 깨집니다.

## 16. 컨테이너 어댑터

`std::stack`과 `std::queue`는 다른 컨테이너 위에 제한된 인터페이스를 제공합니다.

```cpp
std::stack<int> pending;
pending.push(10);
int top = pending.top();
pending.pop();
```

스택이 반복자를 제공하지 않는 것은 누락이 아닙니다. 맨 위에서만 넣고 뺀다는 규칙을 인터페이스로 강제합니다. 내부 원소 전체를 순회하거나 검색해야 한다면 스택이 요구사항에 맞는 구조인지 다시 검토합니다.

---

## 단계형 실습

### 1단계: 함수 템플릿

다음을 구현합니다.

```cpp
template <class T> void swapValue(T &a, T &b);
template <class T> const T &minimum(const T &a, const T &b);
template <class T> const T &maximum(const T &a, const T &b);
```

`int`, `std::string`, 사용자 정의 값 타입으로 검증합니다.

### 2단계: 범위 함수

```cpp
template <class Iterator, class Function>
void apply(Iterator first, Iterator last, Function function);
```

포인터 범위와 `std::vector` 반복자에서 모두 동작하게 합니다.

### 3단계: `Array<T>`

필요한 인터페이스는 다음과 같습니다.

```cpp
template <class T>
class Array
{
public:
    Array();
    explicit Array(std::size_t size);
    Array(const Array &other);
    ~Array();
    Array &operator=(const Array &other);

    T &operator[](std::size_t index);
    const T &operator[](std::size_t index) const;
    std::size_t size() const;
};
```

범위 밖 접근 정책, 복사 독립성과 할당 실패 뒤 상태를 테스트합니다.

### 4단계: 반복자와 알고리즘

- 수동 검색을 `std::find`로 교체
- 조건 검색을 함수 객체와 `std::find_if`로 교체
- 정렬 비교 함수 작성
- `lower_bound` 결과의 경계 처리

### 5단계: 변형

- `const Array<T>` 접근 추가
- 복사 중 예외를 던지는 원소 타입 사용
- 임의 접근 반복자가 아닌 범위에 `std::sort`를 호출하고 오류 읽기
- `vector` 재할당 전후에 반복자가 무효화되는 이유 설명

## 템플릿과 반복자에서 자주 발생하는 오류

- 템플릿 선언만 헤더에 두고 정의를 `.cpp`에 숨깁니다.
- 반환 참조가 지역 객체나 수명이 짧은 임시 객체를 가리킵니다.
- `typename`이 필요한 의존 타입을 값으로 해석하게 둡니다.
- `end()`를 역참조합니다.
- `vector::push_back` 뒤 재할당으로 무효화된 반복자를 사용합니다.
- 비교 함수가 엄격 약순서를 깨뜨립니다.
- 모든 반복문을 억지로 알고리즘으로 바꿔 흐름을 오히려 읽기 어렵게 만듭니다.

## 다른 언어의 제네릭과 비교

Java·C#의 제네릭, Rust의 제네릭과 트레이트, TypeScript의 타입 매개변수도 타입이 달라도 같은 요구사항을 수행하도록 코드를 구성합니다. 다만 코드 생성, 런타임 타입 소거와 제약 표현 방식은 다릅니다. 반복자와 알고리즘의 분리, 반열린 범위와 비교 함수 규칙은 언어가 달라도 그대로 적용됩니다.

## 제네릭 컨테이너 점검

- 템플릿이 요구하는 연산을 함수 본문에서 추출할 수 있습니까?
- 템플릿 정의가 인스턴스화 지점에 보여야 하는 이유는 무엇입니까?
- `[first, last)`의 `last`를 역참조하면 안 되는 이유는 무엇입니까?
- `std::sort`가 `list` 반복자를 받을 수 없는 이유는 무엇입니까?
- 현재 컨테이너 변경이 어떤 반복자와 참조를 무효화합니까?
- 템플릿과 가상 인터페이스 중 하나를 선택한 근거를 설명할 수 있습니까?
