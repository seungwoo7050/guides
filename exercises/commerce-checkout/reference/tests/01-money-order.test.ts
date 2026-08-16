import { describe, expect, it } from "vitest";

import { checkoutBodySchema } from "../src/contracts";
import {
  buildOrderSnapshot,
  safeAdd,
  safeMultiply,
  transitionOrder,
  type ProductForCheckout
} from "../src/domain";

const products: ProductForCheckout[] = [
  { id: "p1", sku: "SKU-1", name: "상품 1", priceMinor: 1200, currency: "KRW", stockOnHand: 5, active: true },
  { id: "p2", sku: "SKU-2", name: "상품 2", priceMinor: 2500, currency: "KRW", stockOnHand: 2, active: true }
];

describe("Stage 01 - Money와 주문 snapshot", () => {
  it("server 가격으로 line과 order total을 계산한다", () => {
    const snapshot = buildOrderSnapshot(products, {
      items: [{ productId: "p1", quantity: 2 }, { productId: "p2", quantity: 1 }]
    });
    expect(snapshot.subtotalMinor).toBe(4900);
    expect(snapshot.totalMinor).toBe(4900);
    expect(snapshot.lines[0]).toMatchObject({ sku: "SKU-1", unitPriceMinor: 1200, lineTotalMinor: 2400 });
  });

  it("현재 product가 바뀌어도 이미 만든 snapshot은 변하지 않는다", () => {
    const mutable = structuredClone(products);
    const snapshot = buildOrderSnapshot(mutable, { items: [{ productId: "p1", quantity: 1 }] });
    mutable[0]!.priceMinor = 999_999;
    mutable[0]!.name = "변경된 이름";
    expect(snapshot.lines[0]).toMatchObject({ unitPriceMinor: 1200, name: "상품 1" });
  });

  it("중복 상품·통화 혼합·재고 부족을 거부한다", () => {
    expect(() => buildOrderSnapshot(products, {
      items: [{ productId: "p1", quantity: 1 }, { productId: "p1", quantity: 1 }]
    })).toThrow(/두 번/);
    expect(() => buildOrderSnapshot([...products, { ...products[1]!, id: "usd", currency: "USD" }], {
      items: [{ productId: "p1", quantity: 1 }, { productId: "usd", quantity: 1 }]
    })).toThrow(/여러 통화/);
    expect(() => buildOrderSnapshot(products, { items: [{ productId: "p2", quantity: 3 }] })).toThrow(/재고/);
  });

  it("safe integer를 넘는 금액 연산을 거부한다", () => {
    expect(() => safeMultiply(Number.MAX_SAFE_INTEGER, 2)).toThrow(/safe integer/);
    expect(() => safeAdd(Number.MAX_SAFE_INTEGER, 1)).toThrow(/safe integer/);
  });

  it("client total과 알 수 없는 field를 schema에서 거부한다", () => {
    const parsed = checkoutBodySchema.safeParse({
      items: [{ productId: "p1", quantity: 1 }],
      totalMinor: 1
    });
    expect(parsed.success).toBe(false);
  });

  it("명시된 주문 상태 전이만 허용한다", () => {
    expect(transitionOrder("pending_payment", "payment.succeeded")).toEqual({ next: "paid", changed: true });
    expect(transitionOrder("cancel_pending", "payment.succeeded")).toEqual({ next: "paid", changed: true });
    expect(transitionOrder("refunded", "payment.succeeded")).toEqual({ next: "refunded", changed: false });
  });
});
