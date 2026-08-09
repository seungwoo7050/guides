# Serverless와 FaaS runtime

`serverless`는 서버가 존재하지 않는다는 뜻이 아닙니다. 소비자가 개별 server instance의 provisioning·patching·scaling을 직접 관리하지 않고, request 또는 event에 더 가까운 단위로 compute를 소비하는 운영 모델입니다.

FaaS는 그중 function invocation을 핵심 실행 단위로 사용하는 형태입니다.

## 1. 실행 상태

한 invocation은 대략 다음 단계를 거칩니다.

```text
event accepted
→ queued or dispatched
→ execution environment selected/created
→ runtime initialized
→ handler invoked
→ external effects
→ result or failure
→ environment reused or discarded
```

공급자별 구현은 다르지만 소비자가 고려해야 할 상태는 비슷합니다.

- event identity
- attempt
- runtime version
- function version
- environment lifecycle
- deadline
- memory와 temporary storage
- external side effect
- completion acknowledgment
- retry 또는 dead-letter

## 2. Ephemeral execution

function environment는 invocation 뒤 재사용될 수도 있고 폐기될 수도 있습니다. 따라서 다음 가정은 위험합니다.

```text
다음 invocation에서도 global variable이 남습니다.
local file이 durable합니다.
한 instance가 같은 tenant 요청만 처리합니다.
background thread가 handler return 뒤 완료됩니다.
```

안전한 원칙:

- durable state는 외부 service에 둡니다.
- local state는 cache·scratch로만 사용합니다.
- cache hit 여부가 correctness를 바꾸지 않게 합니다.
- credential과 tenant context를 invocation마다 확정합니다.
- handler return 전에 필요한 외부 효과와 acknowledgment를 완료합니다.

## 3. Cold start와 warm reuse

새 execution environment가 필요하면 runtime·code·dependency 초기화가 발생합니다. cold start latency는 언어, package size, network initialization, configuration과 provider 기능에 영향을 받습니다.

warm environment는 latency를 줄이지만 다음 위험이 있습니다.

- 이전 invocation의 mutable global state
- stale configuration
- tenant data cache 잔존
- expired credential
- open connection 상태
- memory leak 누적

performance 최적화와 isolation·correctness를 함께 검사합니다.

## 4. Timeout과 deadline

function에는 최대 실행 시간이 있습니다. handler 내부 timeout만 보면 안 됩니다.

```text
queue wait
+ cold start
+ dependency call
+ retry
+ write and acknowledgment
≤ end-to-end deadline
```

handler가 timeout 직전에 외부 write를 완료하고 acknowledgment 전에 종료되면 같은 event가 다시 전달될 수 있습니다. 따라서 timeout은 idempotency와 함께 설계합니다.

## 5. Concurrency

동시성은 단순히 function instance 수가 아닙니다.

- account 또는 region limit
- function reserved limit
- event source poller
- partition 수
- batch size
- downstream connection limit
- tenant quota
- per-key serialization

function이 빠르게 scale-out해도 database connection, third-party API, rate limit와 lock이 병목일 수 있습니다.

### Concurrency control

- maximum concurrency
- reserved capacity
- queue buffering
- per-tenant limiter
- partition key
- semaphore 또는 lease
- batch size
- backpressure

비용과 latency를 함께 관찰합니다.

## 6. Request-driven과 event-driven

### Synchronous request

client가 결과를 기다립니다.

- client timeout
- gateway timeout
- function timeout
- retry owner
- idempotency key
- partial response

### Asynchronous event

producer는 event acceptance까지만 확인할 수 있습니다.

- event durability
- delivery attempt
- retry schedule
- dead-letter
- result notification
- duplicate
- ordering

### Stream·queue event source

poller가 batch를 읽어 function을 호출할 수 있습니다.

- batch 전체 실패
- partial batch response
- partition ordering
- offset 또는 visibility timeout
- poison record
- replay

공급자별 semantics는 다르므로 공식 문서를 확인해야 합니다.

## 7. Deployment와 version

function code만 versioning하면 부족합니다.

- runtime version
- dependency lock
- environment configuration
- layer 또는 shared package
- trigger mapping
- permission
- concurrency setting
- destination·DLQ
- schema

release artifact와 trigger configuration을 같은 manifest로 추적합니다.

traffic shifting 또는 alias 기능이 있어도 state schema와 event compatibility를 별도로 검증합니다.

## 8. Networking

function을 private network에 연결하면 database 접근은 가능해지지만 startup latency, address capacity, DNS와 egress dependency가 달라질 수 있습니다.

질문:

- public API와 private service를 어떤 route로 접근합니까?
- egress NAT·proxy 비용과 capacity는 얼마입니까?
- private DNS가 실패하면 어떻게 관찰합니까?
- function identity와 network rule이 모두 필요한가요?
- metadata 또는 credential endpoint 접근을 제한할 수 있습니까?

## 9. Observability

invocation log만으로 end-to-end outcome을 알 수 없습니다.

필요한 correlation:

```text
event_id
request_id
attempt
function_version
tenant_id
source_partition_or_queue
external_effect_id
deadline
result
retry_decision
cost_or_duration
```

metric:

- invocation count
- success·error·timeout
- throttle
- concurrency
- cold start
- duration distribution
- queue age
- retry count
- dead-letter count
- downstream latency
- cost per useful outcome

## 10. 비용 모델

FaaS는 보통 request, execution duration, allocated memory, provisioned/warm capacity와 data transfer 등에 비용이 연결됩니다.

저빈도·burst workload에는 유리할 수 있지만 다음은 비용을 키웁니다.

- 무한 retry
- oversized memory
- chatty external calls
- large payload
- long-running work
- high log volume
- egress
- provisioned concurrency

instance 비용과 invocation 비용을 workload trace로 비교합니다.

## 11. 적합하지 않은 workload

다음은 검토가 필요합니다.

- 매우 긴 실행
- 강한 local state
- persistent connection
- low-latency warm state가 필수
- custom OS·driver
- 높은 steady-state utilization
- GPU 또는 specialized hardware
- 복잡한 transaction boundary

FaaS를 쓰지 말아야 한다는 뜻이 아니라 function boundary를 작게 두거나 다른 compute model과 조합해야 할 수 있습니다.

## 12. 판단 질문

1. invocation이 반복돼도 결과가 하나입니까?
2. local environment가 사라져도 correctness가 유지됩니까?
3. concurrency가 downstream capacity를 넘지 않습니까?
4. timeout 뒤 외부 효과를 판정할 수 있습니까?
5. poison event를 격리할 수 있습니까?
6. event source와 function version을 함께 추적합니까?
7. useful business outcome당 비용을 계산할 수 있습니까?

## 연결 실습

[04 FaaS event lifecycle](../exercises/04-faas-event-lifecycle/README.md)에서 upload event 처리기의 runtime, timeout, concurrency와 dead-letter 정책을 설계합니다.
