# 보안 검토와 release 결정

보안 검토는 취약점이 “0개”임을 선언하는 행사가 아닙니다. 현재 release가 어떤 자산과 위협을 다루며, 어떤 evidence가 있고, 어떤 잔여 위험을 누가 수용하는지 결정하는 과정입니다.

## 1. review packet

최소 자료:

```text
release scope와 exact artifact
system context·data classification
threat model과 변경된 trust boundary
security requirements
open·closed finding
security test·known-bad 결과
identity·secret·network policy
SBOM·provenance·dependency status
telemetry·detection·runbook
backup·restore·rollback evidence
exception·residual risk
```

문서가 많다는 사실보다 서로 traceable한지가 중요합니다.

## 2. 변경 중심 검토

전체 시스템을 매번 처음부터 검토하지 않습니다. 다음을 확인합니다.

- 새 component·endpoint·identity·data flow
- permission·scope·default 변경
- dependency·build·registry·deployment 경로 변경
- security control 제거·fallback·exception
- sensitive data와 retention 변경
- logging·backup·recovery 영향
- 이전 finding과 attack path 재개 가능성

## 3. evidence quality

각 evidence에 다음을 적습니다.

```text
source revision·artifact digest
실행 environment
실행 시점
검사 owner
test scope
known limitation
expiry·re-run trigger
```

오래된 penetration test나 다른 configuration의 scan을 현재 release evidence로 그대로 사용하지 않습니다.

## 4. open finding 판단

open finding마다:

- `validation_status`: confirmed·false-positive·not-reproducible·unknown
- `treatment`: remediate·mitigate·accept·defer·not-applicable
- `lifecycle_status`: open·assigned·in-progress·ready-for-retest·closed·reopened
- duplicate라면 별도 `duplicate_of` 관계
- current exposure와 attack path
- severity와 조직 priority
- compensating control과 runtime evidence
- owner·target date
- release block 여부
- monitoring·incident readiness

세 축을 하나의 상태로 합치지 않습니다. `accepted risk`는 validation 상태가 아니며,
`accept`는 confirmed finding에 대해서만 조직의 authorized risk acceptance authority가
scope·owner·expiry·compensating control·monitoring·re-review trigger와 함께 선택할 수 있습니다.
false-positive·not-reproducible·unknown에는 상태에 맞는 반증 근거, 미확인 범위, 다음 안전한
evidence와 reopen 조건을 남깁니다. 확인하지 못한 finding을 `not-applicable`로 닫지 않습니다.

서로 독립적인 low finding이 하나의 critical path를 만들 수 있는지 봅니다.

## 5. go·conditional go·no-go

### Go

필수 requirement와 release gate가 충족되고 잔여 위험이 수용 범위입니다.

### Conditional go

명시된 condition·owner·expiry·monitoring 아래 release합니다.

예:

```text
admin endpoint는 public exposure 없이 internal network와 JIT identity로 제한
7일 안에 root fix 배포
특정 detection rule과 daily review 유지
authorized risk acceptance authority 승인
```

conditional go는 monitoring만 추가해 취약 상태를 정상화하는 결정이 아닙니다. monitoring은
첫 impact를 예방하지 못하고 event가 없거나 pipeline이 실패한 공격을 보지 못합니다. condition은
attack-path edge를 줄이는 control, owner, 기한, 확인할 runtime evidence, alert 뒤 response 시간,
rollback·incident trigger와 expiry 뒤 자동 재승인 금지를 함께 포함합니다.

### No-go

다음과 같은 경우 release를 중단할 수 있습니다.

- 중요 asset에 대한 uncontrolled authorization failure
- release gate로 요구한 artifact identity·signature·provenance를 검증하지 못함
- 실제 유효 credential 노출과 revoke 불가
- destructive migration·rollback 부재
- required audit·incident evidence 부재
- 범위·version 불명확으로 결과 신뢰 불가

유효한 signature·provenance도 source·builder·review의 안전을 자동 증명하지 않습니다. no-go
판단은 “서명이 있으므로 안전함”이 아니라 요구한 trust chain과 exact artifact를 확인할 수
있는지에 근거합니다.

## 6. reviewer, risk owner와 acceptance authority

보안 팀이 모든 business risk를 대신 수용하지 않습니다. 자산·제품·운영의 risk owner는
기술 evidence를 바탕으로 impact와 treatment를 소유하고, formal acceptance는 조직이 지정한
authority가 결정합니다.

reviewer는 다음을 명확히 합니다.

- 무엇이 확인됐는가?
- 무엇이 확인되지 않았는가?
- 악용 전제와 영향은 무엇인가?
- 어떤 control이 실제 적용됐는가?
- release를 미루거나 진행할 때 비용·위험은 무엇인가?

역할을 다음처럼 구분합니다.

