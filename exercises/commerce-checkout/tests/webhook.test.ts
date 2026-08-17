import { expect, it } from "vitest";
import { signPaymentWebhook, verifyPaymentWebhook } from "../src/webhook.js";

// [Implementation 12-1] Verify raw-body authenticity, timestamp tolerance, and payload identity independently of HTTP parsing and database state.
it("verifies the exact signed provider payload", () => {
  const now = new Date("2026-01-01T00:00:00.000Z");
  const timestamp = Math.floor(now.getTime() / 1000);
  const body = Buffer.from(JSON.stringify({
    id: "event_1",
    type: "payment.succeeded",
    providerPaymentId: "provider_1",
    occurredAt: now.toISOString()
  }));
  const secret = "a-secret-longer-than-sixteen";
  const verified = verifyPaymentWebhook(
    body,
    String(timestamp),
    signPaymentWebhook(body, timestamp, secret),
    secret,
    300,
    now
  );
  expect(verified.event.id).toBe("event_1");
  expect(verified.payloadHash).toMatch(/^[a-f0-9]{64}$/);
});

it("rejects signature reuse for a different raw payload", () => {
  const now = new Date("2026-01-01T00:00:00.000Z");
  const timestamp = Math.floor(now.getTime() / 1000);
  const secret = "a-secret-longer-than-sixteen";
  const signed = Buffer.from('{"id":"event_1"}');
  const changed = Buffer.from('{"id":"event_2"}');
  expect(() => verifyPaymentWebhook(
    changed,
    String(timestamp),
    signPaymentWebhook(signed, timestamp, secret),
    secret,
    300,
    now
  )).toThrow(/signature/);
});
