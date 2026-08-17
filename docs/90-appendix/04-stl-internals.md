# STL 컨테이너 내부 구조

## 이 문서를 참고할 시점

동적 배열과 트리 기반 컨테이너의 메모리 구성을 살펴보거나, 미초기화 저장 공간에서 객체 수명과 예외 안전성을 검증할 때 참고합니다. 공개 API를 사용하는 방법은 먼저 [템플릿, 반복자와 STL 알고리즘](../02-cpp98-systems/06-templates-iterators-and-stl.md)에서 다룹니다.

다음 내용을 설명할 수 있어야 합니다.

- Rule of Three와 RAII
- 기본·강한·무예외 보장
- 반복자와 반열린 범위
- `vector`, `map`의 공개 동작과 반복자 무효화 규칙
- 함수·클래스 템플릿

## 살펴볼 내용

- 저장 공간 확보와 객체 생성을 분리합니다.
- 부분 생성 실패 시 실제로 생성된 원소만 롤백합니다.
- `iterator_traits`와 반복자 범주 태그의 역할을 설명합니다.
- SFINAE로 정수 인자와 반복자 인자 오버로드를 구분합니다.
- 동적 배열 재할당에서 강한 예외 보장을 구현합니다.
- 노드 기반 컨테이너가 할당자를 내부 노드 타입으로 바꾸는 이유를 설명합니다.

## `mini-vector`로 내부 동작 확인

[`mini-vector` 선택 심화 실습](../../exercises/02-cpp98-systems/generic-programming/mini-vector/README.md)은 할당자, 미초기화 저장 공간, 부분 생성 롤백과 예외를 던지지 않는 포인터 교환을 실제 코드로 확인합니다. C++98 주 경로의 필수 단계가 아니라 저장 공간과 예외 안전성을 더 깊게 확인하기 위한 선택 실습입니다.

```sh
cd exercises/02-cpp98-systems/generic-programming/mini-vector
make observe
```

위 명령은 저장소 루트에서 실행합니다. `make observe`는 작은 `demo.cpp`로 크기와 용량 변화를 관찰하는 선택 실험입니다. 워크스페이스의 `skeleton/`을 구현한 뒤 저장소 루트에서 다음 명령으로 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=generic-programming/mini-vector
```

학습자 구현 검증을 통과한 뒤에만 참조 구현과 비교합니다. 기준 `fail-copy` 검사는 저장소 전체 검증에서 별도로 실행합니다.

---

## 1. 컨테이너의 핵심 불변식

동적 배열의 대표적인 불변식은 다음과 같습니다.

```text
0 <= size <= capacity
[0, size)에는 살아 있는 T 객체가 있습니다.
[size, capacity)에는 T를 담을 수 있지만 아직 T 객체는 없는 저장 공간이 있습니다.
capacity가 0보다 크면 data는 유효한 할당 영역을 가리킵니다.
```

용량이 0일 때 `data`를 널로 둘지, 할당자가 돌려준 특수 값을 보관할지는 구현 정책입니다. 어느 쪽이든 역참조해서는 안 됩니다.

트리 기반 `map`의 대표적인 불변식은 다음과 같습니다.

```text
각 노드는 값 하나를 소유합니다.
키 정렬 규칙이 모든 연결에서 유지됩니다.
부모·자식 링크가 서로 일치합니다.
size는 실제 노드 수와 같습니다.
중복 키 금지 규칙이 유지됩니다.
균형 트리라면 균형 조건도 유지됩니다.
```

함수 구현 전에 어느 구간에 객체가 살아 있는지 적지 않으면 예외 경로에서 소멸 범위를 틀리기 쉽습니다.

## 2. 저장 공간과 객체 생성 분리

`new T[n]`은 저장 공간 확보와 `n`개 객체의 기본 생성을 함께 수행합니다. `vector`는 용량만큼 저장 공간을 확보하고 크기만큼만 객체를 생성해야 합니다.

C++98 할당자는 이 책임을 분리합니다.

| 연산 | 역할 |
|---|---|
| `allocate(n)` | `n`개의 `T`를 담을 미초기화 저장 공간 확보 |
| `construct(p, value)` | `p` 위치에 `T` 객체 생성 |
| `destroy(p)` | `p`의 객체 수명 종료, 저장 공간은 유지 |
| `deallocate(p, n)` | 저장 공간 반환 |

```cpp
std::allocator<T> alloc;
T *memory = alloc.allocate(4);

