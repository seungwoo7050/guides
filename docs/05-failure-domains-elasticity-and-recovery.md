# Failure domain, elasticity와 recovery

클라우드는 resource를 여러 위치에 배치하고 자동 확장하는 기능을 제공하지만, 설정만으로 가용성과 복구가 자동 완성되지는 않습니다. 핵심은 **어떤 실패가 함께 발생하며, 남은 capacity와 state가 실제 업무를 계속 처리할 수 있는지**입니다.

## 1. Failure domain

failure domain은 하나의 사건으로 함께 영향을 받을 수 있는 자원 집합입니다.

예:

- process
- instance 또는 node
- rack·power·network unit
- availability zone
- region
- identity/control plane
- DNS provider
- artifact registry
- organization-wide policy

두 instance가 있어도 같은 zone, 같은 load balancer, 같은 database, 같은 secret 또는 같은 deployment 오류를 공유하면 일부 실패에 독립적이지 않습니다.

## 2. Region과 zone

공급자마다 topology 정의가 다릅니다. 일반적으로 region은 지리적 운영 범위, zone은 region 안의 상대적으로 독립된 failure domain으로 사용됩니다.

검토:

- compute와 stateful service가 실제로 몇 zone에 배치됐습니까?
- zone 간 data replication은 synchronous입니까?
- network·load balancer·control plane이 zonal입니까, regional입니까?
- zone 하나가 사라졌을 때 남은 capacity가 peak traffic을 감당합니까?
- failover가 자동인지, 감지·승격 시간이 얼마인지 확인했습니까?
- client connection과 DNS cache가 새 target으로 이동합니까?

“multi-AZ enabled”는 위 질문의 시작점이지 결론이 아닙니다.

## 3. Availability와 durability

- availability: 지금 요청을 처리할 수 있는가
- durability: 저장된 데이터가 장기간 보존되는가

object가 여러 장치에 복제돼 durability가 높아도 identity outage나 network failure 때문에 읽을 수 없을 수 있습니다. 반대로 application이 available해도 마지막 몇 초의 data가 유실될 수 있습니다.

SLO와 recovery objective를 분리합니다.

```text
availability target
RTO: 서비스 복구까지 허용 시간
RPO: 허용 가능한 data loss window
```

## 4. Redundancy와 recovery

### Redundancy

동시에 여러 replica 또는 경로를 유지합니다. 즉각적인 장애 흡수에 유리하지만 같은 잘못된 변경·삭제·corruption이 복제될 수 있습니다.

### Backup

시점별 독립 artifact를 보존합니다. logical deletion·corruption·ransomware 복구에 필요하지만 restore 시간이 걸립니다.

### Rebuild

image, configuration, external backup과 secret으로 새 환경을 만듭니다. region 또는 account 전체 손실에 대응할 수 있지만 정기적으로 검증해야 합니다.

세 가지는 서로 대체하지 않습니다.

## 5. Elasticity

### Scale out

instance 수를 늘립니다. application이 stateless하거나 shared state가 외부에 있어야 효과적입니다.

### Scale up

instance 크기 또는 provisioned capacity를 늘립니다. 간단하지만 상한·재시작·비용 step이 존재합니다.

### Scale to zero

idle 상태에서 compute를 제거합니다. 비용은 줄지만 cold start, first-request latency, connection·local cache 손실이 생깁니다.

### Queue-based scaling

request rate가 아니라 backlog, oldest message age, processing time과 concurrency를 기준으로 확장합니다. 잘못된 poison message가 무한 backlog와 비용 폭주를 만들 수 있습니다.

## 6. Scaling control loop

```text
observe metric
→ compare target
→ decide desired capacity
→ provision or remove
→ wait for readiness/drain
→ observe effect
```

문제:

- metric delay
- oscillation
- provisioning time
- downstream bottleneck
- quota
- scale-in data loss
- traffic burst가 measurement window보다 짧음
- cost limit 없음

따라서 minimum, maximum, cooldown, step, readiness, drain과 budget guard를 함께 설계합니다.

## 7. Load shedding과 backpressure

무조건 확장하는 것은 방어가 아닙니다. dependency가 병목일 때 application instance만 늘리면 connection storm과 비용이 증가할 수 있습니다.

필요한 통제:

- admission limit
- per-tenant quota
- bounded queue
- timeout budget
- retry budget
- degraded feature
- priority
- circuit breaker
- explicit overload response

일반 원리는 `distributed-services`가 소유합니다. 여기서는 cloud scaling과 quota가 그 통제를 어떻게 구현하는지 봅니다.

## 8. Recovery workflow

복구는 “새 instance를 시작한다”보다 넓습니다.

```text
detect
→ classify scope
→ stop unsafe automation
→ preserve evidence
→ select failover or restore
→ provision clean capacity
→ restore state and configuration
→ validate invariants
→ shift traffic
→ monitor
→ clean old resources
```

자동 failover는 빠르지만 잘못된 data·configuration을 확산할 수 있습니다. 수동 승인은 느리지만 더 많은 판단을 요구합니다. workload의 RTO·data sensitivity·운영 성숙도에 맞춰 선택합니다.

## 9. Chaos와 failure injection

실제 production에서 무작정 장애를 만들지 않습니다. 작은 환경과 명시적 blast radius에서 다음을 검증합니다.

- instance termination
- zone target 제거
- network deny
- dependency latency
- quota exhaustion
- credential expiration
- failed deployment
- backup restore

실험 계약:

```text
hypothesis
scope
steady-state metric
injected failure
expected first alarm
expected degraded behavior
abort condition
recovery action
evidence
cleanup
```

## 10. Common-mode failure

여러 replica를 가져도 공통 요소가 남습니다.

- 같은 image bug
- 같은 deployment
- 같은 IAM policy
- 같은 key
- 같은 region control plane
- 같은 DNS
- 같은 provider
- 같은 operator mistake

고가용성 설계는 replica 개수가 아니라 failure independence를 확인합니다.

## 11. 비용과 recovery

standby capacity, cross-zone transfer, backup retention, cross-region replication과 restore test에는 비용이 듭니다. 반대로 비용 절감을 위해 모든 capacity를 scale-to-zero로 만들면 recovery와 first-request latency가 악화됩니다.

결정에는 다음을 기록합니다.

- 보호하는 business impact
- 예상 장애 빈도와 비용
- steady-state 비용
- failover 시 비용
- test 비용
- 유지할 잔여 위험

## 12. Evidence

- topology inventory
- capacity per failure domain
- load test와 scale timeline
- failover operation log
- RTO·RPO 측정
- restore checksum와 business invariant
- alarm 발생 시각
- traffic shift evidence
- cleanup과 cost delta

## 연결 실습

[02 IaaS failure domain](../exercises/02-iaas-failure-domains/README.md)에서 zone 하나가 사라지는 시나리오를 작성하고 남은 capacity, state와 evidence를 검토합니다.
