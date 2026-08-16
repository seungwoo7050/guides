import type { Kysely } from "kysely";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { ProviderEvent } from "../src/contracts";
import type { Database } from "../src/db";
import { HttpPaymentProvider } from "../src/payment-provider";
import {
  FakePaymentProvider,
  buildTestApp,
  createHarness,
  createTestDatabase,
  injectWebhook,
  key,
  resetDatabase,
  seedProduct,
  startMockProvider
} from "./helpers";

let db: Kysely<Database>;
const apps: Array<Awaited<ReturnType<typeof buildTestApp>>> = [];

beforeAll(async () => { db = await createTestDatabase(); });
afterAll(async () => { await db.destroy(); });
beforeEach(async () => { await resetDatabase(db); });
afterEach(async () => { while (apps.length) await apps.pop()!.close(); });

describe("Stage 04 - HTTP provider와 webhook", () => {
  it("실제 mock provider가 같은 command key의 외부 효과를 재사용한다", async () => {
    const providerProcess = await startMockProvider();
    try {
      const provider = new HttpPaymentProvider(providerProcess.baseUrl, 2000);
      const command = {
        id: key("provider_command"),
        orderId: "order_1",
        kind: "create" as const,
        amountMinor: 1000,
        currency: "KRW",
        providerPaymentId: null
      };
      const first = await provider.execute(command);
      const second = await provider.execute(command);
      expect(second.id).toBe(first.id);
      expect(second.providerPaymentId).toBe(first.providerPaymentId);
    } finally {
      await providerProcess.close();
    }
  });

  it("서명된 success event를 적용하고 duplicate delivery는 effect를 반복하지 않는다", async () => {
    const productId = await seedProduct(db, { stockOnHand: 1 });
    const provider = new FakePaymentProvider();
    const { service } = createHarness(db, provider);
    const checkout = await service.checkout(key(), { items: [{ productId, quantity: 1 }] });
    await service.dispatchPending(1);
    const current = await service.getOrder(checkout.body.id);
    const app = await buildTestApp(service);
    apps.push(app);
    const event: ProviderEvent = {
      id: key("event_success"),
      type: "payment.succeeded",
      providerPaymentId: current.payment.providerPaymentId!,
      occurredAt: new Date().toISOString()
    };
    const first = await injectWebhook(app, event);
    const second = await injectWebhook(app, event);
    const third = await injectWebhook(app, event);
    expect(first.statusCode).toBe(200);
    expect(second.json()).toMatchObject({ duplicate: true });
    expect(third.json()).toMatchObject({ duplicate: true });
    expect((await service.getOrder(checkout.body.id)).status).toBe("paid");
    const appliedEvents = await db.selectFrom("order_events").selectAll().where("event_type", "=", "payment.succeeded").execute();
    expect(appliedEvents).toHaveLength(1);
  });


  it("provider event가 payment identity 저장보다 먼저 와도 retry delivery에서 적용한다", async () => {
    const productId = await seedProduct(db, { stockOnHand: 1 });
    const provider = new FakePaymentProvider();
    const { service, repository } = createHarness(db, provider);
    const checkout = await service.checkout(key(), { items: [{ productId, quantity: 1 }] });
    const now = new Date();
    const command = await repository.claimNextPaymentCommand(now, new Date(now.getTime() - 1));
    expect(command).not.toBeNull();
    const operation = await provider.execute(command!);

    const app = await buildTestApp(service, now);
    apps.push(app);
    const event: ProviderEvent = {
      id: key("early_event"),
      type: "payment.succeeded",
      providerPaymentId: operation.providerPaymentId,
      occurredAt: now.toISOString()
    };
    const timestamp = Math.floor(now.getTime() / 1000);
    const early = await injectWebhook(app, event, { timestamp });
    expect(early.statusCode).toBe(503);
    expect(early.json()).toMatchObject({ outcome: "unknown_payment", duplicate: false });

    await repository.completePaymentCommand(command!, operation.id, operation.providerPaymentId, now);
    const retried = await injectWebhook(app, event, { timestamp });
    expect(retried.statusCode).toBe(200);
    expect(retried.json()).toMatchObject({ outcome: "applied", duplicate: true, orderId: checkout.body.id });
    expect((await service.getOrder(checkout.body.id)).status).toBe("paid");
  });

  it("잘못된 signature와 오래된 timestamp를 거부한다", async () => {
    const provider = new FakePaymentProvider();
    const { service } = createHarness(db, provider);
    const fixedNow = new Date("2026-01-01T00:00:00.000Z");
    const app = await buildTestApp(service, fixedNow);
    apps.push(app);
    const event: ProviderEvent = {
      id: key("event_invalid"),
      type: "payment.succeeded",
      providerPaymentId: "pay_unknown",
      occurredAt: fixedNow.toISOString()
    };
    const invalid = await injectWebhook(app, event, {
      timestamp: Math.floor(fixedNow.getTime() / 1000),
      signature: "0".repeat(64)
    });
    expect(invalid.statusCode).toBe(401);
    const stale = await injectWebhook(app, event, {
      timestamp: Math.floor(fixedNow.getTime() / 1000) - 301
    });
    expect(stale.statusCode).toBe(401);
    expect(await db.selectFrom("provider_events").selectAll().execute()).toHaveLength(0);
  });

  it("같은 event ID의 다른 payload를 충돌로 거부한다", async () => {
    const productId = await seedProduct(db);
    const provider = new FakePaymentProvider();
    const { service } = createHarness(db, provider);
    const checkout = await service.checkout(key(), { items: [{ productId, quantity: 1 }] });
    await service.dispatchPending(1);
    const paymentId = (await service.getOrder(checkout.body.id)).payment.providerPaymentId!;
    const app = await buildTestApp(service);
    apps.push(app);
    const eventId = key("same_event");
    const first = await injectWebhook(app, {
      id: eventId,
      type: "payment.succeeded",
      providerPaymentId: paymentId,
      occurredAt: new Date().toISOString()
    });
    expect(first.statusCode).toBe(200);
    const conflicting = await injectWebhook(app, {
      id: eventId,
      type: "payment.failed",
      providerPaymentId: paymentId,
      occurredAt: new Date().toISOString()
    });
    expect(conflicting.statusCode).toBe(409);
    expect((await service.getOrder(checkout.body.id)).status).toBe("paid");
  });
});
