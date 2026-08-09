# 선택 경로: Paxos, Viewstamped Replication과 다른 consensus family

## 목적

Raft 구현을 기준점으로 삼되 consensus를 Raft API와 동일시하지 않습니다. 서로 다른 protocol이 proposal number, view, ballot, quorum와 log recovery를 어떻게 표현하는지 비교합니다.

## 비교 질문

| 질문 | 확인할 상태 |
|---|---|
| leader 또는 proposer 권한 | term, view, ballot |
| 이전 결정 보존 | accepted value, log prefix, quorum evidence |
| 새 leader recovery | prepare/view-change/election 수집 상태 |
| commit 판단 | quorum certificate 또는 match progress |
| reconfiguration | overlapping quorum과 configuration order |
| client retry | request identity와 replicated result |
| liveness | leader stability와 timing assumption |

## 읽기 순서

1. Paxos Made Simple 또는 정확한 Paxos presentation
2. Multi-Paxos의 stable leader와 repeated instance
3. Viewstamped Replication의 view change
4. Raft의 election restriction과 log repair
5. flexible quorum·EPaxos 같은 확장 중 하나

## 실습

같은 3-node log trace를 각 family의 용어로 다시 씁니다.

- 어떤 evidence가 새 leader의 safe prefix를 정합니까?
- message가 delayed·duplicated되면 어떤 number가 stale state를 거릅니까?
- current leader가 아닌 participant가 client request를 어떻게 처리합니까?
- 어떤 state가 durable해야 합니까?

목적은 모든 protocol을 구현하는 것이 아니라 **상태와 proof obligation을 공통 언어로 읽는 능력**입니다.
