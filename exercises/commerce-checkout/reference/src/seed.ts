import { createDatabase } from "./db";

const databaseUrl = process.env.DATABASE_URL;
if (!databaseUrl) throw new Error("DATABASE_URL이 필요합니다.");
const db = createDatabase(databaseUrl);
try {
  await db.insertInto("products").values([
    { id: "product_keyboard", sku: "KEYBOARD-01", name: "기계식 키보드", price_minor: 125000, currency: "KRW", stock_on_hand: 5, active: true },
    { id: "product_mouse", sku: "MOUSE-01", name: "무선 마우스", price_minor: 59000, currency: "KRW", stock_on_hand: 10, active: true }
  ]).onConflict((oc) => oc.column("id").doNothing()).execute();
  console.log("SEED COMPLETE");
} finally {
  await db.destroy();
}
