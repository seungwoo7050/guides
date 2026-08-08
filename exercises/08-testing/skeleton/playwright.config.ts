import { defineConfig } from "@playwright/test";

const portSeed = process.env.TESTING_E2E_PORT_SEED ?? String(process.pid);
process.env.TESTING_E2E_PORT_SEED = portSeed;
const port = 20000 + (Number(portSeed) % 10000);
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
