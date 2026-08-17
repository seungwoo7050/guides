import type { CheckoutBody, OrderDto, ProviderEvent } from "./contracts.js";
import { ProviderError } from "./errors.js";
import type { PaymentProvider } from "./payment-provider.js";
import {
  CommerceRepository,
  hashCanonicalRequest,
  type IdempotentResult,
  type ProductDto,
  type ProviderEventApplyResult
} from "./repository.js";

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

// [Implementation 8] Coordinate canonical idempotency hashes, leased command dispatch, provider response matching, bounded exponential retry, and repository shutdown.
export class CheckoutService {
  private readonly clock: () => Date;
  private readonly maxCommandAttempts: number;
  private readonly retryBaseDelayMs: number;
  private readonly commandLeaseMs: number;

  constructor(
    private readonly repository: CommerceRepository,
    private readonly paymentProvider: PaymentProvider,
    options: ServiceOptions = {}
  ) {
    this.clock = options.clock ?? (() => new Date());
    this.maxCommandAttempts = options.maxCommandAttempts ?? 3;
    this.retryBaseDelayMs = options.retryBaseDelayMs ?? 1_000;
    this.commandLeaseMs = options.commandLeaseMs ?? 30_000;
  }

  listProducts(): Promise<ProductDto[]> { return this.repository.listProducts(); }
  getOrder(orderId: string): Promise<OrderDto> { return this.repository.getOrder(orderId); }

  checkout(idempotencyKey: string, input: CheckoutBody): Promise<IdempotentResult<OrderDto>> {
    const normalized: CheckoutBody = {
      items: [...input.items].sort((left, right) => left.productId.localeCompare(right.productId))
    };
    return this.repository.createCheckout(
      idempotencyKey,
      hashCanonicalRequest(normalized),
      normalized,
      this.clock()
    );
  }

  cancel(orderId: string, idempotencyKey: string): Promise<IdempotentResult<OrderDto>> {
    return this.repository.requestOrderCommand(
      orderId,
      "cancel",
      idempotencyKey,
      hashCanonicalRequest({ command: "cancel", orderId }),
      this.clock()
    );
  }

  refund(orderId: string, idempotencyKey: string): Promise<IdempotentResult<OrderDto>> {
    return this.repository.requestOrderCommand(
      orderId,
      "refund",
      idempotencyKey,
      hashCanonicalRequest({ command: "refund", orderId }),
      this.clock()
    );
  }

  async dispatchPending(limit: number): Promise<DispatchResult[]> {
    const results: DispatchResult[] = [];
    for (let index = 0; index < limit; index += 1) {
      const result = await this.dispatchOne();
      results.push(result);
      if (result.status === "idle") break;
    }
    return results;
  }

  applyProviderEvent(event: ProviderEvent, payloadHash: string): Promise<ProviderEventApplyResult> {
    return this.repository.applyProviderEvent(event, payloadHash, this.clock());
  }

  close(): Promise<void> { return this.repository.close(); }

  private async dispatchOne(): Promise<DispatchResult> {
    const now = this.clock();
    const command = await this.repository.claimNextPaymentCommand(
      now,
      new Date(now.getTime() - this.commandLeaseMs)
    );
    if (!command) return { status: "idle" };
    try {
      const operation = await this.paymentProvider.execute(command);
      if (
        operation.kind !== command.kind ||
        operation.orderId !== command.orderId ||
        operation.amountMinor !== command.amountMinor ||
        operation.currency !== command.currency ||
        (command.providerPaymentId !== null && operation.providerPaymentId !== command.providerPaymentId)
      ) {
        throw new ProviderError("The provider response does not match the command.", false);
      }
      await this.repository.completePaymentCommand(
        command,
        operation.id,
        operation.providerPaymentId,
        this.clock()
      );
      return {
        status: "sent",
        commandId: command.id,
        kind: command.kind,
        providerOperationId: operation.id
      };
    } catch (error) {
      const providerError = error instanceof ProviderError
        ? error
        : new ProviderError(error instanceof Error ? error.message : String(error), true);
      const failedAt = this.clock();
      const delay = this.retryBaseDelayMs * 2 ** Math.max(0, command.attempts - 1);
      const status = await this.repository.failPaymentCommand(
        command,
        providerError.message,
        providerError.retryable,
        this.maxCommandAttempts,
        new Date(failedAt.getTime() + delay),
        failedAt
      );
      return {
        status: status === "pending" ? "retry_scheduled" : "dead",
        commandId: command.id,
        kind: command.kind,
        attempts: command.attempts
      };
    }
  }
}
