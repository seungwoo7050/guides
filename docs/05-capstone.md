# 통합 과제: Reservation Flow

## 목표

앞선 문서의 개념을 여러 서비스 사이의 하나의 업무 흐름으로 연결합니다. 완성된 프레임워크 프로젝트를 조립하는 것이 아니라, 실패가 발생하는 위치와 최종 수렴 조건을 코드와 검사로 명시하는 것이 목적입니다.

## 시스템 경계

과제는 다음 역할을 가집니다.

```text
Reservation Service
- operation ID와 `PENDING/UNKNOWN/ACCEPTED/REJECTED` 예약 상태의 정본
- Outbox 기록
- 전체 진행 상태와 재조정

Inventory Service
- 품목별 가용 수량의 정본
- operation ID별 단일 차감

Event Broker
- 중복·지연·순서 역전을 주입할 수 있는 전달 경계

Query Service
- 예약 이벤트를 반영한 읽기 모델
- event ID 중복 제거와 aggregate sequence 보류

Dispatcher
- 동시 실행과 queue 한도
- deadline이 지난 작업의 거절
```

실제 네트워크 대신 결정적 in-memory 경계를 사용합니다. 이는 분산 실패를 없애기 위한 것이 아니라 같은 실패를 빠르고 반복 가능하게 재현하기 위한 선택입니다. 실제 Kafka와 Docker 설정은 선택 실습에서 따로 다룹니다.

## 구현 단계

### 1. 연산 식별자와 불확실한 응답

예약 명령은 `operation_id`를 받습니다. Reservation Service가 저장을 마친 직후 응답을 잃을 수 있습니다.

완료 조건:

- 같은 operation ID로 결과를 조회할 수 있습니다.
- 재시도해도 예약과 수량 차감은 하나입니다.
- 같은 ID와 다른 입력은 충돌로 거절합니다.

### 2. 서비스별 정본과 동기 판정

Inventory Service만 수량을 변경합니다. Reservation Service는 수량 테이블을 직접 고치지 않습니다.

완료 조건:

- 수량 부족이면 예약은 `REJECTED`입니다.
- 거절된 요청은 수량을 바꾸지 않습니다.
- inventory 응답을 확정할 수 없으면 예약은 `PENDING` 또는 `UNKNOWN`입니다.

### 3. Outbox와 중복 전달

예약 상태와 이벤트는 하나의 로컬 commit으로 기록됩니다. broker가 끊기면 Outbox는 대기합니다.

완료 조건:

- broker 장애 중에도 예약과 Outbox가 함께 남습니다.
- publish 뒤 표시 전에 중단해도 재전달이 단일 projection 효과를 만듭니다.
- Outbox의 가장 오래된 대기 시간을 계산할 수 있습니다.

`oldestPendingOutboxAge(now)`의 값은 발행되지 않은 레코드의 생성 시각에서
계산합니다. 모두 발행된 경우에는 값이 없으므로, `0`과 “대기 없음”을 혼동하지
않습니다.

### 4. 계약, 순서와 읽기 모델

예약 생성과 상태 변경 이벤트는 aggregate sequence를 가집니다. broker는 의도적으로 순서를 바꾸고 중복을 만듭니다.

완료 조건:

- 예약 생성은 sequence 1, 수락·거절 terminal 상태는 sequence 2로 고정하고 그 밖의 조합은 상태 변경 전에 거절합니다.
- sequence 2가 1보다 먼저 오면 보류합니다.
- 1이 도착한 뒤 1·2를 순서대로 적용합니다.
- 같은 event ID 재전달은 무시합니다.
- 지원하지 않는 schema version은 격리합니다.
- 전체 이벤트 재생으로 읽기 모델을 재구축할 수 있습니다.

