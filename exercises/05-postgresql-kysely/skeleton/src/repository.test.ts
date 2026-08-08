import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createDb } from "./db";
import { createEvent, reserveSeat, SeatTakenError } from "./repository";

const enabled = Boolean(process.env.DATABASE_URL);
const suite = enabled ? describe : describe.skip;

suite("seat reservation", () => {
  let resources: ReturnType<typeof createDb>;
  beforeAll(async () => {
    resources = createDb();
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
  });
});
