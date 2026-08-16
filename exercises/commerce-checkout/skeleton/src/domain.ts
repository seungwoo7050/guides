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

export function buildOrderSnapshot(_products: ProductForCheckout[], _input: CheckoutBody): OrderSnapshot {
  throw new Error("TODO Stage 01: server 가격과 주문 snapshot을 계산하세요.");
}

export function transitionOrder(current: OrderStatus, _signal: OrderSignal): { next: OrderStatus; changed: boolean } {
  return { next: current, changed: false };
}

export function requireTransition(_current: OrderStatus, _signal: OrderSignal): OrderStatus {
  throw new Error("TODO Stage 05: 허용된 상태 전이만 반환하세요.");
}

export function isInventoryReleaseStatus(_status: OrderStatus): boolean {
  return false;
}

export function safeAdd(_left: number, _right: number): number {
  throw new Error("TODO Stage 01: safe integer 합을 구현하세요.");
}

export function safeMultiply(_amount: number, _quantity: number): number {
  throw new Error("TODO Stage 01: safe integer 곱을 구현하세요.");
}

export function assertSafeNonNegativeInteger(_value: number, _label: string): asserts _value is number {
  throw new Error("TODO Stage 01: 0 이상의 safe integer를 검사하세요.");
}
