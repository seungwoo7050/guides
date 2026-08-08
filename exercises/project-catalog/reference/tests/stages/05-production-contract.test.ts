import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GET as getHealth } from "../../app/api/health/route";
import { POST as resetProjects } from "../../app/api/test/reset/route";
import { searchProjects, updateProject } from "../../lib/projects";

const original = {
  NODE_ENV: process.env.NODE_ENV,
  PLAYWRIGHT: process.env.PLAYWRIGHT,
  APP_RELEASE: process.env.APP_RELEASE,
  CATALOG_TEST_RESET_TOKEN: process.env.CATALOG_TEST_RESET_TOKEN,
  CATALOG_SERVER_ONLY_CANARY: process.env.CATALOG_SERVER_ONLY_CANARY
};

beforeEach(() => {
  restoreEnvironment();
});

afterEach(() => {
  vi.unstubAllEnvs();
  restoreEnvironment();
});

describe("Stage 05: production contract", () => {
  it("health는 status와 release만 no-store로 공개합니다", async () => {
    vi.stubEnv("APP_RELEASE", "test-release");
    vi.stubEnv("CATALOG_SERVER_ONLY_CANARY", "do-not-expose");
    const response = await getHealth();
    const body = await response.json();

    expect(response.headers.get("cache-control")).toContain("no-store");
    expect(body).toEqual({ status: "ok", release: "test-release" });
    expect(JSON.stringify(body)).not.toContain("do-not-expose");
  });

  it("reset endpoint는 test mode와 정확한 token을 모두 요구합니다", async () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("PLAYWRIGHT", "");
    vi.stubEnv("CATALOG_TEST_RESET_TOKEN", "expected");
    expect((await resetProjects(resetRequest("expected"))).status).toBe(404);

    vi.stubEnv("PLAYWRIGHT", "1");
    expect((await resetProjects(resetRequest("wrong"))).status).toBe(404);
    expect((await resetProjects(resetRequest("expected"))).status).toBe(200);
  });

  it("승인된 reset은 변경된 test data를 초기화합니다", async () => {
    vi.stubEnv("PLAYWRIGHT", "1");
    vi.stubEnv("CATALOG_TEST_RESET_TOKEN", "expected");
    updateProject("network-inspector", "변경된 제목", 1);
    expect(searchProjects({ q: "변경된", status: "any", page: 1 }).total).toBe(1);

    await resetProjects(resetRequest("expected"));
    expect(searchProjects({ q: "변경된", status: "any", page: 1 }).total).toBe(0);
  });
});

function resetRequest(token: string) {
  return new Request("http://localhost/api/test/reset", {
    method: "POST",
    headers: { "x-catalog-test-token": token }
  });
}

function restoreEnvironment() {
  for (const [key, value] of Object.entries(original)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
}
