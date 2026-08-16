import { providerOperationResponseSchema, type ProviderOperationResponse } from "./contracts";
import { ProviderError } from "./errors";

export type PaymentCommandKind = "create" | "cancel" | "refund";

export type PaymentCommand = {
  id: string;
  orderId: string;
  kind: PaymentCommandKind;
  amountMinor: number;
  currency: string;
  providerPaymentId: string | null;
};

export interface PaymentProvider {
  execute(command: PaymentCommand): Promise<ProviderOperationResponse>;
}

export class HttpPaymentProvider implements PaymentProvider {
  constructor(private readonly baseUrl: string, private readonly timeoutMs: number) {}

  async execute(command: PaymentCommand): Promise<ProviderOperationResponse> {
    let response: Response;
    try {
      response = await fetch(new URL("/operations", this.baseUrl), {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "idempotency-key": command.id
        },
        body: JSON.stringify({
          kind: command.kind,
          orderId: command.orderId,
          amountMinor: command.amountMinor,
          currency: command.currency,
          providerPaymentId: command.providerPaymentId
        }),
        signal: AbortSignal.timeout(this.timeoutMs)
      });
    } catch (error) {
      throw new ProviderError(error instanceof Error ? error.message : "provider network error", true);
    }

    const text = await response.text();
    let body: unknown;
    try {
      body = text ? JSON.parse(text) : null;
    } catch {
      throw new ProviderError("provider가 유효한 JSON을 반환하지 않았습니다.", response.status >= 500, response.status);
    }

    if (!response.ok) {
      const retryable = response.status === 408 || response.status === 425 || response.status === 429 || response.status >= 500;
      throw new ProviderError(`provider 요청 실패: HTTP ${response.status}`, retryable, response.status);
    }
    const parsed = providerOperationResponseSchema.safeParse(body);
    if (!parsed.success) throw new ProviderError("provider 응답 schema가 올바르지 않습니다.", false, response.status);
    const operation = parsed.data;
    if (
      operation.kind !== command.kind ||
      operation.orderId !== command.orderId ||
      operation.amountMinor !== command.amountMinor ||
      operation.currency !== command.currency ||
      (command.providerPaymentId !== null && operation.providerPaymentId !== command.providerPaymentId)
    ) {
      throw new ProviderError("provider 응답이 보낸 command와 일치하지 않습니다.", false, response.status);
    }
    return operation;
  }
}
