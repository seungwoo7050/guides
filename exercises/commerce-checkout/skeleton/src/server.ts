import { buildApp } from "./app";
import { loadConfig } from "./config";
import { createDatabase } from "./db";
import { HttpPaymentProvider } from "./payment-provider";
import { CommerceRepository } from "./repository";
import { CheckoutService } from "./service";

const config = loadConfig(process.env);
const db = createDatabase(config.DATABASE_URL);
const repository = new CommerceRepository(db);
const provider = new HttpPaymentProvider(config.PAYMENT_PROVIDER_URL, config.PAYMENT_PROVIDER_TIMEOUT_MS);
const service = new CheckoutService(repository, provider);
const app = await buildApp({
  service,
  webhookSecret: config.WEBHOOK_SECRET,
  webhookToleranceSeconds: config.WEBHOOK_TOLERANCE_SECONDS,
  close: () => service.close(),
  logger: true
});

await app.listen({ host: "127.0.0.1", port: config.PORT });

let closing = false;
for (const signal of ["SIGINT", "SIGTERM"] as const) {
  process.on(signal, async () => {
    if (closing) return;
    closing = true;
    app.log.info({ signal }, "shutdown started");
    await app.close();
  });
}
