import type { CheckoutBody, OrderDto, ProviderEvent } from "./contracts";
import type { PaymentProvider } from "./payment-provider";
import {
  CommerceRepository,
  hashCanonicalRequest,
  type IdempotentResult,
  type ProductDto,
  type ProviderEventApplyResult
} from "./repository";

export type DispatchResult =
  | { status: "idle" }
  | { status: "sent"; commandId: string; kind: string; providerOperationId: string }
  | { status: "retry_scheduled" | "dead"; commandId: string; kind: string; attempts: number };

export type ServiceOptions = {
  clock?: () => Date;
  maxCommandAttempts?: number;
  retryBaseDelayMs?: number;
  commandLeaseMs?: number;
};

export class CheckoutService {
  private readonly clock: () => Date;

  constructor(
    private readonly repository: CommerceRepository,
    private readonly paymentProvider: PaymentProvider,
    private readonly options: ServiceOptions = {}
  ) {
    this.clock = options.clock ?? (() => new Date());
    void this.paymentProvider;
  }

  listProducts(): Promise<ProductDto[]> { return this.repository.listProducts(); }
  getOrder(orderId: string): Promise<OrderDto> { return this.repository.getOrder(orderId); }

  checkout(idempotencyKey: string, input: CheckoutBody): Promise<IdempotentResult<OrderDto>> {
    const normalized: CheckoutBody = { items: [...input.items].sort((a, b) => a.productId.localeCompare(b.productId)) };
    return this.repository.createCheckout(idempotencyKey, hashCanonicalRequest(normalized), normalized, this.clock());
  }

  cancel(orderId: string, idempotencyKey: string): Promise<IdempotentResult<OrderDto>> {
    return this.repository.requestOrderCommand(orderId, "cancel", idempotencyKey, hashCanonicalRequest({ orderId, command: "cancel" }), this.clock());
  }

  refund(orderId: string, idempotencyKey: string): Promise<IdempotentResult<OrderDto>> {
    return this.repository.requestOrderCommand(orderId, "refund", idempotencyKey, hashCanonicalRequest({ orderId, command: "refund" }), this.clock());
  }

  async dispatchPending(_limit: number): Promise<DispatchResult[]> {
    throw new Error("TODO Stage 03: claim → provider → complete/fail worker loop를 구현하세요.");
  }

  applyProviderEvent(event: ProviderEvent, payloadHash: string): Promise<ProviderEventApplyResult> {
    return this.repository.applyProviderEvent(event, payloadHash, this.clock());
  }

  async close(): Promise<void> { await this.repository.close(); }
}
