# 사람 검토 가이드

자동 검증을 통과한 Capstone을 `EXIT-1..3` 기준으로 검토하는 기록 양식입니다. [정본 계약 evidence map](contract-evidence-map.md)과 [Capstone rubric](../projects/internal-developer-platform/rubric.md)을 함께 사용합니다.

## 판정 언어

각 질문에는 다음 중 하나만 기록합니다.

| 판정 | 의미 | 후속 조치 |
|---|---|---|
| `충족` | 주장, 실행/trace 근거와 한계가 서로 일치합니다. | 근거 경로와 관찰값을 기록합니다. |
| `보완 필요` | 핵심 연결이나 실패·복구 증거가 부족합니다. | owner, 기한과 다시 확인할 evidence를 기록합니다. |
| `범위 밖` | 조직·실습 profile에서 의도적으로 실행하지 않았습니다. | 대체 evidence와 검증하지 못한 보장을 기록합니다. |

`범위 밖`은 `EXIT-1..3` 자체를 면제하지 않습니다. 실제 cluster나 cloud가 없으면 결정적 모델과 tabletop evidence로 판단 범위를 좁힐 수 있지만, 핵심 능력에 필요한 상태·책임·실패·복구 설명이 없으면 `보완 필요`입니다.

### 질문별 판정과 EXIT 집계

- 아래 표의 질문 여섯 개를 각각 판정합니다. 질문 묶음 전체에 판정 하나만 적지 않습니다.
- EXIT 최종 판정은 `충족` 또는 `보완 필요`만 사용합니다. 등재된 종료 능력 자체를 `범위 밖`으로 면제할 수 없습니다.
- 여섯 질문이 모두 `충족`일 때만 EXIT를 `충족`으로 집계합니다. 하나라도 `보완 필요`이거나 해결되지 않은 `범위 밖`이면 EXIT 최종 판정은 `보완 필요`입니다.
- 실제 도구를 실행하지 않은 질문은 우선 `범위 밖`으로 기록합니다. 같은 상태·책임·실패·복구를 결정적 모델, tabletop 또는 독립 관찰 evidence가 충분히 대체하면 그 근거를 명시하고 질문을 `충족`으로 바꿀 수 있습니다.
- 자동 검사 `PASS`는 질문의 입력 근거일 뿐 사람 판정을 대신하지 않습니다. 반대로 선택 profile의 `SKIP`을 `PASS`나 `충족`으로 올리지 않습니다.

## 검토 전 입력

- 검토 대상 commit 또는 archive hash:
- 실행한 `prepare.sh`, `verify.sh`, 분야별 검사와 결과:
- 선택 profile과 `PASS`/`SKIP`/`FAIL`:
- 실제로 만들거나 변경한 외부 자원: 없음 / 목록과 cleanup evidence
- 검토자, 날짜, 환경:
- 자동 검사가 밝힌 한계:

식별자는 product 문서부터 trace까지 같아야 합니다. 최소한 `service_id`, `resource_id`, `operation_id`, `tenant_id`, immutable `artifact_id`, versioned `profile_id`를 샘플 하나에서 끝까지 추적합니다.

## EXIT-1 — Self-service 서비스 경로

정본 능력: **self-service 서비스 경로를 설계한다.**

필수 evidence:

- 사용자 문제의 관찰 근거와 golden path의 지원·비지원 범위
- versioned request/resource/operation identity와 idempotency 결과
- desired/observed state, generation, condition과 외부 `Ready` evidence
- IaC state writer, runtime profile, tenant boundary와 service retirement cleanup
- `FS-01`, `FS-02`, `FS-03`, `FS-07`, `FS-08`의 주입·관찰·복구 기록

| # | 검토 질문 | 판정 | 근거·관찰 | 보완 owner·기한 |
|---|---|---|---|---|
| 1 | Portal이 없어도 API/CLI를 통해 같은 결과와 상태를 얻을 수 있습니까? |  |  |  |
| 2 | 요청 수락, controller 진행, 외부 사용자 성공을 서로 다른 상태로 표현합니까? |  |  |  |
| 3 | 같은 idempotency key의 retry는 중복 effect를 만들지 않고, 다른 payload는 원자적으로 충돌합니까? |  |  |  |
| 4 | 일부 외부 자원만 만들어진 실패에서 resource ID, 비용·credential owner와 cleanup 결정이 보입니까? |  |  |  |
| 5 | 한 tenant의 quota 초과가 다른 tenant의 queue와 production reserve를 막지 않습니까? |  |  |  |
| 6 | Create만큼 migration과 retirement의 consumer·data·credential·orphan 처리가 구체적입니까? |  |  |  |

EXIT-1 집계: `충족` / `보완 필요`

## EXIT-2 — 정책·배포·관측 자동화

정본 능력: **정책·배포·관측을 플랫폼 계약으로 자동화한다.**

필수 evidence:

- source revision→build identity→immutable artifact→environment promotion 연결
- desired artifact와 live state drift의 before/after trace
- workload identity, secret reference·rotation, policy allow/deny와 bounded exception
- user journey correlation ID, 상태·metric·audit와 actionable feedback
- `FS-02`, `FS-04`, `FS-05`, `FS-07`의 주입·관찰·복구 기록

