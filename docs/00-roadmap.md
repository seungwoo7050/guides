# 학습 로드맵

## 목표

이 가이드는 분산 시스템을 제품 이름이나 패턴 모음으로 배우지 않습니다. **어떤 실행을 허용하고, 어떤 상태를 금지하며, 장애 중 무엇을 계속 보장하는가**를 문서·trace·작은 구현으로 고정합니다.

가이드를 마치면 다음 질문에 답할 수 있어야 합니다.

- “노드가 죽었다”는 판단은 어떤 관찰과 시간 가정에 의존합니까?
- 두 사건이 concurrent하다는 것은 단순히 timestamp가 같다는 뜻입니까?
- 안전성은 유지되지만 진행이 멈추는 실행과, 잘못된 값을 commit하는 실행을 어떻게 구분합니까?
- primary-backup, quorum replication과 consensus 기반 state machine replication은 어떤 실패를 다르게 처리합니까?
- `N=3`, `W=2`, `R=2`라는 숫자만으로 linearizable read를 주장할 수 없는 이유는 무엇입니까?
- old leader의 log entry가 새 leader에서 사라질 수 없는 조건은 무엇입니까?
- snapshot을 설치한 뒤 client retry가 중복 적용되지 않도록 어떤 metadata가 함께 이동해야 합니까?
- shard migration 중 stale router와 old owner를 어떻게 fencing합니까?
- 구현이 약속한 consistency를 실제 history에서 어떻게 확인합니까?

## 대상 독자

다음 중 하나에 해당하면 적합합니다.

- 여러 서비스의 장애는 다뤄 봤지만 복제·합의·consistency를 구현 수준에서 배우려는 개발자
- 데이터베이스나 coordination system의 storage·replication 모듈에 기여하려는 개발자
- Raft를 사용했지만 term, commit index, snapshot과 membership 불변식을 정확히 설명하기 어려운 개발자
- 분산 시스템 테스트가 단순한 프로세스 kill과 최종 값 비교에 머물러 있는 개발자
- 논문을 읽어도 시스템 모델과 보장 범위를 구현·검사로 연결하기 어려운 개발자

## 범위와 소유권

이 브랜치가 소유하는 핵심은 다음입니다.

```text
asynchronous message-passing execution
failure model과 partial synchrony
causality, logical clock와 consistent cut
safety·liveness·specification
replication과 consistency model
quorum, version과 anti-entropy
consensus와 Raft replicated log
persistence, client session과 deduplication
snapshot, compaction과 membership change
sharding, routing epoch와 rebalancing
atomic commit와 consensus의 경계
simulation, history checking과 model checking
```

다른 브랜치의 원리를 다시 설명하지 않습니다.

