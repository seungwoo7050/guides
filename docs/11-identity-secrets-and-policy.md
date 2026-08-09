# Identity·secret·policy

공유 플랫폼은 많은 팀의 배포와 운영 권한을 한곳에 연결합니다. 편리한 공통 경로가 과도한 공통 권한이 되면 하나의 credential 또는 controller 결함이 조직 전체의 blast radius가 됩니다.

이 장은 사람, workload와 automation의 identity를 분리하고, secret 전달과 policy enforcement를 수명·증거·예외 계약으로 설계합니다. 일반적인 위협 모델과 공격·방어 과정 전체는 `cybersecurity`가 소유하며, 여기서는 플랫폼이 제공해야 하는 guardrail에 집중합니다.

SPIFFE, Kubernetes ServiceAccount·Secret와 admission policy의 현재 공식 경계는 [source index의 workload identity](../reference/source-index.md#identity)를 확인합니다. 제품 선택과 무관하게 audience·TTL·rotation·revocation과 exception expiry를 검토합니다.

## 1. Identity를 주체별로 분리합니다

### 사람 identity

개발자, reviewer, operator와 emergency responder가 사용합니다.

필요한 속성:

- 조직 directory와 연결된 안정적인 사람 identity
- MFA와 session 수명
- team·role·environment에 따른 권한
- elevation과 approval
- 탈퇴·이동 시 즉시 반영되는 lifecycle
- 사람이 수행한 행동의 audit

### Workload identity

서비스 process, job와 controller가 다른 system에 접근할 때 사용합니다.

필요한 속성:

- workload를 식별하는 attested identity
- namespace·service account·deployment 같은 실행 context
- 짧은 수명의 credential
- 목적과 대상에 제한된 scope
- 자동 rotation
- workload 종료와 함께 폐기되는 수명

### Automation identity

CI runner, promotion bot, IaC controller와 GitOps controller가 사용합니다.

사람 개인 token을 공유하지 않습니다. Automation마다 다음을 분리합니다.

- build
- artifact publish
- environment promotion
- infrastructure apply
- cluster reconciliation
- secret broker access
- audit export

하나의 pipeline credential이 source write, registry push와 production admin을 모두 갖지 않게 합니다.

## 2. Authentication과 authorization

Identity를 확인했다고 모든 작업을 허용하지 않습니다.

```text
Authentication
누가 또는 무엇이 요청했는가?

Authorization
이 identity가 이 resource에 이 action을 이 context에서 수행해도 되는가?
```

Authorization 입력 예:

- subject identity
- team과 workload owner
- action과 resource
- environment
- data classification
- request source
- approval 또는 ticket
- 시간과 session risk
- policy version

결정은 단순 role뿐 아니라 resource ownership과 environment risk를 포함할 수 있습니다.

예:

```text
team-checkout developer
- staging deployment 요청 허용
- production promotion은 verified artifact와 reviewer 필요
- platform policy 수정 금지
- 다른 tenant secret 접근 금지
```

## 3. Ambient authority를 줄입니다

Ambient authority는 process가 명시적으로 요청하지 않아도 주변 환경에서 얻는 권한입니다.

예:

- node 또는 VM metadata credential
- 공유 kubeconfig
- runner host에 남은 cloud key
- 모든 namespace를 읽는 service account
- build job에 자동 주입된 production secret
- developer laptop의 오래된 admin token

대신 다음을 사용합니다.

```text
작업 identity 확인
→ 필요한 resource와 action을 요청
→ policy 평가
→ 짧은 수명의 credential 발급
→ 사용 기록
→ 작업 종료 또는 만료
```

Credential broker가 실패할 때 기존 장기 key로 자동 fallback하지 않습니다.

## 4. Secret의 세 종류

### Source secret

외부 registry, SaaS와 cloud API에 접근하는 원본 credential입니다. 가능하면 플랫폼의 secret system에만 존재합니다.

### Reference

Workload 또는 configuration이 필요한 secret을 가리키는 식별자입니다. Git과 catalog에는 plaintext가 아니라 reference를 둡니다.

### Materialized credential

실행 시점에 workload에 전달된 실제 token·certificate·password입니다. 수명과 저장 위치를 제한합니다.

Secret을 configuration value와 같은 방식으로 복사하면 다음 문제가 생깁니다.

- Git·artifact·log에 노출됩니다.
- owner와 consumer를 찾기 어렵습니다.
- rotation이 여러 저장소와 deployment에 의존합니다.
- 폐기 뒤에도 cache와 filesystem에 남습니다.

## 5. Secret 전달 계약

결정할 항목:

- secret owner와 발급 authority
- consumer identity
- 사용 목적과 대상
- 전달 방식: file, environment, socket, sidecar, dynamic API
- materialization 시점
- TTL과 rotation
- process reload 또는 restart
- redaction
- revocation
- 실패 시 행동

Environment variable은 간단하지만 process dump, child process와 debug output에 노출될 수 있습니다. File mount도 permission, update와 cleanup이 필요합니다. “secret manager를 쓴다”는 제품 이름만으로 안전을 증명하지 않습니다.

### Rotation 상태

```text
새 credential 발급
→ consumer가 후보를 읽음
→ dependency 연결 검증
→ 새 version 활성화
→ old version 사용량 관찰
→ old version 폐기
→ materialized copy 정리
```

후보 검증 전에 old credential을 폐기하지 않습니다. 반대로 무기한 dual-valid 상태로 두지도 않습니다.

## 6. Policy 적용 지점

하나의 gate로 모든 정책을 해결하지 않습니다.

| 단계 | 빠르게 확인할 것 | 한계 |
|---|---|---|
| local/IDE | schema, lint, 기본 contract | 우회 가능, 신뢰 경계 아님 |
| pull request | source·IaC·manifest 검사 | rendered/live context 부족 |
| build | dependency·SBOM·provenance | 배포 context를 모름 |
| platform API | owner·quota·environment·approval | 하위 runtime mutation 전 |
| admission | 최종 object와 cluster context | 이미 늦은 피드백일 수 있음 |
| runtime | process·network·behavior | 사전 차단보다 탐지 중심 |
| audit/continuous | drift·exception·aging | 즉시 차단하지 않을 수 있음 |

같은 규칙을 여러 단계에서 사용할 수 있지만, 각 단계의 입력과 결과를 명확히 합니다.

## 7. Policy as code의 계약

Policy repository에는 규칙만 아니라 다음이 필요합니다.

- policy ID와 목적
- owner
- 적용 resource와 environment
- severity
- 결정: allow, deny, warn, mutate
- 예외 조건
- test fixture
- rollout mode
- version과 changelog
- remediation
- telemetry

예시는 [`examples/policy/platform-policy.json`](../examples/policy/platform-policy.json)에 있습니다.

### Deny와 warn

처음부터 모든 violation을 차단하면 production 변화와 오래된 workload가 멈출 수 있습니다.

권장 rollout:

```text
inventory
→ audit/warn
→ owner와 remediation 제공
→ 신규 resource deny
→ 기존 resource migration
→ 전체 enforce
```

긴급한 고위험 문제는 더 빠르게 차단할 수 있지만 blast radius와 복구 경로를 확인합니다.

## 8. Mutation의 위험

Admission 또는 platform API가 사용자의 요청을 자동 수정할 수 있습니다.

유용한 예:

- standard label 추가
- telemetry sidecar 또는 config 주입
- safe default 설정

위험:

- 사용자가 실제 실행 spec을 예측하지 못합니다.
- 다른 mutator와 순서 의존성이 생깁니다.
- controller field ownership 충돌이 생깁니다.
- upgrade 때 모든 workload 동작이 한 번에 바뀝니다.

Mutation 결과를 조회할 수 있게 하고, 중요한 의미 변경은 명시적 profile version으로 다룹니다.

## 9. Policy exception

예외는 deny를 우회하는 비공식 annotation이 아닙니다.

최소 정보:

- policy ID
- resource와 scope
- business/technical reason
- risk owner
- approver
- compensating control
- created/expiry time
- renewal 횟수
- 종료 조건
- audit reference

예외 만료 전 owner에게 알리고, 만료 뒤 자동 차단이 안전한지 단계별로 결정합니다. Production workload를 예고 없이 중단시키는 방식으로 예외를 종료하지 않습니다.

## 10. Break-glass identity

Emergency identity는 평소 권한을 크게 주는 대신 사용하지 않는 계정이 아닙니다.

계약:

- 정상 identity path 장애 또는 긴급 사용자 영향에만 사용
- 별도 강한 인증
- 시간 제한과 좁은 scope
- 자동 session recording 또는 audit
- 사용 즉시 alert
- 가능한 한 read/diagnose와 write/mitigate 역할 분리
- 작업 종료 뒤 credential 폐기
- 후속 review와 desired state 반영

Break-glass가 작동하는지도 정기적으로 안전한 환경에서 검증합니다.

## 11. 권한 변경 lifecycle

Join, move, leave와 team ownership 변경을 자동 반영합니다.

```text
사람이 팀 이동
→ directory group 변경
→ platform role 재계산
→ old access 제거
→ active session·token 처리
→ audit와 owner 확인
```

Resource owner가 해체된 team으로 남아 있으면 approval·incident·cost 책임이 사라집니다. Catalog owner 검사를 주기적으로 수행합니다.

## 12. 관측과 사고 대응

기록할 사건:

- authentication 실패와 위험 session
- authorization deny
- credential 발급·갱신·폐기
- secret access와 consumer
- policy decision과 version
- exception 생성·연장·만료
- break-glass 시작·행동·종료
- 권한 변경과 orphan owner

Secret value와 민감 payload는 기록하지 않습니다. Audit store는 platform operator가 임의 수정하기 어렵게 분리합니다.

## 13. 실습

[`08-identity-policy`](../exercises/08-identity-policy/)에서 다음을 설계합니다.

- 사람·workload·automation identity
- 작업별 권한과 trust boundary
- secret reference·materialization·rotation
- policy 적용 단계
- deny/warn rollout
- exception과 break-glass 수명
- audit event와 redaction

## 14. 검토 질문

- 개인 token이 automation에 재사용되지 않습니까?
- Build, publish, deploy와 infrastructure 권한이 분리됩니까?
- Workload credential이 짧은 수명과 좁은 audience를 가집니까?
- Secret의 원본·reference·materialized copy가 구분됩니까?
- Policy가 가장 빠른 피드백과 최종 enforcement를 함께 제공합니까?
- Mutation이 실행 결과를 숨기지 않습니까?
- 예외와 break-glass에 owner·scope·expiry·audit가 있습니까?
- 팀 이동·퇴사·서비스 폐기 뒤 권한과 secret이 정리됩니까?

다음 장에서는 이 제어 경로가 실제로 동작하는지 사용자 여정, 내부 component와 audit evidence를 연결해 관측합니다.
