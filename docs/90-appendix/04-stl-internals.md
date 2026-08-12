# STL 컨테이너 내부 구조

## 언제 참고하면 좋은가요?

동적 배열과 트리 기반 컨테이너의 메모리 구성을 살펴보거나, 원시 저장 공간에서 객체 수명과 예외 안전성을 검증할 때 참고하실 수 있습니다. 공개 API를 사용하는 방법은 본문의 [템플릿, 반복자와 STL 알고리즘](../02-cpp98-systems/06-templates-iterators-and-stl.md)에서 먼저 다룹니다.

먼저 다음을 설명할 수 있어야 합니다.

- Rule of Three와 RAII
- 기본, 강한, 무예외 보장
- 반복자와 반열린 범위
- `vector`, `map`의 공개 동작과 무효화 규칙
- 함수·클래스 템플릿

## 살펴볼 내용

- 메모리 확보와 객체 생성을 분리합니다.
- 부분 생성 실패 시 정확히 생성된 원소만 롤백합니다.
- `iterator_traits`와 범주 tag의 역할을 설명합니다.
- SFINAE로 정수 인자와 반복자 인자 오버로드를 구분합니다.
- 동적 배열 재할당에 강한 예외 안전성을 부여합니다.
- 노드 기반 컨테이너가 할당자를 내부 노드 타입으로 바꾸는 이유를 설명합니다.


## mini-vector와 함께 내부 동작 확인

[mini-vector 선택 심화 실습](../../exercises/02-cpp98-systems/generic-programming/mini-vector/README.md)은 할당자, 미초기화 저장 공간, 부분 생성 롤백과 예외를 던지지 않는 포인터 교환을 실제 코드로 확인합니다. 이 실습은 C++98 주 경로를 완료하는 데 필수인 단계가 아니라 저장 공간과 예외 안전성을 더 깊게 확인하려는 학습자를 위한 선택 단계입니다.

```sh
cd exercises/02-cpp98-systems/generic-programming/mini-vector
make observe
```

위 명령은 저장소 루트에서 시작합니다. `make observe`는 좁은 `demo.cpp`로 크기와 용량 변화를 관찰하는 선택 실험입니다. workspace의 `skeleton/`을 구현한 뒤 다시 저장소 루트에서 검사합니다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=generic-programming/mini-vector
```

reference source는 learner 검증을 통과한 뒤에만 비교합니다. canonical `fail-copy` 검사는 repository 검증에서 별도로 실행합니다.

---

## 1. 컨테이너의 핵심 불변식

동적 배열의 대표 불변식:

```text
0 <= size <= capacity
[0, size)에는 살아 있는 T 객체가 있습니다.
[size, capacity)에는 T를 담을 수 있는 미초기화 저장 공간이 있습니다.
data는 capacity가 0일 때만 null일 수 있습니다.
```

트리 기반 map의 대표 불변식:

```text
각 node는 하나의 value를 소유합니다.
key 정렬 규칙이 모든 edge에서 유지됩니다.
부모·자식 링크가 서로 일치합니다.
size는 실제 node 수와 같습니다.
중복 key 정책이 항상 유지됩니다.
```

함수 구현 전에 어떤 구간에 객체가 살아 있는지 적지 않으면 예외 경로에서 소멸 범위를 틀리기 쉽습니다.

## 2. 저장 공간과 객체 생성 분리

`new T[n]`은 메모리 확보와 `n`개 객체의 기본 생성을 함께 수행합니다. `vector`는 용량만큼 메모리를 확보해 두고 크기만큼만 객체를 만들고 싶습니다.

C++98 할당자는 이 책임을 나눕니다.

| 연산 | 역할 |
|---|---|
| `allocate(n)` | `n`개의 `T`를 담을 미초기화 메모리 확보 |
| `construct(p, value)` | `p` 위치에 `T` 객체 생성 |
| `destroy(p)` | `p`의 객체 소멸, 메모리는 유지 |
| `deallocate(p, n)` | 저장 공간 반환 |

```cpp
std::allocator<T> alloc;
T *memory = alloc.allocate(4);

