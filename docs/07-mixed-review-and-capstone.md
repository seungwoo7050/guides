# 혼합 문제와 검증 capstone

## 학습 목표

- 유형 표시가 없는 문제에서 계약·비용·상태를 먼저 추출한다.
- 여러 알고리즘 후보를 전조건과 실패 반례로 비교한다.
- 구현·기준 계산·결함 fixture를 하나의 검증 체계로 연결한다.
- 틀린 문제를 원인별로 기록하고 재발 방지 test로 남긴다.

## 선행 개념

Part 1–6의 계약·복잡도·불변식·자료구조·설계 기법을 한 문제에서 함께 사용할 수 있어야 한다.

## 핵심 모델

혼합 문제에서는 알고리즘 이름보다 다음 의사결정 순서를 사용한다.

```text
계약
→ 입력 크기와 목표 비용
→ 필요한 질의·갱신
→ 단순 기준 풀이
→ 후보 상태와 불변식
→ 전조건 반례
→ 구현과 동치 검사
```

## 1. 문제 선택 질문

### 입력 구조

- 순서가 의미 있는가?
- 구간 질의인가?
- 관계가 graph인가?
- 값 범위가 작은가?
- 같은 상태가 반복되는가?

### 연산 구조

- membership·frequency인가?
- 최솟값을 반복해서 꺼내는가?
- 여러 query 전처리가 가능한가?
- edge 추가가 component를 합치는가?
- 과거 상태를 버릴 단조성이 있는가?

### 최적성 구조

- 국소 선택을 교환할 수 있는가?
- 선택하지 않음/선택함으로 상태가 나뉘는가?
- 최적 경로가 하위 최적 경로로 구성되는가?
- cut 또는 relaxation 성질이 있는가?

## 2. 후보 비교표

구현 전에 적는다.

| 후보 | 전조건 | 시간 | 공간 | 실패 반례 |
|---|---|---:|---:|---|
| sliding window | 상태가 단조 | `O(n)` | `O(1)` | 음수 값 |
| prefix+hash | prefix 차이로 표현 | 기대 `O(n)` | `O(n)` | hash 최악 |
| DP | 상태 수 제한 | 상태×전이 | 상태 수 | 상태 누락 |

가장 빠른 후보가 아니라 계약을 증명할 수 있는 후보를 선택한다.

## 3. 구현 전 proof sketch

다섯 문장 안에 다음을 쓴다.

1. 상태가 무엇을 뜻하는가?
2. 한 단계가 상태를 어떻게 바꾸는가?
3. 어떤 불변식이 유지되는가?
4. 왜 후보를 빠뜨리거나 중복 세지 않는가?
5. 왜 종료하고 목표 비용 안에 드는가?

설명이 길어지는 것은 상태가 불명확하다는 신호일 수 있다.

## 4. 검증 capstone

[검증 capstone](../exercises/07-verified-algorithms-capstone/README.md)은 같은 API에 네 종류의 구현을 연결한다.

```text
skeleton  : 공개 함수와 TODO
workspace : 학습자 구현
reference : 계약을 만족하는 기준 구현
broken    : 알려진 결함을 가진 품질 fixture
```

검사는 다음 방식으로 독립성을 높인다.

- prefix sum ↔ 직접 합산
- lower bound ↔ 표준 bisect
- shortest path ↔ Floyd–Warshall
- knapsack·interval ↔ 부분집합 열거
- red-black invariant ↔ 독립 검증기
- MST ↔ spanning tree 조합 열거
- max flow ↔ cut 열거
- LCS ↔ 모든 짧은 subsequence

## 5. stage 진행

```sh
scripts/new-workspace.sh exercises/07-verified-algorithms-capstone
cd exercises/07-verified-algorithms-capstone

python3 check.py --impl workspace --stage data-structures --expect pass
python3 check.py --impl workspace --stage design-techniques --expect pass
python3 check.py --impl workspace --stage graphs --expect pass
python3 check.py --impl workspace --stage strings --expect pass
python3 check.py --impl workspace --stage all --expect pass
```

앞 stage 검사가 통과해도 뒤 함수를 미리 구현할 필요는 없다.

## 6. 실패 기록

```text
문제:
실패한 최소 입력:
틀린 출력 또는 예외:
깨진 계약:
원인 분류:
- 모델링
- 전조건
- 불변식
- 경계
- 비용
- 구현
수정:
추가한 regression test:
```

“실수했다”로 끝내지 않는다. 같은 종류의 실수를 막을 수 있는 관찰 가능한 규칙을 남긴다.

## 7. 시간 제한 아래의 판단

- 초반: 계약과 단순 풀이를 확정
- 중반: 목표 비용과 후보 상태를 선택
- 구현 전: 최소 경계 사례를 적음
- 막힘: 15분 안에 새로운 가설이나 실험이 없으면 기준 풀이·작은 입력으로 돌아감
- 제출 전: overflow, 빈 입력, 동점, 초기화, 복사 비용 확인

속도를 위해 분석을 생략하는 것이 아니라, 분석 단위를 짧게 고정한다.

## 연결 실습

[검증 capstone](../exercises/07-verified-algorithms-capstone/README.md)에서 안전한 workspace를 만든 뒤 stage별로 구현한다. reference·skeleton·네 결함 fixture·비종료 fixture가 각각 기대한 결과를 내는지도 확인한다.

## 완료 기준

- 모든 stage reference 검사와 완성한 workspace 전체 검사가 통과한다.
- skeleton은 의도한 `NotImplementedError`, 결함 fixture는 해당 계약 위반으로 거부된다.
- 선택한 두 알고리즘의 계약·정확성·비용과 최소 실패 입력을 코드 없이 설명한다.

## 실패 조건

- 문제 제목이나 익숙한 단어만 보고 유형을 결정한다.
- 기준 구현 없이 샘플만 비교한다.
- 무작위 실패 입력을 보존하지 않는다.
- reference가 후보와 같은 핵심 로직을 공유한다.
- 모든 실패를 구현 오타로 분류한다.
- stage 검사가 뒤 단계 구현까지 요구한다.

## 연습

[Exercise 로드맵](../exercises/README.md)의 1–6단계를 완료한 뒤 capstone workspace에서 전체 stage를 통과시킨다. 최종적으로 결함 fixture 네 개가 각각 어떤 계약을 깨뜨리는지 최소 반례와 함께 설명한다.
