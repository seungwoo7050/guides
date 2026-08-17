import { createHash, createHmac, timingSafeEqual } from "node:crypto";
import { providerEventSchema, type ProviderEvent } from "./contracts.js";
import { InvalidRequestError, UnauthorizedWebhookError } from "./errors.js";

export type VerifiedWebhook = { event: ProviderEvent; payloadHash: string };

// [Implementation 9] Authenticate the exact raw payload with a timestamped HMAC, constant-time comparison, replay tolerance, schema validation, and a payload identity hash.
export function verifyPaymentWebhook(
  rawBody: Buffer,
  timestampHeader: string | undefined,
  signatureHeader: string | undefined,
  secret: string,
  toleranceSeconds: number,
  now: Date
): VerifiedWebhook {
  if (!timestampHeader || !/^\d{10}$/.test(timestampHeader)) {
    throw new UnauthorizedWebhookError("The webhook timestamp is missing.");
  }
  if (!signatureHeader || !/^[a-f0-9]{64}$/i.test(signatureHeader)) {
    throw new UnauthorizedWebhookError("The webhook signature is missing.");
  }
  const timestampSeconds = Number(timestampHeader);
  if (!Number.isSafeInteger(timestampSeconds)) {
    throw new UnauthorizedWebhookError("The webhook timestamp is invalid.");
  }
  const age = Math.abs(Math.floor(now.getTime() / 1000) - timestampSeconds);
  if (age > toleranceSeconds) {
    throw new UnauthorizedWebhookError("The webhook timestamp is outside the allowed tolerance.");
  }

  const expected = createHmac("sha256", secret)
    .update(String(timestampSeconds)).update(".").update(rawBody).digest();
  const actual = Buffer.from(signatureHeader, "hex");
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
    throw new UnauthorizedWebhookError("The webhook signature does not match.");
  }

  let decoded: unknown;
  try {
    decoded = JSON.parse(rawBody.toString("utf8"));
  } catch {
    throw new InvalidRequestError("The webhook body is not valid JSON.");
  }
  return {
    event: providerEventSchema.parse(decoded),
    payloadHash: createHash("sha256").update(rawBody).digest("hex")
  };
}

export function signPaymentWebhook(rawBody: Buffer, timestampSeconds: number, secret: string): string {
  return createHmac("sha256", secret)
    .update(String(timestampSeconds)).update(".").update(rawBody).digest("hex");
}
