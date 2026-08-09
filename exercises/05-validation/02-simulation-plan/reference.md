# 결정적 simulation 계획 검토 예시

이 문서는 `plan-template.json`을 대체하는 제출물이 아니라 각 TODO가 어느 정도 구체적이어야 하는지 보여 주는 review 기준입니다.

## 최소로 충분한 계획 예

```text
protocol: 3-node Raft election과 한 entry 복제
node state: role, term, voted_for, log, commit_index, last_applied
network state: delivery ID가 있는 in-flight message multiset과 directed partition
storage state: node별 durable term, vote, log
client state: invocation, completion, unknown request
clock: virtual monotonic time, 동일 deadline은 node ID 순서
```

event는 `deliver(message_id)`, `fire_timer(node_id)`, `client_invoke`, `drop`, `duplicate`, `partition`, `heal`, `crash`, `restart`처럼 enabled 조건과 state transition을 가져야 합니다. 문자열 설명만 나열해서는 replay할 수 없습니다.

정상 schedule은 leader election과 한 command의 commit·apply·reply를 포함합니다. fault schedule은 최소 split vote, vote persist 뒤 crash, leader crash, one-way partition, response loss/retry, slow follower 중 다섯 가지를 고르고 explicit event ID를 저장합니다.

각 event 뒤 election safety, vote safety, log matching, commit monotonicity와 apply bound를 검사합니다. liveness는 “connected majority가 유지되고, enabled delivery와 timer가 fair하게 선택되며, durable save가 완료된다”는 조건과 최대 step bound를 함께 기록합니다.

실패 artifact에는 source/config identity, seed, explicit schedule, first violated invariant와 state before/after가 필요합니다. shrink는 event chunk를 제거한 뒤 같은 invariant가 같은 state relation으로 깨지는지 다시 확인합니다.

## 사람 검토 질문

- seed뿐 아니라 explicit schedule을 남겼습니까?
- 정상 1개와 fault 5개 이상이 실제 enabled event로 재생됩니까?
- safety invariant와 bounded liveness expectation을 분리했습니까?
- simulation에서 빠진 filesystem, serialization, thread와 실제 network 위험을 별도 integration 계획에 연결했습니까?

## 이 결과가 증명하지 않는 것

계획 문서 자체는 simulator나 protocol correctness를 증명하지 않습니다. 실제 구현, 정상·known-wrong schedule 실행과 artifact 검토가 뒤따라야 합니다.
