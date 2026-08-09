# Kubernetes network·storage·scheduling

## 1. Platform과 workload가 공유하는 runtime 경계

Kubernetes에서 application이 실행되지 않는 이유는 image나 code만이 아닙니다.

- Pod가 배치될 node가 없습니다.
- required volume이 attach되지 않습니다.
- Service selector가 endpoint를 찾지 못합니다.
- NetworkPolicy가 필요한 egress를 차단합니다.
- voluntary disruption을 견딜 replica가 없습니다.
- tenant quota가 요청을 거부합니다.

platform team은 공통 substrate와 정책을 소유하고, service team은 workload가 요구하는 통신·저장·자원·availability를 선언합니다.

## 2. Service와 endpoint

Service는 안정적인 virtual endpoint와 backend selection을 제공합니다. 확인할 경계:

- selector가 의도한 Pod label을 선택합니까?
- readiness를 통과한 endpoint만 traffic을 받습니까?
- port와 target port의 protocol이 일치합니까?
- headless service나 직접 Pod identity가 필요한 이유가 있습니까?
- service DNS가 namespace 경계에서 어떻게 해석됩니까?

Service object가 존재한다고 backend가 준비된 것은 아닙니다. endpoint와 실제 request를 확인합니다.

## 3. 외부 traffic의 여러 층

일반적인 경로:

```text
public DNS
→ load balancer
→ Gateway 또는 Ingress
→ Service
→ endpoint
→ Pod listener
```

각 층의 owner와 evidence를 분리합니다.

- DNS와 certificate는 `web-infra`의 공개 운영 계약과 연결합니다.
- Gateway route와 namespace 권한은 platform policy가 관리할 수 있습니다.
- application path·host·protocol 요구는 service owner가 선언합니다.
- external smoke는 전체 경로의 결과를 판정합니다.

특정 ingress controller의 annotation을 platform public API로 직접 노출하면 구현 교체가 어려워집니다. 필요한 capability를 platform field로 추상화하고, 지원하지 않는 기능은 extension profile로 분리합니다.

## 4. NetworkPolicy는 구현 지원을 확인해야 합니다

NetworkPolicy object를 만들었다고 traffic이 반드시 차단되는 것은 아닙니다. cluster network implementation이 해당 정책을 적용하는지 확인해야 합니다.

multi-tenant 기준선:

```text
namespace default deny
+ DNS 등 공통 infrastructure 허용
+ 명시된 ingress source 허용
+ 명시된 egress destination 허용
+ 정책 효과를 실제 packet 또는 request로 검증
```

IP range만으로 dynamic service identity를 표현하기 어렵다면 workload identity와 application-layer authorization을 함께 사용합니다.

## 5. Persistent volume의 수명

구분:

- StorageClass: provisioning profile과 policy
- PersistentVolumeClaim: workload가 요청한 storage contract
- PersistentVolume: 실제 volume binding
- application data: volume 안의 업무 상태

PVC가 `Bound`라고 application data가 일관되거나 backup된 것은 아닙니다. platform은 storage profile과 snapshot capability를 제공할 수 있지만, application-consistent backup과 restore 검증은 data owner와 `web-infra`/`database-systems` 계약에 연결합니다.

확인:

- access mode와 topology
- reclaim policy
- expansion
- snapshot과 restore
- encryption과 key owner
- workload·namespace 삭제 뒤 retention
- migration과 attach 제한

## 6. Scheduler는 request와 constraint를 해석합니다

Pod가 `Pending`이면 scheduler event와 constraint를 확인합니다.

대표 입력:

- CPU·memory·extended resource request
- node selector와 affinity
- taint와 toleration
- topology spread
- volume topology
- priority와 preemption
- tenant policy

constraint를 많이 추가할수록 배치 가능한 node 집합이 줄어듭니다. “고가용성”을 위해 anti-affinity를 추가했지만 작은 cluster에서 어떤 Pod도 배치되지 않을 수 있습니다.

## 7. Availability와 topology

replica 수만 늘려도 같은 node 또는 zone에 몰리면 공통 실패를 견디지 못합니다.

질문:

- 어떤 failure domain을 견뎌야 합니까? process, node, zone, cluster, region 중 무엇입니까?
- replica가 실제로 다른 failure domain에 배치됐습니까?
- dependency도 같은 failure domain을 견딥니까?
- topology constraint가 capacity shortage 때 어떻게 동작합니까?
- 비용과 recovery 목표가 추가 replica를 정당화합니까?

platform profile은 지원하는 availability tier와 필요한 최소 capacity를 명시해야 합니다.

## 8. Voluntary disruption 계약

node upgrade, repair와 scale-down은 의도된 disruption입니다. application이 이를 견디려면 다음이 필요합니다.

- replica와 readiness
- graceful termination
- in-flight request drain
- PodDisruptionBudget(PDB)
- dependency와 quorum 이해
- 충분한 대체 capacity

PDB는 모든 삭제를 막지 않으며 involuntary disruption을 예방하지도 않습니다. cluster operator는 Eviction API와 drain 절차를 사용하고, service owner는 application이 실제로 종료·재시작 가능한지 검증합니다. 공식 disruption 자료는 [source index](../reference/source-index.md#kubernetes-disruption)에 있습니다.

## 9. Quota와 capacity는 다릅니다

ResourceQuota는 tenant의 요청 상한을 제한할 수 있지만 cluster에 실제 capacity를 생성하지 않습니다. quota 합계가 cluster capacity보다 클 수도 있습니다.

platform은 다음을 함께 관리합니다.

- tenant quota와 object count
- workload request·limit default
- cluster allocatable과 headroom
- unschedulable backlog
- node provisioning latency
- disruption·upgrade reserve
- 비용 budget

quota 거부와 capacity 부족을 같은 오류로 보고하지 않습니다.

## 10. Cluster와 namespace 선택

새 cluster를 만드는 기준을 “팀 하나당 cluster 하나”로 단순화하지 않습니다.

분리 요인:

- trust와 regulatory boundary
- cluster-scoped API·webhook 충돌
- blast radius와 upgrade cadence
- network·data locality
- scale와 control-plane load
- 비용과 운영 인력
- dedicated hardware 요구

namespace는 가벼운 논리 경계지만 모든 cluster-scoped resource와 node isolation 문제를 해결하지 않습니다. [13장](13-multitenancy-quotas-and-isolation.md)에서 tenant model을 더 자세히 다룹니다.

## 11. 증거를 남기는 진단

예: workload가 schedule되지 않습니다.

```text
platform resource condition
→ namespace quota와 LimitRange
→ Pod request와 scheduling event
→ node allocatable·taint·topology
→ PVC binding과 zone
→ autoscaler/provisioner 상태
→ 최근 policy 또는 profile 변경
```

임시로 request를 줄이거나 taint를 제거하기 전에 어떤 계약을 깨는지 기록합니다.

## 12. 실습 연결

[`05-workload-contract`](../exercises/05-workload-contract/)에서 network·storage·scheduling·disruption 요구까지 포함해 workload contract를 완성합니다.

선택적으로 [`kind Kubernetes lab`](90-optional-labs/01-kind-kubernetes-lab.md)에서 Service, probe, request, NetworkPolicy와 disruption을 로컬 cluster에서 관찰합니다.
