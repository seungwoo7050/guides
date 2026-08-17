# 알고리즘·ranges·templates·concepts

## 목표

컨테이너 순회 코드를 반복해서 작성하는 대신 연산의 의도, 복잡도, 타입 요구사항을 명시합니다. 표준 알고리즘과 ranges를 사용하되 뷰의 수명과 반복자 무효화 규칙을 놓치지 않습니다. 템플릿은 아무 타입이나 받는 코드가 아니라, 필요한 연산을 제공하는 타입에 재사용할 수 있는 코드로 이해합니다.

## 시작하기 전에

[오류·optional·variant·expected](05-errors-optional-variant-and-expected.md)를 완료하고 값, 비소유 뷰, 오류 타입의 차이를 설명할 수 있어야 합니다.

## 1. 컨테이너는 접근 방식에 맞게 선택합니다

| 요구사항 | 우선 검토할 컨테이너 |
|---|---|
| 연속 저장, 순차 순회, 끝 삽입 | `std::vector` |
| 양 끝 삽입·삭제 | `std::deque` |
| 키 정렬과 범위 조회 | `std::map` |
| 평균 O(1) 키 조회 | `std::unordered_map` |
| 정렬된 고유 값 | `std::set` |
| FIFO | `std::queue` 어댑터 |
| LIFO | `std::stack` 어댑터 |

`std::list`는 중간 삽입이 O(1)이라는 이유만으로 선택하지 않습니다. 삽입 위치를 찾는 비용, 캐시 지역성, 실제 순회 패턴을 함께 고려해야 합니다.

## 2. 복잡도는 실제 데이터 규모와 함께 판단합니다

O(1)과 O(log n)의 차이가 항상 중요한 것은 아닙니다. 다음 조건을 함께 기록합니다.

- 최대 항목 수
- 읽기와 쓰기의 비율
- 정렬된 순서가 필요한가
- 전체 순회를 자주 수행하는가
- 키 해시 비용과 충돌 가능성은 어느 정도인가
- 반복자·참조의 안정성이 필요한가

항목 수가 적은 설정 목록이라면 `vector`를 선형 탐색하는 방식이 가장 단순할 수 있습니다. 성능 문제는 실제 작업 부하로 측정한 뒤 자료구조를 변경합니다.

## 3. 알고리즘 이름으로 연산 의도를 표현합니다

```cpp
const auto found = std::ranges::find_if(jobs, [](const Job& job) {
    return job.status == JobStatus::failed;
});
```

직접 작성한 반복문이 잘못된 것은 아닙니다. 다만 `find`, `count`, `any_of`, `transform`, `sort`, `partition`처럼 의도가 드러나는 알고리즘을 사용하면 반복 조건과 끝 처리를 매번 다시 구현할 필요가 줄어듭니다.

알고리즘을 호출하기 전에 다음 항목을 확인합니다.

- 원본 범위를 변경하는가
- 반환된 반복자는 어느 범위에 속하는가
- 정렬 전제와 비교 함수가 strict weak ordering을 만족하는가
- 이후 컨테이너 변경으로 반복자가 무효화되는가

## 4. projection

ranges 알고리즘은 객체에서 비교에 사용할 값을 projection으로 지정할 수 있습니다.

```cpp
std::ranges::sort(jobs, std::less{}, &Job::id);
```

단순 필드를 기준으로 정렬할 때는 복잡한 람다보다 의도가 분명합니다. 우선순위가 같은 항목의 순서를 결정해야 한다면 비교 함수를 명시합니다.

```cpp
std::ranges::sort(jobs, [](const Job& left, const Job& right) {
    if (left.duration == right.duration)
        return left.id < right.id;
    return left.duration < right.duration;
});
```

동등한 항목의 기존 순서가 결과의 일부라면 안정 정렬을 사용하고, 항상 같은 결과 순서가 필요하다면 고유한 보조 키까지 비교합니다.

## 5. range 뷰의 지연 평가와 소유권

```cpp
auto failed = jobs | std::views::filter([](const Job& job) {
    return job.status == JobStatus::failed;
});
```

이 예제의 `failed`는 새 `vector`가 아니라 lvalue인 `jobs`를 참조하며 필요할 때 원소를 필터링하는 뷰입니다. 중간 컨테이너를 만들지 않고 여러 연산을 조합할 수 있습니다.

