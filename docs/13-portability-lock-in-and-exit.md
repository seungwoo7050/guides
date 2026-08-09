# Portability, lock-in과 exit

특정 공급자 기능을 사용하는 것은 자동으로 나쁜 설계가 아닙니다. 문제는 dependency를 인식하지 못하거나, 이득과 교체 비용을 검증하지 않은 상태입니다.

```text
lock-in
교체 비용이 존재하는 상태

unmanaged lock-in
비용·절차·owner·exit evidence가 없는 상태
```

목표는 모든 것을 lowest common denominator로 제한하는 것이 아니라 deliberate dependency를 만드는 것입니다.

## 1. Dependency 종류

### API dependency

provider SDK, event format, identity API, monitoring query와 deployment interface입니다.

### Semantic dependency

consistency, delivery, transaction, ordering, timeout와 retry behavior입니다. 이름이 같은 다른 서비스로 바꿔도 semantics가 다를 수 있습니다.

### Data dependency

proprietary format, index, feature, large data volume, egress와 export speed입니다.

### Operational dependency

runbook, dashboard, alert, on-call, support와 team skill입니다.

### Commercial dependency

discount commitment, contract, license, minimum spend와 data transfer 가격입니다.

### Organizational dependency

security approval, account structure, compliance evidence와 vendor relationship입니다.

## 2. Portability 층

| 층 | 질문 |
|---|---|
| source | code와 configuration을 다른 환경에서 build할 수 있는가 |
| artifact | image·bundle·schema가 portable한가 |
| runtime | 필요한 OS·API·limit를 다른 환경이 제공하는가 |
| data | full·incremental export와 import가 가능한가 |
| identity | account·role·tenant mapping을 재구성할 수 있는가 |
| operation | monitoring·backup·incident workflow를 옮길 수 있는가 |
| commercial | commitment·egress·contract 종료 비용은 얼마인가 |

container image가 portable해도 data, identity와 operation은 그렇지 않을 수 있습니다.

## 3. Abstraction의 비용

provider-neutral wrapper를 만들면 일부 API dependency를 줄일 수 있지만 다음 비용이 생깁니다.

- provider 고유 기능을 사용하지 못함
- lowest common denominator
- 자체 control plane과 bug
- observability 손실
- team이 두 추상화를 이해해야 함

wrapper는 실제로 교체할 가능성과 변경 빈도가 있을 때 사용합니다. 모든 provider API를 미리 감싸는 것은 낭비일 수 있습니다.

## 4. Exit plan

exit는 “나중에 export합니다”가 아닙니다.

```text
trigger
owner
scope
freeze or dual-run strategy
full data export
incremental catch-up
schema and metadata
identity mapping
configuration and secret
new environment validation
traffic cutover
rollback window
source retention and deletion
cost and duration
```

## 5. Data migration

### Snapshot migration

쓰기 중단 후 consistent snapshot을 옮깁니다. 간단하지만 downtime이 필요합니다.

### Dual-write

새·기존 시스템에 동시에 씁니다. divergence와 reconciliation이 어려워집니다.

### Change capture

initial snapshot 뒤 change stream을 따라갑니다. ordering, schema evolution과 replay를 처리해야 합니다.

### Application-level export/import

business object로 옮겨 provider storage semantics에서 분리할 수 있지만 대용량·속도·hidden metadata 문제가 있습니다.

## 6. Serverless migration

function code만 옮기는 것이 아닙니다.

- trigger와 event schema
- retry·batch·ordering semantics
- identity
- timeout·memory·concurrency
- network
- destination·DLQ
- logs·trace
- deployment version

같은 handler가 실행돼도 delivery contract가 달라 결과가 달라질 수 있습니다.

## 7. SaaS provider exit

외부 SaaS를 소비하는 조직도 exit를 준비해야 합니다.

- user·group·role export
- data와 attachment
- audit
- API rate와 export limit
- retention after termination
- encryption key
- integration token revoke
- legal hold
- replacement workflow

완성 SaaS를 만드는 공급자는 고객에게 export와 deletion evidence를 제공해야 합니다.

## 8. Multi-cloud

여러 provider를 동시에 사용하면 특정 failure와 commercial dependency를 줄일 수 있지만 다음을 증가시킵니다.

- identity와 network complexity
- duplicate platform
- data consistency
- skill requirement
- observability correlation
- security policy drift
- steady cost

multi-cloud은 backup strategy, acquisition, regulation, customer requirement 등 구체적인 이유가 있어야 합니다. “lock-in 방지” 한 문장으로 정당화하지 않습니다.

## 9. Exit rehearsal

실제 migration 전체를 자주 수행하기 어렵다면 작은 rehearsal을 합니다.

- representative data export
- clean environment import
- checksum와 business invariant
- identity remap
- application smoke
- measured throughput
- estimated total duration
- egress cost

rehearsal 결과로 plan을 갱신합니다.

## 10. Deletion evidence

서비스 종료 뒤 다음을 확인합니다.

- active resource 없음
- snapshot·backup retention
- object version
- key state
- log와 audit legal retention
- support copy
- invoice close
- DNS·certificate·token revoke

공급자 내부 media 삭제는 service contract의 범위일 수 있으므로 소비자가 직접 증명할 수 있는 것과 공급자 attest에 의존하는 것을 구분합니다.

## 11. Lock-in register

각 dependency를 기록합니다.

```text
dependency
benefit
alternative
migration obstacle
data volume
estimated effort
trigger
owner
last rehearsal
accepted_until
```

모든 lock-in을 제거하지 않고, 이득이 비용보다 큰 동안 의식적으로 유지합니다.

## 연결 실습

[03 managed service 계약](../exercises/03-managed-service-contract/README.md)과 [06 비용과 exit](../exercises/06-cost-and-exit/README.md)에서 export·replacement·deletion을 실제 순서와 estimate로 작성합니다.
