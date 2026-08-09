# Cloud-computing 사람 검토 가이드

자동 검사는 구조·필수 표식·공개 local model contract의 보조 근거만 제공합니다. 리뷰어는 Capstone의 실제 주장과 evidence를 읽고 각 종료 능력을 `충족`, `보완 필요`, `범위 밖` 중 하나로 판정합니다. 점수 합산으로 핵심 공백을 상쇄하지 않습니다.

## 판정 값

| 판정 | 의미 | release 처리 |
|---|---|---|
| `충족` | 해당 EXIT의 핵심 주장, 대표 실패, 관찰 근거와 한계가 연결됩니다. | 다른 EXIT 검토를 계속합니다. |
| `보완 필요` | 방향은 맞지만 owner 없는 실패, 빠진 Stage, 재현 불가 evidence처럼 완료를 막는 공백이 있습니다. | 공백마다 owner·due·verification·rollback을 적고 완료를 보류합니다. |
| `범위 밖` | 실제 provider·법률·인접 구현 브랜치처럼 이 Capstone이 자동 또는 로컬로 증명할 수 없는 항목입니다. | 숨기지 말고 handoff 대상, 필요한 외부 evidence와 release condition을 기록합니다. |

`범위 밖`은 면제가 아닙니다. Capstone 계약 안의 항목을 임의로 범위 밖으로 바꿀 수 없으며, 외부에서 닫아야 할 조건과 owner를 명확히 해야 합니다.

## 리뷰 입력

- [`contract-evidence-map.md`](contract-evidence-map.md)
- Capstone [`evidence-manifest.json`](../projects/multitenant-document-processing-saas/reference/evidence-manifest.json)
- 아홉 reference dossier와 학습자 workspace의 같은 파일
- [`local-model-report.json`](../projects/multitenant-document-processing-saas/reference/evidence/local-model-report.json) 또는 학습자 재실행 report
- Capstone [`rubric.md`](../projects/multitenant-document-processing-saas/rubric.md)
- 선택 provider를 사용했다면 experiment charter, before/after inventory, cost·destroy evidence

## EXIT-1 — 책임 경계로 service를 분류한다

필수 evidence:

- `01-responsibility-matrix.md`의 네 Stage에 task별 provider·consumer·customer owner가 있습니다.
- IaaS·managed platform·FaaS·SaaS를 하나의 마케팅 축으로 섞지 않습니다.
- managed/FaaS로 이동하지 않은 data·identity·limit·restore·exit 책임을 표시합니다.
- 각 책임 주장에 official contract, audit, test, restore 또는 `unknown` 확인 계획이 있습니다.

질문:

1. service 이름을 지워도 control과 evidence로 분류할 수 있는가?
2. 공동 책임에서 누락된 task 또는 owner 없는 상태가 없는가?
3. provider를 아직 선택하지 않은 주장을 측정 완료처럼 쓰지 않았는가?

provider별 최신 약관·SLA 확인은 `범위 밖`일 수 있지만, 확인 owner와 release condition이 없으면 `보완 필요`입니다.

## EXIT-2 — 같은 workload의 배치 trade-off를 설명한다

필수 evidence:

- 모든 Stage가 `2/s`, peak `50/s`, 평균 `8 MB`, 최대 `100 MB`, 평균 `4s`, p99 `40s`의 같은 workload를 사용합니다.
- 평균 concurrency `2 × 4 = 8`, 보수적 peak bound `50 × 40 = 2,000`, peak ingress `400 MB/s`와 max-object stress `5 GB/s`의 단위·가정을 공개합니다.
- invalid `1%`와 transient `2%`를 terminal/retryable failure로 분리합니다.
- zone loss, RPO `15분`, RTO `60분`, queue/DLQ, cost driver와 exit가 Stage마다 비교됩니다.
- provider price와 실제 capacity는 만들지 않고 `unmeasured/unknown`과 측정 계획으로 남깁니다.

질문:

1. 평균과 stress bound가 capacity promise로 오해되지 않는가?
2. 책임 감소와 새 quota·control-plane·observability failure를 함께 비교했는가?
3. release 결정이 failure·cost·exit evidence에서 논리적으로 이어지는가?

## EXIT-3 — SaaS tenant 계약과 구현 handoff를 정의한다

필수 evidence:

- tenant·membership·role·plan version·entitlement·quota reservation·usage·export·deletion 상태가 구분됩니다.
- tenant context가 request·DB·object·cache·queue·function·analytics·support·export·backup·deletion을 통과합니다.
- starter `100건/월`, pro `10,000건/월` commercial quota를 local model의 active capacity와 혼동하지 않습니다.
- 한 tenant가 workload `30%`를 만들 때 concurrency·quota·cost attribution이 다른 tenant를 보호합니다.
- export `24시간`, active deletion `7일`, backup retention 고지를 subsystem별 상태와 evidence로 추적합니다.
- `web-app`, `database-systems`, `distributed-services`, `cybersecurity`, `platform-engineering` handoff가 상세 소유권을 침범하지 않습니다.

