# Control plane, data plane과 identity

클라우드 시스템은 “서비스에 접근할 수 있다”는 한 문장으로 권한을 설명할 수 없습니다. resource를 생성·변경하는 경로와 workload data를 읽고 쓰는 경로가 다르기 때문입니다.

```text
control plane
resource의 존재·설정·정책·배치를 변경합니다.

management data plane
log·backup·secret·artifact처럼 운영 상태를 다룹니다.

application data plane
사용자 request와 business data를 처리합니다.
```

공급자마다 용어와 경계가 다를 수 있지만, 권한·감사·사고 범위를 나누는 사고 모델로 유용합니다.

## 1. Control plane

control plane 작업의 예:

- VM·database·function 생성과 삭제
- network와 route 변경
- IAM role·policy 연결
- backup retention 변경
- autoscaling limit 변경
- logging 비활성화
- key policy 변경
- region 또는 replication topology 변경

control plane compromise는 실행 중인 workload code를 직접 바꾸지 않아도 시스템 전체를 재구성할 수 있습니다.

### 중요한 상태

- desired configuration
- resource identity
- policy binding
- deployment version
- operation status
- audit event
- lock과 approval

### 중요한 불변식

```text
production 변경은 승인된 identity만 수행합니다.
변경은 audit event와 change ID를 가집니다.
중요 log·backup·key를 workload identity가 삭제할 수 없습니다.
```

## 2. Data plane

application data plane은 사용자 요청, object read, database query, queue publish 같은 실제 업무 처리를 수행합니다.

control plane 권한이 없어도 data plane token이 유출되면 데이터 침해가 발생할 수 있습니다. 반대로 data plane 접근이 없어도 control plane 권한으로 snapshot을 복제하거나 network를 공개할 수 있습니다.

따라서 두 경로를 별도 위협 모델로 다룹니다.

## 3. Identity의 종류

### Human identity

개발자, 운영자, 지원 담당자와 감사자입니다. 개인별 계정, 강한 인증, 짧은 privileged session과 승인 흐름이 필요합니다.

### Workload identity

VM, container, function, job와 service가 다른 resource에 접근할 때 사용하는 identity입니다. 장기 access key를 파일이나 environment에 넣는 방식보다 runtime이 짧은 credential을 발급받는 방식이 안전합니다.

### Automation identity

CI/CD, IaC runner, backup job, security scanner처럼 control plane 또는 운영 작업을 수행합니다. workload identity와 비슷하지만 변경 범위·승인·audit 요구가 더 강할 수 있습니다.

### Customer identity

SaaS 사용자와 tenant member입니다. cloud IAM과 application authorization을 동일시하면 안 됩니다. 고객 role은 business object 접근을 제어하고, cloud IAM은 infrastructure resource 접근을 제어합니다.

### Provider identity

공급자 운영자와 service principal이 내부적으로 resource를 관리합니다. 소비자가 직접 보지 못하는 경계가 있을 수 있으므로 service contract, audit capability와 support process를 확인합니다.

## 4. Authentication, authorization와 delegation

- authentication: identity가 누구인지 확인합니다.
- authorization: 특정 action을 특정 resource에 허용할지 결정합니다.
- delegation: 한 identity가 제한된 범위를 다른 identity에 맡깁니다.
- impersonation: 지원·운영 목적 등으로 다른 사용자 관점에서 작업합니다.

SaaS support 기능에서는 impersonation을 숨겨진 관리자 bypass로 만들지 않아야 합니다.

필요한 상태:

```text
who
for which tenant
for which resource
action
reason or ticket
approved_by
starts_at
expires_at
result
audit_event
```

## 5. Policy의 네 질문

1. Principal은 누구입니까?
2. Action은 무엇입니까?
3. Resource scope는 어디까지입니까?
4. 어떤 condition에서 허용합니까?

`admin` 같은 포괄 역할보다 실제 task를 표현합니다.

