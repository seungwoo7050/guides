# PaaS와 managed service 계약

관리형 서비스는 운영을 제거하지 않습니다. 운영의 일부를 공급자에게 이전하고, 소비자는 더 높은 수준의 configuration·data·compatibility·cost·exit 책임을 가집니다.

이 문서는 “누가 patch하는가”를 넘어, 관리형 서비스의 외부 계약과 숨겨진 상태를 어떻게 검토할지 다룹니다.

## 1. Managed의 의미를 작업별로 분해한다

관리형 database를 예로 들면 공급자는 보통 다음을 담당할 수 있습니다.

- host와 storage fabric
- engine installation
- 일부 patching
- replica orchestration
- metric export
- automated backup 기능

소비자에게 남는 것:

- schema와 query
- transaction contract
- connection management
- access policy
- backup retention과 restore drill
- maintenance window
- version compatibility
- extension과 parameter
- capacity와 quota
- data classification
- migration과 exit

제품 문구가 아니라 실제 task와 evidence로 responsibility를 작성합니다.

## 2. Service contract의 필수 항목

```text
capability
control surface
data model
identity and network
availability scope
consistency or delivery semantics
limits and quotas
maintenance and version lifecycle
backup and restore
observability
data export and deletion
cost unit
support and incident path
```

모든 항목을 공급자가 명시적으로 보장하지는 않습니다. 문서에 없는 부분은 가정이 아니라 unknown으로 기록하고 검증 또는 support 문의가 필요합니다.

## 3. Hidden state

관리형 서비스는 내부 node·process를 숨기지만 상태가 없어지는 것은 아닙니다.

- replica lag
- storage compaction
- queue partition
- runtime pool
- background maintenance
- index build
- cache warming
- connection proxy
- failover state
- quota accounting

소비자는 내부 구현을 직접 보지 못할 수 있으므로 외부 signal과 service-level metric으로 판단합니다.

## 4. Version과 maintenance

질문:

- runtime 또는 engine version을 누가 선택합니까?
- 자동 upgrade와 opt-in upgrade가 어떻게 다릅니까?
- deprecated version의 종료 일정은 어떻게 통지됩니까?
- maintenance 중 connection과 request는 어떻게 됩니까?
- extension·driver·protocol 호환성은 누가 검증합니까?
- rollback이 가능합니까, migration이 irreversible합니까?

관리형 서비스는 patch burden을 줄이지만 지원 종료와 강제 upgrade라는 새 event를 만듭니다.

## 5. Availability claim

SLA와 실제 architecture를 구분합니다.

- SLA는 보상 계약일 수 있으며 application recovery를 대신하지 않습니다.
- multi-zone 기능이 모든 resource와 operation에 적용되는지 확인합니다.
- control plane 장애 중 data plane이 계속 동작하는지 확인합니다.
- failover 시 connection, DNS, transaction과 in-flight request가 어떻게 되는지 확인합니다.
- scheduled maintenance와 customer misconfiguration이 SLA에서 제외될 수 있습니다.

## 6. Backup과 restore

“automated backup enabled”만으로는 부족합니다.

- snapshot 주기
- transaction log 또는 point-in-time 범위
- retention
- cross-account 또는 cross-region copy
- encryption key dependency
- logical corruption 복구
- deleted service의 backup lifecycle
- restore target과 network
- restore 완료 뒤 schema·row·business invariant

공급자가 backup artifact를 만들더라도 restore drill과 application consistency는 소비자가 검증합니다.

## 7. Network와 identity

managed endpoint가 public인지 private인지, private endpoint가 DNS와 route에 어떤 dependency를 갖는지 확인합니다.

- client workload identity
- service resource policy
- database/application role
- admin identity
- provider maintenance identity
- support access
- key access

cloud IAM allow가 database row authorization을 대신하지 않습니다.

## 8. Limits와 quota

관리형 서비스는 많은 내부 운영을 숨기지만 limit를 노출합니다.

- connection
- request rate
- payload size
- object count
- partition throughput
- retention
- execution time
- concurrent operation
- backup count
- API rate

limit 초과 시 동작을 확인합니다.

```text
reject
throttle
queue
degrade
partial success
bill more
request manual quota increase
```

limit는 architecture 입력입니다. 문서 footer가 아닙니다.

## 9. Observability

공급자 metric만으로 business success를 알 수 없습니다. 다음 계층을 연결합니다.

- provider service health
- resource metric
- client-side latency와 error
- application trace
- business outcome
- cost and usage

예를 들어 managed queue의 message count가 감소해도 잘못된 consumer가 data를 버렸을 수 있습니다. 최종 업무 상태와 대조해야 합니다.

## 10. Data ownership와 exit

관리형 서비스 선택 전에 종료 절차를 적습니다.

- export format
- full·incremental export
- consistency point
- schema·metadata·ACL 포함 여부
- key와 secret
- transfer bandwidth와 egress cost
- destination import
- dual-write 또는 freeze
- validation
- source deletion과 retention
- provider backup 잔존

export 기능이 있다는 사실과 실제 migration 가능성은 다릅니다. 데이터량과 변경률을 포함해 rehearsal합니다.

## 11. Build versus buy

관리형 서비스를 선택하는 이유는 단순한 편의가 아닙니다.

비교:

| 기준 | 직접 운영 | managed service |
|---|---|---|
| 제어 | 높음 | 제한될 수 있음 |
| 운영 부담 | 높음 | 일부 이전 |
| 표준 기능 | 직접 구성 | 빠르게 사용 |
| custom extension | 자유로움 | 제한 가능 |
| scaling | 직접 설계 | 기능 제공, limit 존재 |
| failure visibility | 내부까지 관찰 | 외부 contract 중심 |
| 비용 | 인력+resource | premium+usage+egress |
| exit | artifact 제어 가능 | API·format·provider dependency |

team 역량, workload 중요도, change rate와 total cost를 함께 판단합니다.

## 12. 계약 검토 질문

1. 어떤 운영 작업이 실제로 공급자에게 이동합니까?
2. 어떤 작업은 기능만 제공되고 실행 책임은 소비자에게 남습니까?
3. version·maintenance·quota가 application에 어떤 event를 만듭니까?
4. provider 내부 failure를 어떤 외부 signal로 감지합니까?
5. restore와 export를 마지막으로 언제 검증했습니까?
6. service가 없어져도 data와 configuration을 재구성할 수 있습니까?
7. 비용이 workload와 tenant에 귀속됩니까?

## 연결 실습

[03 managed service 계약](../exercises/03-managed-service-contract/README.md)에서 가상의 database·queue·object service를 비교하고 unknown, consumer evidence와 exit를 작성합니다.
