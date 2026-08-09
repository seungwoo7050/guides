# Capstone 리뷰 루브릭

이 루브릭은 자동 점수표가 아닙니다. 학습자 외의 리뷰어가 dossier, evidence manifest와 local report를 읽고 각 항목을 `충분`, `조건부`, `부족`으로 판단합니다. 자동 contract 통과만으로 `충분`을 부여하지 않습니다.

## 사용 방법

1. [`inputs/system-brief.md`](inputs/system-brief.md)의 값이 아홉 dossier 전체에서 같은지 확인합니다.
2. [`evidence-manifest.json`](reference/evidence-manifest.json)과 학습자 manifest의 `OWN-1..6 → EXIT-1..4 → file+heading` 연결을 비교합니다.
3. [`evidence/local-model-report.json`](reference/evidence/local-model-report.json) 또는 학습자 report의 hash·check·한계를 실제 파일과 대조합니다.
4. 각 EXIT를 [사람 검토 가이드](../../reference/manual-review-guide.md)에 따라 `충족`, `보완 필요`, `범위 밖`으로 별도 판정합니다.
5. 조건과 공백마다 owner·due·verification·rollback을 기록한 뒤 최종 release 결정을 내립니다.

## 책임과 서비스 모델

- 네 Stage에서 provider·consumer·customer admin task가 실제로 달라집니다.
- business·runtime·data·security·cost owner가 상태와 증거에 연결됩니다.
- IaaS·PaaS/SaaS 서비스 모델과 VM·container·FaaS 실행 모델을 같은 축으로 섞지 않습니다.
- managed service가 이동시킨 task뿐 아니라 남은 identity·data·limit·restore·exit 책임을 기록합니다.

`조건부`: provider가 미선택이라 실제 SLA·quota는 unknown이지만 확인 owner와 release condition이 있습니다.

`부족`: `managed라서 공급자가 운영한다`처럼 task·control·evidence가 없습니다.

## 상태와 resource lifecycle

- durable authoritative, derived, ephemeral, evidence, commercial state를 구분합니다.
- resource ID·owner·region/zone·dependency·backup·cost center·expiry가 있습니다.
- create·update·delete의 중간 상태, retry와 reconciliation을 표시합니다.
- tenant 삭제 후 보존할 tombstone·aggregate usage와 제거할 active state를 구분합니다.

## Workload와 계산

- 정상 `2/s`, peak `50/s`, 평균 `8 MB`, 최대 `100 MB`, 평균 `4s`, p99 `40s`를 사용합니다.
- 평균 in-flight `8`, 보수적 peak bound `2,000`, peak ingress `400 MB/s`, max-object stress `5 GB/s`의 식·단위를 공개합니다.
- bound를 guaranteed capacity로 표현하지 않습니다.
- invalid `1%`, transient `2%`, 단일 tenant `30%`를 failure·fairness·비용 근거에 반영합니다.
- provider price, 실제 compression·capacity·quota는 만들어내지 않고 `unmeasured/unknown`으로 표시합니다.

## 실패와 recovery

- instance·zone·managed control plane·dependency·event·quota·tenant·cost failure를 구분합니다.
- duplicate, timeout 뒤 partial success, poison input, DLQ replay와 deletion 중 late event를 다룹니다.
- RPO `15분`, RTO `60분`은 backup 존재가 아니라 restore/rebuild 측정과 연결됩니다.
- alarm time, operation/event ID, checksum, final inventory와 reconciliation 결과가 있습니다.

## Identity와 tenant isolation

- human·workload·automation·support identity가 분리됩니다.
- control plane과 application data plane permission을 구분합니다.
- tenant context가 request·DB·object·cache·queue·function·analytics·support·export·backup·deletion을 통과합니다.
- cross-tenant·missing context·deleted tenant·support access의 negative evidence가 있습니다.

## Event, quota와 metering