`QueryService.rebuild(history)`는 schema version과 이벤트를 함께 담은
`EventEnvelope` 이력을 받습니다. 기존 projection·gap buffer·중복 기록을 비운 뒤
`consume(EventEnvelope)`와 같은 계약으로 전체 이력을 다시 적용하므로, 지원하지
않는 schema도 적용하지 않고 다시 격리해야 합니다. 역순 이력은 sequence gap에
보류했다가 앞 이벤트가 들어오면 연속 적용되어야 합니다.

### 5. 시간 예산과 부하 한도

Dispatcher는 실행·대기 한도를 가집니다.

완료 조건:

- queue가 정해진 크기를 넘지 않습니다.
- deadline이 지난 작업을 실행하지 않습니다.
- 과부하 거절은 상태 변경을 만들지 않습니다.
- 재시도는 같은 operation ID와 전체 deadline을 사용합니다.

실습의 결정적 `Dispatcher`는 enqueue, 실행 slot 획득, 실행, slot 반환을 분리합니다.
따라서 thread timing 없이도 queue 포화와 동시 실행 포화를 각각 재현하며, queue에서
기한이 지난 작업이 Reservation Service를 호출하지 않았다는 부정 불변식을 검사합니다.

### 6. 재조정과 근거

오래된 `PENDING` 예약은 Inventory Service의 operation 결과를 확인해 수렴합니다.

완료 조건:

- 재조정은 처음 operation ID를 사용합니다.
- 정본을 확인할 수 없으면 자동 성공 또는 자동 보상하지 않습니다.
- operation·event·correlation·causation ID가 단계 사이에서 유지됩니다.
- 장애 전·중·복구 후 업무 상태를 검사합니다.

정본 조회 자체가 실패하면 예약은 `UNKNOWN`으로 드러나며, `ReconciliationRecord`에
원래 operation ID와 다음 시도 시각을 남깁니다. 결과가 아직 없으면 `PENDING`을
유지합니다. 다음 재조정은 같은 operation ID로 다시 조회하고, 정본 결과가 생긴
경우에만 terminal 상태와 Outbox 이벤트를 만듭니다.

Outbox가 잠시 비고 정본과 projection이 모두 `PENDING`이라는 이유만으로 수렴했다고
판정하지 않습니다. 두 소유자의 상태가 같은 `ACCEPTED` 또는 `REJECTED`이고 남은
Outbox가 없을 때만 이 업무 흐름의 terminal 수렴입니다.

## 실패 행렬

| 실패 | 장애 중 기대 상태 | 복구 뒤 기대 상태 |
|---|---|---|
| 예약 저장 뒤 응답 유실 | 호출자는 결과를 확정할 수 없음 | 조회로 기존 결과 확인, 효과 1회 |
| inventory 거절 | 예약 REJECTED | 수량 변화 없음 |
| broker 중단 | Outbox PENDING | 복구 뒤 모두 발행 |
| publish 뒤 표시 전 중단 | 같은 이벤트 재전달 가능 | projection 효과 1회 |
| 상태 이벤트가 생성보다 먼저 도착 | 이벤트 보류 | 생성 뒤 순서대로 적용 |
| queue 포화 | 새 요청 OVERLOADED | 기존 실행·대기 작업은 정상 완료 |
| 재조정 중 정본 조회 실패 | UNKNOWN과 다음 시도 시각 기록 | 다음 재조정에서 정본 확인 뒤 수렴 |

## 실습

[reservation-flow capstone](../exercises/05-capstone/reservation-flow/README.md)은 단계별 검사를 제공합니다. 먼저 skeleton에서 실패 행렬이 어떻게 깨지는지 확인한 뒤, 한 단계씩 수정합니다.

## 완료 조건

다음 네 문장을 코드와 검사로 증명해야 합니다.

1. 응답과 전달은 여러 번 실패할 수 있지만 같은 업무 효과는 한 번만 남습니다.
2. 중간 상태는 숨지 않고 소유자·기한·다음 행동을 가집니다.
3. broker와 projection이 지연되어도 정본과 파생 상태는 복구 뒤 수렴합니다.
4. 과부하와 cleanup 실패가 원래 업무 결과와 검증 근거를 왜곡하지 않습니다.
