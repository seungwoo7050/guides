import { createHash, randomUUID } from "node:crypto";
import { defineConfig, devices } from "@playwright/test";

// [Implementation 8]
// 실제 browser evidence는 run별 난수 seed에서 파생한 port의 API·web process를 소유하고 재사용하지 않습니다.
// desktop/mobile project와 failure artifact는 unit·API evidence가 확인하지 못하는 사용자 경계를 담당합니다.
const portSeed = process.env.BOARD_E2E_PORT_SEED ?? `${process.cwd()}:${process.pid}:${randomUUID()}`;
process.env.BOARD_E2E_PORT_SEED = portSeed;
const portOffset = createHash("sha256").update(portSeed).digest().readUInt32BE(0) % 10000;
const webPort = 20000 + portOffset;
const apiPort = 40000 + portOffset;
const webUrl = `http://127.0.0.1:${webPort}`;
const apiUrl = `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  use: { baseURL: webUrl, trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } }
  ],
  webServer: [
    {
      command: "pnpm --filter @board/api start",
      url: `${apiUrl}/health`,
      reuseExistingServer: false,
      env: { PORT: String(apiPort), WEB_ORIGINS: webUrl }
    },
    {
      command: `pnpm --filter @board/web exec next dev --hostname 127.0.0.1 --port ${webPort}`,
      url: webUrl,
      reuseExistingServer: false,
      env: {
        NEXT_PUBLIC_API_BASE_URL: apiUrl,
        NEXT_PUBLIC_WS_URL: `ws://127.0.0.1:${apiPort}/ws`
      }
    }
  ]
});
