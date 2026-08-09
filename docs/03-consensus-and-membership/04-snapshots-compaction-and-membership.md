# Snapshot, log compaction과 membership 변경

## 목표

무한히 증가하는 replicated log를 snapshot으로 줄이면서도 state·session·configuration을 잃지 않습니다. cluster membership을 변경할 때 old와 new quorum이 서로 교차하지 않아 split brain이 생기는 상태를 막습니다.

## Snapshot의 의미

snapshot은 단순한 backup 파일이 아닙니다. committed log prefix를 같은 abstract state로 대체하는 protocol object입니다.

```text
Snapshot {
  lastIncludedIndex
  lastIncludedTerm
  applicationState
  clientSessions
  configuration
  formatVersion
  checksum
}
```

정확성 조건:

```text
snapshot state == log[1..lastIncludedIndex]를 순서대로 apply한 state
```

snapshot 이후 필요한 state는 다음과 같습니다.

```text
snapshot + log[lastIncludedIndex+1 ..]
```

## Snapshot 생성

snapshot을 만드는 동안 application apply가 계속될 수 있습니다. 선택 가능한 경계:

- state machine lock으로 특정 applied index에서 복사
- copy-on-write 또는 immutable state view
- checkpoint API로 consistent state 생성
- incremental snapshot과 base generation

`commitIndex`가 아니라 실제 `lastApplied`까지의 state를 snapshot합니다. commit됐지만 아직 apply되지 않은 entry를 포함했다고 기록하면 snapshot metadata와 state가 불일치합니다.

## Atomic install

file 생성과 active pointer 교체를 분리합니다.

```text
1. 임시 generation에 snapshot write
2. checksum·length 검증
3. durable flush
4. active metadata를 원자 교체
5. directory metadata flush
6. old generation과 불필요 log 정리
```

capstone은 filesystem detail을 단순화하지만 state machine 차원에서 “완성 전 snapshot은 active하지 않음”을 보장합니다.

## InstallSnapshot

leader는 follower가 필요한 log prefix를 이미 compaction했으면 snapshot을 전송합니다.

follower 처리:

1. term과 leader validity를 확인합니다.
2. chunk·generation·checksum을 확인합니다.
3. 완성된 snapshot을 atomic install합니다.
4. local log에 snapshot boundary와 일치하는 suffix가 있으면 보존할 수 있습니다.
5. 그렇지 않으면 conflicting log를 제거합니다.
6. commitIndex와 lastApplied를 최소 snapshot index까지 올립니다.
7. application state·session·configuration을 함께 교체합니다.

중복 또는 오래된 snapshot은 idempotent하게 거절·무시합니다.

## Log compaction

snapshot이 durable하고 active하다는 evidence가 생긴 뒤 prefix를 삭제합니다.

주의:

- slow follower가 prefix를 필요로 할 수 있습니다. leader는 snapshot 전송으로 전환합니다.
- index가 1부터 다시 시작한다고 가정하지 않습니다. logical index와 local array offset을 분리합니다.
- boundary entry의 term을 보존해야 AppendEntries consistency check를 할 수 있습니다.
- snapshot 이전 client session을 잃지 않습니다.

## Membership 문제

configuration이 다음처럼 바뀐다고 가정합니다.

```text
old = {A, B, C}
new = {D, E, F}
```

old majority `{A, B}`와 new majority `{D, E}`는 교차하지 않습니다. 두 집합이 독립적으로 leader를 선출하고 서로 다른 log를 commit할 수 있습니다.

configuration 변경도 consensus로 순서를 정하고, 전이 기간에 quorum overlap을 보장해야 합니다.

## Joint consensus

한 가지 방식은 joint configuration을 log에 기록하는 것입니다.

```text
C_old
→ C_old,new
→ C_new
```

joint 단계에서는 election과 commit에 old majority와 new majority를 모두 요구합니다. 따라서 어느 쪽도 단독으로 conflicting decision을 만들 수 없습니다.

완료 조건:

- joint entry가 commit되기 전 new config만 사용하지 않습니다.
- old leader가 configuration transition을 log order로 처리합니다.
- restart와 snapshot에도 current configuration이 복원됩니다.
- removed node의 stale message와 client traffic을 fencing합니다.

## Single-server change

한 번에 node 하나만 추가·제거해 연속 configuration의 majority가 겹치도록 만드는 방식도 있습니다. 간단해 보이지만 다음이 필요합니다.

- 동시에 하나의 change만 진행
- learner가 서로 다른 pending change를 시작하지 못하게 함
- 새 node가 충분히 catch up한 뒤 voter로 승격
- 제거 node와 old leader의 fencing
- 각 configuration entry의 commit 확인

구현하는 Raft variant의 정확한 membership algorithm을 문서와 일치시켜야 합니다.

## Learner와 non-voter

새 node는 log를 따라잡기 전 voting member로 추가하지 않는 편이 안전합니다.

```text
add learner
→ snapshot·log catch-up
→ progress와 durability 확인
→ voting member로 promote
```

catch-up threshold는 단순 index 차이뿐 아니라 snapshot generation, storage health와 network stability를 고려할 수 있습니다.

## Node 제거

제거된 node가 local state만 보고 계속 leader·writer처럼 행동하지 않도록 다음을 사용합니다.

- 더 큰 configuration epoch
- protocol message에서 membership 확인
- external storage와 routing layer의 fencing token
- client redirect와 connection 종료
- operator가 old data를 재사용할 때 explicit rejoin/bootstrap

## Snapshot과 configuration

configuration entry를 compaction한 뒤에도 snapshot에서 effective configuration을 복원해야 합니다. 그렇지 않으면 restart한 node가 이미 제거된 voter를 다시 포함하거나 잘못된 quorum을 계산할 수 있습니다.

snapshot boundary와 configuration index를 함께 기록합니다.

## 실패 조건

- snapshot을 `commitIndex` 기준으로 만들고 state는 `lastApplied`까지만 포함합니다.
- 완성되지 않은 snapshot file을 active로 표시합니다.
- logical log index와 local list offset을 혼동합니다.
- snapshot에서 session과 configuration을 제외합니다.
- old config에서 new config로 즉시 교체합니다.
- 새 node가 catch up하기 전에 voter가 됩니다.
- membership change 두 개를 동시에 진행합니다.
- 제거 node의 external write 권한을 fencing하지 않습니다.

## 검증

필수 schedule:

```text
1. leader가 snapshot index 100을 생성합니다.
2. snapshot pointer 교체 전 crash합니다.
3. restart 후 이전 snapshot과 log로 복구합니다.
4. 다시 snapshot을 완료합니다.
5. follower가 index 50까지만 가진 상태에서 InstallSnapshot을 받습니다.
6. 같은 snapshot chunk와 완료 message를 중복 전달합니다.
```

membership schedule:

```text
A,B,C에서 D를 learner로 추가
→ D catch-up 중 leader crash
→ 새 leader가 transition을 이어감
→ D voter 승격
→ A 제거
→ partition된 A가 stale client write 시도
```

검사:

- same index에 conflicting apply가 없습니다.
- snapshot install은 idempotent합니다.
- transition 중 요구 quorum이 정확합니다.
- 제거 node의 write가 external owner에서 거절됩니다.

## 완료 조건

- snapshot을 committed log prefix와 동등한 abstract state로 정의합니다.
- atomic snapshot install과 compaction 순서를 설명합니다.
- snapshot에 session·configuration metadata를 포함합니다.
- membership 변경에서 quorum overlap을 보존합니다.
- learner catch-up과 removed node fencing을 설계합니다.
