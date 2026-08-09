# 클라우드 특성, 서비스 모델과 배포 모델

클라우드 관련 용어는 서로 다른 분류 축을 섞을 때 혼란이 생깁니다.

```text
IaaS·PaaS·SaaS        무엇을 서비스로 소비하는가
VM·container·FaaS     workload가 어떤 실행 단위로 동작하는가
public·private·hybrid 어디에 어떤 조직 경계로 배치되는가
managed·serverless    운영 책임과 제어가 얼마나 공급자에게 이동하는가
```

이 문서는 축을 분리한 뒤 다시 연결합니다.

## 1. 클라우드의 다섯 공통 특성

NIST SP 800-145는 클라우드 컴퓨팅을 다섯 essential characteristic으로 설명합니다.

### 1.1 On-demand self-service

소비자가 사람의 개별 승인을 기다리지 않고 API·portal·automation으로 resource를 요청하고 해제할 수 있습니다.

이 특성은 편의만 뜻하지 않습니다.

- 누가 생성 권한을 가집니까?
- quota와 policy는 어디서 검사됩니까?
- resource owner와 expiry는 어떻게 기록합니까?
- 잘못 생성한 resource를 누가 발견하고 지웁니까?

### 1.2 Broad network access

표준화된 network mechanism을 통해 여러 client에서 접근할 수 있습니다. “인터넷에 공개”와 같은 뜻은 아닙니다. private endpoint, VPN, service network, API gateway도 포함될 수 있습니다.

### 1.3 Resource pooling

공급자가 공유 pool에서 compute·storage·network capacity를 할당합니다. 소비자는 정확한 물리 자원을 통제하지 않는 대신 논리적 isolation과 service contract를 신뢰합니다.

공유는 noisy neighbor, isolation, capacity shortage와 location control 문제를 만듭니다.

### 1.4 Rapid elasticity

수요에 따라 resource를 빠르게 늘리고 줄일 수 있습니다. 무한 capacity나 즉시 확장을 뜻하지 않습니다.

- quota
- provisioning latency
- warm-up
- stateful bottleneck
- regional capacity
- scaling metric 오류
- 비용 상한

이 남습니다.

### 1.5 Measured service

사용량을 측정하고 보고합니다. 측정 단위는 request, execution duration, byte-month, I/O operation, provisioned capacity, data transfer 등으로 다양합니다.

측정 가능성은 비용 배분과 최적화를 가능하게 하지만 잘못된 tag·tenant attribution·late billing data는 다른 문제를 만듭니다.

## 2. Service model: IaaS

IaaS에서 소비자는 compute, network와 storage resource를 조합하고 그 위의 운영체제·runtime·application을 더 많이 관리합니다.

소비자가 보통 제어하는 것:

- instance image와 OS configuration
- network segmentation과 route
- attached storage와 filesystem
- workload runtime
- application과 data
- patch window와 host-level monitoring 일부

공급자가 보통 관리하는 것:

- physical facility와 hardware
- hypervisor 또는 underlying host
- core control plane
- physical network와 storage fabric

IaaS의 장점은 제어 가능성입니다. 비용은 patching, hardening, capacity와 failure recovery 책임이 더 많이 남는다는 점입니다.

## 3. Service model: PaaS

PaaS는 application을 배포·실행하기 위한 platform capability를 제공합니다. 소비자는 운영체제와 runtime 관리의 상당 부분을 공급자에게 맡기고 application과 data에 집중합니다.

PaaS를 하나의 고정된 제품 형태로 보면 안 됩니다. managed runtime, managed database, queue, integration service 등은 서로 다른 책임을 숨깁니다.

검토할 질문:

- runtime version을 누가 선택하고 언제 종료합니까?
- patch는 자동입니까, maintenance window를 선택합니까?
- scale unit은 instance입니까, request입니까, throughput입니까?
- network와 identity를 어느 수준까지 제어할 수 있습니까?
- backup과 restore는 누구 책임입니까?
- extension·custom binary·privileged operation이 필요합니까?

## 4. Service model: SaaS

SaaS 소비자는 완성된 application capability를 사용합니다. 공급자는 application·runtime·platform·infrastructure 운영을 담당합니다.

그러나 SaaS 고객에게도 책임이 남습니다.

- account와 identity 관리
- organization·role·sharing 설정
- data classification과 입력 적법성
- export·retention·deletion 요구
- integration token과 API 사용
- audit·compliance 설정
- client device와 endpoint 보안

SaaS를 만드는 공급자 입장에서는 tenant lifecycle, isolation, entitlement, metering, support, migration과 exit가 제품의 핵심 상태가 됩니다.

## 5. FaaS는 다른 축이다

Function as a Service는 일반적으로 serverless compute의 한 형태입니다. 함수를 event 또는 request 단위로 실행하고, 공급자가 runtime instance의 생성·확장·폐기를 관리합니다.