| # | 검토 질문 | 판정 | 근거·관찰 | 보완 owner·기한 |
|---|---|---|---|---|
| 1 | 환경별 재빌드 없이 같은 digest를 승격하고 provenance·policy 결과를 release에 고정합니까? |  |  |  |
| 2 | Git과 controller가 소유하는 field, prune guardrail과 emergency writer가 명확합니까? |  |  |  |
| 3 | Break-glass는 승인자·사유·만료·evidence가 있고 종료 뒤 desired state로 수렴합니까? |  |  |  |
| 4 | 장기 static credential을 fallback으로 사용하지 않으며 발급 실패가 원인 계층과 사용자 행동으로 드러납니까? |  |  |  |
| 5 | 정책 deny가 단순 실패가 아니라 rule version, owner, remediation과 함께 전달됩니까? |  |  |  |
| 6 | 자동화의 성공 주장이 external smoke나 사용자 journey evidence까지 이어집니까? |  |  |  |

EXIT-2 집계: `충족` / `보완 필요`

## EXIT-3 — SLO·용량·업그레이드 운영

정본 능력: **플랫폼 SLO·용량·업그레이드를 운영한다.**

필수 evidence:

- platform journey별 SLI 분자·분모, SLO window, exclusion과 error budget 행동
- tenant fairness, queue saturation, headroom, admission과 capacity owner
- profile·API·cluster inventory, compatibility, preflight, canary/wave와 abort
- alert→runbook→완화→복구 판정과 support escalation
- `FS-03`, `FS-06`, `FS-08`의 주입·관찰·복구 기록

| # | 검토 질문 | 판정 | 근거·관찰 | 보완 owner·기한 |
|---|---|---|---|---|
| 1 | SLO가 component uptime이 아니라 create·deploy·recover 같은 사용자 journey 결과를 측정합니까? |  |  |  |
| 2 | 수요, quota와 실제 공급 capacity를 구분하고 overload 때 어떤 요청을 거부할지 정했습니까? |  |  |  |
| 3 | Retry storm, noisy tenant와 stuck queue를 구분하는 signal과 bounded mitigation이 있습니까? |  |  |  |
| 4 | Migration wave 실패가 이후 wave를 멈추며 이미 변경된 state의 rollback/roll-forward 경계를 설명합니까? |  |  |  |
| 5 | Version skew, deprecated API, policy·template·controller 호환성과 이전 version 종료 조건이 있습니까? |  |  |  |
| 6 | Retirement 뒤 active resource·credential·exception은 없어지고 필요한 audit·data retention만 남습니까? |  |  |  |

EXIT-3 집계: `충족` / `보완 필요`

## 자동 evidence와 사람 확인의 경계

결정적 `PE-*` 검사는 작은 in-memory 상태에서 공개 불변식을 확인합니다. 다음 실패 시나리오는 dossier 설명과 자동 pointer가 모두 있어도, 표의 조직·도구 행동은 사람 evidence 없이는 증명되지 않습니다.

| 시나리오 | 자동으로 확인하는 부분 | 사람 또는 선택 profile이 확인할 부분 |
|---|---|---|
| `FS-04` live drift·break-glass | `PE-005`의 desired 수렴, `PE-006`의 승인자·사유·만료가 있는 bounded exception | 만료 시 emergency writer를 실제로 닫고 prune guardrail을 지키며 desired state로 수렴하는지 |
| `FS-05` identity issuer 장애 | `PE-007`의 장기 static credential fallback 거부 | issuer 장애가 `Blocked` condition, 원인 계층, 사용자 행동으로 드러나고 rotation·revocation이 실제로 작동하는지 |
| `FS-06` migration wave 실패 | `PE-008`의 이후 wave 중단과 abort evidence | 이미 바뀐 workload·data·policy·artifact의 rollback 또는 roll-forward와 호환성 판단 |
| `FS-07` IaC partial apply | `PE-003`의 partial effect ID·cleanup 필요 상태 공개 | 실제 backend state serial·lock, 비용·credential owner, import/repair/destroy와 재개 승인 |
| `FS-08` retirement | `PE-009`의 합성 resource·operation·credential·exception cleanup과 tombstone | 실제 traffic 차단, data retention·삭제, catalog·DNS·비용 종료와 orphan 탐색 |

## 교차 검토

- `owns`마다 single writer, failure owner, escalation과 cleanup owner가 있습니까?
- `excludes`에 속하는 단일 서비스 운영, 애플리케이션 업무 로직, 문화 일반론, cloud 자격증 내용을 완료 근거로 대신하지 않았습니까?
- 정상·경계·대표 실패가 같은 ID와 상태 vocabulary를 사용합니까?
- 실행하지 않은 도구와 외부 보장을 `PASS`로 표시하지 않았습니까?
- secret, personal data, 실제 credential과 비용 있는 자원을 evidence에 포함하지 않았습니까?
- 알려진 한계가 결론을 뒤집을 정도라면 `보완 필요`로 남겼습니까?

## 최종 기록

| 종료 능력 | 판정 (`충족`/`보완 필요`) | 핵심 evidence | 보완 owner·기한 |
|---|---|---|---|
| `EXIT-1` |  |  |  |
| `EXIT-2` |  |  |  |
| `EXIT-3` |  |  |  |

최종 결론에는 자동 검사 결과와 사람 판단을 분리합니다. 예: “결정적 공개 계약과 evidence 연결 검사는 통과했다. 실제 조직 적합성·IAM·Kubernetes enforcement·동시성·비용·물리 삭제는 사람 검토 또는 선택 profile evidence가 필요하다.”
