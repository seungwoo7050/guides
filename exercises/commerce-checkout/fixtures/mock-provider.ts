import { randomUUID } from "node:crypto";
import Fastify from "fastify";
import { z } from "zod";
import { currencySchema, idSchema, amountMinorSchema } from "../src/contracts.js";

const OperationSchema = z.object({
  kind: z.enum(["create", "cancel", "refund"]),
  orderId: idSchema,
  amountMinor: amountMinorSchema,
  currency: currencySchema,
  providerPaymentId: idSchema.nullable()
}).strict();

type OperationInput = z.infer<typeof OperationSchema>;
type Operation = OperationInput & {
  id: string;
  providerPaymentId: string;
  status: "accepted";
  createdAt: string;
};
type CachedOperation = { requestFingerprint: string; operation: Operation };

const app = Fastify({ logger: true });
const operations = new Map<string, CachedOperation>();

// [Implementation 7-1] Preserve one provider-side effect per idempotency key while rejecting reuse of that key for a different command payload.
app.post("/operations", async (request, reply) => {
  const key = String(request.headers["idempotency-key"] ?? "");
  if (!key) return reply.code(400).send({ code: "missing_idempotency_key" });

  const input = OperationSchema.parse(request.body);
  const requestFingerprint = JSON.stringify(input);
  const cached = operations.get(key);
  if (cached) {
    if (cached.requestFingerprint !== requestFingerprint) {
      return reply.code(409).send({ code: "idempotency_key_reused" });
    }
    return cached.operation;
  }

  const operation: Operation = {
    id: `op_${randomUUID()}`,
    providerPaymentId: input.providerPaymentId ?? `provider_${randomUUID()}`,
    kind: input.kind,
    orderId: input.orderId,
    amountMinor: input.amountMinor,
    currency: input.currency,
    status: "accepted",
    createdAt: new Date().toISOString()
  };
  operations.set(key, { requestFingerprint, operation });
  return operation;
});

await app.listen({ host: "127.0.0.1", port: Number(process.env.PROVIDER_PORT ?? "3100") });