alloc.construct(memory, value);
alloc.destroy(memory);
alloc.deallocate(memory, 4);
```

`allocate`가 성공해도 해당 위치에는 아직 `T` 객체가 없습니다. 역참조나 대입을 하기 전에 `construct`로 객체 수명을 시작해야 합니다.

`allocate(0)`의 반환값에 의존하지 않는 편이 단순합니다. 용량이 0이면 할당을 건너뛰고, 실제로 할당한 포인터만 동일한 할당자와 크기로 `deallocate`합니다.

## 3. 위치 지정 `new`와 명시적 소멸

고전적인 할당자의 `construct`는 위치 지정 `new`를 사용합니다.

```cpp
new (address) T(value);
```

이미 확보된 저장 공간에서 객체 수명만 시작합니다. 짝이 되는 동작은 메모리 반환이 아니라 명시적인 소멸자 호출입니다.

```cpp
address->~T();
```

같은 주소에 새 객체를 만들기 전에 이전 객체의 수명이 끝났는지 확인합니다. 기본 타입만 생각해 소멸자 호출을 생략하면 사용자 정의 타입이 가진 자원이 누수될 수 있습니다.

위치 지정 `new`를 사용하려면 일반적으로 `<new>`를 포함합니다.

## 4. 부분 생성 실패 롤백

여러 객체를 순서대로 생성하다 세 번째 복사에서 예외가 발생할 수 있습니다.

```cpp
T *newData = alloc.allocate(newCapacity);
std::size_t built = 0;

try
{
    for (; built < oldSize; ++built)
        alloc.construct(newData + built, oldData[built]);
}
catch (...)
{
    while (built != 0)
    {
        --built;
        alloc.destroy(newData + built);
    }
    alloc.deallocate(newData, newCapacity);
    throw;
}
```

롤백 원칙은 다음과 같습니다.

1. 생성에 성공한 원소 수를 별도로 기록합니다.
2. 실제로 생성된 객체만 역순으로 소멸시킵니다.
3. 저장 공간을 같은 할당자로 반환합니다.
4. 원래 예외를 `throw;`로 다시 던집니다.
5. 모든 준비가 끝나기 전에는 기존 컨테이너를 변경하지 않습니다.

원소 소멸자는 예외를 밖으로 내보내지 않아야 합니다. 롤백 중 소멸자가 예외를 던지면 원래 실패를 안전하게 처리할 수 없습니다.

## 5. 동적 배열 재할당

재할당의 큰 단계는 다음과 같습니다.

```text
새 저장 공간 확보
→ 기존 원소를 새 공간에 복사
→ 모든 복사 성공
→ 기존 원소 소멸
→ 기존 저장 공간 반환
→ data와 capacity를 새 값으로 교체
```

복사 중 실패하면 새 공간만 정리하고 원본은 그대로 둡니다. 이것이 강한 예외 보장입니다.

```cpp
void reallocate(size_type newCapacity)
{
    pointer candidate = alloc_.allocate(newCapacity);
    size_type built = 0;

    try
    {
        for (; built < size_; ++built)
            alloc_.construct(candidate + built, data_[built]);
    }
    catch (...)
    {
        destroyRange(candidate, built);
        alloc_.deallocate(candidate, newCapacity);
        throw;
    }

    destroyRange(data_, size_);
    if (data_ != 0)
        alloc_.deallocate(data_, capacity_);

    data_ = candidate;
    capacity_ = newCapacity;
}
```

이 함수는 `newCapacity >= size_`이고 양수라는 전제를 별도로 확인해야 합니다. 반영 뒤 `size_`는 그대로 유지됩니다. `T`의 복사가 원본을 변경하지 않는 정상적인 값 복사라는 전제도 필요합니다.

삽입을 위해 재할당하면서 새 원소까지 만들어야 한다면 기존 원소와 새 원소를 모두 후보 공간에 완성한 뒤 반영해야 강한 예외 보장을 유지할 수 있습니다.

## 6. 증가 정책과 상각 비용

용량을 매번 1씩 늘리면 `n`개 원소를 추가하는 동안 총 O(n²)번의 원소 복사가 발생할 수 있습니다. 용량을 2배처럼 기하급수적으로 늘리면 전체 복사량이 O(n)에 머물러 끝 삽입의 상각 비용이 O(1)이 됩니다.

성장 배수는 표준이 강제하지 않습니다. 다음 항목을 함께 고려합니다.

- 재할당 횟수
- 사용하지 않는 여유 메모리
- `size + 추가량` 계산의 오버플로
- `max_size` 초과
- 요청 용량보다 작은 값이 선택되지 않는지

```cpp
if (requested > max_size())
    throw std::length_error("capacity overflow");
