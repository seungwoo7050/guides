# 관측성과 경보

관측성은 로그 수집기를 설치하는 일이 아닙니다. 외부 증상과 내부 상태를 연결해 다음 질문에 답할 수 있는 능력입니다.

```text
무엇이 실패했는가?
언제 시작됐는가?
누가 영향을 받는가?
어느 release와 구성 변경 뒤 발생했는가?
어떤 의존 경계까지 성공했는가?
지금 완화가 필요한가, 분석을 계속해도 되는가?
복구됐다는 증거는 무엇인가?
```

대응 실습은 [`exercises/14-observability`](../exercises/14-observability/)입니다.

## 1. 관측 신호

### 로그

개별 event의 구체적인 문맥을 기록합니다.

```json
{
  "timestamp": "2026-08-07T12:00:00Z",
  "level": "error",
  "service": "app",
  "release": "2026-08-07.1",
  "request_id": "req-...",
  "event": "database_query_failed",
  "error_class": "timeout",
  "duration_ms": 2000
}
```

### 지표

시간에 따른 수치와 분포를 집계합니다.

```text
http_requests_total
http_request_duration_seconds
http_errors_total
db_pool_in_use
container_restarts_total
backup_age_seconds
certificate_expiry_seconds
```

### Trace

하나의 요청이 gateway, application, database와 외부 API를 거치는 구간을 연결합니다. 단일 호스트 작은 서비스에서도 느린 요청과 의존 경계를 찾는 데 유용할 수 있습니다.

### Profile

CPU, memory allocation과 lock contention처럼 process 내부 자원 사용을 분석합니다. 상시 사용 여부와 보존 비용을 정합니다.

모든 신호를 처음부터 도입할 필요는 없습니다. 최소 기준선은 구조화 로그, 핵심 지표, 외부 상태 검사와 actionable alert입니다.

## 2. 사용자 관점과 내부 관점

### 외부 관점

호스트 밖에서 다음을 확인합니다.

- DNS 해석
- TCP 연결
- TLS hostname·chain·expiry
- HTTP 상태와 응답 계약
- 실제 사용자 경로 latency

### 내부 관점

- container·process 상태
- CPU·memory·disk·inode
- restart count
- DB connection·query 오류
- queue·worker lag
- backup·certificate renewal job

외부 실패와 내부 신호를 함께 봐야 합니다.

```text
외부 5xx 증가 + app DB timeout 증가
→ database 경계 조사

외부 TLS 실패 + app·gateway 정상
→ certificate·DNS 경계 조사
```

## 3. 상태 검사 다시 구분하기

07장에서 다룬 상태를 운영 신호에 연결합니다.

### Liveness

process가 회복 불가능하게 멈췄는지 판단합니다. 외부 dependency 실패를 무조건 포함하면 restart storm을 만들 수 있습니다.

### Readiness

현재 새 요청을 받을 준비가 됐는지 판단합니다. migration, connection pool과 필수 내부 자원 상태를 포함할 수 있습니다.

### Smoke 또는 synthetic check

호스트 밖에서 실제 사용자 경로를 검사합니다. 공개 DNS와 TLS를 통과해야 합니다.

세 검사의 실패 의미와 자동 반응을 다르게 설정합니다.

## 4. 구조화 로그 계약

문자열 문장만 남기면 검색과 집계가 어렵습니다. 최소 필드를 정합니다.

| 필드 | 의미 |
|---|---|
| `timestamp` | timezone이 명확한 event 시각 |
| `level` | debug·info·warn·error |
| `service` | event 소유 component |
| `environment` | production·staging |
| `release` | 실행 image와 연결되는 release ID |
| `event` | 안정된 기계 판독 event 이름 |
| `request_id` | 한 HTTP 요청 안의 상관관계 |
| `trace_id` | 여러 서비스 구간의 상관관계 |
| `duration_ms` | 작업 시간, 있을 때 |
| `error_class` | timeout·validation·dependency 등 안정된 분류 |

로그 message는 사람이 읽는 설명이고, `event`와 분류 필드는 query 계약입니다.

## 5. Correlation ID

