import { buildApp } from "./app";

// [Implementation 10] Start the network listener only in the executable composition root after the realtime state boundaries are fully assembled.
const port = parsePort(process.env.PORT ?? "4000");
await (await buildApp()).listen({ host: "0.0.0.0", port });

function parsePort(value: string): number {
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1 || port > 65_535) {
    throw new Error("PORT must be an integer between 1 and 65535");
  }
  return port;
}