```

덧셈이나 배수 계산 자체가 오버플로하기 전에 나눗셈 형태의 상한 검사를 수행합니다.

## 7. 범위 생성자와 개수 생성자의 모호성

동적 배열에는 다음 두 형태가 함께 존재할 수 있습니다.

```cpp
vector(size_type count, const value_type &value);

template <class InputIterator>
vector(InputIterator first, InputIterator last);
```

`vector<int> values(5, 3)`에서 템플릿 생성자도 `InputIterator = int`로 추론될 수 있습니다. 정수를 반복자처럼 사용하려다 템플릿 내부에서 오류가 발생할 수 있습니다.

C++98에서는 SFINAE를 사용해 정수 타입일 때 범위 생성자를 후보에서 제거할 수 있습니다.

```cpp
template <bool Condition, class T = void>
struct enable_if
{
};

template <class T>
struct enable_if<true, T>
{
    typedef T type;
};
```

```cpp
template <class InputIterator>
vector(
    InputIterator first,
    InputIterator last,
    typename enable_if<!is_integral<InputIterator>::value>::type * = 0);
```

조건이 거짓이면 치환 중 `type`이 없어지고 해당 함수 템플릿만 후보에서 제외됩니다. 함수 본문을 인스턴스화한 뒤 발생한 오류는 SFINAE가 아니므로 제약은 함수 시그니처의 치환 영역에 둡니다.

## 8. `integral_constant`와 타입 특성

컴파일 시점 값을 값이자 타입으로 표현합니다.

```cpp
template <class T, T Value>
struct integral_constant
{
    static const T value = Value;
    typedef T value_type;
    typedef integral_constant<T, Value> type;
};

typedef integral_constant<bool, true> true_type;
typedef integral_constant<bool, false> false_type;
```

기본 `is_integral`은 거짓이고 정수 타입마다 완전 특수화를 제공합니다. `const`와 `volatile` 한정자를 제거하는 부분 특수화도 필요합니다.

```cpp
template <class T>
struct is_integral : false_type {};

template <>
struct is_integral<int> : true_type {};

template <class T>
struct is_integral<const T> : is_integral<T> {};
```

실제 구현은 `bool`, 문자형, 모든 부호 있는·없는 정수형과 `volatile`, `const volatile` 조합을 빠짐없이 처리해야 합니다. 학습용 구현의 지원 범위를 테스트로 고정합니다.

## 9. 태그 디스패치

특성 결과나 반복자 범주를 빈 태그 타입으로 전달해 컴파일 시점에 오버로드를 선택합니다.

```cpp
template <class Iterator>
void advanceImpl(
    Iterator &it,
    int distance,
    std::random_access_iterator_tag)
{
    it += distance;
}

