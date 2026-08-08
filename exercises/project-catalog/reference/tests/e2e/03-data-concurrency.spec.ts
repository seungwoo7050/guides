import { expect, test } from "@playwright/test";

const resetToken = process.env.CATALOG_TEST_RESET_TOKEN;

test.beforeEach(async ({ request }) => {
  expect(resetToken, "Playwright reset token이 설정되어야 합니다.").toBeTruthy();
  const response = await request.post("/api/test/reset", {
    headers: { "x-catalog-test-token": resetToken ?? "" }
  });
  expect(response.status()).toBe(200);
});

test("@stage-03 검색 조건을 URL·reload·back에 복원합니다", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("검색어").fill("저장소");
  await page.getByRole("button", { name: "검색", exact: true }).click();

  await expect(page).toHaveURL(/q=%EC%A0%80%EC%9E%A5%EC%86%8C/);
  await expect(page.getByRole("heading", { name: "저장소 인덱스" })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("검색어")).toHaveValue("저장소");

  await page.getByLabel("검색어").fill("네트워크");
  await page.getByRole("button", { name: "검색", exact: true }).click();
  await expect(page.getByRole("heading", { name: "네트워크 흐름 분석" })).toBeVisible();
  await page.goBack();

  await expect(page.getByLabel("검색어")).toHaveValue("저장소");
  await expect(page.getByRole("heading", { name: "저장소 인덱스" })).toBeVisible();
});

test("@stage-03 취소를 무시하고 늦게 도착한 응답도 최신 화면을 덮지 않습니다", async ({ page }) => {
  await page.goto("/");
  await page.evaluate(() => {
    const nativeFetch = window.fetch.bind(window);
    let releaseOld: (() => void) | undefined;
    let oldSignal: AbortSignal | undefined;
    let oldStarted = false;

    const project = (id: string, title: string) => ({
      id,
      title,
      summary: `${title} 설명`,
      status: "active" as const,
      version: 1
    });
    const response = (value: unknown) =>
      new Response(JSON.stringify(value), {
        status: 200,
        headers: { "content-type": "application/json" }
      });

    window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(
        typeof input === "string" || input instanceof URL ? input.toString() : input.url,
        window.location.href
      );
      if (url.pathname === "/api/projects" && url.searchParams.get("q") === "네트워크") {
        oldStarted = true;
        oldSignal = init?.signal ?? undefined;
        return new Promise<Response>((resolve) => {
          releaseOld = () =>
            resolve(
              response({
                projects: [project("network-inspector", "네트워크 흐름 분석")],
                total: 1,
                page: 1,
                pageSize: 4
              })
            );
        });
      }
      if (url.pathname === "/api/projects" && url.searchParams.get("q") === "저장소") {
        return Promise.resolve(
          response({
            projects: [project("storage-index", "저장소 인덱스")],
            total: 1,
            page: 1,
            pageSize: 4
          })
        );
      }
      return nativeFetch(input, init);
    };

    Object.assign(window, {
      __catalogOldStarted: () => oldStarted,
      __catalogOldSignalAborted: () => Boolean(oldSignal?.aborted),
      __catalogReleaseOld: () => releaseOld?.()
    });
  });

  await page.getByLabel("검색어").fill("네트워크");
  await page.getByRole("button", { name: "검색", exact: true }).click();
  await expect
    .poll(() =>
      page.evaluate(() =>
        (window as typeof window & { __catalogOldStarted(): boolean }).__catalogOldStarted()
      )
    )
    .toBe(true);

  await page.getByLabel("검색어").fill("저장소");
  await page.getByLabel("검색어").press("Enter");
  await expect(page.getByRole("heading", { name: "저장소 인덱스" })).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() =>
        (
          window as typeof window & { __catalogOldSignalAborted(): boolean }
        ).__catalogOldSignalAborted()
      )
    )
    .toBe(true);

  await page.evaluate(() =>
    (window as typeof window & { __catalogReleaseOld(): void }).__catalogReleaseOld()
  );
  await expect(page.getByRole("heading", { name: "네트워크 흐름 분석" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "저장소 인덱스" })).toBeVisible();
});

test("@stage-03 malformed 성공 응답을 거절하고 이전 결과를 유지합니다", async ({ page }) => {
  await page.goto("/");
  await page.route("**/api/projects?*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ projects: "not-an-array", total: 1, page: 1, pageSize: 4 })
    });
  });

  await page.getByLabel("검색어").fill("malformed");
  await page.getByRole("button", { name: "검색", exact: true }).click();

  await expect(page.getByRole("status")).toContainText("서버 응답을 확인할 수 없어");
  await expect(page.getByRole("heading", { name: "네트워크 흐름 분석" })).toBeVisible();
});

test("@stage-03 409에서는 최신 서버 값과 로컬 초안을 함께 보존합니다", async ({ page }) => {
  await page.goto("/");
  const editButton = page
    .getByRole("article", { name: "네트워크 흐름 분석 프로젝트" })
    .getByRole("button", { name: "제목 수정" });
  await editButton.click();
  const input = page.getByLabel("프로젝트 제목");
  await input.fill("로컬 초안 제목");

  const external = await page.request.patch("/api/projects/network-inspector", {
    data: { title: "서버에서 바뀐 제목", version: 1 }
  });
  expect(external.status()).toBe(200);
  await page.getByRole("button", { name: "저장", exact: true }).click();

  await expect(page.getByRole("status")).toContainText("서버의 최신 제목");
  await expect(page.getByRole("heading", { name: "서버에서 바뀐 제목" })).toBeVisible();
  await expect(input).toHaveValue("로컬 초안 제목");
  await expect(input).toBeFocused();
});

test("@stage-03 일반 저장 실패에서는 서버 값을 복구하고 초안을 유지합니다", async ({ page }) => {
  await page.goto("/");
  await page.route("**/api/projects/network-inspector", async (route) => {
    if (route.request().method() === "PATCH") {
      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ code: "unavailable" })
      });
    } else {
      await route.continue();
    }
  });

  const article = page.getByRole("article", { name: "네트워크 흐름 분석 프로젝트" });
  await article.getByRole("button", { name: "제목 수정" }).click();
  const input = page.getByLabel("프로젝트 제목");
  await input.fill("실패해도 남을 초안");
  await page.getByRole("button", { name: "저장", exact: true }).click();

  await expect(page.getByRole("status")).toContainText("이전 서버 값으로 복구");
  await expect(page.getByRole("heading", { name: "네트워크 흐름 분석" })).toBeVisible();
  await expect(input).toHaveValue("실패해도 남을 초안");
  await expect(input).toBeFocused();
});
