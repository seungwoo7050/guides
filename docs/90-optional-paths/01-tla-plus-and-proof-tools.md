# 선택 경로: TLA+와 proof 도구

## 목적

본문의 state·transition·invariant를 formal specification으로 옮겨 bounded test보다 넓은 실행을 탐색합니다. 이 경로는 capstone의 필수 구현 언어가 아니며, model과 code 사이의 gap을 문서화하는 연습입니다.

## 권장 순서

1. 단일 register의 sequential specification
2. primary-backup state model
3. leader election만 있는 작은 Raft model
4. log replication과 commit
5. snapshot 또는 membership 중 하나
6. code simulator trace와 model counterexample 변환

## 최소 specification

```text
VARIABLES roles, terms, votes, logs, commitIndex, messages

Init
- 모든 node follower
- term 0
- empty log
- no messages

Next
- Timeout
- RequestVote
- GrantVote
- AppendEntries
- AckAppend
- Crash
- Restart
- DropMessage

Invariants
- ElectionSafety
- LogMatching
- AppliedOnlyCommitted
```

## 검토 항목

- set·sequence·function이 실제 state와 어떻게 대응합니까?
- message를 set으로 두면 duplicate를 표현합니까?
- crash가 volatile state를 어떻게 지웁니까?
- durable state는 restart에 남습니까?
- fairness를 어떤 action에 적용합니까?
- bounded term·log length가 어떤 bug를 놓칠 수 있습니까?

## 산출물

- specification source
- model configuration
- invariant 목록
- 최소 counterexample
- code regression schedule
- model과 implementation mapping 문서

## 주의

formal tool 결과를 production correctness 인증으로 표현하지 않습니다. model이 허용한 failure, 추상화한 storage·network, 검사한 state 범위를 함께 기록합니다.