FaaS를 IaaS·PaaS·SaaS와 동일한 네 번째 NIST service model로 단순 나열하면 분류 축이 섞입니다. 실무적으로는 PaaS 계열의 managed execution capability로 볼 수 있지만, 중요한 것은 이름보다 다음 실행 계약입니다.

- invocation 단위
- ephemeral execution environment
- timeout과 memory limit
- concurrency와 scale behavior
- event source delivery
- retry와 duplicate
- cold/warm start
- local state 비보장
- observability와 cost unit

## 6. VM, container와 CaaS

VM과 container는 실행·격리 단위입니다. 같은 VM을 IaaS로 직접 관리할 수도 있고, container를 PaaS 또는 Kubernetes platform에서 실행할 수도 있습니다.

CaaS(Container as a Service)라는 표현도 쓰이지만 모든 공급자가 같은 의미로 사용하지 않습니다. 다음을 확인하는 편이 정확합니다.

- 누가 cluster 또는 node를 관리합니까?
- scheduler와 network policy는 누가 제어합니까?
- image와 runtime patch는 누구 책임입니까?
- workload identity와 secret은 어디서 주입됩니까?
- scaling과 disruption은 어떤 controller가 수행합니까?

조직용 container platform과 golden path는 `platform-engineering`의 후속 범위입니다.

## 7. Deployment model

### Public cloud

공급자가 다수의 소비자에게 cloud capability를 제공합니다. public network 공개 여부와는 다른 개념입니다. public cloud 안에서도 private network와 private endpoint를 사용할 수 있습니다.

### Private cloud

한 조직을 위해 cloud 특성을 제공하는 환경입니다. 단순히 사내 virtualization cluster가 있다는 이유만으로 cloud가 되는 것은 아닙니다. self-service, pooling, elasticity와 measured service가 실제로 제공되는지 확인해야 합니다.

### Community cloud

공통 요구를 가진 조직 집단을 위한 환경입니다. 실제 사용은 public·private보다 적지만 규제·산업 공동 요구를 설명할 때 등장합니다.

### Hybrid cloud

서로 다른 cloud 또는 기존 환경을 data·application portability와 orchestration으로 연결합니다. 단순히 두 환경을 모두 사용한다는 사실만으로 운영 가능한 hybrid architecture가 되지 않습니다.

필요한 계약:

- identity federation
- network connectivity
- data ownership과 synchronization
- deployment coordination
- failure independence
- observability correlation
- exit와 degraded mode

## 8. “Cloud-native”는 service model이 아니다

cloud-native는 보통 automation, immutable artifact, distributed workload, elastic scaling, managed services와 observability를 활용하는 설계 방식을 뜻합니다. 정확한 제품 분류가 아닙니다.

“cloud-native이므로 좋다”가 아니라 다음을 물어야 합니다.

- 어떤 변화와 장애에 더 잘 대응합니까?
- 어떤 새로운 dependency와 운영 복잡성을 만듭니까?
- 비용과 provider coupling은 증가합니까?
- team이 이를 검증·운영할 수 있습니까?

## 9. 분류 절차

새 서비스를 보면 다음 순서로 판정합니다.

1. 소비자가 실제로 얻는 capability를 적습니다.
2. 소비자가 직접 제어할 수 있는 resource와 configuration을 적습니다.
3. 공급자가 patch·scale·recover하는 범위를 적습니다.
4. 소비자가 data·identity·availability·cost에 대해 남는 책임을 적습니다.
5. 실행 단위를 VM·container·function·application 중 무엇인지 적습니다.
6. public·private·hybrid deployment 경계를 적습니다.
7. 제품 이름 대신 가장 가까운 service model과 예외를 기록합니다.

## 10. 대표 오분류

| 표현 | 문제 | 더 정확한 질문 |
|---|---|---|
| VM이므로 cloud | virtualization과 cloud characteristic을 혼동 | self-service·pooling·elasticity·metering이 있는가 |
| Lambda이므로 SaaS | 실행 모델과 완성 application을 혼동 | 소비자가 function code를 소유하는가 |
| managed DB이므로 책임 없음 | engine 운영과 data 책임을 혼동 | schema·query·backup 검증·access는 누가 소유하는가 |
| SaaS이므로 multi-tenant | business delivery와 deployment topology를 혼동 | tenant를 정의하며 어떤 resource를 공유하는가 |
| serverless이므로 무한 확장 | abstraction과 limit을 혼동 | quota·concurrency·downstream capacity는 얼마인가 |

## 연결 실습

[01 서비스 분류](../exercises/01-service-classification/README.md)에서 사례마다 service model, execution model, deployment model과 responsibility를 별도 열로 작성합니다.
