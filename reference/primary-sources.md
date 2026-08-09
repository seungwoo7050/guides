# 1차 자료 지도

이 문서는 본문 개념을 원 논문과 공식 저자·연구기관 자료에서 확인하는 순서를 정리합니다. 자료의 결론을 현재 구현의 검증 결과로 대신하지 않고 **system model, failure·storage·time 가정, safety·liveness와 구현 gap**을 기록합니다.

## 자료 사용 원칙

- 논문 제목, 저자와 판본을 먼저 기록합니다.
- DOI, 학회, 저자 또는 소속 연구기관이 제공하는 원문을 우선합니다.
- survey·강의·blog는 탐색에는 사용할 수 있지만 원 논문의 보장 범위를 대체하지 않습니다.
- 논문의 theorem이 현재 starter, 선택한 read protocol 또는 fault adapter에 그대로 적용되는지 별도로 확인합니다.
- 논문이 다루지 않은 durability, corruption, reconfiguration, client retry와 운영 조건을 자동으로 보장된 것으로 확장하지 않습니다.

## 시간, causality와 global state

### Leslie Lamport, “Time, Clocks, and the Ordering of Events in a Distributed System”

- 공식 자료: [Microsoft Research publication](https://www.microsoft.com/en-us/research/publication/time-clocks-ordering-events-distributed-system/)
- 확인할 것: happened-before, logical clock의 단방향 보장, partial order와 임의로 확장한 total order의 차이
- 적용 한계: Lamport timestamp의 대소만으로 causality의 역방향을 추론하지 않습니다.
- 연결 문서: [causality와 logical clock](../docs/01-model-and-time/03-causality-and-logical-clocks.md)

### K. Mani Chandy, Leslie Lamport, “Distributed Snapshots: Determining Global States of Distributed Systems”

- 저자 원문: [Lamport-hosted paper PDF](https://lamport.azurewebsites.net/pubs/chandy.pdf)
- 확인할 것: process state, channel state, marker 규칙, FIFO channel 가정과 consistent global state
- 적용 한계: arbitrary non-FIFO transport나 snapshot을 durable checkpoint로 게시하는 절차까지 자동으로 보장하지 않습니다.
- 연결 문서: [global snapshot](../docs/04-partitioning-and-atomicity/04-global-snapshots-and-checkpointing.md)

## 비동기성, partial synchrony와 failure detector

### Michael J. Fischer, Nancy A. Lynch, Michael S. Paterson, “Impossibility of Distributed Consensus with One Faulty Process”

- 연구기관 원문: [MIT-hosted JACM PDF](https://groups.csail.mit.edu/tds/papers/Lynch/jacm85.pdf)
- 확인할 것: 완전 비동기 message-passing model, deterministic protocol, 한 crash 가능성과 termination 제한
- 적용 한계: safety 불가능성이나 모든 실용 consensus의 불가능성을 주장하는 논문으로 읽지 않습니다. randomization·failure detector·partial synchrony는 별도 가정입니다.
- 연결 문서: [failure model과 불가능성](../docs/01-model-and-time/02-failure-models-and-impossibility.md)

### Cynthia Dwork, Nancy Lynch, Larry Stockmeyer, “Consensus in the Presence of Partial Synchrony”

- 연구기관 원문: [MIT-hosted JACM PDF](https://groups.csail.mit.edu/tds/papers/Lynch/jacm88.pdf)
- 확인할 것: 알려지지 않은 bound와 unknown global stabilization time, safety와 termination 조건, failure model별 resilience
- 적용 한계: simulator에서 임의 timeout 하나를 선택했다고 partial synchrony 가정이 증명되는 것은 아닙니다.
- 연결 문서: [failure model과 불가능성](../docs/01-model-and-time/02-failure-models-and-impossibility.md), [failure detector·lease](../docs/03-consensus-and-membership/05-failure-detectors-leases-and-time.md)

### Tushar Deepak Chandra, Sam Toueg, “Unreliable Failure Detectors for Reliable Distributed Systems”

- 기관 자료: [Cornell eCommons record and paper](https://ecommons.cornell.edu/items/7948ff49-7263-49f8-a29b-d062e7cbb240)
- 확인할 것: completeness·accuracy, failure detector class, asynchronous crash-failure model과 consensus·atomic broadcast 관계
- 적용 한계: heartbeat timeout을 실제 crash 사실이나 lease fencing으로 곧바로 바꾸지 않습니다.
- 연결 문서: [failure detector·lease](../docs/03-consensus-and-membership/05-failure-detectors-leases-and-time.md)

## Consistency와 availability

### Maurice P. Herlihy, Jeannette M. Wing, “Linearizability: A Correctness Condition for Concurrent Objects”

- 출판 원문: [ACM Digital Library DOI](https://doi.org/10.1145/78969.78972)
- 확인할 것: invocation·response, real-time order, locality와 sequential object specification
- 적용 한계: final state 일치나 completed operation만 무조건 버리는 checker는 이 정의를 구현하지 못합니다.
- 연결 문서: [consistency model](../docs/02-replication-and-consistency/02-consistency-models-and-histories.md), [history 검사](../docs/05-validation/02-history-and-linearizability-checking.md)

### Seth Gilbert, Nancy Lynch, “Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services”

- 출판 원문: [ACM Digital Library DOI](https://doi.org/10.1145/564585.564601)
- 확인할 것: 논문이 정의한 atomic consistency, availability와 partition execution
- 적용 한계: latency·평상시 운영 trade-off 전체를 ‘CAP 중 둘’이라는 구호로 환원하지 않습니다.
- 연결 문서: [failure model과 불가능성](../docs/01-model-and-time/02-failure-models-and-impossibility.md)

## Consensus와 replicated log

### Diego Ongaro, John Ousterhout, “In Search of an Understandable Consensus Algorithm”

- 저자 프로젝트: [Raft publications](https://raft.github.io/)
- 확인할 것: election safety, log matching, leader completeness, state machine safety와 current-term commit rule
- 적용 한계: 논문의 core safety argument만으로 storage adapter, client session, read protocol과 snapshot publication이 완성됐다고 보지 않습니다.
- 연결 문서: [leader election](../docs/03-consensus-and-membership/01-consensus-and-leader-election.md), [log replication](../docs/03-consensus-and-membership/02-raft-log-replication-and-commit.md)

### Diego Ongaro, “Consensus: Bridging Theory and Practice”

- 공식 진입점: [Raft project의 dissertation 링크](https://raft.github.io/)
- 확인할 것: client interaction, log compaction, membership change, TLA+ specification과 구현 판단
- 적용 한계: dissertation의 membership 방식과 다른 reconfiguration protocol을 섞을 때 quorum 전제와 state transition을 다시 명세합니다.
- 연결 문서: [snapshot과 membership](../docs/03-consensus-and-membership/04-snapshots-compaction-and-membership.md)

### Leslie Lamport, “Paxos Made Simple” 및 Paxos 자료

- 저자 자료: [Lamport publications](https://lamport.azurewebsites.net/pubs/pubs.html)
- 확인할 것: proposal number, acceptor durable state, quorum intersection과 chosen value 보존
- 적용 한계: Paxos terminology를 Raft field에 이름만 대응시키지 말고 각 protocol의 transition과 recovery 계약을 비교합니다.
- 연결 문서: [consensus family 선택 경로](../docs/90-optional-paths/02-consensus-families.md)

### Barbara Liskov, James Cowling, “Viewstamped Replication Revisited”

- 연구기관 원문: [MIT CSAIL PDF](https://pmg.csail.mit.edu/papers/vr-revisited.pdf)
- 확인할 것: view change, operation number, client request 처리, replica recovery와 reconfiguration
- 적용 한계: Raft와 비슷한 이름의 상태를 동일한 commit·view-change 규칙으로 간주하지 않습니다.
- 연결 문서: [consensus family 선택 경로](../docs/90-optional-paths/02-consensus-families.md)

## Leaderless replication과 분할 저장소

### Giuseppe DeCandia et al., “Dynamo: Amazon's Highly Available Key-value Store”

- 공식 자료: [Amazon Science](https://www.amazon.science/publications/dynamo-amazons-highly-available-key-value-store)
- 확인할 것: consistent hashing, vector clock, sloppy quorum, hinted handoff, anti-entropy와 application conflict resolution
- 적용 한계: `R + W > N`만으로 linearizability를 주장하거나 Dynamo의 availability 선택을 모든 workload에 일반화하지 않습니다.
- 연결 문서: [quorum](../docs/02-replication-and-consistency/03-quorums-versions-and-read-write-paths.md), [anti-entropy](../docs/02-replication-and-consistency/04-anti-entropy-and-convergence.md)

### James C. Corbett et al., “Spanner: Google's Globally-Distributed Database”

- 공식 자료: [Google Research](https://research.google/pubs/spanner-googles-globally-distributed-database-2/)
- 확인할 것: Paxos-replicated data, external consistency, TrueTime uncertainty와 read-only transaction
- 적용 한계: 일반 NTP wall clock이나 임의 lease가 TrueTime의 uncertainty·commit-wait 계약을 제공한다고 보지 않습니다.
- 연결 문서: [logical clock과 physical time](../docs/01-model-and-time/03-causality-and-logical-clocks.md), [atomic transaction](../docs/04-partitioning-and-atomicity/02-atomic-commit-and-distributed-transactions.md)

### Fay Chang et al., “Bigtable: A Distributed Storage System for Structured Data”

- 공식 자료: [Google Research](https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/)
- 확인할 것: tablet·range partition, metadata hierarchy, split과 storage layout
- 적용 한계: 이 논문만으로 arbitrary shard migration의 fencing·delta catch-up·cutover 안전성이 증명되지는 않습니다.
- 연결 문서: [sharding과 rebalancing](../docs/04-partitioning-and-atomicity/01-sharding-routing-and-rebalancing.md)

## Atomic commit 경계

### Jim Gray, Leslie Lamport, “Consensus on Transaction Commit”

- 공식 자료: [Microsoft Research publication](https://www.microsoft.com/en-us/research/publication/consensus-on-transaction-commit/)
- 확인할 것: transaction commit problem, Two-Phase Commit과 Paxos Commit의 fault-tolerance 차이, participant별 decision state
- 적용 한계: atomic commit은 복제 log의 명령 순서 합의나 transaction isolation 전체를 대신하지 않습니다.
- 연결 문서: [atomic commit와 distributed transaction](../docs/04-partitioning-and-atomicity/02-atomic-commit-and-distributed-transactions.md)

## 구현 검증

### Jingyu Zhou et al., “FoundationDB: A Distributed Unbundled Transactional Key Value Store”

- 공식 논문: [FoundationDB-hosted SIGMOD paper PDF](https://www.foundationdb.org/files/fdb-paper.pdf)
- 확인할 것: deterministic simulation을 개발·검증 과정에 통합하는 방식, injected fault와 simulation architecture
- 적용 한계: FoundationDB의 장기간 simulator 경험을 이 저장소의 작은 fixed schedule 통과와 동등하게 표현하지 않습니다.
- 연결 문서: [결정적 simulation](../docs/05-validation/01-deterministic-simulation.md)

### Leslie Lamport, TLA+

- 공식 자료: [TLA+ homepage](https://lamport.azurewebsites.net/tla/tla.html)
- 확인할 것: state-machine specification, invariant, liveness와 fairness
- 적용 한계: TLC의 bounded exploration 결과와 unbounded proof를 구분하고 실제 code refinement gap을 기록합니다.
- 연결 문서: [model checking](../docs/05-validation/03-model-checking-and-invariants.md), [TLA+ 선택 경로](../docs/90-optional-paths/01-tla-plus-and-proof-tools.md)

## 보조 탐색 지도

[Jepsen consistency models](https://jepsen.io/consistency/models)는 consistency 용어와 관계를 탐색하는 보조 자료입니다. 원 논문, 실제 history, checker configuration과 독립적인 증거 없이 이 페이지의 model 이름만 인용해 구현 보장을 주장하지 않습니다.

## 논문 기록 양식

```text
자료와 판본:
문제:
system model:
network·failure·storage·time 가정:
safety:
liveness와 필요한 fairness·time 조건:
핵심 protocol state:
commit 또는 decision rule:
recovery·reconfiguration:
논문의 검증 방법:
현재 본문·starter와 다른 점:
현재 evidence가 실제로 확인한 범위:
production에서 추가로 필요한 것:
```