gateway에서 들어온 request ID를 검증하거나 새로 만들고 application에 전달합니다. 외부 사용자가 매우 긴 값이나 제어 문자를 주입하지 못하도록 형식과 길이를 제한합니다.

구분:

- request ID: 한 HTTP 요청
- trace ID: 여러 span으로 이어지는 분산 요청
- operation ID: 재시도 사이에서도 같은 업무 작업
- user ID: 사용자 주체, 개인정보 정책 적용
- release ID: 배포 단위

모든 것을 request ID 하나로 대신하지 않습니다.

## 6. 민감 정보와 cardinality

로그에 secret, token, password와 전체 request body를 남기지 않습니다.

지표 label에는 값 종류가 무한히 늘어나는 항목을 넣지 않습니다.

나쁜 예:

```text
http_requests_total{user_id="...",request_id="...",url="/notes/12345"}
```

좋은 예:

```text
http_requests_total{method="GET",route="/notes/:id",status_class="2xx"}
```

높은 cardinality는 metric 저장 비용과 query 성능을 급격히 악화시킵니다. 구체적인 ID는 로그나 trace에서 찾습니다.

## 7. 핵심 지표

### 요청

- 요청 수
- 4xx·5xx 비율
- latency 분포
- active request
- timeout

평균만 보지 않고 percentile 또는 histogram을 사용합니다. 소수의 매우 느린 요청이 평균에 가려질 수 있습니다.

### 자원

- CPU usage와 throttling
- memory working set과 OOM
- disk byte·inode 사용률
- network error
- process·PID 수

### 데이터베이스

- connection pool 사용률
- connection 실패
- query latency
- lock wait와 deadlock
- storage 증가
- backup 성공과 age

### 배포·운영

- 현재 release
- 마지막 성공 배포
- container restart
- certificate expiry
- backup restore drill age
- alert delivery 실패

### 업무 지표

서비스가 실제로 제공해야 하는 결과를 나타냅니다.

- 생성 성공 수
- 처리 대기량
- 결제 성공률
- 동기화 지연

업무 지표가 0이 된 것이 정상적인 비수기인지 장애인지 문맥을 함께 봅니다.

## 8. SLI와 SLO

SLI는 실제 측정치이고 SLO는 목표입니다.

예:

```text
SLI: 외부 synthetic check의 성공 비율
SLO: 최근 30일 99.5% 이상
```

좋은 SLI는 사용자 경험과 가깝습니다. container running 비율은 운영 지표지만 사용자가 기능을 쓸 수 있는지를 직접 나타내지 않을 수 있습니다.

초기 서비스의 최소 SLI:

- 핵심 경로 성공률
- 핵심 경로 latency
- 데이터 freshness 또는 job lag
- 복원 시험 성공과 소요 시간

## 9. 경보 원칙

좋은 경보는 다음을 만족합니다.

- 실제 사용자 영향 또는 임박한 자원 고갈을 나타냅니다.
- 수신자가 취할 수 있는 행동이 있습니다.
- 긴급도와 대응 시간이 명확합니다.
- 관련 dashboard와 runbook이 연결됩니다.
- 일시적인 한 번의 spike보다 지속 조건을 고려합니다.

증상 기반 경보를 우선합니다.

```text
좋음: 외부 핵심 경로 성공률이 10분간 목표 이하
보조: database CPU 90%
```

CPU가 높아도 사용자가 영향을 받지 않을 수 있고, CPU가 낮아도 deadlock으로 모든 요청이 실패할 수 있습니다.

## 10. 경보 수준

한 가지 예:

### Page

즉시 사람이 대응해야 합니다.

- 핵심 사용자 경로 지속 실패
- 데이터 손실 진행 가능성
- 인증서 임박 만료
- disk 고갈 임박
- backup과 복구 원본 동시 위험

### Ticket

근무 시간 안에 처리할 수 있습니다.

- base image 업데이트 필요
- disk 증가 추세
- restore drill 기한 초과
- 비긴급 경고율 상승

### Dashboard only

추세와 분석에는 필요하지만 매번 사람을 호출하지 않습니다.

경보가 너무 자주 잘못 울리면 운영자는 무시하게 됩니다. 알림을 끄기 전에 조건과 사용자 신호를 개선합니다.