```text
backup-restore-runner
- restore artifact 읽기
- isolated restore environment 생성
- production overwrite 금지
- 60분 후 credential 만료
```

## 6. Resource hierarchy와 blast radius

cloud provider는 account·organization·subscription·project·folder·resource group 같은 hierarchy를 제공합니다. 이름은 다르지만 다음 목적을 가집니다.

- ownership 분리
- policy inheritance
- billing allocation
- quota와 limit
- environment isolation
- audit boundary

한 production account 안에 모든 실험 자원을 넣으면 잘못된 policy·route·quota 변경의 blast radius가 커집니다. 반대로 너무 잘게 나누면 identity, network, inventory와 비용 관리가 복잡해집니다.

분리 기준:

- 신뢰 수준
- data sensitivity
- lifecycle
- cost owner
- administrator
- failure independence
- 규제·감사 경계

## 7. Metadata와 ambient credential

VM·container·function runtime은 identity metadata 또는 credential endpoint를 제공할 수 있습니다. 애플리케이션 code가 별도 secret 없이 credential을 얻는 장점이 있지만, SSRF·sandbox escape·과도한 role이 결합되면 공격 경로가 됩니다.

검토:

- metadata endpoint에 어떤 process가 접근할 수 있습니까?
- credential scope와 lifetime은 얼마입니까?
- token audience와 resource condition이 있습니까?
- outbound request가 임의 endpoint로 향할 수 있습니까?
- credential 사용 event를 기록합니까?

구체적인 SSRF와 공격 검증은 `cybersecurity`가 소유하고, 이 브랜치에서는 cloud identity의 상태와 blast radius를 다룹니다.

## 8. Secret와 configuration

secret은 application configuration의 일부이지만 동일하게 다루면 안 됩니다.

- source repository에 포함하지 않습니다.
- image에 bake하지 않습니다.
- runtime identity로 필요한 시점에 읽습니다.
- version과 rotation 상태를 가집니다.
- log와 error에 plaintext를 남기지 않습니다.
- previous·candidate·current·revoked 상태를 구분합니다.

managed secret service를 사용해도 application이 rotation을 견디는지와 old credential을 폐기했는지는 소비자의 책임입니다.

## 9. Audit evidence

control plane audit는 최소한 다음을 복원해야 합니다.

- actor identity와 session
- source context
- action과 resource
- request parameter의 안전한 subset
- allow·deny
- operation ID
- time
- result

data plane audit는 volume과 비용이 크므로 risk에 따라 선택합니다. tenant export·admin read·key use·backup restore처럼 민감한 action은 별도 event가 필요합니다.

Audit log 자체도 보호해야 합니다.

- workload와 분리된 storage
- append 또는 tamper-evident 정책
- 충분한 retention
- time synchronization
- restricted delete
- incident 시 export 경로

## 10. Break-glass

정상 identity provider나 automation이 실패했을 때 사용할 emergency access가 필요할 수 있습니다. break-glass는 평소 사용 가능한 super-admin 계정이 아닙니다.

- 제한된 수
- 강한 보관
- 사용 조건과 승인
- 즉시 alert
- 짧은 session
- 사용 후 credential rotation
- 사후 review

## 11. 사고 시 분리 질문

1. control plane configuration이 바뀌었습니까?
2. workload code나 image가 바뀌었습니까?
3. data plane credential이 사용됐습니까?
4. tenant 또는 resource scope가 어디까지입니까?
5. log와 backup을 공격자가 변경할 수 있었습니까?
6. credential revoke 뒤 cached session이 남습니까?
7. clean account/project에서 재구축할 수 있습니까?

## 연결 실습

[03 managed service 계약](../exercises/03-managed-service-contract/README.md)에서 사람·workload·automation identity와 control/data plane action을 책임표에 분리합니다. [05 SaaS tenant isolation](../exercises/05-saas-tenant-isolation/README.md)에서는 cloud IAM과 application tenant authorization을 혼동하지 않도록 검토합니다.
