# identity network and tenant boundaries

## Scope

tenant는 B2B customer organization이고 한 user가 여러 tenant에 속할 수 있다. 로그인 identity만으로 tenant를 결정하지 않고, 매 request에서 선택된 organization을 active membership과 대조해 `tenant_context`를 만든다. client body, URL, object name, queue message에 들어 있는 tenant ID는 단독 신뢰 source가 아니다.

cloud **control plane**은 resource·network·identity·deployment·backup 설정을 바꾸는 경로이고, application **data plane**은 upload·metadata·processing·result·usage·export·deletion을 수행하는 경로다. 두 plane의 identity, credential, approval과 audit을 분리한다.

| Identity class | 발급·scope | 허용 동작 | 금지 동작 | Credential·session | Audit evidence |
| --- | --- | --- | --- | --- | --- |
| customer member | application auth + 선택 tenant의 active membership | 자신의 role이 허용한 upload/read/download | 다른 tenant 선택, role·resource policy 변경 | 짧은 application session; tenant 전환 시 재검증 | actor, tenant, membership version, operation ID |
| customer admin | 위와 같고 tenant-admin role | 자기 tenant member 초대·role·export/deletion 요청 | cloud IAM, 다른 tenant, support 권한 부여 | 민감 변경 시 재인증 | before/after, approver, tenant audit |
| API workload | VM/managed runtime workload identity | object/queue/DB의 API용 최소 동작 | IAM 변경, backup restore, function deploy | 장기 static key 금지; 실제 TTL은 provider 선택 후 측정 | role revision과 service access log |
| processing function | function version에 결합된 workload identity | source read, deterministic result write, status·usage update | 임의 prefix list, tenant admin, trigger/concurrency 변경 | invocation-scoped credential; TTL unknown | function version, operation/tenant, resource action |
| deployment/migration automation | 승인 pipeline별 identity | version 배포, trigger·schema migration의 명시 작업 | document content read, customer role 변경 | short-lived, environment-scoped | approver, revision, diff, outcome |
| support operator | ticket와 tenant에 결합된 time-bound session | 승인된 진단 read 또는 명시 action | bulk export, 다른 tenant, 권한 지속 | 기본 0권한, 만료·즉시 revoke | ticket, customer approval, fields/actions, end time |

인증 프로토콜, 일반적인 credential 공격·incident response는 `cybersecurity`, tenant 관계 schema와 constraint는 `database-systems`가 소유한다. 이 문서는 그 결과를 cloud IAM/network와 모든 tenant data path에 적용한다. provider IAM·private network의 실제 동작과 가격은 `unmeasured/unknown`이다.

## Stage 1 — IaaS

public ingress는 `edge-lb`의 HTTPS listener 하나뿐이다. VM과 database는 private subnet에 있고, admin access는 일반 application port나 public SSH가 아니라 승인·감사되는 별도 control-plane 경로를 사용한다. object storage는 public listing/read를 거부하고 workload policy와 짧은 download authorization을 사용한다.

| Flow / boundary | Public surface·private hop | Identity / policy decision | Tenant context source·propagation | Representative deny test |
| --- | --- | --- | --- | --- |
| upload API | public LB → private API VM | member session + upload permission; VM workload role | route tenant를 active membership과 대조, operation·object key에 고정 | tenant A session + tenant B route/body, forged tenant body 모두 403/404이며 B 상태 불변 |
| metadata DB | private VM → private DB | application role은 prepared API operation만 | DB query parameter는 server-side context에서만 생성 | A document ID로 B row를 조회·갱신해도 결과/row change 0 |
| object put/get | private VM/worker → private object endpoint | source/result prefix action 분리; customer는 storage credential 없음 | `tenant_id/operation_id/version` deterministic key | guessed B key, encoded path, stale signed download 모두 deny |
| queue publish/consume | private workload → queue | API는 publish, worker는 consume/ack; admin과 분리 | message의 operation ID로 authoritative record를 다시 읽어 tenant 확인 | payload tenant만 B로 변조하면 terminal reject, B object/usage 변화 0 |
| admin/break-glass | public application path와 분리 | approval + MFA 정책 + time-bound admin role | tenant content access는 별도 support workflow 필요 | 일반 runtime credential로 VM/IAM/network 변경 deny |
| egress | private VM → allowlisted dependency | workload별 destination/action | tenant data export는 export workflow와 recipient identity 필요 | 임의 external host와 unapproved bulk transfer deny·alarm |

