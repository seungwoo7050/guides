# 실습: failure detector의 의심과 증거

## 목표

Heartbeat timeout을 crash 사실이 아니라 suspicion transition으로 다룹니다. 정상 전달, timeout 경계와 false suspicion 뒤의 위험한 irreversible action을 같은 state machine으로 추적합니다.

## 입력

[observations.json](observations.json)은 timeout이 5 virtual tick인 detector의 세 실행을 제공합니다.

- stable-heartbeats: timeout 전에 heartbeat가 반복 도착합니다.
- delayed-heartbeat: 정확히 경계에서 suspect한 뒤 같은 incarnation heartbeat가 늦게 도착합니다.
- timeout-as-proof: timeout만으로 member를 영구 제거한 뒤 현재 incarnation heartbeat가 도착합니다.

## 작업

각 event 뒤 다음 상태를 기록합니다.

    monitor status
    last valid heartbeat step
    observed incarnation
    suspicion reason
    irreversible action

다음 질문에 답합니다.

1. detector가 ALIVE, SUSPECT 중 어느 상태를 출력합니까?
2. timeout이 알려 주는 관찰과 알려 주지 않는 실제 상태는 무엇입니까?
3. delayed heartbeat가 suspicion을 해제할 수 있는 조건은 무엇입니까?
4. membership 제거나 durable data 삭제에 어떤 quorum/configuration evidence가 추가로 필요합니까?
5. liveness를 주장하려면 delivery, timer와 process scheduling에 어떤 fairness가 필요합니까?

## 정상·경계·실패

- 정상: stable-heartbeats에서 suspicion이 생기지 않습니다.
- 경계: delayed-heartbeat에서 step 5에 suspect하지만 step 6의 valid heartbeat로 ALIVE로 돌아옵니다.
- 실패: timeout-as-proof에서 timeout-only irreversible_remove가 첫 계약 위반입니다.

## 제출과 사람 검토

analysis.md에 event별 detector state, 가능한 실제 상태, safety/liveness 구분과 필요한 추가 evidence를 기록합니다. False suspicion 자체는 허용될 수 있지만 그것만으로 irreversible state loss를 정당화하면 안 됩니다.

[해설](reference.md)과 [기계 판정값](expected.json)을 비교한 뒤 저장소 루트에서 실행합니다.

    python3 scripts/check_exercises.py exercises/01-model-and-time/03-failure-detector

## 한계

이 실습은 perfect failure detector를 구현하거나 crash 원인을 진단하지 않습니다. Virtual step은 실제 RTT, clock drift, GC pause와 scheduler delay의 분포를 대신하지 않습니다.

## 완료 조건

- timeout evidence와 crash fact를 분리합니다.
- false suspicion 중에도 protocol safety가 별도 quorum evidence로 유지됨을 설명합니다.
- irreversible action에 필요한 configuration transition을 제시합니다.
- liveness를 stable delivery와 fairness 조건부로 작성합니다.