- `(tenant_id, event_id)` 또는 동등하게 명시된 operation identity가 있습니다.
- duplicate가 output과 usage를 한 번만 만들며 payload conflict를 구분합니다.
- starter `100건/월`, pro `10,000건/월` commercial quota를 active document capacity와 분리합니다.
- quota reservation과 usage event가 원자적·멱등이며 late/replayed event policy가 있습니다.

## 비용과 exit

- request·duration·storage·I/O·egress·retry·DLQ·log·provisioned capacity의 단위가 있습니다.
- 가격 숫자가 없다면 provider 미선택과 측정 계획을 명시합니다.
- owner·tag·expiry, orphan cleanup, budget alert와 hard guard가 있습니다.
- export `24시간`, active deletion `7일`, backup retention 고지와 final inventory를 분리합니다.
- migration throughput·checksum·duration·egress와 rollback trigger가 rehearsal 가능한 절차입니다.

## 격리 실험과 evidence

- 필수 local experiment는 budget `0`, credential 없음, network 없음, 외부 resource 없음입니다.
- human identity는 명령을 시작하고 workload identity는 model contract가 제한한 행위만 수행한다고 구분합니다.
- exact command, before inventory, after inventory, observations, cleanup과 limitations가 있습니다.
- report에 implementation/contract SHA-256과 `CM-001..CM-013` 결과가 있습니다.
- 실제 provider 실험은 선택 사항이며 local report를 대체하지 않습니다.

## 구현 owner handoff

- `web-app`: authentication·membership·API authorization과 tenant context
- `database-systems`: 관계 schema·constraint·transaction·query isolation
- `distributed-services`: 일반 retry·idempotency·Outbox·Saga·DLQ
- `cybersecurity`: credential threat·공격 검증·탐지·incident recovery
- `platform-engineering`: 여러 팀의 Kubernetes·IaC module·golden path·self-service tenancy

Cloud Capstone은 각 handoff의 입력·불변식·acceptance evidence를 제공하되 인접 브랜치의 상세 구현을 다시 가르치지 않습니다.

## EXIT 판정 기록

| EXIT | 사람 판정 | 필요한 최소 evidence |
|---|---|---|
| `EXIT-1` | `충족 / 보완 필요 / 범위 밖` | responsibility matrix의 네 Stage와 task별 control/evidence |
| `EXIT-2` | `충족 / 보완 필요 / 범위 밖` | 동일 workload의 failure·cost·운영 책임 비교와 release review |
| `EXIT-3` | `충족 / 보완 필요 / 범위 밖` | tenant isolation·quota·metering·export·deletion과 구현 handoff |
| `EXIT-4` | `충족 / 보완 필요 / 범위 밖` | isolated experiment, exact report hash, before/after inventory, cleanup·한계 |

핵심 EXIT 하나라도 `보완 필요`이면 Capstone 완료로 승인하지 않습니다. 실제 provider에서만 확인 가능한 내용은 `범위 밖`으로 기록할 수 있지만 owner와 verification condition이 필요합니다.

## 결정

허용 결정은 다음 네 가지입니다.

```text
APPROVE
APPROVE_WITH_CONDITIONS
DEFER
REJECT
```

모든 condition과 residual risk에는 다음이 필요합니다.

| 필드 | 완료 기준 |
|---|---|
| owner | 상태·resource·정책을 바꿀 실제 책임자 |
| due | 검증 가능한 날짜 또는 release 전 trigger |
| verification | pass/fail을 구분할 test·metric·audit·restore·inventory |
| rollback | 실패 때 traffic·trigger·data·commitment를 되돌리는 절차 |

리뷰 기록에는 reviewer, review date, evidence 한계와 재검토 trigger도 포함합니다.

## Automation limitations

현재 checker는 파일·heading·phrase·JSON key와 미완성 token을 검사합니다. local model validator는 합성 in-process 공개 행동을 검사합니다. 어느 쪽도 실제 provider IAM·network·queue·billing·physical deletion, 가격·SLA·capacity, 법적 retention, 분산 transaction, process crash, concurrent writer 또는 production readiness를 증명하지 않습니다.