모든 뷰가 항상 비소유인 것은 아닙니다. 일부 뷰는 내부 상태나 기반 범위를 소유할 수 있으므로 구체적인 뷰 타입의 수명 규칙을 확인해야 합니다. 위와 같이 lvalue 컨테이너를 기반으로 만든 필터 뷰에서는 다음 사항에 주의합니다.

- 원본이 먼저 파괴되면 뷰를 사용할 수 없습니다.
- 원본 변경으로 뷰가 사용하는 반복자가 무효화될 수 있습니다.
- predicate에 부수 효과가 있으면 호출 횟수와 순서에 따라 결과가 달라질 수 있습니다.
- 뷰를 장기간 저장하거나 API 밖으로 반환하면 수명 조건이 복잡해집니다.

결과를 독립적으로 보관해야 한다면 소유 컨테이너로 구체화합니다.

```cpp
std::vector<Job> result;
for (const Job& job : failed)
    result.push_back(job);
```

복사 없이 비소유 참조만 모으려면 `std::reference_wrapper<const Job>`를 저장할 수 있지만, 참조 대상의 수명이 결과보다 길어야 한다는 조건을 문서화합니다.

## 6. 반복자 무효화

컨테이너를 변경한 뒤 기존 반복자, 참조, 포인터가 계속 유효하다고 가정하지 않습니다.

대표적인 규칙은 다음과 같습니다.

- `vector` 재할당: 모든 반복자·참조·포인터가 무효화됩니다.
- `vector` 원소 삭제: 삭제 위치부터 끝까지의 반복자와 참조가 무효화됩니다.
- `map` 삽입: 일반적으로 기존 원소의 반복자와 참조는 유지됩니다.
- `map` 원소 삭제: 삭제한 원소를 가리키던 반복자와 참조만 무효화됩니다.
- unordered 컨테이너 rehash: 반복자는 무효화되지만 원소에 대한 참조와 포인터는 일반적으로 유지됩니다.

정확한 규칙은 사용하는 컨테이너와 연산의 표준 계약을 확인합니다. 반복자를 보관한 채 컨테이너를 변경하는 코드는 특히 주의해야 합니다.

## 7. erase-remove와 `std::erase_if`

Modern C++에서는 컨테이너에 맞는 표준 도우미를 사용할 수 있습니다.

```cpp
std::erase_if(jobs, [](const Job& job) {
    return job.status == JobStatus::cancelled;
});
```

C++98 트랙에서는 erase-remove 관용구를 직접 사용합니다. 문법 차이보다 제거 알고리즘이 새 논리적 끝을 반환하고, 컨테이너의 `erase`가 실제 원소 수를 줄인다는 모델을 이해하는 것이 중요합니다.

## 8. 템플릿의 요구사항

```cpp
template <typename Range>
std::string summarize(const Range& jobs);
```

이 선언만으로는 `Range`가 어떤 연산을 제공해야 하는지 알기 어렵습니다. 템플릿 본문을 인스턴스화한 뒤에야 긴 컴파일 오류가 발생할 수 있습니다.

concept으로 실제 요구사항에 이름을 붙입니다.

```cpp
template <typename Range>
concept JobRange =
    std::ranges::input_range<const Range> &&
    std::convertible_to<
        std::ranges::range_reference_t<const Range>,
        const Job&>;

template <JobRange Range>
std::string summarize(const Range& jobs);
```

이 concept은 `Job`, `const Job`, `reference_wrapper<const Job>`처럼 원소를 `const Job&`로 읽을 수 있는 입력 범위를 허용합니다. concept은 런타임 검사가 아니라 템플릿이 후보가 될 조건을 제한하고 오류 위치를 더 명확하게 만드는 컴파일 시점 제약입니다.

## 9. concept을 필요 이상으로 구체화하지 않습니다

구현에 실제로 필요한 연산만 요구합니다.

불필요하게 좁은 요구사항:

```text
vector<Job>만 허용
```

실제 요구사항:

```text
Job을 읽을 수 있는 입력 범위
```

반대로 구현이 임의 접근이나 상수 시간 `size()`를 필요로 하는데 단순한 입력 범위만 요구하면 concept과 구현의 전제가 어긋납니다.

## 10. 함수 템플릿과 완벽 전달