template <class Iterator>
void advanceImpl(
    Iterator &it,
    int distance,
    std::input_iterator_tag)
{
    while (distance-- > 0)
        ++it;
}
```

런타임 `if`가 아니라 태그 타입에 따라 함수가 선택됩니다. 입력 반복자는 뒤로 이동할 수 없으므로 두 번째 오버로드는 음수 거리를 지원하지 않는다는 전제가 필요합니다. 양방향 반복자에는 음수 거리를 처리하는 별도 구현을 둘 수 있습니다.

## 10. `iterator_traits`

일반 반복자는 내부 typedef로 값 타입과 범주를 공개합니다.

```cpp
template <class Iterator>
struct iterator_traits
{
    typedef typename Iterator::value_type value_type;
    typedef typename Iterator::difference_type difference_type;
    typedef typename Iterator::pointer pointer;
    typedef typename Iterator::reference reference;
    typedef typename Iterator::iterator_category iterator_category;
};
```

원시 포인터에는 멤버 typedef가 없으므로 부분 특수화합니다.

```cpp
template <class T>
struct iterator_traits<T *>
{
    typedef T value_type;
    typedef std::ptrdiff_t difference_type;
    typedef T *pointer;
    typedef T &reference;
    typedef std::random_access_iterator_tag iterator_category;
};
```

이 특수화 덕분에 포인터도 STL 반복자 규칙에 참여합니다. `const T*`는 위 특수화에서 `T`가 `const U`로 추론되어 읽기 전용 참조와 포인터 타입을 자연스럽게 얻습니다.

## 11. 사용자 반복자의 최소 요구사항

반복자가 실제 능력보다 강한 범주를 선언하면 알고리즘이 제공하지 못하는 연산과 복잡도를 가정하게 됩니다.

- 입력 반복자: 한 방향 읽기와 전진
- 전방 반복자: 여러 번 순회 가능한 한 방향 전진
- 양방향 반복자: 전진과 후진
- 임의 접근 반복자: 상수 시간 거리·덧셈·인덱스·순서 비교

`map`의 트리 반복자를 임의 접근 반복자로 선언할 수 없습니다. 다음 노드로 이동할 수는 있지만 `it + n`을 상수 시간에 제공하지 못합니다.

반복자의 동등 비교는 같은 범위나 허용된 관련 범위 안에서만 의미가 있을 수 있습니다. 서로 다른 컨테이너의 반복자를 임의로 비교하지 않습니다.

## 12. `reverse_iterator`

역방향 반복자는 기반 반복자가 가리키는 위치의 바로 앞 원소를 역참조합니다.

```text
rbegin = reverse_iterator(end)
rend   = reverse_iterator(begin)
```

```cpp
reference operator*() const
{
    Iterator temporary = current_;
    --temporary;
    return *temporary;
}
```

이 한 칸 차이 덕분에 빈 범위에서도 `rbegin == rend`가 자연스럽게 성립합니다. `base()`는 현재 역방향 반복자가 역참조하는 원소가 아니라 그 다음 정방향 위치를 반환합니다.

`rend()`를 역참조하면 내부적으로 `begin()` 앞을 만들게 되므로 유효하지 않습니다.

## 13. 노드 할당자와 `rebind`

사용자가 `map<Key, T>`에 제공하는 할당자는 일반적으로 `pair<const Key, T>`용입니다. 실제 구현은 이 값을 트리 노드 안에 저장하므로 노드 타입용 할당자가 필요합니다.

```cpp
typedef typename allocator_type::template rebind<Node>::other
    node_allocator_type;
```

- `typename`: 결과가 타입임을 알립니다.
- `template`: 의존 타입의 멤버 템플릿임을 알립니다.
- `rebind<Node>`: 같은 할당자 계열을 노드 타입용으로 바꿉니다.

노드 생성도 저장 공간 할당과 객체 생성을 분리합니다. 노드나 내부 값 생성이 실패하면 연결 구조에 공개하기 전에 생성된 부분을 정리하고 저장 공간을 반환합니다.

## 14. 트리 노드 수명과 링크

노드 삽입은 다음 순서로 처리합니다.

```text
삽입 위치 탐색
→ 노드 저장 공간 확보
→ 노드와 값 완전 생성
→ 부모·자식 링크에 연결
→ size 증가
→ 균형 조건 복구
```

완성되지 않은 노드를 트리에 먼저 연결하면 생성 실패 시 트리 구조가 깨집니다. 후보를 완성한 뒤 트리에 연결합니다.

삭제의 큰 순서는 다음과 같습니다.

```text
삭제 대상과 교체 노드 결정
→ 링크와 균형 정보 수정
→ 외부 반복자에서 대상 노드 접근 불가
→ 값과 노드 소멸
→ 저장 공간 반환
→ size 감소
```

두 자식을 가진 노드 삭제, 루트 교체와 후속 노드 이동에서는 부모·자식 링크와 반복자 안정성을 모두 확인합니다. 공개 키가 `const`라면 값을 단순 대입해 교체할 수 없는 점도 내부 알고리즘에 반영해야 합니다.

## 15. 반복자 무효화 규칙 반영

공개 컨테이너의 무효화 규칙은 내부 구현에 제약을 줍니다.

- `vector` 재할당: 모든 반복자, 참조와 포인터가 무효화됩니다.
- `vector` 비재할당 삽입: 삽입 위치와 그 이후가 무효화됩니다.
- `map` 삽입: 기존 반복자와 참조가 유지됩니다.
- `map` 삭제: 삭제한 원소를 가리키던 반복자와 참조만 무효화됩니다.

`map` 구현이 삽입 때 기존 노드를 다른 주소로 옮기면 표준의 반복자 안정성 요구를 깨뜨립니다. 노드 기반 구조가 각 원소의 주소를 안정적으로 유지하는 이유입니다.

## 16. `swap`과 할당자

컨테이너 `swap`이 내부 포인터와 크기만 교환하려면 각 객체가 나중에 상대 객체가 할당한 저장 공간을 안전하게 해제할 수 있어야 합니다. 상태를 가진 서로 다른 할당자 사이에서 단순 포인터 교환이 허용되는지는 C++98 할당자 요구사항과 프로젝트 지원 범위를 확인해야 합니다.

학습 구현이 상태 없는 `std::allocator`만 지원한다면 그 제한을 문서화하고 테스트합니다. 할당자 상태를 무시한 채 범용 구현이라고 주장하지 않습니다.

`swap`을 강한 예외 보장의 최종 반영 단계로 사용하려면 해당 지원 범위에서 예외를 던지지 않아야 합니다.

## 17. 관계 연산과 알고리즘 재사용

순차 컨테이너의 `==`는 길이와 모든 원소가 같아야 합니다. `<`는 사전식 순서를 사용합니다.

```cpp
if (left.size() != right.size())
    return false;
