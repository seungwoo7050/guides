# 알고리즘·ranges·templates·concepts

## 목표

container 순회 코드를 복사하는 대신 의도, 복잡도와 타입 요구조건을 명시합니다. 표준 알고리즘과 ranges를 사용하되 view 수명과 iterator 무효화를 놓치지 않습니다. template은 “아무 타입이나 받는 코드”가 아니라 필요한 연산을 가진 타입에 재사용되는 계약으로 이해합니다.

## 시작하기 전에

[오류·optional·variant·expected](05-errors-optional-variant-and-expected.md)를 완료하고 값, 비소유 view와 실패 타입을 설명할 수 있어야 합니다.

## 1. container는 접근 패턴으로 선택합니다

| 요구 | 우선 검토 |
|---|---|
| 연속 저장, 순차 순회, 끝 삽입 | `std::vector` |
| 양 끝 삽입·삭제 | `std::deque` |
| 정렬된 key와 범위 조회 | `std::map` |
| 평균 O(1) key 조회 | `std::unordered_map` |
| 유일한 정렬 값 | `std::set` |
| FIFO | `std::queue` adapter |
| LIFO | `std::stack` adapter |

`std::list`는 중간 삽입이 O(1)이라는 이유만으로 선택하지 않습니다. 삽입 위치 iterator를 찾는 비용, cache locality와 실제 순회 패턴을 함께 봅니다.

## 2. 복잡도는 업무 크기와 함께 봅니다

O(1)과 O(log n) 차이가 항상 중요한 것은 아닙니다. 다음을 함께 기록합니다.

- 최대 항목 수
- 읽기와 쓰기 비율
- 순서가 필요한가
- 반복 순회가 많은가
- key hash 비용과 충돌
- iterator·reference 안정성이 필요한가

작은 설정 목록에는 vector 선형 탐색이 가장 단순할 수 있습니다. 성능 문제는 workload로 측정한 뒤 구조를 바꿉니다.

## 3. 알고리즘은 의도를 이름으로 표현합니다

```cpp
const auto found = std::ranges::find_if(jobs, [](const Job& job) {
    return job.status == JobStatus::failed;
});
```

수동 loop가 나쁜 것은 아닙니다. 그러나 `find`, `count`, `any_of`, `transform`, `sort`와 `partition`으로 의도가 직접 드러나면 경계 조건을 다시 구현할 필요가 줄어듭니다.

algorithm 호출 전 다음을 확인합니다.

- 원본을 변경하는가
- 결과 iterator가 어느 range에 속하는가
- 정렬 전제와 comparator가 strict weak ordering을 만족하는가
- iterator가 이후 변경으로 무효화되는가

## 4. projections

ranges 알고리즘은 객체의 특정 필드를 projection으로 선택할 수 있습니다.

```cpp
std::ranges::sort(jobs, std::less{}, &Job::id);
```

복잡한 lambda보다 의도가 선명할 수 있습니다. tie-breaker가 필요한 경우 comparator를 명시합니다.

```cpp
std::ranges::sort(jobs, [](const Job& left, const Job& right) {
    if (left.duration == right.duration)
        return left.id < right.id;
    return left.duration < right.duration;
});
```

동등한 항목의 순서가 결과 계약에 중요하다면 안정 정렬 또는 명시적인 보조 key를 사용합니다.

## 5. ranges view는 lazy하고 비소유입니다

```cpp
auto failed = jobs | std::views::filter([](const Job& job) {
    return job.status == JobStatus::failed;
});
```

`failed`는 새 vector가 아니라 원본을 순회하는 view입니다. 장점은 중간 container를 만들지 않고 연산을 조합할 수 있다는 것입니다.

주의할 점:

- 원본이 먼저 파괴되면 view가 dangling 상태가 됩니다.
- 원본 변경으로 iterator가 무효화될 수 있습니다.
- predicate가 호출될 때마다 결과가 달라지는 부수 효과를 가져서는 안 됩니다.
- view를 API 밖에 오래 저장하면 수명 계약이 복잡해집니다.

필요하면 결과를 소유 container로 materialize합니다.

```cpp
std::vector<Job> result;
for (const Job& job : failed)
    result.push_back(job);
```

비소유 참조만 필요하면 `std::reference_wrapper<const Job>`를 담을 수 있지만 원본 수명 전제를 문서화합니다.

## 6. iterator 무효화

container 변경 뒤 기존 iterator·reference·pointer가 계속 유효하다고 가정하지 않습니다.

대표적인 예:

- vector 재할당: 모든 iterator·reference·pointer 무효화
- vector erase: 지운 위치 이후 iterator 무효화
- map insert: 일반적으로 기존 iterator 유지
- map erase: 지운 원소의 iterator만 무효화
- unordered container rehash: iterator 무효화 가능

정확한 규칙은 사용하는 연산의 계약을 확인합니다. iterator를 저장한 채 container를 변경하는 코드는 특히 주의합니다.

## 7. erase-remove와 `std::erase_if`

Modern C++에서는 container에 맞는 표준 helper를 사용할 수 있습니다.

