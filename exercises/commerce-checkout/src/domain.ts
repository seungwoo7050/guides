import type { CheckoutBody, ProviderEventType } from "./contracts.js";
import { ConflictError, InvalidRequestError, UnprocessableError } from "./errors.js";

export type ProductForCheckout = {
  id: string;
  sku: string;
  name: string;
  priceMinor: number;
  currency: string;
  stockOnHand: number;
  active: boolean;
};
export type OrderLineSnapshot = {
  productId: string;
  sku: string;
  name: string;
  unitPriceMinor: number;
  currency: string;
  quantity: number;
  lineTotalMinor: number;
};
export type OrderSnapshot = {
  currency: string;
  subtotalMinor: number;
  totalMinor: number;
  lines: OrderLineSnapshot[];
};
export type OrderStatus =
  | "pending_payment"
  | "cancel_pending"
  | "paid"
  | "refund_pending"
  | "payment_failed"
  | "canceled"
  | "refunded";
export type OrderSignal = ProviderEventType | "cancel.requested" | "refund.requested";

// [Implementation 3] Snapshot product identity, price, currency, and quantity as safe minor-unit integers before an order can reserve inventory.
export function buildOrderSnapshot(products: ProductForCheckout[], input: CheckoutBody): OrderSnapshot {
  const requestedIds = input.items.map((item) => item.productId);
  if (new Set(requestedIds).size !== requestedIds.length) {
    throw new InvalidRequestError("A product cannot appear more than once in checkout items.");
  }

  const byId = new Map(products.map((product) => [product.id, product]));
  const lines = input.items.map((item): OrderLineSnapshot => {
    const product = byId.get(item.productId);
    if (!product) {
      throw new UnprocessableError("product_unavailable", "The requested product is unavailable.", { productId: item.productId });
    }
    if (!product.active) {
      throw new UnprocessableError("product_inactive", "The requested product is inactive.", { productId: item.productId });
    }
    assertSafeNonNegativeInteger(product.priceMinor, "product price");
    if (product.stockOnHand < item.quantity) {
      throw new ConflictError("insufficient_stock", "Insufficient stock.", {
        productId: product.id,
        available: product.stockOnHand,
        requested: item.quantity
      });
    }
    const lineTotalMinor = safeMultiply(product.priceMinor, item.quantity);
    return {
      productId: product.id,
      sku: product.sku,
      name: product.name,
      unitPriceMinor: product.priceMinor,
      currency: product.currency,
      quantity: item.quantity,
      lineTotalMinor
    };
  });

  const currencies = new Set(lines.map((line) => line.currency));
  if (currencies.size !== 1) throw new InvalidRequestError("An order cannot contain multiple currencies.");
  const currency = lines[0]?.currency;
  if (!currency) throw new InvalidRequestError("The order contains no items.");
  const subtotalMinor = lines.reduce((sum, line) => safeAdd(sum, line.lineTotalMinor), 0);
  return { currency, subtotalMinor, totalMinor: subtotalMinor, lines };
}

// [Implementation 3-1] Constrain cancellation, payment, and refund signals with an explicit order-state transition table instead of route-local conditionals.
export function transitionOrder(current: OrderStatus, signal: OrderSignal): { next: OrderStatus; changed: boolean } {
  const allowed: Partial<Record<OrderStatus, Partial<Record<OrderSignal, OrderStatus>>>> = {
    pending_payment: {
      "payment.succeeded": "paid",
      "payment.failed": "payment_failed",
      "cancel.requested": "cancel_pending"
    },
    cancel_pending: {
      "payment.canceled": "canceled",
      "payment.succeeded": "paid",
      "payment.failed": "payment_failed"
    },
    paid: { "refund.requested": "refund_pending" },
    refund_pending: { "payment.refunded": "refunded" }
  };
  const next = allowed[current]?.[signal];
  return next ? { next, changed: next !== current } : { next: current, changed: false };
}

export function requireTransition(current: OrderStatus, signal: OrderSignal): OrderStatus {
  const result = transitionOrder(current, signal);
  if (!result.changed) {
    throw new ConflictError("invalid_order_transition", `Signal ${signal} is not valid while the order is ${current}.`);
  }
  return result.next;
}

export function isInventoryReleaseStatus(status: OrderStatus): boolean {
  return status === "payment_failed" || status === "canceled" || status === "refunded";
}

export function safeAdd(left: number, right: number): number {
  assertSafeNonNegativeInteger(left, "left amount");
  assertSafeNonNegativeInteger(right, "right amount");
  const result = left + right;
  assertSafeNonNegativeInteger(result, "amount sum");
  return result;
}

export function safeMultiply(amount: number, quantity: number): number {
  assertSafeNonNegativeInteger(amount, "amount");
  if (!Number.isInteger(quantity) || quantity < 0) {
    throw new InvalidRequestError("Quantity must be a non-negative integer.");
  }
  const result = amount * quantity;
  assertSafeNonNegativeInteger(result, "amount product");
  return result;
}

export function assertSafeNonNegativeInteger(value: number, label: string): asserts value is number {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new InvalidRequestError(`${label} must be a non-negative safe integer.`);
  }
}
