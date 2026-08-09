# Capstone 사람 검토 루브릭

자동 validator 통과는 리뷰 시작 조건입니다. 리뷰어는 각 세부 질문을 `충족`, `보완 필요`, `범위 밖`으로 판정하고, 남은 조건에는 owner·due·verification·rollback을 기록합니다. `범위 밖`은 실행하지 않은 보장을 표시할 뿐 EXIT 자체를 면제하지 않습니다. 대체 evidence로 같은 상태·책임·실패·복구를 확인하지 못한 `범위 밖`은 EXIT 집계에서 `보완 필요`입니다.

## Product와 Golden Path

- 실제 사용자와 반복 마찰 evidence가 capability 선택에 연결됩니다.
- `svc-payments`의 생성·변경·migration·retirement가 하나의 지원 경로입니다.
- portal이 없어도 versioned API/status 계약은 동작합니다.
- escape hatch와 비범위가 숨은 수동 운영 경로가 되지 않습니다.

## Ownership과 상태

- spec·status·external resource·artifact·policy·data마다 single writer가 있습니다.
- application team, platform control plane, runtime operator, security owner와 provider의 실패 책임이 구분됩니다.
- `Accepted`, `Progressing`, `Ready`, `Blocked`, `Degraded`, `Retired`가 외부 evidence와 사용자 행동을 가집니다.
- partial effect와 cleanup owner가 operation status에서 사라지지 않습니다.

## IaC·Runtime·Delivery

- configuration, IaC state, provider resource와 observed runtime을 구분합니다.
- Kubernetes readiness, network, storage, scheduling과 disruption의 owner가 명시됩니다.
- 같은 artifact digest를 승격하며 build와 deploy identity가 분리됩니다.
- GitOps drift, break-glass 종료, data/config compatibility와 rollback/roll-forward 조건이 있습니다.

## Security·Catalog·Tenancy

- human·workload·automation identity와 credential TTL·audience·revocation이 구분됩니다.
- static fallback을 사용하지 않고 policy exception에는 approver·expiry·evidence가 있습니다.
- tenant quota가 capacity를 생성한다고 표현하지 않으며 queue fairness와 production reserve가 있습니다.
- catalog status와 developer error가 controller 내부 log가 아닌 실행 가능한 feedback입니다.

## SLO·Capacity·Migration·Retirement

- journey 시작·성공·실패 사건과 SLI 분모가 재현 가능합니다.
- queue, cluster, provider, policy와 telemetry capacity를 따로 측정합니다.
- migration wave의 entry·exit·abort와 이미 바뀐 상태의 복구가 있습니다.
- retirement가 traffic·data·credential·resource·catalog·cost inventory를 닫고 tombstone 보존 범위를 설명합니다.

## Evidence와 EXIT 판정

| EXIT | 사람 판정 | 최소 근거 |
|---|---|---|
| `EXIT-1` | `충족 / 보완 필요` | 같은 ID를 사용하는 product, API/status, 정상·중복·부분 실패·retirement 경로 |
| `EXIT-2` | `충족 / 보완 필요` | policy·artifact·GitOps·telemetry와 drift/break-glass runtime evidence |
| `EXIT-3` | `충족 / 보완 필요` | journey SLO·capacity/fairness·migration wave·abort·support/runbook evidence |

Model report의 hash와 `PE-001..010` 통과는 합성 공개 행동의 근거입니다. 실제 IAM, network, cluster, cloud, concurrency, crash recovery, 비용과 physical deletion은 별도 owner와 검증 조건 없이는 세부 질문에서 `범위 밖`이며, 미해결 상태라면 해당 EXIT는 `보완 필요`입니다. 질문별 기록과 집계는 [`reference/manual-review-guide.md`](../../reference/manual-review-guide.md)를 사용합니다.

## 최종 결정

허용 결정은 `APPROVE`, `APPROVE_WITH_CONDITIONS`, `DEFER`, `REJECT` 중 하나입니다. 모든 condition과 residual risk에는 다음을 남깁니다.

`APPROVE`와 `APPROVE_WITH_CONDITIONS`는 세 EXIT가 모두 `충족`일 때만 가능합니다. 필수 상태·책임·실패·복구 evidence가 빠진 condition, `보완 필요` EXIT 또는 미해결 `범위 밖`이 있으면 `DEFER` 또는 `REJECT`를 사용합니다. `APPROVE_WITH_CONDITIONS`는 종료 능력을 뒤집지 않는 잔여 개선에만 사용합니다.

| 필드 | 요구 사항 |
|---|---|
| owner | 상태·resource·정책을 바꿀 실제 책임자 |
| due | 날짜 또는 release/migration 전 trigger |
| verification | pass/fail을 나눌 test·metric·audit·inventory |
| rollback | 실패 때 traffic·artifact·policy·data commitment를 되돌리거나 안전하게 전진시키는 절차 |