| 역할 | 책임 | 자동으로 갖지 않는 권한 |
|---|---|---|
| security reviewer | scope·threat·test·limitation을 평가하고 gate 충족 여부를 보고 | business risk acceptance |
| risk owner | asset·서비스 impact와 remediation 책임을 소유 | 조직 절차 밖의 공식 acceptance |
| risk acceptance authority | 정해진 범위·기간의 residual risk를 조직 정책에 따라 승인 | finding의 기술적 사실 변경 |
| release authority | evidence와 승인 상태를 바탕으로 배포 여부를 결정 | 미승인 risk를 임의 수용 |

조직에 따라 한 사람이 여러 역할을 맡을 수 있지만 decision record에는 어떤 authority로
서명했는지와 delegation 근거를 남깁니다. reviewer가 test를 통과시켰거나 security team이
조건부 진행을 추천했다는 사실만으로 risk acceptance가 되지 않습니다. 공식 authority,
규제·법무 적합성과 감사 workflow는 조직의 GRC·법무 정본을 따릅니다.

## 7. exception 관리

exception에는 반드시:

```text
requirement·finding ID
scope
justification
compensating control
owner
approval
start·expiry
monitoring
remediation milestone
re-review trigger
```

expiry가 지나면 자동 승인 상태를 유지하지 않습니다.

## 8. release 뒤 확인

- 실제 runtime digest·configuration
- security smoke와 policy deny
- new event·alert health
- old credential·artifact 차단
- migration·data integrity
- external exposure
- error·performance regression

release 전에 통과한 test가 production wiring을 자동 증명하지 않습니다.

production validation은 사전 승인된 비파괴 검사로 제한합니다.

- synthetic identity·tenant·data와 전용 correlation ID 사용
- 허용 endpoint·action, request rate·time·resource budget 명시
- write가 필요하면 격리된 synthetic resource와 cleanup·reconciliation 증거 준비
- 실제 credential 탈취·권한 상승·destructive payload·무단 scanner 사용 금지
- privacy·availability 이상, 범위 이탈, cleanup 실패 시 즉시 중단·escalation

“production validation 계획”은 실행 evidence가 아니며, staging이나 합성 요청의 성공도
실제 공격자 input 전체와 모든 path의 안전을 증명하지 않습니다. 결과에는 exact release,
실행 시각, 관찰한 decision·state·event, 생략한 path와 알려진 한계를 남깁니다.

## 9. re-review trigger

- emergency patch·rollback
- identity·permission·network change
- new exploitation·advisory
- dependency·base image update
- data classification·retention change
- incident·near miss
- expired evidence·exception
- logging·backup·recovery degradation

## 10. review 결과 문서

```text
Decision
Release identifier
Scope
Evidence summary
Open risks
Required conditions
Risk owner and approver
Monitoring period
Rollback·incident trigger
Next review date
```

“보안 승인”이라는 한 줄 대신 조건과 한계를 남깁니다.

## 11. NIST CSF와 연결

NIST CSF 2.0의 Govern·Identify·Protect·Detect·Respond·Recover는 보안 검토에서 빠진 수명 주기를 확인하는 상위 지도입니다.

- Govern: owner·risk·policy·supply chain
- Identify: asset·context·threat·current risk
- Protect: requirement·access·data·platform control
- Detect: telemetry·analytic·health
- Respond: escalation·containment·communication
- Recover: restore·rebuild·improvement

framework category를 채우는 것보다 자신의 release evidence에 연결합니다.

공개 서비스의 TLS·CI/CD·backup·rollback 구현은 `web-infra`, 여러 팀의 공통 policy·identity·
telemetry와 self-service gate 구현은 `platform-engineering`의 정본입니다. 이 브랜치는 해당
control을 복제하지 않고 threat·finding·test·incident evidence로 release 위험을 판단합니다.
조직 규제·감사 전체와 공식 risk acceptance 절차는 GRC·법무 담당 범위이며 이 checklist가
그 승인을 대체하지 않습니다.

## 12. 이 장의 산출물

Capstone release에 대해 다음을 작성합니다.

1. review packet index
2. changed boundary
3. requirement·test·event traceability
4. open finding과 attack-path context
5. evidence age·limitation
6. go·conditional go·no-go 결정
7. exception과 risk owner
8. production validation
9. re-review trigger
10. reviewer·risk owner·acceptance authority·release authority 근거
11. conditional-go monitoring의 blind spot과 response·expiry 조건

[보안 검토 checklist](../reference/security-review-checklist.md)를 사용합니다.

## 13. 완료 질문

- finding 0개가 안전을 증명하지 못하는 이유는 무엇입니까?
- release evidence가 다른 version·environment이면 어떤 문제가 생깁니까?
- conditional go에 반드시 필요한 조건은 무엇입니까?
- security reviewer와 risk owner의 책임은 어떻게 다릅니까?
- release 뒤 production validation이 필요한 이유는 무엇입니까?
- risk owner와 risk acceptance authority가 항상 같은 역할이 아닌 이유는 무엇입니까?
- synthetic production validation이 보장하지 못하는 범위는 무엇입니까?