return ft::equal(left.begin(), left.end(), right.begin());
```

두 범위의 길이를 확인하지 않고 공통 접두 범위만 비교하면 오른쪽 범위가 더 짧을 때 범위를 벗어나거나, 길이가 다른 두 컨테이너를 같다고 판단할 수 있습니다.

나머지 비교 연산은 `==`와 `<`에서 유도할 수 있습니다.

```text
!=  → !(left == right)
>   → right < left
<=  → !(right < left)
>=  → !(left < right)
```

각 연산을 독립적으로 작성해 서로 다른 비교 규칙이 생기지 않게 합니다.

## 18. 구현 순서

한꺼번에 모든 컨테이너를 만들지 않습니다.

1. 타입 특성과 컴파일 테스트
2. 반복자 특성과 역방향 반복자
3. 고정 용량 컨테이너로 객체 수명 확인
4. 동적 배열의 생성·소멸·복사
5. `reserve`와 재할당 롤백
6. 삽입·삭제와 무효화 테스트
7. 스택 어댑터
8. 트리 노드 생성·삭제
9. 검색과 반복자
10. `map` 복사와 예외 안전성
11. 표준 컨테이너와 결과 대조

각 단계를 독립적으로 검증한 뒤 다음 단계로 이동합니다.

## 19. 실패를 검증하는 테스트 타입

N번째 복사에서 예외를 던지고 살아 있는 객체 수를 세는 타입을 만듭니다.

검증 항목:

- 재할당 실패 뒤 원본 크기와 값이 그대로입니까?
- 후보 저장 공간이 반환됐습니까?
- 생성된 객체 수와 소멸된 객체 수가 맞습니까?
- 복사 대입 실패 뒤 대상이 유효합니까?
- `map` 노드 값 생성 실패 뒤 트리 크기와 링크가 그대로입니까?
- 예외를 던지지 않는 경로에서도 객체가 이중 소멸되지 않습니까?

정수처럼 복사와 소멸이 실패하지 않는 타입만으로는 이 경로를 검증할 수 없습니다.

## 20. 직접 구현하지 말아야 하는 경우

제품 코드에서 표준 컨테이너를 대체할 명확한 이유가 없다면 직접 구현하지 않습니다. 학습 구현은 다음을 이해하기 위한 수단입니다.

- 객체 수명
- 반복자 요구사항
- 예외 안전성
- 할당자와 미초기화 저장 공간
- 자료구조 불변식

보안, 성능, ABI와 표준 호환성이 필요한 범용 컨테이너에는 검증된 표준 라이브러리를 사용합니다.

---

## STL 내부 구조 점검

- `allocate` 뒤 아직 `T` 객체가 없다는 뜻을 설명할 수 있습니까?
- 부분 생성 실패 시 어느 범위만 `destroy`해야 합니까?
- `vector` 재할당에서 기존 상태를 변경하는 실제 반영 지점은 어디입니까?
- 범위 생성자와 개수 생성자가 왜 모호해질 수 있습니까?
- SFINAE가 함수 본문 인스턴스화 오류에는 적용되지 않는 이유는 무엇입니까?
- 포인터용 `iterator_traits` 특수화가 필요한 이유는 무엇입니까?
- 역방향 반복자의 `base()`가 현재 원소 다음 위치를 가리키는 이유는 무엇입니까?
- `map` 노드를 완성하기 전에 트리에 연결하면 어떤 실패가 생깁니까?
- 공개 반복자 안정성이 내부 노드 주소 설계에 어떤 제약을 줍니까?
