import { createHash, randomUUID } from "node:crypto";
import { defineConfig } from "@playwright/test";

// [Implementation 6] Give each browser run a deterministic isolated port and a dedicated web-server lifecycle so parallel runs cannot reuse hidden state.
const seed = process.env.COUNTER_E2E_PORT_SEED ?? `${process.cwd()}:${process.pid}:${randomUUID()}`;
process.env.COUNTER_E2E_PORT_SEED = seed;
const offset = createHash("sha256").update(seed).digest().readUInt32BE(0) % 10_000;
const port = 20_000 + offset;
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "tests",
  use: { baseURL, trace: "retain-on-failure" },
  webServer: {
    command: "pnpm dev",
    url: baseURL,
    reuseExistingServer: false,
    env: { COUNTER_PORT: String(port) }
  }
});
