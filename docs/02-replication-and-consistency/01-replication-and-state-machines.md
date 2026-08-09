# 복제와 결정적 상태 기계

## 목표

복제의 목적을 “서버 수를 늘리는 것”으로 표현하지 않고, 어떤 failure에도 어떤 상태와 service를 보존할 것인지 정의합니다. primary-backup, operation replication과 state transfer를 구분하고, replicated state machine이 같은 명령 순서와 결정적 적용을 요구하는 이유를 이해합니다.

## 복제의 목적

복제는 하나의 목표만 갖지 않습니다.

- node 또는 disk 장애 뒤 data durability를 유지합니다.
- 일부 failure 중에도 read 또는 write service를 계속합니다.
- 사용자와 가까운 위치에서 read latency를 줄입니다.
- read throughput을 분산합니다.
- maintenance와 upgrade 중 service를 유지합니다.

목표가 다르면 선택하는 consistency와 protocol도 달라집니다. read scale을 위한 asynchronous replica와 metadata consistency를 위한 consensus group을 같은 “replica”로 부르면 보장 범위가 흐려집니다.

## 복제 대상

### State replication

완성된 state 또는 state delta를 전달합니다.

```text
primary state after command
→ backup에 새 value 또는 page 전송
```

장점:

- follower가 command 구현을 공유하지 않아도 됩니다.
- nondeterministic command의 결과를 그대로 보낼 수 있습니다.

비용:

- 변경량이 클 수 있습니다.
- update ordering과 partial transfer를 별도로 처리해야 합니다.
- 어떤 state가 authoritative한지 명확해야 합니다.

### Operation replication

모든 replica가 같은 명령을 같은 순서로 적용합니다.

```text
log[42] = put("x", 7)
```

조건:

- 명령 순서에 agreement가 필요합니다.
- state machine transition이 결정적이어야 합니다.
- snapshot과 restart 뒤 같은 prefix를 재현해야 합니다.

replicated log는 state 자체가 아니라 **state를 재구성하는 ordered command history**입니다.

### Mixed replication

실제 시스템은 log replication과 snapshot/state transfer를 함께 사용합니다.

```text
최근 상태 = snapshot + snapshot 이후 committed log suffix
```

snapshot이 어떤 log index·term까지 포함하는지 명시하지 않으면 follower가 중복 적용하거나 prefix를 잃을 수 있습니다.

## Primary-backup

하나의 primary가 client write를 받고 backup에 전달합니다.

설계할 항목:

- primary 선정과 epoch
- write를 commit으로 볼 시점
- 몇 개 backup acknowledgment가 필요한지
- primary crash 뒤 successor의 state 조건
- old primary가 다시 돌아왔을 때 fencing
- read를 어느 replica가 제공하는지

단순 failover는 consensus 문제를 피하지 못합니다. 여러 node가 새 primary를 다르게 선택할 수 있으므로 **primary identity와 epoch에 대한 agreement**가 필요합니다.

## State machine replication

상태 기계 복제는 다음 구성으로 볼 수 있습니다.

```text
client command
→ consensus로 log position 결정
→ committed prefix 확정
→ 모든 replica가 같은 순서로 apply
→ 같은 state와 response 생성
```

핵심 조건:

1. 같은 index에 서로 다른 committed command가 없습니다.
2. replica는 committed command를 index 순서로 apply합니다.
3. transition이 같은 입력과 state에서 같은 결과를 만듭니다.
4. response가 command의 committed·applied 상태와 일치합니다.

## 결정성

다음 값을 state machine handler에서 직접 읽으면 replica가 달라질 수 있습니다.

- 현재 wall clock
- random number
- local filesystem 상태
- 외부 HTTP 응답
- process ID
- map iteration의 비결정 순서

필요한 nondeterministic input은 명령에 포함하거나 leader가 선택한 값을 log에 기록합니다.

```text
나쁜 예
apply(CreateSession)에서 각 replica가 random token 생성

좋은 예
leader가 token을 생성해 CreateSession(token)을 log에 기록
```

시간 기반 expiry도 같은 문제를 가집니다. `expire_at` 또는 logical tick을 명령으로 기록하고 모든 replica가 같은 기준을 적용해야 합니다.

## Commit과 apply

`log에 존재`, `quorum에 복제`, `commit`, `state machine apply`, `client response`는 서로 다른 상태입니다.

| 상태 | 의미 |
|---|---|
| appended | local log에 기록됨 |
| replicated | 일부 follower에 같은 entry가 있음 |
| committed | protocol 규칙상 미래 leader에서 보존되어야 함 |
| applied | local application state에 반영됨 |
| responded | client가 결과를 관찰함 |

commit index보다 앞선 entry를 apply하면 rollback이 필요한 application state가 생깁니다. committed entry를 apply하기 전에 response하면 restart와 failover 뒤 결과가 사라질 수 있습니다.

일부 protocol은 commit과 apply 사이를 비동기로 두며, read path가 어느 index까지 apply됐는지 확인해야 합니다.

## Read path

replicated write가 안전해도 read는 별도 protocol이 필요합니다.

가능한 선택:

- leader가 current leadership을 확인한 뒤 read합니다.
- read도 log에 넣어 순서를 확정합니다.
- follower가 stale read를 명시적으로 제공합니다.
- client session의 observed index 이상을 apply한 replica에서 읽습니다.
- lease와 clock bound를 사용합니다.

“leader에서 읽으므로 linearizable”은 충분하지 않습니다. partition된 old leader가 자신이 leader라고 믿고 있을 수 있습니다.

## Replica recovery

뒤처진 replica는 다음 방법으로 복구할 수 있습니다.

- missing log suffix 전송
- snapshot 설치 후 suffix 전송
- peer state를 chunk로 복사
- checksum과 version tree로 차이 탐색

복구 중 replica가 read를 제공한다면 어떤 consistency를 제공하는지 명시합니다. incomplete snapshot과 새 log를 섞어 보이지 않도록 generation 또는 atomic install 경계가 필요합니다.

## 실패 조건

- replication factor만 적고 commit rule을 적지 않습니다.
- backup 수신 전 client에게 durable success를 반환합니다.
- old primary를 epoch 없이 다시 write 가능 상태로 둡니다.
- nondeterministic state machine input을 각 replica에서 새로 만듭니다.
- uncommitted log entry를 application state에 적용합니다.
- read consistency가 write protocol에서 자동으로 나온다고 봅니다.
- snapshot과 log suffix의 boundary index를 기록하지 않습니다.

## 검증

다음 trace를 최소로 포함합니다.

```text
1. primary가 entry를 local append합니다.
2. 한 backup에만 전송합니다.
3. client response 전 또는 후 primary가 crash합니다.
4. 서로 다른 backup 후보가 successor가 됩니다.
5. 어떤 value가 read되는지 검사합니다.
```

검사할 부정 불변식:

- acknowledged write가 successor에서 사라지지 않습니다.
- 같은 log index에 서로 다른 command를 apply하지 않습니다.
- uncommitted command가 client-visible state에 남지 않습니다.
- snapshot recovery가 command를 두 번 적용하지 않습니다.

## 완료 조건

- state replication과 operation replication을 구분합니다.
- primary identity에 epoch와 fencing이 필요한 이유를 설명합니다.
- log presence, commit, apply와 response를 분리합니다.
- replicated state machine의 결정성 조건을 지킵니다.
- read path를 write replication과 별도로 설계합니다.
