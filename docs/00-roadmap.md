# 학습 로드맵

## 대상 독자

이 가이드는 하나 이상의 프로그래밍 언어로 함수·조건문·반복문·배열 또는 리스트를 작성해 본 사람을 대상으로 한다. 특정 언어의 문법 입문서는 아니다. 저장소가 제공하는 실행형 capstone과 검증 도구에는 Python 3.12 이상이 필요하다. C++20으로 개념을 옮기려면 [C++20 프로필](90-implementation-profiles/cpp20.md)의 지원 경계를 먼저 확인한다.

## 선행지식과 지원 환경

함수·조건문·반복문·배열을 작성하고 작은 입력의 실행 상태를 손으로 추적할 수 있어야 한다. 자동 검증은 Python 3.12 이상, Git, POSIX shell과 `make`가 있는 macOS 또는 Linux를 지원한다. core 문서의 계약과 증명은 언어 중립이지만, 저장소가 제공하는 skeleton·reference·oracle은 Python용이다. C++20 구현은 선택 확장이며 동일한 자동 완료 판정을 제공하지 않는다.

## 종료 능력

가이드를 마친 독자는 다음을 할 수 있어야 한다.

- 문제 서술을 입력·출력·실패·동점 규칙을 포함한 계약으로 바꾼다.
- 가장 단순한 기준 풀이를 만들고 입력 크기에서 허용 가능한 비용을 계산한다.
- 반복 불변식, 귀납법, 교환 논리, 절단 성질 또는 환원으로 정확성을 설명한다.
- 자료구조와 알고리즘을 이름이 아니라 필요한 연산과 불변식으로 선택한다.
- 작은 독립 기준 계산과 고정 시드 입력으로 후보 구현을 검증한다.
- 틀린 구현에서 최소 반례를 보존하고 오류가 처음 발생한 상태를 찾는다.
- 계산 불가능성이나 NP-완전성에 관한 주장을 환원의 방향과 전제까지 포함해 정확히 표현한다.

## 이 가이드가 다루지 않는 것

- Python이나 C++ 전체 문법
- 특정 온라인 저지의 입출력 요령 모음
- 라이브러리 API 암기
- 경쟁 프로그래밍용 트릭의 무작위 나열
- 계산복잡도 이론 전체, 근사 알고리즘 전체, 확률 알고리즘 전체
- 실제 하드웨어 성능 최적화와 병렬 알고리즘의 심화 과정

필요한 내용을 의도적으로 제한하는 이유는 첫 알고리즘을 구현하기 전에 모든 수학과 자료구조를 끝내려는 선행학습 함정을 피하기 위해서다.

## 학습 순서

Part 1–7과 대응 exercise는 **필수 경로**다. 뒤의 선택 확장은 필수 경로의 완료 기준을 대신하지 않는다.

### Part 1. 분석과 정확성의 언어

1. [문제 계약과 반례](01-foundations/01-problem-contracts-and-counterexamples.md)
2. [점근 분석](01-foundations/02-asymptotic-analysis.md)
3. [점화식과 분할 정복](01-foundations/03-recurrences-and-divide-and-conquer.md)
4. [정확성, 불변식과 종료](01-foundations/04-correctness-and-invariants.md)

이 Part는 뒤의 모든 문서에서 사용하는 공통 언어다. 처음 읽을 때 완전한 증명을 매번 쓰지 못해도 좋지만, 입력 크기·상태·불변식·종료 조건을 적는 습관은 생략하지 않는다.

### Part 2. 자료구조

1. [선형 구조, 구간과 해시](02-data-structures/01-linear-structures-ranges-and-hashing.md)
2. [순서, 탐색, 힙과 우선순위](02-data-structures/02-order-search-heaps-and-priority.md)
3. [트리와 균형 탐색 트리](02-data-structures/03-trees-and-balanced-search-trees.md)
4. [분리 집합과 상각 분석](02-data-structures/04-disjoint-sets-and-amortized-analysis.md)

자료구조는 저장 모양보다 지원해야 할 연산에서 선택한다. 각 연산의 최악·기대·상각 비용을 구분한다.

### Part 3. 설계 기법

1. [완전탐색과 백트래킹](03-design-techniques/01-brute-force-and-backtracking.md)
2. [그리디 설계](03-design-techniques/02-greedy-methods.md)
3. [동적 계획법](03-design-techniques/03-dynamic-programming.md)