질문:

1. body의 tenant ID가 아니라 인증된 membership에서 context를 만드는가?
2. duplicate event가 output과 usage를 한 번만 만드는가?
3. 삭제가 late event·DLQ·cache·export·support access까지 전파되는가?
4. 관계 schema·웹 authorization·일반 idempotency·보안 공격 검증을 올바른 owner에게 넘겼는가?

실제 구현 정확성은 인접 브랜치/프로젝트의 `범위 밖`입니다. 그러나 입력·출력·불변식·acceptance evidence가 없으면 handoff 자체가 `보완 필요`입니다.

## EXIT-4 — 격리된 cloud 실험을 재현한다

필수 evidence:

- `09-isolated-experiment.md`에 목적, 중단 조건, budget `0`, credential 없음, human/workload identity, exact command가 있습니다.
- before inventory와 after inventory가 모두 외부 resource `0`을 보이고 cleanup을 설명합니다.
- report의 implementation SHA-256과 contract SHA-256을 실제 파일과 대조합니다.
- `CM-001..CM-013` 결과, 관찰값과 evidence hash를 필요한 dossier 주장에 연결합니다.
- local model이 실제 IAM·network·queue·billing·physical deletion·분산 transaction·process crash·concurrent writer를 검증하지 않는다고 밝힙니다.
- 실제 provider profile은 명시적으로 선택 사항이며 local evidence를 대체하지 않습니다.

질문:

1. 다른 사람이 같은 command로 같은 contract 결과를 얻을 수 있는가?
2. report가 기존 evidence를 덮어쓰지 않은 새 파일인가?
3. cleanup 뒤 임시 report 외에 process·credential·resource가 남지 않는가?
4. provider 실험을 하지 않은 사실을 실패나 성공으로 위장하지 않았는가?

실제 provider IAM·network·billing·region failure는 `범위 밖`입니다. 로컬 명령·report·inventory·cleanup 중 하나가 없으면 `보완 필요`입니다.

## Release condition 검토

`APPROVE_WITH_CONDITIONS`, `DEFER` 또는 남은 위험이 있는 `APPROVE`에는 다음 네 필드가 모두 있어야 합니다.

| 필드 | 리뷰 질문 |
|---|---|
| owner | 상태와 자원을 실제로 바꿀 권한·책임이 있는가? |
| due | 날짜 또는 release 전 trigger가 검증 전에 도달 가능한가? |
| verification | pass/fail을 판단할 관찰값·test·inventory·restore가 있는가? |
| rollback | 조건 실패 때 traffic·trigger·data·commitment를 안전하게 되돌리는가? |

owner가 `team`, verification이 `확인한다`, rollback이 `복구한다`처럼 추상적이면 `보완 필요`입니다.

## Automation limitations

현재 자동화가 확인하는 것:

- 필수 파일, heading, phrase, JSON key와 미완성 token
- local model 공개 API의 private state, tenant access, quota 원자성, duplicate suppression, bounded retry/DLQ, cleanup과 deterministic evidence
- reference는 통과하고 template/starter는 실패한다는 최소 negative path

자동화가 확인하지 않는 것:

- 설명의 기술적 타당성이나 최신 provider 계약
- 실제 peak capacity, price, quota, SLA, RPO/RTO 또는 export/deletion 시간
- IAM·network·cache·analytics·support·backup의 실제 tenant isolation
- 법률·계약상 retention과 physical deletion
- 사람의 risk acceptance 또는 production readiness

자동 결과가 모두 통과해도 리뷰어는 네 EXIT를 별도로 판정해야 합니다.

## 리뷰 기록 양식

| EXIT | 판정 | 근거 file+heading/report | 공백 또는 범위 밖 | owner | due | verification | rollback |
|---|---|---|---|---|---|---|---|
| EXIT-1 | `충족/보완 필요/범위 밖` |  |  |  |  |  |  |
| EXIT-2 | `충족/보완 필요/범위 밖` |  |  |  |  |  |  |
| EXIT-3 | `충족/보완 필요/범위 밖` |  |  |  |  |  |  |
| EXIT-4 | `충족/보완 필요/범위 밖` |  |  |  |  |  |  |

최종 판정에는 reviewer, review date, `APPROVE | APPROVE_WITH_CONDITIONS | DEFER | REJECT`와 재검토 trigger를 남깁니다.
