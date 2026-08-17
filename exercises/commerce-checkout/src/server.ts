import { buildApp } from "./app.js";
import { loadConfig } from "./config.js";
import { createDatabase } from "./db.js";
import { HttpPaymentProvider } from "./payment-provider.js";
import { CommerceRepository } from "./repository.js";
import { CheckoutService } from "./service.js";

// [Implementation 11] Select concrete database and provider adapters, bind application shutdown to their lifecycle, and open the network listener only at the executable boundary.
const config = loadConfig(process.env);
const service = new CheckoutService(
  new CommerceRepository(createDatabase(config.DATABASE_URL)),
  new HttpPaymentProvider(config.PAYMENT_PROVIDER_URL, config.PAYMENT_PROVIDER_TIMEOUT_MS)
);
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