```cpp
std::erase_if(jobs, [](const Job& job) {
    return job.status == JobStatus::cancelled;
});
```

C++98 트랙에서는 erase-remove idiom을 직접 사용합니다. 두 문법의 차이보다 “알고리즘이 논리적 끝을 반환하고 container가 실제 크기를 변경한다”는 모델을 이해합니다.

## 8. template의 요구조건

```cpp
template <typename Range>
std::string summarize(const Range& jobs);
```

이 선언만 보면 어떤 Range가 필요한지 알기 어렵습니다. implementation을 읽을 때까지 오류가 길게 이어질 수 있습니다.

concept으로 필요한 연산을 이름 붙입니다.

```cpp
template <typename Range>
concept JobRange =
    std::ranges::input_range<Range> &&
    std::same_as<
        std::remove_cvref_t<std::ranges::range_reference_t<Range>>,
        std::reference_wrapper<const Job>>;

template <JobRange Range>
std::string summarize(const Range& jobs);
```

concept은 runtime 검사가 아닙니다. template overload가 참여할 조건과 오류 위치를 좁힙니다.

## 9. concept을 너무 구체적으로 만들지 않습니다

정말 필요한 연산만 요구합니다.

나쁜 요구:

```text
vector<Job>만 허용
```

실제 필요:

```text
Job을 읽는 input range
```

반대로 implementation이 random access와 size O(1)을 필요로 하는데 단순 input range만 요구하면 함수 내부에서 잘못된 전제를 갖게 됩니다.

## 10. 함수 template과 forwarding

모든 parameter를 forwarding reference로 만들 필요는 없습니다.

```cpp
template <typename Callable>
void run(Callable&& callable)
{
    std::invoke(std::forward<Callable>(callable));
}
```

이 패턴은 callable의 값 범주를 보존해야 할 때 유용합니다. 하지만 일반 값 타입 API는 값 또는 `const&`가 더 읽기 쉽습니다. perfect forwarding은 overload 집합과 수명 문제를 복잡하게 만들 수 있으므로 실제 전달 요구가 있을 때 사용합니다.

## 11. template 정의 위치

compiler가 필요한 타입으로 template을 instantiate하려면 정의가 보통 사용 지점에 보여야 합니다. 따라서 header에 구현을 두거나 명시적 instantiation 경계를 설계합니다.

```cpp
// formatter.hpp
template <typename T>
std::string format_value(const T& value)
{
    // ...
}
```

일반 함수처럼 선언만 header에 두고 정의를 `.cpp`에 숨기면 caller 타입에 대한 정의를 찾지 못할 수 있습니다.

## 12. compile-time 검증

```cpp
static_assert(!std::is_copy_constructible_v<UniqueFile>);
static_assert(std::is_nothrow_move_constructible_v<UniqueFile>);
```

타입 계약은 runtime test만으로 충분하지 않을 수 있습니다. 잘못된 호출이 **컴파일되지 않아야 하는 것**도 검증 대상입니다.

compile-fail test는 compiler 진단 문구 전체에 의존하기보다 컴파일 성공 여부와 핵심 원인을 검사합니다.

## 13. 성능을 추정과 측정으로 분리합니다

ranges와 template을 사용한다고 자동으로 빠르거나 느린 것은 아닙니다. 다음을 구분합니다.

- 복잡도와 allocation 수에 근거한 설계 추정
- profiler·benchmark로 얻은 실제 관찰
- Debug와 Release 차이
- 작은 입력과 실제 workload 차이

성능 최적화 때문에 소유권과 수명 계약을 흐리지 않습니다.

## 연결 실습

[조회 파이프라인](../../exercises/01-modern-cpp/03-query-pipeline/README.md)을 구현합니다.

실습은 다음 경계를 갖습니다.

```text
span<const Job> 원본
→ lazy filter view
→ reference_wrapper 목록으로 materialize
→ 결정적 sort
→ concept으로 제한된 summarize
```

원본 vector를 정렬하지 않고, 결과가 원본보다 오래 살 수 없다는 비소유 계약을 설명합니다.

## 실패 실험

- view를 반환하고 원본 local vector를 파괴합니다.
- vector iterator를 저장한 뒤 push_back으로 재할당을 일으킵니다.
- comparator에서 `<=`를 사용해 strict ordering을 깨뜨립니다.
- 실행 시간이 같은 항목의 tie-breaker를 제거합니다.
- template 요구조건을 구현 내부의 긴 오류에만 맡깁니다.

## 완료 기준

- 접근 패턴과 복잡도로 container를 선택합니다.
- 알고리즘의 변경 여부와 iterator 결과를 설명합니다.
- range view의 lazy·비소유 특성을 설명합니다.
- iterator 무효화 규칙을 변경 연산과 함께 확인합니다.
- concept으로 실제 필요한 template 요구조건을 표현합니다.

## 다음 문서

[동시성·시간·filesystem](07-concurrency-time-and-filesystem.md)에서 하나의 thread 안에서 유효했던 값과 container 계약을 여러 실행 흐름과 외부 파일 상태로 확장합니다.
