# 용어

## Platform product

개발 팀을 사용자로 보고 반복되는 전달·운영 문제를 공통 capability로 해결하며, adoption·outcome·support·roadmap을 관리하는 내부 제품입니다.

## Internal Developer Platform

개발자가 서비스와 환경을 self-service로 생성·변경·관찰할 수 있도록 API, workflow, runtime, identity, policy와 운영 기능을 결합한 내부 플랫폼입니다.

## Platform API

사용자가 원하는 결과를 versioned input, status, error와 lifecycle로 제공하는 인터페이스입니다. Portal UI와 분리해서 자동화할 수 있어야 합니다.

## Control plane

Desired state를 저장하고 외부 system의 observed state를 읽어 reconciliation을 수행하는 구성요소와 상태의 집합입니다.

## Data plane

플랫폼이 관리하는 실제 workload와 traffic, storage 등 사용자 요청을 실행하는 경로입니다. 문맥에 따라 runtime plane이라고도 부릅니다.

## Desired state

사용자가 또는 정본 repository가 선언한 목표 상태입니다.

## Observed state

Controller가 외부 API와 runtime에서 확인한 현재 상태입니다.

## Reconciliation

Desired와 observed state의 차이를 반복적으로 줄여 수렴시키는 과정입니다.

## Condition

Resource의 현재 의미 상태를 stable type, status, reason, message와 observed generation으로 표현한 값입니다.

## Finalizer

외부 resource 정리와 보존 작업이 완료되기 전에 API object 삭제를 마치지 않도록 하는 lifecycle 장치입니다.

## Infrastructure as Code

Infrastructure의 desired configuration을 versioned code로 선언하고 plan/apply와 state를 통해 외부 resource를 관리하는 방식입니다.

## State

IaC configuration의 resource address와 외부 object identity, 일부 observed attribute를 연결하는 관리 상태입니다. Configuration이나 실제 resource와 동일하지 않습니다.

## Drift

Declared/recorded state와 실제 외부 resource 사이의 의미 있는 차이입니다. 수동 변경, 외부 controller, default와 stale input 등 여러 원인이 있습니다.

## Software catalog

Service·library·resource·owner·dependency·lifecycle metadata를 검색 가능한 관계로 제공하는 시스템입니다. Runtime state의 단일 정본과 동일하지 않습니다.

## Golden path

일반적인 workload가 적은 결정으로 조직의 build·보안·운영 기준을 만족하도록 제공되는 지원 경로입니다. 강제 template와 동일하지 않습니다.

## Platform profile

Runtime, build, identity, telemetry, policy와 support를 versioned 계약으로 묶은 지원 단위입니다.

## Escape hatch

표준 경로로 해결할 수 없는 요구를 제한된 scope, risk owner, support level과 expiry 아래 허용하는 공식 예외 경로입니다.

## Artifact promotion

같은 immutable artifact가 evidence와 environment gate를 통과해 다음 환경의 배포 대상으로 승인되는 과정입니다.

## GitOps

Versioned desired state를 controller가 자동으로 pull하고 지속적으로 reconciliation하는 운영 방식입니다.

## Break-glass

정상 권한·변경 경로가 실패하거나 긴급 영향이 있을 때 좁은 scope와 짧은 수명, 강화된 audit로 수행하는 비상 접근입니다.

## Tenant

플랫폼 자원, 권한, 비용과 blast radius를 구분하는 사용자 또는 workload 집합입니다. 팀, 고객, environment 또는 trust zone일 수 있습니다.

## Isolation profile

Tenant risk와 비용에 맞춰 account·cluster·namespace·node·network·storage 등 공유/격리 경계를 묶은 계약입니다.

## Platform journey

서비스 생성, 환경 provisioning, artifact promotion처럼 사용자가 플랫폼을 통해 얻으려는 종단 결과입니다.

## SLI/SLO

SLI는 journey 결과를 측정하는 지표이며 SLO는 일정 기간에 달성할 목표입니다.

## Error budget

SLO가 허용하는 실패 범위이며 변화와 reliability 작업의 우선순위를 조정하는 입력입니다.

## Supply-chain provenance

Artifact가 어떤 source·input·builder·build process에서 생성됐는지 연결하는 검증 가능한 statement입니다.

## Showback/Chargeback

Showback은 팀별 사용량과 비용을 보여 주는 방식이고, chargeback은 실제 비용을 해당 조직에 배분하는 방식입니다.
