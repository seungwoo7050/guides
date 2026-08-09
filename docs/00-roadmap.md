# 학습 로드맵

## 목표

이 가이드는 분산 시스템을 제품 이름이나 패턴 모음으로 배우지 않습니다. **어떤 실행을 허용하고, 어떤 상태를 금지하며, 장애 중 무엇을 계속 보장하는가**를 system model·trace·작은 구현과 반례로 고정합니다.

완료 뒤에는 다음 세 가지 정본 종료 능력을 근거와 함께 보여야 합니다.

1. 복제 상태 기계의 safety·liveness를 설명합니다.
2. partition과 leader 교체를 재현합니다.
3. 작은 분산 저장소를 구현·검증합니다.

## 대상 독자

다음 중 하나에 해당하면 적합합니다.

- 여러 서비스의 부분 실패는 다뤄 봤지만 복제·합의·consistency를 구현 수준에서 배우려는 개발자
- 데이터베이스나 coordination system의 storage·replication 모듈에 기여하려는 개발자
- Raft를 사용했지만 term, commit index, snapshot과 membership 불변식을 설명하기 어려운 개발자
- 분산 시스템 테스트를 process kill과 최종 값 비교에서 결정적 schedule·history 검사로 확장하려는 개발자

## 정본 범위와 관계

`distributed-systems`는 `specialization` 브랜치이며 다음 다섯 영역을 소유합니다.

```text
분산 시간·순서·failure detector
복제와 일관성 모델
leader election·합의·replicated log
snapshot·membership change·sharding
결정적 장애 주입과 history 검증
```

다음은 명시적인 비소유 범위입니다.

