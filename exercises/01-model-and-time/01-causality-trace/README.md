# 실습: causality trace

## 목표

세 process의 event에서 happened-before, concurrent pair, Lamport clock, vector clock과 consistent cut를 직접 계산합니다.

## 입력

[`trace.json`](trace.json)은 각 process의 local event와 세 message를 제공합니다. 배열 순서는 수집기가 관찰한 순서일 뿐 전역 physical order라고 가정하지 않습니다. 같은 process 안의 배열 위치와 message send→receive만 causal edge를 만듭니다.

## 작업

### 1. Direct edge

다음을 구분해 작성합니다.

- 같은 process의 바로 이전 event
- message send→receive
- transitive edge는 별도 표시

### 2. Concurrent pair

최소 다섯 event pair를 골라 어느 방향의 happened-before도 없음을 설명합니다. 수집 배열에서 앞에 나온다는 이유만으로 causal order를 만들지 않습니다.

### 3. Lamport clock

모든 process의 counter를 0에서 시작하고 다음 규칙으로 timestamp를 부여합니다.

```text
local/send: counter += 1
receive(ts): counter = max(counter, ts) + 1
```

message에 포함되는 send timestamp도 기록합니다.

### 4. Vector clock

vector 순서는 `[A, B, C]`로 고정합니다. 모든 event의 vector를 계산하고 concurrent pair가 incomparable한지 확인합니다.

### 5. Consistent cut

`candidate_cuts`의 각 cut가 consistent한지 판정합니다. 일관되지 않다면 최소 event를 추가하거나 제거해 consistent하게 바꿉니다.

## 제출

```text
analysis.md
- direct·transitive edge
- concurrent pair
- Lamport·vector clock 표
- cut 판정과 수정
```

선택 구현:

```text
clock.py
- trace.json을 읽어 timestamp 계산
- causal edge에서 Lamport order 확인
- vector incomparable pair 출력
```

## 대표 오답

- JSON 배열 순서를 전역 order로 사용합니다.
- `L(a) < L(b)`이면 `a -> b`라고 역추론합니다.
- vector component 합이나 최대값으로 concurrency를 판정합니다.
- receive를 cut에 넣으면서 send를 제외합니다.

## 완료 조건

- 모든 direct causal edge가 맞습니다.
- Lamport clock은 causal edge의 증가를 보존합니다.
- 선택한 concurrent pair는 vector가 서로 지배하지 않습니다.
- consistent cut는 포함 event의 causal predecessor를 모두 포함합니다.
