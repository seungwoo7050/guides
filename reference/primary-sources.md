# 1차 자료 지도

이 문서는 본문 개념을 더 깊게 확인할 때 읽을 논문과 공식 자료의 순서를 정리합니다. 각 자료의 결론보다 **시스템 모델, failure 가정, safety·liveness와 구현 gap**을 기록합니다.

## 시간과 causality

### Leslie Lamport, “Time, Clocks, and the Ordering of Events in a Distributed System”

- 공식 자료: [Microsoft Research publication](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/)
- 확인할 것: happened-before, logical clock의 단방향 보장, partial order와 total order의 차이
- 연결 문서: [causality와 logical clock](../docs/01-model-and-time/03-causality-and-logical-clocks.md)

### K. Mani Chandy, Leslie Lamport, “Distributed Snapshots: Determining Global States of Distributed Systems”

- 공식 자료: [Lamport publications](https://lamport.azurewebsites.net/pubs/pubs.html)
- 확인할 것: process·channel state, FIFO channel 가정, consistent global state
- 연결 문서: [global snapshot](../docs/04-partitioning-and-atomicity/04-global-snapshots-and-checkpointing.md)

## 불가능성과 consistency

### Fischer, Lynch, Paterson, “Impossibility of Distributed Consensus with One Faulty Process”

- 공개 논문: [MIT CSAIL PDF](https://groups.csail.mit.edu/tds/papers/Lynch/jacm85.pdf)
- 확인할 것: 완전 비동기 model, deterministic protocol, 한 crash 가능성, termination 제한
- 연결 문서: [failure model과 불가능성](../docs/01-model-and-time/02-failure-models-and-impossibility.md)

### Herlihy, Wing, “Linearizability: A Correctness Condition for Concurrent Objects”

- DOI: [ACM Digital Library](https://doi.org/10.1145/78969.78972)
- 확인할 것: invocation·response, real-time order, locality, sequential object specification
- 연결 문서: [consistency model](../docs/02-replication-and-consistency/02-consistency-models-and-histories.md), [history 검사](../docs/05-validation/02-history-and-linearizability-checking.md)

### Gilbert, Lynch, “Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services”

- 출판 정보: [ACM DOI](https://doi.org/10.1145/564585.564601)
- 확인할 것: atomic consistency와 availability의 정의, network partition execution
- 연결 문서: [failure model과 불가능성](../docs/01-model-and-time/02-failure-models-and-impossibility.md)

## Consensus와 replicated log

### Ongaro, Ousterhout, “In Search of an Understandable Consensus Algorithm”

- 공식 자료: [Raft project](https://raft.github.io/)
- 확인할 것: election safety, log matching, leader completeness, state machine safety, current-term commit rule
- 연결 문서: [leader election](../docs/03-consensus-and-membership/01-consensus-and-leader-election.md), [log replication](../docs/03-consensus-and-membership/02-raft-log-replication-and-commit.md)

### Diego Ongaro, “Consensus: Bridging Theory and Practice”

- 공식 자료: [Raft project의 dissertation 링크](https://raft.github.io/)
- 확인할 것: membership 변경, client interaction, TLA+ specification, implementation detail
- 연결 문서: [snapshot과 membership](../docs/03-consensus-and-membership/04-snapshots-compaction-and-membership.md)

### Lamport, “Paxos Made Simple” 및 관련 Paxos 자료

- 공식 자료: [Lamport publications](https://lamport.azurewebsites.net/pubs/pubs.html)
- 확인할 것: proposal number, acceptor state, quorum intersection과 chosen value preservation
- 연결 문서: [consensus family 선택 경로](../docs/90-optional-paths/02-consensus-families.md)

### Liskov, Cowling, “Viewstamped Replication Revisited”

- 공식 저자 자료를 사용해 view change와 log recovery를 Raft와 비교합니다.
- 연결 문서: [consensus family 선택 경로](../docs/90-optional-paths/02-consensus-families.md)

## Leaderless replication과 대규모 저장소

### DeCandia et al., “Dynamo: Amazon's Highly Available Key-value Store”

- 공식 자료: [Amazon Science](https://www.amazon.science/publications/dynamo-amazons-highly-available-key-value-store)
- 확인할 것: consistent hashing, vector clock, sloppy quorum, hinted handoff, anti-entropy, application conflict resolution
- 연결 문서: [quorum](../docs/02-replication-and-consistency/03-quorums-versions-and-read-write-paths.md), [anti-entropy](../docs/02-replication-and-consistency/04-anti-entropy-and-convergence.md)

### Corbett et al., “Spanner: Google's Globally-Distributed Database”

- 공식 자료: [Google Research](https://research.google/pubs/spanner-googles-globally-distributed-database-2/)
- 확인할 것: synchronous replication, external consistency, clock uncertainty와 read-only transaction
- 연결 문서: [logical clock과 physical time](../docs/01-model-and-time/03-causality-and-logical-clocks.md), [atomic transaction](../docs/04-partitioning-and-atomicity/02-atomic-commit-and-distributed-transactions.md)

### Chang et al., “Bigtable: A Distributed Storage System for Structured Data”

- 공식 자료: [Google Research](https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/)
- 확인할 것: tablet/range partition, metadata, split과 storage layout
- 연결 문서: [sharding과 rebalancing](../docs/04-partitioning-and-atomicity/01-sharding-routing-and-rebalancing.md)

## 구현 검증

### FoundationDB: A Distributed, Unbundled, Transactional Key Value Store

- 공식 소개: [FoundationDB paper announcement](https://www.foundationdb.org/blog/fdb-paper/)
- 확인할 것: deterministic simulation, fault injection을 release 과정에 통합하는 방식
- 연결 문서: [결정적 simulation](../docs/05-validation/01-deterministic-simulation.md)

### Leslie Lamport, TLA+

- 공식 자료: [TLA+ homepage](https://lamport.azurewebsites.net/tla/tla.html)
- 확인할 것: state machine specification, invariant, liveness와 fairness
- 연결 문서: [model checking](../docs/05-validation/03-model-checking-and-invariants.md), [TLA+ 선택 경로](../docs/90-optional-paths/01-tla-plus-and-proof-tools.md)

### Jepsen consistency model reference

- 자료: [Jepsen consistency models](https://jepsen.io/consistency/models)
- 확인할 것: consistency hierarchy와 history terminology
- 이 자료는 1차 논문을 대체하지 않고 model 사이 관계를 탐색하는 참고 지도입니다.

## 논문 기록 양식

```text
자료:
문제:
시스템 모델:
network·failure·storage 가정:
safety:
liveness와 필요한 조건:
핵심 protocol state:
commit 또는 decision rule:
recovery:
검증 방법:
본문과 다른 점:
production에서 추가로 필요한 것:
```
