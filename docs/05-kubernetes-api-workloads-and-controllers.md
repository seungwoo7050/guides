# Kubernetes API와 workload controller

## 1. Kubernetes는 플랫폼의 substrate이지 사용자 제품 전체가 아닙니다

Kubernetes는 선언형 API와 controller를 통해 container workload를 관리합니다. platform team은 이 API를 그대로 모든 개발자에게 노출할 수도 있고, 더 작은 platform API 뒤에 둘 수도 있습니다.

어떤 방식을 선택하더라도 다음을 이해해야 합니다.

- API object에 desired state가 어떻게 표현됩니까?
- 어떤 controller가 어떤 child resource를 소유합니까?
- Pod가 사라졌을 때 어떤 higher-level object가 다시 만듭니까?
- readiness와 availability가 사용자 요청 성공으로 어떻게 연결됩니까?
- platform policy와 service-specific configuration의 경계는 어디입니까?

Kubernetes architecture, API와 workload 자료는 [source index의 Kubernetes](../reference/source-index.md#kubernetes)를 확인하세요.

## 2. API object는 의도와 상태의 기록입니다

공통 필드:

### `metadata`

- name·namespace·UID
- labels와 annotations
- generation
- owner references
- finalizers

### `spec`

사용자가 선언한 desired state입니다.

### `status`

controller가 관찰하고 해석한 현재 상태입니다.

platform automation은 object 생성 성공과 workload 성공을 혼동하지 않습니다.

```text
API create 성공
≠ Pod schedule 성공
≠ container start 성공
≠ readiness 성공
≠ 사용자의 endpoint 성공
```

## 3. Label은 identity와 selection contract입니다

label은 controller selector, Service, policy, cost allocation과 observability에 사용됩니다.

안정적인 label 예:

- `platform.example.io/service-id`
- `platform.example.io/owner`
- `platform.example.io/environment`
- `platform.example.io/tenant`
- `app.kubernetes.io/name`
- `app.kubernetes.io/version`

변경 가능한 설명이나 긴 값은 annotation에 둡니다. selector에 사용된 label을 임의로 바꾸면 controller 소유 관계가 깨질 수 있습니다.

## 4. Pod는 직접 운영 단위가 아닙니다

Pod는 교체 가능한 실행 단위입니다. 직접 만든 Pod는 node 장애나 삭제 뒤 원하는 개수로 복구되지 않습니다.

대표 workload:

### Deployment

stateless replica와 rolling update에 적합합니다. Pod가 상호 교체 가능하다는 전제가 필요합니다.

### StatefulSet

안정적인 identity, 순서와 persistent volume 연결이 필요한 workload에 사용합니다. 이것이 database의 backup·replication·failover를 자동으로 해결하지는 않습니다.

### Job·CronJob

완료되는 작업을 표현합니다. 중복 실행과 재시도 가능성에 맞춰 application side effect를 설계해야 합니다.

### DaemonSet

선택된 node마다 agent를 실행합니다. platform telemetry, networking과 security agent에서 사용되지만 node 전체 blast radius를 가집니다.

workload kind는 기술 취향보다 수명·identity·completion contract로 선택합니다.

## 5. Controller ownership을 추적합니다

Deployment는 ReplicaSet을 만들고 ReplicaSet은 Pod를 만듭니다. 각 object의 owner reference와 selector를 사용해 다음을 확인합니다.

```text
누가 이 object를 만들었습니까?
누가 원하는 replica 수를 정합니까?
이 object를 직접 수정하면 다음 reconcile에서 유지됩니까?
삭제하면 controller가 다시 만듭니까?
```

live Pod의 임시 수정은 debugging에는 쓸 수 있어도 desired state 변경이 아닙니다.

## 6. Probe의 목적을 분리합니다

### Startup probe

느리게 시작하는 application이 초기화 중이라는 사실을 표현합니다. 성공하기 전에는 다른 liveness·readiness 판정의 시점을 조절할 수 있습니다.

### Readiness probe

현재 traffic을 받을 준비가 됐는지 판정합니다. 실패하면 일반적으로 endpoint selection에서 제외되지만 process를 재시작하는 목적이 아닙니다.

### Liveness probe

process를 재시작해야만 회복되는 상태인지 판정합니다. dependency 일시 장애를 liveness에 연결하면 전체 replica가 반복 재시작할 수 있습니다.

platform template는 probe field를 제공할 수 있지만 application-specific health 의미는 service team이 소유합니다.

## 7. Resource request와 limit은 scheduling·격리 계약입니다

- request는 scheduler가 배치와 보장 계산에 사용합니다.
- limit은 runtime이 허용하는 상한과 관련됩니다.
- 실제 사용량과 request 차이는 cluster capacity와 비용에 영향을 줍니다.
- memory limit 초과와 CPU limit의 결과는 같지 않습니다.

platform은 default tier와 guardrail을 제공할 수 있습니다. service owner는 실제 측정과 부하 특성으로 값을 조정해야 합니다.

다음은 위험합니다.

- 모든 서비스에 같은 값 적용
- request 없이 autoscaling 기대
- limit을 capacity planning으로 간주
- peak 한 번만 보고 과도한 request 고정
- JVM·cache·sidecar의 전체 memory를 빠뜨림

## 8. Configuration과 secret을 image에서 분리합니다

Kubernetes object에 secret이라는 이름이 있다고 값이 자동으로 안전해지는 것은 아닙니다. platform contract는 다음을 정합니다.

- configuration source와 version
- secret의 authoritative store
- workload에 전달되는 방식
- rotation과 reload/restart
- namespace와 service account access
- log와 debugging에서 redaction

구체적인 identity와 secret lifecycle은 [11장](11-identity-secrets-and-policy.md)에서 다룹니다.

## 9. Custom Resource를 만들기 전 질문

Kubernetes API를 platform API의 저장소로 확장할 수 있습니다. 하지만 CRD를 만든다고 안정적인 product API가 되는 것은 아닙니다.

확인:

- 사용자 문제와 desired state가 충분히 안정됐습니까?
- namespace scope와 cluster scope 중 무엇입니까?
- spec/status/version conversion이 필요합니까?
- controller가 외부 state를 어떻게 관찰합니까?
- deletion과 finalizer 실패를 어떻게 복구합니까?
- API server가 중단돼도 필요한 작업이 무엇입니까?
- tenant가 CRD와 webhook을 악용할 수 있습니까?

작은 service에서만 쓰는 설정을 cluster-wide CRD로 확장하지 않습니다.

## 10. Workload contract

platform이 지원하는 workload는 최소한 다음을 선언해야 합니다.

```text
owner와 service identity
artifact digest
workload kind와 replica contract
port와 protocol
startup·readiness·liveness 의미
CPU·memory request와 limit
network ingress·egress dependency
persistent state와 backup owner
disruption tolerance
service account와 secret reference
telemetry와 external smoke
```

이 contract는 template 생성 시점과 admission, release gate와 catalog scorecard에서 재사용할 수 있습니다.

## 11. Debugging 순서

```text
platform request와 generation
→ desired-state revision
→ Kubernetes object와 controller condition
→ Pod scheduling event
→ image pull·volume mount·secret access
→ container state와 probe
→ Service endpoint와 network policy
→ external request
```

마지막 error message만 보고 liveness delay를 늘리는 식으로 수정하지 않습니다.

## 12. 실습

[`05-workload-contract`](../exercises/05-workload-contract/)에서 하나의 HTTP service에 대한 workload·resource·probe·network·storage·disruption·security·evidence 계약을 작성합니다.

reference는 하나의 안전한 기본값일 뿐입니다. 실제 application 특성에 맞지 않으면 다른 값을 사용하고 근거를 남깁니다.
