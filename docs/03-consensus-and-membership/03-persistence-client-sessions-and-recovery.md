# 영속 상태, client session과 crash recovery

## 목표

protocol message를 보내기 전에 durable해야 하는 상태를 식별하고, crash·restart와 client retry에도 command가 중복 적용되거나 잊히지 않도록 session state를 replicated state machine에 포함합니다.

## Durable state를 명시합니다

Raft의 핵심 durable state는 일반적으로 다음을 포함합니다.

```text
currentTerm
votedFor
log entries
snapshot metadata와 state
```

구현에 따라 다음도 durable 또는 snapshot에 포함합니다.

- client session별 마지막 request ID와 result
- cluster configuration
- application state
- checksum·format version
- last included index와 term

`commitIndex`와 `lastApplied`는 재구성 가능하다고 볼 수 있지만, restart 직후 어떤 message를 받고 어느 prefix를 apply하는지 계약을 명확히 해야 합니다.

## Persist-before-send 규칙

node가 durable update를 근거로 다른 participant에게 약속을 보낼 때는 저장 완료 뒤 응답합니다.

### Vote

```text
currentTerm와 votedFor 저장
→ RequestVote success 응답
```

응답을 먼저 보내고 crash하면 restart 뒤 같은 term에 다른 candidate에게 다시 vote할 수 있습니다.

### AppendEntries

```text
새 log entry와 필요한 suffix 변경 저장
→ AppendEntries success 응답
```

memory에만 저장한 뒤 success를 보내면 leader가 majority commit으로 판단했지만 crash 후 follower에서 entry가 사라질 수 있습니다.

### Client success

client-visible success는 protocol commit과 state machine apply·session result 저장 경계에 연결합니다.

## Storage abstraction

protocol core와 storage를 다음 operation으로 분리할 수 있습니다.

```text
load_hard_state()
append_entries(entries)
truncate_suffix(from_index)
save_term_and_vote(term, voted_for)
save_snapshot(snapshot)
flush()
```

실제 구현에서는 atomic batch, WAL, fsync와 directory entry durability가 필요할 수 있습니다. capstone은 operation 단위 atomic durable storage를 사용하고, 선택 과제에서 write·flush를 분리합니다.

## Crash point 표

각 state transition 사이 crash를 주입합니다.

| 위치 | restart 뒤 기대 상태 |
|---|---|
| term 증가 전 | 이전 term |
| term 저장 뒤 vote send 전 | 새 term, vote 기록 유지 |
| log append 전 | entry 없음 |
| append 저장 뒤 ack 전 | entry 존재, duplicate AppendEntries에 idempotent |
| commit 뒤 apply 전 | log로부터 apply 재개 |
| apply 뒤 client response 전 | session result로 retry에 동일 응답 |
| snapshot file 완성 전 | 이전 snapshot 사용 |
| snapshot pointer 교체 뒤 old log 삭제 전 | 새 snapshot과 중복 log를 안전하게 해석 |

crash point가 많을수록 storage transaction boundary가 중요합니다.

## Client retry 문제

client가 response를 받지 못하면 같은 command를 새 leader에 retry할 수 있습니다.

```text
client request (session=7, sequence=42)
→ leader commits and applies
→ response lost
→ leader crashes
→ client retries sequence=42
```

request ID가 없으면 command가 두 번 적용됩니다.

## Session table

replicated application state에 client별 진행 상태를 둡니다.

```text
SessionRecord {
  client_id
  last_sequence
  last_result
}
```

apply 규칙:

- `sequence == last_sequence`: 이전 result를 반환하고 state를 바꾸지 않습니다.
- `sequence == last_sequence + 1`: command를 적용하고 result를 저장합니다.
- `sequence < last_sequence`: 오래된 retry로 거절하거나 저장된 범위 안 결과를 반환합니다.
- `sequence > last_sequence + 1`: gap을 거절하거나 protocol에 맞는 pending 상태로 둡니다.

