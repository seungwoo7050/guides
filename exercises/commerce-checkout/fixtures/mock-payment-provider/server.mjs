import { createHmac, createHash, randomUUID } from "node:crypto";
import http from "node:http";

const requestedPort = Number(process.env.PORT ?? 55991);
const webhookUrl = process.env.WEBHOOK_URL ?? "http://127.0.0.1:3001/webhooks/payment";
const webhookSecret = process.env.WEBHOOK_SECRET ?? "guide-commerce-secret";
const operations = new Map();

const server = http.createServer(async (request, response) => {
  try {
    const url = new URL(request.url ?? "/", `http://${request.headers.host ?? "127.0.0.1"}`);

    if (request.method === "GET" && url.pathname === "/health") return json(response, 200, { ok: true });
    if (request.method === "GET" && url.pathname === "/operations") {
      return json(response, 200, { operations: [...operations.values()] });
    }
    if (request.method === "POST" && url.pathname === "/test/reset") {
      operations.clear();
      return json(response, 204);
    }
    if (request.method === "POST" && url.pathname === "/operations") {
      const key = header(request, "idempotency-key");
      if (!key) return json(response, 400, { code: "missing_idempotency_key" });
      const raw = await readBody(request);
      const body = parseJson(raw);
      const fingerprint = sha256(raw);
      const existing = operations.get(key);
      if (existing) {
        if (existing.requestFingerprint !== fingerprint) {
          return json(response, 409, { code: "idempotency_conflict" });
        }
        return json(response, 200, publicOperation(existing));
      }
      if (
        !body ||
        !["create", "cancel", "refund"].includes(body.kind) ||
        typeof body.orderId !== "string" ||
        !Number.isSafeInteger(body.amountMinor) ||
        body.amountMinor < 0 ||
        typeof body.currency !== "string" ||
        !/^[A-Z]{3}$/.test(body.currency) ||
        (body.kind !== "create" && (typeof body.providerPaymentId !== "string" || body.providerPaymentId.length === 0))
      ) {
        return json(response, 400, { code: "invalid_operation" });
      }
      const operation = {
        id: `op_${randomUUID()}`,
        providerPaymentId: body.providerPaymentId ?? `pay_${randomUUID()}`,
        kind: body.kind,
        orderId: body.orderId,
        amountMinor: body.amountMinor,
        currency: body.currency,
        status: "accepted",
        requestFingerprint: fingerprint,
        createdAt: new Date().toISOString()
      };
      operations.set(key, operation);
      return json(response, 201, publicOperation(operation));
    }
    if (request.method === "POST" && url.pathname === "/test/emit") {
      const body = parseJson(await readBody(request));
      const operation = [...operations.values()].find((item) => item.id === body?.operationId);
      if (!operation) return json(response, 404, { code: "operation_not_found" });
      if (!body || !["payment.succeeded", "payment.failed", "payment.canceled", "payment.refunded"].includes(body.type)) {
        return json(response, 400, { code: "invalid_event" });
      }
      const event = {
        id: body.eventId ?? `evt_${randomUUID()}`,
        type: body.type,
        providerPaymentId: operation.providerPaymentId,
        occurredAt: body.occurredAt ?? new Date().toISOString()
      };
      const raw = Buffer.from(JSON.stringify(event));
      const timestamp = body.timestamp ?? Math.floor(Date.now() / 1000);
      const signature = sign(timestamp, raw);
      const delivery = await fetch(webhookUrl, {
        method: "POST",
        headers: {
          "content-type": "application/vnd.guide-payment+json",
          "x-payment-timestamp": String(timestamp),
          "x-payment-signature": signature
        },
        body: raw,
        signal: AbortSignal.timeout(3000)
      });
      const responseText = await delivery.text();
      return json(response, 200, {
        deliveredStatus: delivery.status,
        deliveredBody: responseText,
        event
      });
    }
    return json(response, 404, { code: "not_found" });
  } catch (error) {
    return json(response, 500, { code: "provider_internal_error", message: error instanceof Error ? error.message : String(error) });
  }
});

server.listen(requestedPort, "127.0.0.1", () => {
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : requestedPort;
  console.log(`MOCK_PROVIDER_READY ${port}`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}

function publicOperation(operation) {
  const { requestFingerprint: _requestFingerprint, ...publicValue } = operation;
  return publicValue;
}

function sign(timestamp, raw) {
  return createHmac("sha256", webhookSecret).update(String(timestamp)).update(".").update(raw).digest("hex");
}

function header(request, name) {
  const value = request.headers[name];
  return Array.isArray(value) ? value[0] : value;
}

async function readBody(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    const buffer = Buffer.from(chunk);
    size += buffer.length;
    if (size > 64 * 1024) throw new Error("body_too_large");
    chunks.push(buffer);
  }
  return Buffer.concat(chunks);
}

function parseJson(raw) {
  try {
    return JSON.parse(raw.toString("utf8"));
  } catch {
    return null;
  }
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function json(response, status, body) {
  response.statusCode = status;
  if (body === undefined || status === 204) return response.end();
  response.setHeader("content-type", "application/json; charset=utf-8");
  response.end(JSON.stringify(body));
}
