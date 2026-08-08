# C++20 구현 프로필

## 목적

이 문서는 C++ 문법 과정이 아니다. 현대 C++의 전체 객체·수명·빌드 모델은 `guide-cpp`가 소유한다. 여기서는 알고리즘 계약을 C++20으로 옮길 때 자주 발생하는 비용·경계 문제만 다룬다.

## 빌드 기준

```sh
c++ -std=c++20 -Wall -Wextra -Wpedantic -Wconversion -g main.cpp -o program
```

성능 측정 전에는 먼저 경고와 sanitizer 검사를 통과한다.

```sh
c++ -std=c++20 -fsanitize=address,undefined -fno-omit-frame-pointer -g main.cpp -o program
```

## 자료구조 대응

| 알고리즘 개념 | C++20 도구 | 주의점 |
|---|---|---|
| 동적 배열 | `std::vector` | 재할당과 iterator/reference 무효화 |
| queue/deque | `std::queue`, `std::deque` | adapter의 제공 연산 확인 |
| min-heap | `std::priority_queue` + comparator | 기본은 max-heap |
| ordered set/map | `std::set`, `std::map` | `O(log n)` |
| hash set/map | `std::unordered_set/map` | 평균 비용과 reserve |
| binary search | `std::lower_bound` | 반열린 iterator range |
| optional 거리 | `std::optional<long long>` | sentinel overflow 회피 |

## 정수 범위

대입 대상이 넓어도 연산이 먼저 좁은 타입에서 수행될 수 있다.

```cpp
long long product = 1LL * left * right;
```

입력 상한으로 합·곱·거리의 최대값을 계산하고 타입을 정한다. signed overflow는 정의되지 않은 동작이므로 wraparound를 기대하지 않는다.

## index와 크기

`size()`는 unsigned 계열이다. 음수 sentinel과 섞지 않는다. index가 없는 결과는 `std::optional<std::size_t>` 또는 명시적 계약을 사용한다.

중간 위치:

```cpp
const auto mid = lo + (hi - lo) / 2;
```

## comparator

strict weak ordering을 지켜야 한다.

```cpp
return std::tie(a.primary, a.secondary) < std::tie(b.primary, b.secondary);
```

`<=`를 comparator로 사용하지 않는다. 비교 중 바뀌는 외부 상태를 참조하지 않는다.

## recursion과 stack

graph DFS나 편향 tree가 `O(n)` 깊이가 될 수 있으면 명시적 stack을 고려한다. tail call optimization을 보장으로 가정하지 않는다.

## 복사 비용

- 큰 container는 `const&`로 관찰
- 소유권을 넘길 의도면 value와 move를 명시
- range slicing은 iterator pair 또는 `std::span` 검토
- loop 안에서 container를 반환·복사하는 비용 확인

copy elision이 있어도 알고리즘 분석에서 의도하지 않은 `O(n)` 복사를 숨기지 않는다.

## 결정적인 출력

`unordered_*` iteration 순서에 기대지 않는다. 결과 순서가 계약이면 정렬하거나 ordered structure를 사용한다.

## 입출력 분리

```cpp
Result solve(const Input& input);
```

파싱·출력과 domain algorithm을 분리하면 기준 계산과 property test에 연결하기 쉽다.

## Python capstone과의 관계

공식 executable checker는 Python으로 제공되지만 API와 검증 방법은 언어 중립이다. C++ 구현은 같은 고정 fixture를 읽는 별도 adapter를 만들거나, 작은 입력을 JSON/text로 교환해 Python oracle과 비교할 수 있다.
