# 통합 과제: 결정적 복제 Key-Value Store

## 목표

앞선 문서의 실행 모델, consistency, Raft, crash recovery와 검증 방식을 하나의 작은 시스템에 연결합니다. production database를 만드는 것이 아니라 **어떤 event order에서도 committed state와 client-visible history를 지키는 protocol core**를 구현하는 것이 목적입니다.

완성할 시스템:

```text
3~5개 node의 단일 Raft group
+ key-value state machine
+ 결정적 network와 virtual time
+ crash-recovery storage
+ client retry와 deduplication
+ snapshot과 log compaction
+ history·invariant 검사
```

sharding, membership change와 real socket runtime은 core 완료 뒤 선택 확장입니다.

## 비범위

- Byzantine fault tolerance
- TLS·인증·authorization
- production-grade filesystem durability와 corruption repair
- multi-region topology
- SQL·secondary index 전체
- 고성능 network transport
- Kubernetes 운영

이 비범위가 중요합니다. 작은 model에서 protocol state와 failure를 끝까지 검증하는 것이 여러 제품을 얕게 조립하는 것보다 우선입니다.

## Starter

[`capstone/starter`](../capstone/starter/README.md)는 다음을 제공합니다.

```text
dskv/
├── types.py       message, log entry, request와 response 타입
├── storage.py     crash-recovery용 in-memory durable store
├── network.py     delay·drop·duplicate·partition 가능한 scheduler
├── node.py        구현할 Raft protocol core
└── cluster.py     node·client·fault를 조합하는 test harness
```

`node.py`의 핵심 transition은 의도적으로 구현되지 않았습니다. reference answer는 제공하지 않습니다. 문서와 public tests를 계약으로 사용합니다.

학습 공간:

```sh
mkdir -p .workspace
cp -R capstone/starter .workspace/replicated-kv
```

검사는 환경 변수로 구현 경로를 지정할 수 있습니다.

```sh
CAPSTONE_ROOT=.workspace/replicated-kv \
  python3 -m unittest discover -s capstone/tests -v
```

## Sequential specification

초기 object state는 빈 map과 client session table입니다.

```text
put(key, value)
- map[key] = value
- OK 반환

get(key)
- 현재 value 또는 NOT_FOUND 반환

compare_and_set(key, expected, next)
- 현재 값이 expected면 next로 변경하고 OK
- 아니면 state를 바꾸지 않고 MISMATCH
```

각 mutating command는 `(client_id, sequence)`를 가집니다.

```text
같은 pair 재전달
→ 이전 result 반환
→ application effect 추가 없음
```

## 시스템 모델

### Node

```text
role: FOLLOWER | CANDIDATE | LEADER
current_term
voted_for
log
commit_index
last_applied
next_index
match_index
state_machine
client_sessions
snapshot
configuration
```

### Event

- election timer
- heartbeat timer
- RequestVote request·response
- AppendEntries request·response
- client command
- crash·restart
- storage completion
- snapshot trigger·install

### Network

- message delay
- drop
- duplicate
- reorder
- one-way partition
- heal

### Storage

core 단계에서는 storage operation이 원자적이고 durable하다고 가정합니다. persist 호출 뒤 process가 crash해도 저장 결과가 남습니다. 선택 확장에서 write와 flush를 분리합니다.

## Core invariant

모든 simulator step 뒤 검사합니다.

```text
Election Safety
같은 term에 leader는 최대 하나입니다.

Vote Safety
한 node는 같은 term에 최대 한 candidate에게 vote합니다.

Log Matching
같은 index와 term을 가진 log prefix는 같습니다.

Commit Monotonicity
commit_index는 감소하지 않습니다.

Apply Bound
last_applied <= commit_index입니다.

State Machine Safety
같은 index에 서로 다른 command를 apply하지 않습니다.

Client At-Most-Once Effect
같은 (client_id, sequence)의 effect는 최대 한 번입니다.

Snapshot Equivalence
snapshot state는 lastIncludedIndex까지 apply한 state와 같습니다.
```

