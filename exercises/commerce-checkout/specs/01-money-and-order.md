# Stage 01: Money와 주문 snapshot

## 목표

client가 보내는 것은 상품 ID와 수량뿐입니다. server는 현재 product를 읽어 금액을 계산하고 주문 당시의 SKU·이름·단가를 snapshot합니다.

## 구현 계약

- `amountMinor`는 0 이상의 safe integer입니다.
- `currency`는 대문자 3자리 코드입니다.
- quantity는 1–20입니다.
- 한 checkout에서 같은 product ID를 두 번 보내면 거부합니다.
- 한 주문의 모든 item은 같은 currency입니다.
- line total과 order total의 모든 곱·합을 safe integer로 검사합니다.
- client total 필드는 schema에 존재하지 않습니다.
- order DTO는 product 현재 값을 다시 읽지 않고 snapshot을 반환할 수 있습니다.

## 순수 함수

최소한 다음 책임을 pure domain으로 분리합니다.

```text
normalize checkout items
calculate order snapshot
validate order transition
```

DB·Fastify·environment variable을 import하지 않습니다.

## 검증 시나리오

- 두 item 합계 계산
- quantity 0·21 거부
- 같은 product 중복 거부
- 비활성 product 거부
- currency 혼합 거부
- safe integer overflow 거부
- 상품 가격을 바꿔도 이미 만든 snapshot 값 불변
- 허용되지 않은 order transition 거부

## 완료 기준

```sh
node exercises/commerce-checkout/checks/verify-work.mjs 1
```

baseline `tests/01-money-order.test.ts`가 통과해야 합니다.