API process의 root 권한이나 VM network reachability가 tenant authorization을 대체하지 않는다. workload identity에는 storage·queue·DB에서 필요한 action만 주고, human admin identity와 key를 공유하지 않는다. 평균 2 uploads/s, peak 50/s와 8 MB/100 MB object는 ingress guard에도 적용하지만 실제 LB·network limit은 미측정이다.

## Stage 2 — Managed platform

managed service 사이에도 명시적 caller identity, resource policy/private attachment와 application tenant check가 모두 필요하다. 같은 account·project·VPC 또는 "managed"라는 label은 신뢰 증거가 아니다.

| Managed connection | Calling identity | Network/resource gate | Data-plane tenant check | Control-plane owner·evidence |
| --- | --- | --- | --- | --- |
| managed API → database | `api-role` | private attachment, DB auth, API subnet/service allow | membership-derived tenant를 모든 operation에 bind | data/runtime owner; connection/policy inventory와 cross-tenant query test |
| managed API → object | `api-role` | private endpoint, bucket/container policy | server-built tenant/operation key, download authorization 재검증 | security/data owner; policy simulation + object access log |
| managed API → queue | `api-role` publish only | queue policy와 encrypted transport | operation ID를 publish하고 tenant는 authoritative record와 일치 확인 | application owner; publish/consume audit |
| processor → DB/object | `processor-role` | source read/result write/status update action만 | operation record의 tenant와 deterministic key를 대조 | runtime/security owner; denied broad list/write test |
| migration → database | `migration-role` | maintenance window와 대상 DB 명시 | data migration은 tenant key preserve invariant 검사 | data owner; approved revision, row/count checksum |
| backup/restore | `restore-role` | isolated recovery environment에만 attach | restored tenant data는 production endpoint에서 접근 불가 | data/security owner; role activation과 restore inventory |

service credential rotation, private attachment, policy propagation과 admin/migration/backup identity는 application runtime과 분리한다. provider가 실제로 제공하는 private path, control-plane regionality, IAM propagation delay·policy size limit은 provider 선택 뒤 시험할 unknown이다.

## Stage 3 — FaaS

processing function의 trust root는 event payload가 아니라 immutable function version, trigger configuration, operation record와 scoped workload identity다. function은 source object read, deterministic result write, document status·usage update만 허용한다. trigger enable/disable, code deploy, concurrency 변경은 deployment identity만 수행한다.

| Event field / action | Trusted source와 재검증 | Function permission | 대표 실패·abuse | Guard와 evidence |
| --- | --- | --- | --- | --- |
| operation ID | API가 생성한 immutable ID; DB operation 존재·상태 확인 | 해당 operation read/update | guessed/replayed ID | unique operation trace, unknown ID terminal reject |
| tenant context | operation record의 tenant; payload 값과 일치 확인 | 해당 tenant key의 source/result만 | payload의 tenant를 B로 변조 | mismatch reject, B access log·state change 0 |
| source object | operation에 저장한 key+checksum | exact/prefix-scoped read | 임의 key나 traversal-like name | canonical key builder, checksum match |
| result object | tenant/operation/processor-version으로 결정 | deterministic key write | retry마다 다른 key·cross-tenant overwrite | conditional/idempotent publish, one final object |
| status·usage | same operation과 tenant에 결합 | scoped update API | result write 뒤 timeout·duplicate usage | operation ID unique accept와 reconciliation trace |
| DLQ replay | original envelope + reviewed replay identity | 원래 operation 범위만 | operator가 tenant/key를 바꾼 replay | immutable original, approver, before/after, outcome |

평균 concurrency는 8, peak/p99를 곱한 보수적 bound는 2,000이다. enterprise tenant 하나가 전체 workload의 30%를 만들 수 있으므로 initial fairness guard는 tenant별 active work를 global admitted concurrency의 30%로 제한하되, 실제 고객 SLA와 측정 뒤 versioning한다. 나머지 70%가 다른 tenant에 열려 있는지 tenant별 queued/running/throttled metric으로 확인한다. 이 30%는 provider 보장이 아니라 workload brief에서 도출한 소비자 정책이며 provider concurrency·cold start·timeout은 미측정이다.

## Stage 4 — SaaS

