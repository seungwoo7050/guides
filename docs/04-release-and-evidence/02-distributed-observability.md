# 분산 관측성

## 목표

서비스별 로그를 많이 남기는 수준을 넘어, 한 업무 연산이 HTTP 요청·명령·이벤트·재처리를 거치는 과정을 연결하고 복구 지연과 불일치를 측정합니다.

## 문제

하나의 `request_id`만 모든 곳에 복사하면 다음을 구분하기 어렵습니다.

- 사용자가 시작한 업무 연산
- 동일 연산의 여러 HTTP 시도
- 연산이 발행한 여러 이벤트
- 이벤트를 원인으로 새로 만들어진 이벤트
- 같은 이벤트의 재전달
- aggregate의 현재 상태

관측 식별자가 부족하면 로그를 검색해도 어떤 효과가 중복되었는지, 어떤 작업이 아직 수렴하지 않았는지 알 수 없습니다. 반대로 사용자 ID나 operation ID를 metric label로 사용하면 cardinality가 폭발합니다.

## 계약

### 식별자의 역할을 구분합니다

| 식별자 | 역할 |
|---|---|
| `trace_id` | 동기 호출과 비동기 처리의 한 추적 흐름 |
| `request_id` | 개별 HTTP 요청 또는 호출 시도 |
| `operation_id` | 사용자가 시작한 한 번의 업무 의도 |
| `event_id` | 전달되는 한 이벤트 |
| `correlation_id` | 관련 이벤트와 명령을 묶는 업무 상관관계 |
| `causation_id` | 현재 이벤트를 직접 만든 이전 명령 또는 이벤트 |
| `aggregate_id` | 상태를 소유한 업무 대상 |

재시도는 새 request ID를 가질 수 있지만 operation ID는 유지합니다. 이벤트를 다시 전달할 때 event ID도 유지합니다. 후속 이벤트는 새 event ID를 가지며 causation ID로 원인을 연결합니다.
이미 upstream에서 시작된 흐름을 받는 ingress는 새 request ID와 별도로 기존
`trace_id`·`correlation_id`를 명시적으로 받습니다. 편의 기본값은 새 흐름에서만
사용하며 전달받은 업무 상관관계를 request ID로 덮어쓰지 않습니다.

### 구조화 로그에 상태 전이를 남깁니다

로그 메시지 문장만으로 검색하지 않습니다. 적어도 다음 필드를 구조화합니다.

```text
service
component
operation_id
event_id
correlation_id
causation_id
aggregate_id
state_before
state_after
outcome
attempt
elapsed_ms
```

비밀번호, token, 전체 개인정보와 payload 원문을 무조건 남기지 않습니다. 민감한 값과 고유 식별자 보존 기간을 정합니다.

### metric은 낮은 cardinality로 설계합니다

좋은 metric은 집계와 경보에 사용하고, 개별 식별자는 log나 trace에서 찾습니다.

예:

```text
outbox_pending_total{service,event_type}
outbox_oldest_age_seconds{service}
consumer_lag{group,topic,partition}
reconciliation_total{service,outcome}
idempotency_duplicate_total{operation_type}
dlq_messages{topic,error_class}
load_shed_total{service,reason}
```

다음 label은 일반적으로 피합니다.

```text
user_id
operation_id
event_id
reservation_id
raw_url
exception_message
```

### 수렴 상태를 관측합니다

CPU와 HTTP latency만으로 분산 업무가 정상인지 알 수 없습니다. 다음 업무 지표가 필요합니다.

- 가장 오래된 Outbox 대기 시간
- PENDING 상태의 개수와 최대 나이
- 재조정 성공·실패·수동 확인 건수
- 읽기 모델 lag와 checkpoint
- 중복 이벤트 감지 수
- DLQ backlog와 가장 오래된 메시지
- 원본과 projection의 불일치
- breaker open과 load shedding 비율

경보는 “문제가 생겼다”가 아니라 담당자가 취할 첫 행동과 runbook을 연결해야 합니다.

## 실패 조건

- 모든 단계에서 `request_id` 하나만 사용합니다.
- 재시도마다 operation ID를 바꿉니다.
- 후속 이벤트가 causation ID를 남기지 않습니다.
- operation ID를 metric label로 사용합니다.
- 로그에 업무 상태 전이와 결과가 없습니다.
- 프로세스 health만 보고 Outbox age와 projection lag를 보지 않습니다.
- 민감한 payload 전체를 디버깅 편의를 위해 저장합니다.

## 검증

한 명령이 다음 경로를 지나도록 합니다.

```text
HTTP request
→ command
→ Outbox event
→ consumer
→ projection event
```

각 단계의 record에서 trace·operation·correlation이 유지되고, 후속 이벤트의 causation이 이전 event ID를 가리키는지 확인합니다. metric registry는 고 cardinality label을 거절해야 합니다.

## 실습

[observability-correlation 실습](../../exercises/04-release-and-evidence/02-observability-correlation/README.md)은 식별자 전파와 metric label allowlist를 검사합니다.

## 완료 조건

- request, operation, event, causation과 aggregate ID를 구분합니다.
- HTTP와 event 경계를 넘어 상관관계를 유지합니다.
- 수렴 상태를 나타내는 업무 지표를 정의합니다.
- metric과 log·trace의 식별자 역할을 분리합니다.
