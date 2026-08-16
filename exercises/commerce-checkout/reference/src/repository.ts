import { createHash, randomUUID } from "node:crypto";
import { sql, type Kysely, type Transaction } from "kysely";

import type { CheckoutBody, OrderDto, ProviderEvent } from "./contracts";
import type { Database } from "./db";
import {
  buildOrderSnapshot,
  isInventoryReleaseStatus,
  requireTransition,
  transitionOrder,
  type OrderStatus,
  type ProductForCheckout
} from "./domain";
import { ConflictError, NotFoundError } from "./errors";
import type { PaymentCommand, PaymentCommandKind } from "./payment-provider";

export type IdempotentResult<T> = {
  statusCode: number;
  body: T;
  replayed: boolean;
};

export type ProductDto = {
  id: string;
  sku: string;
  name: string;
  price: { amountMinor: number; currency: string };
  stockOnHand: number;
  active: boolean;
};

export type ClaimedPaymentCommand = PaymentCommand & {
  attempts: number;
  claimToken: string;
};

export type ProviderEventApplyResult = {
  duplicate: boolean;
  outcome: string;
  orderId: string | null;
  orderStatus: string | null;
};

type Executor = Kysely<Database> | Transaction<Database>;

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

  async getOrder(orderId: string): Promise<OrderDto> {
    return this.loadOrder(this.db, orderId);
  }

  async createCheckout(
    idempotencyKey: string,
    requestHash: string,
    input: CheckoutBody,
    now: Date
  ): Promise<IdempotentResult<OrderDto>> {
    return this.db.transaction().execute(async (trx) => {
      return this.withIdempotency(trx, "checkout", idempotencyKey, requestHash, now, async () => {
        const sortedIds = [...input.items.map((item) => item.productId)].sort();
        const productRows = await trx
          .selectFrom("products")
          .selectAll()
          .where("id", "in", sortedIds)
          .orderBy("id")
          .forUpdate()
          .execute();

        const products: ProductForCheckout[] = productRows.map((row) => ({
          id: row.id,
          sku: row.sku,
          name: row.name,
          priceMinor: row.price_minor,
          currency: row.currency,
          stockOnHand: row.stock_on_hand,
          active: row.active
        }));
        const snapshot = buildOrderSnapshot(products, input);
        const orderId = `ord_${randomUUID()}`;
        const paymentId = `pmt_${randomUUID()}`;

        await trx.insertInto("orders").values({
          id: orderId,
          status: "pending_payment",
          currency: snapshot.currency,
          subtotal_minor: snapshot.subtotalMinor,
          total_minor: snapshot.totalMinor,
          inventory_released_at: null,
          created_at: now,
          updated_at: now
        }).execute();

        await trx.insertInto("order_items").values(snapshot.lines.map((line) => ({
          order_id: orderId,
          product_id: line.productId,
          sku: line.sku,
          product_name: line.name,
          unit_price_minor: line.unitPriceMinor,
          currency: line.currency,
          quantity: line.quantity,
          line_total_minor: line.lineTotalMinor
        }))).execute();

        for (const line of snapshot.lines) {
          const updated = await trx
            .updateTable("products")
            .set({
              stock_on_hand: sql<number>`stock_on_hand - ${line.quantity}`,
              updated_at: now
            })
            .where("id", "=", line.productId)
            .where("stock_on_hand", ">=", line.quantity)
            .returning("id")
            .executeTakeFirst();
          if (!updated) throw new ConflictError("insufficient_stock", "재고가 부족합니다.", { productId: line.productId });

          await trx.insertInto("inventory_movements").values({
            id: `imv_${randomUUID()}`,
            order_id: orderId,
            product_id: line.productId,
            kind: "reserve",
            quantity: line.quantity,
            created_at: now
          }).execute();
        }

        await trx.insertInto("payments").values({
          id: paymentId,
          order_id: orderId,
          provider_payment_id: null,
          status: "pending",
          amount_minor: snapshot.totalMinor,
          currency: snapshot.currency,
          created_at: now,
          updated_at: now
        }).execute();

        await trx.insertInto("payment_commands").values({
          id: `cmd_${randomUUID()}`,
          order_id: orderId,
          kind: "create",
          status: "pending",
          attempts: 0,
          provider_operation_id: null,
          last_error: null,
          next_attempt_at: now,
          claimed_at: null,
          claim_token: null,
          created_at: now,
          updated_at: now
        }).execute();

        await this.appendOrderEvent(trx, orderId, "checkout.created", {
          subtotalMinor: snapshot.subtotalMinor,
          currency: snapshot.currency
        }, now);

        const body = await this.loadOrder(trx, orderId);
        return { statusCode: 201, body };
      });
    });
  }

  async requestOrderCommand(
    orderId: string,
    kind: Exclude<PaymentCommandKind, "create">,
    idempotencyKey: string,
    requestHash: string,
    now: Date
  ): Promise<IdempotentResult<OrderDto>> {
    const signal = kind === "cancel" ? "cancel.requested" : "refund.requested";
    const nextPaymentStatus = kind === "cancel" ? "cancel_pending" : "refund_pending";
    return this.db.transaction().execute(async (trx) => {
      return this.withIdempotency(trx, `${kind}:${orderId}`, idempotencyKey, requestHash, now, async () => {
        const order = await trx.selectFrom("orders").selectAll().where("id", "=", orderId).forUpdate().executeTakeFirst();
        if (!order) throw new NotFoundError("주문을 찾을 수 없습니다.");
        const nextStatus = requireTransition(order.status as OrderStatus, signal);

        const payment = await trx.selectFrom("payments").selectAll().where("order_id", "=", orderId).forUpdate().executeTakeFirst();
        if (!payment) throw new NotFoundError("결제 상태를 찾을 수 없습니다.");
        if (!payment.provider_payment_id) {
          throw new ConflictError("payment_not_dispatched", "결제 생성 command가 아직 provider에 전달되지 않았습니다.");
        }

        await trx.updateTable("orders").set({ status: nextStatus, updated_at: now }).where("id", "=", orderId).execute();
        await trx.updateTable("payments").set({ status: nextPaymentStatus, updated_at: now }).where("id", "=", payment.id).execute();
        await trx.insertInto("payment_commands").values({
          id: `cmd_${randomUUID()}`,
          order_id: orderId,
          kind,
          status: "pending",
          attempts: 0,
          provider_operation_id: null,
          last_error: null,
          next_attempt_at: now,
          claimed_at: null,
          claim_token: null,
          created_at: now,
          updated_at: now
        }).execute();
        await this.appendOrderEvent(trx, orderId, signal, {}, now);
        const body = await this.loadOrder(trx, orderId);
        return { statusCode: 202, body };
      });
    });
  }

  async claimNextPaymentCommand(now: Date, staleBefore: Date): Promise<ClaimedPaymentCommand | null> {
    return this.db.transaction().execute(async (trx) => {
      await trx
        .updateTable("payment_commands")
        .set({ status: "pending", claimed_at: null, claim_token: null, next_attempt_at: now, updated_at: now })
        .where("status", "=", "processing")
        .where("claimed_at", "<", staleBefore)
        .execute();

      const row = await trx
        .selectFrom("payment_commands")
        .selectAll()
        .where("status", "=", "pending")
        .where("next_attempt_at", "<=", now)
        .orderBy("next_attempt_at")
        .orderBy("created_at")
        .forUpdate()
        .skipLocked()
        .limit(1)
        .executeTakeFirst();
      if (!row) return null;

      const claimToken = `claim_${randomUUID()}`;
      const updated = await trx
        .updateTable("payment_commands")
        .set({
          status: "processing",
          attempts: sql<number>`attempts + 1`,
          claimed_at: now,
          claim_token: claimToken,
          updated_at: now
        })
        .where("id", "=", row.id)
        .returningAll()
        .executeTakeFirstOrThrow();

      const payment = await trx
        .selectFrom("payments")
        .selectAll()
        .where("order_id", "=", updated.order_id)
        .executeTakeFirstOrThrow();

      return {
        id: updated.id,
        orderId: updated.order_id,
        kind: updated.kind as PaymentCommandKind,
        amountMinor: payment.amount_minor,
        currency: payment.currency,
        providerPaymentId: payment.provider_payment_id,
        attempts: updated.attempts,
        claimToken
      };
    });
  }

  async completePaymentCommand(
    command: ClaimedPaymentCommand,
    providerOperationId: string,
    providerPaymentId: string,
    now: Date
  ): Promise<void> {
    await this.db.transaction().execute(async (trx) => {
      const updated = await trx
        .updateTable("payment_commands")
        .set({
          status: "sent",
          provider_operation_id: providerOperationId,
          last_error: null,
          claimed_at: null,
          claim_token: null,
          updated_at: now
        })
        .where("id", "=", command.id)
        .where("status", "=", "processing")
        .where("claim_token", "=", command.claimToken)
        .returning("id")
        .executeTakeFirst();
      if (!updated) throw new ConflictError("command_not_claimed", "처리 중인 payment command가 아닙니다.");

      if (command.kind === "create") {
        const paymentUpdated = await trx
          .updateTable("payments")
          .set({ provider_payment_id: providerPaymentId, updated_at: now })
          .where("order_id", "=", command.orderId)
          .where((eb) => eb.or([
            eb("provider_payment_id", "is", null),
            eb("provider_payment_id", "=", providerPaymentId)
          ]))
          .returning("id")
          .executeTakeFirst();
        if (!paymentUpdated) {
          throw new ConflictError("provider_payment_conflict", "주문에 이미 다른 provider payment ID가 연결되어 있습니다.");
        }
      }
      await this.appendOrderEvent(trx, command.orderId, `payment_command.${command.kind}.sent`, {
        commandId: command.id,
        providerOperationId
      }, now);
    });
  }

  async failPaymentCommand(
    command: ClaimedPaymentCommand,
    message: string,
    retryable: boolean,
    maxAttempts: number,
    nextAttemptAt: Date,
    now: Date
  ): Promise<"pending" | "dead"> {
    const status = retryable && command.attempts < maxAttempts ? "pending" : "dead";
    const updated = await this.db.updateTable("payment_commands").set({
      status,
      last_error: sanitizeError(message),
      next_attempt_at: nextAttemptAt,
      claimed_at: null,
      claim_token: null,
      updated_at: now
    })
      .where("id", "=", command.id)
      .where("status", "=", "processing")
      .where("claim_token", "=", command.claimToken)
      .returning("id")
      .executeTakeFirst();
    if (!updated) throw new ConflictError("command_not_claimed", "현재 worker가 소유한 payment command가 아닙니다.");
    return status;
  }

  async applyProviderEvent(event: ProviderEvent, payloadHash: string, now: Date): Promise<ProviderEventApplyResult> {
    return this.db.transaction().execute(async (trx) => {
      const inserted = await trx.insertInto("provider_events").values({
        event_id: event.id,
        event_type: event.type,
        provider_payment_id: event.providerPaymentId,
        payload_hash: payloadHash,
        outcome: "processing",
        received_at: now
      }).onConflict((oc) => oc.column("event_id").doNothing()).returning("event_id").executeTakeFirst();

      let duplicate = false;
      if (!inserted) {
        const existing = await trx.selectFrom("provider_events").selectAll().where("event_id", "=", event.id).forUpdate().executeTakeFirstOrThrow();
        if (existing.payload_hash !== payloadHash) {
          throw new ConflictError("webhook_event_conflict", "같은 webhook event ID가 다른 payload로 재사용되었습니다.");
        }
        if (existing.outcome !== "unknown_payment") {
          return { duplicate: true, outcome: existing.outcome, orderId: null, orderStatus: null };
        }
        duplicate = true;
      }

      const payment = await trx
        .selectFrom("payments")
        .selectAll()
        .where("provider_payment_id", "=", event.providerPaymentId)
        .forUpdate()
        .executeTakeFirst();
      if (!payment) {
        await trx.updateTable("provider_events").set({ outcome: "unknown_payment" }).where("event_id", "=", event.id).execute();
        return { duplicate, outcome: "unknown_payment", orderId: null, orderStatus: null };
      }

      const order = await trx.selectFrom("orders").selectAll().where("id", "=", payment.order_id).forUpdate().executeTakeFirstOrThrow();
      const transition = transitionOrder(order.status as OrderStatus, event.type);
      if (!transition.changed) {
        await this.appendOrderEvent(trx, order.id, "provider_event.ignored", {
          providerEventId: event.id,
          signal: event.type,
          currentStatus: order.status
        }, now);
        await trx.updateTable("provider_events").set({ outcome: "ignored_invalid_transition" }).where("event_id", "=", event.id).execute();
        return { duplicate, outcome: "ignored_invalid_transition", orderId: order.id, orderStatus: order.status };
      }

      await trx.updateTable("orders").set({ status: transition.next, updated_at: now }).where("id", "=", order.id).execute();
      await trx.updateTable("payments").set({ status: paymentStatusForEvent(event.type), updated_at: now }).where("id", "=", payment.id).execute();
      if (isInventoryReleaseStatus(transition.next)) {
        await this.releaseInventory(trx, order.id, now);
      }
      await this.appendOrderEvent(trx, order.id, event.type, {
        providerEventId: event.id,
        providerPaymentId: event.providerPaymentId,
        previousStatus: order.status,
        nextStatus: transition.next
      }, now);
      await trx.updateTable("provider_events").set({ outcome: "applied" }).where("event_id", "=", event.id).execute();
      return { duplicate, outcome: "applied", orderId: order.id, orderStatus: transition.next };
    });
  }

  async close(): Promise<void> {
    await this.db.destroy();
  }

  private async withIdempotency<T>(
    trx: Transaction<Database>,
    scope: string,
    key: string,
    requestHash: string,
    now: Date,
    execute: () => Promise<{ statusCode: number; body: T }>
  ): Promise<IdempotentResult<T>> {
    const inserted = await trx.insertInto("idempotency_records").values({
      scope,
      key,
      request_hash: requestHash,
      state: "processing",
      response_status: null,
      response_body: null,
      created_at: now,
      updated_at: now
    }).onConflict((oc) => oc.columns(["scope", "key"]).doNothing()).returning("key").executeTakeFirst();

    if (!inserted) {
      const existing = await trx.selectFrom("idempotency_records").selectAll().where("scope", "=", scope).where("key", "=", key).executeTakeFirstOrThrow();
      if (existing.request_hash !== requestHash) {
        throw new ConflictError("idempotency_conflict", "같은 idempotency key가 다른 요청에 사용되었습니다.");
      }
      if (existing.state !== "completed" || existing.response_status === null || existing.response_body === null) {
        throw new ConflictError("request_in_progress", "같은 요청이 처리 중입니다.");
      }
      return {
        statusCode: existing.response_status,
        body: existing.response_body as T,
        replayed: true
      };
    }

    const result = await execute();
    await trx.updateTable("idempotency_records").set({
      state: "completed",
      response_status: result.statusCode,
      response_body: result.body,
      updated_at: now
    }).where("scope", "=", scope).where("key", "=", key).execute();
    return { ...result, replayed: false };
  }

  private async loadOrder(executor: Executor, orderId: string): Promise<OrderDto> {
    const order = await executor.selectFrom("orders").selectAll().where("id", "=", orderId).executeTakeFirst();
    if (!order) throw new NotFoundError("주문을 찾을 수 없습니다.");
    const [items, payment] = await Promise.all([
      executor.selectFrom("order_items").selectAll().where("order_id", "=", orderId).orderBy("product_id").execute(),
      executor.selectFrom("payments").selectAll().where("order_id", "=", orderId).executeTakeFirst()
    ]);
    if (!payment) throw new NotFoundError("결제 상태를 찾을 수 없습니다.");
    return {
      id: order.id,
      status: order.status,
      subtotal: { amountMinor: order.subtotal_minor, currency: order.currency },
      total: { amountMinor: order.total_minor, currency: order.currency },
      inventoryReleased: order.inventory_released_at !== null,
      payment: {
        id: payment.id,
        providerPaymentId: payment.provider_payment_id,
        status: payment.status
      },
      items: items.map((item) => ({
        productId: item.product_id,
        sku: item.sku,
        name: item.product_name,
        unitPrice: { amountMinor: item.unit_price_minor, currency: item.currency },
        quantity: item.quantity,
        lineTotal: { amountMinor: item.line_total_minor, currency: item.currency }
      })),
      createdAt: toIso(order.created_at),
      updatedAt: toIso(order.updated_at)
    };
  }

  private async releaseInventory(trx: Transaction<Database>, orderId: string, now: Date): Promise<boolean> {
    const marked = await trx.updateTable("orders").set({
      inventory_released_at: now,
      updated_at: now
    }).where("id", "=", orderId).where("inventory_released_at", "is", null).returning("id").executeTakeFirst();
    if (!marked) return false;

    const items = await trx.selectFrom("order_items").select(["product_id", "quantity"]).where("order_id", "=", orderId).orderBy("product_id").execute();
    for (const item of items) {
      await trx.updateTable("products").set({
        stock_on_hand: sql<number>`stock_on_hand + ${item.quantity}`,
        updated_at: now
      }).where("id", "=", item.product_id).execute();
      await trx.insertInto("inventory_movements").values({
        id: `imv_${randomUUID()}`,
        order_id: orderId,
        product_id: item.product_id,
        kind: "release",
        quantity: item.quantity,
        created_at: now
      }).execute();
    }
    return true;
  }

  private async appendOrderEvent(
    trx: Transaction<Database>,
    orderId: string,
    eventType: string,
    data: Record<string, unknown>,
    now: Date
  ): Promise<void> {
    await trx.insertInto("order_events").values({
      id: `oev_${randomUUID()}`,
      order_id: orderId,
      event_type: eventType,
      data,
      created_at: now
    }).execute();
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

function paymentStatusForEvent(type: ProviderEvent["type"]): string {
  switch (type) {
    case "payment.succeeded": return "succeeded";
    case "payment.failed": return "failed";
    case "payment.canceled": return "canceled";
    case "payment.refunded": return "refunded";
    default: throw new Error(`지원하지 않는 provider event입니다: ${String(type)}`);
  }
}

function sanitizeError(message: string): string {
  return message.replace(/[\r\n\t]+/g, " ").slice(0, 500);
}

function toIso(value: Date | string): string {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}
