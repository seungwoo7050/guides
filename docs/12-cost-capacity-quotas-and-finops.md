# Cost, capacity, quota와 FinOps

클라우드 비용은 나중에 청구서를 보는 회계 문제가 아닙니다. architecture가 resource를 생성·확장·보존·전송하는 방식의 실행 결과입니다.

```text
workload demand
→ resource allocation
→ measured usage
→ price rule
→ bill
```

비용을 줄이기 전에 어떤 업무 결과를 어떤 resource가 만들었는지 연결해야 합니다.

## 1. 비용 driver

대표 단위:

- VM 또는 node 시간
- provisioned CPU·memory
- request
- function duration과 memory
- storage byte-month
- I/O operation
- database capacity unit
- snapshot과 backup
- network egress
- cross-zone·cross-region transfer
- log ingestion·retention·query
- public address·NAT·load balancer
- support plan

“serverless는 사용한 만큼만 지불한다”는 표현도 log, provisioned concurrency, storage와 egress를 포함해 확인해야 합니다.

## 2. Fixed, variable와 step cost

### Fixed 또는 idle cost

traffic이 없어도 발생합니다.

- provisioned instance
- managed database minimum
- load balancer
- NAT
- reserved capacity
- dedicated tenant resource

### Variable cost

사용량과 함께 증가합니다.

- request
- function execution
- object operation
- egress
- log ingestion

### Step cost

threshold를 넘을 때 resource tier 또는 replica 하나가 추가됩니다.

비용 곡선을 이해하면 small workload와 steady high workload의 적합한 서비스가 달라집니다.

## 3. Unit economics

총 bill만 보면 효율을 판단하기 어렵습니다.

```text
cost per active tenant
cost per 1000 processed documents
cost per successful job
cost per GB retained
cost per API request
```

분모가 business outcome과 연결돼야 합니다. retry와 failed job을 포함한 실제 cost를 계산합니다.

## 4. Allocation

resource cost를 team·service·environment·tenant에 귀속합니다.

- account/project
- tag/label
- resource group
- usage event
- shared cost allocation rule

untagged resource를 허용하면 owner가 없는 비용과 cleanup 실패가 누적됩니다.

shared database와 network cost는 완벽히 정확하지 않을 수 있습니다. 일관된 rule과 version을 기록합니다.

## 5. Budget는 hard limit가 아닐 수 있다

budget alert가 resource 생성을 자동 차단하지 않는 경우가 많습니다.

계층:

- forecast
- alert
- approval
- quota
- policy deny
- automation kill switch
- service degradation

어떤 조치가 자동이고 누가 override할 수 있는지 기록합니다.

## 6. Cost anomaly

원인:

- retry loop
- log storm
- unbounded autoscaling
- data egress
- orphan resource
- snapshot retention
- compromised credential
- tenant abuse
- pricing or discount change

anomaly alert에는 baseline, threshold, delay, owner와 containment가 필요합니다.

## 7. Capacity와 quota

cloud에 resource pool이 있어도 소비자 quota와 지역 capacity가 존재합니다.

- instance count
- address
- storage
- API request
- function concurrency
- database connection
- throughput
- account-level resource count

peak 전에 quota를 확인하고 increase lead time을 고려합니다. quota가 높을수록 compromise와 cost blast radius도 커질 수 있습니다.

## 8. Rightsizing

작은 instance로 줄이는 것만이 rightsizing은 아닙니다.

- CPU·memory·I/O utilization
- tail latency
- request burst
- failure headroom
- scaling latency
- license
- operational overhead

average utilization만 보고 줄이면 peak와 zone failure 시 capacity가 부족할 수 있습니다.

## 9. Commitment

reserved capacity, savings plan, committed use 등은 할인과 lock-in을 교환합니다.

검토:

- 실제 steady baseline
- 기간
- instance/service flexibility
- region dependency
- growth·shrink scenario
- migration 계획
- unused commitment

할인율만 보지 않고 workload uncertainty와 exit를 함께 봅니다.

## 10. Storage lifecycle

비용과 보존 요구를 연결합니다.

- hot·cool·archive tier
- retrieval latency와 fee
- minimum retention
- versioning
- duplicate backup
- legal hold
- abandoned multipart upload
- snapshot dependency

lifecycle rule이 data를 지우기 전에 business retention과 restore를 검증합니다.

## 11. Network egress

architecture diagram의 화살표는 비용일 수 있습니다.

- internet egress
- cross-zone
- cross-region
- provider 간 transfer
- backup copy
- analytics export
- customer download

data gravity가 portability와 disaster recovery 비용에 영향을 줍니다.

## 12. FinOps operating loop

```text
inform
resource와 cost를 보이게 합니다.

optimize
낭비와 구조 문제를 줄입니다.

operate
budget·policy·forecast·ownership을 일상 workflow로 만듭니다.
```

FinOps는 비용 절감 팀만의 업무가 아닙니다. engineering, finance, product와 business owner가 trade-off를 공유하는 운영 방식입니다.

## 13. Cleanup contract

실험과 ephemeral environment는 종료 조건을 가집니다.

```text
resource prefix
tag owner
expires_at
dependency graph
destroy command
final inventory
billing delay note
log·evidence retention
```

cleanup 성공은 command exit code가 아니라 inventory가 비고 비용 발생 resource가 사라졌음을 확인하는 것입니다.

## 14. Cost review 질문

1. 가장 큰 세 cost driver는 무엇입니까?
2. idle 상태에서 어떤 비용이 남습니까?
3. retry와 failure가 비용을 얼마나 늘립니까?
4. 한 tenant가 전체 bill을 키울 수 있습니까?
5. zone failure 뒤 필요한 headroom을 유지합니까?
6. egress와 log 비용을 estimate에 포함했습니까?
7. resource owner와 expiry가 있습니까?
8. commitment가 migration을 막습니까?

## 연결 실습

[06 비용과 exit](../exercises/06-cost-and-exit/README.md)에서 workload 단위 cost model과 orphan resource cleanup plan을 작성합니다.
