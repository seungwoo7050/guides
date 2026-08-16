import type { Kysely } from "kysely";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { ProviderEvent } from "../src/contracts";
import type { Database } from "../src/db";
import {
  FakePaymentProvider,
  buildTestApp,
  createHarness,
  createTestDatabase,
  injectWebhook,
  key,
  resetDatabase,
  seedProduct
} from "./helpers";

let db: Kysely<Database>;
const apps: Array<Awaited<ReturnType<typeof buildTestApp>>> = [];

beforeAll(async () => { db = await createTestDatabase(); });
afterAll(async () => { await db.destroy(); });
beforeEach(async () => { await resetDatabase(db); });
afterEach(async () => { while (apps.length) await apps.pop()!.close(); });

async function createDispatchedOrder(stockOnHand = 1) {
  const productId = await seedProduct(db, { stockOnHand });
  const provider = new FakePaymentProvider();
  const harness = createHarness(db, provider);
  const checkout = await harness.service.checkout(key(), { items: [{ productId, quantity: 1 }] });
  await harness.service.dispatchPending(1);
  return { productId, checkout, ...harness };
}

async function send(app: Awaited<ReturnType<typeof buildTestApp>>, type: ProviderEvent["type"], providerPaymentId: string, id = key("event")) {
  return injectWebhook(app, { id, type, providerPaymentId, occurredAt: new Date().toISOString() });
}

describe("Stage 05 - Cancel과 refund", () => {
  it("cancel request는 pending이고 provider canceled event에서 재고를 한 번 반환한다", async () => {
    const { productId, checkout, service } = await createDispatchedOrder();
    const app = await buildTestApp(service);
    apps.push(app);
    const requested = await service.cancel(checkout.body.id, key("cancel"));
    expect(requested.body.status).toBe("cancel_pending");
    expect((await db.selectFrom("products").selectAll().where("id", "=", productId).executeTakeFirstOrThrow()).stock_on_hand).toBe(0);
    await service.dispatchPending(1);
    const providerPaymentId = (await service.getOrder(checkout.body.id)).payment.providerPaymentId!;
    const eventId = key("canceled");
    expect((await send(app, "payment.canceled", providerPaymentId, eventId)).statusCode).toBe(200);
    expect((await send(app, "payment.canceled", providerPaymentId, eventId)).statusCode).toBe(200);
    const order = await service.getOrder(checkout.body.id);
    expect(order.status).toBe("canceled");
    expect((await db.selectFrom("products").selectAll().where("id", "=", productId).executeTakeFirstOrThrow()).stock_on_hand).toBe(1);
    const releases = await db.selectFrom("inventory_movements").selectAll().where("kind", "=", "release").execute();
    expect(releases).toHaveLength(1);
  });

  it("cancel_pending에서 결제 성공이 먼저 오면 paid가 되고 재고를 반환하지 않는다", async () => {
    const { productId, checkout, service } = await createDispatchedOrder();
    const app = await buildTestApp(service);
    apps.push(app);
    await service.cancel(checkout.body.id, key("cancel_race"));
    const providerPaymentId = (await service.getOrder(checkout.body.id)).payment.providerPaymentId!;
    await send(app, "payment.succeeded", providerPaymentId);
    expect((await service.getOrder(checkout.body.id)).status).toBe("paid");
    expect((await db.selectFrom("products").selectAll().where("id", "=", productId).executeTakeFirstOrThrow()).stock_on_hand).toBe(0);
  });

  it("paid 주문을 refund하고 terminal event에서 재고를 한 번 반환한다", async () => {
    const { productId, checkout, service } = await createDispatchedOrder();
    const app = await buildTestApp(service);
    apps.push(app);
    const providerPaymentId = (await service.getOrder(checkout.body.id)).payment.providerPaymentId!;
    await send(app, "payment.succeeded", providerPaymentId);
    const refund = await service.refund(checkout.body.id, key("refund"));
    expect(refund.body.status).toBe("refund_pending");
    await service.dispatchPending(1);
    const refundedEvent = key("refunded");
    await send(app, "payment.refunded", providerPaymentId, refundedEvent);
    await send(app, "payment.refunded", providerPaymentId, refundedEvent);
    expect((await service.getOrder(checkout.body.id)).status).toBe("refunded");
    expect((await db.selectFrom("products").selectAll().where("id", "=", productId).executeTakeFirstOrThrow()).stock_on_hand).toBe(1);
    expect(await db.selectFrom("inventory_movements").selectAll().where("kind", "=", "release").execute()).toHaveLength(1);
  });

  it("terminal refunded 상태를 늦은 success event가 되돌리지 않는다", async () => {
    const { checkout, service } = await createDispatchedOrder();
    const app = await buildTestApp(service);
    apps.push(app);
    const providerPaymentId = (await service.getOrder(checkout.body.id)).payment.providerPaymentId!;
    await send(app, "payment.succeeded", providerPaymentId);
    await service.refund(checkout.body.id, key("refund_late"));
    await service.dispatchPending(1);
    await send(app, "payment.refunded", providerPaymentId);
    const late = await send(app, "payment.succeeded", providerPaymentId, key("late_success"));
    expect(late.json()).toMatchObject({ outcome: "ignored_invalid_transition", orderStatus: "refunded" });
    expect((await service.getOrder(checkout.body.id)).status).toBe("refunded");
  });

  it("payment failure에서 주문과 payment를 종료하고 재고를 한 번 반환한다", async () => {
    const { productId, checkout, service } = await createDispatchedOrder();
    const app = await buildTestApp(service);
    apps.push(app);
    const providerPaymentId = (await service.getOrder(checkout.body.id)).payment.providerPaymentId!;
    const eventId = key("failed");
    await send(app, "payment.failed", providerPaymentId, eventId);
    await send(app, "payment.failed", providerPaymentId, eventId);
    const order = await service.getOrder(checkout.body.id);
    expect(order).toMatchObject({ status: "payment_failed", inventoryReleased: true, payment: { status: "failed" } });
    expect((await db.selectFrom("products").selectAll().where("id", "=", productId).executeTakeFirstOrThrow()).stock_on_hand).toBe(1);
    expect(await db.selectFrom("inventory_movements").selectAll().where("kind", "=", "release").execute()).toHaveLength(1);
  });

  it("같은 cancel idempotency key는 최초 pending 응답을 replay한다", async () => {
    const { checkout, service } = await createDispatchedOrder();
    const requestKey = key("cancel_replay");
    const first = await service.cancel(checkout.body.id, requestKey);
    const second = await service.cancel(checkout.body.id, requestKey);
    expect(first.replayed).toBe(false);
    expect(second.replayed).toBe(true);
    expect(second.body).toEqual(first.body);
    expect(await db.selectFrom("payment_commands").selectAll().where("kind", "=", "cancel").execute()).toHaveLength(1);
  });

});
