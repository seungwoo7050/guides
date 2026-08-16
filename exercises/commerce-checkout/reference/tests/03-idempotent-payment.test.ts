import type { Kysely } from "kysely";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { Database } from "../src/db";
import { FakePaymentProvider, createHarness, createTestDatabase, key, resetDatabase, seedProduct } from "./helpers";

let db: Kysely<Database>;

beforeAll(async () => { db = await createTestDatabase(); });
afterAll(async () => { await db.destroy(); });
beforeEach(async () => { await resetDatabase(db); });

describe("Stage 03 - Idempotent checkout과 payment command", () => {
  it("같은 key와 같은 request는 최초 응답을 replay한다", async () => {
    const productId = await seedProduct(db, { stockOnHand: 2 });
    const { service } = createHarness(db);
    const requestKey = key("same_request");
    const first = await service.checkout(requestKey, { items: [{ productId, quantity: 1 }] });
    const second = await service.checkout(requestKey, { items: [{ productId, quantity: 1 }] });
    expect(first.replayed).toBe(false);
    expect(second.replayed).toBe(true);
    expect(second.body).toEqual(first.body);
    expect(await db.selectFrom("orders").selectAll().execute()).toHaveLength(1);
    expect((await db.selectFrom("products").selectAll().where("id", "=", productId).executeTakeFirstOrThrow()).stock_on_hand).toBe(1);
  });

  it("동시에 같은 key가 들어와도 주문과 차감은 하나다", async () => {
    const productId = await seedProduct(db, { stockOnHand: 2 });
    const { service } = createHarness(db);
    const requestKey = key("concurrent_same");
    const [left, right] = await Promise.all([
      service.checkout(requestKey, { items: [{ productId, quantity: 1 }] }),
      service.checkout(requestKey, { items: [{ productId, quantity: 1 }] })
    ]);
    expect(left.body.id).toBe(right.body.id);
    expect([left.replayed, right.replayed].sort()).toEqual([false, true]);
    expect(await db.selectFrom("orders").selectAll().execute()).toHaveLength(1);
  });

  it("같은 key를 다른 request에 재사용하면 거부한다", async () => {
    const productId = await seedProduct(db, { stockOnHand: 3 });
    const { service } = createHarness(db);
    const requestKey = key("conflict");
    await service.checkout(requestKey, { items: [{ productId, quantity: 1 }] });
    await expect(service.checkout(requestKey, { items: [{ productId, quantity: 2 }] })).rejects.toMatchObject({ code: "idempotency_conflict" });
  });

  it("checkout transaction에 create-payment command를 함께 남긴다", async () => {
    const productId = await seedProduct(db);
    const { service } = createHarness(db);
    const result = await service.checkout(key(), { items: [{ productId, quantity: 1 }] });
    const command = await db.selectFrom("payment_commands").selectAll().where("order_id", "=", result.body.id).executeTakeFirstOrThrow();
    expect(command).toMatchObject({ kind: "create", status: "pending", attempts: 0 });
  });

  it("retryable provider 실패 뒤 같은 command identity로 재시도한다", async () => {
    const productId = await seedProduct(db);
    const provider = new FakePaymentProvider();
    provider.failuresRemaining = 1;
    const { service } = createHarness(db, provider, { retryBaseDelayMs: 0 });
    await service.checkout(key(), { items: [{ productId, quantity: 1 }] });
    expect(await service.dispatchPending(1)).toMatchObject([{ status: "retry_scheduled", attempts: 1 }]);
    expect(await service.dispatchPending(1)).toMatchObject([{ status: "sent" }]);
    const command = await db.selectFrom("payment_commands").selectAll().executeTakeFirstOrThrow();
    expect(command).toMatchObject({ status: "sent", attempts: 2 });
    expect(provider.calls[0]?.id).toBe(provider.calls[1]?.id);
    expect(provider.operations.size).toBe(1);
  });


  it("provider 성공 뒤 내부 저장 실패는 같은 command로 재시도한다", async () => {
    const productId = await seedProduct(db);
    const provider = new FakePaymentProvider();
    const { service, repository } = createHarness(db, provider, { retryBaseDelayMs: 0 });
    const original = repository.completePaymentCommand.bind(repository);
    let failOnce = true;
    const spy = vi.spyOn(repository, "completePaymentCommand").mockImplementation(async (...args) => {
      if (failOnce) {
        failOnce = false;
        throw new Error("simulated internal persistence failure");
      }
      return original(...args);
    });
    try {
      await service.checkout(key(), { items: [{ productId, quantity: 1 }] });
      expect(await service.dispatchPending(1)).toMatchObject([{ status: "retry_scheduled", attempts: 1 }]);
      expect(await service.dispatchPending(1)).toMatchObject([{ status: "sent" }]);
      expect(provider.calls[0]?.id).toBe(provider.calls[1]?.id);
      expect(provider.operations.size).toBe(1);
    } finally {
      spy.mockRestore();
    }
  });

  it("lease 만료 뒤 stale worker가 새 claim을 완료하거나 실패 처리하지 못한다", async () => {
    const productId = await seedProduct(db);
    const { service, repository } = createHarness(db);
    await service.checkout(key(), { items: [{ productId, quantity: 1 }] });

    const firstTime = new Date("2026-01-01T00:00:00.000Z");
    const first = await repository.claimNextPaymentCommand(firstTime, new Date(firstTime.getTime() - 1));
    expect(first).not.toBeNull();

    const secondTime = new Date(firstTime.getTime() + 60_000);
    const second = await repository.claimNextPaymentCommand(secondTime, new Date(firstTime.getTime() + 1));
    expect(second).not.toBeNull();
    expect(second!.claimToken).not.toBe(first!.claimToken);

    await expect(repository.completePaymentCommand(
      first!,
      key("stale_operation"),
      key("stale_payment"),
      secondTime
    )).rejects.toMatchObject({ code: "command_not_claimed" });

    await repository.completePaymentCommand(
      second!,
      key("current_operation"),
      key("current_payment"),
      secondTime
    );
    const command = await db.selectFrom("payment_commands").selectAll().executeTakeFirstOrThrow();
    expect(command).toMatchObject({ status: "sent", claim_token: null });
  });

  it("worker 둘이 경쟁해 같은 pending command를 한 번만 claim한다", async () => {
    const productId = await seedProduct(db);
    const provider = new FakePaymentProvider();
    const left = createHarness(db, provider, { retryBaseDelayMs: 0 });
    const right = createHarness(db, provider, { retryBaseDelayMs: 0 });
    await left.service.checkout(key(), { items: [{ productId, quantity: 1 }] });
    const [first, second] = await Promise.all([
      left.service.dispatchPending(1),
      right.service.dispatchPending(1)
    ]);
    const statuses = [first[0]?.status, second[0]?.status].sort();
    expect(statuses).toEqual(["idle", "sent"]);
    expect(provider.calls).toHaveLength(1);
    expect(await db.selectFrom("payment_commands").selectAll().where("status", "=", "sent").execute()).toHaveLength(1);
  });

});
