import Fastify, { type FastifyInstance } from "fastify";
import { ZodError } from "zod";
import {
  checkoutBodySchema,
  dispatchBodySchema,
  idSchema,
  idempotencyKeySchema
} from "./contracts.js";
import { AppError, InvalidRequestError } from "./errors.js";
import type { CheckoutService } from "./service.js";
import { verifyPaymentWebhook } from "./webhook.js";

export type BuildAppOptions = {
  service: CheckoutService;
  webhookSecret: string;
  webhookToleranceSeconds?: number;
  clock?: () => Date;
  close?: () => Promise<void>;
  logger?: boolean;
};

// [Implementation 10] Build an injectable HTTP application with a bounded raw-webhook parser, stable error envelopes, and no listener or database allocation on import.
export async function buildApp(options: BuildAppOptions): Promise<FastifyInstance> {
  const app = Fastify({ logger: options.logger ?? false, bodyLimit: 64 * 1024 });
  const clock = options.clock ?? (() => new Date());
  const tolerance = options.webhookToleranceSeconds ?? 300;
  app.addContentTypeParser(
    "application/vnd.guide-payment+json",
    { parseAs: "buffer", bodyLimit: 64 * 1024 },
    (_request, body, done) => done(null, body)
  );
  app.get("/health", async () => ({ ok: true }));
  app.get("/products", async () => ({ products: await options.service.listProducts() }));

  // [Implementation 10-1] Require an idempotency key at every command route and preserve replay status while exposing immutable order snapshots through reads.
  app.post("/checkouts", async (request, reply) => {
    const key = parseIdempotencyKey(request.headers["idempotency-key"]);
    const result = await options.service.checkout(key, checkoutBodySchema.parse(request.body));
    if (result.replayed) reply.header("idempotency-replayed", "true");
    return reply.code(result.statusCode).send(result.body);
  });
  app.get<{ Params: { id: string } }>("/orders/:id", async (request) => {
    return options.service.getOrder(idSchema.parse(request.params.id));
  });
  app.post<{ Params: { id: string } }>("/orders/:id/cancel", async (request, reply) => {
    const result = await options.service.cancel(
      idSchema.parse(request.params.id),
      parseIdempotencyKey(request.headers["idempotency-key"])
    );
    if (result.replayed) reply.header("idempotency-replayed", "true");
    return reply.code(result.statusCode).send(result.body);
  });
  app.post<{ Params: { id: string } }>("/orders/:id/refund", async (request, reply) => {
    const result = await options.service.refund(
      idSchema.parse(request.params.id),
      parseIdempotencyKey(request.headers["idempotency-key"])
    );
    if (result.replayed) reply.header("idempotency-replayed", "true");
    return reply.code(result.statusCode).send(result.body);
  });

  // [Implementation 10-2] Keep command dispatch and raw signed webhook ingestion as explicit operational boundaries, returning retryable status for an event whose payment is not linked yet.
  app.post("/internal/payment-commands/dispatch", async (request, reply) => {
    const { limit } = dispatchBodySchema.parse(request.body ?? {});
    return reply.send({ results: await options.service.dispatchPending(limit) });
  });
  app.post("/webhooks/payment", async (request, reply) => {
    if (!Buffer.isBuffer(request.body)) {
      throw new InvalidRequestError("Webhook requests must use the raw-body content type.");
    }
    const verified = verifyPaymentWebhook(
      request.body,
      firstHeader(request.headers["x-payment-timestamp"]),
      firstHeader(request.headers["x-payment-signature"]),
      options.webhookSecret,
      tolerance,
      clock()
    );
    const result = await options.service.applyProviderEvent(verified.event, verified.payloadHash);
    return reply.code(result.outcome === "unknown_payment" ? 503 : 200).send(result);
  });

  app.setErrorHandler((error, request, reply) => {
    if (error instanceof ZodError) {
      return reply.code(400).send({
        code: "invalid_request",
        message: "The request format is invalid.",
        details: error.issues.map((issue) => ({ path: issue.path.join("."), reason: issue.code })),
        requestId: request.id
      });
    }
    if (error instanceof AppError) {
      return reply.code(error.statusCode).send({
        code: error.code,
        message: error.message,
        ...(error.details === undefined ? {} : { details: error.details }),
        requestId: request.id
      });
    }
    request.log.error({ err: error }, "unhandled request error");
    return reply.code(500).send({
      code: "internal_error",
      message: "The request could not be processed.",
      requestId: request.id
    });
  });

  if (options.close) app.addHook("onClose", options.close);
  await app.ready();
  return app;
}

function parseIdempotencyKey(value: string | string[] | undefined): string {
  const header = firstHeader(value);
  if (!header) throw new InvalidRequestError("The Idempotency-Key header is required.");
  return idempotencyKeySchema.parse(header);
}
function firstHeader(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
