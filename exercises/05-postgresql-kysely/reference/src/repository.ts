import type { Kysely, Transaction } from "kysely";
import type { Database } from "./db";

export class SeatTakenError extends Error {}

export interface ReserveSeatOptions {
  afterReservation?: () => void | Promise<void>;
}

// [Implementation 4] 첫 query부터 Kysely value binding을 사용해 사용자 값을 SQL syntax와 분리합니다.
export async function createEvent(db: Kysely<Database>, name: string) {
  return db.insertInto("events").values({ name }).returningAll().executeTakeFirstOrThrow();
}

// [Implementation 5] transaction 수명을 use case에 두고 PostgreSQL unique failure만 안정된 domain failure로 변환합니다.
export async function reserveSeat(
  db: Kysely<Database>,
  input: { eventId: string; userId: string; seatNo: number },
  options: ReserveSeatOptions = {}
) {
  try {
    return await db.transaction().execute(async (trx) => reserveInTransaction(trx, input, options));
  } catch (error: unknown) {
    if (isUniqueViolation(error)) throw new SeatTakenError("seat_taken");
    throw error;
  }
}

// [Implementation 6] 예약 row와 audit row를 같은 transaction resource로 써서 둘이 함께 commit하거나 rollback되게 합니다.
async function reserveInTransaction(
  trx: Transaction<Database>,
  input: { eventId: string; userId: string; seatNo: number },
  options: ReserveSeatOptions
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
  await options.afterReservation?.();
  return reservation;
}

function isUniqueViolation(error: unknown): boolean {
  return typeof error === "object" && error !== null && "code" in error && error.code === "23505";
}