alloc.construct(memory, value);
alloc.destroy(memory);
alloc.deallocate(memory, 4);
```

`allocate` 뒤에는 아직 `T` 객체가 없습니다. 역참조하거나 대입하기 전에 `construct`가 필요합니다.

## 3. 위치 지정 `new`와 명시적 소멸

할당자의 고전적 `construct`는 위치 지정 `new`를 사용합니다.

```cpp
new (address) T(value);
```

이미 확보된 주소에 객체 수명만 시작합니다. 짝은 메모리 반환이 아니라 명시적 소멸자 호출입니다.

```cpp
address->~T();
```

같은 주소를 다시 사용하기 전에 이전 객체의 수명이 끝났는지 확인합니다. 단순 소멸 가능 타입만 생각해 소멸자 호출을 생략하면 사용자 타입에서 자원이 누수됩니다.

## 4. 부분 생성 실패 롤백

여러 객체를 순서대로 생성하다 세 번째 복사에서 예외가 날 수 있습니다.

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

롤백 원칙:

1. 실제 생성에 성공한 개수를 별도로 셉니다.
2. 생성된 객체만 역순으로 destroy합니다.
3. 저장 공간을 deallocate합니다.
4. 원래 예외를 `throw;`로 다시 던집니다.
5. 성공 전에는 기존 컨테이너를 건드리지 않습니다.

## 5. 동적 배열 재할당

재할당의 큰 단계:

```text
새 저장 공간 확보
→ 기존 원소를 새 공간에 복사
→ 전부 성공
→ 기존 원소 소멸
→ 기존 저장 공간 deallocate
→ data/size/capacity 교체
```

복사 중 실패하면 새 공간만 정리하고 원본은 그대로 둡니다. 이것이 강한 예외 안전성입니다.

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

반영 뒤 `size_`가 보존되는지, candidate가 널일 수 있는지 등 세부 불변식을 구현에 맞게 확인합니다.

## 6. 증가 정책과 상각 비용

용량을 매번 1씩 늘리면 `n`개 추가에 총 O(n²) 복사가 발생합니다. 용량을 2배처럼 기하급수적으로 늘리면 전체 복사량이 O(n)에 머물러 추가당 상각 O(1)이 됩니다.

성장 배수는 표준이 강제하지 않습니다. 다음을 균형 있게 봅니다.

- 재할당 횟수
- 사용하지 않는 여유 메모리
- 오버플로와 `max_size`
- 요청 용량보다 작아지지 않는가

## 7. 범위 생성자와 정수 생성자의 모호성

동적 배열에는 다음 두 형태가 공존할 수 있습니다.

```cpp
vector(size_type count, const value_type &value);

template <class InputIterator>
vector(InputIterator first, InputIterator last);
```

`vector<int> values(5, 3)`에서 템플릿은 `InputIterator = int`로 추론될 수 있습니다. 그러면 정수를 반복자처럼 사용하려다 오류가 납니다.

C++98에서는 SFINAE로 반복자 생성자를 정수 타입에서 제거합니다.

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

조건이 false면 `type`이 없어 해당 오버로드가 후보에서 조용히 제거됩니다. 함수 본문 안의 오류는 SFINAE가 아니므로 조건은 함수 시그니처의 치환 영역에 둡니다.

## 8. `integral_constant`와 타입 특성

컴파일 시점 불리언을 값이자 타입으로 표현합니다.

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

기본 `is_integral`은 false이고 정수 타입을 완전 특수화합니다. `const`, `volatile` 한정자를 처리할 부분 특수화도 필요합니다.

```cpp
template <class T>
struct is_integral : false_type {};

template <>
struct is_integral<int> : true_type {};

