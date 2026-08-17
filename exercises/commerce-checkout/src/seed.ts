import { loadConfig } from "./config.js";
import { createDatabase } from "./db.js";

const config = loadConfig(process.env);
const db = createDatabase(config.DATABASE_URL);
try {
  await db.insertInto("products").values([
    { id: "product_keyboard", sku: "KB-001", name: "Mechanical Keyboard", price_minor: 12900, currency: "USD", stock_on_hand: 10, active: true },
    { id: "product_mouse", sku: "MS-001", name: "Precision Mouse", price_minor: 6900, currency: "USD", stock_on_hand: 15, active: true },
    { id: "product_dock", sku: "DK-001", name: "USB-C Dock", price_minor: 15900, currency: "USD", stock_on_hand: 5, active: true }
  ]).onConflict((oc) => oc.column("id").doNothing()).execute();
  console.log("products seeded");
} finally {
  await db.destroy();
}
