# Cloud security, observability와 incident

클라우드 보안은 방화벽 규칙 몇 개나 “암호화 enabled” 표시로 끝나지 않습니다. control plane, workload runtime, managed service, tenant data와 evidence가 서로 다른 identity와 수명을 가지므로 **누가 무엇을 바꿀 수 있고, 침해가 어느 resource·tenant·시간 범위에 미쳤는지** 복원해야 합니다.

일반 위협 모델과 사고 대응 절차는 각각 [`cybersecurity`의 assets·trust boundaries·threat models](https://github.com/seungwoo7050/guides/blob/cybersecurity/docs/02-assets-trust-boundaries-and-threat-models.md)와 [incident response·recovery](https://github.com/seungwoo7050/guides/blob/cybersecurity/docs/14-incident-response-and-recovery.md)가 소유합니다. 이 문서는 account/project, control plane, workload identity, managed resource와 tenant별 evidence라는 cloud 고유 상태만 연결합니다.

## 1. Shared responsibility의 보안 의미

공급자는 physical facility와 managed capability 일부를 보호하지만, 소비자는 최소한 다음을 소유합니다.

- account·organization 구조
- human과 workload identity
- resource policy
- network exposure
- application authorization
- data classification
- key와 secret 사용
- logging과 alert 설정
- backup·restore 검증
- configuration drift
- tenant isolation
- incident response

“cloud provider가 secure하다”와 “우리 architecture가 secure하다”는 다른 주장입니다.

## 2. Account와 organization boundary

account·subscription·project는 billing container만이 아니라 blast radius와 policy boundary입니다.

분리 기준:

- production·non-production
- sensitive·general data
- team ownership
- customer-dedicated environment
- security tooling
- log archive
- backup vault
- experimentation

중앙 security account가 모든 production resource를 직접 변경할 수 있으면 compromise blast radius가 커질 수 있습니다. 반대로 지나친 분리는 monitoring과 response를 복잡하게 합니다.

## 3. Identity security

- human은 개인 account와 MFA를 사용합니다.
- privileged access는 필요 시 짧은 session으로 승격합니다.
- workload는 long-lived static key보다 runtime identity를 사용합니다.
- CI/CD는 environment·repository·artifact scope를 제한합니다.
- support access는 reason·tenant·expiry와 audit를 가집니다.
- break-glass는 평상시 사용하지 않고 사용 즉시 alert합니다.

권한 검토는 role name이 아니라 실제 action-resource-condition을 확인합니다.

## 4. Resource exposure

public IP가 없다고 private한 것은 아닙니다. 다음 경로를 함께 확인합니다.

- public endpoint
- peering·transit
- private endpoint
- VPN
- service-to-service network
- identity-based access
- pre-signed URL
- support channel
- backup copy
- logging export

network와 identity를 교차 검토합니다. overly broad identity는 private network 안에서도 위험하고, strict identity도 public exploit surface를 없애지는 않습니다.

## 5. Key와 secret

cloud key service를 사용하면 key material을 직접 저장하지 않을 수 있지만 다음 책임은 남습니다.

- key policy
- encrypt/decrypt principal
- region·replication
- rotation
- disable·delete delay
- backup dependency
- audit
- key loss 시 recovery

key를 먼저 삭제하면 backup·archive를 영구히 읽지 못할 수 있습니다. data lifecycle과 key lifecycle을 함께 설계합니다.

## 6. Supply chain

cloud workload는 다음 artifact를 신뢰합니다.

- base image
- package
- container image
- function bundle
- IaC module
- CI action
- provider extension
- policy template

확인:

- source와 build
- immutable identity
- signature·provenance
- dependency version
- scanner 결과의 범위
- deploy authorization
- rollback artifact

일반 공급망 보안은 [`cybersecurity`의 supply-chain·build trust](https://github.com/seungwoo7050/guides/blob/cybersecurity/docs/08-supply-chain-and-build-trust.md), 단일 서비스의 registry·release artifact 운영은 [`web-infra`](https://github.com/seungwoo7050/guides/blob/web-infra/docs/11-image-registry-and-release-artifacts.md)가 소유합니다. 여기서는 cloud runtime identity, function bundle·managed extension, deploy authorization과 control-plane audit 연결만 검토합니다.

## 7. Observability 계층

### Control plane

- resource create/update/delete
- policy·identity change
- log disable
- key operation
- network change
- quota change

### Resource plane

- instance health
- database replica·connection
- queue depth
- function concurrency·throttle
- storage request

### Application plane

- request·trace
- business error
- tenant action
- entitlement decision
- external effect

### Cost plane

- usage
- daily cost
- anomaly
- untagged resource
- commitment utilization

계층을 request ID, resource ID, deployment version와 tenant ID로 연결합니다.

## 8. Log design

log에 secret·token·sensitive payload를 남기지 않습니다. 그러나 redaction 때문에 incident에 필요한 identity와 resource를 모두 잃어서도 안 됩니다.

권장 필드:

```text
time
account_or_project
region
resource_id
action
actor_or_workload_identity
tenant_id_if_applicable
request_id
change_id
deployment_version
result
reason_code
source_context
```

로그 저장소는 workload write 권한과 분리하고 retention·immutability·export를 검토합니다.

## 9. Detection hypothesis

좋은 alert는 “error > 0”보다 공격·운영 가설을 표현합니다.

- production에서 interactive admin role 사용
- logging 또는 backup policy disable
- public access enable
- key policy가 broad principal로 변경
- function concurrency가 비정상 급증
- 한 tenant의 cross-region export
- orphan resource 급증
- break-glass 사용
- unexpected region resource 생성

alert에는 owner, severity, evidence query와 first response가 있어야 합니다.

## 10. Incident scope

cloud incident에서 다음 scope를 분리합니다.

- identity scope
- account/project scope
- resource scope
- region scope
- data scope
- tenant scope
- time window
- artifact/deployment version

credential 하나가 여러 account를 assume할 수 있으면 실제 scope가 커집니다. resource policy와 audit를 따라가야 합니다.

## 11. Containment

가능한 조치:

- session·key revoke
- role assumption 차단
- public route 또는 endpoint 제거
- function trigger disable
- compromised image deployment 중단
- tenant suspend
- affected account isolation
- snapshot·log preservation

위험:

- evidence 삭제
- backup·log 접근도 함께 차단
- production 전체 중단
- attacker가 남긴 automation을 놓침
- dependency가 다른 경로로 계속 호출

containment 전에 owner와 reversible action을 확인합니다.

## 12. Recovery

깨끗한 상태를 정의합니다.

- trusted account·identity
- verified artifact
- known configuration
- rotated secret·key
- restored data
- validated tenant isolation
- active monitoring
- blocked persistence path

compromised resource를 직접 고치는 것보다 clean environment로 rebuild하는 편이 신뢰성이 높을 수 있습니다.

## 13. Evidence preservation

- control plane audit export
- resource configuration snapshot
- network flow 또는 access log
- instance disk snapshot이 필요한지 검토
- function version과 bundle
- identity policy history
- key usage log
- billing·usage anomaly
- provider support case

개인정보와 tenant data를 포함할 수 있으므로 evidence 접근·보존·삭제 정책이 필요합니다.

## 14. 검토 질문

1. workload가 자신의 audit·backup을 삭제할 수 있습니까?
2. tenant-level incident scope를 구분할 수 있습니까?
3. control plane 변경과 application request를 같은 timeline에 놓을 수 있습니까?
4. credential revoke 뒤 asynchronous job이 계속 실행됩니까?
5. clean account/project에서 exact artifact를 재배포할 수 있습니까?
6. incident 중 비용 폭주를 감지하고 제한할 수 있습니까?

## 연결 실습

[02 IaaS failure domain](../exercises/02-iaas-failure-domains/README.md)과 [05 SaaS isolation](../exercises/05-saas-tenant-isolation/README.md)에서 필요한 audit field와 alert hypothesis를 작성합니다.
