import { Kysely, PostgresDialect, type ColumnType, type Generated } from "kysely";
import { Pool, types } from "pg";

const INT8_OID = 20;

// [Implementation 5] Reject PostgreSQL bigint values outside JavaScript's safe range and expose a typed database whose pool is owned by Kysely.
types.setTypeParser(INT8_OID, (value) => {
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) {
    throw new Error(`PostgreSQL bigint exceeds the JavaScript safe-integer range: ${value}`);
  }
  return parsed;
});

type JsonValue = ColumnType<unknown, unknown, unknown>;
export interface ProductTable {
  id: string; sku: string; name: string; price_minor: number; currency: string;
  stock_on_hand: number; active: boolean; created_at: Generated<Date>; updated_at: Generated<Date>;
}
export interface OrderTable {
  id: string; status: string; currency: string; subtotal_minor: number; total_minor: number;
  inventory_released_at: Date | null; created_at: Generated<Date>; updated_at: Generated<Date>;
}
export interface OrderItemTable {
  order_id: string; product_id: string; sku: string; product_name: string;
  unit_price_minor: number; currency: string; quantity: number; line_total_minor: number;
}
export interface PaymentTable {
  id: string; order_id: string; provider_payment_id: string | null; status: string;
  amount_minor: number; currency: string; created_at: Generated<Date>; updated_at: Generated<Date>;
}
export interface IdempotencyTable {
  scope: string; key: string; request_hash: string; state: string;
  response_status: number | null; response_body: JsonValue | null;
  created_at: Generated<Date>; updated_at: Generated<Date>;
}
export interface PaymentCommandTable {
  id: string; order_id: string; kind: string; status: string; attempts: Generated<number>;
  provider_operation_id: string | null; last_error: string | null; next_attempt_at: Date;
  claimed_at: Date | null; claim_token: string | null; created_at: Generated<Date>; updated_at: Generated<Date>;
}
export interface ProviderEventTable {
  event_id: string; event_type: string; provider_payment_id: string;
  payload_hash: string; outcome: string; received_at: Generated<Date>;
}
export interface InventoryMovementTable {
  id: string; order_id: string; product_id: string; kind: string;
  quantity: number; created_at: Generated<Date>;
}
export interface OrderEventTable {
  id: string; order_id: string; event_type: string; data: JsonValue; created_at: Generated<Date>;
}
export interface Database {
  products: ProductTable;
  orders: OrderTable;
  order_items: OrderItemTable;
  payments: PaymentTable;
  idempotency_records: IdempotencyTable;
  payment_commands: PaymentCommandTable;
  provider_events: ProviderEventTable;
  inventory_movements: InventoryMovementTable;
  order_events: OrderEventTable;
}

export function createDatabase(databaseUrl: string): Kysely<Database> {
  return new Kysely<Database>({
    dialect: new PostgresDialect({ pool: new Pool({ connectionString: databaseUrl, max: 10 }) })
  });
}
