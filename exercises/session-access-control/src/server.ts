import { buildApp } from "./app";
import { InMemorySecurityStore } from "./store";

// [Implementation 10] Start the network listener only at the executable composition root after selecting the concrete state owner and browser origin policy.
const port = parsePort(process.env.PORT ?? "4000");
const origins = (process.env.ALLOWED_ORIGINS ?? "http://localhost:3000")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

if (origins.length === 0) throw new Error("ALLOWED_ORIGINS must contain at least one origin");

await buildApp({
  store: new InMemorySecurityStore(),
  allowedOrigins: origins
}).listen({ host: "0.0.0.0", port });

function parsePort(value: string): number {
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new Error("PORT must be an integer between 1 and 65535");
  }
  return port;
}
