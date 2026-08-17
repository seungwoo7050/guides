import type { Kysely, Transaction } from "kysely";
import type { Database } from "./db.js";

export class SeatTakenError extends Error {}

// [Implementation 4] Bind values through Kysely from the first query so user input remains separate from SQL syntax.
export async function createEvent(db: Kysely<Database>, name: string) {
  return db.insertInto("events")
    .values({ name })
    .returningAll()
    .executeTakeFirstOrThrow();
}

// [Implementation 5] Own the transaction at the use-case boundary and translate only PostgreSQL uniqueness failures into a stable domain error.
export async function reserveSeat(
  db: Kysely<Database>,
  input: { eventId: string; userId: string; seatNo: number }
) {
  try {
    return await db.transaction().execute(async (trx) => reserveInTransaction(trx, input));
  } catch (error: unknown) {
    if (isUniqueViolation(error)) throw new SeatTakenError("seat_taken");
    throw error;
  }
}

// [Implementation 6] Write the reservation and audit record through one transaction so both commit or both roll back.
async function reserveInTransaction(
  trx: Transaction<Database>,
  input: { eventId: string; userId: string; seatNo: number }
) {
  const reservation = await trx.insertInto("reservations").values({
    event_id: input.eventId,
    user_id: input.userId,
    seat_no: input.seatNo
  }).returningAll().executeTakeFirstOrThrow();

  await trx.insertInto("reservation_audit").values({
    reservation_id: reservation.id,
    action: "reserved"
  }).executeTakeFirstOrThrow();

  return reservation;
}

function isUniqueViolation(error: unknown): boolean {
  return typeof error === "object"
    && error !== null
    && "code" in error
    && error.code === "23505";
}