## Milestone 0. Model과 trace

코드를 수정하기 전에 다음을 작성합니다.

```text
.workspace/replicated-kv/design/
├── system-model.md
├── sequential-spec.md
├── invariants.md
├── liveness.md
└── trace-format.md
```

완료 조건:

- crash-stop과 crash-recovery를 구분합니다.
- safety와 liveness를 별도 항목으로 둡니다.
- timeout이 crash를 확정하지 않음을 기록합니다.
- client invocation·completion 형식을 정합니다.

## Milestone 1. Follower와 election

구현:

- term과 vote persistence
- election timeout
- RequestVote
- log freshness check
- majority election
- higher-term step-down

Failure schedule:

- split vote
- vote 저장 뒤 response 전 crash
- stale candidate
- delayed old vote response
- partition된 old leader의 higher term 관찰

완료 조건:

```text
same-term dual leader 없음
same-term double vote 없음
majority가 안정되면 bounded simulation 안에서 leader 선출
```

bounded liveness test는 protocol proof가 아니라 설정한 schedule과 fairness 아래의 검사임을 기록합니다.

## Milestone 2. Log replication

구현:

- leader local append
- AppendEntries consistency check
- follower conflicting suffix 삭제
- nextIndex·matchIndex
- current-term commit rule
- ordered apply

Failure schedule:

- follower마다 서로 다른 suffix
- ack delay·duplicate
- leader local append 뒤 crash
- majority replication 뒤 response 전 crash
- old leader의 stale AppendEntries

완료 조건:

- log matching 유지
- commit index 감소 없음
- current term entry 없이 과거 entry를 직접 commit하지 않음
- 같은 index에 conflicting apply 없음

## Milestone 3. Key-Value state machine과 client response

구현:

- `put`, `get`, `compare_and_set`
- command result
- leader redirect 또는 NOT_LEADER
- commit·apply 뒤 response
- read protocol 선택

core 권장 read:

- read도 log command로 넣거나
- current-term commit과 quorum confirmation을 요구하는 ReadIndex 방식

lease read는 선택 확장입니다.

완료 조건:

- completed write 뒤 시작한 read가 이전 값을 반환하지 않습니다.
- CAS mismatch는 state를 바꾸지 않습니다.
- uncommitted command가 client-visible state에 없습니다.

## Milestone 4. Crash recovery

구현:

- durable term·vote·log
- restart는 follower로 시작
- snapshot 이후 log suffix 복원
- commit·apply 재개
- corrupt state 명시적 거절

Crash point:

- term 저장 전·후
- vote response 전·후
- append 전·후
- follower ack 전·후
- commit 뒤 apply 전
- apply 뒤 response 전

완료 조건:

- durable promise가 restart 뒤 뒤집히지 않습니다.
- acknowledged command가 future leader에서 보존됩니다.
- apply가 restart 뒤 중복되지 않습니다.

## Milestone 5. Client session과 retry

구현:

```text
SessionRecord(client_id, last_sequence, last_result)
```

schedule:

```text
command commit·apply
→ response drop
→ leader crash
→ new leader election
→ same request retry
```

완료 조건:

- effect는 한 번입니다.
- retry result는 원래 result와 같습니다.
- sequence gap policy가 명확합니다.
- session state는 모든 replica와 snapshot에서 복원됩니다.

## Milestone 6. Snapshot과 compaction

구현:

- `lastIncludedIndex`, `lastIncludedTerm`
- application state와 session table snapshot
- atomic active generation 전환
- logical index와 local offset 분리
- InstallSnapshot
- snapshot 이후 log suffix 유지·삭제

schedule:

- snapshot write 중 crash
- active 전환 뒤 cleanup 전 crash
- duplicate chunk 또는 duplicate install
- slow follower가 compacted prefix 요청
- snapshot install 직후 retry

완료 조건:

