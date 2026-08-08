import assert from "node:assert/strict";
import test from "node:test";
import type { ApplicationRepository } from "@capstone/db";
import { createApplication } from "./app.js";

test("health 계약과 멱등 종료 경계를 제공한다", async () => {
  let closeCount = 0;
  const repository: ApplicationRepository = {
    async close() {
      closeCount += 1;
    }
  };
  const application = createApplication(repository);
  const response = await application.app.inject({ method: "GET", url: "/health" });

  assert.equal(response.statusCode, 200);
  assert.deepEqual(response.json(), { status: "ok" });

  await Promise.all([application.close(), application.close()]);
  assert.equal(closeCount, 1);
});
