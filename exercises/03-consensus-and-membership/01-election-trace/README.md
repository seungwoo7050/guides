# Election trace 실습

## 목표

`term`, 영속 vote와 log freshness가 어떤 실행을 허용하고 어떤 실행을 거절하는지 trace로 판정합니다. heartbeat가 늦었다는 사실을 leader의 죽음으로 단정하지 않고, election safety와 liveness를 분리합니다.

## 입력

[`election.json`](election.json)은 5개 노드의 영속 상태와 전달 순서가 다른 세 시나리오를 제공합니다.

- `stale-candidate`: log가 뒤처진 후보가 더 높은 term으로 출마합니다.
- `split-vote-and-retry`: 두 후보가 같은 term에서 표를 나눠 갖고 다음 term에서 다시 시도합니다.
- `vote-before-persist`: vote 응답을 보낸 뒤 `voted_for`를 영속화하기 전에 crash하는 잘못된 구현을 모델링합니다.

## 작업

각 message delivery 뒤에 다음 표를 갱신합니다.

```text
node | current_term | role | voted_for | last_log_index | last_log_term
```

그리고 다음을 작성합니다.

1. 각 `RequestVote`가 승인되거나 거절되어야 하는 이유
2. 한 term에서 선출될 수 있는 leader 수
3. 후보가 필요한 quorum과 실제로 받은 영속 vote
4. election safety가 처음 깨지는 event
5. 안전성을 복구하기 위해 응답 전에 영속화해야 하는 상태
6. 메시지를 모두 전달한 뒤에도 leader가 없을 수 있다면, 그것이 safety 위반인지 liveness 지연인지

## 보존할 불변식

- 한 노드는 같은 term에서 최대 한 후보에게만 vote합니다.
- vote를 승인한 사실은 응답보다 먼저 crash-recovery storage에 반영됩니다.
- voter는 자신의 log보다 덜 최신인 후보에게 vote하지 않습니다.
- 한 term의 두 후보가 각각 quorum을 얻을 수 없습니다.
- 더 높은 term을 관찰한 노드는 그 term으로 이동하고 leader/candidate 상태를 내려놓습니다.

## 대표 오답

- candidate term만 높으면 log 상태와 관계없이 vote합니다.
- `last_log_index`만 비교하고 `last_log_term`을 먼저 비교하지 않습니다.
- vote 응답 뒤에 `voted_for`를 저장합니다.
- timeout이 발생하면 기존 leader가 확실히 죽었다고 기록합니다.
- 동일 term의 중복 `RequestVote`에 매번 다른 결과를 냅니다.

## 완료 조건

- 세 시나리오의 최종 node 상태와 leader 여부를 표로 제출합니다.
- 안전성 위반 trace를 가능한 짧게 줄입니다.
- vote의 영속화 지점과 crash 뒤 복원 규칙을 문장으로 고정합니다.
- election timeout의 역할을 안전성 증명이 아니라 진행을 위한 시간 가정으로 설명합니다.