- incomplete snapshot을 사용하지 않습니다.
- snapshot과 log가 command를 중복 적용하지 않습니다.
- deduplication metadata가 보존됩니다.
- stale snapshot은 current state를 되돌리지 않습니다.

## Milestone 7. History와 simulation

구현 또는 산출물:

- seeded random schedule
- explicit event schedule 저장
- every-step invariant
- register·CAS history checker
- failure trace shrink
- run artifact manifest

필수 run:

1. 정상 write/read
2. split vote
3. leader crash
4. one-way partition
5. response loss와 retry
6. slow follower와 snapshot install
7. repeated crash-restart

완료 조건:

- 같은 schedule이 같은 trace hash를 만듭니다.
- safety invariant가 모든 step에서 유지됩니다.
- client history가 선택한 consistency model을 만족합니다.
- 실패한 run은 최소 counterexample과 source identity를 남깁니다.

## 선택 확장 A. Membership 변경

- learner 추가와 catch-up
- 한 번에 한 voter 변경 또는 joint consensus
- configuration을 log와 snapshot에 포함
- removed node fencing

완료 조건:

- transition 중 conflicting majority가 없습니다.
- leader crash 뒤 transition을 재개합니다.
- removed node write가 거절됩니다.

## 선택 확장 B. Sharding

두 Raft group과 metadata group을 둡니다.

- range route와 epoch
- snapshot + change catch-up
- source fence
- metadata cutover
- stale router rejection
- cleanup

완료 조건:

- key당 write authority는 하나입니다.
- cutover 전 acknowledged write가 target에서 보입니다.
- duplicate transfer가 effect를 추가하지 않습니다.

## 선택 확장 C. 실제 runtime

protocol core를 변경하지 않고 adapter를 추가합니다.

- TCP 또는 HTTP transport
- filesystem storage
- process launcher
- metrics·trace export

simulation과 실제 runtime이 같은 message·state schema를 사용하도록 합니다.

## Failure matrix

| 실패 | 장애 중 허용 상태 | 복구 뒤 필수 상태 |
|---|---|---|
| minority partition | majority에서만 write commit | minority catch-up |
| leader crash before commit | entry가 사라질 수 있음, success 없음 | 새 leader의 legal suffix |
| leader crash after commit before response | client UNKNOWN | retry에 같은 result, effect 1회 |
| follower ack after restart | durable entry에 대해서만 success | majority evidence 정확 |
| stale old leader | local leader belief 가능 | higher term·fencing으로 commit 불가 |
| snapshot interruption | 이전 snapshot 사용 | 완성 generation만 active |
| InstallSnapshot duplicate | 중복 message | state·session effect 1회 |
| history checker violation | run 실패 | 최소 schedule과 regression fixture |

## 제출 산출물

```text
implementation/
- protocol core와 storage·network adapter

design/
- system model
- sequential specification
- invariants와 liveness assumptions
- durable state·crash point 표
- read protocol 결정
- snapshot·session 계약

tests/
- deterministic schedules
- generated runs
- history checker
- fault matrix

artifacts/
- 최소 한 개의 실패 counterexample
- 최종 검증 report
- source·config·seed·schedule identity
```

## 최종 완료 조건

다음 문장을 구현과 검사로 증명합니다.

1. 같은 term에는 leader가 최대 하나이며 durable vote가 restart 뒤 바뀌지 않습니다.
2. committed log prefix는 future leader와 snapshot에서 보존됩니다.
3. 같은 log index에 서로 다른 command를 apply하지 않습니다.
4. response가 사라져 client가 retry해도 application effect는 한 번입니다.
5. snapshot과 compaction 뒤에도 state·session·configuration 의미가 같습니다.
6. 지원하는 failure model 안의 모든 생성 trace에서 safety invariant가 유지됩니다.
7. liveness 주장은 majority·delivery·storage·timer의 구체적인 조건과 함께 기록됩니다.
8. client-visible history는 선택한 consistency model의 checker를 통과합니다.
