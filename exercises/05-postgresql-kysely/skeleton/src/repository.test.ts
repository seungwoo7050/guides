import { sql } from "kysely";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { createDb } from "./db";
import { createEvent, reserveSeat, SeatTakenError } from "./repository";

const enabled = Boolean(process.env.DATABASE_URL);
const suite = enabled ? describe : describe.skip;

suite("seat reservation", () => {
  let resources: ReturnType<typeof createDb>;
  beforeAll(async () => {
    resources = createDb();
  });
  beforeEach(async () => {
    await sql`delete from reservation_audit`.execute(resources.db);
    await resources.db.deleteFrom("reservations").execute();
    await resources.db.deleteFrom("events").execute();
  });
  afterAll(async () => {
    await resources.db.destroy();
    await resources.pool.end().catch(() => undefined);
  });
  it("allows only one concurrent reservation", async () => {
    const event = await createEvent(resources.db, "Final");
    const results = await Promise.allSettled([
      reserveSeat(resources.db, { eventId: event.id, userId: "a", seatNo: 1 }),
      reserveSeat(resources.db, { eventId: event.id, userId: "b", seatNo: 1 })
    ]);
    expect(results.filter((result) => result.status === "fulfilled")).toHaveLength(1);
    const rejected = results.find((result) => result.status === "rejected");
    expect((rejected as PromiseRejectedResult).reason).toBeInstanceOf(SeatTakenError);
    expect(await rowCount("reservations")).toBe(1);
    expect(await rowCount("reservation_audit")).toBe(1);
  });

  it("rolls back both the reservation and audit when the transaction fails", async () => {
    const event = await createEvent(resources.db, "Rollback final");
    let externallyVisibleBeforeCommit: [number, number] | undefined;
    await expect(reserveSeat(
      resources.db,
      { eventId: event.id, userId: "rollback-user", seatNo: 7 },
      {
        afterReservation: async () => {
          externallyVisibleBeforeCommit = [
            await rowCount("reservations"),
            await rowCount("reservation_audit")
          ];
          throw new Error("injected failure");
        }
      }
    )).rejects.toThrow("injected failure");
    expect(externallyVisibleBeforeCommit).toEqual([0, 0]);
    expect(await rowCount("reservations")).toBe(0);
    expect(await rowCount("reservation_audit")).toBe(0);
  });

  it("binds SQL-looking event and user input as values", async () => {
    const eventName = "safe' text'); drop table reservation_audit; --";
    const userId = "user' text'); drop table events; --";
    const event = await createEvent(resources.db, eventName);
    const reservation = await reserveSeat(resources.db, {
      eventId: event.id,
      userId,
      seatNo: 9
    });

    const storedEvent = await resources.db.selectFrom("events")
      .select("name")
      .where("id", "=", event.id)
      .executeTakeFirstOrThrow();
    const storedReservation = await resources.db.selectFrom("reservations")
      .select("user_id")
      .where("id", "=", reservation.id)
      .executeTakeFirstOrThrow();
    expect(storedEvent.name).toBe(eventName);
    expect(storedReservation.user_id).toBe(userId);
    expect(await rowCount("reservation_audit")).toBe(1);
  });

  async function rowCount(table: "reservations" | "reservation_audit") {
    const result = table === "reservations"
      ? await sql<{ count: string }>`select count(*)::text as count from reservations`.execute(resources.db)
      : await sql<{ count: string }>`select count(*)::text as count from reservation_audit`.execute(resources.db);
    return Number(result.rows[0]?.count ?? -1);
  }
});