이 Part에서는 “이 유형이면 이 알고리즘”이라는 분류보다, 어떤 정보를 버려도 되는지와 왜 국소 선택이 전체 최적해를 보존하는지를 묻는다.

### Part 4. 그래프

1. [그래프 표현, 순회와 위상 순서](04-graph-algorithms/01-traversal-and-topological-order.md)
2. [최소 스패닝 트리](04-graph-algorithms/02-minimum-spanning-trees.md)
3. [최단 경로](04-graph-algorithms/03-shortest-paths.md)
4. [네트워크 유량과 이분 매칭](04-graph-algorithms/04-network-flow-and-matching.md)

### Part 5. 문자열

1. [문자열 매칭과 전처리](05-string-algorithms/01-string-matching-and-preprocessing.md)

### Part 6. 정렬과 계산복잡도

1. [정렬, 안정성과 비교 하한](06-complexity/01-sorting-stability-and-lower-bounds.md)
2. [복잡도 클래스와 다항식 환원](06-complexity/02-complexity-classes-and-reductions.md)

### Part 7. 통합

[혼합 문제와 검증 capstone](07-mixed-review-and-capstone.md)에서 유형 표시가 없는 문제를 선택하고, 같은 API를 skeleton·reference·결함 fixture로 비교한다.

### 선택 확장

핵심 Part를 마친 뒤 [확장 문제와 검증 설계](80-extended-practice.md)에서 구간·tree·graph·문자열·flow의 고급 문제를 골라 같은 검증 루프를 반복한다. 확장 과정은 필수가 아니며 핵심 완료 기준을 대신하지 않는다.

이 문서와 구현 프로필은 **선택 경로**를 명시하며, 독자가 이미 알고 있는 Part를 건너뛰더라도 연결 exercise의 증거는 직접 확인해야 한다.

## Exercise 대응

| 학습 구간 | Exercise | 자동 검증 |
|---|---|---|
| Part 1 | [분석과 반례](../exercises/01-analysis-and-counterexamples/README.md) | 서술형 rubric |
| Part 2 | [자료구조](../exercises/02-data-structures/README.md) | prefix sum, lower bound, 레드블랙트리 |
| Part 3 | [설계 기법](../exercises/03-design-techniques/README.md) | 배낭, 구간 선택, LCS |
| Part 4 | [그래프](../exercises/04-graphs/README.md) | BFS, Dijkstra, Kruskal, Bellman–Ford, 최대 유량 |
| Part 5 | [문자열](../exercises/05-strings/README.md) | KMP와 표준 검색 동치 검사 |
| Part 6 | [복잡도](../exercises/06-complexity/README.md) | 서술형 rubric |
| Part 7 | [검증 capstone](../exercises/07-verified-algorithms-capstone/README.md) | 전체 reference·skeleton·결함 fixture |

## 권장 반복 방식

각 문서는 다음 순서로 사용한다.

1. 작은 입력을 손으로 추적한다.
2. 계약과 실패 조건을 한 문장으로 적는다.
3. 단순한 기준 풀이를 작성한다.
4. 목표 비용과 필요한 상태를 정한다.
5. 의사코드와 불변식을 작성한다.
6. 선택한 언어로 구현한다.
7. 기준 풀이와 동치 검사를 수행한다.
8. 실패 입력을 최소화하고 수정 뒤 다시 실행한다.

완성 예제를 읽는 것만으로 완료하지 않는다. 구현을 닫고 같은 계약을 다시 작성할 수 있어야 한다.

## 완료 기준

- Part 1–7의 문서와 대응 exercise에서 요구하는 관찰 가능한 증거를 모두 남긴다.
- verified algorithms capstone의 reference 20개 검사를 통과시키고 skeleton과 known-bad fixture가 지정된 이유로 실패함을 설명한다.
- 새로운 실패 입력을 최소화하고 계약·복잡도·정확성 근거와 수정 뒤 회귀 결과를 함께 기록한다.

## 자동 검증의 한계

자동 검사는 고정된 API, 대표 경계값, timeout과 알려진 오답을 거부한다. 모든 입력에 대한 수학적 정확성, 선택한 구현의 실제 하드웨어 성능, 서술형 증명의 타당성을 대신하지 않는다. 통과 결과는 증명의 보조 증거이며 학습자가 불변식과 반례를 직접 설명해야 한다.
