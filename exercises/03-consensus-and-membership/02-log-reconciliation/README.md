# Log reconciliation 실습

## 목표

Raft leader가 follower의 conflicting suffix를 찾아 제거하고 자신의 log와 일치시키는 과정을 추적합니다. `replicated`, `committed`, `applied`를 구분하고 current-term commit 규칙이 왜 필요한지 확인합니다.

## 입력

[`logs.json`](logs.json)은 두 시나리오를 제공합니다.

- `conflicting-suffix`: follower가 같은 index에 다른 term의 entry를 가지고 있습니다.
- `old-term-majority`: 새 leader의 과거 term entry가 현재 quorum에 복제됐지만 아직 current term entry가 quorum에 복제되지 않았습니다.

## 작업

### Conflicting suffix

각 `AppendEntries` 시도에 대해 다음을 기록합니다.

```text
prevLogIndex | prevLogTerm | 성공 여부 | conflict hint | 다음 nextIndex | follower 최종 log
```

- follower가 어느 index부터 suffix를 제거하는지 표시합니다.
- 이미 일치하는 prefix는 다시 쓰지 않습니다.
- leader의 `nextIndex`와 `matchIndex`가 응답 뒤 어떻게 바뀌는지 적습니다.

### Current-term commit

- 각 replication 상태에서 leader가 올릴 수 있는 `commitIndex`를 계산합니다.
- “현재 quorum에 저장돼 있음”과 “Raft 규칙으로 commit됨”을 구분합니다.
- current term의 no-op 또는 client entry가 commit된 뒤 과거 entry가 함께 commit되는 이유를 설명합니다.

## 보존할 불변식

- 같은 index와 term의 entry를 가진 두 log는 그 index까지 같은 prefix를 가집니다.
- follower는 leader와 충돌하는 entry와 그 뒤 suffix만 제거합니다.
- leader는 자신의 log를 follower 상태에 맞춰 덮어쓰지 않습니다.
- leader는 current term entry에 대해 quorum의 `matchIndex`를 확인한 경우에만 counting rule로 commit index를 전진시킵니다.
- `lastApplied`는 `commitIndex`를 넘지 않습니다.

## 대표 오답

- 첫 실패 응답에 follower log 전체를 지웁니다.
- follower가 더 긴 suffix를 갖고 있다는 이유만으로 그 suffix를 유지합니다.
- `matchIndex`의 중앙값만 보고 entry term을 확인하지 않습니다.
- follower가 entry를 받자마자 모든 노드가 apply했다고 기록합니다.
- client 응답을 commit보다 먼저 보냅니다.

## 완료 조건

- 모든 AppendEntries 시도의 결과와 최종 log를 표로 제출합니다.
- 최소한의 conflict hint를 사용한 경우와 index를 하나씩 줄인 경우의 message 수를 비교합니다.
- old-term entry를 즉시 commit하는 잘못된 rule의 반례를 설명합니다.
- `append → persist → replicate → commit → apply → reply`의 순서를 자신의 storage API에 맞춰 기록합니다.

직접 추적한 뒤 [`reference.md`](reference.md)의 해설과 [`expected.json`](expected.json)의 관측 결과를 비교합니다.
