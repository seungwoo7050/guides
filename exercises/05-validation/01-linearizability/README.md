# Linearizability history 실습

## 목표

client가 관찰한 invocation·completion history에서 real-time order를 보존하는 legal sequential execution이 존재하는지 판정합니다. 최종 값만 같은 실행과 linearizable 실행을 구분합니다.

## 입력

[`histories.json`](histories.json)은 단일 read/write register의 completed·overlapping·pending operation을 포함합니다. 시간 값은 wall clock의 정확성을 뜻하지 않고 한 수집기에서 기록한 history 순서를 표현합니다.

Sequential specification:

```text
initial value = 0
write(v) -> OK, 이후 register value는 v
read() -> 현재 register value
```

## 작업

각 history에 대해 다음을 제출합니다.

- linearizable / not linearizable / 기록만으로 판정 불가
- 가능하다면 operation의 legal sequential order
- 불가능하다면 모순을 만드는 최소 operation 집합
- pending operation을 drop하거나 completion을 보완한 방법
- real-time precedence edge 목록

[`examples/linearizable-register/checker.py`](../../../examples/linearizable-register/checker.py)를 사용할 수 있지만, 먼저 손으로 판정합니다. checker의 결과가 곧 증명이라는 뜻은 아니며 입력 parsing, pending policy와 sequential spec이 맞는지 검토해야 합니다.

## 보존할 규칙

- operation A의 completion이 B의 invocation보다 먼저라면 A는 B보다 앞에 linearize됩니다.
- 겹치는 operation의 상대 순서는 결과가 spec을 만족하는 범위에서 선택할 수 있습니다.
- pending operation은 삭제하거나, 관찰 결과와 모순되지 않는 completion을 붙여 포함할 수 있습니다.
- per-key history를 따로 검사한 결과만으로 multi-key transaction의 atomicity를 주장하지 않습니다.

## 대표 오답

- completion timestamp 순서로만 operation을 정렬합니다.
- 마지막 값이 맞으면 모든 중간 read를 무시합니다.
- client process의 program order를 잊습니다.
- pending write를 무조건 실패로 취급합니다.
- 검색이 오래 걸린다는 이유로 실패한 첫 순서를 반례로 확정합니다.

## 완료 조건

- 모든 history에 판정과 witness 또는 최소 반례를 제출합니다.
- 한 history의 timestamp를 최소 한 곳 바꿔 판정이 뒤집히는 사례를 만듭니다.
- checker가 탐색한 상태 수와 pruning rule을 기록합니다.
- multi-key history에 같은 checker를 그대로 적용할 수 없는 이유를 설명합니다.
