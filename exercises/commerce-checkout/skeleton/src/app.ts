import Fastify, { type FastifyInstance } from "fastify";
import { ZodError } from "zod";

import {
  checkoutBodySchema,
  dispatchBodySchema,
  idSchema,
  idempotencyKeySchema
} from "./contracts";
import { AppError, InvalidRequestError } from "./errors";
import type { CheckoutService } from "./service";
import { verifyPaymentWebhook } from "./webhook";

export type BuildAppOptions = {
  service: CheckoutService;
  webhookSecret: string;
  webhookToleranceSeconds?: number;
  clock?: () => Date;
  close?: () => Promise<void>;
  logger?: boolean;
};

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

  app.post("/checkouts", async (request, reply) => {
    const key = parseIdempotencyKey(request.headers["idempotency-key"]);
    const input = checkoutBodySchema.parse(request.body);
    const result = await options.service.checkout(key, input);
    if (result.replayed) reply.header("idempotency-replayed", "true");
    return reply.code(result.statusCode).send(result.body);
  });

  app.get<{ Params: { id: string } }>("/orders/:id", async (request) => {
    return options.service.getOrder(idSchema.parse(request.params.id));
  });

  app.post<{ Params: { id: string } }>("/orders/:id/cancel", async (request, reply) => {
    const orderId = idSchema.parse(request.params.id);
    const key = parseIdempotencyKey(request.headers["idempotency-key"]);
    const result = await options.service.cancel(orderId, key);
    if (result.replayed) reply.header("idempotency-replayed", "true");
    return reply.code(result.statusCode).send(result.body);
  });

  app.post<{ Params: { id: string } }>("/orders/:id/refund", async (request, reply) => {
    const orderId = idSchema.parse(request.params.id);
    const key = parseIdempotencyKey(request.headers["idempotency-key"]);
    const result = await options.service.refund(orderId, key);
    if (result.replayed) reply.header("idempotency-replayed", "true");
    return reply.code(result.statusCode).send(result.body);
  });

  app.post("/internal/payment-commands/dispatch", async (request, reply) => {
    const { limit } = dispatchBodySchema.parse(request.body ?? {});
    return reply.code(200).send({ results: await options.service.dispatchPending(limit) });
  });

  app.post("/webhooks/payment", async (request, reply) => {
    if (!Buffer.isBuffer(request.body)) throw new InvalidRequestError("webhook은 raw body content type을 사용해야 합니다.");
    const verified = verifyPaymentWebhook(
      request.body,
      firstHeader(request.headers["x-payment-timestamp"]),
      firstHeader(request.headers["x-payment-signature"]),
      options.webhookSecret,
      tolerance,
      clock()
    );
    const result = await options.service.applyProviderEvent(verified.event, verified.payloadHash);
    const statusCode = result.outcome === "unknown_payment" ? 503 : 200;
    return reply.code(statusCode).send(result);
  });

  app.setErrorHandler((error, request, reply) => {
    if (error instanceof ZodError) {
      return reply.code(400).send({
        code: "invalid_request",
        message: "요청 형식이 올바르지 않습니다.",
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
      message: "요청을 처리하지 못했습니다.",
      requestId: request.id
    });
  });

  if (options.close) app.addHook("onClose", options.close);
  await app.ready();
  return app;
}

function parseIdempotencyKey(value: string | string[] | undefined): string {
  const header = firstHeader(value);
  if (!header) throw new InvalidRequestError("Idempotency-Key header가 필요합니다.");
  return idempotencyKeySchema.parse(header);
}

function firstHeader(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
