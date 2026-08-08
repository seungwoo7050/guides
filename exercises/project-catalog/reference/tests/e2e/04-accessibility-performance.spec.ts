import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

const resetToken = process.env.CATALOG_TEST_RESET_TOKEN;
const budget = JSON.parse(
  readFileSync(join(process.cwd(), "performance-budget.json"), "utf8")
) as {
  maximumInitialJavaScriptBytes: number;
  maximumDomNodes: number;
};

test.beforeEach(async ({ request }) => {
  expect(resetToken, "Playwright reset token이 설정되어야 합니다.").toBeTruthy();
  const response = await request.post("/api/test/reset", {
    headers: { "x-catalog-test-token": resetToken ?? "" }
  });
  expect(response.status()).toBe(200);
});

test("@stage-04 keyboard 취소와 연속 저장 뒤 시작 button으로 focus를 복구합니다", async ({ page }) => {
  await page.goto("/");
  const article = page.getByRole("article", { name: "네트워크 흐름 분석 프로젝트" });
  const editButton = article.getByRole("button", { name: "제목 수정" });

  await editButton.focus();
  await page.keyboard.press("Enter");
  const input = page.getByLabel("프로젝트 제목");
  await expect(input).toBeFocused();
  await input.fill("취소할 초안");
  await page.keyboard.press("Escape");
  await expect(editButton).toBeFocused();

  for (const title of ["첫 번째 키보드 저장 제목", "두 번째 키보드 저장 제목"]) {
    await page.keyboard.press("Enter");
    await expect(input).toBeFocused();
    await input.fill(title);
    await page.getByRole("button", { name: "저장", exact: true }).click();
    await expect(page.getByRole("article", { name: `${title} 프로젝트` })).toBeVisible();
    await expect(page.getByRole("status")).toContainText("제목을 저장했습니다");
    await expect(
      page
        .getByRole("article", { name: `${title} 프로젝트` })
        .getByRole("button", { name: "제목 수정" })
    ).toBeFocused();
  }
});

test("@stage-04 의미 구조와 focus-visible 표시가 존재합니다", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("main")).toHaveCount(1);
  await expect(page.getByRole("heading", { level: 1, name: "프로젝트 목록" })).toBeVisible();
  await expect(page.getByRole("search")).toBeVisible();
  await expect(page.getByLabel("검색어")).toBeVisible();
  await expect(page.getByLabel("상태")).toBeVisible();
  await expect(page.getByRole("list")).toBeVisible();

  const query = page.getByLabel("검색어");
  await query.focus();
  const focusStyle = await query.evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      width: Number.parseFloat(style.outlineWidth),
      style: style.outlineStyle,
      color: style.outlineColor
    };
  });
  expect(focusStyle.width).toBeGreaterThanOrEqual(2);
  expect(focusStyle.style).not.toBe("none");
  expect(focusStyle.color).not.toBe("transparent");
});

test("@stage-04 reduced motion에서 transition과 animation을 줄입니다", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const durations = await page.getByRole("button", { name: "검색", exact: true }).evaluate((element) => {
    const style = getComputedStyle(element);
    return {
      transition: style.transitionDuration,
      animation: style.animationDuration
    };
  });
  expect(maximumDurationInMilliseconds(durations.transition)).toBeLessThanOrEqual(0.01);
  expect(maximumDurationInMilliseconds(durations.animation)).toBeLessThanOrEqual(0.01);
});

test("@stage-04 320px·200% 확대·긴 제목에서도 가로 넘침이 없습니다", async ({ page }) => {
  const longTitle = "가".repeat(80);
  const update = await page.request.patch("/api/projects/network-inspector", {
    data: { title: longTitle, version: 1 }
  });
  expect(update.status()).toBe(200);

  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: longTitle })).toBeVisible();
  expect(await hasNoHorizontalOverflow(page)).toBe(true);

  await page.setViewportSize({ width: 640, height: 720 });
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  expect(await hasNoHorizontalOverflow(page)).toBe(true);
});

test("@stage-04 초기 JavaScript body와 DOM node가 예산 안에 있습니다", async ({ page }) => {
  const scriptBytes: number[] = [];
  page.on("response", async (response) => {
    if (response.request().resourceType() !== "script") return;
    try {
      scriptBytes.push((await response.body()).byteLength);
    } catch {
      // navigation이 끝나며 취소된 선택 script는 초기 body 합계에서 제외합니다.
    }
  });

  await page.goto("/", { waitUntil: "networkidle" });
  const totalScriptBytes = scriptBytes.reduce((total, size) => total + size, 0);
  const domNodes = await page.locator("*").count();

  expect(totalScriptBytes).toBeGreaterThan(0);
  expect(totalScriptBytes).toBeLessThanOrEqual(budget.maximumInitialJavaScriptBytes);
  expect(domNodes).toBeLessThanOrEqual(budget.maximumDomNodes);
});

function maximumDurationInMilliseconds(value: string) {
  return Math.max(
    ...value.split(",").map((entry) => {
      const duration = entry.trim();
      if (duration.endsWith("ms")) return Number.parseFloat(duration);
      if (duration.endsWith("s")) return Number.parseFloat(duration) * 1_000;
      return Number.POSITIVE_INFINITY;
    })
  );
}

async function hasNoHorizontalOverflow(page: Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth
  );
}
