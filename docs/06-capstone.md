# 통합 과제: 결정적 복제 Key-Value Store

## 목표

앞선 문서의 실행 모델, consistency, Raft, crash recovery와 검증 방식을 하나의 작은 시스템에 연결합니다. production database를 만드는 것이 아니라 **명시한 failure model과 실제 실행·탐색한 schedule 범위에서 committed state와 client-visible history를 검사할 수 있는 protocol core**를 구현하는 것이 목적입니다.

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

membership change·sharding의 실제 코드와 real socket runtime은 core 완료 뒤 선택 구현입니다. 다만 membership·sharding의 상태 전이, 불변식, 대표 실패를 분석한 capstone dossier는 필수입니다.

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
./scripts/new-capstone-workspace.sh
```

helper는 기존 `.workspace/replicated-kv`를 덮어쓰지 않습니다. 이미 만든 학습 공간이 있다면 그대로 사용합니다.

검사는 환경 변수로 구현 경로를 지정할 수 있습니다.

```sh
CAPSTONE_ROOT="$PWD/.workspace/replicated-kv" \
  python3 -m unittest discover -s capstone/tests -v
```

`CAPSTONE_ROOT`를 생략하면 `.workspace`가 아니라 canonical starter를 검사합니다.

## 검증의 세 층

1. `make check`와 `make verify`는 저장소 구조, 문서·fixture, canonical starter 계약을 검사합니다.
2. 위 `CAPSTONE_ROOT` 명령은 학습자 구현에 공개된 storage·protocol 계약의 일부를 검사합니다.
3. [`completion-evidence-rubric`](../reference/completion-evidence-rubric.md)에 따라 추가 schedule·trace·history·설계 증거를 사람이 검토합니다.

공개 tests 통과만으로 모든 schedule, 전체 Raft safety·liveness, membership·sharding 구현 또는 production 적합성을 증명하지는 않습니다.

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

- 같은 source·runtime·configuration·initial state·seed·schedule이 같은 canonical trace hash를 만듭니다.
- 실제 실행하고 기록한 모든 schedule의 각 step에서 safety invariant가 유지됩니다.
- client history가 선택한 consistency model을 만족합니다.
- 실패한 run은 최소 counterexample과 source identity를 남깁니다.

## Milestone 8. Membership·sharding 누적 검토

실제 코드를 확장하지 않더라도 다음 두 dossier는 필수입니다.

```text
.workspace/replicated-kv/evidence/
├── membership-review.md
└── sharding-review.md
```

`membership-review.md`에는 learner catch-up, configuration transition, quorum overlap, transition 중 leader crash·restart, snapshot의 configuration 복원, removed node fencing을 하나의 상태 전이와 대표 trace로 연결합니다. conflicting majority가 생기지 않는 근거와 아직 자동 검사하지 못한 가정을 분리합니다.

`sharding-review.md`에는 snapshot + change catch-up, source fence, metadata cutover, stale router rejection, duplicate transfer, cleanup을 연결합니다. 각 key의 write authority가 한 곳뿐인 시점, cutover 전 acknowledged write의 보존, 중복 transfer의 idempotence를 trace로 제시합니다.

평가 기준과 필요한 trace 필드는 [`completion-evidence-rubric`](../reference/completion-evidence-rubric.md)과 [`trace-schema`](../reference/trace-schema.md)를 따릅니다.

## 선택 구현 확장 A. Membership 변경

- learner 추가와 catch-up
- 한 번에 한 voter 변경 또는 joint consensus
- configuration을 log와 snapshot에 포함
- removed node fencing

완료 조건:

- transition 중 conflicting majority가 없습니다.
- leader crash 뒤 transition을 재개합니다.
- removed node write가 거절됩니다.

## 선택 구현 확장 B. Sharding

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

## 선택 구현 확장 C. 실제 runtime

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

상세 판정 기준은 [`completion-evidence-rubric`](../reference/completion-evidence-rubric.md)을 사용합니다. 최소 dossier는 다음과 같습니다.

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

evidence/
- manifest: source·runtime·config·seed·schedule·failure model identity
- public-tests.log와 추가 검사 결과
- schedules/와 traces/: 정상·경계·대표 실패 실행
- invariants.md와 histories.md
- 최소 한 개의 알려진 오답 또는 실패 counterexample와 regression
- membership-review.md와 sharding-review.md
- final-report.md: 통과·실패·UNVERIFIED와 알려진 한계
```

trace와 manifest는 [`trace-schema`](../reference/trace-schema.md)를 따릅니다. test 이름이나 존재만 나열하지 말고 실제 command, 결과, trace hash와 사람이 확인할 판단 근거를 남깁니다.

## 최종 완료 조건

다음 문장을 구현과 검사로 증명합니다.

1. 같은 term에는 leader가 최대 하나이며 durable vote가 restart 뒤 바뀌지 않습니다.
2. committed log prefix는 future leader와 snapshot에서 보존됩니다.
3. 같은 log index에 서로 다른 command를 apply하지 않습니다.
4. response가 사라져 client가 retry해도 application effect는 한 번입니다.
5. snapshot과 compaction 뒤에도 state·session·configuration 의미가 같습니다.
6. 기록한 source·config·seed·schedule로 실제 생성·실행한 모든 trace step에서 safety invariant가 유지됩니다.
7. liveness 주장은 majority·delivery·storage·timer의 구체적인 조건과 함께 기록됩니다.
8. client-visible history는 선택한 consistency model의 checker를 통과합니다.

이 완료 조건은 제출한 유한한 실행과 명시한 가정에 대한 증거입니다. 자동 검사 결과를 탐색하지 않은 event order 전체나 production 안전성에 대한 보편 증명으로 확대하지 않습니다. 최종 판정에는 rubric에 따른 human review가 필요합니다.
