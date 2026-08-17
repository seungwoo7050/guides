# 선택형 종합 프로젝트: 커머스 체크아웃

이 선택형 종합 프로젝트는 상품 UI를 만드는 과제가 아닙니다. 작은 주문·결제 시스템에서 **주문 금액 스냅샷, 동시 재고 차감, 멱등성을 갖춘 명령, 외부 결제 어댑터, 서명된 웹훅, 취소·환불, 실패 후 상태 수렴**을 하나의 검증 가능한 시스템으로 결합합니다.

기본 과정의 `05-postgresql-kysely`, `06-security`, `08-testing`, `collaboration-board`를 완료했다면 바로 시작할 수 있습니다. WebSocket과 Canvas는 사용하지 않습니다.

기본 워크스페이스와 자동 검증은 [`commerce-checkout 실습`](../../exercises/commerce-checkout/README.md)에 있습니다.

## 완료 후 갖춰야 할 역량

프로젝트를 완료한 뒤에는 다음 내용을 설명하고 테스트로 증명할 수 있어야 합니다.

- 클라이언트의 장바구니 입력과 서버가 관리하는 가격·재고 기준의 차이
- 현재 상품 가격과 주문 항목 가격 스냅샷의 차이
- 상품 행 잠금, 일관된 잠금 순서, 초과 판매 방지
- 체크아웃 멱등성 키의 범위·요청 해시·응답 재현
- 주문 트랜잭션과 외부 결제 명령의 분리
- 결제 제공자 멱등성과 워커 재시도의 관계
- 원문 본문 HMAC 웹훅, 타임스탬프, 이벤트 중복 제거
- 주문·결제·재고 상태 전이를 하나의 트랜잭션으로 처리하는 경계
- 결제 취소와 환불의 차이, 늦게 도착한 이벤트 처리
- 도메인·API·실제 PostgreSQL·외부 HTTP 어댑터 테스트가 증명하는 범위

## 시스템 구조

```text
HTTP client
  ├─ POST /checkouts ──────────────┐
  ├─ POST /orders/:id/cancel ──────┤
  ├─ POST /orders/:id/refund ──────┤
  └─ GET  /orders/:id ─────────────┤
                                    ↓
Fastify application
  ├─ checkout / order service
  ├─ PostgreSQL repository
  ├─ durable payment command worker ─── HTTP ──> mock payment provider
  └─ signed webhook endpoint <────────── event ── mock payment provider
```

외부 결제 제공자는 `fixtures/mock-payment-provider/`에서 실행되는 독립 프로세스입니다. 학습자는 제공자 내부 구현을 변경하지 않고 애플리케이션 어댑터와 실패 처리 규칙을 구현합니다.

## 범위

포함하는 기능:

- 상품 초기 데이터와 목록 조회
- 체크아웃 요청
- 주문·주문 항목의 가격 스냅샷
- PostgreSQL에서의 재고 경쟁 처리
- 주문 조회
- 결제 생성·취소·환불 명령
- 명령 재시도와 제공자 멱등성
- 결제 성공·실패·취소·환불 웹훅
- 전체 주문 취소·환불과 재고 반환
- 도메인·DB·API·결제 제공자 어댑터 자동 테스트

제외하는 기능:

- 상품 관리 UI와 장바구니 화면
- 사용자 인증과 다중 상점
- 실제 카드·PG SDK와 PCI 범위
- 할인·쿠폰·세금·배송비
- 부분 취소와 부분 환불
- 배송과 반품 검수
- 메시지 브로커와 여러 서비스
- 스케줄러와 관리자용 대사 UI

제외된 기능을 임의로 추가하기보다 현재 범위의 불변식과 실패 주입 테스트를 먼저 통과시킵니다.

## HTTP 요구사항

### 상품 목록

```http
GET /products
```

공개 DTO에는 현재 가격과 판매 가능한 재고를 포함합니다. 교육용 단일 인스턴스에서만 재고 수치를 노출하며, 실제 제품에서는 별도의 노출 정책이 필요할 수 있습니다.

### 체크아웃

```http
POST /checkouts
Idempotency-Key: 7cf8...
Content-Type: application/json

{
  "items": [
    { "productId": "...", "quantity": 2 }
  ]
}
```

성공 응답:

```text
201 Created
```

응답은 `pending_payment` 상태의 주문과 주문 당시 금액을 반환합니다. 같은 키와 같은 본문을 다시 보내면 최초 상태 코드와 본문을 반환하고 `Idempotency-Replayed: true` 헤더를 추가합니다. 같은 키에 다른 본문을 사용하면 409를 반환합니다.

### 주문 조회

```http
GET /orders/:id
```

현재 상품 테이블이 아니라 주문 항목에 저장한 가격 스냅샷을 반환합니다.

### 결제 취소

```http
POST /orders/:id/cancel
Idempotency-Key: ...
```