template <class T>
struct is_integral<const T> : is_integral<T> {};
```

## 9. 태그 디스패치

특성 결과나 반복자 범주를 빈 태그 타입으로 전달해 컴파일 시점 오버로드를 고릅니다.

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

런타임 `if`가 아니라 인자 태그 타입으로 함수가 선택됩니다.

## 10. `iterator_traits`

일반 반복자는 내부 typedef로 능력과 값 타입을 공개합니다.

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

생 포인터에는 멤버 typedef가 없으므로 부분 특수화합니다.

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

이 특수화 덕분에 포인터도 STL 반복자 프로토콜에 참여합니다.

## 11. 사용자 반복자의 최소 계약

반복자가 자신의 범주보다 강한 연산을 광고하면 알고리즘이 잘못된 가정을 합니다.

- 입력: 읽기와 전진
- 전방: 다회 통과
- 양방향: 후진
- 무작위 접근: 차이, 덧셈, 인덱스, 순서 비교

`map`의 트리 반복자를 무작위 접근으로 표시할 수 없습니다. 노드를 한 칸 전진하는 것은 가능하지만 `it + n`을 O(1)에 제공하지 못합니다.

## 12. `reverse_iterator`

역방향 반복자는 기반 클래스 반복자의 바로 앞 원소를 역참조합니다.

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

이 한 칸 차이 덕분에 빈 범위에서도 `rbegin == rend`가 자연스럽게 성립합니다. `base()`는 현재 역참조 원소가 아니라 그 다음 정방향 위치를 반환합니다.

## 13. 노드 할당자와 `rebind`

사용자가 `map<Key, T>`에 주는 할당자는 보통 `pair<const Key, T>`용입니다. 실제 구현은 값을 트리 노드 안에 저장하므로 노드용 할당자가 필요합니다.

```cpp
typedef typename allocator_type::template rebind<Node>::other node_allocator_type;
```

- `typename`: 결과가 타입임을 알림
- `template`: 의존 타입의 멤버 템플릿임을 알림
- `rebind<Node>`: 같은 할당자 종류를 노드용으로 바꿈

노드 생성도 할당과 construction을 분리합니다. 값 생성이 실패하면 노드 memory를 바로 반환합니다.

## 14. 트리 노드 수명과 링크

노드 삽입을 다음 순서로 처리합니다.

```text
위치 탐색
→ 노드 메모리 확보
→ node/value 완전 생성
→ 부모·자식 링크에 공개
→ size 증가
```

완성되지 않은 노드를 트리에 먼저 연결하면 생성 실패 시 트리가 깨집니다. **완성 후 공개** 원칙을 지킵니다.

삭제는 반대입니다.

```text
대상과 교체 node 결정
→ tree 링크 수정
→ 외부에서 더 이상 접근 불가
→ 값 소멸
→ 노드 메모리 해제
→ size 감소
```

두 자식을 가진 노드 삭제, 루트 교체와 후속 노드 이동에서 부모 링크를 모두 확인합니다.

## 15. 반복자 무효화 계약 반영

공개 컨테이너의 무효화 규칙은 내부 구현 제약이 됩니다.

- `vector` 재할당: 모든 위치 참조가 무효화됩니다.
- `vector` 비재할당 삽입: 삽입 위치 이후가 무효화됩니다.
- `map` 삽입: 기존 반복자가 유지됩니다.
- `map` 삭제: 삭제된 노드의 반복자만 무효화됩니다.

`map` 구현이 삽입 때 기존 노드를 메모리에서 이동시키면 표준 반복자 안정성 요구를 깨뜨립니다. 노드 기반 구조가 각 노드 주소를 안정적으로 유지하는 이유입니다.

## 16. `swap`과 할당자

컨테이너 `swap`이 포인터와 크기만 교환할 수 있으려면 할당자 상태와 소유한 저장 공간의 해제 책임이 맞아야 합니다. 상태를 가진 할당자가 서로 다를 때 단순 포인터 교환이 안전한지 C++98 할당자 계약을 확인합니다.

기본 구현에서 상태가 없는 `std::allocator`만 지원한다면 그 제한을 문서화하고 테스트합니다. 할당자 상태를 무시하면서 범용 구현인 것처럼 제공해서는 안 됩니다.

## 17. 관계 연산과 알고리즘 재사용

순차 컨테이너의 `==`는 길이와 모든 원소가 같아야 합니다. `<`는 사전식 순서를 사용합니다.

```cpp
return ft::equal(left.begin(), left.end(), right.begin());
```

길이가 다른 범위를 비교할 때 공통 접두 범위만 비교하지 않도록 `equal` 호출 전 크기를 확인하거나 두 범위 끝을 모두 받는 설계를 사용합니다.

나머지 비교는 `==`와 `<`에서 유도할 수 있습니다.

```cpp
!=  → !(left == right)
>   → right < left
<=  → !(right < left)
>=  → !(left < right)
```

## 18. 구현 순서

한꺼번에 모든 컨테이너를 만들지 않습니다.

1. 타입 특성과 컴파일 테스트
2. 반복자 특성과 역방향 반복자
3. 고정 용량 컨테이너로 객체 수명 확인
4. 동적 배열의 생성·소멸·복사
5. `reserve`와 재할당 롤백
6. 삽입/삭제와 무효화 테스트
7. 스택 어댑터
8. 트리 노드 생성·삭제
9. 검색과 반복자
10. `map` 복사와 예외 안전성
11. 표준 컨테이너와 결과 대조

각 단계는 단독 테스트가 통과한 뒤 다음으로 넘어갑니다.

## 19. 실패를 검증하는 테스트 타입

N번째 복사에서 예외를 던지고 살아 있는 객체 수를 세는 타입을 만듭니다.

검증할 것:

- 재할당 실패 뒤 원본 크기와 값이 그대로입니까?
- 후보 저장 공간이 해제됐습니까?
- 생성된 객체 수와 소멸된 객체 수가 맞습니까?
- 복사 대입 실패 뒤 대상이 유효합니까?
- `map` 노드 값 생성 실패 뒤 트리 크기와 링크가 그대로입니까?

정상 정수 타입만으로는 이 경로를 검증할 수 없습니다.

## 20. 직접 구현하지 말아야 하는 경우

제품 코드에서 표준 컨테이너를 대체할 이유가 없다면 직접 구현하지 않습니다. 학습 구현은 다음을 이해하기 위한 수단입니다.

- 객체 수명
- 반복자 계약
- 예외 안전성
- 할당자와 저장 공간
- 자료구조 불변식

보안, 성능, ABI와 표준 호환성이 필요한 범용 컨테이너는 검증된 표준 라이브러리를 사용합니다.

---

## STL 내부 구조 점검

- `allocate` 뒤 아직 `T` 객체가 없다는 뜻을 설명할 수 있습니까?
- 부분 생성 실패 시 어떤 범위만 destroy해야 합니까?
- `vector` 재할당의 실제 반영 지점은 어디입니까?
- 범위 생성자와 개수 생성자가 왜 모호해질 수 있습니까?
- SFINAE가 함수 본문 오류에는 적용되지 않는 이유는 무엇입니까?
- 포인터용 `iterator_traits` 특수화가 필요한 이유는 무엇입니까?
- 역방향 반복자의 `base()`가 한 칸 앞을 가리키는 이유는 무엇입니까?
- `map` 노드를 완성하기 전에 트리에 연결하면 어떤 실패가 생깁니까?
- 공개 반복자 안정성이 내부 노드 주소 설계에 어떤 제약을 줍니까?
