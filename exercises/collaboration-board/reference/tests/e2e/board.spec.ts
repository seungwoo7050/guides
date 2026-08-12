import { expect, test } from "@playwright/test";

// [Implementation 8-1]
// E2E는 구현 세부 selector 대신 label, role과 화면 결과로 로그인부터 board surface까지의 실제 사용자 계약을 증명합니다.
test("로그인 후 보드 목록을 표시합니다", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("핸들").fill(`editor-${Date.now()}`);
  await page.getByLabel("표시 이름").fill("편집자");
  await page.getByRole("button", { name: "로그인" }).click();
  await expect(page.getByRole("heading", { name: /님의 보드/ })).toBeVisible();
});
