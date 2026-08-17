import { buildApp } from "./app";

// [Implementation 5] Read the test- or operator-owned port only at the executable boundary and start the actual network listener there.
await buildApp().listen({
  host: "127.0.0.1",
  port: Number(process.env.COUNTER_PORT ?? 4100)
});