## 11. 경보에 포함할 문맥

```text
무슨 환경·서비스인가?
언제 시작됐는가?
현재 값과 임계값은 무엇인가?
어떤 사용자가 영향을 받는가?
최근 배포는 무엇인가?
어디서 로그·지표를 보는가?
첫 안전 조치는 무엇인가?
어떤 runbook을 따르는가?
```

경보 message에 secret이나 전체 개인정보를 넣지 않습니다.

## 12. Dashboard

Dashboard는 모든 지표를 한 화면에 넣는 곳이 아닙니다.

권장 계층:

### 서비스 개요

- 사용자 성공률과 latency
- 현재 release
- 주요 dependency
- 활성 incident

### 자원

- host CPU·memory·disk
- container restart·limit
- DB pool과 storage

### 배포 비교

- release marker
- 배포 전후 error·latency
- rollback event

### 복구 준비

- backup age
- restore drill 결과
- certificate expiry
- base image age

## 13. 로그 전달과 장애

container stdout만 host 로컬에 두면 host 손실과 함께 사고 증거도 사라질 수 있습니다. 필요에 따라 외부 로그 목적지로 전달합니다.

결정할 것:

- 전송 실패 때 application을 막을 것인가?
- local buffer 크기와 disk 한계
- backpressure와 drop 정책
- TLS와 인증
- 보존 기간
- 개인정보 삭제 요청
- 목적지 장애 경보

로그 수집 장애가 production 전체를 멈추게 할지 신중히 결정합니다. 일반적으로 business request는 계속 처리하되 손실을 탐지하고 제한된 local buffer를 둡니다.

## 14. Trace 도입 경계

여러 service·queue·external API를 거치면 trace 가치가 커집니다. 단일 service에서도 느린 DB query를 찾을 수 있습니다.

도입 시 확인:

- sampling 정책
- trace context 신뢰 경계
- 개인정보·secret attribute 금지
- exporter 실패 처리
- collector의 resource limit
- logs·metrics와 release ID 연결

관측 시스템이 장애를 증폭하지 않도록 비동기 전송, 제한된 queue와 drop 정책을 둡니다.

## 15. 배포와 관측성

배포 workflow는 다음 marker를 남깁니다.

```text
release_id
image digest
source revision
start·complete·rollback timestamp
```

문제가 발생하면 배포 전후 같은 시간 창을 비교합니다. “최근 배포가 있었으니 원인이다”라고 단정하지 않고 상관관계를 증거로 확인합니다.

## 16. 관측 시스템 자체 검사

- 외부 probe가 실행되고 있는가?
- metric scrape가 끊기지 않았는가?
- log pipeline이 지연되지 않았는가?
- alert rule evaluator가 정상인가?
- 알림 채널로 테스트 message가 도착하는가?
- 시간 동기화가 정상인가?

아무 경보가 없다는 사실이 정상 상태를 의미하지 않을 수 있습니다.

## 17. 실습

[`exercises/14-observability`](../exercises/14-observability/)은 표준 라이브러리 HTTP service를 실행하고 다음을 검증합니다.

- `/healthz`와 `/readyz`의 의미가 다름
- 요청마다 제한된 request ID 생성·전달
- JSON log에 service·release·event·duration 포함
- token·cookie가 로그에 남지 않음
- `/metrics`에서 요청·오류·latency 집계
- path parameter 대신 안정된 route label 사용
- dependency 실패가 readiness와 사용자 응답에 다르게 반영됨
- release 변경 뒤 로그와 metric에서 새 release 식별

도구 설치보다 신호의 의미와 schema를 먼저 고정합니다.

## 18. 공식 확인 자료

- OpenTelemetry signals: <https://opentelemetry.io/docs/concepts/signals/>
- Prometheus metric and label practices: <https://prometheus.io/docs/practices/naming/>
- Prometheus alerting philosophy: <https://prometheus.io/docs/practices/alerting/>
- Docker logging drivers: <https://docs.docker.com/engine/logging/configure/>

다음 장에서는 관측으로 발견한 장애가 데이터 손실로 이어졌을 때, 실제로 복원 가능한 backup과 재해 복구 절차를 만듭니다.
