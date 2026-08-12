# 통합 과제: 복구 가능한 예약 흐름

## 목표

앞선 문서와 실습의 계약을 하나의 프레임워크 독립적인 다중 서비스 흐름에 통합합니다. 과제는 예약 서비스, 재고 서비스, 읽기 모델과 메시지 전송기를 메모리 안에서 결정적으로 실행합니다. Kafka나 Spring 설정이 아니라 **실패 뒤 남는 업무 상태**가 핵심입니다.

## 시스템 경계

```text
client
  │ command(operationId, correlationId)
  ▼
reservation service ── outbox ── broker ── inventory service
       ▲                                      │
       └──────── inventory result ────────────┘
       │
       └── reservation status event ── query service
```

- 예약 서비스만 예약 상태를 변경합니다.
- 재고 서비스만 가용 수량을 변경합니다.
- 읽기 모델은 생성 sequence 1과 terminal sequence 2 계약을 검사한 뒤 예약 이벤트를 순서대로 투영합니다.
- 브로커 장애 중에는 Outbox가 복구 위치를 보존합니다.
- 같은 명령과 이벤트는 여러 번 들어올 수 있습니다.

## 반드시 만족할 계약

### 명령

- 같은 `operationId`와 같은 입력은 같은 예약을 반환합니다.
- 같은 `operationId`에 다른 수량을 사용하면 거절합니다.
- 대기 중인 예약 수가 상한에 도달하면 새 명령을 상태 변경 없이 거절합니다.
- 응답이 사라져도 `operationId`로 기존 결과를 조회할 수 있습니다.

### Outbox와 전달

- 예약과 첫 Outbox 이벤트는 하나의 로컬 변경으로 남습니다.
- 브로커 전송에 실패하면 Outbox를 발행 완료로 표시하지 않습니다.
- 전송 뒤 표시 전에 프로세스가 멈추면 같은 `eventId`가 다시 전송될 수 있습니다.
- 재고 서비스는 중복 이벤트를 한 번의 재고 효과로 수렴시킵니다.

### 결과와 읽기 모델

- 재고 결과의 중복 전달은 예약 상태 이벤트를 여러 개 만들지 않습니다.
- 상태 이벤트가 생성 이벤트보다 먼저 도착하면 버리지 않고 보류합니다.
- 누락된 앞 이벤트가 도착하면 연속된 순서까지 자동으로 적용합니다.
- 모든 이벤트는 같은 `correlationId`를 유지하고 `causationId`로 원인을 가리킵니다.
- Outbox가 비고 정본과 projection이 같더라도 둘 다 `PENDING`이면 수렴으로 판정하지 않습니다.
- 정본과 projection이 같은 `ACCEPTED` 또는 `REJECTED`일 때만 terminal 수렴입니다.

## 권장 구현 순서

`reference/` 전체가 하나의 numbering scope입니다. 아래 Implementation 번호는 권장
구현 순서이며 실제 과거 작성 순서를 뜻하지 않습니다.

1. README에서 각 서비스의 정본과 불변식을 표로 작성합니다.
2. skeleton의 첫 실패를 재현합니다.
3. 명령 멱등성과 대기 상태 상한을 먼저 고칩니다.
4. Outbox의 `send → mark` 순서와 중복 구독 처리를 고칩니다.
5. 읽기 모델의 보류·drain 규칙을 구현합니다.
6. 식별자 전파와 최종 수렴 조건을 검사합니다.
7. reference와 클래스 구조가 아니라 실패 행렬과 관찰 결과를 비교합니다.