- 서비스 업무 saga 재교육: [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services)
- DBMS 단일 노드 내부 전체: [`database-systems`](https://github.com/seungwoo7050/guides/tree/database-systems)
- Kubernetes 운영: [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering)
- 특정 클라우드 제품: 이 가이드의 완료 조건이 아님

정본 관계는 다음과 같습니다.

| 필드 | 브랜치 |
|---|---|
| `requires` | `operating-systems`, `computer-networks`, `database-systems` |
| `recommends` | `algorithms`, `distributed-services` |
| `connects` | `data-engineering`, `platform-engineering` |
| `continues_to` | 없음 |

필수 선행에서는 process·동시성·crash recovery, TCP·timeout·partition 증거, transaction·WAL·단일 노드 recovery를 다시 처음부터 가르치지 않습니다. 권장 선행의 불변식·반례 설계와 서비스 업무 상태 수렴도 필요한 접점만 링크합니다.

## 언어와 실행 환경

카탈로그의 `distributed-systems` 트랙은 C·C++·Java·Python 중 한 언어를 `required_any`로 요구하며 `default` 선형 경로는 C를 대표합니다. 이 저장소의 배포된 예제·starter·public test·검증 도구는 Python 3.12 이상 표준 라이브러리를 사용합니다.

다른 언어로 protocol core를 구현할 때는 다음을 별도 근거로 제공합니다.

- 제공된 Python public API와 동등한 adapter 또는 명시적인 API 대응표
- 같은 정상·경계·실패 schedule과 invariant 결과
- [trace schema](../reference/trace-schema.md)에 맞춘 artifact
- Python test가 직접 판정하지 못하는 부분의 사람 검토 기록

저장소 자체 검증은 구현 언어와 관계없이 Python 3.12가 필요합니다.

## 권장 읽기 경로

### 최소 추론 경로

설계 문서의 보장 범위를 검토하려면 다음을 먼저 읽습니다.

1. [분산 실행 모델과 관찰 경계](01-model-and-time/01-distributed-execution-model.md)
2. [Failure model, 비동기성과 불가능성](01-model-and-time/02-failure-models-and-impossibility.md)
3. [사건 순서, causality와 logical clock](01-model-and-time/03-causality-and-logical-clocks.md)
4. [Safety, liveness와 명세](01-model-and-time/04-safety-liveness-and-specification.md)
5. [Consistency model과 history](02-replication-and-consistency/02-consistency-models-and-histories.md)

이 경로를 마치면 failure·time 가정을 먼저 적고 잘못된 상태와 진행 실패를 분리해 검토할 수 있습니다.

### 복제와 수렴 경로

복제 저장소, cache나 metadata service의 상태 수렴을 다룰 때 읽습니다.

1. 최소 추론 경로
2. [복제와 결정적 상태 기계](02-replication-and-consistency/01-replication-and-state-machines.md)
3. [Quorum, version과 읽기·쓰기 경로](02-replication-and-consistency/03-quorums-versions-and-read-write-paths.md)
4. [Anti-entropy, conflict와 eventual convergence](02-replication-and-consistency/04-anti-entropy-and-convergence.md)

### Consensus와 coordination 경로

replicated log, metadata store와 leader 기반 상태 기계를 구현할 때 읽습니다.

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

atomic commit·secondary index·global snapshot은 sharding이 만드는 cross-group 경계를 검토하기 위한 연결 주제입니다. 단일 DBMS transaction 내부 전체를 다시 소유하지 않습니다.

### 검증 경로

protocol 구현 또는 장애를 조사할 때 읽습니다.

1. [결정적 시뮬레이션](05-validation/01-deterministic-simulation.md)
2. [History와 linearizability 검사](05-validation/02-history-and-linearizability-checking.md)
3. [Model checking과 불변식](05-validation/03-model-checking-and-invariants.md)
4. [Fault injection과 성능 주장](05-validation/04-fault-injection-and-performance-evidence.md)
5. [통합 과제](06-capstone.md)

실제 host·network·storage fault 명령은 자동 학습 경로에 포함되지 않습니다. 운영 실험으로 확장하기 전에 [실습 안전·정리 계약](../reference/lab-safety.md)을 적용합니다.

## 소유 범위에서 종료 능력까지

아래 표가 핵심 추적 경로입니다. 세부 제출물과 사람 검토 질문은 [완료 근거 루브릭](../reference/completion-evidence-rubric.md)에 있습니다.

| `owns` | 핵심 문서 | 단계 실습·대표 실패 | capstone 누적 근거 | 연결되는 종료 능력 |
|---|---|---|---|---|
| 분산 시간·순서·failure detector | Part 1, failure detector 문서 | causality trace, failure model, failure detector의 false suspicion·lease/fencing 반례 | Milestone 0·1·7의 model, partition과 leader-change schedule | safety·liveness 설명, partition·leader 교체 재현 |
| 복제와 일관성 모델 | Part 2 | consistency history, quorum register, anti-entropy의 sibling·tombstone resurrection | Milestone 2·3·5·7의 replicated state와 history 결과 | safety·liveness 설명, 작은 저장소 구현·검증 |
| leader election·합의·replicated log | Part 3의 election·log·persistence | election trace, log reconciliation, client session, stale candidate·conflicting suffix | Milestone 1–5·7의 term·vote·log·commit·retry evidence | 세 종료 능력 모두 |
| snapshot·membership change·sharding | snapshot/membership 문서, Part 4 | client session, membership change, shard rebalance의 incomplete snapshot·disjoint quorum·stale epoch | Milestone 6과 필수 reconfiguration·sharding dossier; 구현 확장은 선택 | safety·liveness 설명, 작은 저장소 구현·검증 |
| 결정적 장애 주입과 history 검증 | Part 5 | linearizability, simulation plan, known violation·pending operation | Milestone 7의 replayable schedule, checker, 최소 counterexample와 manifest | 세 종료 능력 모두 |

membership와 sharding의 실제 코드 확장은 선택이지만, 해당 소유 범위를 capstone에서 생략할 수는 없습니다. learner catch-up·configuration 전이·removed-node fencing과 shard snapshot·delta·fence·cutover·stale-router 거절을 현재 capstone 상태에 적용한 설계·trace dossier는 필수입니다.

## 문서와 단계 실습 대응

| 문서 주제 | 실습 |
|---|---|
| 실행 모델·causality | [causality trace](../exercises/01-model-and-time/01-causality-trace/README.md) |
| failure model·불가능성 | [failure model](../exercises/01-model-and-time/02-failure-model/README.md) |
| failure detector·lease·fencing | [failure detector](../exercises/01-model-and-time/03-failure-detector/README.md) |
| consistency model | [consistency history](../exercises/02-replication-and-consistency/01-consistency-history/README.md) |
| quorum과 version | [quorum register](../exercises/02-replication-and-consistency/02-quorum-register/README.md) |
| anti-entropy·tombstone repair | [anti-entropy](../exercises/02-replication-and-consistency/03-anti-entropy/README.md) |
| leader election | [election trace](../exercises/03-consensus-and-membership/01-election-trace/README.md) |
| log replication | [log reconciliation](../exercises/03-consensus-and-membership/02-log-reconciliation/README.md) |
| client retry·snapshot | [client session](../exercises/03-consensus-and-membership/03-client-session/README.md) |
| joint quorum·learner fencing | [membership change](../exercises/03-consensus-and-membership/04-membership-change/README.md) |
| sharding·rebalancing | [shard rebalance](../exercises/04-partitioning-and-atomicity/01-shard-rebalance/README.md) |
| atomic commit 경계 | [atomic commit](../exercises/04-partitioning-and-atomicity/02-atomic-commit/README.md) |
| linearizability | [history checking](../exercises/05-validation/01-linearizability/README.md) |
| 결정적 simulation | [simulation plan](../exercises/05-validation/02-simulation-plan/README.md) |
| 전체 과정 | [replicated key-value store](06-capstone.md) |

## 실습 방법

### Trace 실습

1. 초기 상태와 허용 event를 읽습니다.
2. 각 participant의 local state와 전송 중 message를 기록합니다.
3. event 적용 전후의 invariant를 확인합니다.
4. decision 또는 첫 위반 event를 찾습니다.
5. 같은 결과를 보존하는 더 짧은 trace로 줄입니다.
6. 자동화가 판단하지 못하는 가정과 비보장 범위를 적습니다.

### 구현 실습

1. sequential specification과 public API를 먼저 고정합니다.
2. virtual time과 결정적 network로 정상·경계·실패 schedule을 작성합니다.
3. canonical starter와 학습자 workspace를 구분합니다.
4. public test 뒤에도 every-step invariant, history checker와 회귀 schedule을 추가합니다.
5. source·config·seed·schedule identity를 artifact manifest에 남깁니다.

### 논문 읽기

[1차 자료 지도](../reference/primary-sources.md)에서 직접 논문과 공식 자료를 확인하고 다음을 기록합니다.

- 시스템 모델과 장애 가정
- safety와 liveness 및 필요한 fairness·time 조건
- 복제·commit·recovery의 핵심 상태
- 본문 축소 모델과 원문 사이의 차이
- 논문이 증명하지 않는 운영·구현 범위

논문 결론을 현재 구현의 검증 결과로 대신하지 않습니다.

## Capstone 검증의 세 층

1. `make verify`: 문서·fixture·예제·canonical starter를 포함한 **가이드 배포본**의 무결성 검사
2. `CAPSTONE_ROOT=... python3 -m unittest ...`: learner workspace의 공개 API와 초기 milestone 계약 검사
3. learner 추가 검사와 dossier: 전체 fault matrix, history checker, membership·sharding 검토, source identity와 알려진 한계

1이나 2의 통과만으로 세 종료 능력을 완료했다고 판정하지 않습니다. public test가 다루지 않는 상태와 failure는 [완료 근거 루브릭](../reference/completion-evidence-rubric.md)에 따라 사람이 검토합니다.

## 트랙 위치와 선형 경로

`main`에서 이 브랜치를 포함하는 모든 트랙은 다음과 같습니다.

| 트랙 | 위치 | `linear_paths` 확인 결과 |
|---|---|---|
| `distributed-systems` | required | `default`: `git → c → computer-architecture → operating-systems → computer-networks → database-systems → distributed-systems` |
| `data-engineering` | recommended | `default`에는 미포함; 핵심 data-engineering 완료 뒤 선택 |
| `web-backend` | advanced | `default`에는 미포함 |
| `cloud-engineering` | advanced | `default`에는 미포함 |
| `infrastructure-platform` | advanced | `host-platform`, `cloud-platform` 모두 미포함 |
| `cybersecurity` | advanced | `default`에는 미포함 |
| `machine-learning` | advanced | `default`에는 미포함 |
| `database-engineering` | advanced | `internals`, `application-data` 모두 미포함 |
| `game-server` | advanced | `default`에는 미포함 |
| `game-security-anticheat` | advanced | `default`에는 미포함 |

권장·심화 위치는 해당 트랙의 필수 완료 조건이 아닙니다. `continues_to`는 비어 있으며, 이후에는 정본 `connects`인 `data-engineering` 또는 `platform-engineering`과 필요에 따라 연결합니다.

## 완료 판정과 한계

완료하려면 다음을 모두 남깁니다.

- 각 소유 범위의 단계 실습 분석과 대표 실패 근거
- 실행 가능한 작은 복제 저장소
- partition·leader crash/change·response loss·snapshot 경계의 재현 가능한 schedule
- history와 every-step invariant 결과
- membership change와 sharding의 필수 설계·trace dossier
- 최소 한 개의 위반 trace와 수정 뒤 regression
- 사용한 source·runtime·config·seed·schedule identity
- 자동 검사로 증명하지 못한 범위와 사람 검토 답변

자동 검사는 고정 fixture와 실제 실행한 bounded schedule을 확인합니다. 모든 가능한 event order, production filesystem durability, 실제 network·clock, Byzantine fault, Kubernetes·cloud 운영을 증명하지 않습니다. 이 한계를 숨기지 않은 dossier까지 검토해야 정본 종료 능력에 중대한 공백이 없다고 판단할 수 있습니다.
