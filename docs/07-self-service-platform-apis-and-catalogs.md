# Self-service platform API와 software catalog

개발자 portal은 플랫폼의 화면일 수 있지만 플랫폼 자체는 아닙니다. 사람이 화면을 누르지 않아도 CI, CLI와 다른 controller가 같은 결과를 요청할 수 있어야 합니다. 그러려면 먼저 안정적인 **platform API**, 비동기 작업의 상태 모델과 소유권을 표현하는 **software catalog**가 필요합니다.

이 장은 [`02 플랫폼 계약과 책임 경계`](02-platform-contracts-and-ownership.md)와 [`03 Control plane과 reconciliation`](03-control-planes-and-reconciliation.md)의 계약을 실제 self-service 인터페이스로 확장합니다.

Backstage catalog와 template의 공식 역할은 [source index의 platform product](../reference/source-index.md#platform-product)를 확인합니다. Catalog metadata가 platform API의 실행 상태나 control plane 정본을 자동으로 대신하지 않는다는 경계를 유지합니다.

## 1. Self-service가 의미하는 것

Self-service는 승인과 책임을 없애는 것이 아닙니다.

```text
사용자가 필요한 결과를 선언
→ 플랫폼이 입력·정책·quota를 즉시 검증
→ 자동화 가능한 작업은 기다림 없이 시작
→ 사람 판단이 필요한 작업은 명시적인 승인 상태로 전환
→ 진행·실패·복구 상태를 사용자가 직접 조회
```

다음은 self-service가 아닙니다.

- portal form이 ticket을 대신 생성합니다.
- 성공 여부를 platform team에게 채팅으로 물어야 합니다.
- API는 `200 OK`를 반환하지만 실제 provisioning 결과를 추적할 식별자가 없습니다.
- 실패 이유가 controller log에만 있고 요청자에게 보이지 않습니다.
- 같은 요청을 다시 보내면 중복 resource가 생깁니다.
- 삭제나 취소 뒤 남는 자원을 확인할 방법이 없습니다.

## 2. 결과 중심 API

Platform API는 cloud resource와 Kubernetes object를 그대로 노출하는 것보다 사용자가 원하는 결과를 표현해야 합니다.

예를 들어 개발자는 다음 결과를 요청합니다.

```json
{
  "apiVersion": "platform.northstar.dev/v1alpha1",
  "kind": "ServiceEnvironment",
  "metadata": {
    "name": "checkout-staging",
    "owner": "team-checkout"
  },
  "spec": {
    "service": "checkout",
    "environmentClass": "staging",
    "releaseDigest": "sha256:example",
    "dataProfile": "postgres-small",
    "exposure": "internal"
  }
}
```

이 요청이 내부적으로 namespace, database, workload identity, secret reference, DNS와 deployment를 만들 수 있습니다. 그러나 API 사용자가 그 구현 순서를 직접 조정하게 만들면 플랫폼이 아니라 자동화 library를 제공한 셈입니다.

결과 중심 API에는 최소한 다음이 필요합니다.

- **식별자:** 동일한 의도를 다시 제출했는지 판단합니다.
- **version:** 입력 구조와 의미의 호환 범위를 고정합니다.
- **desired state:** 사용자가 원하는 최종 결과입니다.
- **status:** 현재 관측과 다음 행동을 설명합니다.
- **condition:** `Ready`, `Progressing`, `Degraded`, `Blocked` 같은 안정적인 상태입니다.
- **generation:** 어떤 요청 세대의 결과인지 구분합니다.
- **owner:** 변경·승인·복구 책임자를 찾습니다.
- **deletion policy:** 삭제 시 보존·snapshot·폐기할 상태를 정합니다.

예시 schema는 [`examples/platform-api/service-environment.schema.json`](../examples/platform-api/service-environment.schema.json)에 있습니다.

## 3. 동기 응답과 비동기 결과

Infrastructure 생성과 deployment는 보통 요청 시간 안에 끝나지 않습니다. API는 작업이 완료되지 않았는데 완료된 것처럼 응답하면 안 됩니다.

### 권장 흐름

```text
POST /service-environments
→ 202 Accepted
→ resource identity와 status URL 반환
→ controller가 dependency를 순차 수렴
→ condition과 event 갱신
→ 외부 검증이 통과하면 Ready
```

응답 예:

```json
{
  "id": "service-environment/checkout-staging",
  "generation": 4,
  "statusUrl": "/v1/service-environments/checkout-staging",
  "condition": "Progressing"
}
```

### 완료 판정

`Ready`는 모든 하위 API 호출이 성공했다는 뜻으로 정의하면 부족합니다. 사용자가 실제로 의존하는 결과를 확인해야 합니다.

```text
resource 생성
+ workload Available
+ policy 적용
+ route 또는 DNS 준비
+ 외부 smoke 성공
+ catalog 상태와 실제 generation 일치
= Ready
```

각 플랫폼 capability는 자신이 보장할 수 있는 완료 조건만 선언합니다. 애플리케이션의 업무 정합성을 platform controller가 대신 주장하지 않습니다.

## 4. 오류 분류와 사용자 행동

오류 메시지는 내부 stack trace가 아니라 다음 행동을 알려야 합니다.

| 오류 종류 | 예 | 자동 재시도 | 사용자에게 필요한 행동 |
|---|---|---:|---|
| 입력 오류 | 지원하지 않는 profile | 아니요 | 입력 수정 |
| 정책 거부 | production 공개 endpoint 승인 누락 | 아니요 | 승인 요청 또는 범위 변경 |
| quota 부족 | tenant CPU quota 초과 | 조건부 | 기존 resource 정리 또는 quota 변경 |
| 일시 dependency 실패 | cloud API timeout | 예 | 상태 관찰, budget 초과 시 문의 |
| 영구 dependency 실패 | region에서 type 미지원 | 아니요 | profile 또는 region 변경 |
| 내부 결함 | controller invariant 위반 | 아니요 | platform team 조사 |
| 취소 충돌 | irreversible migration 진행 중 | 아니요 | 안전한 완료 또는 복구 절차 선택 |

안정적인 machine-readable error code와 사람용 설명을 분리합니다.

```json
{
  "code": "POLICY_APPROVAL_REQUIRED",
  "message": "production 공개 경로에는 security approval이 필요합니다.",
  "retryable": false,
  "owner": "platform-security",
  "evidence": "audit-event/01J..."
}
```

## 5. Idempotency와 중복 요청

사용자가 응답을 받지 못하면 같은 요청을 다시 보냅니다. platform API는 중복을 예외가 아니라 정상 입력으로 다룹니다.

가능한 식별 방법:

- resource 이름과 owner를 자연 key로 사용합니다.
- client가 `Idempotency-Key`를 제공합니다.
- spec의 canonical hash를 generation과 함께 저장합니다.
- request ID와 operation ID를 분리합니다.

다음은 피합니다.

- 매 요청마다 임의 이름의 resource를 생성합니다.
- timeout이면 생성 여부를 확인하지 않고 다시 생성합니다.
- controller가 이전 operation의 결과를 찾을 수 없습니다.
- 동일 spec의 재제출과 의도적인 새 generation을 구분하지 않습니다.

## 6. 취소와 삭제

취소는 단순 `DELETE`가 아닙니다. provisioning 도중 이미 만들어진 외부 자원, data와 credential의 처리 계약이 필요합니다.

```text
요청 수락
→ 일부 resource 생성
→ 사용자 취소
→ 새 단계 시작 차단
→ reversible 단계 rollback
→ 보존 대상 snapshot 또는 retention 적용
→ credential 폐기
→ orphan 검사
→ terminal condition 기록
```

삭제 정책 예:

- `Delete`: 환경과 비영구 data를 폐기합니다.
- `RetainData`: runtime은 제거하지만 database snapshot은 보존합니다.
- `Archive`: catalog와 audit evidence를 유지하고 실행 자원만 제거합니다.
- `Block`: 법적 보존 또는 production 보호 때문에 자동 삭제를 거부합니다.

정책 이름만 제공하지 말고 보존 기간, 비용 소유자와 복구 절차를 함께 명시합니다.

## 7. Software catalog의 역할

Catalog는 서비스 목록 페이지가 아니라 **소유권과 관계의 검색 가능한 정본**입니다.

최소 metadata:

- 서비스·library·resource의 안정적인 ID
- owner team과 연락·escalation 경로
- repository와 주요 release pipeline
- runtime environment와 dependency
- API와 event contract
- data classification과 exposure
- runbook·dashboard·SLO
- lifecycle 상태와 deprecation 시점
- platform profile과 현재 version

예시는 [`examples/catalog/component.yaml`](../examples/catalog/component.yaml)에 있습니다.

Catalog가 직접 cloud와 cluster의 모든 실시간 상태를 소유하지는 않습니다. 정적 metadata, desired 관계와 관측 결과를 구분합니다.

| 정보 | 권장 정본 |
|---|---|
| 서비스 이름과 owner | catalog source repository 또는 platform API |
| 현재 release digest | deployment controller 또는 release record |
| 현재 Pod 상태 | Kubernetes API |
| SLO 계산 | telemetry backend |
| 승인 이력 | audit store |
| 비용 | billing/usage system |

Catalog 화면은 여러 정본을 읽어 조합할 수 있지만, 화면 cache를 새로운 정본으로 만들지 않습니다.

## 8. Portal, catalog, template와 control plane

구성요소를 구분합니다.

```text
Portal
사용자에게 문서·검색·상태·요청 UI를 제공합니다.

Catalog
component·owner·dependency·lifecycle metadata를 제공합니다.

Template
새 repository나 configuration의 시작 구조를 생성합니다.

Platform API
사용자가 원하는 결과를 안정적인 계약으로 받습니다.

Control plane
desired state를 외부 시스템의 실제 상태로 수렴시킵니다.
```

Portal이 중단돼도 API와 controller는 계속 동작할 수 있어야 합니다. Template을 다시 실행할 수 없더라도 생성된 서비스는 표준 upgrade 경로로 진화해야 합니다. Catalog가 오래됐다고 실제 workload를 즉시 삭제하지 않습니다.

## 9. API version과 compatibility

Platform API는 내부 구현보다 오래 살아남을 수 있습니다.

변경을 다음으로 구분합니다.

- 새 optional field 추가
- default 변경
- validation 강화
- 의미 변경
- field rename 또는 제거
- 상태 condition 변경
- 외부 효과 순서 변경

JSON schema가 호환돼도 의미가 바뀌면 breaking change일 수 있습니다. 예를 들어 `exposure: internal`의 network 범위를 바꾸면 같은 입력이 다른 보안 경계를 만듭니다.

Version 정책에는 다음이 필요합니다.

- 지원 version 목록
- conversion 또는 migration 경로
- default가 적용된 최종 spec을 조회하는 방법
- warning과 deprecation 기간
- old client의 행동 검사
- rollback 시 어느 version을 복원하는지

자세한 변화 관리는 [`15 Upgrade·migration·deprecation`](15-upgrades-migrations-and-deprecation.md)에서 다룹니다.

## 10. API의 운영 근거

Platform API에 필요한 기본 신호:

- 요청량과 요청자
- validation·policy 거부율
- provisioning latency 분포
- condition별 체류 시간
- controller retry와 dependency error
- 취소·삭제·orphan 수
- version별 사용량
- request ID에서 외부 resource까지 이어지는 trace

민감 spec과 secret은 audit event와 trace에 그대로 남기지 않습니다. 누가 어떤 type의 요청을 어떤 policy version으로 수행했는지 추적하되 credential과 민감 data는 redaction합니다.

## 11. 실습

[`06-self-service`](../exercises/06-self-service/)에서 다음을 작성합니다.

- versioned platform API resource
- 비동기 상태와 condition
- idempotency key
- 오류 code와 retryability
- 취소·삭제 정책
- catalog metadata와 정본
- portal이 없어도 가능한 automation 경로

검사기는 필요한 계약 요소가 존재하는지만 확인합니다. 실제 조직에서 이해 가능한 API인지는 user journey test와 운영 evidence로 추가 검증해야 합니다.

## 12. 검토 질문

- API가 cloud·Kubernetes 구현 세부가 아니라 사용자 결과를 표현합니까?
- 요청 수락과 실제 완료를 분리합니까?
- 같은 요청을 재전송해도 중복 외부 효과가 생기지 않습니까?
- condition이 사용자 행동과 platform owner를 알려 줍니까?
- 취소·삭제 뒤 data·credential·orphan 처리가 명확합니까?
- catalog의 각 field가 어느 정본에서 오는지 설명할 수 있습니까?
- portal이 없어도 CLI·CI·controller가 같은 contract를 사용할 수 있습니까?
- version 변경이 기존 automation에 미치는 영향을 검사합니까?

다음 장에서는 이 API를 통해 제공할 **지원되는 경로와 서비스 수명 전체**를 설계합니다.
