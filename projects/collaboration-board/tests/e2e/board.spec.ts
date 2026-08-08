import { expect, test } from "@playwright/test";

test("로그인 후 보드 목록을 표시합니다", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("핸들").fill(`editor-${Date.now()}`);
  await page.getByLabel("표시 이름").fill("편집자");
  await page.getByRole("button", { name: "로그인" }).click();
  await expect(page.getByRole("heading", { name: /님의 보드/ })).toBeVisible();
});
