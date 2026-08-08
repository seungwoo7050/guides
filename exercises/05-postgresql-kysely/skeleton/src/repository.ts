import type { Kysely } from "kysely";
import type { Database } from "./db";

export class SeatTakenError extends Error {}

export async function createEvent(db: Kysely<Database>, name: string) {
  // TODO: INSERT ... RETURNING 쿼리를 구현해 주세요.
  throw new Error("TODO");
}

export async function reserveSeat(db: Kysely<Database>, input: { eventId: string; userId: string; seatNo: number }) {
  // TODO: 트랜잭션을 사용하고 고유 제약 위반 코드 23505를 변환해 주세요.
  throw new Error("TODO");
}