| Surface | Tenant context derivation | Isolation key / enforcement | Customer admin 범위 | SaaS provider 의무 | Representative deny evidence |
| --- | --- | --- | --- | --- | --- |
| API request | authenticated user + route tenant + active membership/version | authorization input; body tenant 무시 | 자기 tenant member·role·plan action | every request에서 재검증·audit | A token/B route·body deny, B state hash 불변 |
| database | server context | tenant-bound operation/query와 key/constraint defense | 직접 DB access 없음 | app·migration·support 모든 path에서 tenant predicate | A document ID로 B row read/update 0 |
| object/download | operation record의 tenant | tenant/operation/version key + short authorization | 자기 tenant export/download 요청 | public access 금지, recipient·expiry 검증 | guessed key, expired link, recipient mismatch deny |
| cache | request context | tenant가 첫 key component | 직접 access 없음 | eviction보다 isolation 우선 | 동일 document ID를 두 tenant에 두고 교차 hit 0 |
| queue/function | authoritative operation tenant | immutable operation ID + function 재검증 | 직접 publish/replay 없음 | poison·replay에도 tenant 보존 | forged payload가 other-tenant effect 0 |
| analytics/usage | accepted operation tenant | tenant-tagged append event와 scoped aggregate | 자기 tenant dashboard | raw shared export 접근 제한·reconciliation | A dashboard/query에 B event 0 |
| support | ticket + customer approval + selected tenant | time-bound field/action allowlist | 세션 승인·취소 | default no access, audit·notification | ticket 범위 밖 tenant/action deny |
| export/deletion | requester membership + step-up approval | workflow 전체에 immutable tenant ID | 자기 tenant 요청·수신자 확인 | export ≤24시간, active deletion ≤7일, backup notice | 다른 tenant request/recipient, deleted tenant access deny |

starter 100건/월·pro 10,000건/월 quota는 authorization과 별개의 commercial boundary이며 atomic reservation에서 같은 tenant context를 쓴다. 고객 admin은 자기 tenant의 member·sharing을 관리하지만 SaaS provider는 request, DB, object, cache, queue, function, analytics, support, export와 deletion 전체의 isolation을 위임할 수 없다.

## Evidence와 한계

| Claim | Test / observation | Expected result | 보존 evidence | 한계 |
| --- | --- | --- | --- | --- |
| cross-tenant API/DB 접근 차단 | A identity로 B route/body/document ID read·update | deny 또는 존재 비공개 응답, B row/count/hash 불변 | actor·tenant·membership version과 before/after query | test case 밖 application path는 사람 review 필요 |
| object/cache key 격리 | guessed/encoded B object, 동일 local document ID cache collision | object deny, A/B cache response 정확 | object access log, cache tenant-key trace | provider 내부 cache/storage isolation은 contract 의존 |
| event tenant 보존 | queue payload tenant 변조, duplicate·DLQ replay | authoritative mismatch terminal, B output·usage 0 | original/replay envelope, operation trace | local queue는 provider delivery 보장 재현 안 함 |
| 최소 권한 | runtime/function 역할로 IAM/network/admin action 시도 | 명시 허용 외 모두 deny | policy revision, simulation과 실제 sandbox deny | simulation은 runtime tenant bug를 증명 안 함 |
| support 제한 | 만료·다른 tenant·허용 밖 field 접근 | 모두 deny, 세션 종료 뒤 credential 무효 | ticket, approval, accessed fields/actions, revoke | insider/process risk 전체를 자동 증명 못 함 |
| public surface 최소화 | endpoint/route/resource policy inventory scan | 승인한 HTTPS ingress만 public | scan result와 desired inventory diff 0 | provider 선택 전 실제 network는 unknown |

local negative test는 application contract를, policy simulation은 policy 문법을, provider sandbox deny는 실제 IAM/network 적용을 각각 다른 범위에서 증명한다. 어느 하나도 전체 isolation이나 architecture의 교육적 완성을 자동 승인하지 않는다.

## Open risks와 owner

| Risk / unknown | Owner | 닫는 trigger | Verification | Containment / handoff |
| --- | --- | --- | --- | --- |
| provider identity·private network 동작 | runtime/security owner | provider 선택 전 | sandbox에서 actual allow/deny, propagation, endpoint scan | public data path 금지; 미확인 release 조건 |
| metadata credential·SSRF 경계 | security owner | runtime profile 확정 전 | threat model과 egress/metadata deny test | `cybersecurity`에 공격·incident 상세 handoff |
| support impersonation / break-glass | security/support owner | support 기능 출시 전 | two-person approval, expiry/revoke, audit exercise | default disabled |
| analytics/export tenant leakage | data/security owner | analytics/export 연결 전 | representative cross-tenant negative set과 recipient test | bulk integration 보류 |
| 30% enterprise tenant fairness | runtime/product owner | capacity test·SLA 승인 전 | tenant별 queued/running/throttled와 latency report | admission cap 조정; 실제 limit unknown |
