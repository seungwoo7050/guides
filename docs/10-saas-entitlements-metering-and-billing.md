# Entitlement, metering와 billing

SaaS의 상업 상태는 애플리케이션 기능과 분리해서 모델링해야 합니다.

```text
plan
판매 가능한 상품 정의

subscription
tenant가 선택한 계약 상태

entitlement
현재 tenant가 사용할 수 있는 capability

quota
허용된 사용량 또는 동시성 상한

metering
실제 사용량 기록

billing
가격 규칙을 적용해 청구 상태를 생성
```

이들을 하나의 `is_paid` boolean으로 축약하면 upgrade·downgrade·trial·grace period·refund와 partial provisioning을 처리하기 어렵습니다.

## 1. Plan

plan은 이름이 아니라 versioned product definition입니다.

```text
plan_id
version
currency
billing_period
base_price
included_usage
feature_set
limits
overage_rule
effective_from
retired_at
```

기존 subscription에 plan 변경을 자동 적용할지, grandfathering할지 정합니다.

## 2. Subscription state

대표 상태:

```text
TRIAL
→ ACTIVE
→ PAST_DUE
→ GRACE
→ SUSPENDED
→ CANCELED
→ ENDED
```

외부 payment provider 상태와 내부 service state는 동일하지 않을 수 있습니다. webhook 지연·중복·순서 역전을 고려합니다.

subscription change는 여러 작업을 일으킵니다.

- entitlement update
- quota update
- invoice 또는 proration
- resource provisioning
- notification
- audit

일부만 성공하면 reconciliation이 필요합니다.

## 3. Entitlement

entitlement는 “이 기능을 쓸 수 있는가”에 답합니다.

입력:

- tenant
- plan version
- add-on
- contract override
- rollout flag
- region·compliance constraint
- subscription state

결정은 server-side에서 수행하고 UI hide를 authorization으로 사용하지 않습니다.

entitlement evidence:

```text
tenant_id
feature
allowed
source_plan_or_override
version
evaluated_at
expires_at
```

## 4. Quota

quota는 수량과 기간, scope를 가집니다.

- storage bytes
- project count
- monthly processed documents
- concurrent jobs
- API request rate
- user seats

### Hard quota

초과 action을 거부합니다. 거부 전에 partial state가 생기지 않아야 합니다.

### Soft quota

초과를 허용하지만 alert 또는 overage billing을 만듭니다.

### Burst quota

짧은 burst를 허용하고 장기 평균을 제한합니다.

### Concurrency quota

현재 실행 중인 작업 수를 제한합니다. distributed environment에서는 atomic counter·lease·partitioned limit가 필요합니다.

## 5. Quota의 원자성

나쁜 구현:

```text
usage 조회
→ limit 비교
→ resource 생성
→ usage 증가
```

두 요청이 동시에 limit를 통과할 수 있습니다.

안전한 방법:

- database constraint
- conditional update
- reservation
- token bucket
- transactional outbox
- idempotent usage record

실패하면 reservation을 release하거나 expiration으로 회수합니다.

## 6. Metering event

usage event는 다음을 가집니다.

```text
event_id
tenant_id
metric
quantity
unit
occurred_at
source
resource_id
idempotency_key
schema_version
```

### 기준

- 같은 event를 두 번 수집해도 한 번만 집계합니다.
- tenant가 항상 존재하고 귀속 근거가 있습니다.
- late event와 correction을 처리합니다.
- negative adjustment와 refund를 원본 event에 연결합니다.
- raw event와 aggregate의 보존 기간을 정합니다.

## 7. Measurement와 billing을 분리한다

metering은 사실을 기록하고 billing은 가격을 적용합니다.

```text
1000 document-pages processed
```

은 measurement입니다.

```text
included 500 pages
+ overage 500 × unit price
+ discount
+ tax
```

는 billing입니다.

가격 변경 때문에 raw usage를 다시 평가할 수 있어야 합니다. aggregate만 저장하면 분쟁 해결이 어려울 수 있습니다.

## 8. External billing provider

외부 결제 서비스는 payment method, charge, invoice delivery 일부를 맡을 수 있지만 내부 product entitlement의 정본을 자동으로 제공하지 않을 수 있습니다.

문제:

- webhook duplicate
- out-of-order update
- API timeout 후 charge 결과 unknown
- charge success 후 entitlement update 실패
- refund 후 usage state 불일치
- provider customer와 tenant mapping 오류

필요한 상태:

- external object ID
- internal tenant·subscription ID
- event cursor 또는 processed ID
- reconciliation job
- manual correction audit

## 9. Upgrade와 downgrade

### Upgrade

- 즉시 entitlement 확대 여부
- quota reset 또는 유지
- resource provisioning
- proration
- provisioning 실패 시 rollback

### Downgrade

현재 사용량이 새 limit보다 클 수 있습니다.

선택:

- 새 생성만 금지
- grace period
- archive
- 강제 delete 금지
- next billing period 적용

고객 data를 자동 삭제해 quota에 맞추는 것은 위험합니다.

## 10. Trial과 abuse

trial은 subscription 상태이자 abuse surface입니다.

- duplicate account
- resource mining
- invitation abuse
- payment verification
- data retention after trial
- export right

일반 공격 경로와 abuse 검증은 [`cybersecurity`의 attack surface와 paths](https://github.com/seungwoo7050/guides/blob/cybersecurity/docs/05-attack-surface-and-paths.md)와 실제 product project에서 확장합니다. 여기서는 trial이 cloud resource·quota·measured usage와 tenant deletion에 남기는 상태만 다룹니다.

## 11. Cost attribution

provider bill과 SaaS usage는 동일하지 않습니다.

- shared database cost
- per-request function cost
- storage
- egress
- support
- third-party API

tenant별 unit economics를 계산하려면 resource cost를 usage driver로 배분해야 합니다. 완벽한 정확성보다 일관된 allocation rule과 변경 version이 중요합니다.

## 12. Audit와 분쟁

고객이 usage 또는 invoice를 이의 제기할 때 다음을 재구성할 수 있어야 합니다.

- 어떤 event가 집계됐는가
- duplicate가 제거됐는가
- 어떤 plan version과 가격이 적용됐는가
- manual adjustment가 있었는가
- 시간대와 period boundary는 무엇인가
- correction invoice가 어떻게 연결되는가

## 13. Local model 불변식

```text
quota 초과 request는 document를 만들지 않습니다.
같은 event ID는 usage를 한 번만 증가시킵니다.
삭제된 tenant는 새 usage를 만들 수 없습니다.
usage는 정확히 한 tenant에 귀속됩니다.
```

## 연결 실습

[05 SaaS tenant isolation](../exercises/05-saas-tenant-isolation/README.md)에서 entitlement와 tenant boundary를 연결하고, [06 비용과 exit](../exercises/06-cost-and-exit/README.md)에서 provider 비용과 SaaS usage를 구분합니다.
