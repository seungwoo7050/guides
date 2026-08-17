import { readFile } from "node:fs/promises";
import { sql } from "kysely";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { createDatabase } from "../src/db.js";
import { CommerceRepository, hashCanonicalRequest } from "../src/repository.js";

const databaseUrl = process.env.TEST_DATABASE_URL;
const suite = databaseUrl ? describe : describe.skip;

// [Implementation 12-2] Exercise PostgreSQL row locking, idempotent replay, command leasing, event deduplication, and one-time inventory release against the real schema.
suite("commerce repository", () => {
  const db = createDatabase(databaseUrl!);
  const repository = new CommerceRepository(db);

  beforeAll(async () => {
    const migration = await readFile(new URL("../migrations/001_initial.sql", import.meta.url), "utf8");
    await sql.raw(migration).execute(db);
  });
  beforeEach(async () => {
    for (const table of [
      "order_events", "inventory_movements", "provider_events", "payment_commands",
      "idempotency_records", "payments", "order_items", "orders", "products"
    ] as const) await sql.raw(`delete from ${table}`).execute(db);
    await db.insertInto("products").values({
      id: "product_1", sku: "P-1", name: "Product", price_minor: 1000,
      currency: "USD", stock_on_hand: 1, active: true
    }).execute();
  });
  afterAll(async () => repository.close());

  it("allows only one checkout to reserve the final unit", async () => {
    const input = { items: [{ productId: "product_1", quantity: 1 }] };
    const results = await Promise.allSettled([
      repository.createCheckout("checkout-key-0001", hashCanonicalRequest(input), input, new Date()),
      repository.createCheckout("checkout-key-0002", hashCanonicalRequest(input), input, new Date())
    ]);
    expect(results.filter((result) => result.status === "fulfilled")).toHaveLength(1);
    expect(await db.selectFrom("orders").selectAll().execute()).toHaveLength(1);
  });

  it("replays the stored response for the same canonical request", async () => {
    const input = { items: [{ productId: "product_1", quantity: 1 }] };
    const hash = hashCanonicalRequest(input);
    const first = await repository.createCheckout("checkout-key-0003", hash, input, new Date());
    const replay = await repository.createCheckout("checkout-key-0003", hash, input, new Date());
    expect(replay.replayed).toBe(true);
    expect(replay.body.id).toBe(first.body.id);
  });

  it("leases one command at a time and schedules retry without releasing ownership early", async () => {
    const input = { items: [{ productId: "product_1", quantity: 1 }] };
    await repository.createCheckout("checkout-key-0004", hashCanonicalRequest(input), input, new Date());
    const now = new Date("2026-01-01T00:00:00.000Z");
    const first = await repository.claimNextPaymentCommand(now, new Date(now.getTime() - 30_000));
    expect(first).not.toBeNull();
    expect(await repository.claimNextPaymentCommand(now, new Date(now.getTime() - 30_000))).toBeNull();

    await repository.failPaymentCommand(
      first!,
      "temporary provider failure",
      true,
      3,
      new Date(now.getTime() + 1_000),
      now
    );
    expect(await repository.claimNextPaymentCommand(now, new Date(now.getTime() - 30_000))).toBeNull();
    const retried = await repository.claimNextPaymentCommand(
      new Date(now.getTime() + 1_000),
      new Date(now.getTime() - 29_000)
    );
    expect(retried).toMatchObject({ id: first!.id, attempts: 2 });
  });

  it("retries an early provider event after linkage and releases inventory exactly once", async () => {
    const input = { items: [{ productId: "product_1", quantity: 1 }] };
    const checkout = await repository.createCheckout(
      "checkout-key-0005",
      hashCanonicalRequest(input),
      input,
      new Date("2026-01-01T00:00:00.000Z")
    );
    const command = await repository.claimNextPaymentCommand(
      new Date("2026-01-01T00:00:01.000Z"),
      new Date("2025-12-31T23:59:31.000Z")
    );
    const event = {
      id: "event_early_1",
      type: "payment.failed" as const,
      providerPaymentId: "provider_payment_1",
      occurredAt: "2026-01-01T00:00:02.000Z"
    };
    const payloadHash = "a".repeat(64);

    expect(await repository.applyProviderEvent(event, payloadHash, new Date(event.occurredAt)))
      .toMatchObject({ outcome: "unknown_payment", duplicate: false });
    await repository.completePaymentCommand(
      command!,
      "provider_operation_1",
      event.providerPaymentId,
      new Date("2026-01-01T00:00:03.000Z")
    );
    expect(await repository.applyProviderEvent(event, payloadHash, new Date("2026-01-01T00:00:04.000Z")))
      .toMatchObject({ outcome: "applied", duplicate: true, orderId: checkout.body.id, orderStatus: "payment_failed" });

    const replay = await repository.applyProviderEvent(event, payloadHash, new Date("2026-01-01T00:00:05.000Z"));
    expect(replay).toMatchObject({ outcome: "applied", duplicate: true });
    expect(await repository.getOrder(checkout.body.id)).toMatchObject({
      status: "payment_failed",
      inventoryReleased: true
    });
    expect((await db.selectFrom("products").select("stock_on_hand").where("id", "=", "product_1").executeTakeFirstOrThrow()).stock_on_hand)
      .toBe(1);
    expect(await db.selectFrom("inventory_movements").selectAll().where("kind", "=", "release").execute())
      .toHaveLength(1);
  });
});