| 구현 단계 | 파일·경계 | 책임 |
|---:|---|---|
| Implementation 1 | 공유 vocabulary | 서비스 사이의 상태·event·evidence와 terminal 상태를 고정합니다. |
| Implementation 2 | `OutboxRecord` | event, 생성 시각과 발행 lifecycle을 함께 소유합니다. |
| Implementation 3 | `ReservationService` | 예약 상태와 Reservation Outbox의 유일한 writer가 됩니다. |
| Implementation 3-1 | `submit` | operation 입력 claim과 예약·Outbox 생성을 한 경계로 묶습니다. |
| Implementation 3-2 | `applyInventoryResult` | 결과 identity와 terminal 전이를 검증합니다. |
| Implementation 3-3 | `pendingOutbox` | 아직 발행되지 않은 event snapshot만 노출합니다. |
| Implementation 3-4 | `oldestPendingOutboxAge` | 가장 오래된 미발행 record의 복구 지연을 계산합니다. |
| Implementation 4 | `InventoryService` | 재고 효과와 operation별 정본 결과를 소유합니다. |
| Implementation 4-1 | `handle` | event·operation identity를 claim하고 효과를 한 번만 적용합니다. |
| Implementation 4-2 | `findResultByOperation` | 재조정에 원래 operation의 정본 결과를 제공합니다. |
| Implementation 5 | `Broker` | 전달 시도와 broker failure만 모델링합니다. |
| Implementation 6 | `Publisher` | Reservation Outbox와 Broker 사이의 전달 순서를 소유합니다. |
| Implementation 6-1 | `publishPending` | `send` 성공 뒤에만 Outbox를 완료 표시합니다. |
| Implementation 7 | `QueryService` | schema·sequence별 projection과 보류 event를 소유합니다. |
| Implementation 7-1 | `consume` | event identity, schema와 sequence를 mutation 전에 검증합니다. |
| Implementation 7-2 | `rebuild` | envelope identity를 보존하며 projection을 처음부터 replay합니다. |
| Implementation 7-3 | `drain` | 연속된 다음 sequence만 보류 buffer에서 적용합니다. |
| Implementation 7-4 | `apply` | terminal contradiction을 막고 checkpoint를 전진시킵니다. |
| Implementation 8 | `SystemUnderTest` | 서비스 경계를 연결하고 end-to-end evidence를 수집합니다. |
| Implementation 8-1 | ingress `submit` | deadline과 correlation을 상태 변경 전에 검증합니다. |
| Implementation 8-2 | `reconcile` | 전달·inventory·재조정·projection을 복구 순서로 연결합니다. |
| Implementation 8-3 | `reconcilePending` | 정본 조회 결과와 다음 시도 시각을 기록합니다. |
| Implementation 8-4 | `converged` | Outbox가 비고 두 owner가 같은 terminal 상태인지 판정합니다. |
| Implementation 9 | `Dispatcher` | queue, running slot과 deadline의 자원 수명을 제한합니다. |
| Implementation 9-1 | `enqueue` | deadline과 queue 상한을 확인하고 task를 소유합니다. |
| Implementation 9-2 | `beginNext` | running slot을 예약하고 만료 task를 실행하지 않습니다. |
| Implementation 9-3 | `execute` | 원래 operation과 deadline을 ingress에 전달합니다. |
| Implementation 9-4 | `complete` | 정확히 한 실행의 slot을 반환합니다. |

먼저 `./scripts/new-workspace.sh reservation-flow`로 안전한 복사본을 만들고
`.workspace/reservation-flow`만 수정합니다. 정본 검사를 통과하고 서비스별 state owner와
실패 행렬을 설명한 뒤에만 `reference/`의 순서와 결과를 비교합니다.

## 완료 기준

- 명령 재시도·Outbox 재발행·소비 재전달 뒤에도 예약과 재고 효과가 한 번입니다.
- 순서가 뒤바뀐 상태 이벤트가 gap 해소 뒤 자동으로 적용되어 projection이 수렴합니다.
- 충돌 payload·모순 terminal transition·deadline 초과가 상태 변경 전에 거절되고 재조정 근거가 남습니다.
- queue·동시 실행 상한, 가장 오래된 Outbox age, 정본 조회 재시도와 전체 projection replay가 관찰 가능한 값으로 검증됩니다.
- `PENDING` 상태 일치는 완료가 아니며 같은 terminal 상태에서만 최종 수렴합니다.

## 자기 설명

- 예약·재고·읽기 모델의 정본 소유자를 분리해야 하는 이유는 무엇입니까?
- 전송 성공과 업무 수렴을 구분하려면 어떤 재조정 근거가 필요합니까?

## 검증

학습자 복사본은 다음 정본 명령으로 검사합니다.

```sh
./scripts/verify-java.sh .workspace/reservation-flow
```

workspace 검사가 통과하고 자기 설명을 마친 뒤에만 `reference/`의 실패 행렬과
권장 구현 순서를 비교합니다.

저장소 루트의 `./verify.sh`는 다음을 한 번에 확인합니다.

- 명령 재시도와 입력 충돌
- 과부하 거절 시 부정 불변식
- queue·동시 실행 상한과 deadline 만료
- 브로커 중단
- 전송 뒤 표시 전 crash
- 중복 이벤트
- 순서가 뒤바뀐 읽기 모델
- 수용과 거절 결과
- correlation·causation 연결
- 가장 오래된 pending Outbox age
- 같은 operation ID를 사용하는 정본 조회 재조정과 다음 시도 시각
- schema version을 보존한 역순 event envelope history의 projection rebuild와 격리 복구
- 모든 Outbox와 projection의 최종 수렴

reference는 모두 통과해야 하고 skeleton은 계약 위반으로 실패해야 합니다.
