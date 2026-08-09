# Atomic commit 실습

## 목표

여러 shard에 걸친 transaction에서 `PREPARED`, durable decision과 recovery의 관계를 추적합니다. 2PC가 atomicity를 제공하는 조건과 coordinator 장애에서 진행이 멈출 수 있는 이유를 구분합니다.

## 입력

[`transactions.json`](transactions.json)은 세 시나리오를 제공합니다.

- `commit-decision-survives`: 모든 participant가 prepare한 뒤 coordinator가 COMMIT 결정을 durable하게 저장하고 crash합니다.
- `prepared-without-decision`: participant는 prepare했지만 durable global decision이 없습니다.
- `participant-votes-no`: 한 participant가 prepare를 거절합니다.

## 작업

각 event 뒤 다음 표를 갱신합니다.

```text
coordinator durable state
participant A durable state
participant B durable state
locks/intents held
client-visible result
allowed recovery action
```

다음 질문에 답합니다.

1. participant는 언제 local change를 되돌릴 수 없게 됩니까?
2. COMMIT/ABORT decision은 어떤 저장소에 먼저 durable해야 합니까?
3. participant가 `PREPARED`인데 coordinator와 decision service에 접근할 수 없을 때 안전한 행동은 무엇입니까?
4. client timeout은 transaction decision과 어떤 관계입니까?
5. participant group 자체가 consensus로 복제돼 있어도 global atomic commit이 자동 해결되지 않는 이유는 무엇입니까?

## 보존할 불변식

- 같은 transaction에서 한 participant가 COMMIT하고 다른 participant가 ABORT하지 않습니다.
- COMMIT decision은 모든 participant가 YES를 durable하게 기록한 경우에만 만들어집니다.
- participant는 PREPARED 응답 전에 redo/intent와 transaction identity를 durable하게 저장합니다.
- coordinator는 participant에게 decision을 보내기 전에 global decision을 durable하게 저장합니다.
- recovery는 추측이나 local timeout만으로 PREPARED transaction을 임의로 바꾸지 않습니다.

## 대표 오답

- client timeout을 global ABORT로 간주합니다.
- participant가 YES를 보낸 뒤 lock과 intent를 삭제합니다.
- coordinator가 COMMIT 메시지를 먼저 보내고 decision log를 나중에 기록합니다.
- 한 participant가 ABORT를 관찰했다는 이유로 이미 durable COMMIT인 transaction을 되돌립니다.
- 2PC의 blocking을 availability를 높이는 retry로 숨깁니다.

## 완료 조건

- 세 시나리오의 durable state와 client-visible state를 분리한 표를 제출합니다.
- crash event 위치를 바꾼 추가 trace 두 개를 만듭니다.
- PREPARED transaction의 recovery source와 operator escalation 조건을 정의합니다.
- 2PC, Saga와 consensus를 동일한 문제의 대체 구현처럼 표현하지 않고 차이를 설명합니다.

직접 추적한 뒤 [`reference.md`](reference.md)의 해설과 [`expected.json`](expected.json)의 관측 결과를 비교합니다.
