# Failure injection 카탈로그

## Network

| Fault | 최소 state | 확인할 property |
|---|---|---|
| message drop | message ID·sender·receiver | retry와 safety |
| duplicate | same message ID 재전달 | handler idempotence |
| reorder | 두 message delivery 순서 변경 | term·index·version check |
| one-way partition | directed link state | heartbeat와 response 비대칭 |
| delay spike | virtual delivery time | timeout과 stale message |
| connection reset | in-flight request 상태 | UNKNOWN·retry |

## Process

| Fault | 주입 위치 | 확인할 property |
|---|---|---|
| crash before persist | state mutation 전 | promise 없음 |
| crash after persist before send | durable state 뒤 | retry response 일관성 |
| crash after send | receiver 처리 여부 다양 | duplicate·UNKNOWN |
| pause | timer·lease 중 | false suspicion·fencing |
| rapid restart | incarnation 증가 | stale worker 제거 |
| coordinated pause | majority timer 정지 | liveness assumption |

## Storage

| Fault | 확인할 property |
|---|---|
| append failure | success ack 없음 |
| flush delay | queue·timeout·backpressure |
| disk full | explicit rejection·no partial promise |
| checksum mismatch | corruption 격리 |
| snapshot interruption | 이전 generation 유지 |
| stale backup restore | epoch·fencing·repair |

## Client

| Fault | 확인할 property |
|---|---|
| response drop | retry effect 1회 |
| duplicate request | session deduplication |
| stale leader target | redirect·term handling |
| stale route epoch | owner fencing |
| client restart | session incarnation·request ID |

## Configuration

| Fault | 확인할 property |
|---|---|
| leader crash during membership | transition resume·quorum overlap |
| shard transfer coordinator crash | durable transfer state |
| rolling version skew | wire·log·snapshot compatibility |
| old feature activation | old node apply 거절 방지 |

## 실험 기록

```text
fault_id:
trigger condition:
injection mechanism:
actual-application evidence:
supported failure model:
expected safety:
expected recovery:
abort condition:
cleanup:
artifacts:
```
