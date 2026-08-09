# 플랫폼을 제품으로 정의하기

## 1. 도구를 먼저 고르면 플랫폼이 되지 않습니다

조직에서 반복되는 요청을 자동화하려고 할 때 흔히 다음 순서로 시작합니다.

```text
Kubernetes를 도입합니다.
→ portal을 설치합니다.
→ template를 만듭니다.
→ 모든 팀에 사용하라고 알립니다.
```

이 순서는 사용자가 어떤 문제를 겪는지 확인하지 않습니다. 결과적으로 기존 ticket 절차가 새로운 UI로 옮겨지거나, platform team이 자동화와 예외 처리를 동시에 떠안게 됩니다.

플랫폼을 제품으로 본다는 말은 다음 질문에서 시작한다는 뜻입니다.

- 사용자는 누구입니까?
- 사용자가 완료하려는 작업은 무엇입니까?
- 현재 작업에서 시간이 오래 걸리거나 실패하는 지점은 어디입니까?
- 플랫폼이 제공하면 안 되는 책임은 무엇입니까?
- 사용자가 얻은 결과를 어떤 근거로 측정합니까?

플랫폼은 내부 사용자에게 제공되지만, 사용자 조사·우선순위·호환성·지원·폐기 책임이 있는 제품입니다. 공식 자료의 연결은 [source index의 platform product](../reference/source-index.md#platform-product)를 확인하세요.

## 2. 플랫폼 사용자를 구분합니다

“개발자”를 하나의 사용자로 묶으면 요구가 충돌합니다.

### Application developer

원하는 결과:

- 새 서비스를 빠르게 시작합니다.
- 변경을 배포하고 상태를 확인합니다.
- secret, database, queue 같은 capability를 안전하게 요청합니다.
- 실패 원인과 다음 행동을 이해합니다.

### Service owner

원하는 결과:

- 소유자, SLO, on-call, 비용과 위험을 한 곳에서 확인합니다.
- environment와 release의 현재 상태를 추적합니다.
- migration과 deprecation 일정을 관리합니다.

### Platform operator

원하는 결과:

- tenant별 사용량과 blast radius를 제한합니다.
- controller와 dependency 실패를 조기에 발견합니다.
- upgrade와 정책 변경을 wave로 전달합니다.
- 반복 ticket보다 platform contract를 개선합니다.

### Security·compliance owner

원하는 결과:

- source, artifact, identity와 정책 증거를 추적합니다.
- 예외가 영구 권한으로 남지 않게 합니다.
- 위험한 경로를 배포 전에 차단합니다.

사용자마다 같은 UI가 필요하지 않습니다. 안정적인 API와 상태 모델이 먼저 있고, CLI·portal·Git integration은 그 위의 client가 되어야 합니다.

## 3. 사용자 여정을 상태 전이로 기록합니다

“배포가 어렵다”는 표현만으로는 설계할 수 없습니다. 작업을 시작 사건과 완료 증거가 있는 여정으로 나눕니다.

예: 새 서비스의 첫 production 배포

```text
저장소 생성 요청
→ 소유자와 서비스 metadata 등록
→ build pipeline 생성
→ artifact 생성·검증
→ staging environment 생성
→ staging 배포·smoke
→ production 승인
→ 같은 artifact 승격
→ production readiness·external smoke
→ catalog에 release·runbook·dashboard 연결
```

각 단계에 다음을 기록합니다.

| 항목 | 질문 |
|---|---|
| 입력 | 누가 무엇을 선언합니까? |
| 정본 | 현재 desired state는 어디에 저장됩니까? |
| 담당 | platform과 service team 중 누가 변경합니까? |
| 대기 | 어떤 외부 dependency를 기다립니까? |
| 실패 | 재시도 가능, 사용자 수정 필요, 운영자 개입 중 무엇입니까? |
| 완료 | 어떤 독립된 evidence가 성공을 판정합니까? |
| 취소 | 중간 상태를 어떻게 정리합니까? |

이 표를 작성하면 portal 화면보다 먼저 platform API와 controller가 필요한 이유가 드러납니다.

## 4. 마찰은 의견이 아니라 근거로 수집합니다

가능한 근거:

- 첫 배포까지 걸린 시간의 분포
- provisioning 요청의 queue time과 실제 작업 시간
- 실패한 deployment에서 원인을 찾기까지 걸린 시간
- platform team이 반복 처리한 ticket 유형
- 정책 위반이 발견된 단계
- template에서 벗어난 서비스 수와 이유
- deprecated 경로를 계속 사용하는 workload 수
- 동일 문제에 대한 문서 검색과 문의 반복

한두 명의 불만을 전체 조직 요구로 일반화하지 않습니다. 반대로 ticket 수가 적다는 이유로 문제가 없다고 보지도 않습니다. 사용자가 비공식 우회 경로를 사용하면 platform team에 ticket이 남지 않을 수 있습니다.

## 5. Outcome과 output을 구분합니다

Output 예:

- portal을 배포했습니다.
- template 20개를 만들었습니다.
- cluster를 세 개 추가했습니다.

Outcome 예:

- 첫 production 배포의 중간값과 상위 지연 구간이 줄었습니다.
- 배포 실패가 더 이른 단계에서 발견됩니다.
- service owner와 on-call 정보가 최신 상태로 유지됩니다.
- 정책 예외의 수명과 소유자가 추적됩니다.
- 반복 ticket이 self-service 성공으로 전환됩니다.

Output은 platform team이 무엇을 만들었는지 보여 줍니다. Outcome은 사용자가 어떤 결과를 더 안정적으로 얻었는지 보여 줍니다.

## 6. North star와 guardrail을 함께 둡니다

North star 하나만 최적화하면 다른 위험이 커질 수 있습니다.

예:

```text
North star
- production 첫 배포까지의 성공 시간

Guardrail
- rollback 가능한 release 비율
- 정책 예외 없이 완료된 요청 비율
- platform-induced incident 수
- 비용 budget을 넘은 environment 비율
- 사용자가 platform team 개입 없이 복구한 비율
```

속도를 올리면서 실패와 비용을 숨기지 않습니다.

## 7. 지원 범위와 non-goal을 선언합니다

좋은 platform product brief에는 하지 않을 일이 포함됩니다.

예:

- 지원 언어를 제한하지 않지만 표준 health·telemetry contract는 요구합니다.
- database schema와 application transaction은 service team이 소유합니다.
- production data restore는 `web-infra`와 data owner의 절차를 따릅니다.
- custom kernel module이나 privileged workload는 기본 golden path에서 제외합니다.
- 규제상 dedicated account 또는 cluster가 필요한 workload는 별도 profile로 분기합니다.

non-goal이 없으면 platform team이 모든 장애의 최종 담당자가 됩니다.

## 8. 작은 capability부터 검증합니다

처음부터 완전한 developer portal을 만들지 않습니다. 사용자 여정 한 개를 선택합니다.

예:

```text
목표
staging environment 생성

입력
service ID, owner, region profile, resource tier

출력
namespace, workload identity, DNS name, deployment target, dashboard link

완료 evidence
API condition Ready=True
+ GitOps revision applied
+ external smoke success

지원하지 않음
production approval, database provisioning, customer DNS
```

이 경로가 실제 사용자에게 반복 사용된 뒤 다음 capability를 추가합니다.

## 9. 흔한 실패

### Platform team의 취향을 사용자 문제로 포장합니다

특정 tool과 구조를 표준화하고 싶은 이유를 productivity로 단정합니다. 실제 여정과 측정 근거를 먼저 남깁니다.

### 모든 팀을 한 번에 migration합니다

사용자 유형과 위험이 다른데 한 번에 강제하면 exception과 긴급 수정이 폭증합니다. pilot, early adopter와 wave를 분리합니다.

### Adoption을 사용 계정 수로만 봅니다

강제 사용은 adoption처럼 보일 수 있습니다. self-service 성공, 우회 경로, 지원 ticket과 실제 여정 시간을 함께 봅니다.

### Portal을 platform으로 봅니다

portal이 중단돼도 API와 reconciliation은 계속 작동해야 합니다. UI는 client이지 정본이나 control plane이 아닙니다.

## 10. 실습

[`01-platform-product`](../exercises/01-platform-product/)에서 사용자·여정·non-goal·outcome metric과 지원 경계를 작성합니다.

완료 뒤 다음 질문에 답합니다.

- 가장 먼저 자동화할 여정은 무엇이며 왜 지금입니까?
- platform team의 output이 아니라 사용자의 outcome은 무엇입니까?
- 어떤 서비스는 이 경로를 사용하면 안 됩니까?
- 성공을 확인하기 위해 현재 수집되지 않는 evidence는 무엇입니까?