- 네트워크 헤더·TCP 손실·DNS·TLS: [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks)
- process·thread·filesystem·WAL 기초: [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems)
- 관계 transaction·MVCC·단일 DBMS recovery: [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- Outbox·Saga·업무 재조정: [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)

## 권장 읽기 경로

### 최소 추론 경로

분산 시스템 설계 문서를 읽고 보장 범위를 검토하려면 다음을 먼저 읽습니다.

1. [분산 실행 모델과 관찰 경계](01-model-and-time/01-distributed-execution-model.md)
2. [Failure model, 비동기성과 불가능성](01-model-and-time/02-failure-models-and-impossibility.md)
3. [사건 순서, causality와 logical clock](01-model-and-time/03-causality-and-logical-clocks.md)
4. [Safety, liveness와 명세](01-model-and-time/04-safety-liveness-and-specification.md)
5. [Consistency model과 history](02-replication-and-consistency/02-consistency-models-and-histories.md)

이 경로를 마치면 설계의 가정을 먼저 적고, 잘못된 상태와 진행 실패를 분리해 검토할 수 있습니다.

### 복제와 수렴 경로

복제 저장소, cache나 metadata service의 상태 수렴을 다룰 때 읽습니다.

1. 최소 추론 경로
2. [복제와 결정적 상태 기계](02-replication-and-consistency/01-replication-and-state-machines.md)
3. [Quorum, version과 읽기·쓰기 경로](02-replication-and-consistency/03-quorums-versions-and-read-write-paths.md)
4. [Anti-entropy, conflict와 eventual convergence](02-replication-and-consistency/04-anti-entropy-and-convergence.md)

이 경로는 leaderless 또는 weakly consistent 설계의 장점과 남는 책임을 다룹니다.

### Consensus와 coordination 경로

replicated log, metadata store와 leader 기반 state machine을 구현할 때 읽습니다.

1. 최소 추론 경로
2. [복제와 결정적 상태 기계](02-replication-and-consistency/01-replication-and-state-machines.md)
3. [Consensus와 leader election](03-consensus-and-membership/01-consensus-and-leader-election.md)
4. [Raft log replication과 commit](03-consensus-and-membership/02-raft-log-replication-and-commit.md)
5. [영속 상태, client session과 재시도](03-consensus-and-membership/03-persistence-client-sessions-and-recovery.md)
6. [Snapshot, compaction과 membership 변경](03-consensus-and-membership/04-snapshots-compaction-and-membership.md)
7. [Failure detector, lease와 시간 가정](03-consensus-and-membership/05-failure-detectors-leases-and-time.md)

### 분할 저장소 경로

하나의 consensus group을 여러 shard로 확장할 때 읽습니다.

1. Consensus와 coordination 경로
2. [Sharding, routing과 rebalancing](04-partitioning-and-atomicity/01-sharding-routing-and-rebalancing.md)
3. [Atomic commit, consensus와 transaction](04-partitioning-and-atomicity/02-atomic-commit-and-distributed-transactions.md)
4. [Secondary index와 cross-shard query](04-partitioning-and-atomicity/03-secondary-indexes-and-cross-shard-queries.md)
5. [Global snapshot과 checkpoint](04-partitioning-and-atomicity/04-global-snapshots-and-checkpointing.md)

### 검증 경로

protocol 구현이나 production issue를 조사할 때 읽습니다.

1. [결정적 시뮬레이션](05-validation/01-deterministic-simulation.md)
2. [History와 linearizability 검사](05-validation/02-history-and-linearizability-checking.md)
3. [Model checking과 불변식](05-validation/03-model-checking-and-invariants.md)
4. [Fault injection과 성능 주장](05-validation/04-fault-injection-and-performance-evidence.md)
5. [통합 과제](06-capstone.md)

## 문서와 실습 대응

| 문서 | 실습 |
|---|---|
| 분산 실행 모델·causality | [causality trace](../exercises/01-model-and-time/01-causality-trace/README.md) |
| failure model·불가능성 | [failure model](../exercises/01-model-and-time/02-failure-model/README.md) |
| consistency model | [consistency history](../exercises/02-replication-and-consistency/01-consistency-history/README.md) |
| quorum과 version | [quorum register](../exercises/02-replication-and-consistency/02-quorum-register/README.md) |
| leader election | [election trace](../exercises/03-consensus-and-membership/01-election-trace/README.md) |
| log replication | [log reconciliation](../exercises/03-consensus-and-membership/02-log-reconciliation/README.md) |
| client retry·snapshot | [client session](../exercises/03-consensus-and-membership/03-client-session/README.md) |
| sharding·rebalancing | [shard rebalance](../exercises/04-partitioning-and-atomicity/01-shard-rebalance/README.md) |
| atomic commit | [atomic commit](../exercises/04-partitioning-and-atomicity/02-atomic-commit/README.md) |
| linearizability | [history checking](../exercises/05-validation/01-linearizability/README.md) |
| 결정적 simulation | [simulation plan](../exercises/05-validation/02-simulation-plan/README.md) |
| 전체 과정 | [replicated key-value store](06-capstone.md) |

## 실습 방법

### Trace 실습

1. 초기 상태와 허용 event를 읽습니다.
2. 각 node의 local state와 전송 중 message를 표로 기록합니다.
3. event 적용 전후의 invariant를 확인합니다.
4. 위반이 생긴 첫 event를 찾습니다.
5. 동일 결과를 더 짧은 trace로 만들 수 있는지 줄입니다.

### 구현 실습

1. sequential specification을 먼저 작성합니다.
2. public API와 storage boundary를 고정합니다.
3. virtual time과 결정적 network를 사용합니다.
4. 정상 실행보다 crash·delay·duplicate·reorder부터 fixture로 만듭니다.
5. safety 검사가 통과한 뒤 liveness와 성능을 확인합니다.

### 논문 읽기

논문의 결론만 요약하지 않습니다. [1차 자료 지도](../reference/primary-sources.md)를 사용해 다음을 기록합니다.

- 시스템 모델과 장애 가정
- 제공하는 safety와 liveness
- 복제·commit·recovery의 핵심 상태
- 구현에서 추가된 가정
- 논문이 다루지 않는 운영 문제

## 완료 기준

다음 산출물을 만들 수 있으면 가이드의 목표를 달성한 것입니다.

- 분산 알고리즘의 system model과 failure model
- node·message·timer·disk event를 포함한 상태 전이표
- safety invariant와 liveness 조건
- consistency model을 판정하는 history fixture
- quorum·version·read repair 설계표
- Raft term·vote·log·commit·apply trace
- crash 전후 영속 상태 목록
- client retry와 중복 제거 session 계약
- snapshot·membership 변경 failure matrix
- shard ownership과 routing epoch 전이표
- atomic commit coordinator recovery 기록
- deterministic fault schedule과 최소 위반 trace
- capstone의 반복 가능한 전체 검증 보고서
