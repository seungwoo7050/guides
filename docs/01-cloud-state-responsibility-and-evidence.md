# 클라우드 상태, 책임과 증거

클라우드 서비스를 평가할 때 가장 위험한 문장은 다음과 같습니다.

```text
managed라서 운영할 것이 없습니다.
serverless라서 서버가 없습니다.
multi-AZ라서 장애가 나지 않습니다.
autoscaling이라서 부하를 처리합니다.
암호화돼 있으므로 안전합니다.
```

모두 일부 조건에서는 맞지만, 실제 판단에 필요한 owner·state·event·failure·evidence가 빠져 있습니다. 이 문서는 클라우드의 마케팅 표현을 검증 가능한 계약으로 바꾸는 방법을 정리합니다.

## 1. 클라우드 자원도 상태 기계다

클라우드 자원은 콘솔에 나타난 아이콘이 아니라 상태를 가진 객체입니다.

예를 들어 VM은 다음과 같은 상태를 가질 수 있습니다.

```text
ABSENT
→ PROVISIONING
→ STARTING
→ RUNNING
→ STOPPING
→ STOPPED
→ DELETING
→ DELETED
```

실제 공급자는 더 많은 중간 상태와 실패 상태를 가질 수 있습니다. 중요한 점은 API 호출이 즉시 최종 상태를 보장하지 않는다는 것입니다.

```text
create 요청 성공
≠
instance가 실행 준비됨
≠
애플리케이션이 요청을 받을 준비가 됨
≠
외부 사용자가 정상 기능을 사용할 수 있음
```

따라서 변경 작업은 최소한 다음을 구분해야 합니다.

- 요청이 수락됐는가
- control plane 작업이 완료됐는가
- resource가 data plane 요청을 처리하는가
- dependency와 연결됐는가
- 업무 기능이 준비됐는가
- 실패 뒤 어떤 부분 상태가 남았는가

## 2. 다섯 종류의 상태

클라우드 설계에서는 모든 상태를 “인프라”라고 뭉치지 않습니다.

### 2.1 Desired state

사용자가 원하는 선언입니다.

```text
application instance 3개
private database
public HTTPS endpoint
object retention 30일
worker concurrency 최대 20
```

IaC, configuration, deployment manifest 또는 관리 API 요청이 desired state를 표현합니다.

### 2.2 Provider control state

공급자가 resource를 생성·연결·확장하기 위해 관리하는 상태입니다.

- resource ID
- region과 zone 배치
- lifecycle status
- policy와 attachment
- autoscaling target
- managed backup 설정

소비자는 API로 일부를 읽고 바꿀 수 있지만 내부 scheduler·hardware·control service는 직접 소유하지 않습니다.

### 2.3 Workload runtime state

실행 중인 애플리케이션과 프로세스의 상태입니다.

- process와 memory
- connection pool
- local cache
- temporary file
- in-flight request
- function execution context

VM에서는 소비자가 더 많이 제어하고, PaaS·FaaS에서는 공급자가 runtime lifecycle의 상당 부분을 제어합니다. 그렇더라도 workload가 만든 오류와 resource leak은 소비자의 책임으로 남습니다.

### 2.4 Durable business state

사용자·tenant·문서·결제·작업 결과처럼 서비스가 보존해야 하는 상태입니다. 저장 위치가 managed database나 object storage여도 의미와 보존·삭제 기준은 애플리케이션 소유자에게 남습니다.

### 2.5 Evidence state

변경과 장애를 설명하는 근거입니다.

- audit log
- resource event
- metric
- trace
- deployment record
- billing line item
- backup manifest
- restore report
- tenant export manifest

관측 자료도 보존 기간, 접근 권한, 무결성과 시간 기준이 있는 상태입니다.

## 3. 책임은 층이 아니라 작업으로 기록한다

“OS 아래는 공급자, 애플리케이션 위는 사용자” 같은 도식은 입문용으로 유용하지만 실제 책임을 충분히 설명하지 못합니다. 같은 database라도 작업별 책임이 다릅니다.

| 작업 | 공급자 가능 책임 | 소비자에게 남는 책임 |
|---|---|---|
| hardware 교체 | 물리 장치와 host 유지 | 서비스 영향과 복구 목표 확인 |
| database engine patch | patch 적용과 기본 호환성 | 적용 시점, extension·query 호환성, rollback 판단 |
| backup 생성 | schedule과 artifact 생성 | 보존 정책, 성공 감시, restore 가능성 검증 |
| encryption | 기능과 key service 제공 | key 선택, 권한, rotation, plaintext 경로 차단 |
| availability | zone·replica 기능 제공 | topology 선택, client retry, application readiness |
| monitoring | metric·log 수집 기능 제공 | 필요한 signal 선택, alert, response owner |
| scaling | instance 수 조정 기능 제공 | 올바른 metric, limit, stateful bottleneck, 비용 상한 |

