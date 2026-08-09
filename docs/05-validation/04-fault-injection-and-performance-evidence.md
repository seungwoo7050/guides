# Fault injection과 성능 주장 근거

## 목표

protocol safety를 결정적 model에서 검증한 뒤 실제 process·network·storage 환경에서 fault와 resource limit을 주입합니다. 장애 복구와 성능 주장을 같은 test run의 구성·workload·trace와 함께 재현 가능하게 남깁니다.

## 계층별 검증

```text
상태 model
→ 결정적 simulator
→ 단일 process 구현 test
→ multi-process local integration
→ container/VM network·disk fault
→ staging workload
→ production 관측과 제한된 experiment
```

위 단계는 서로 대체하지 않습니다.

- model은 가능한 ordering과 invariant를 넓게 탐색합니다.
- simulator는 code에 가까운 state transition을 반복합니다.
- integration은 serialization·thread·filesystem·socket gap을 찾습니다.
- staging은 resource와 운영 도구의 상호작용을 확인합니다.

## Fault matrix

### Network

- one-way partition
- latency와 jitter
- packet loss·reorder·duplicate
- connection reset
- DNS·route 변화
- bandwidth 제한

application protocol에서 실제로 어떤 message가 영향을 받았는지 trace로 확인합니다. `tc` command가 성공했다는 사실만으로 fault 적용을 증명하지 않습니다.

### Process

- leader kill
- follower kill
- pause·resume
- rapid restart loop
- coordinated pause
- CPU starvation
- file descriptor exhaustion

### Storage

- fsync latency 증가
- disk full
- read-only filesystem
- write error
- corruption fixture
- snapshot interruption
- log replay 지연

### Configuration

- membership transition 중 crash
- rolling upgrade version skew
- stale routing metadata
- incompatible snapshot·wire format
- credential·certificate rotation

보안·배포 자체는 다른 브랜치의 소유이지만 protocol compatibility와 state transition은 이 브랜치에서 검증합니다.

## Experiment 계약

각 experiment에 다음을 기록합니다.

```text
Hypothesis
System model과 지원 failure
Initial state
Software·configuration·topology identity
Workload
Fault trigger와 실제 적용 evidence
Expected safety invariant
Expected liveness·recovery bound
Abort condition
Cleanup·restore
Artifacts
```

“leader를 죽였더니 복구되었습니다”보다 구체적이어야 합니다.

```text
3-node group에서 current-term entry 100까지 commit
leader A SIGKILL
A-B/C link 상태 확인
B 또는 C leader election
client retry
entry 100 보존과 101 commit
recovery time과 rejected request 기록
```

## Safety와 recovery metric

### Safety evidence

- conflicting commit 없음
- acknowledged write loss 없음
- duplicate client effect 없음
- stale epoch write 거절
- checksum·history checker 통과

### Recovery evidence

- leader election time
- write unavailability duration
- follower catch-up time
- snapshot transfer time
- repair backlog drain time
- membership transition completion time

process가 다시 실행 중이라는 사실만으로 recovery를 선언하지 않습니다. client-visible contract와 replica frontier를 확인합니다.

## 성능 model

측정 전에 비용을 식으로 분해합니다.

leader consensus write의 단순 latency 예:

```text
client -> leader
+ local durable append
+ fastest majority replication round
+ leader apply
+ response
```

실제 구현에는 batching, queueing, fsync group commit, scheduler와 network tail이 추가됩니다.

throughput 제한 후보:

- leader CPU
- serialization
- log append·fsync
- network fanout
- follower slowest path와 in-flight window
- apply state machine
- snapshot·repair background IO
- lock·queue contention

## Benchmark 원칙

- warm-up과 steady state를 구분합니다.
- 평균뿐 아니라 p50·p95·p99·max와 error rate를 기록합니다.
- offered load와 achieved throughput을 구분합니다.
- open-loop와 closed-loop workload 차이를 기록합니다.
- request size·key distribution·read/write ratio를 고정합니다.
- client 수와 connection 수를 기록합니다.
- durability level과 fsync policy를 변경하지 않습니다.
- fault 전·중·복구 후를 분리합니다.

## Coordinated omission

client가 이전 request 완료를 기다린 뒤 다음 request를 보내는 closed-loop test는 system이 멈춘 동안 발생했어야 할 request를 생성하지 않아 tail latency를 낮게 보일 수 있습니다.

목표가 service-time인지 user-perceived latency인지에 따라 workload generator와 보정을 선택합니다. 어떤 의미의 latency를 측정했는지 명시합니다.

## Failure 중 성능

정상 상태 benchmark만으로 fault tolerance 비용을 알 수 없습니다.

측정:

- follower 하나가 느릴 때 leader queue와 majority latency
- snapshot 전송 중 foreground latency
- partition 뒤 retry storm
- leader change 직후 cache·connection warm-up
- repair와 rebalancing 중 throughput
- disk full·read error에서 backpressure와 rejection

safety를 희생해 성능을 유지한 것인지 검사합니다.

## Upgrade와 compatibility

rolling upgrade에서는 old/new node가 같은 cluster에 존재합니다.

- wire format version
- log entry command version
- snapshot format
- feature flag activation 순서
- downgrade·rollback 가능 지점
- unknown field·command 처리

새 command를 old node가 apply할 수 없으면 모든 voter upgrade 전 commit하지 않도록 feature activation을 별도 configuration entry로 둘 수 있습니다.

## Artifact

```text
artifacts/run-id/
├── manifest.json
├── topology.json
├── workload.json
├── fault.json
├── events.jsonl
├── metrics.csv
├── history.jsonl
├── invariant-results.json
└── report.md
```

source commit, binary digest와 config hash를 포함합니다.

## 실패 조건

- fault command 실행 성공을 fault 적용 evidence로 사용합니다.
- process restart만 확인하고 client consistency를 검사하지 않습니다.
- 평균 latency와 최대 throughput만 보고합니다.
- durability setting을 바꾼 benchmark를 직접 비교합니다.
- benchmark 중 error와 rejected request를 latency 통계에서 숨깁니다.
- 정상 상태 결과로 failure 중 성능을 추론합니다.
- rolling upgrade에서 snapshot·log command 호환을 검사하지 않습니다.
- run artifact에 source·config identity가 없습니다.

## 검증

capstone의 최종 보고서에 최소한 다음 run을 포함합니다.

1. 정상 steady-state write/read
2. leader crash와 client retry
3. one-way partition
4. slow follower
5. snapshot install 중 foreground traffic
6. restart와 log replay

각 run에서 safety checker와 recovery metric을 함께 실행합니다.

## 완료 조건

- model·simulation·integration·staging 검증의 역할을 구분합니다.
- fault가 실제 적용됐다는 관측 근거를 남깁니다.
- recovery를 client contract와 replica frontier로 판정합니다.
- 성능 결과에 workload·durability·error·tail을 포함합니다.
- failure·upgrade 중 protocol safety와 성능을 함께 검증합니다.
