import { sql, type Kysely } from "kysely";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

import type { Database } from "../src/db";
import { createHarness, createTestDatabase, key, resetDatabase, seedProduct } from "./helpers";

let db: Kysely<Database>;

beforeAll(async () => { db = await createTestDatabase(); });
afterAll(async () => { await db.destroy(); });
beforeEach(async () => { await resetDatabase(db); });

describe("Stage 02 - Checkout과 inventory", () => {
  it("stock=1 경쟁 checkout에서 정확히 하나만 성공한다", async () => {
    const productId = await seedProduct(db, { id: "limited", stockOnHand: 1 });
    const { service } = createHarness(db);
    const results = await Promise.allSettled([
      service.checkout(key("checkout_a"), { items: [{ productId, quantity: 1 }] }),
      service.checkout(key("checkout_b"), { items: [{ productId, quantity: 1 }] })
    ]);
    expect(results.filter((result) => result.status === "fulfilled")).toHaveLength(1);
    expect(results.filter((result) => result.status === "rejected")).toHaveLength(1);
    const product = await db.selectFrom("products").selectAll().where("id", "=", productId).executeTakeFirstOrThrow();
    const orders = await db.selectFrom("orders").select(({ fn }) => fn.countAll<number>().as("count")).executeTakeFirstOrThrow();
    const reserves = await db.selectFrom("inventory_movements").select(({ fn }) => fn.countAll<number>().as("count")).where("kind", "=", "reserve").executeTakeFirstOrThrow();
    expect(product.stock_on_hand).toBe(0);
    expect(Number(orders.count)).toBe(1);
    expect(Number(reserves.count)).toBe(1);
  });

  it("여러 상품 중 하나가 부족하면 주문과 모든 차감을 rollback한다", async () => {
    const first = await seedProduct(db, { id: "first", stockOnHand: 3 });
    const second = await seedProduct(db, { id: "second", stockOnHand: 0 });
    const { service } = createHarness(db);
    await expect(service.checkout(key(), {
      items: [{ productId: first, quantity: 2 }, { productId: second, quantity: 1 }]
    })).rejects.toThrow(/재고/);
    const rows = await db.selectFrom("products").select(["id", "stock_on_hand"]).orderBy("id").execute();
    expect(rows).toEqual([{ id: "first", stock_on_hand: 3 }, { id: "second", stock_on_hand: 0 }]);
    expect(await db.selectFrom("orders").selectAll().execute()).toHaveLength(0);
  });

  it("stock 차감 뒤 movement insert 실패도 transaction 전체를 rollback한다", async () => {
    const productId = await seedProduct(db, { id: "triggered", stockOnHand: 2 });
    await sql.raw(`
      create or replace function commerce_fail_reserve() returns trigger language plpgsql as $$
      begin
        if new.kind = 'reserve' then raise exception 'forced reserve failure'; end if;
        return new;
      end $$;
      create trigger commerce_fail_reserve_trigger
      before insert on inventory_movements
      for each row execute function commerce_fail_reserve();
    `).execute(db);
    try {
      const { service } = createHarness(db);
      await expect(service.checkout(key(), { items: [{ productId, quantity: 1 }] })).rejects.toThrow(/forced reserve failure/);
      const product = await db.selectFrom("products").selectAll().where("id", "=", productId).executeTakeFirstOrThrow();
      expect(product.stock_on_hand).toBe(2);
      expect(await db.selectFrom("orders").selectAll().execute()).toHaveLength(0);
      expect(await db.selectFrom("inventory_movements").selectAll().execute()).toHaveLength(0);
    } finally {
      await sql.raw(`drop trigger if exists commerce_fail_reserve_trigger on inventory_movements; drop function if exists commerce_fail_reserve();`).execute(db);
    }
  });

  it("서로 반대 순서의 multi-item 요청도 stable lock order로 완료한다", async () => {
    const first = await seedProduct(db, { id: "a", stockOnHand: 2 });
    const second = await seedProduct(db, { id: "b", stockOnHand: 2 });
    const { service } = createHarness(db);
    const results = await Promise.all([
      service.checkout(key("order_ab"), { items: [{ productId: first, quantity: 1 }, { productId: second, quantity: 1 }] }),
      service.checkout(key("order_ba"), { items: [{ productId: second, quantity: 1 }, { productId: first, quantity: 1 }] })
    ]);
    expect(results).toHaveLength(2);
    const products = await db.selectFrom("products").select(["id", "stock_on_hand"]).orderBy("id").execute();
    expect(products).toEqual([{ id: "a", stock_on_hand: 0 }, { id: "b", stock_on_hand: 0 }]);
  });
});
