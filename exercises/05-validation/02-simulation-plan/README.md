# 결정적 simulation 계획 실습

## 목표

분산 protocol을 테스트하기 전에 state, event, fault, invariant와 탐색 전략을 명시한 simulation 계획을 작성합니다. 무작위 sleep과 프로세스 kill을 반복하는 대신 실패를 재생·축소할 수 있는 입력으로 바꿉니다.

## 입력

[`plan-template.json`](plan-template.json)은 계획의 필수 필드를 제공합니다. 값의 `TODO`를 자신의 protocol에 맞게 채웁니다.

## 작업

최소 하나의 protocol을 선택합니다.

- leader election
- replicated register
- Raft log replication
- shard migration
- 2PC coordinator recovery

다음 내용을 정의합니다.

1. node·network·timer·storage·client state
2. 결정적으로 적용 가능한 event 종류
3. drop·delay·duplicate·reorder·crash·restart·disk fault
4. 매 event 뒤 검사할 safety invariant
5. 진행을 기대하는 fairness와 time bound
6. schedule 생성·seed 저장·재생 방식
7. 실패 trace 축소 전략
8. 실제 runtime과 simulation 사이 model gap

## 대표 오답

- thread와 wall-clock sleep을 그대로 simulation 안에 사용합니다.
- fault를 문자열 로그로만 남기고 재생 가능한 event ID를 저장하지 않습니다.
- 최종 상태만 검사하고 중간 event의 invariant 위반을 놓칩니다.
- seed만 저장하고 code/config/version을 기록하지 않습니다.
- liveness 실패에 필요한 fairness 가정을 적지 않습니다.
- simulation이 통과했다는 이유로 storage·network·runtime의 실제 동작까지 증명했다고 주장합니다.

## 완료 조건

- `plan-template.json`의 모든 `TODO`를 구체적인 값으로 바꿉니다.
- 정상 schedule 1개와 fault schedule 5개 이상을 작성합니다.
- 최소 한 fault schedule을 event 수가 더 작은 동등 반례로 축소합니다.
- simulation에서 다루지 않는 실제 runtime 위험을 별도 통합 실험으로 연결합니다.

계획을 작성한 뒤 [`reference.md`](reference.md)의 review 예시와 [`expected.json`](expected.json)의 계약을 비교합니다.
