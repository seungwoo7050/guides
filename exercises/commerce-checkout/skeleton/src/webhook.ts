import type { ProviderEvent } from "./contracts";

export type VerifiedWebhook = { event: ProviderEvent; payloadHash: string };

export function verifyPaymentWebhook(
  _rawBody: Buffer,
  _timestampHeader: string | undefined,
  _signatureHeader: string | undefined,
  _secret: string,
  _toleranceSeconds: number,
  _now: Date
): VerifiedWebhook {
  throw new Error("TODO Stage 04: timestamp, raw-body HMAC, JSON과 schema를 순서대로 검증하세요.");
}

export function signPaymentWebhook(_rawBody: Buffer, _timestampSeconds: number, _secret: string): string {
  throw new Error("TODO Stage 04: test와 mock provider가 공유하는 HMAC 형식을 구현하세요.");
}
