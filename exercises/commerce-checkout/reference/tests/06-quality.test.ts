import type { Kysely } from "kysely";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { ProviderEvent, ProviderOperationResponse } from "../src/contracts";
import type { PaymentCommand, PaymentProvider } from "../src/payment-provider";
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

describe("Stage 06 - API 품질과 실패 경계", () => {
  it("HTTP checkout의 stable error와 replay header를 제공한다", async () => {
    const productId = await seedProduct(db, { stockOnHand: 2 });
    const { service } = createHarness(db, new FakePaymentProvider());
    const app = await buildTestApp(service);
    apps.push(app);
    const missingKey = await app.inject({ method: "POST", url: "/checkouts", payload: { items: [{ productId, quantity: 1 }] } });
    expect(missingKey.statusCode).toBe(400);
    expect(missingKey.json()).toMatchObject({ code: "invalid_request" });

    const requestKey = key("http_checkout");
    const first = await app.inject({
      method: "POST",
      url: "/checkouts",
      headers: { "idempotency-key": requestKey },
      payload: { items: [{ productId, quantity: 1 }] }
    });
    const second = await app.inject({
      method: "POST",
      url: "/checkouts",
      headers: { "idempotency-key": requestKey },
      payload: { items: [{ productId, quantity: 1 }] }
    });
    expect(first.statusCode).toBe(201);
    expect(second.statusCode).toBe(201);
    expect(second.headers["idempotency-replayed"]).toBe("true");
    expect(second.json()).toEqual(first.json());
  });

  it("internal dispatch route가 durable command를 처리한다", async () => {
    const productId = await seedProduct(db);
    const provider = new FakePaymentProvider();
    const { service } = createHarness(db, provider);
    const app = await buildTestApp(service);
    apps.push(app);
    await service.checkout(key(), { items: [{ productId, quantity: 1 }] });
    const dispatched = await app.inject({ method: "POST", url: "/internal/payment-commands/dispatch", payload: { limit: 1 } });
    expect(dispatched.statusCode).toBe(200);
    expect(dispatched.json()).toMatchObject({ results: [{ status: "sent", kind: "create" }] });
  });

  it("유효하지만 모르는 payment webhook은 격리하고 retry 가능한 503을 반환한다", async () => {
    const { service } = createHarness(db, new FakePaymentProvider());
    const app = await buildTestApp(service);
    apps.push(app);
    const event: ProviderEvent = {
      id: key("unknown_event"),
      type: "payment.succeeded",
      providerPaymentId: "pay_missing",
      occurredAt: new Date().toISOString()
    };
    const response = await injectWebhook(app, event);
    expect(response.statusCode).toBe(503);
    expect(response.json()).toMatchObject({ outcome: "unknown_payment", orderId: null });
    const stored = await db.selectFrom("provider_events").selectAll().where("event_id", "=", event.id).executeTakeFirstOrThrow();
    expect(stored.outcome).toBe("unknown_payment");
  });

  it("provider가 command와 다른 응답을 주면 sent로 기록하지 않는다", async () => {
    const productId = await seedProduct(db);
    const badProvider: PaymentProvider = {
      async execute(command: PaymentCommand): Promise<ProviderOperationResponse> {
        return {
          id: key("bad_operation"),
          providerPaymentId: key("bad_payment"),
          kind: command.kind,
          orderId: command.orderId,
          amountMinor: command.amountMinor + 1,
          currency: command.currency,
          status: "accepted",
          createdAt: new Date().toISOString()
        };
      }
    };
    const { service } = createHarness(db, badProvider, { retryBaseDelayMs: 0 });
    await service.checkout(key(), { items: [{ productId, quantity: 1 }] });
    const result = await service.dispatchPending(1);
    expect(result).toMatchObject([{ status: "dead" }]);
    const command = await db.selectFrom("payment_commands").selectAll().executeTakeFirstOrThrow();
    const payment = await db.selectFrom("payments").selectAll().executeTakeFirstOrThrow();
    expect(command.status).toBe("dead");
    expect(payment.provider_payment_id).toBeNull();
  });

});
