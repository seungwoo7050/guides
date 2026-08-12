# 템플릿, 반복자와 STL 알고리즘

## 타입이 달라도 같은 책임을 구현합니다

같은 코드를 타입마다 복사하면 수정과 검증도 반복됩니다. 실행 시간 다형성이 필요하지 않은 차이까지 가상 인터페이스로 감추면 불필요한 객체 계층이 생깁니다. C++ 템플릿은 타입이 달라도 같은 표현과 책임을 수행하는 코드를 컴파일 시점에 만듭니다.

STL은 템플릿 위에서 컨테이너, 반복자와 알고리즘을 분리합니다. 알고리즘의 적용 범위는 구체 컨테이너가 아니라 반복자가 제공하는 능력으로 판단합니다.

## 템플릿과 STL의 연결

```text
템플릿 + 타입의 요구 연산 → 인스턴스화 → 구체 코드

container ── begin/end iterator 범위 ── algorithm
```

컨테이너와 알고리즘이 서로의 구체 타입을 몰라도 되는 이유는 반복자가 이동·역참조 능력을 계약으로 제공하기 때문입니다.

## 배열과 vector를 구현하며 확인

[템플릿 배열과 반복자 실습](../../exercises/02-cpp98-systems/generic-programming/template-array/README.md)에서 함수 템플릿, 반복자 범위와 `Array<T>`를 순서대로 구현합니다.

```sh
cd exercises/02-cpp98-systems/generic-programming/template-array
make observe
```

