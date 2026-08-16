import { createHash } from "node:crypto";
import type { Kysely } from "kysely";

import type { CheckoutBody, OrderDto, ProviderEvent } from "./contracts";
import type { Database } from "./db";
import type { PaymentCommand, PaymentCommandKind } from "./payment-provider";

export type IdempotentResult<T> = { statusCode: number; body: T; replayed: boolean };
export type ProductDto = {
  id: string;
  sku: string;
  name: string;
  price: { amountMinor: number; currency: string };
  stockOnHand: number;
  active: boolean;
};
export type ClaimedPaymentCommand = PaymentCommand & { attempts: number; claimToken: string };
export type ProviderEventApplyResult = {
  duplicate: boolean;
  outcome: string;
  orderId: string | null;
  orderStatus: string | null;
};

export class CommerceRepository {
  constructor(private readonly db: Kysely<Database>) {}

  async listProducts(): Promise<ProductDto[]> {
    const rows = await this.db.selectFrom("products").selectAll().orderBy("sku").execute();
    return rows.map((row) => ({
      id: row.id,
      sku: row.sku,
      name: row.name,
      price: { amountMinor: row.price_minor, currency: row.currency },
      stockOnHand: row.stock_on_hand,
      active: row.active
    }));
  }

  async getOrder(_orderId: string): Promise<OrderDto> {
    throw new Error("TODO Stage 02: order item snapshot과 payment를 조립하세요.");
  }

  async createCheckout(
    _idempotencyKey: string,
    _requestHash: string,
    _input: CheckoutBody,
    _now: Date
  ): Promise<IdempotentResult<OrderDto>> {
    throw new Error("TODO Stage 02–03: lock, snapshot, stock, idempotency와 create command transaction을 구현하세요.");
  }

  async requestOrderCommand(
    _orderId: string,
    _kind: Exclude<PaymentCommandKind, "create">,
    _idempotencyKey: string,
    _requestHash: string,
    _now: Date
  ): Promise<IdempotentResult<OrderDto>> {
    throw new Error("TODO Stage 05: cancel/refund pending transition과 command transaction을 구현하세요.");
  }

  async claimNextPaymentCommand(_now: Date, _staleBefore: Date): Promise<ClaimedPaymentCommand | null> {
    throw new Error("TODO Stage 03: command를 원자적으로 claim하세요.");
  }

  async completePaymentCommand(
    _command: ClaimedPaymentCommand,
    _providerOperationId: string,
    _providerPaymentId: string,
    _now: Date
  ): Promise<void> {
    throw new Error("TODO Stage 03: provider 성공 결과를 저장하세요.");
  }

  async failPaymentCommand(
    _command: ClaimedPaymentCommand,
    _message: string,
    _retryable: boolean,
    _maxAttempts: number,
    _nextAttemptAt: Date,
    _now: Date
  ): Promise<"pending" | "dead"> {
    throw new Error("TODO Stage 03: 제한된 retry와 dead 상태를 구현하세요.");
  }

  async applyProviderEvent(_event: ProviderEvent, _payloadHash: string, _now: Date): Promise<ProviderEventApplyResult> {
    throw new Error("TODO Stage 04–05: event dedupe, 상태 전이와 inventory release transaction을 구현하세요.");
  }

  async close(): Promise<void> {
    await this.db.destroy();
  }
}

export function hashCanonicalRequest(value: unknown): string {
  return createHash("sha256").update(stableStringify(value)).digest("hex");
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  const object = value as Record<string, unknown>;
  return `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(object[key])}`).join(",")}}`;
}
