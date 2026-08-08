# 복잡도 클래스와 다항식 환원

## 학습 목표

- decision problem과 optimization problem을 구분한다.
- P, NP, NP-hard, NP-complete의 관계를 정확히 표현한다.
- certificate와 verifier의 다항 시간을 설명한다.
- 환원의 방향을 이용해 난이도 주장을 검증한다.
- 알려지지 않은 문제를 해결된 사실처럼 표현하지 않는다.

## 선행 개념

점근 시간, 결정 문제의 입력 계약과 한 문제의 해를 다른 문제의 해로 바꾸는 함수 개념을 알고 있어야 한다.

## 핵심 모델

복잡도 클래스는 구현 한 번의 속도가 아니라 입력 크기에 따른 문제 family의 계산 자원에 관한 주장이다.

## 1. decision problem

복잡도 이론은 주로 yes/no 문제를 다룬다.

예:

```text
최단 경로 길이가 K 이하인가?
가치가 V 이상이고 무게가 C 이하인 부분집합이 존재하는가?
graph에 크기 k clique가 존재하는가?
```

optimization 문제는 decision version과 관계를 설명한 뒤 사용한다.

## 2. P

결정적 알고리즘으로 입력 크기의 다항 시간 안에 해결 가능한 decision problem 집합이다.

다항 차수가 크거나 상수가 커도 이론적으로 P일 수 있다. 실용적으로 빠르다는 뜻과 동일하지 않다.

## 3. NP

yes instance에 대해 다항 크기의 certificate가 있고, 이를 다항 시간에 검증할 수 있는 decision problem 집합이다.

예: Hamiltonian cycle의 certificate는 정점 순서이며, 모든 정점을 한 번 포함하고 인접 edge가 존재하는지 다항 시간에 검증할 수 있다.

NP는 “non-polynomial”의 약자가 아니며, no instance도 쉽게 검증된다는 뜻이 아니다.

## 4. NP-hard와 NP-complete

- NP-hard: NP의 모든 문제가 다항 시간에 이 문제로 환원됨
- NP-complete: NP-hard이면서 NP에도 속함

NP-hard 문제는 decision problem이 아니거나 NP 밖일 수도 있다.

## 5. 다항 시간 many-one reduction

`A <=p B`는 A instance를 다항 시간에 B instance로 변환해 답을 보존한다는 뜻이다.

```text
x가 A의 yes instance  iff  f(x)가 B의 yes instance
```

B를 빠르게 풀 수 있다면 변환과 B 풀이로 A도 빠르게 풀 수 있다.

### 난이도를 B에 전달하려면

알려진 어려운 문제 `A`에서 새 문제 `B`로 환원한다.

```text
A <=p B
```

반대로 `B <=p A`만 보이면 B가 A보다 어렵다는 결론은 나오지 않는다.

## 6. NP-complete 증명 구조

1. 문제 `B`가 NP에 속함을 보인다.
   - certificate 정의
   - verifier 정확성
   - certificate 크기와 검증 시간
2. 알려진 NP-complete 문제 `A`를 고른다.
3. `A` instance를 `B` instance로 다항 시간에 변환한다.
4. yes/no 양방향 보존을 증명한다.
5. 변환 크기와 시간의 다항 상한을 적는다.

## 7. 예: Independent Set과 Vertex Cover

정점 집합 `S`가 independent set이면 `V-S`는 vertex cover다. 반대도 성립한다.

```text
G에 크기 k independent set 존재
iff
G에 크기 |V|-k vertex cover 존재
```

이 관계는 같은 graph에서 parameter를 바꾸는 양방향 변환이다. edge 정의와 크기 관계를 정확히 써야 한다.

## 8. pseudo-polynomial

0/1 knapsack의 `O(nC)` DP에서 `C`는 숫자 값이다. 입력에서 `C`를 binary로 표현하면 비트 수는 `log C`이므로 `O(nC)`는 입력 비트 길이에 대한 다항 시간이 아닐 수 있다. 이를 pseudo-polynomial이라고 부른다.

값의 크기와 표현 길이를 구분한다.

## 9. P 대 NP에 관한 표현

현재 알려진 일반 결과의 범위를 넘는 단정을 피한다.

- 어떤 문제에 다항 알고리즘을 찾지 못했다는 사실은 NP-hard 증명이 아니다.
- exponential algorithm이 있다는 사실도 NP-hard 증명이 아니다.
- NP-complete problem에 다항 알고리즘을 제시했다고 주장하려면 증명과 검증이 필요하다.
- P와 NP의 관계에 관한 미해결 상태를 전제로 표현한다.

## 10. 환원 검토표

- source와 target problem이 정확히 무엇인가?
- decision version인가?
- parameter가 어떻게 변하는가?
- 변환이 다항 시간인가?
- yes → yes와 no → no가 모두 보였는가?
- 새 instance의 크기가 다항으로 제한되는가?
- 환원 방향으로 얻을 수 있는 결론이 맞는가?

## 연결 실습

[복잡도 exercise](../../exercises/06-complexity/README.md)에서 Hamiltonian Cycle certificate 검증기와 `A ≤p B` 환원 증명 rubric을 채우고 서로의 방향을 교차 검토한다.

## 완료 기준

- decision problem, certificate 크기, verifier 시간을 입력 비트 길이로 표현한다.
- 알려진 어려운 문제에서 새 문제로 가는 변환과 `yes iff yes`를 증명한다.
- NP-hard와 NP-complete 결론에 필요한 membership 증명을 구분한다.

## 실패 조건

- NP를 “다항 시간에 풀 수 없는 문제”로 정의한다.
- NP-hard와 NP-complete를 같은 뜻으로 사용한다.
- 새 문제에서 알려진 어려운 문제로 환원하고 새 문제의 어려움을 주장한다.
- verifier가 최적해를 다시 계산한다.
- 숫자 값과 입력 비트 길이를 혼동한다.
- 실험적 느림을 복잡도 하한으로 제시한다.

## 연습

[복잡도 exercise](../../exercises/06-complexity/README.md)에서 certificate, verifier와 환원의 양방향을 rubric에 따라 작성한다.