위 명령은 저장소 루트에서 시작합니다. `make observe`는 좁은 `demo.cpp`를 reference API에 연결해 결과만 관찰하는 선택 실험입니다. workspace의 `skeleton/`을 구현한 뒤 다시 저장소 루트에서 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=generic-programming/template-array
```

reference source는 learner 검증을 통과한 뒤에만 비교합니다. canonical `compile-fail` 검사는 반복자 요구를 만족하지 않는 타입과 const 경계를 의도적으로 넘깁니다. 컴파일 실패도 라이브러리 계약을 검증하는 테스트임을 확인합니다.

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

이 함수는 “모든 타입”에 동작하지 않습니다. 사용한 표현이 계약입니다.

- `T`에 `<`가 정의되어야 합니다.
- 반환 참조가 함수 뒤에도 유효해야 합니다.
- 두 인자가 비교 가능한 같은 의미를 가져야 합니다.

C++98에는 콘셉트 문법이 없으므로 요구 조건을 문서, 테스트와 컴파일 실패로 드러냅니다.

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

호출 시 컴파일러가 인자에서 `T`를 추론합니다.

```cpp
int a = 1;
int b = 2;
swapValue(a, b);
```

타입 추론이 모호하거나 원하는 타입을 명시하려면 템플릿 인자를 직접 쓸 수 있습니다.

```cpp
const long result = smaller<long>(3, 7);
```

함수 템플릿과 일반 함수가 동시에 후보라면 일반적인 오버로드 해석 규칙이 적용됩니다. 특정 타입을 위한 동작은 함수 템플릿 specialization보다 일반 오버로드가 더 읽기 쉬운 경우가 많습니다.

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

클래스 템플릿은 원소 타입마다 다른 코드가 필요할 때 유용하지만, 코드 크기와 컴파일 시간이 늘 수 있습니다. 실제로 사용되는 타입과 함수만 인스턴스화되는 경우가 많습니다.

## 4. 인스턴스화와 오류 위치

템플릿은 구체 타입을 넣는 순간 실제 코드가 만들어집니다. 정의만 보았을 때는 문제가 없던 표현이 특정 타입에서 실패할 수 있습니다.

```cpp
template <class T>
void printTwice(const T &value)
{
    std::cout << value << value;
}
```

`operator<<`가 없는 타입으로 호출하면 호출 지점에서 긴 오류가 발생합니다. 오류 메시지를 읽을 때는 다음 순서로 좁힙니다.

1. 처음 인스턴스화된 사용자 코드 위치를 찾습니다.
2. 템플릿 안에서 실패한 표현을 찾습니다.
3. 타입 `T`가 그 표현을 제공하는지 확인합니다.
4. 필요 없는 연산을 템플릿이 요구하고 있지 않은지 봅니다.

## 5. 템플릿 정의 위치

컴파일러가 템플릿을 인스턴스화하려면 선언뿐 아니라 정의도 보여야 합니다. 따라서 함수 본문을 보통 헤더에 둡니다.

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

본문을 별도 `.tpp` 파일에 두고 헤더 끝에서 포함해도 원리는 같습니다. 명시적 instantiation으로 `.cpp`에 둘 수 있지만 지원 타입을 미리 고정하는 별도 설계이므로 입문 단계에서는 사용하지 않습니다.

## 6. 의존 이름과 특수화

### `typename`

템플릿 인자에 따라 달라지는 멤버 이름이 타입일 때 `typename`으로 알립니다.

```cpp
template <class Container>
void printAll(const Container &values)
{
    typename Container::const_iterator it = values.begin();
    for (; it != values.end(); ++it)
        std::cout << *it << '\n';
}
```

`Container::const_iterator`가 타입인지 정적 멤버인지 템플릿 정의 시점에는 확정할 수 없기 때문입니다.

### 완전·부분 특수화

클래스 템플릿은 특정 타입 또는 타입 패턴에 별도 정의를 줄 수 있습니다.

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

`T*` 패턴을 처리하므로 부분 특수화입니다. 특수화는 일반 규칙으로 표현하기 어려운 구조적 차이가 있을 때만 사용합니다.

## 7. 실행 시간 다형성과 비교

| 질문 | 템플릿 | 가상 인터페이스 |
|---|---|---|
| 구현 선택 시점 | 컴파일 | 실행 |
| 호출 비용 | 보통 정적 호출 | 간접 가상 호출 |
| 타입 집합 | 컴파일 시 알려짐 | 실행 중 여러 구현 사용 가능 |
| 요구 표현 | 템플릿 본문 | 기반 클래스 인터페이스 |
| 별도 컴파일 | 정의가 보여야 함 | 인터페이스만으로 가능 |

원소 타입에 같은 알고리즘을 적용한다면 템플릿이 자연스럽습니다. 설정에 따라 실행 중 백엔드를 바꾸거나 서로 다른 구현을 한 컨테이너에 보관한다면 가상 인터페이스가 자연스럽습니다.

## 8. STL의 세 축

```text
container: 데이터를 보관합니다.
iterator:  범위 안의 위치와 이동 능력을 표현합니다.
algorithm: iterator 범위에 동작합니다.
```

알고리즘은 `std::vector`나 `std::list` 자체보다 반복자가 제공하는 능력에 의존합니다.

```cpp
std::vector<int> values;
std::sort(values.begin(), values.end());
```

## 9. 반열린 범위 `[first, last)`

`first`는 첫 원소를 가리키고 `last`는 마지막 원소의 다음 위치를 가리킵니다.

```text
[first, last)
```

이 규약의 장점:

- 빈 범위에서는 `first == last`가 성립합니다.
- 처리한 원소 수와 다음 위치가 자연스럽게 연결됩니다.
- 한 범위를 `[first, middle)`, `[middle, last)`로 겹치지 않게 나눕니다.

`end()`는 원소가 아니므로 역참조하지 않습니다.

## 10. 반복자 범주

| 범주 | 핵심 능력 | 대표 예 |
|---|---|---|
| 입력 | 한 방향 읽기 | 입력 스트림 반복자 |
| 전방 | 여러 번 통과, 한 방향 | 전방 구조 |
| bidirectional | `++`, `--` | `list`, `map` |
| 무작위 접근 | 덧셈, 차이, 인덱스, 순서 비교 | 포인터, `vector`, `deque` |

능력이 강한 반복자는 약한 범주의 요구를 만족합니다. `std::sort`는 무작위-접근 반복자가 필요하므로 `vector`에는 쓸 수 있지만 `list`에는 쓸 수 없습니다. `list`는 자기 구조에 맞는 멤버 `sort`를 제공합니다.

## 11. const 반복자

const 컨테이너를 통해 원소를 수정할 수 없어야 합니다.

```cpp
void print(const std::vector<int> &values)
{
    std::vector<int>::const_iterator it = values.begin();
    for (; it != values.end(); ++it)
        std::cout << *it << '\n';
}
```

`const_iterator`는 편의가 아니라 캡슐화 경계입니다. 사용자 컨테이너를 구현한다면 const와 non-const `begin`/`end`를 구분합니다.

## 12. 반복자, 참조와 포인터 무효화

컨테이너를 변경하면 기존 위치를 가리키던 handle이 무효가 될 수 있습니다.

### `vector`

- 용량이 증가하는 재할당: 모든 반복자, 포인터, 참조 무효화
- 중간 삽입/삭제: 위치 이후가 무효화

### `deque`

연산 종류와 위치에 따라 반복자 무효화 규칙이 복잡합니다. 구체 연산의 계약을 확인합니다.

### `list`

일반적으로 다른 원소의 삽입·삭제가 기존 원소 반복자를 무효화하지 않습니다. 삭제된 원소 자체는 무효입니다.

### `map`

삽입은 기존 반복자를 보통 유지하고, 삭제는 삭제된 원소만 무효화합니다.

무효화 가능성이 있는 연산 뒤에는 오래 보관한 반복자를 다시 얻는 것이 기본 방어입니다.

## 13. 표준 알고리즘

수동 반복문보다 알고리즘 이름이 의도를 더 직접적으로 표현할 수 있습니다.

```cpp
std::vector<int>::iterator found =
    std::find(values.begin(), values.end(), target);