`pending_payment` 상태에서 결제 생성 명령이 제공자에게 전달된 뒤에만 `cancel_pending`으로 전환하고 영속 취소 명령을 추가합니다. 아직 제공자 결제 식별자가 없다면 409 `payment_not_dispatched`를 반환합니다. 제공자의 `payment.canceled` 이벤트가 오기 전에는 `canceled`로 확정하지 않습니다.

### 환불

```http
POST /orders/:id/refund
Idempotency-Key: ...
```

`paid` 상태에서만 `refund_pending`으로 전환하고 영속 환불 명령을 추가합니다. 제공자의 `payment.refunded` 이벤트를 처리할 때 `refunded` 상태와 재고 반환을 함께 커밋합니다.

### 결제 명령 전송

```http
POST /internal/payment-commands/dispatch
```

교육용 단일 워커 엔드포인트입니다. 한 번에 처리할 최대 개수를 제한하고 각 명령의 결과를 반환합니다. 프로덕션 공개 API가 아니며 실제 운영에서는 스케줄러나 별도 워커 프로세스가 담당합니다.

### 웹훅

```http
POST /webhooks/payment
Content-Type: application/vnd.guide-payment+json
X-Payment-Timestamp: 1730000000
X-Payment-Signature: <hex hmac>
```

서명은 `timestamp + "." + raw_body`를 HMAC-SHA256으로 계산합니다. 기본 타임스탬프 허용 범위는 5분입니다.

## 데이터 기준

```text
products
  현재 가격·통화·재고

orders
  주문 상태·금액·재고 반환 여부

order_items
  SKU·이름·주문 당시 가격·수량 스냅샷

payments
  제공자 결제 식별자·상태·금액

idempotency_records
  명령 범위·키·요청 해시·최초 응답

payment_commands
  외부 결제 생성·취소·환불 작업과 재시도 상태

provider_events
  웹훅 중복 제거·페이로드 해시·판정 결과

inventory_movements
  재고 차감·반환 기록

order_events
  도메인 상태 전이와 무시된 이벤트의 감사 기록
```

현재 재고의 기준값은 `products.stock_on_hand`입니다. 재고 변동 기록은 현재 재고를 매번 다시 계산하기 위한 이벤트 소싱 로그가 아니라 트랜잭션이 수행한 변경의 증거입니다.

## 01단계: 금액과 주문 스냅샷

상세 요구사항: [`01-money-and-order.md`](../../exercises/commerce-checkout/specs/01-money-and-order.md)

완료 조건:

- 최소 화폐 단위 정수와 통화 코드
- 클라이언트가 보낸 총액을 신뢰하지 않음
- 주문 항목의 가격·SKU·이름 스냅샷
- 주문 항목 합계와 주문 총액 일치
- 잘못된 수량과 중복 상품 처리 정책
- 상품 가격 변경 후에도 과거 주문 금액 유지

## 02단계: 체크아웃과 재고 경쟁

상세 요구사항: [`02-checkout-inventory.md`](../../exercises/commerce-checkout/specs/02-checkout-inventory.md)

완료 조건:

- 상품 행을 항상 같은 순서로 잠금
- 실제 PostgreSQL 트랜잭션
- 재고 부족 시 전체 롤백
- 재고가 1개일 때 동시 요청 중 하나만 성공
- 재고 차감 기록과 현재 재고를 함께 변경
- 여러 상품 중간 실패 시 부분 주문이 남지 않음

## 03단계: 멱등성을 갖춘 체크아웃과 영속 결제 명령

상세 요구사항: [`03-idempotent-payment.md`](../../exercises/commerce-checkout/specs/03-idempotent-payment.md)

완료 조건:

- 체크아웃 키의 범위와 정규화한 요청 해시
- 같은 키·같은 본문의 결과 재현
- 같은 키·다른 본문에 409 반환
- 주문·재고·멱등성 결과·결제 생성 명령을 한 트랜잭션으로 처리
- 명령 선점과 제한된 재시도
- 제공자 멱등성 키로 프로세스 중단 구간 흡수

## 04단계: 결제 제공자 어댑터와 웹훅

상세 요구사항: [`04-payment-webhook.md`](../../exercises/commerce-checkout/specs/04-payment-webhook.md)

완료 조건:

- 실제 HTTP 모의 결제 제공자 어댑터
- 원문 본문 HMAC과 타임스탬프 허용 범위
- 이벤트 ID와 페이로드 해시를 사용한 중복 제거
- 중복 전달에도 도메인 효과가 한 번만 발생
- 같은 이벤트 ID와 다른 페이로드 거부
- 순서가 뒤바뀐 이벤트가 상태를 역행시키지 않음
- 웹훅 트랜잭션 실패 시 재시도를 유도하는 응답

## 05단계: 결제 취소와 환불

상세 요구사항: [`05-cancel-refund.md`](../../exercises/commerce-checkout/specs/05-cancel-refund.md)

완료 조건:

- 결제 대기 중 취소와 결제 완료 후 환불 구분
- 제공자 확정 전에는 대기 상태 유지
- 취소 요청과 결제 성공이 경쟁할 때 허용된 상태 전이 적용
- 최종 이벤트에서 재고를 정확히 한 번 반환
- 취소·환불 명령의 중복 요청이 안전함
- 늦은 이벤트가 최종 상태를 변경하지 않음

