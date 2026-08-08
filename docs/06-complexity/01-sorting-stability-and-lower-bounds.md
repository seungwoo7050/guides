# 정렬, 안정성과 비교 하한

## 학습 목표

- 정렬 계약을 key·동점·안정성·제자리 여부로 정의한다.
- comparison sort와 key 구조를 사용하는 정렬을 구분한다.
- merge sort, quicksort, heapsort의 보장을 비교한다.
- 결정 트리로 비교 정렬의 `Ω(n log n)` 하한을 설명한다.

## 선행 개념

[점근 분석](../01-foundations/02-asymptotic-analysis.md), 비교 기반 정렬과 정확성 불변식을 알고 있어야 한다.

## 핵심 모델

“정렬한다”는 말에는 다음 계약이 빠져 있다.

```text
오름차순 또는 내림차순
비교할 key
같은 key의 상대 순서
입력 변경 여부
추가 공간
최악·기대 시간 보장
```

## 1. 안정성

안정 정렬은 같은 key를 가진 원소의 원래 상대 순서를 보존한다.

예:

```text
먼저 이름으로 안정 정렬
그 뒤 부서로 안정 정렬
```

최종 결과에서 부서가 주 key이고 같은 부서 안의 이름 순서가 유지된다. 안정성이 필요 없으면 그 비용을 감수할 이유가 없다.

## 2. 대표 비교 정렬

| 알고리즘 | 시간 | 추가 공간 | 안정성 | 주의점 |
|---|---|---|---|---|
| merge sort | 최악 `O(n log n)` | 일반적으로 `O(n)` | 가능 | 결합 buffer |
| quicksort | 기대 `O(n log n)`, 최악 `O(n²)` | recursion | 일반적으로 불안정 | pivot·partition |
| heapsort | 최악 `O(n log n)` | `O(1)` 가능 | 불안정 | locality와 상수 |
| insertion sort | 최악 `O(n²)` | `O(1)` | 안정 가능 | 작은·거의 정렬 입력 |

실제 표준 정렬은 hybrid일 수 있으므로 API의 보장을 확인한다.

## 3. merge sort 불변식

두 정렬된 run을 병합한다.

```text
출력 prefix는 두 입력에서 소비한 원소의 정렬된 합이다.
각 pointer는 아직 소비하지 않은 첫 원소를 가리킨다.
```

같은 key에서 왼쪽을 먼저 선택하면 안정성을 유지한다.

## 4. quicksort의 partition

partition 계약을 하나로 고정한다.

예:

```text
partition 후 pivot 왼쪽은 pivot 이하,
오른쪽은 pivot 이상,
pivot은 최종 위치에 있다.
```

Hoare와 Lomuto partition의 반환값 의미를 섞지 않는다. 같은 값이 많을 때 3-way partition이 유리할 수 있다.

## 5. 비교 정렬 하한

서로 다른 `n`개 원소에는 `n!`개 순열이 있다. 비교 기반 알고리즘은 각 비교가 두 갈래인 decision tree로 표현된다. 모든 순열을 구분하려면 leaf가 최소 `n!`개 필요하다.

높이 `h`인 이진 tree의 leaf는 최대 `2^h`이므로:

```text
2^h >= n!
h >= log2(n!) = Ω(n log n)
```

따라서 일반 comparison sort의 최악 비교 횟수는 `Ω(n log n)`이다.

이 하한은 key 범위를 이용하는 counting/radix sort에는 그대로 적용되지 않는다.

## 6. counting과 radix sort

### counting sort

key가 작은 정수 범위 `0..K`에 있을 때 `O(n+K)` 시간과 `O(K)` 공간을 사용할 수 있다. `K`가 매우 크면 부적절하다.

### radix sort

고정 길이 digit를 여러 pass로 정렬한다. 각 pass의 정렬이 안정적이어야 낮은 digit의 순서가 보존된다. 시간은 digit 수와 base에 의존한다.

“선형 정렬”이라는 표현에는 key 표현과 범위 전제가 포함되어야 한다.

## 7. 선택 문제

전체 정렬이 필요하지 않고 k번째 원소만 필요하면 selection algorithm이나 heap을 고려한다. 불필요한 전체 순서를 만들지 않는다.

## 8. 검사

정렬 결과는 다음을 확인한다.

- 원본과 같은 multiset인가?
- 정렬 순서를 만족하는가?
- 안정성이 계약이면 동점 상대 순서가 유지되는가?
- comparator가 일관적인가?
- 빈 입력·중복·역순·이미 정렬된 입력은 어떤가?

## 연결 실습

[복잡도 exercise](../../exercises/06-complexity/README.md)에서 comparison tree 하한을 작성하고, 같은 key의 원래 위치를 넣은 record로 안정성을 판정한다.

## 완료 기준

- 정렬 결과가 순서뿐 아니라 원본과 같은 multiset인지 검사한다.
- `n!`개 순열과 decision tree 높이에서 `Ω(n log n)` 하한을 유도한다.
- counting/radix sort가 비교 하한을 피하는 key 범위·표현 전제를 명시한다.

## 실패 조건

- 안정성이 필요한데 key만 비교해 상대 순서를 잃는다.
- quicksort 기대 시간을 최악 보장으로 쓴다.
- counting sort에서 key 범위 비용을 누락한다.
- comparison 하한을 모든 정렬에 적용한다.
- 정렬 결과의 순서만 보고 원소 유실·중복을 검사하지 않는다.

## 연습

[복잡도 exercise](../../exercises/06-complexity/README.md)에서 비교 정렬 하한을 설명하고, 안정성 결함을 드러내는 record 입력을 만든다.