모든 매개변수를 전달 참조(forwarding reference)로 받을 필요는 없습니다.

```cpp
template <typename Callable>
void run(Callable&& callable)
{
    std::invoke(std::forward<Callable>(callable));
}
```

이 패턴은 호출 가능 객체의 값 범주와 cv/ref 속성을 다음 호출까지 보존해야 할 때 유용합니다. 일반적인 값 타입 인터페이스는 값이나 `const&`가 더 읽기 쉬울 수 있습니다. 완벽 전달은 오버로드 선택과 수명 추론을 복잡하게 만들므로 실제 전달 요구가 있을 때만 사용합니다.

## 11. 템플릿 정의 위치

컴파일러가 필요한 타입으로 템플릿을 인스턴스화하려면 일반적으로 사용 지점에서 정의를 볼 수 있어야 합니다. 따라서 구현을 헤더에 두거나 지원할 타입을 정해 명시적 인스턴스화 경계를 설계합니다.

```cpp
// formatter.hpp
template <typename T>
std::string format_value(const T& value)
{
    // ...
}
```

일반 함수처럼 선언만 헤더에 두고 정의를 `.cpp` 파일에 숨기면, 별도로 명시적 인스턴스화하지 않은 호출 타입에 대한 정의를 링크 단계에서 찾지 못할 수 있습니다.

## 12. 컴파일 시점 검증

```cpp
static_assert(!std::is_copy_constructible_v<UniqueFile>);
static_assert(std::is_nothrow_move_constructible_v<UniqueFile>);
```

타입의 사용 계약은 런타임 테스트만으로 모두 검증할 수 없습니다. 잘못된 사용이 **컴파일되지 않아야 한다는 조건**도 검사 대상입니다.

컴파일 실패 테스트는 컴파일러별로 달라질 수 있는 전체 진단 문구보다 성공·실패 여부와 필요한 경우 안정적인 핵심 패턴만 검사합니다.

## 13. 성능 추정과 측정을 구분합니다

ranges나 템플릿을 사용한다고 코드가 자동으로 빠르거나 느려지는 것은 아닙니다. 다음을 구분합니다.

- 복잡도와 할당 횟수에 근거한 설계 단계의 추정
- 프로파일러와 벤치마크로 얻은 실제 관찰
- Debug와 Release 빌드의 차이
- 작은 예제 입력과 실제 작업 부하의 차이

성능 최적화를 이유로 소유권과 수명 규칙을 불분명하게 만들지 않습니다.

## 연결 실습

[조회 파이프라인](../../exercises/01-modern-cpp/03-query-pipeline/README.md)을 구현합니다.

실습의 데이터 흐름은 다음과 같습니다.

```text
span<const Job> 원본
→ 지연 평가 필터 뷰
→ 비소유 참조 목록으로 구체화
→ 결정적인 순서로 정렬
→ concept으로 제한한 summarize
```

원본 `vector`를 직접 정렬하지 않으며, 비소유 결과가 원본보다 오래 살아서는 안 되는 이유를 설명합니다.

## 실패 실험

- 지역 `vector`를 기반으로 만든 뷰를 반환한 뒤 원본을 파괴합니다.
- `vector` 반복자를 저장한 뒤 `push_back`으로 재할당을 일으킵니다.
- 비교 함수에서 `<=`를 사용해 strict weak ordering을 깨뜨립니다.
- 실행 시간이 같은 항목의 보조 정렬 키를 제거합니다.
- 템플릿의 요구사항을 concept 없이 구현 내부 오류에만 맡깁니다.

## 완료 기준

- 접근 방식과 복잡도에 따라 컨테이너를 선택합니다.
- 알고리즘이 원본을 변경하는지와 반환 반복자의 소속 범위를 설명합니다.
- range 뷰의 지연 평가와 구체적인 소유권·수명 규칙을 설명합니다.
- 컨테이너 변경 연산별 반복자 무효화 규칙을 확인합니다.
- concept으로 템플릿이 실제로 요구하는 연산을 표현합니다.

## 다음 문서

[동시성·시간·파일 시스템](07-concurrency-time-and-filesystem.md)에서 단일 스레드에서 성립하던 값과 컨테이너 규칙을 여러 실행 흐름과 외부 파일 상태로 확장합니다.
