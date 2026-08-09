# Atomic commit 기대 결과

## Durable COMMIT 뒤 coordinator crash

tx-101은 두 participant의 YES가 durable한 뒤 e8에서 COMMIT decision이 durable해집니다. e11의 coordinator crash는 결정을 되돌리지 않습니다. shard-B는 recovery query로 같은 durable decision을 읽고 COMMIT해야 하며, client 응답이 없더라도 transaction 결과는 COMMIT입니다.

## PREPARED이나 decision 없음

tx-102의 participant는 intent와 YES를 durable하게 기록했지만 global decision은 없습니다. client timeout이나 participant local timeout은 ABORT evidence가 아닙니다. decision source에 접근할 수 없는 동안 lock/intent를 유지하고 `BLOCKED` 또는 client 관점의 `UNKNOWN`으로 남아야 합니다.

## Participant가 NO

tx-103에서 shard-B의 NO 때문에 COMMIT은 허용되지 않습니다. coordinator가 durable ABORT를 기록한 뒤 participant에 전달하고 shard-A가 prepared intent를 abort합니다. 어느 participant도 COMMIT할 수 없습니다.

## 사람 검토 질문

- local PREPARED와 global decision을 다른 durable record로 구분했습니까?
- response timeout을 definite abort로 바꾸지 않았습니까?
- participant group 내부 consensus와 global atomic commit decision을 구분했습니까?
- atomicity 보장과 lock 때문에 멈추는 liveness 문제를 분리했습니까?

## 이 결과가 증명하지 않는 것

이 fixture는 2PC atomicity만 다루며 transaction isolation, deadlock, heuristic decision, presumed-abort 최적화와 coordinator decision store 자체의 구현을 검증하지 않습니다.
