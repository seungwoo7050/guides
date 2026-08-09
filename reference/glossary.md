# 용어집

## A

### Anti-entropy

client request와 독립적으로 replica state·version·digest를 비교하고 차이를 복구하는 background protocol입니다.

### Apply

committed command를 application state machine에 반영하는 과정입니다. log append·replication·commit과 구분합니다.

### Atomic commit

여러 participant가 하나의 transaction을 모두 commit하거나 모두 abort하도록 결정하는 문제입니다.

## B

### Ballot / Term / View

consensus protocol에서 leadership 또는 proposal generation을 구분하는 monotonic logical number입니다. 서로 다른 protocol이 다른 이름을 사용합니다.

### Byzantine failure

participant가 protocol을 임의로 위반하거나 거짓 message·state를 만드는 failure model입니다. crash-only protocol이 제공하는 보장 밖입니다.

## C

### Causal consistency

causally related update의 순서를 모든 observer가 보존하고 concurrent update는 서로 다른 순서로 볼 수 있는 consistency model입니다.

### Commit

protocol 규칙상 command가 미래의 legal leader·replica state에서 보존되어야 하는 상태입니다. local log 존재와 다릅니다.

### Consistent cut

포함한 event의 모든 causal predecessor를 포함하는 분산 trace의 절단입니다.

### Consensus

여러 participant가 validity·agreement·integrity를 만족하며 하나의 값 또는 순서에 합의하는 문제입니다. termination은 환경 가정에 의존합니다.

## D

### Deterministic simulation

clock·network·disk·random과 scheduler 선택을 explicit event로 바꿔 같은 fault schedule을 반복하는 검증 방식입니다.

### Durable state

process crash와 restart 뒤에도 남아 protocol promise를 보존해야 하는 state입니다.

## E

### Epoch

configuration, owner 또는 leader generation을 구분하는 monotonic identifier입니다. stale actor를 fencing하는 데 사용합니다.

### Eventual convergence

새 update가 멈추고 repair·communication이 계속되면 replica가 같은 state로 수렴하는 성질입니다.

## F

### Failure detector

다른 participant의 crash 가능성을 의심하는 abstraction입니다. 완전 비동기 환경에서 확정 failure oracle이 아닙니다.

### Fencing token

새 owner가 더 큰 monotonic token을 받고 external resource가 오래된 token의 write를 거절하도록 하는 값입니다.

## H

### Happened-before

같은 process order, message send→receive와 transitivity로 정의되는 causal partial order입니다.

### History

client operation의 invocation과 completion을 포함한 실행 기록입니다. consistency checker의 입력입니다.

## L

### Leader completeness

어떤 term에 commit된 log entry가 이후 모든 leader의 log에 존재하는 Raft safety property입니다.

### Lease

정해진 시간 구간 동안 holder에 권한을 부여하는 계약입니다. clock·pause·renewal 가정과 fencing이 필요합니다.

### Linearizability

operation이 invocation과 response 사이에 원자적으로 실행된 것처럼 보이고 non-overlapping operation의 real-time order를 보존하는 consistency model입니다.

### Liveness

필요한 환경·fairness 조건에서 좋은 일이 결국 발생한다는 property입니다.

### Log matching

두 Raft log가 같은 index와 term의 entry를 가지면 그 이전 prefix도 같은 property입니다.

## M

### Majority

participant의 절반보다 큰 집합입니다. 고정 membership에서 어떤 두 majority도 교차합니다.

### Membership

consensus 또는 replication에 참여하는 node와 voting 권한의 configuration입니다.

## P

### Partial synchrony

일정 시점 이후 message·processing bound가 성립하는 등 synchronous와 asynchronous 가정 사이의 model입니다.

### Partition

일부 node 집합 또는 방향 사이 message가 전달되지 않거나 무기한 지연되는 network execution입니다.

## Q

### Quorum

read, write, election 또는 commit decision에 필요한 participant 집합입니다. 교차 조건과 실제 protocol을 함께 정의해야 합니다.

## R

### Read repair

foreground read가 여러 replica의 version 차이를 발견했을 때 오래된 replica를 복구하는 방식입니다.

### Replicated state machine

여러 replica가 같은 ordered command를 결정적으로 적용해 같은 abstract state를 제공하는 구조입니다.

### Replication

같은 data 또는 operation history의 여러 copy를 유지해 durability·availability·latency 목표를 달성하는 방식입니다.

## S

### Safety

나쁜 state가 발생하지 않는 property입니다. 유한 trace prefix에서 위반을 찾을 수 있습니다.

### Sequential consistency

모든 operation이 각 process order를 보존하는 하나의 sequential order로 설명되지만 real-time order는 요구하지 않는 consistency model입니다.

### Session guarantee

read-your-writes, monotonic reads처럼 한 client session에 제공하는 ordering·visibility 보장입니다.

### Shard

전체 key space 또는 data set의 일부를 소유하는 partition입니다. 각 shard는 자체 replica group을 가질 수 있습니다.

### Snapshot

특정 log prefix를 apply한 abstract state와 동등한 compact state입니다. backup file과 protocol 의미를 구분합니다.

### State machine safety

어떤 replica도 같은 log index에 서로 다른 command를 apply하지 않는 property입니다.

## T

### Termination

consensus 또는 operation이 필요한 조건에서 결국 결정·완료하는 liveness property입니다.

### Tombstone

delete를 versioned update로 표현해 오래된 replica의 값이 되살아나는 것을 막는 marker입니다.

## V

### Version vector

replica 또는 participant별 version progress를 기록해 causal order와 concurrent version을 비교하는 metadata입니다.
