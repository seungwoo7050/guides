import { createHash, randomUUID } from "node:crypto";
import { defineConfig } from "@playwright/test";

const portSeed = process.env.TESTING_E2E_PORT_SEED ?? `${process.cwd()}:${process.pid}:${randomUUID()}`;
process.env.TESTING_E2E_PORT_SEED = portSeed;
const portOffset = createHash("sha256").update(portSeed).digest().readUInt32BE(0) % 10000;
const port = 20000 + portOffset;
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "tests",
  use: { baseURL, trace: "retain-on-failure" },
  webServer: {
    command: "pnpm dev",
    url: baseURL,
    reuseExistingServer: false,
    env: { EXERCISE_PORT: String(port) }
  }
});
