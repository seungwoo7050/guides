# Global snapshot과 distributed checkpoint

## 목표

공통 시계 없이 여러 process와 channel의 상태를 하나의 consistent global state로 기록합니다. local backup의 집합과 consistent snapshot의 차이를 이해하고 checkpoint, audit, deadlock detection과 복구 경계를 설계합니다.

## Local snapshot의 집합은 global snapshot이 아닙니다

두 account shard가 transfer를 처리한다고 가정합니다.

```text
Shard A에서 10 차감
→ transfer message
→ Shard B에서 10 추가
```

A를 차감 후, B를 추가 전 snapshot하면 전체 합이 10 줄어든 것처럼 보일 수 있습니다. channel에 전송 중인 message를 포함하면 consistent state로 설명할 수 있습니다.

Global state는 다음으로 구성됩니다.

```text
각 process의 local state
+ 각 channel에서 전송 중인 message state
```

## Consistent cut

snapshot이 receive event를 포함하면서 causal send를 제외하면 일관되지 않습니다.

```text
receive(m) in cut
send(m) not in cut
```

consistent cut는 모든 포함 event의 causal predecessor를 포함합니다.

[causality 문서](../01-model-and-time/03-causality-and-logical-clocks.md)의 happened-before 관계를 사용합니다.

## Chandy–Lamport snapshot 직관

가정:

- process는 message로 통신합니다.
- channel이 reliable하고 FIFO입니다.
- snapshot 중 application computation은 계속됩니다.

marker 기반 절차:

1. initiator가 local state를 기록합니다.
2. 모든 outgoing channel에 marker를 보냅니다.
3. process가 처음 marker를 받으면 local state를 기록합니다.
4. 처음 marker를 받은 incoming channel은 empty로 기록합니다.
5. 다른 incoming channel에서는 marker를 받을 때까지 도착한 application message를 channel state로 기록합니다.
6. 모든 process와 channel 기록을 모읍니다.

FIFO 조건 때문에 marker보다 먼저 보낸 message와 뒤에 보낸 message를 구분할 수 있습니다.

## Non-FIFO channel

channel이 FIFO가 아니면 marker보다 먼저 보낸 application message가 marker 뒤에 도착할 수 있습니다. 추가 sequence, coloring 또는 다른 snapshot algorithm이 필요합니다.

실제 transport가 TCP여도 reconnect·multiple stream·broker partition·retry를 거치면 application-level channel이 FIFO인지 별도 검토해야 합니다.

## Snapshot의 용도

### Checkpoint와 recovery

여러 process를 consistent state로 복구합니다. 그러나 external side effect, client response와 durable channel을 함께 다루지 않으면 duplicate·lost effect가 생길 수 있습니다.

### Stable property detection

한 번 참이 되면 계속 참인 property를 찾는 데 사용할 수 있습니다.

- computation termination
- deadlock
- 특정 token의 소실

### Audit와 debugging

분산 trace의 consistent cut를 재구성해 “그 시점에 어떤 message가 transit이었는가”를 조사합니다.

### Backup

각 shard snapshot과 global metadata를 같은 generation으로 묶습니다. restore에서는 generation manifest와 checksum을 확인합니다.

## Coordinated checkpoint

모든 participant가 barrier에 도달해 local checkpoint를 만들 수 있습니다.

장점:

- 이해와 restore가 단순할 수 있습니다.

비용:

- pause와 straggler
- barrier coordinator availability
- participant가 빠졌을 때 abort·retry
- large state write와 foreground impact

## Uncoordinated checkpoint와 rollback propagation

각 process가 독립 checkpoint를 만들면 서로 호환되지 않는 state 조합을 선택할 수 있습니다. recovery 중 message dependency 때문에 다른 process도 더 이전 checkpoint로 돌아가는 domino effect가 생길 수 있습니다.

message logging과 dependency tracking으로 복구 가능한 consistent line을 찾을 수 있지만 metadata와 protocol이 복잡해집니다.

## Global snapshot manifest

```text
SnapshotManifest {
  generation
  participants
  participant_snapshot_id
  channel_or_log_frontier
  routing_epoch
  configuration
  created_by
  status
  checksums
}
```

manifest status:

```text
PREPARING
→ COMPLETE
또는
→ ABORTED
```

모든 component가 durable하고 검증되기 전 COMPLETE로 publish하지 않습니다.

## Restore

restore는 단순 file copy가 아닙니다.

1. manifest와 participant set을 확인합니다.
2. 각 snapshot checksum과 format compatibility를 검증합니다.
3. routing·membership generation을 복원합니다.
4. channel state 또는 log frontier 이후 message 처리 정책을 적용합니다.
5. client session과 external effect deduplication을 복원합니다.
6. isolated environment에서 invariant를 검사합니다.
7. 새 fencing epoch로 service를 공개합니다.

old process와 resource writer가 살아 있으면 restored cluster와 동시에 write할 수 있으므로 environment·credential·fencing을 분리합니다.

## Snapshot과 transaction

global snapshot이 모든 cross-shard transaction을 atomic하게 보여 주는지 확인합니다.

- prepared transaction과 final decision
- in-flight commit message
- coordinator record
- participant lock·intent

restore 뒤 coordinator가 decision을 재전송할 수 있어야 합니다. prepared state만 있고 decision service가 없으면 blocking이 다시 나타납니다.

## 실패 조건

- local snapshot timestamp가 비슷하다는 이유로 consistent global snapshot이라고 부릅니다.
- receive를 포함하면서 send 또는 channel state를 제외합니다.
- FIFO가 아닌 application channel에 marker algorithm을 그대로 적용합니다.
- 모든 participant 완료 전 manifest를 COMPLETE로 publish합니다.
- backup 성공만 검사하고 restore를 실행하지 않습니다.
- restore에서 client session·prepared transaction·routing epoch를 제외합니다.
- old cluster와 restored cluster의 write 권한을 fencing하지 않습니다.

## 검증

trace fixture에서 다음을 재현합니다.

```text
A가 debit을 기록하고 transfer message를 보냅니다.
snapshot marker가 서로 다른 channel로 이동합니다.
B가 transfer를 적용합니다.
application message와 marker 전달 순서를 바꿉니다.
```

검사:

- snapshot 안의 총액 + channel in-flight value가 invariant를 만족합니다.
- receive가 포함되면 send 또는 equivalent channel evidence가 포함됩니다.
- incomplete generation은 restore 후보가 아닙니다.
- restore 뒤 duplicate transfer가 한 번만 적용됩니다.

## 완료 조건

- local snapshot 집합과 consistent global state를 구분합니다.
- process state와 channel state를 함께 기록합니다.
- FIFO 가정과 non-FIFO 확장을 설명합니다.
- checkpoint manifest를 generation·participant·frontier로 설계합니다.
- backup을 restore와 fencing까지 포함한 계약으로 검증합니다.
