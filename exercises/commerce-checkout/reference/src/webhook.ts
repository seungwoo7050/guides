import { createHash, createHmac, timingSafeEqual } from "node:crypto";

import { providerEventSchema, type ProviderEvent } from "./contracts";
import { InvalidRequestError, UnauthorizedWebhookError } from "./errors";

export type VerifiedWebhook = {
  event: ProviderEvent;
  payloadHash: string;
};

export function verifyPaymentWebhook(
  rawBody: Buffer,
  timestampHeader: string | undefined,
  signatureHeader: string | undefined,
  secret: string,
  toleranceSeconds: number,
  now: Date
): VerifiedWebhook {
  if (!timestampHeader || !/^\d{10}$/.test(timestampHeader)) {
    throw new UnauthorizedWebhookError("webhook timestamp가 없습니다.");
  }
  if (!signatureHeader || !/^[a-f0-9]{64}$/i.test(signatureHeader)) {
    throw new UnauthorizedWebhookError("webhook signature가 없습니다.");
  }
  const timestampSeconds = Number(timestampHeader);
  if (!Number.isSafeInteger(timestampSeconds)) throw new UnauthorizedWebhookError("webhook timestamp가 올바르지 않습니다.");
  const age = Math.abs(Math.floor(now.getTime() / 1000) - timestampSeconds);
  if (age > toleranceSeconds) throw new UnauthorizedWebhookError("webhook timestamp 허용 범위를 벗어났습니다.");

  const expected = createHmac("sha256", secret)
    .update(String(timestampSeconds))
    .update(".")
    .update(rawBody)
    .digest();
  const actual = Buffer.from(signatureHeader, "hex");
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
    throw new UnauthorizedWebhookError("webhook signature가 일치하지 않습니다.");
  }

  let decoded: unknown;
  try {
    decoded = JSON.parse(rawBody.toString("utf8"));
  } catch {
    throw new InvalidRequestError("webhook body가 유효한 JSON이 아닙니다.");
  }
  const event = providerEventSchema.parse(decoded);
  return {
    event,
    payloadHash: createHash("sha256").update(rawBody).digest("hex")
  };
}

export function signPaymentWebhook(rawBody: Buffer, timestampSeconds: number, secret: string): string {
  return createHmac("sha256", secret)
    .update(String(timestampSeconds))
    .update(".")
    .update(rawBody)
    .digest("hex");
}
