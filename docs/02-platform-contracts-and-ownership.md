# 플랫폼 계약과 책임 경계

## 1. 플랫폼은 결과를 약속하는 API입니다

플랫폼의 핵심은 UI나 cluster가 아니라 **사용자가 요청할 수 있는 결과와 그 결과의 상태를 설명하는 계약**입니다.

예:

```text
사용자 요청
ServiceEnvironment checkout/staging을 생성합니다.

플랫폼 약속
- 소유자와 cost center가 유효한지 검사합니다.
- 선택한 runtime profile의 namespace와 workload identity를 준비합니다.
- deployment target과 DNS endpoint를 생성합니다.
- 정책과 상태를 condition으로 보고합니다.
- 취소 또는 폐기 요청을 반복 실행 가능하게 처리합니다.

서비스 팀 책임
- build 가능한 source와 health endpoint를 제공합니다.
- resource request와 데이터 의존성을 선언합니다.
- application SLO와 on-call을 소유합니다.
- schema migration과 업무 데이터 복구를 소유합니다.
```

이 경계가 없으면 platform team이 application 오류까지 떠안거나, service team이 기반의 내부 구현에 직접 의존합니다.

## 2. 계약의 다섯 층

### 요청 계약

- resource 이름과 identity
- 필수·선택 입력
- default가 적용되는 시점
- validation과 정책 거부
- idempotency key 또는 stable resource identity

### 상태 계약

- 현재 generation과 observed generation
- `Pending`, `Reconciling`, `Ready`, `Degraded`, `Deleting` 같은 phase 또는 condition
- 사용자 수정이 필요한 오류와 자동 재시도 중인 오류
- 마지막 성공 revision과 evidence link

### 결과 계약

- endpoint, identity, environment ID, artifact revision
- catalog와 dashboard URL
- 다른 automation이 소비할 stable output
- 민감하지 않은 정보와 secret reference의 구분

### 운영 계약

- SLO와 지원 시간
- platform team과 service team의 on-call 경계
- incident severity와 escalation
- emergency change와 break-glass

### 수명 계약

- create·update·suspend·resume·delete
- retention과 cleanup
- API version과 compatibility
- deprecation과 migration deadline

## 3. 정본과 writer를 하나씩 정합니다

같은 상태를 여러 controller와 사람이 동시에 관리하면 drift가 정상 상태가 됩니다.

예:

| 상태 | 정본 | 허용 writer |
|---|---|---|
| service owner | catalog metadata repository | service owner PR + catalog validator |
| cloud network | IaC configuration/state | infrastructure pipeline |
| workload desired state | GitOps desired-state repository | release promotion automation |
| live workload | Kubernetes API | GitOps/controller와 Kubernetes controller |
| production secret value | secret manager | authorized rotation workflow |
| platform request status | platform control-plane store | 해당 resource controller |

`kubectl edit`, cloud console과 ad-hoc script가 정본을 우회하면 긴급 변경 절차로 기록하고 정해진 시간 안에 정본으로 되돌립니다.

## 4. 책임을 작업이 아니라 실패로 나눕니다

RACI 표만으로는 장애 중 경계가 모호합니다. 다음처럼 실패 단위로 기록합니다.

| 실패 | 1차 소유자 | 필요한 협업 |
|---|---|---|
| platform API가 요청을 저장하지 못함 | platform team | storage owner |
| IaC plan이 destructive change를 포함 | infrastructure owner | 요청 service owner |
| workload가 readiness를 통과하지 못함 | service team | platform은 status와 evidence 제공 |
| cluster capacity 부족으로 schedule 실패 | platform team | service는 request 조정 가능 |
| application schema migration 실패 | service/data owner | platform은 배포 중단과 rollback 경계 제공 |
| admission policy가 정상 workload를 차단 | policy owner | service team 재현 정보 제공 |
| secret rotation 뒤 application 인증 실패 | secret workflow owner + service owner | platform identity owner |

“platform이 제공합니다”보다 “어떤 실패를 누가 복구합니다”가 더 정확한 경계입니다.

## 5. Abstraction은 누출될 수 있음을 인정합니다

플랫폼이 underlying system을 완전히 숨기면 사용자는 장애를 설명할 수 없습니다. 반대로 모든 Kubernetes와 cloud 세부를 노출하면 self-service의 가치가 사라집니다.

좋은 abstraction은 다음을 제공합니다.

- 일반 경로에서는 작은 입력 집합과 안전한 default
- status에 실패한 dependency와 evidence link
- 고급 사용자를 위한 제한된 profile과 extension point
- platform 내부 object와 사용자 resource의 추적 관계
- escape hatch의 owner·기간·지원 수준

예: 사용자가 `resourceTier: medium`을 선택하더라도 실제 CPU·memory request, quota 영향과 예상 비용을 확인할 수 있어야 합니다.

## 6. Escape hatch를 계약으로 만듭니다

표준 경로로 처리할 수 없는 workload는 존재합니다. escape hatch를 금지하면 shadow platform이 생기고, 무제한 허용하면 golden path가 무의미해집니다.

필수 항목:

- 요청 이유와 표준 경로가 부족한 근거
- 추가 권한과 blast radius
- 소유자와 승인자
- 지원 책임
- 시작·만료 날짜
- 정본 상태와 audit 위치
- 표준 경로로 돌아올 조건

예외는 영구적인 두 번째 기본 경로가 아닙니다.

## 7. Shared responsibility를 사용자 화면에 드러냅니다

계약 문서는 platform team 내부에만 두지 않습니다. catalog 또는 API status에서 다음을 찾을 수 있어야 합니다.

- service owner와 platform capability owner
- 현재 release와 platform profile version
- SLO와 support channel
- runbook과 dashboard
- active exception과 만료일
- deprecated dependency와 migration 상태

사용자가 장애 때 담당자를 추측하지 않게 합니다.

## 8. API version과 capability version을 구분합니다

platform API의 schema가 같아도 구현 profile이 달라질 수 있습니다.

```text
API version: platform.example.io/v1
runtime profile: kubernetes-standard@3.4
policy bundle: baseline@2026-08
service template: java-http@7
```

각 version의 compatibility와 migration 책임을 별도로 기록합니다. `latest`만 사용하면 어떤 변경이 workload에 적용됐는지 재현하기 어렵습니다.

## 9. 계약 검토 질문

- 사용자 입력이 실제 underlying implementation과 불필요하게 결합돼 있습니까?
- 비동기 완료를 단순 HTTP `200`으로 오해하게 만들지 않습니까?
- 같은 자원을 둘 이상의 writer가 관리합니까?
- 삭제 중 외부 자원 정리가 실패하면 누가 재시도합니까?
- platform SLO와 workload SLO가 혼합돼 있습니까?
- escape hatch가 만료와 owner 없이 남을 수 있습니까?
- API 또는 profile upgrade의 compatibility가 선언돼 있습니까?

## 10. 실습

[`02-platform-contract`](../exercises/02-platform-contract/)에서 하나의 capability에 대해 요청·상태·결과·실패 소유권·escape hatch·수명 계약을 작성합니다.

reference와 비교할 때 문구보다 다음을 확인합니다.

1. 정본과 writer가 하나씩 정해졌는가?
2. `Ready`를 판정하는 외부 evidence가 있는가?
3. service team과 platform team의 실패 책임이 분리됐는가?
4. 삭제·취소·예외 만료가 계약에 포함됐는가?
