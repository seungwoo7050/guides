import { createHash, randomUUID } from "node:crypto";
import { defineConfig } from "@playwright/test";

const seed = process.env.BOARD_E2E_PORT_SEED ?? `${process.cwd()}:${process.pid}:${randomUUID()}`;
const digest = createHash("sha256").update(seed).digest();
const apiPort = 20_000 + digest.readUInt16BE(0) % 8_000;
const webPort = 30_000 + digest.readUInt16BE(2) % 8_000;
const apiUrl = `http://127.0.0.1:${apiPort}`;
const webUrl = `http://127.0.0.1:${webPort}`;

export default defineConfig({
  testDir: "tests",
  fullyParallel: false,
  use: { baseURL: webUrl, trace: "retain-on-failure" },
  webServer: [
    {
      command: "pnpm --filter @board/api start",
      url: `${apiUrl}/health`,
      reuseExistingServer: false,
      env: {
        PORT: String(apiPort),
        WEB_ORIGINS: webUrl,
        LOG_LEVEL: "silent"
      }
    },
    {
      command: `pnpm --filter @board/web dev -- --hostname 127.0.0.1 --port ${webPort}`,
      url: webUrl,
      reuseExistingServer: false,
      env: {
        NEXT_PUBLIC_API_BASE_URL: apiUrl,
        NEXT_PUBLIC_WS_URL: `ws://127.0.0.1:${apiPort}/ws`
      }
    }
  ]
});