따라서 responsibility matrix는 제품 component가 아니라 **운영 작업** 단위로 작성하는 편이 낫습니다.

## 4. Owner의 다섯 종류

하나의 자원에는 여러 owner가 있을 수 있습니다.

- **business owner**: 왜 필요한지와 종료 조건을 결정합니다.
- **configuration owner**: 원하는 설정과 변경 승인 책임을 가집니다.
- **runtime owner**: 정상 동작과 on-call을 담당합니다.
- **data owner**: 분류, 보존, export, deletion을 결정합니다.
- **cost owner**: 예산, allocation, anomaly와 cleanup을 담당합니다.

`owner=platform-team` 같은 한 필드만으로는 부족할 수 있습니다. 최소한 변경·장애·데이터·비용 owner를 구분해야 합니다.

## 5. 성공과 실패를 evidence로 바꾸기

### 주장: “두 개 zone에 배치했습니다”

필요한 근거:

- resource inventory의 실제 zone
- traffic distribution
- zone 하나를 제거했을 때 health와 사용자 영향
- stateful dependency의 배치
- capacity가 남은 zone에서 충분한지

### 주장: “자동 확장합니다”

필요한 근거:

- scale trigger와 threshold
- 측정 window
- minimum·maximum capacity
- provisioning latency
- load test 중 queue·latency·error·cost 변화
- scale-in 때 in-flight work 처리

### 주장: “백업됩니다”

필요한 근거:

- 최근 성공한 backup ID와 checksum
- backup이 포함하는 상태와 제외하는 상태
- 다른 환경에 restore한 결과
- restore 시간과 data loss window
- key·secret·configuration 재구성 경로

### 주장: “tenant가 격리됩니다”

필요한 근거:

- 모든 access path의 tenant context
- cross-tenant negative test
- cache·queue·background job·export 경계
- support/admin access audit
- backup·analytics·log에서의 tenant 분리

## 6. Cloud change의 최소 기록

cloud resource 변경은 다음 정보를 남겨야 합니다.

```text
change_id
actor_identity
requested_at
resource_scope
before_state
requested_state
authorization_decision
provider_operation_id
observed_final_state
verification_evidence
cost_effect
rollback_or_compensation
```

모든 시스템이 이 exact schema를 써야 하는 것은 아닙니다. 그러나 “누가 무엇을 왜 바꿨으며 실제로 어떤 상태가 됐는지”를 복원할 수 있어야 합니다.

## 7. 비동기 control plane의 함정

관리 API는 다음 상태를 만들 수 있습니다.

- 요청 timeout이지만 작업은 계속 진행됨
- 일부 resource 생성 뒤 dependency 생성 실패
- 삭제 요청 성공 뒤 실제 삭제 대기
- rollback 중 새 오류 발생
- 같은 요청 재시도로 중복 resource 생성
- console에는 최신 상태가 보이지만 audit export는 지연

따라서 provisioning workflow에도 `distributed-services`에서 다룬 불확실한 결과와 idempotency가 필요합니다.

```text
client request ID
+ provider operation ID
+ resource tag
+ desired/observed reconciliation
+ retry-safe create-or-read
```

## 8. Evidence의 한계

- control plane audit가 data plane의 모든 접근을 기록하지 않을 수 있습니다.
- metric 평균은 짧은 오류 burst를 숨길 수 있습니다.
- “backup completed”는 restore 가능성을 증명하지 않습니다.
- provider status page는 tenant별 영향과 다를 수 있습니다.
- 비용 estimate는 실제 data transfer와 request pattern을 놓칠 수 있습니다.
- local emulator는 실제 quota·latency·event ordering·IAM propagation을 재현하지 못합니다.

따라서 증거를 제시할 때는 반드시 **보장하는 것과 보장하지 않는 것**을 함께 기록합니다.

## 9. 검토 질문

1. 이 resource가 없어져도 다시 만들 수 있습니까?
2. 다시 만들 수 없다면 정본 상태는 어디에 있습니까?
3. create·update·delete가 중간 실패하면 무엇이 남습니까?
4. 변경 권한과 runtime data 권한이 같은 identity에 묶여 있습니까?
5. 공급자가 관리한다고 주장하는 작업을 소비자가 어떻게 검증합니까?
6. resource가 유휴 상태여도 비용이 발생합니까?
7. 서비스 종료 때 data·log·key·configuration을 회수하고 삭제할 수 있습니까?

## 연결 실습

[서비스 분류 실습](../exercises/01-service-classification/README.md)에서 각 사례의 state·owner·evidence를 작성합니다. 이후 모든 실습에서 같은 형식을 반복 사용합니다.
