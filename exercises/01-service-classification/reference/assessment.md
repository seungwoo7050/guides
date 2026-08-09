# 서비스 분류 평가

## 판정 기준

service model은 소비자가 얻는 capability와 직접 제어하는 층으로 판정한다. execution model은 workload가 VM·managed instance·function·완성 application 중 어떤 단위로 실행되는지 구분한다. deployment model은 public·private·hybrid 조직 경계를 따로 적는다. `managed`와 `serverless`는 책임 이전의 정도와 runtime lifecycle을 설명하는 보조 표현이며, 제품명 자체를 분류 근거로 사용하지 않는다.

## 사례별 분류

### A

가장 가까운 service model은 IaaS다. 소비자는 VM image, OS, network policy, application과 data lifecycle을 제어한다. 실행 단위는 VM이고 deployment model은 제시된 정보만으로 알 수 없다. 공급자가 physical host를 관리하더라도 OS patch, backup 검증과 instance replacement는 소비자 책임으로 남는다.

### B

PaaS 또는 managed application runtime에 가깝다. 실행 단위는 provider가 관리하는 application instance 또는 container이며, 사용자는 code/image와 application configuration을 소유한다. 공급자는 host·runtime orchestration·health routing 일부를 관리하지만 dependency compatibility, application readiness, data, request failure와 비용 상한은 소비자가 소유한다.

### C

FaaS를 사용하는 managed execution capability다. NIST의 별도 네 번째 service model로 단정하지 않고 PaaS 계열 capability와 serverless execution model을 함께 기록한다. 핵심 계약은 ephemeral environment, timeout, concurrency, at-least-once 가능성, idempotency와 dead-letter다.

### D

소비자 관점의 SaaS다. 고객은 완성된 협업 capability를 사용하며 application과 infrastructure를 직접 운영하지 않는다. 그러나 organization membership, sharing, role, data 입력, integration token, export와 retention 설정은 고객 책임으로 남는다. SaaS 공급자 관점에서는 tenant isolation, entitlement, metering, support access와 deletion이 핵심 상태다.

### E

virtualization capability는 있지만 입력만으로 NIST cloud characteristic을 충족한다고 보기 어렵다. on-demand self-service, measured service와 rapid elasticity가 없으므로 단순 private virtualization service일 수 있다. ticket 자동화, resource pooling의 실제 동작과 사용량 계측을 추가 확인해야 한다.

## 책임 경계

| 작업 | A IaaS | B managed runtime | C FaaS | D SaaS |
|---|---|---|---|---|
| physical host | 공급자 | 공급자 | 공급자 | SaaS 공급자/하위 공급자 |
| OS/runtime patch | 소비자 중심 | 공급자 중심, 호환성은 소비자 | 공급자, 지원 runtime 선택은 소비자 | SaaS 공급자 |
| application code | 소비자 | 소비자 | 소비자 | SaaS 공급자 |
| customer data meaning | 소비자 | 소비자 | 소비자 | 고객과 SaaS 공급자의 계약 |
| scaling configuration | 소비자 | 공동 | 공급자 기능+소비자 limit | SaaS 공급자 |
| identity | cloud IAM 소비자 | workload identity 소비자 | function identity 소비자 | 고객 account 설정+SaaS 공급자 운영 |
| backup restore 검증 | 소비자 | 소비자 | 외부 state 소비자 | SaaS 계약과 고객 요구 |
| cost owner | 소비자 | 소비자 | 소비자 | SaaS 공급자, 고객은 subscription 비용 |

## 실패와 증거

A에서는 instance termination, OS drift와 orphan volume을 inventory·replacement log·backup restore로 확인한다. B에서는 runtime upgrade, scale limit와 provider maintenance를 client metric·deployment version·service event로 확인한다. C에서는 duplicate, timeout과 throttle을 event ID·attempt·DLQ·external effect trace로 확인한다. D에서는 cross-tenant access, support access와 deletion을 negative test·audit·export manifest·deletion inventory로 확인한다.

공급자 metric은 application business success를 증명하지 않고, backup success는 restore 가능성을 증명하지 않는다. SLA는 실제 recovery를 대신하지 않는다.

## 분류의 한계

서비스는 여러 capability를 조합하므로 하나의 label로 모든 책임을 설명할 수 없다. managed database를 쓰는 IaaS application처럼 architecture 전체와 개별 component의 service model이 다를 수 있다. 최종 판정에는 provider의 현재 control surface, version·maintenance, identity, limit, delivery semantics, data export와 비용 문서를 확인해야 한다.
