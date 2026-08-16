import { ConflictError, InvalidRequestError, UnprocessableError } from "./errors";
import type { CheckoutBody, ProviderEventType } from "./contracts";

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

export function buildOrderSnapshot(products: ProductForCheckout[], input: CheckoutBody): OrderSnapshot {
  const requestedIds = input.items.map((item) => item.productId);
  if (new Set(requestedIds).size !== requestedIds.length) {
    throw new InvalidRequestError("같은 상품을 checkout items에 두 번 넣을 수 없습니다.");
  }

  const byId = new Map(products.map((product) => [product.id, product]));
  const lines = input.items.map((item): OrderLineSnapshot => {
    const product = byId.get(item.productId);
    if (!product) throw new UnprocessableError("product_unavailable", "판매 가능한 상품을 찾을 수 없습니다.", { productId: item.productId });
    if (!product.active) throw new UnprocessableError("product_inactive", "판매 중이 아닌 상품입니다.", { productId: item.productId });
    assertSafeNonNegativeInteger(product.priceMinor, "product price");
    if (!Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 20) {
      throw new InvalidRequestError("상품 수량은 1 이상 20 이하여야 합니다.");
    }
    if (product.stockOnHand < item.quantity) {
      throw new ConflictError("insufficient_stock", "재고가 부족합니다.", {
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
  if (currencies.size !== 1) throw new InvalidRequestError("한 주문에 여러 통화를 섞을 수 없습니다.");
  const currency = lines[0]?.currency;
  if (!currency) throw new InvalidRequestError("주문 항목이 없습니다.");
  const subtotalMinor = lines.reduce((sum, line) => safeAdd(sum, line.lineTotalMinor), 0);
  return { currency, subtotalMinor, totalMinor: subtotalMinor, lines };
}

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
    paid: {
      "refund.requested": "refund_pending"
    },
    refund_pending: {
      "payment.refunded": "refunded"
    }
  };
  const next = allowed[current]?.[signal];
  return next ? { next, changed: next !== current } : { next: current, changed: false };
}

export function requireTransition(current: OrderStatus, signal: OrderSignal): OrderStatus {
  const result = transitionOrder(current, signal);
  if (!result.changed) {
    throw new ConflictError("invalid_order_transition", `현재 주문 상태 ${current}에서 ${signal} 작업을 수행할 수 없습니다.`);
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
  if (!Number.isInteger(quantity) || quantity < 0) throw new InvalidRequestError("quantity는 0 이상의 정수여야 합니다.");
  const result = amount * quantity;
  assertSafeNonNegativeInteger(result, "amount product");
  return result;
}

export function assertSafeNonNegativeInteger(value: number, label: string): asserts value is number {
  if (!Number.isSafeInteger(value) || value < 0) {
    throw new InvalidRequestError(`${label}는 0 이상의 safe integer여야 합니다.`);
  }
}