```

자주 쓰는 범주:

- 검색: `find`, `find_if`
- 비교: `equal`, `lexicographical_compare`
- 변환·복사: `copy`, `transform`
- 정렬·범위: `sort`, `lower_bound`
- 순회: `for_each`

알고리즘을 선택할 때는 다음을 확인합니다.

- 필요한 반복자 범주
- 값을 수정하는지
- 출력 범위가 충분한지
- 비교 함수가 어떤 계약을 가져야 하는지
- 반복자 무효화가 발생하는지

## 14. 함수 객체

C++98에는 lambda가 없으므로 상태를 가진 호출 가능 객체를 클래스로 만듭니다.

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

함수 객체는 조건자, 비교 함수와 변환 정책을 템플릿에 전달하는 C++98의 핵심 방식입니다.

## 15. 비교 함수 계약

정렬 비교자는 엄격 약순서를 만족해야 합니다.

- `comp(x, x)`는 false
- 관계의 추이성이 유지됨
- 두 값이 서로 작지 않다면 같은 동치 그룹으로 일관되게 취급

정수 비교를 `left - right < 0`으로 구현하면 뺄셈 오버플로가 날 수 있습니다. 직접 `left < right`를 사용합니다.

비교 결과가 시간, 전역 가변 상태나 무작위 값에 의존하면 정렬 알고리즘의 전제가 깨집니다.

## 16. 컨테이너 어댑터

`std::stack`과 `std::queue`는 다른 컨테이너 위에 제한된 인터페이스를 제공합니다.

```cpp
std::stack<int> pending;
pending.push(10);
int top = pending.top();
pending.pop();
```

스택이 반복자를 공개하지 않는 것은 실수가 아닙니다. “맨 위에서만 넣고 뺀다”는 계약을 강제합니다. 내부 컨테이너 전체를 순회해야 한다면 스택이 요구사항에 맞는 구조인지 다시 봅니다.

---

## 단계형 실습

### 1단계: 함수 템플릿

다음을 구현합니다.

```cpp
template <class T> void swapValue(T &a, T &b);
template <class T> const T &minimum(const T &a, const T &b);
template <class T> const T &maximum(const T &a, const T &b);
```

`int`, `std::string`, 사용자 값 타입으로 검증합니다.

### 2단계: 범위 함수

```cpp
template <class Iterator, class Function>
void apply(Iterator first, Iterator last, Function function);
```

포인터 범위와 `std::vector` 반복자에서 모두 동작하게 합니다.

### 3단계: `Array<T>`

필요한 인터페이스:

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
- 조건 검색을 함수 객체 + `std::find_if`로 교체
- 정렬 비교 함수 작성
- `lower_bound` 결과의 경계 처리

### 5단계: 변형

- `const Array<T>` 접근 추가
- 복사 중 예외를 던지는 원소 타입 사용
- 무작위-접근가 아닌 반복자에 `std::sort`를 호출해 오류 읽기
- `vector` 재할당 전후 반복자가 왜 무효인지 설명

## 템플릿·반복자에서 생기는 오류

- 템플릿 선언만 헤더에 두고 정의를 `.cpp`에 숨깁니다.
- 반환 참조가 지역 객체를 가리킵니다.
- `typename`이 필요한 의존 타입을 값으로 해석하게 둡니다.
- `end()`를 역참조합니다.
- `vector::push_back` 뒤 재할당된 옛 반복자를 사용합니다.
- 비교 함수가 엄격 약순서를 깨뜨립니다.
- 모든 반복문을 억지로 알고리즘으로 바꿔 흐름을 더 읽기 어렵게 만듭니다.

## Rust·Java와 비교하는 제네릭

Java와 C#의 제네릭, Rust의 제네릭과 특성, TypeScript의 타입 매개변수도 타입이 달라도 같은 계약을 수행합니다. 다만 코드 생성, 런타임 타입 소거와 제약 표현 방식은 다릅니다. 반복자와 알고리즘 분리, 반열린 범위, 비교 함수 계약은 언어를 넘어 재사용됩니다.

## 제네릭 컨테이너 점검

- 템플릿이 요구하는 연산을 함수 본문에서 추출할 수 있습니까?
- 템플릿 정의가 호출 지점에 보여야 하는 이유는 무엇입니까?
- `[first, last)`의 `last`를 역참조하면 안 되는 이유는 무엇입니까?
- `std::sort`가 `list` 반복자를 받을 수 없는 이유는 무엇입니까?
- 현재 컨테이너 변경이 어떤 반복자와 참조를 무효화합니까?
- 템플릿과 가상 인터페이스 중 하나를 선택한 근거를 설명할 수 있습니까?
