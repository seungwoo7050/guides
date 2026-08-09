# Election trace 기대 결과

이 문서는 구현 모양이 아니라 각 delivery 뒤 허용되는 vote와 durable state를 비교하는 기준입니다. 먼저 직접 추적한 뒤 확인합니다.

## Stale candidate

후보 C는 term 5에서 자신에게 vote합니다. A와 E의 마지막 log term은 4이므로 마지막 term 3인 C를 거절합니다. D는 index가 더 길지만 마지막 term이 2이므로 Raft의 `(lastLogTerm, lastLogIndex)` 사전식 비교에서 C가 더 최신이고 C에게 vote할 수 있습니다. C가 얻는 표는 C와 D의 2표뿐이므로 leader는 없습니다.

## Split vote와 재시도

term 9에서 A는 A·B, D는 D·C의 표만 얻습니다. E로 향한 두 요청은 모두 drop되므로 어느 후보도 quorum 3을 얻지 못합니다. 이는 safety 위반이 아니라 진행 지연입니다.

term 10에서 D는 먼저 자신에게 vote하고 B와 C의 응답을 받는 시점에 quorum을 얻습니다. E의 표는 결과를 바꾸지 않습니다. 더 높은 term을 관찰한 B·C·E는 term 10으로 이동해야 합니다.

## Persist 전 응답하는 잘못된 구현

unsafe variant에서 A는 B에게 term 7 vote 응답을 보낸 뒤 `voted_for=B`를 저장하기 전에 crash합니다. restart 뒤 C에게 다시 vote하는 e7이 one-vote-per-term invariant의 첫 위반입니다. 이후 B는 A·B·D, C는 A·C·E의 표를 각각 모을 수 있어 같은 term에 두 leader가 생깁니다.

수정 계약은 `current_term`과 `voted_for`를 원자적으로 durable하게 저장한 뒤에만 granted response를 공개하는 것입니다.

## 사람 검토 질문

- timeout이 leader의 죽음을 증명하지 않고 새 election을 시작할 근거일 뿐임을 설명했습니까?
- candidate freshness 비교에서 term을 index보다 먼저 비교했습니까?
- leader가 없는 유한 trace와 fairness 아래의 liveness 주장을 구분했습니까?
- e7을 제거했을 때 double vote 반례가 사라지는지 확인했습니까?

## 이 결과가 증명하지 않는 것

세 유한 fixture는 모든 message interleaving에서의 Raft election safety나 무조건적인 termination을 증명하지 않습니다. 구현에서는 duplicate·delayed response, one-way partition과 반복 crash도 별도 schedule로 검사해야 합니다.
