import { randomUUID } from "node:crypto";
import { spawn, type ChildProcess } from "node:child_process";
import { fileURLToPath } from "node:url";
import { sql, type Kysely } from "kysely";

import { buildApp } from "../src/app";
import type { ProviderEvent, ProviderOperationResponse } from "../src/contracts";
import { createDatabase, type Database } from "../src/db";
import { ProviderError } from "../src/errors";
import { runMigration } from "../src/migrate";
import type { PaymentCommand, PaymentProvider } from "../src/payment-provider";
import { CommerceRepository } from "../src/repository";
import { CheckoutService } from "../src/service";
import { signPaymentWebhook } from "../src/webhook";

export const WEBHOOK_SECRET = "guide-commerce-secret";

export function requireDatabaseUrl(): string {
  const value = process.env.DATABASE_URL;
  if (!value) throw new Error("DATABASE_URL이 필요합니다. commerce-checkout compose.test.yml을 시작하세요.");
  return value;
}

export async function createTestDatabase(): Promise<Kysely<Database>> {
  const databaseUrl = requireDatabaseUrl();
  await runMigration(databaseUrl);
  return createDatabase(databaseUrl);
}

export async function resetDatabase(db: Kysely<Database>): Promise<void> {
  await sql.raw(`
    truncate table
      provider_events,
      order_events,
      inventory_movements,
      payment_commands,
      idempotency_records,
      payments,
      order_items,
      orders,
      products
    restart identity cascade
  `).execute(db);
}

export async function seedProduct(
  db: Kysely<Database>,
  overrides: Partial<{
    id: string;
    sku: string;
    name: string;
    priceMinor: number;
    currency: string;
    stockOnHand: number;
    active: boolean;
  }> = {}
): Promise<string> {
  const id = overrides.id ?? `product_${randomUUID()}`;
  await db.insertInto("products").values({
    id,
    sku: overrides.sku ?? `SKU-${randomUUID()}`,
    name: overrides.name ?? "테스트 상품",
    price_minor: overrides.priceMinor ?? 10_000,
    currency: overrides.currency ?? "KRW",
    stock_on_hand: overrides.stockOnHand ?? 5,
    active: overrides.active ?? true
  }).execute();
  return id;
}

export function createHarness(
  db: Kysely<Database>,
  provider: PaymentProvider = new FakePaymentProvider(),
  options: { retryBaseDelayMs?: number; clock?: () => Date } = {}
) {
  const repository = new CommerceRepository(db);
  const service = new CheckoutService(repository, provider, {
    retryBaseDelayMs: options.retryBaseDelayMs ?? 0,
    ...(options.clock ? { clock: options.clock } : {})
  });
  return { repository, service, provider };
}

export class FakePaymentProvider implements PaymentProvider {
  readonly operations = new Map<string, { fingerprint: string; response: ProviderOperationResponse }>();
  readonly calls: PaymentCommand[] = [];
  failuresRemaining = 0;

  async execute(command: PaymentCommand): Promise<ProviderOperationResponse> {
    this.calls.push({ ...command });
    if (this.failuresRemaining > 0) {
      this.failuresRemaining -= 1;
      throw new ProviderError("simulated timeout", true);
    }
    const fingerprint = JSON.stringify({
      orderId: command.orderId,
      kind: command.kind,
      amountMinor: command.amountMinor,
      currency: command.currency,
      providerPaymentId: command.providerPaymentId
    });
    const existing = this.operations.get(command.id);
    if (existing) {
      if (existing.fingerprint !== fingerprint) throw new ProviderError("idempotency conflict", false, 409);
      return existing.response;
    }
    if (command.kind !== "create" && !command.providerPaymentId) {
      throw new ProviderError("provider payment ID가 필요합니다.", false, 422);
    }
    const response: ProviderOperationResponse = {
      id: `op_${randomUUID()}`,
      providerPaymentId: command.providerPaymentId ?? `pay_${randomUUID()}`,
      kind: command.kind,
      orderId: command.orderId,
      amountMinor: command.amountMinor,
      currency: command.currency,
      status: "accepted",
      createdAt: new Date().toISOString()
    };
    this.operations.set(command.id, { fingerprint, response });
    return response;
  }
}

export function key(prefix = "key"): string {
  return `${prefix}_${randomUUID()}`;
}

export async function buildTestApp(service: CheckoutService, now = new Date()) {
  return buildApp({
    service,
    webhookSecret: WEBHOOK_SECRET,
    webhookToleranceSeconds: 300,
    clock: () => now
  });
}

export async function injectWebhook(
  app: Awaited<ReturnType<typeof buildApp>>,
  event: ProviderEvent,
  options: { timestamp?: number; signature?: string; secret?: string } = {}
) {
  const raw = Buffer.from(JSON.stringify(event));
  const timestamp = options.timestamp ?? Math.floor(Date.now() / 1000);
  const signature = options.signature ?? signPaymentWebhook(raw, timestamp, options.secret ?? WEBHOOK_SECRET);
  return app.inject({
    method: "POST",
    url: "/webhooks/payment",
    headers: {
      "content-type": "application/vnd.guide-payment+json",
      "x-payment-timestamp": String(timestamp),
      "x-payment-signature": signature
    },
    payload: raw
  });
}

export async function startMockProvider(): Promise<{
  baseUrl: string;
  child: ChildProcess;
  close: () => Promise<void>;
}> {
  const script = fileURLToPath(new URL("../../fixtures/mock-payment-provider/server.mjs", import.meta.url));
  const child = spawn(process.execPath, [script], {
    env: { ...process.env, PORT: "0", WEBHOOK_SECRET },
    stdio: ["ignore", "pipe", "pipe"]
  });
  let stderr = "";
  child.stderr!.on("data", (chunk) => { stderr += chunk.toString(); });
  const port = await new Promise<number>((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error(`mock provider 시작 timeout: ${stderr}`)), 5000);
    let stdout = "";
    child.stdout!.on("data", (chunk) => {
      stdout += chunk.toString();
      const match = stdout.match(/MOCK_PROVIDER_READY (\d+)/);
      if (match?.[1]) {
        clearTimeout(timeout);
        resolve(Number(match[1]));
      }
    });
    child.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`mock provider가 준비 전에 종료되었습니다: ${code} ${stderr}`));
    });
    child.once("error", reject);
  });

  return {
    baseUrl: `http://127.0.0.1:${port}`,
    child,
    close: async () => {
      if (child.exitCode !== null) return;
      child.kill("SIGTERM");
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          child.kill("SIGKILL");
          reject(new Error("mock provider 종료 timeout"));
        }, 3000);
        child.once("exit", () => {
          clearTimeout(timeout);
          resolve();
        });
      });
    }
  };
}
