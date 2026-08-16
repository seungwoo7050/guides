import type { ProviderOperationResponse } from "./contracts";

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
  constructor(private readonly baseUrl: string, private readonly timeoutMs: number) {
    void this.baseUrl;
    void this.timeoutMs;
  }

  async execute(_command: PaymentCommand): Promise<ProviderOperationResponse> {
    throw new Error("TODO Stage 04: timeout, idempotency header와 response schema를 가진 HTTP adapter를 구현하세요.");
  }
}
