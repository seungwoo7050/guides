# Raft log replication과 commit

## 목표

leader가 command를 log에 추가하고 follower의 conflicting suffix를 복구하며, 미래 leader가 보존해야 하는 committed prefix를 결정하는 과정을 trace로 이해합니다. log에 있다는 사실과 commit된 사실을 구분합니다.

## Log entry

각 entry는 최소한 다음을 가집니다.

```text
LogEntry {
  index
  term
  command
}
```

`index`는 log 안의 위치이고 `term`은 entry가 처음 leader에 의해 생성된 election epoch입니다. index만 비교하면 서로 다른 leader가 만든 conflicting entry를 구분할 수 없습니다.

## Leader의 follower별 상태

leader는 follower마다 replication progress를 가집니다.

```text
nextIndex[follower]
- 다음 AppendEntries에서 보낼 첫 index

matchIndex[follower]
- follower에 동일하게 복제됐다고 leader가 확인한 마지막 index
```

새 leader는 보수적인 `nextIndex`에서 시작해 rejection 정보를 사용해 conflict를 뒤로 찾습니다. 구현 최적화로 conflict term의 첫 index를 한 번에 건너뛸 수 있지만, 먼저 한 칸씩 감소하는 정확한 상태 전이를 이해합니다.

## AppendEntries consistency check

leader는 다음 정보를 보냅니다.

```text
term
leaderId
prevLogIndex
prevLogTerm
entries[]
leaderCommit
```

follower는 `prevLogIndex`에 entry가 있고 term이 같은지 확인합니다. 다르면 새 entries를 적용하지 않고 rejection합니다.

일치한다면 새 entries와 충돌하는 local suffix를 제거하고 leader entries를 append합니다.

```text
leader:   [1/1, 2/1, 3/2, 4/4]
follower: [1/1, 2/1, 3/3, 4/3, 5/3]

prev = 2/1에서 일치
index 3의 term conflict
→ follower suffix 3..5 제거
→ leader 3/2, 4/4 append
```

아직 committed인지와 무관하게 follower log는 leader prefix를 따라갑니다.

## Log Matching property

두 log가 같은 index와 term의 entry를 가지면 그 index 이전 prefix가 동일해야 합니다.

AppendEntries의 previous entry check와 conflicting suffix 제거가 이 속성을 보존합니다.

이 property만으로 어떤 entry가 commit됐는지는 알 수 없습니다. commit rule과 election restriction이 함께 필요합니다.

## Commit index

leader는 current term에 생성된 entry가 majority `matchIndex`에 포함되면 해당 index까지 commit할 수 있습니다.

중요한 제한:

```text
과거 term entry를 replica count만 보고 직접 commit하지 않습니다.
current term entry를 commit하면서 그 앞의 과거 entry가 함께 commit됩니다.
```

왜 필요한가?

과거 term의 entry가 일부 majority에 있어도 서로 다른 configuration의 election과 log 상태 때문에 미래 leader에서 보존됨이 아직 충분히 증명되지 않을 수 있습니다. current-term entry를 majority에 복제하고 leader election restriction과 결합하면 leader completeness를 확보합니다.

대표적인 잘못된 구현:

```text
if count(matchIndex >= N) >= majority:
    commitIndex = N
```

여기에 `log[N].term == currentTerm` 조건이 없으면 safety가 깨질 수 있습니다.

## Follower commit

follower는 leader가 보낸 `leaderCommit`과 자신의 마지막 log index 중 작은 값까지 commit index를 올립니다.

```text
commitIndex = min(leaderCommit, lastLogIndex)
```

commit index는 감소하지 않습니다. follower가 아직 받지 못한 entry까지 apply해서도 안 됩니다.

## Apply

node는 `lastApplied < commitIndex`인 동안 index 순서대로 state machine에 적용합니다.

```text
lastApplied += 1
result = apply(log[lastApplied].command)
```

조건:

- apply order는 log index 순서입니다.
- 같은 command를 두 번 apply하지 않습니다.
- apply 결과와 client session metadata를 snapshot에 포함합니다.
- application exception이 protocol thread를 임의 상태에 두지 않도록 오류 계약을 정합니다.

## Client response

write response는 최소한 다음 중 어느 시점인지 명시해야 합니다.

- local append 완료
- majority replication 완료
- commit 완료
- local apply와 response 생성 완료

linearizable state machine command라면 보통 commit 및 apply 결과와 연결합니다. leader가 response 직전 crash하면 client가 retry할 수 있으므로 request ID와 session table이 필요합니다.

## New leader와 no-op entry

새 leader가 current term의 no-op entry를 append·commit하면 자신의 leadership 아래 commit boundary를 확정하고 이전 term prefix를 함께 commit할 수 있습니다. 또한 linearizable read barrier 구현에 필요한 current-term commit evidence로 사용할 수 있습니다.

no-op은 application state를 바꾸지 않더라도 replicated log와 commit progression에 의미가 있습니다.

## Read protocol

선택지:

### Log read

read 명령을 log에 append하고 commit·apply합니다. 단순하지만 latency와 log volume이 증가합니다.

### ReadIndex 또는 quorum confirmation

leader가 current term에 유효하며 필요한 commit boundary를 알고 있음을 majority heartbeat로 확인한 뒤, local state machine이 해당 index까지 apply됐을 때 read합니다.

### Lease read

clock와 network bound 가정을 사용해 lease 기간 동안 quorum round-trip을 생략합니다. 자세한 경계는 [lease 문서](05-failure-detectors-leases-and-time.md)에서 다룹니다.

## Pipelining과 batching

여러 entry를 한 번에 전송하거나 client command를 pipeline할 수 있습니다. 최적화해도 다음은 유지합니다.

- response와 request ID 매핑
- follower별 match index
- conflict 발생 시 suffix recovery
- commit order와 apply order
- max in-flight와 backpressure

## 실패 조건

- follower가 `prevLogTerm`을 확인하지 않습니다.
- conflict index 이후 일부 entry만 덮어쓰고 오래된 suffix를 남깁니다.
- follower acknowledgment를 받기 전에 `matchIndex`를 올립니다.
- 과거 term entry를 replica count만 보고 직접 commit합니다.
- commit index보다 앞선 entry를 apply합니다.
- apply 전에 client success를 반환하면서 recovery 계약이 없습니다.
- read가 current leadership이나 applied index를 확인하지 않습니다.

## 검증

[log reconciliation 실습](../../exercises/03-consensus-and-membership/02-log-reconciliation/README.md)은 서로 다른 term suffix를 가진 다섯 log를 제공합니다.

검사 항목:

- AppendEntries rejection이 올바른 conflict 위치를 찾습니다.
- follower의 conflicting suffix가 정확히 제거됩니다.
- current-term commit restriction이 적용됩니다.
- commit index가 감소하지 않습니다.
- 같은 index에 서로 다른 command를 apply하지 않습니다.
- leader crash와 새 election 뒤 acknowledged command의 결과가 보존됩니다.

## 완료 조건

- `nextIndex`, `matchIndex`, `commitIndex`, `lastApplied`를 구분합니다.
- AppendEntries consistency check와 log matching을 trace로 설명합니다.
- current-term entry commit 제한의 이유를 이해합니다.
- commit, apply와 client response 시점을 명시합니다.
- linearizable read에 추가 leadership·apply 검사가 필요함을 설명합니다.
