import { Kysely, PostgresDialect, type Generated, type Insertable, type Selectable } from "kysely";
import { Pool } from "pg";

// [Implementation 2] 실제 SQL schema를 Kysely table type으로 옮겨 query column을 compile time에 제한하고 pool owner를 노출합니다.
interface EventTable {
  id: Generated<string>;
  name: string;
  created_at: Generated<Date>;
}
interface ReservationTable {
  id: Generated<string>;
  event_id: string;
  user_id: string;
  seat_no: number;
  created_at: Generated<Date>;
}
interface ReservationAuditTable {
  id: Generated<string>;
  reservation_id: string;
  action: "reserved";
  created_at: Generated<Date>;
}
export interface Database {
  events: EventTable;
  reservations: ReservationTable;
  reservation_audit: ReservationAuditTable;
}
export type EventRow = Selectable<EventTable>;
export type NewEvent = Insertable<EventTable>;

export function createDb(url = process.env.DATABASE_URL) {
  if (!url) throw new Error("DATABASE_URL이 필요합니다.");
  const pool = new Pool({ connectionString: url });
  return { db: new Kysely<Database>({ dialect: new PostgresDialect({ pool }) }), pool };
}