session table 자체가 replicated log의 command 적용 결과여야 모든 leader가 같은 deduplication 결정을 합니다.

## Result cache 범위

마지막 result만 저장하면 client가 순서대로 하나의 outstanding request만 보낸다는 가정이 필요합니다. 여러 request를 pipeline하면 더 넓은 result cache 또는 operation ID map이 필요합니다.

명시할 항목:

- client당 최대 in-flight request
- sequence gap 처리
- result 보존 기간
- large response를 저장할지 digest·reference를 저장할지
- session 만료와 client incarnation

## Session GC

session metadata를 영원히 저장할 수는 없습니다. 그러나 너무 일찍 지우면 오래된 retry가 새 command처럼 적용됩니다.

GC evidence 예:

- client가 더 작은 sequence를 보내지 않겠다는 close/ack protocol
- session lease와 bounded retry 기간
- application-level idempotency key의 별도 durable record
- external client incarnation 증가

시간만으로 삭제하면 clock·offline client·network delay 가정이 필요합니다.

## Snapshot과 session

snapshot은 key-value state뿐 아니라 deduplication에 필요한 session table과 configuration을 포함해야 합니다.

```text
snapshot at index 100
- application map
- client session records through index 100
- cluster configuration effective at index 100
- lastIncludedIndex=100
- lastIncludedTerm=8
```

session을 빼면 log 1..100을 삭제한 뒤 request 42의 이전 결과를 확인할 수 없어 중복 적용될 수 있습니다.

## Restart sequence

권장 순서:

```text
1. snapshot metadata와 checksum 검증
2. snapshot state와 session table 복원
3. snapshot 이후 log suffix 로드
4. hard state(term, vote) 복원
5. protocol role은 follower로 시작
6. committed prefix를 필요한 지점까지 apply
7. timer와 network participation 시작
```

corrupt snapshot이나 log는 정상 empty state로 묵시적으로 대체하지 않습니다. 안전하게 중단하고 repair 또는 operator action을 요구합니다.

## Fencing node incarnation

crash·restart 뒤 같은 node ID가 이전 process의 delayed message와 섞일 수 있습니다. term과 log check가 protocol message를 대부분 거르지만 runtime resource와 connection에는 incarnation ID가 유용합니다.

- old process의 disk writer
- duplicate background snapshot task
- stale connection callback
- old shard transfer worker

새 incarnation이 시작되면 이전 worker의 effect를 fencing합니다.

## 실패 조건

- vote·append acknowledgment를 durable write 전에 보냅니다.
- crash point를 operation 사이가 아니라 process 종료 한 곳에서만 검사합니다.
- client retry를 새 command로 처리합니다.
- session table을 local leader memory에만 둡니다.
- snapshot에서 session·configuration metadata를 제외합니다.
- session GC를 근거 없이 wall clock TTL로 수행합니다.
- corrupt storage를 empty node로 자동 초기화합니다.
- restart 뒤 이전 role을 그대로 복원해 leader로 시작합니다.

## 검증

[client session 실습](../../exercises/03-consensus-and-membership/03-client-session/README.md)은 apply 뒤 response 유실, leader crash, snapshot과 session GC를 조합합니다.

검사할 부정 불변식:

```text
같은 (client_id, sequence)의 application effect는 한 번뿐입니다.
retry는 원래 result와 같은 result를 반환합니다.
snapshot install 뒤에도 이전 request를 중복 적용하지 않습니다.
corrupt durable state를 정상 empty state로 사용하지 않습니다.
```

capstone 테스트는 각 persist boundary 전후에 crash를 주입하도록 설계합니다.

## 완료 조건

- protocol promise 전에 durable해야 하는 state를 나열합니다.
- crash point별 restart state를 표로 작성합니다.
- client session과 result deduplication을 replicated state로 구현합니다.
- snapshot·session GC와 retry horizon을 연결합니다.
- corruption과 empty initialization을 구분합니다.
