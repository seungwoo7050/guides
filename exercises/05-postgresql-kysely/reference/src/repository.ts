import type { Kysely, Transaction } from "kysely";
import type { Database } from "./db";

export class SeatTakenError extends Error {}

export async function createEvent(db: Kysely<Database>, name: string) {
  return db.insertInto("events").values({ name }).returningAll().executeTakeFirstOrThrow();
}

export async function reserveSeat(db: Kysely<Database>, input: { eventId: string; userId: string; seatNo: number }) {
  try {
    return await db.transaction().execute(async (trx) => reserveInTransaction(trx, input));
  } catch (error: unknown) {
    if (isUniqueViolation(error)) throw new SeatTakenError("seat_taken");
    throw error;
  }
}

async function reserveInTransaction(trx: Transaction<Database>, input: { eventId: string; userId: string; seatNo: number }) {
  return trx.insertInto("reservations").values({
    event_id: input.eventId,
    user_id: input.userId,
    seat_no: input.seatNo
  }).returningAll().executeTakeFirstOrThrow();
}

function isUniqueViolation(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && error.code === "23505";
}
