# Atomic commit, consensus와 분산 transaction

## 목표

여러 shard 또는 resource manager가 하나의 transaction을 모두 commit하거나 모두 abort해야 할 때 atomic commit 문제를 모델링합니다. Two-Phase Commit(2PC)이 해결하는 것과 consensus가 해결하는 것을 구분하고, coordinator crash와 participant recovery를 명시합니다.

## 업무 Saga와 다른 문제입니다

`distributed-services`의 Saga는 여러 서비스의 이미 공개된 업무 효과를 보상·재조정하는 방식입니다. 이 문서는 하나의 transaction protocol 안에서 participant의 commit/abort를 원자적으로 결정하는 문제를 다룹니다.

```text
Atomic commit
- participant의 prepared state와 하나의 commit/abort decision
- transaction 내부의 all-or-nothing

Saga
- 독립 서비스의 여러 local transaction
- compensating action과 업무 수렴
```

두 방식을 섞어 사용할 수 있지만 보장과 실패 상태를 분리합니다.

## Two-Phase Commit

### Phase 1: Prepare

coordinator가 participant에 prepare를 요청합니다.

participant가 `YES`를 반환하려면 다음을 durable하게 보장해야 합니다.

- transaction의 write와 lock 또는 validation state가 복구 가능합니다.
- 이후 coordinator decision에 따라 commit할 수 있습니다.
- 자신의 판단으로 abort하지 않고 decision을 기다립니다.

```text
ACTIVE
→ PREPARED(txn_id, write_set, lock_state)
```

### Phase 2: Decision

모든 participant가 YES이면 coordinator가 COMMIT, 하나라도 NO면 ABORT를 durable log에 기록합니다. 그 뒤 participant에 decision을 전송합니다.

participant는 decision을 durable하게 적용하고 resource를 정리합니다.

## Blocking

participant가 PREPARED 상태에서 coordinator decision을 알 수 없고 coordinator가 unavailable하면 안전하게 독자 결정하기 어려울 수 있습니다.

```text
participant P는 YES를 durable하게 기록했습니다.
coordinator가 decision 기록 전후 어느 지점에서 crash했는지 모릅니다.
P는 lock을 유지하고 decision을 기다립니다.
```

2PC는 failure-free execution에서 atomic decision을 조정하지만, coordinator availability와 recovery를 추가하지 않으면 blocking이 생깁니다.

## Coordinator recovery

coordinator durable state:

```text
TransactionRecord {
  txn_id
  participants
  phase
  votes
  decision
  decision_epoch
}
```

restart 규칙:

- decision이 durable하면 같은 decision을 재전송합니다.
- decision이 없고 prepare가 완료되지 않았다면 protocol 규칙에 따라 abort할 수 있습니다.
- 모든 YES 뒤 commit decision을 보냈다면 commit record가 먼저 durable해야 합니다.
- duplicate vote·decision은 idempotent합니다.

coordinator state를 consensus group에 저장하면 coordinator process failure에도 decision service를 사용할 수 있습니다. 그러나 각 participant의 local prepare·commit durability와 transaction concurrency control은 여전히 필요합니다.

## Consensus와의 차이

Consensus는 여러 participant가 하나의 proposal 또는 log order에 합의하는 문제입니다. Atomic commit은 각 participant의 local ability to commit과 하나의 all-or-nothing decision을 결합합니다.

차이:

- participant 하나가 `NO`이면 transaction은 commit할 수 없습니다.
- consensus validity는 특정 proposal 선택을 허용하지만 2PC vote의 의미와 다릅니다.
- consensus로 coordinator decision을 복제해도 participant prepare 실패를 없애지 않습니다.
- participant group 자체가 replicated이면 transaction은 여러 consensus group을 가로지를 수 있습니다.

## Per-shard consensus와 transaction

각 shard가 Raft group이라고 가정합니다.

```text
Shard A: prepare(txn) command를 consensus로 commit
Shard B: prepare(txn) command를 consensus로 commit
Coordinator group: final decision을 consensus로 commit
Shard A/B: decision을 apply
```

이 구조에서 failure point는 여러 겹입니다.

- shard leader 변경
- prepare entry commit 뒤 response 유실
- coordinator decision commit 뒤 notification 유실
- participant snapshot과 prepared transaction recovery
- transaction timeout과 orphan cleanup

모든 message에 `txn_id`와 participant/configuration epoch를 포함합니다.

## Isolation과 atomicity

2PC는 all-or-nothing decision을 다루지만 concurrent transaction의 serializability를 자동 보장하지 않습니다.

별도 concurrency control이 필요합니다.

- two-phase locking
- timestamp ordering
- optimistic validation
- MVCC와 conflict detection

`database-systems`의 isolation 계약을 participant와 cross-shard validation에 연결합니다.

## Presumed abort와 presumed commit

log record와 recovery message를 줄이는 optimization이 있지만 기본 state machine을 이해한 뒤 적용합니다. 누락된 record를 어떤 default decision으로 해석하는지, participant가 어떤 evidence를 요구하는지 정확해야 합니다.

## Timeout

coordinator의 client deadline과 participant prepared-state lifetime을 구분합니다.

- client가 기다리기를 중단해도 transaction decision이 이미 진행 중일 수 있습니다.
- PREPARED participant가 local timeout만으로 abort하면 global atomicity를 깨뜨릴 수 있습니다.
- orphan transaction은 coordinator recovery 또는 replicated decision service를 조회합니다.

## Exactly-once 착시

transaction ID와 idempotent prepare·decision handler가 필요합니다.

```text
prepare(txn_id) 중복
→ 기존 vote와 prepared state 반환

commit(txn_id) 중복
→ 이미 commit됨 반환, effect 추가 없음
```

message exactly-once delivery를 가정하지 않습니다.

## 실패 조건

- participant가 YES 응답 전에 prepared state를 durable하게 저장하지 않습니다.
- coordinator가 commit decision을 durable하게 기록하기 전에 participant에 COMMIT을 보냅니다.
- PREPARED participant가 local timeout으로 독자 abort합니다.
- coordinator memory만 transaction record를 소유합니다.
- 2PC가 serializability까지 자동 제공한다고 봅니다.
- 각 shard의 configuration epoch를 확인하지 않습니다.
- duplicate decision이 application effect를 두 번 만듭니다.

## 검증

[atomic commit 실습](../../exercises/04-partitioning-and-atomicity/02-atomic-commit/README.md)은 두 participant와 replicated coordinator의 crash trace를 제공합니다.

필수 schedule:

1. A와 B가 YES를 durable하게 기록합니다.
2. coordinator가 COMMIT을 기록한 뒤 A에만 전달하고 crash합니다.
3. B는 PREPARED 상태로 restart합니다.
4. 새 coordinator가 durable decision을 읽어 B에 COMMIT을 재전송합니다.
5. 모든 participant가 같은 decision을 적용합니다.

부정 불변식:

```text
한 transaction에서 일부 participant만 commit하고 다른 participant가 abort하지 않습니다.
COMMIT decision은 모든 YES evidence 없이 생성되지 않습니다.
PREPARED state와 lock이 recovery에서 사라지지 않습니다.
중복 decision이 effect를 추가하지 않습니다.
```

## 완료 조건

- atomic commit와 Saga의 보장을 구분합니다.
- 2PC의 prepare·decision durable state를 설명합니다.
- blocking과 coordinator recovery를 모델링합니다.
- consensus가 coordinator availability를 개선하지만 participant protocol을 대체하지 않음을 이해합니다.
- atomicity와 isolation을 별도 계약으로 검증합니다.
