import { describe, expect, it } from "vitest";
import { buildOrderSnapshot, safeAdd, transitionOrder } from "../src/domain.js";

// [Implementation 12] Verify deterministic money, order, webhook, and transaction guarantees at the smallest layer that owns each invariant.
describe("order domain", () => {
  it("snapshots minor-unit prices without floating-point arithmetic", () => {
    const snapshot = buildOrderSnapshot([
      { id: "p1", sku: "P-1", name: "Product", priceMinor: 1299, currency: "USD", stockOnHand: 3, active: true }
    ], { items: [{ productId: "p1", quantity: 2 }] });
    expect(snapshot.totalMinor).toBe(2598);
    expect(snapshot.lines[0]?.lineTotalMinor).toBe(2598);
  });

  it("rejects unsafe sums", () => {
    expect(() => safeAdd(Number.MAX_SAFE_INTEGER, 1)).toThrow(/safe integer/);
  });

  it("accepts only declared lifecycle transitions", () => {
    expect(transitionOrder("pending_payment", "payment.succeeded")).toEqual({ next: "paid", changed: true });
    expect(transitionOrder("paid", "payment.failed")).toEqual({ next: "paid", changed: false });
    expect(transitionOrder("paid", "refund.requested")).toEqual({ next: "refund_pending", changed: true });
  });
});
