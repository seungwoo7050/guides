# Provider crosswalk 작성법

공급자 제품명은 바뀔 수 있으므로 이 문서는 정답 표가 아니라 mapping 방법을 제공합니다.

| Generic capability | 확인할 질문 | AWS 예시 계열 | Azure 예시 계열 | Google Cloud 예시 계열 |
|---|---|---|---|---|
| VM compute | image, zone, identity, local disk | EC2 | Virtual Machines | Compute Engine |
| virtual network | subnet, route, firewall, egress | VPC | Virtual Network | VPC |
| object storage | version, lifecycle, access, egress | S3 | Blob Storage | Cloud Storage |
| managed relational DB | version, failover, backup, connection | RDS/Aurora 계열 | Azure SQL/managed DB 계열 | Cloud SQL/AlloyDB 계열 |
| managed app runtime | build/deploy, scale, network, version | App Runner/Elastic Beanstalk 계열 | App Service/Container Apps 계열 | App Engine/Cloud Run 계열 |
| function compute | trigger, timeout, concurrency, retry | Lambda | Functions | Cloud Run functions 계열 |
| identity | human/workload, policy, short credential | IAM/STS | Entra ID/managed identity/RBAC | Cloud IAM/service account |
| monitoring | metric, log, audit, trace, cost | CloudWatch/CloudTrail 계열 | Azure Monitor/Activity Log 계열 | Cloud Monitoring/Logging/Audit Logs |

`계열`은 capability 예시일 뿐이며 특정 제품 선택을 권장하지 않습니다. 실제 profile에서 다음을 채웁니다.

```text
provider
service name
region
service model
execution model
control surface
identity
network
state and durability
delivery semantics
limits
maintenance
observability
cost unit
export and deletion
official docs
checked_at
```