## 06단계: 품질과 종료

상세 요구사항: [`06-quality.md`](../../exercises/commerce-checkout/specs/06-quality.md)

완료 조건:

- 도메인 단위 테스트
- 실제 PostgreSQL 경쟁·롤백 테스트
- Fastify `inject` API 테스트
- 모의 결제 제공자 HTTP 어댑터 테스트
- 서명 웹훅 실패 테스트
- 명령 재시도·이벤트 중복·상태 역행의 잘못된 구현 검출
- 애플리케이션·데이터베이스 연결 풀·결제 제공자 하위 프로세스 정리

## 구현 순서

1. 금액, 주문 상태, 외부 DTO 스키마를 먼저 확정합니다.
2. 순수 금액 계산과 상태 전이를 단위 테스트로 작성합니다.
3. 마이그레이션과 Kysely 데이터베이스 타입을 작성합니다.
4. 체크아웃 트랜잭션과 실제 경쟁 테스트를 통과시킵니다.
5. 멱등성 레코드와 결제 명령 아웃박스를 같은 트랜잭션에 연결합니다.
6. 결제 제공자 포트와 HTTP 어댑터를 구현합니다.
7. 원문 본문을 사용하는 웹훅 라우트와 이벤트 트랜잭션을 연결합니다.
8. 취소·환불 명령과 재고 반환을 추가합니다.
9. 실패 주입과 전체 자원 정리를 검증합니다.

각 단계에서는 현재 단계의 테스트를 먼저 통과시킨 뒤 자신의 커밋을 남깁니다. 이후 단계의 참조 파일을 미리 복사하지 않습니다.

## 자동 검증

저장소 루트에서 워크스페이스를 생성합니다.

```sh
node exercises/commerce-checkout/checks/create-workspace.mjs
```

데이터베이스를 시작합니다.

```sh
POSTGRES_PORT=55433 docker compose \
  -p guide-commerce-checkout \
  -f exercises/commerce-checkout/compose.test.yml \
  up -d --wait

export DATABASE_URL=postgres://postgres:postgres@127.0.0.1:55433/commerce_dev
```

학습자 패키지를 설치하고 단계별 검증을 실행합니다.

```sh
corepack enable
pnpm --dir exercises/commerce-checkout/work install --ignore-workspace
pnpm --dir exercises/commerce-checkout/work migrate
node exercises/commerce-checkout/checks/verify-work.mjs 1
# ...
node exercises/commerce-checkout/checks/verify-work.mjs 6
```

검증기는 `skeleton/`에 포함된 기본 테스트 변경을 거부하고 `reference/` import와 심볼릭 링크를 차단한 뒤 해당 `verify:0N` 스크립트를 실행합니다.

완료 후 데이터베이스와 볼륨을 제거합니다.

```sh
docker compose \
  -p guide-commerce-checkout \
  -f exercises/commerce-checkout/compose.test.yml \
  down -v
```

## 흔한 오류

- 클라이언트가 보낸 총액을 저장합니다.
- 현재 상품 가격으로 과거 주문 금액을 다시 계산합니다.
- 재고 확인과 차감을 서로 다른 트랜잭션에서 처리합니다.
- 상품 행 잠금을 유지한 트랜잭션 안에서 외부 결제 제공자의 응답을 기다립니다.
- 멱등성 키를 메모리에만 저장합니다.
- 제공자 멱등성 식별자 없이 결제 명령을 재시도합니다.
- 웹훅 본문을 파싱한 뒤 객체를 대상으로 서명을 계산합니다.
- 중복 이벤트마다 재고를 반환합니다.
- 취소 요청 직후 제공자 확인 없이 주문을 `canceled`로 표시합니다.
- 늦은 성공 이벤트가 `refunded`나 `canceled` 상태를 `paid`로 되돌립니다.
- 기본 테스트를 삭제하거나 참조 구현을 import해 검증기를 통과합니다.

## 완료 기준

- 01–06단계의 기본 테스트를 변경하지 않고 모두 통과합니다.
- 실제 PostgreSQL에서 경쟁하는 체크아웃 요청과 트랜잭션 롤백을 증명합니다.
- 모의 결제 제공자의 HTTP 경계와 서명된 웹훅을 실행합니다.
- 같은 명령과 이벤트가 반복되어도 주문·결제·재고 효과가 한 번만 남습니다.
- 종료 후 서버, 연결 풀, 하위 프로세스가 남지 않습니다.

## 다음 단계

이 문서는 선택형 도메인 학습 경로의 종료점입니다. 실제 커머스 제품으로 확장한다면 인증, 부분 환불, 예약 만료, 배송·반품, 회계 원장, 결제 제공자 대사를 각각 별도의 요구사항으로 추가합니다. 기능을 늘리기 전에 현재 상태 머신과 실패 행렬이 그대로 유지되는지 먼저 확인합니다.
