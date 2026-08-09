# IaaS compute, network와 storage

IaaS는 물리 장비 대신 API로 compute·network·storage를 조합하게 합니다. 그렇다고 기존 host 운영 책임이 사라지는 것은 아닙니다. 오히려 resource가 빠르게 생성·교체되므로 **정본 상태, 수명, 연결, identity와 cleanup**을 명시해야 합니다.

## 1. Resource inventory가 시작점이다

IaaS architecture를 diagram만으로 관리하면 실제 resource와 owner가 어긋나기 쉽습니다. 최소 inventory 필드는 다음과 같습니다.

```text
resource_id
resource_type
account_or_project
region
zone
owner
purpose
environment
data_classification
created_by
created_at
expires_at
dependencies
stateful
backup_policy
cost_center
```

resource name은 identity가 아닙니다. 이름을 재사용하거나 사람이 바꿀 수 있으므로 provider ID와 별도 business key를 구분합니다.

## 2. Compute instance

VM instance는 다음 상태를 가집니다.

- base image
- boot disk
- instance configuration
- network interface
- workload identity
- user data 또는 startup script
- local ephemeral storage
- runtime process와 local cache

### Immutable과 mutable

instance를 장기간 수동 변경하면 실제 상태가 선언과 달라집니다.

```text
새 image 또는 declarative bootstrap
→ 새 instance 생성
→ readiness 검증
→ traffic 전환
→ 이전 instance 종료
```

이 방식은 복구와 scale-out을 쉽게 하지만 database migration, local state와 in-flight request를 별도로 처리해야 합니다.

### Image 계약

- 정확한 image ID와 build source
- OS와 package version
- vulnerability와 지원 종료
- startup dependency
- embedded secret 부재
- boot 뒤 readiness 조건
- 이전 image로 rollback 가능성

## 3. Network

IaaS virtual network는 다음 객체의 조합입니다.

- address range
- subnet
- route table
- network interface
- public/private address
- firewall 또는 security rule
- NAT·egress
- load balancer
- private endpoint
- DNS

“private subnet”이라는 이름이 실제 isolation을 증명하지 않습니다. route, public address, peering, endpoint와 firewall을 함께 확인해야 합니다.

### Ingress와 egress

Ingress만 제한하고 egress를 모두 허용하면 compromised workload가 외부로 연결하거나 다른 service에 접근할 수 있습니다. 반대로 egress를 과도하게 막으면 patch, package, identity, telemetry 경로가 깨집니다.

필요한 기록:

```text
source identity 또는 network
destination service
protocol과 port
purpose
DNS dependency
proxy 또는 inspection
failure behavior
owner
```

### Load balancer

load balancer가 healthy target만 선택한다는 주장은 health check가 올바를 때만 성립합니다.

- process alive와 application ready를 구분합니다.
- dependency 전체를 readiness에 묶어 cascading removal을 만들지 않습니다.
- drain timeout과 long-lived connection을 고려합니다.
- client IP·TLS termination·request ID 전달을 확인합니다.
- zonal target 분포와 cross-zone behavior를 확인합니다.

## 4. Storage 유형

### Block storage

filesystem 또는 database volume처럼 instance에 block device로 연결합니다.

검토:

- attachment scope와 zone 제한
- single/multi attach 의미
- snapshot consistency
- encryption key
- detach·reattach 순서
- filesystem repair
- volume 삭제 보호

### Object storage

object key와 metadata로 접근합니다. filesystem rename·locking·partial write와 같은 의미를 그대로 가정하면 안 됩니다.

검토:

- object versioning
- overwrite·delete semantics
- lifecycle policy
- retention 또는 legal hold
- multipart upload 잔존
- public access
- tenant key prefix
- inventory와 checksum
- request·storage·egress 비용

### Ephemeral/local storage

instance 또는 execution environment 수명과 함께 사라질 수 있습니다. cache와 scratch에는 적합하지만 정본 상태로 사용하면 안 됩니다.

### Managed database

IaaS의 단순 storage가 아니라 PaaS/managed service에 가깝습니다. database 내부 계약은 [managed service 문서](06-paas-and-managed-service-contracts.md)에서 다룹니다.

## 5. State classification

resource별로 다음을 분류합니다.

| 상태 | 예 | instance 교체 시 처리 |
|---|---|---|
| reproducible | image, deployment config | source에서 다시 생성 |
| durable authoritative | database, object | 외부 durable service와 backup |
| derived | search index, thumbnail | 정본에서 재생성 |
| ephemeral | temp file, local cache | 손실 허용 |
| evidence | audit, metric, trace | workload 밖으로 전송·보존 |

이 분류 없이 “instance를 버릴 수 있다”는 주장은 성립하지 않습니다.

## 6. Bootstrap과 configuration

startup script는 다음 실패를 고려합니다.

- package repository 지연
- DNS 실패
- secret 미발급
- database migration 경쟁
- 같은 script 재실행
- 일부 단계 성공 뒤 중단
- log에 secret 노출

bootstrap은 반복 가능하고, 실패 지점과 최종 상태를 남기며, readiness 전에 완료돼야 합니다. 복잡한 build를 startup 때 수행하기보다 image build 단계로 옮기는 편이 재현성이 높습니다.

## 7. Resource dependency와 deletion

생성 순서:

```text
identity와 policy
→ network
→ storage·database
→ compute
→ load balancer·DNS
→ telemetry와 alert
```

삭제 순서는 단순 역순이 아닐 수 있습니다.

- DNS TTL과 traffic drain
- final backup·export
- retention lock
- log 보존
- key 폐기 시점
- shared resource 참조
- billing 종료 확인

resource graph에 owner와 deletion condition을 기록합니다.

## 8. Failure 사례

### Instance loss

- load balancer가 제거합니까?
- replacement가 같은 image와 configuration으로 생성됩니까?
- local state 손실이 허용됩니까?
- capacity와 quota가 남아 있습니까?

### Network rule 오류

- control plane audit에서 변경 actor를 찾을 수 있습니까?
- management access가 끊겼을 때 복구 경로가 있습니까?
- overly broad rule을 자동 검출합니까?

### Disk full 또는 volume loss

- application이 read-only 또는 fail-fast로 전환합니까?
- snapshot이 crash-consistent입니까?
- restore 뒤 application invariants를 확인합니까?

### Orphan resource

- unattached volume, idle address, snapshot, load balancer, NAT와 log sink가 남아 있습니까?
- resource tag와 cost owner가 있습니까?
- delete workflow가 inventory를 갱신합니까?

## 9. 검증 증거

- resource inventory export
- image digest 또는 immutable ID
- network path test
- private resource negative access test
- replacement instance bootstrap log
- backup·restore report
- instance termination 뒤 user-facing result
- cleanup diff와 billing status

## 연결 실습

[02 IaaS failure domain](../exercises/02-iaas-failure-domains/README.md)에서 합성 architecture의 resource inventory, zone 배치, state lifetime과 failure injection을 작성합니다.
