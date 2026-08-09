# Membership change 실습

## 목표

Raft configuration을 바꾸는 동안 old/new quorum이 안전하게 연결되고, 새 voter가 committed prefix를 따라잡은 뒤에만 투표하며, 제거된 node가 다시 write authority를 얻지 못하도록 설계합니다.

## 입력

[`membership.json`](membership.json)은 다음 세 scenario를 제공합니다.

- `safe-joint-consensus`: learner D catch-up, joint configuration, leader crash, final configuration과 removed-node fencing
- `unsafe-disjoint-switch`: quorum 교차 없이 `{A,B,C}`에서 `{D,E,F}`로 직접 전환
- `unsafe-promote-before-catchup`: committed prefix보다 뒤처진 D를 voter로 조기 승격

## 작업

각 event 뒤 다음 상태를 기록합니다.

```text
active configuration phase
old/new voter sets
각 node match_index와 role
configuration log index와 commit 여부
election에 필요한 old/new quorum
write authority와 removed-node fence epoch
```

다음을 판정합니다.

1. D가 voter가 되기 전 만족해야 하는 catch-up frontier는 무엇입니까?
2. joint phase에서 election과 commit에 필요한 old/new quorum은 무엇입니까?
3. leader A crash 뒤 B가 election을 이길 수 있는 vote 집합은 무엇입니까?
4. final configuration을 어떤 quorum rule로 commit합니까?
5. restart한 A의 stale write를 어느 state boundary에서 거절합니까?
6. disjoint direct switch와 premature promotion이 어떤 safety property를 위협합니까?

## 보존할 불변식

- committed configuration transition의 decision quorum은 이전 configuration의 decision과 교차합니다.
- learner는 committed prefix를 따라잡기 전 voter quorum에 포함되지 않습니다.
- joint phase의 election과 commit은 old·new 각각의 quorum을 만족합니다.
- final configuration이 commit되기 전 old configuration을 제거하지 않습니다.
- removed node의 stale term·configuration epoch write는 storage boundary에서 거절합니다.
- crash 뒤 configuration phase와 log entry를 durable state에서 복원합니다.

## 대표 오답

- metadata의 node 목록을 한 번에 교체하고 log ordering을 생략합니다.
- snapshot copy 시작을 catch-up 완료로 간주합니다.
- joint phase에서 old 또는 new 한쪽 quorum만으로 leader를 선출합니다.
- final configuration entry가 commit되기 전에 old voter를 fencing합니다.
- removed node의 client redirect만 믿고 storage write epoch를 검사하지 않습니다.

## 완료 조건

- 세 scenario의 configuration·quorum·frontier 표를 제출합니다.
- safe scenario에서 A crash 뒤 B election과 final configuration commit을 설명합니다.
- 두 unsafe scenario의 첫 위험 event와 가능한 conflicting decision을 제시합니다.
- restart·retry를 포함한 configuration recovery 계약과 fencing evidence를 작성합니다.

기대 결과는 [`reference.md`](reference.md)와 [`expected.json`](expected.json)에서 비교합니다.
