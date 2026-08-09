# Sharding, routing metadata와 rebalancing

## 목표

하나의 replicated state machine을 여러 key range 또는 hash partition으로 나눌 때 data ownership, routing, migration과 failure를 명시적인 state transition으로 설계합니다. shard를 옮기는 동안 double-write, lost write와 stale router를 막습니다.

## Sharding이 바꾸는 것

replication은 같은 data의 여러 copy를 다룹니다. sharding은 서로 다른 data subset을 여러 group에 나눕니다.

```text
Shard 1: keys [a, m)
Shard 2: keys [m, z)
```

각 shard가 별도 consensus group이라면 다음 상태가 추가됩니다.

- key를 어느 shard가 소유하는지 나타내는 routing metadata
- shard configuration과 replica set
- metadata version 또는 epoch
- shard split·merge·move의 전이 상태
- cross-shard operation의 coordination

## Partitioning 방식

### Range partitioning

연속 key range를 shard에 배치합니다.

장점:

- range scan과 locality
- split boundary가 명확함

위험:

- sequential key와 hot range
- uneven data size
- split 시 secondary index와 scan cursor 처리

### Hash partitioning

hash space를 나눠 key를 분산합니다.

장점:

- 균등 분배에 유리
- hot sequential key 완화

위험:

- range query 어려움
- hash function·virtual node·token metadata 관리
- key count가 같아도 workload가 균등하지 않을 수 있음

### Directory-based routing

metadata service가 key/range와 shard mapping을 소유합니다. 유연하지만 metadata consistency와 cache invalidation이 중요합니다.

## Routing metadata

```text
Route {
  key_range
  shard_id
  epoch
  replica_group
  state
}
```

router는 request에 자신이 본 epoch를 포함합니다. shard owner는 stale epoch request를 거절하고 최신 metadata 위치를 알려줍니다.

이중 방어:

- router cache invalidation
- storage owner의 authoritative epoch check

cache만 갱신하는 것으로는 race와 delayed request를 막지 못합니다.

## Ownership invariant

write path의 핵심 invariant를 먼저 정합니다.

```text
각 key와 configuration epoch에 대해
write를 commit할 권한이 있는 shard group은 최대 하나입니다.
```

migration 중 source와 target이 모두 data를 가질 수는 있지만, commit 권한과 replication responsibility를 분리합니다.

## Rebalancing state machine

예시 단계:

```text
STABLE(source owns epoch 10)
→ PREPARE(target bootstraps snapshot)
→ CATCH_UP(source change stream을 target에 적용)
→ FENCE(source의 새 write 권한을 epoch 11로 종료)
→ CUTOVER(metadata가 target epoch 11을 publish)
→ CLEANUP(source가 old data 제거)
→ STABLE(target owns epoch 11)
```

각 단계는 retry와 crash를 허용해야 합니다.

### PREPARE

- target은 아직 client write를 승인하지 않습니다.
- snapshot ID와 source epoch를 기록합니다.
- 같은 transfer ID 재요청은 기존 progress를 반환합니다.

### CATCH_UP

- snapshot 이후 change sequence를 적용합니다.
- gap과 duplicate를 검출합니다.
- source log retention이 transfer cursor를 지나지 않도록 pin합니다.

### FENCE

- source group은 새 epoch의 write를 승인하지 않습니다.
- 이전 epoch in-flight command의 commit boundary를 정합니다.
- external side effect가 있으면 fencing token을 사용합니다.

### CUTOVER

- metadata update가 consensus로 commit됩니다.
- stale router는 target 또는 metadata service에서 거절됩니다.
- target이 required snapshot·change frontier를 갖고 있어야 합니다.

### CLEANUP

- old route TTL만 기다리지 않고 stale request가 storage에서 fenced되는지 확인합니다.
- backup·repair·secondary index가 새 owner를 보도록 갱신합니다.
- rollback 가능 지점과 data deletion 시점을 구분합니다.

## Split과 merge

### Split

```text
[a, z) epoch 20
→ [a, m) epoch 21 + [m, z) epoch 21
```

검사:

- 모든 key가 정확히 한 child range에 속합니다.
- boundary key `m`의 소유가 명확합니다.
- parent에 도착한 stale write가 거절됩니다.
- scan cursor와 snapshot이 어느 epoch에 속하는지 기록합니다.

### Merge

두 shard의 state와 version frontier를 하나의 group으로 모읍니다. 서로 다른 commit order를 전역 total order로 소급해 만들 수는 없습니다. merge 이후 순서와 cross-shard invariant를 별도로 정의합니다.

## Hot shard

data size와 QPS, write amplification, storage IO, key skew를 따로 측정합니다. 단순 key count만으로 split하면 hot key 하나가 계속 한 shard에 남을 수 있습니다.

선택:

- hot key 내부 partition
- read replica·cache
- application key redesign
- rate limit
- workload-aware split

## Metadata availability

모든 request가 metadata service에 동기 조회하면 bottleneck이 됩니다. cache를 사용하되 stale route를 owner가 fencing해야 합니다.

metadata service 장애 중 정책:

- cached route로 제한된 시간 read/write 허용
- read-only
- 새 routing이 필요한 request 거절
- epoch 확인 가능한 owner에만 요청

availability와 consistency를 API별로 명시합니다.

## Failure matrix

| 실패 | 기대 상태 |
|---|---|
| snapshot 중 target crash | 같은 transfer ID로 재개 또는 새 generation 재시작 |
| change stream gap | cutover 금지, source에서 missing range 재전송 |
| fence 뒤 metadata commit 전 coordinator crash | source write는 닫혀 있고 재개 담당이 transition을 이어감 |
| cutover 뒤 stale router | old epoch request 거절과 route refresh |
| cleanup 전 source restart | old data는 있어도 write authority 없음 |
| metadata partition | 정책에 따라 cached operation 제한 또는 거절 |

## 실패 조건

- source와 target이 migration 중 모두 client write를 승인합니다.
- route cache invalidation만 사용하고 storage epoch check가 없습니다.
- snapshot과 change stream 사이 gap을 기록하지 않습니다.
- cutover 전에 target durability와 applied frontier를 확인하지 않습니다.
- cleanup에서 stale request fencing을 확인하지 않고 source data를 지웁니다.
- split boundary의 inclusive/exclusive 규칙이 없습니다.
- transfer coordinator memory만으로 progress를 관리합니다.

## 검증

[shard rebalance 실습](../../exercises/04-partitioning-and-atomicity/01-shard-rebalance/README.md)은 source·target·metadata service와 stale router를 가진 trace를 제공합니다.

검사할 invariant:

```text
key는 모든 epoch에서 정확히 한 write authority를 가집니다.
acknowledged write는 cutover 뒤 target에서 보입니다.
stale epoch write는 commit되지 않습니다.
transfer retry가 같은 change를 두 번 적용하지 않습니다.
cleanup은 rollback·stale-request 조건 뒤에만 실행됩니다.
```

## 완료 조건

- replication과 sharding을 구분합니다.
- routing metadata에 epoch와 authoritative owner check를 둡니다.
- rebalancing을 retry 가능한 state machine으로 설계합니다.
- snapshot·change frontier·fence·cutover 순서를 설명합니다.
- split·merge·hot shard와 metadata failure를 별도 문제로 다룹니다.
